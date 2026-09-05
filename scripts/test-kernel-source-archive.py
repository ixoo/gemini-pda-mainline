#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise real tiny compressed archives; never extract kernel sources."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('source_archive', Path(__file__).with_name('kernel-source-archive.py'))
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


def file(name, data=b'fixture', kind=tarfile.REGTYPE, target=''):
    entry = tarfile.TarInfo(name)
    entry.type = kind
    entry.linkname = target
    entry.mode = 0o755
    entry.size = len(data) if kind == tarfile.REGTYPE else 0
    return entry, data


class ArchiveTests(unittest.TestCase):
    def attempt(self, entries, fmt='tar.gz', digest=None, declared=None, root='linux-test', fails=False):
        with tempfile.TemporaryDirectory(prefix='source-archive-fixture-') as directory:
            base = Path(directory)
            source = base / fmt
            with tarfile.open(source, 'w:gz' if fmt == 'tar.gz' else 'w:xz') as output:
                for entry, data in entries:
                    output.addfile(entry, io.BytesIO(data) if entry.isfile() else None)
            actual = hashlib.sha256(source.read_bytes()).hexdigest()
            destination = base / 'destination'
            destination.mkdir()
            if fails:
                with self.assertRaises((ValueError, tarfile.TarError)):
                    archive.unpack(source, destination, digest or actual, declared or fmt, root)
                self.assertEqual(list(destination.iterdir()), [])
            else:
                archive.unpack(source, destination, digest or actual, declared or fmt, root)
                self.assertEqual((destination / root / 'Makefile').read_bytes(), b'fixture')
                self.assertEqual((destination / root / 'Makefile').stat().st_mode & 0o777, 0o755)
                if (destination / root / 'link').is_symlink():
                    self.assertEqual((destination / root / 'link').read_bytes(), b'fixture')

    def test_both_formats_and_safe_links(self):
        for fmt in ('tar.gz', 'tar.xz'):
            self.attempt([file('linux-test/Makefile'),
                          file('linux-test/link', kind=tarfile.SYMTYPE, target='Makefile'),
                          file('linux-test/hard', kind=tarfile.LNKTYPE, target='linux-test/Makefile')], fmt)

    def test_digest_compression_and_root(self):
        entries = [file('linux-test/Makefile')]
        self.attempt(entries, digest='0' * 64, fails=True)
        self.attempt(entries, declared='tar.xz', fails=True)
        self.attempt(entries, root='linux-wrong', fails=True)

    def test_unsafe_names_and_types(self):
        for name in ('/linux-test/file', 'linux-test/../file', 'other/file',
                     'linux-test//file', 'linux-test/./file', 'linux-test/a\\b'):
            self.attempt([file(name)], fails=True)
        for kind in (tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE):
            self.attempt([file('linux-test/special', kind=kind)], fails=True)

    def test_duplicates_and_children_of_links(self):
        self.attempt([file('linux-test/Makefile')] * 2, fails=True)
        self.attempt([file('linux-test/a', kind=tarfile.SYMTYPE, target='b'),
                      file('linux-test/a/file')], fails=True)

    def test_escaping_and_chained_links(self):
        for target in ('../../escape', '/tmp/escape'):
            self.attempt([file('linux-test/link', kind=tarfile.SYMTYPE, target=target)], fails=True)
        self.attempt([file('linux-test/a', kind=tarfile.SYMTYPE, target='b'),
                      file('linux-test/b', kind=tarfile.SYMTYPE, target='a')], fails=True)
        self.attempt([file('linux-test/a', kind=tarfile.LNKTYPE, target='linux-test/missing')], fails=True)

    def test_symlink_traversal_cannot_be_hidden_by_parent_component(self):
        # Filesystem resolution follows sub -> '.' before processing '..',
        # escaping the root despite a lexically contained final target.
        for entries in (
            [file('linux-test/sub', kind=tarfile.SYMTYPE, target='.'),
             file('linux-test/escape', kind=tarfile.SYMTYPE, target='sub/../outside')],
            [file('linux-test/escape', kind=tarfile.SYMTYPE, target='sub/../outside'),
             file('linux-test/sub', kind=tarfile.SYMTYPE, target='.')],
            [file('linux-test/sub', kind=tarfile.SYMTYPE, target='.'),
             file('linux-test/escape', kind=tarfile.LNKTYPE,
                  target='linux-test/sub/../Makefile'),
             file('linux-test/Makefile')],
        ):
            self.attempt(entries, fails=True)

    def test_refuse_destination_residue(self):
        with tempfile.TemporaryDirectory(prefix='source-destination-fixture-') as directory:
            root = Path(directory)
            (root / 'keep').write_text('keep')
            with self.assertRaises(ValueError):
                archive.unpack(root / 'missing', root, '0' * 64, 'tar.gz', 'linux-test')
            self.assertEqual((root / 'keep').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
