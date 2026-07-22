from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.sync_friend_metadata import (
    FriendMetadata,
    MAX_RESPONSE_BYTES,
    extract_metadata,
    fetch_metadata,
    friend_key,
    sync_friends,
)


class MetadataExtractionTests(unittest.TestCase):
    def test_uses_metadata_priority_and_resolves_relative_icon(self) -> None:
        html = """
        <html><head>
          <title>Document title</title>
          <meta property="og:title" content="Open Graph title">
          <meta property="og:site_name" content="Site name">
          <meta name="description" content="Fallback description">
          <meta property="og:description" content="  Preferred   description  ">
          <meta property="og:image" content="/cover.jpg">
          <link rel="icon" href="/small.png" sizes="32x32">
          <link rel="apple-touch-icon" href="images/avatar.png" sizes="180x180">
        </head></html>
        """
        metadata = extract_metadata(html, "https://example.com/blog/")
        self.assertEqual(metadata.name, "Site name")
        self.assertEqual(metadata.description, "Preferred description")
        self.assertEqual(metadata.avatar, "https://example.com/blog/images/avatar.png")

    def test_uses_largest_icon_then_og_image(self) -> None:
        icons = """
        <link rel="icon" href="/small.png" sizes="16x16">
        <link rel="shortcut icon" href="/large.png" sizes="64x64">
        <meta property="og:image" content="/cover.jpg">
        """
        self.assertEqual(
            extract_metadata(icons, "https://example.com/").avatar,
            "https://example.com/large.png",
        )
        self.assertEqual(
            extract_metadata('<meta property="og:image" content="/cover.jpg">', "https://example.com/").avatar,
            "https://example.com/cover.jpg",
        )

    def test_rejects_empty_oversized_and_non_http_values(self) -> None:
        html = (
            '<meta property="og:title" content="' + "x" * 121 + '">'
            '<meta property="og:description" content="   ">'
            '<link rel="icon" href="data:image/png;base64,abc">'
        )
        metadata = extract_metadata(html, "https://example.com/")
        self.assertIsNone(metadata.name)
        self.assertIsNone(metadata.description)
        self.assertIsNone(metadata.avatar)


class FetchTests(unittest.TestCase):
    def make_response(self, payload: bytes, *, content_type: str = "text/html"):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.headers.get_content_type.return_value = content_type
        response.headers.get_content_charset.return_value = "utf-8"
        response.read.return_value = payload
        response.geturl.return_value = "https://redirected.example.com/home/"
        return response

    @mock.patch("scripts.sync_friend_metadata.urlopen")
    def test_fetch_uses_timeout_and_final_redirect_url(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = self.make_response(
            b'<meta property="og:title" content="Example">'
            b'<link rel="icon" href="avatar.png">'
        )
        metadata = fetch_metadata("https://example.com/", timeout=3.5)
        self.assertEqual(metadata.name, "Example")
        self.assertEqual(
            metadata.avatar,
            "https://redirected.example.com/home/avatar.png",
        )
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 3.5)

    @mock.patch("scripts.sync_friend_metadata.urlopen")
    def test_fetch_rejects_non_html_and_oversized_responses(self, mocked_urlopen) -> None:
        mocked_urlopen.return_value = self.make_response(b"{}", content_type="application/json")
        with self.assertRaisesRegex(ValueError, "unsupported content type"):
            fetch_metadata("https://example.com/")

        mocked_urlopen.return_value = self.make_response(b"x" * (MAX_RESPONSE_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "exceeds 1 MiB"):
            fetch_metadata("https://example.com/")


class SyncTests(unittest.TestCase):
    def write_data(self, directory: str, content: str) -> Path:
        path = Path(directory) / "friends.yaml"
        path.write_text(content, encoding="utf-8")
        return path

    def test_defaults_to_syncing_all_fields_without_changing_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_data(
                directory,
                """friends:
  "https://example.com/original":
    name: "Old name"
    avatar: "https://example.com/old.png"
    description: "Old description"
""",
            )

            result = sync_friends(
                path,
                fetcher=lambda _: FriendMetadata(
                    name="New name",
                    avatar="https://cdn.example.com/new.png",
                    description="New description",
                ),
            )

            updated = path.read_text(encoding="utf-8")
            self.assertTrue(result.changed)
            self.assertEqual(result.updated_fields, 3)
            self.assertIn('  "https://example.com/original":', updated)
            self.assertIn('name: "New name"', updated)
            self.assertIn('avatar: "https://cdn.example.com/new.png"', updated)
            self.assertIn('description: "New description"', updated)

    def test_field_flags_preserve_manual_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_data(
                directory,
                """friends:
  "https://example.com/":
    name: "Manual name"
    avatar: "https://example.com/manual.png"
    description: "Old description"
    sync_name: false
    sync_avatar: false
""",
            )

            result = sync_friends(
                path,
                fetcher=lambda _: FriendMetadata(
                    name="Remote name",
                    avatar="https://example.com/remote.png",
                    description="Remote description",
                ),
            )

            updated = path.read_text(encoding="utf-8")
            self.assertEqual(result.updated_fields, 1)
            self.assertIn('name: "Manual name"', updated)
            self.assertIn('avatar: "https://example.com/manual.png"', updated)
            self.assertIn('description: "Remote description"', updated)

    def test_missing_remote_fields_and_fetch_failures_keep_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            original = """friends:
  "https://example.com/":
    name: "Known name"
    description: "Known description"
"""
            path = self.write_data(directory, original)

            no_fields = sync_friends(path, fetcher=lambda _: FriendMetadata())
            self.assertFalse(no_fields.changed)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

            def failing_fetcher(_: str) -> FriendMetadata:
                raise TimeoutError("timed out")

            failed = sync_friends(path, fetcher=failing_fetcher)
            self.assertFalse(failed.changed)
            self.assertEqual(len(failed.warnings), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_no_change_is_idempotent_and_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            original = """friends:
  "https://example.com/":
    name: "Same"
    avatar: "https://example.com/avatar.png"
    description: "Same description"
"""
            path = self.write_data(directory, original)
            metadata = FriendMetadata(
                name="Same",
                avatar="https://example.com/avatar.png",
                description="Same description",
            )
            unchanged = sync_friends(path, fetcher=lambda _: metadata)
            self.assertFalse(unchanged.changed)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

            preview = sync_friends(
                path,
                fetcher=lambda _: FriendMetadata(name="Different"),
                dry_run=True,
            )
            self.assertTrue(preview.changed)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_invalid_switch_is_a_configuration_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_data(
                directory,
                """friends:
  "https://example.com/":
    name: "Example"
    sync_name: yes
""",
            )
            with self.assertRaisesRegex(ValueError, "sync_name must be true or false"):
                sync_friends(path, fetcher=lambda _: FriendMetadata())

    def test_url_is_normalized_as_unique_primary_key(self) -> None:
        self.assertEqual(
            friend_key("HTTPS://Example.COM:443"),
            "https://example.com/",
        )
        self.assertEqual(
            friend_key("https://example.com/path?view=full#section"),
            "https://example.com/path?view=full",
        )

    def test_duplicate_normalized_urls_are_rejected_before_fetching(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_data(
                directory,
                """friends:
  "https://example.com":
    name: "First"
  "https://EXAMPLE.com:443/":
    name: "Second"
""",
            )
            fetcher = mock.Mock(return_value=FriendMetadata())
            with self.assertRaisesRegex(ValueError, "duplicates"):
                sync_friends(path, fetcher=fetcher)
            fetcher.assert_not_called()


if __name__ == "__main__":
    unittest.main()
