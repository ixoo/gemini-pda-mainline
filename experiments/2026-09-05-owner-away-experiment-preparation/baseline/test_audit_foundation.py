#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Refusal fixtures for the foundation's exact package inventory boundary."""

from pathlib import Path
import tempfile
import unittest

from audit_foundation import digest, inventory, safe_directory


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gemini-foundation-", dir="/tmp")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.member = self.root / "member"
        self.member.write_bytes(b"pinned input\n")
        self.manifest = self.root / "SHA256SUMS"
        self.reset_manifest()

    def reset_manifest(self, text=None):
        if text is None:
            text = f"{digest(self.member.read_bytes())}  ./member\n"
        self.manifest.write_text(text)
        self.expected = {"manifest_sha256": digest(self.manifest.read_bytes()), "inventory_count": 1}

    def test_accept(self):
        self.assertEqual(inventory(self.root, self.expected), self.root)

    def test_mutated_member(self):
        self.member.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            inventory(self.root, self.expected)

    def test_unpinned_manifest(self):
        self.manifest.write_text(self.manifest.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "manifest digest"):
            inventory(self.root, self.expected)

    def test_unlisted_file(self):
        (self.root / "extra").write_bytes(b"unlisted")
        with self.assertRaisesRegex(ValueError, "unlisted"):
            inventory(self.root, self.expected)

    def test_missing_file(self):
        self.member.unlink()
        with self.assertRaises(OSError):
            inventory(self.root, self.expected)

    def test_malformed_paths(self):
        for path in ("../member", "/member", "a/../member", "a//member", "./member"):
            with self.subTest(path=path):
                self.reset_manifest(f"{digest(b'pinned input' + bytes([10]))}  ./{path}\n")
                with self.assertRaisesRegex(ValueError, "unsafe"):
                    inventory(self.root, self.expected)

    def test_duplicate(self):
        self.reset_manifest(self.manifest.read_text() * 2)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            inventory(self.root, self.expected)

    def test_symlink_member(self):
        self.member.unlink()
        self.member.symlink_to("SHA256SUMS")
        with self.assertRaisesRegex(ValueError, "nonregular"):
            inventory(self.root, self.expected)

    def test_symlink_directory(self):
        (self.root / "inside").mkdir()
        (self.root / "alias").symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            safe_directory(self.root / "alias")
        with self.assertRaisesRegex(ValueError, "symlink"):
            safe_directory(self.root / "alias" / "inside")
        with self.assertRaisesRegex(ValueError, "symlink"):
            inventory(self.root, self.expected)

    def test_count(self):
        self.expected["inventory_count"] = 2
        with self.assertRaisesRegex(ValueError, "count"):
            inventory(self.root, self.expected)


if __name__ == "__main__":
    unittest.main()
