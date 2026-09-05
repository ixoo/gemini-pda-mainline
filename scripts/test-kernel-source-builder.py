#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run actual builder preparation on tiny fixtures with fake download/toolchain.

No kernel source, compilation, network, device, or shared builder state is used.
The Linux identity is an explicit fixture; Linux package tests remain separate.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='kernel-builder-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for name in ('scripts', 'kernel', 'configs', 'patches', 'bin'):
            (self.root / name).mkdir()
        for name in ('kernel', 'validate-manifest-series', 'source-tree-integrity',
                     'kernel_source_contract.py', 'kernel-source-archive.py'):
            shutil.copy2(SCRIPTS / name, self.root / 'scripts' / name)
        (self.root / 'patches/series').write_text('test.patch\n')
        (self.root / 'patches/test.patch').write_text(
            'diff --git a/Makefile b/Makefile\n--- a/Makefile\n+++ b/Makefile\n'
            '@@ -1 +1 @@\n-old\n+new\n')
        (self.root / 'configs/test.fragment').write_text('CONFIG_TEST=y\n')
        self.source = dict(version='7.3-rc1', released='2026-09-05',
                           source_url='https://example.invalid/source.tar.gz',
                           sha256='0' * 64, archive_format='tar.gz', archive_root='linux-snapshot')
        self.manifest = {'schema': 1, 'architecture': 'arm64', 'kernel': dict(self.source),
                         'patch_series': 'patches/series',
                         'config': {'default_profile': 'full', 'profiles': {
                             'full': {'base': 'defconfig', 'fragments': ['configs/test.fragment']},
                             'topic': {'base': 'defconfig', 'fragments': ['configs/test.fragment'],
                                       'kernel': self.source}}}}
        if shutil.which('gsha256sum'):
            (self.root / 'bin/sha256sum').symlink_to(shutil.which('gsha256sum'))
        self.executable('uname', '#!/bin/sh\ncase "$1" in -s) echo Linux;; -m) echo x86_64;; *) exit 2;; esac\n')
        self.executable('fixture-gcc', '#!/bin/sh\necho aarch64-fixture\n')
        self.executable('fixture-ld', '#!/bin/sh\necho fixture-linker\n')
        self.executable('curl', '#!' + sys.executable + '\n' +
                        'import os, pathlib, shutil, signal, sys\n'
                        'args=sys.argv[1:]\n'
                        'target=pathlib.Path(args[args.index("--output")+1])\n'
                        'if os.environ.get("FIXTURE_DOWNLOAD_SIGNAL"):\n'
                        ' target.write_bytes(b"partial"); os.kill(os.getppid(), signal.SIGTERM); sys.exit(0)\n'
                        'if os.environ.get("FIXTURE_DOWNLOAD_FAIL"):\n'
                        ' target.write_bytes(b"partial"); sys.exit(28)\n'
                        'shutil.copyfile(os.environ["FIXTURE_ARCHIVE"],target)\n')
        self.env = dict(os.environ, PATH=str(self.root / 'bin') + os.pathsep + os.environ['PATH'],
                        KERNEL_PROFILE='topic', CROSS_COMPILE='fixture-', KERNEL_CCACHE='0',
                        GEMINI_SOURCE_ROOT=str(self.root / 'source'), GEMINI_BUILD_ROOT=str(self.root / 'build'),
                        GEMINI_CACHE_ROOT=str(self.root / 'cache'), GEMINI_ARTIFACT_ROOT=str(self.root / 'output'),
                        PYTHONDONTWRITEBYTECODE='1')

    def executable(self, name, text):
        path = self.root / 'bin' / name
        path.write_text(text)
        path.chmod(0o755)

    def prepare_archive(self, fmt='tar.gz', root='linux-snapshot'):
        path = self.root / 'input.tar'
        with tarfile.open(path, 'w:gz' if fmt == 'tar.gz' else 'w:xz') as output:
            entry = tarfile.TarInfo(root + '/Makefile')
            entry.size = 4
            output.addfile(entry, io.BytesIO(b'old\n'))
        self.source.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           archive_format=fmt, archive_root=root)
        self.env['FIXTURE_ARCHIVE'] = str(path)

    def run_builder(self, action='prepare', success=True):
        (self.root / 'kernel/manifest.json').write_text(json.dumps(self.manifest))
        result = subprocess.run(['bash', str(self.root / 'scripts/kernel'), action],
                                env=self.env, text=True, capture_output=True, timeout=40)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        self.assertFalse(list((self.root / 'source').glob('.prepare-*')))
        self.assertFalse(list((self.root / 'cache').glob('*.partial')))
        return result.stdout + result.stderr

    def test_prepare_patch_reuse_and_content_cache(self):
        for fmt in ('tar.gz', 'tar.xz'):
            self.prepare_archive(fmt)
            self.run_builder()
            prepared = self.root / 'source/linux-7.3-rc1'
            self.assertEqual((prepared / 'Makefile').read_text(), 'new\n')
            self.assertTrue((self.root / 'cache' / ('linux-' + self.source['sha256'] + '.' + fmt)).is_file())
            self.assertIn('already prepared', self.run_builder())
            # A changed declared root must not bypass archive checks by reusing a tree.
            self.source['archive_root'] = 'linux-wrong'
            self.assertIn('unexpected archive root', self.run_builder(success=False))
            self.assertEqual((prepared / 'Makefile').read_text(), 'new\n')

    def test_download_failure_and_stale_partial_cleanup(self):
        self.prepare_archive()
        self.env['FIXTURE_DOWNLOAD_FAIL'] = '1'
        self.run_builder(success=False)
        self.assertEqual(list((self.root / 'cache').iterdir()), [])
        del self.env['FIXTURE_DOWNLOAD_FAIL']
        self.env['FIXTURE_DOWNLOAD_SIGNAL'] = '1'
        self.run_builder(success=False)
        self.assertEqual(list((self.root / 'cache').iterdir()), [])
        del self.env['FIXTURE_DOWNLOAD_SIGNAL']
        stale = self.root / 'cache' / ('linux-' + self.source['sha256'] + '.tar.gz.partial')
        stale.write_text('interrupted')
        self.run_builder()

    def test_bad_digest_and_compression_refuse(self):
        self.prepare_archive()
        digest = self.source['sha256']
        self.source['sha256'] = 'c' * 64
        self.assertIn('checksum mismatch', self.run_builder(success=False))
        self.source['sha256'] = digest
        self.source['archive_format'] = 'tar.xz'
        self.run_builder(success=False)
        self.assertFalse((self.root / 'source/linux-7.3-rc1').exists())

    def test_legacy_paths(self):
        self.prepare_archive('tar.xz', 'linux-7.3-rc1')
        self.manifest['kernel'] = {k: v for k, v in self.source.items()
                                   if k not in ('archive_format', 'archive_root')}
        self.env['KERNEL_PROFILE'] = 'full'
        output = self.run_builder('paths')
        self.assertIn('source=' + str(self.root / 'source/linux-7.3-rc1'), output)
        self.assertIn('build=' + str(self.root / 'build/linux-7.3-rc1'), output)
        self.assertIn('archive=' + str(self.root / 'cache/linux-7.3-rc1.tar.xz'), output)
        self.run_builder()


if __name__ == '__main__':
    unittest.main()
