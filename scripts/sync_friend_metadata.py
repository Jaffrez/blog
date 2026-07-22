from __future__ import annotations

import argparse
import io
import re
import sys
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlparse, urlunsplit
from urllib.request import Request, urlopen

from ruamel.yaml import YAML


DEFAULT_TIMEOUT = 10.0
MAX_RESPONSE_BYTES = 1_048_576
MAX_NAME_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 300
USER_AGENT = "JaffrezBlogFriendSync/1.0 (+https://jaffrez.io/friends/)"


@dataclass(frozen=True)
class FriendMetadata:
    name: str | None = None
    avatar: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class SyncResult:
    changed: bool
    updated_friends: int
    updated_fields: int
    warnings: tuple[str, ...]


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.icons: list[tuple[str, str, str]] = []
        self._in_title = False
        self._title_parts: list[str] = []

    @property
    def title(self) -> str:
        return "".join(self._title_parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {key.lower(): value or "" for key, value in attrs}

        if tag == "title":
            self._in_title = True
            return

        if tag == "meta":
            key = (attr_map.get("property") or attr_map.get("name") or "").lower()
            content = attr_map.get("content", "")
            if key and content and key not in self.meta:
                self.meta[key] = content
            return

        if tag == "link":
            rel_tokens = {token.lower() for token in attr_map.get("rel", "").split()}
            href = attr_map.get("href", "")
            if href and ("icon" in rel_tokens or "apple-touch-icon" in rel_tokens):
                kind = "apple-touch-icon" if "apple-touch-icon" in rel_tokens else "icon"
                self.icons.append((kind, href, attr_map.get("sizes", "")))

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)


def normalize_text(value: str | None, *, max_length: int) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"\s+", " ", value).strip()
    if not normalized or len(normalized) > max_length:
        return None
    return normalized


def normalize_http_url(value: str | None, base_url: str) -> str | None:
    if not value:
        return None
    absolute = urljoin(base_url, value.strip())
    parsed = urlparse(absolute)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return absolute


def friend_key(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ValueError("must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise ValueError("must not contain credentials")

    try:
        port = parsed.port
    except ValueError as error:
        raise ValueError("contains an invalid port") from error

    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    netloc = host if port is None or default_port else f"{host}:{port}"
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))


def icon_size_score(sizes: str) -> int:
    scores: list[int] = []
    for token in sizes.lower().split():
        match = re.fullmatch(r"(\d+)x(\d+)", token)
        if match:
            scores.append(int(match.group(1)) * int(match.group(2)))
    return max(scores, default=0)


def select_icon(parser: MetadataParser, base_url: str) -> str | None:
    for kind in ("apple-touch-icon", "icon"):
        candidates = [item for item in parser.icons if item[0] == kind]
        candidates.sort(key=lambda item: icon_size_score(item[2]), reverse=True)
        for _, href, _ in candidates:
            normalized = normalize_http_url(href, base_url)
            if normalized:
                return normalized
    return normalize_http_url(parser.meta.get("og:image"), base_url)


def extract_metadata(html: str, final_url: str) -> FriendMetadata:
    parser = MetadataParser()
    parser.feed(html)
    parser.close()

    name = normalize_text(
        parser.meta.get("og:site_name") or parser.meta.get("og:title") or parser.title,
        max_length=MAX_NAME_LENGTH,
    )
    description = normalize_text(
        parser.meta.get("og:description") or parser.meta.get("description"),
        max_length=MAX_DESCRIPTION_LENGTH,
    )
    return FriendMetadata(
        name=name,
        avatar=select_icon(parser, final_url),
        description=description,
    )


def fetch_metadata(url: str, *, timeout: float = DEFAULT_TIMEOUT) -> FriendMetadata:
    request = Request(
        url,
        headers={
            "Accept": "text/html,application/xhtml+xml",
            "User-Agent": USER_AGENT,
        },
    )
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise ValueError(f"unsupported content type: {content_type}")

        payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("response exceeds 1 MiB limit")

        encoding = response.headers.get_content_charset() or "utf-8"
        html = payload.decode(encoding, errors="replace")
        return extract_metadata(html, response.geturl())


def sync_enabled(friend: dict, field: str) -> bool:
    key = f"sync_{field}"
    value = friend.get(key, True)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be true or false")
    return value


def load_yaml(path: Path) -> tuple[YAML, dict]:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.load(stream)
    if not isinstance(data, dict) or not isinstance(data.get("friends"), dict):
        raise ValueError("friends data must contain a 'friends' URL mapping")
    return yaml, data


def dump_yaml(yaml: YAML, data: dict) -> str:
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    return buffer.getvalue()


def write_atomic(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as stream:
        stream.write(content)
        temp_path = Path(stream.name)
    temp_path.replace(path)


def sync_friends(
    path: Path,
    *,
    fetcher: Callable[[str], FriendMetadata] = fetch_metadata,
    dry_run: bool = False,
) -> SyncResult:
    yaml, data = load_yaml(path)
    original = path.read_text(encoding="utf-8")
    warnings: list[str] = []
    updated_friends = 0
    updated_fields = 0

    seen_urls: dict[str, str] = {}
    for url, friend in data["friends"].items():
        if not isinstance(url, str):
            raise ValueError("friend URL keys must be strings")
        if not isinstance(friend, dict):
            raise ValueError(f"friend {url!r} must be a mapping")
        try:
            key = friend_key(url)
        except ValueError as error:
            raise ValueError(f"friend key {url!r} {error}") from error
        if key in seen_urls:
            raise ValueError(
                f"friend key {url!r} duplicates {seen_urls[key]!r}"
            )
        seen_urls[key] = url

    for url, friend in data["friends"].items():
        enabled = {
            field: sync_enabled(friend, field)
            for field in ("name", "avatar", "description")
        }
        if not any(enabled.values()):
            continue

        try:
            metadata = fetcher(url)
        except Exception as error:  # Remote failures must not erase known-good data.
            warning = f"{url}: {error}"
            warnings.append(warning)
            print(f"warning: {warning}", file=sys.stderr)
            continue

        friend_changed = False
        for field in ("name", "avatar", "description"):
            value = getattr(metadata, field)
            if enabled[field] and value and friend.get(field) != value:
                friend[field] = value
                updated_fields += 1
                friend_changed = True

        if friend_changed:
            updated_friends += 1

    rendered = dump_yaml(yaml, data) if updated_fields else original
    changed = updated_fields > 0 and rendered != original
    if changed and not dry_run:
        write_atomic(path, rendered)

    return SyncResult(
        changed=changed,
        updated_friends=updated_friends,
        updated_fields=updated_fields,
        warnings=tuple(warnings),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synchronize friend metadata from homepages")
    parser.add_argument("--file", type=Path, default=Path("data/friends.yaml"))
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    def configured_fetcher(url: str) -> FriendMetadata:
        return fetch_metadata(url, timeout=args.timeout)

    try:
        result = sync_friends(args.file, fetcher=configured_fetcher, dry_run=args.dry_run)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    action = "would update" if args.dry_run else "updated"
    if result.changed:
        print(
            f"{action} {result.updated_fields} field(s) across "
            f"{result.updated_friends} friend(s)"
        )
    else:
        print("friend metadata is already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
