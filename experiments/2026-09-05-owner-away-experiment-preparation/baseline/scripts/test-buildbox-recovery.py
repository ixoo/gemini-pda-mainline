#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Hardware/network-free transfer interruption and refusal fixtures."""
import hashlib
import io
import os
from pathlib import Path
import runpy
import tarfile
import sys
import tempfile
import unittest

M = runpy.run_path(str(Path(__file__).with_name('buildbox_userspace.py')))
REV = '1' * 40


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory(prefix='a53-transfer-', dir='/tmp')
        self.addCleanup(self.work.cleanup)
        self.root = Path(self.work.name)
        self.files = {'provenance.txt': ('repository_commit=' + REV + '\n').encode(), 'binary': b'fixture'}
        sums = ''.join(hashlib.sha256(value).hexdigest() + '  ./' + name + '\n'
                       for name, value in sorted(self.files.items())).encode()
        self.identity = hashlib.sha256(sums).hexdigest()
        self.files['SHA256SUMS'] = sums

    def archive(self, changes=None, extra=None):
        path = self.root / 'package.tar.gz'
        with tarfile.open(path, 'w:gz') as tar:
            for name, value in (changes or self.files).items():
                item = tarfile.TarInfo('./' + name)
                item.size = len(value)
                tar.addfile(item, io.BytesIO(value))
            if extra:
                tar.addfile(extra)
        return path

    def test_exact_fetch_and_reuse(self):
        target = self.root / 'output'
        M['extract'](self.archive(), target, self.identity, REV)
        M['check_package'](target, self.identity, REV)
        self.assertEqual((target / 'binary').read_bytes(), b'fixture')

    def test_interrupted_partial_cleared_without_log_loss(self):
        stage = self.root / '.fetch-userspace'
        stage.mkdir()
        (stage / 'package.tar.gz').write_bytes(b'partial')
        log = self.root / 'userspace-build.log'
        log.write_text('failed diagnostic')
        M['clear_partial'](stage)
        self.assertFalse(stage.exists())
        self.assertEqual(log.read_text(), 'failed diagnostic')

    def test_cleanup_refuses_symlink_or_unmanaged_name(self):
        for name in ('.fetch-userspace', 'valuable'):
            path = self.root / name
            path.symlink_to(self.root, target_is_directory=True)
            with self.assertRaises(ValueError):
                M['clear_partial'](path)
            self.assertTrue(path.is_symlink())

    def test_cleanup_refuses_nested_symlink(self):
        stage = self.root / '.fetch-userspace'
        stage.mkdir()
        (stage / 'linked').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            M['clear_partial'](stage)
        self.assertTrue(stage.exists())

    def test_wrong_revision_or_manifest(self):
        for identity, revision in (('0' * 64, REV), (self.identity, '2' * 40)):
            target = self.root / revision
            with self.assertRaises(ValueError):
                M['extract'](self.archive(), target, identity, revision)

    def test_corrupt_missing_extra_member(self):
        for index, changes in enumerate(({**self.files, 'binary': b'bad'},
                                        {k: v for k, v in self.files.items() if k != 'binary'},
                                        {**self.files, 'extra': b'bad'})):
            with self.assertRaises((ValueError, FileNotFoundError)):
                M['extract'](self.archive(changes), self.root / str(index), self.identity, REV)

    def test_archive_links_traversal_duplicate_refused(self):
        for index, name in enumerate(('../escape', '/absolute', './binary', './link')):
            extra = tarfile.TarInfo(name)
            if name.endswith('link'):
                extra.type = tarfile.SYMTYPE
                extra.linkname = 'binary'
            with self.assertRaises(ValueError):
                M['extract'](self.archive(extra=extra), self.root / str(index), self.identity, REV)

    def test_manifest_path_escape_refused(self):
        files = {'SHA256SUMS': (('0' * 64) + '  ./../escape\n').encode()}
        identity = hashlib.sha256(files['SHA256SUMS']).hexdigest()
        with self.assertRaises(ValueError):
            M['extract'](self.archive(files), self.root / 'output', identity, REV)

    def test_existing_package_corruption_detected(self):
        target = self.root / 'output'
        M['extract'](self.archive(), target, self.identity, REV)
        (target / 'binary').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            M['check_package'](target, self.identity, REV)

    def test_stream_byte_cap_and_exact_boundary(self):
        command = [sys.executable, '-c', 'import sys; sys.stdin.read(); sys.stdout.buffer.write(b"x" * 4096)']
        output = self.root / 'bounded'
        M['fetch_bounded'](command, b'fixture', output, limit=4096, timeout=3)
        self.assertEqual(output.stat().st_size, 4096)
        with self.assertRaisesRegex(ValueError, 'byte cap'):
            M['fetch_bounded'](command, b'fixture', self.root / 'oversized', limit=4095, timeout=3)
        self.assertLessEqual((self.root / 'oversized').stat().st_size, 4095)

    def test_stream_timeout_preserves_partial_and_reaps(self):
        command = [sys.executable, '-c', 'import sys,time; sys.stdin.read(); print("partial", flush=True); time.sleep(30)']
        output = self.root / 'timed'
        with self.assertRaisesRegex(ValueError, 'deadline'):
            M['fetch_bounded'](command, b'fixture', output, timeout=1.5)
        self.assertEqual(output.read_bytes(), b'partial\n')

    def test_signal_after_stdout_close_cannot_be_promoted(self):
        command = [sys.executable, '-c', 'import os,signal,sys,time; sys.stdin.read(); os.close(1); time.sleep(0.1); os.kill(os.getppid(),signal.SIGTERM); time.sleep(0.1)']
        with self.assertRaisesRegex(ValueError, 'interrupted'):
            M['fetch_bounded'](command, b'fixture', self.root / 'interrupted', timeout=3)

    def test_fetch_only_has_no_builder(self):
        self.assertNotIn('build-userspace.sh', M['REMOTE_FETCH'])
        self.assertIn('published/$revision', M['REMOTE_FETCH'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
