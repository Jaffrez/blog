from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {name.lower(): value for name, value in attrs if value}

        for attr in ("href", "src"):
            if attr in attr_map:
                self.links.append((attr, attr_map[attr] or ""))

        if "id" in attr_map:
            self.ids.add(attr_map["id"] or "")

        if tag == "a" and "name" in attr_map:
            self.ids.add(attr_map["name"] or "")


def load_pages(root: Path) -> dict[Path, LinkParser]:
    pages: dict[Path, LinkParser] = {}
    for path in root.rglob("*.html"):
        parser = LinkParser()
        parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
        pages[path.resolve()] = parser
    return pages


def target_path(root: Path, source: Path, raw_path: str) -> Path:
    path = unquote(raw_path)
    if path.startswith("/"):
        target = root / path[1:]
    else:
        target = source.parent / path

    if raw_path.endswith("/") or target.is_dir():
        target = target / "index.html"
    elif not target.suffix:
        target = target / "index.html"

    return target.resolve()


def should_skip(parsed) -> bool:
    return (
        parsed.scheme in {"mailto", "tel", "javascript", "data"}
        or parsed.path == ""
        or parsed.path.endswith("/livereload.js")
    )


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "public").resolve()
    base_hosts = {urlparse(arg).netloc for arg in sys.argv[2:] if urlparse(arg).netloc}
    pages = load_pages(root)
    errors: list[str] = []

    for page, parser in pages.items():
        for attr, link in parser.links:
            parsed = urlparse(link)
            if should_skip(parsed):
                continue

            if parsed.netloc and parsed.netloc not in base_hosts:
                continue

            if not parsed.path and parsed.fragment:
                target = page
            else:
                target = target_path(root, page, parsed.path)

            if not target.exists():
                errors.append(f"{page.relative_to(root)}: missing {attr} target {link}")
                continue

            if parsed.fragment and target.suffix == ".html":
                target_parser = pages.get(target)
                if target_parser and parsed.fragment not in target_parser.ids:
                    errors.append(
                        f"{page.relative_to(root)}: missing fragment #{parsed.fragment} in {link}"
                    )

    if errors:
        print("Broken internal links found:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Checked {len(pages)} HTML files; no broken internal links found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
