#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Host-only routing checks; mock every transport and use the real extractor."""
import hashlib
import io
import runpy
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
MODULE = runpy.run_path(str(HERE / '../baseline/scripts/buildbox_userspace.py'))
WORK = HERE.parents[2] / 'artifacts/a53-authenticated/development/keyboard-build-routing'


class RoutingTests(unittest.TestCase):
    def exercise(self, kind, fetch_only, branch=None):
        branch = branch or MODULE['BRANCH']
        WORK.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=WORK) as temporary:
            root = Path(temporary)
            revision = 'a' * 40
            provenance = ('repository_commit=' + revision + '\n').encode()
            sums = (hashlib.sha256(provenance).hexdigest() + '  ./provenance.txt\n').encode()
            identity = hashlib.sha256(sums).hexdigest()
            calls = []

            def git(*args):
                return {('remote', 'get-url', 'origin'): MODULE['ORIGIN'],
                        ('status', '--porcelain'): '',
                        ('branch', '--show-current'): branch,
                        ('rev-parse', 'HEAD'): revision,
                        ('rev-parse', revision + '^{commit}'): revision,
                        ('ls-remote', '--exit-code', 'origin', 'refs/heads/' + branch): revision}[args]

            def build(command, **kwargs):
                self.assertFalse(fetch_only)
                self.assertEqual(command[-3:], [revision, branch, kind])
                self.assertEqual(kwargs['input'], MODULE['REMOTE_BUILD'].encode())
                kwargs['stdout'].write(('validated_' + kind.replace('-', '_') +
                    '_package=/workspace/gemini-a53-userspace/' + kind + '-' + identity + '\n').encode())
                calls.append('build')
                return SimpleNamespace(returncode=0)

            def fetch(command, script, path):
                self.assertEqual(command[-3:], [revision, identity, kind])
                self.assertEqual(script, MODULE['REMOTE_FETCH'].encode())
                with tarfile.open(path, 'w:gz') as archive:
                    for name, raw in [('provenance.txt', provenance), ('SHA256SUMS', sums)]:
                        info = tarfile.TarInfo('./' + name)
                        info.size = len(raw)
                        archive.addfile(info, io.BytesIO(raw))
                calls.append('fetch')

            argv = ['buildbox_userspace.py', '--branch', branch]
            if kind == 'keyboard-monitor':
                argv.append('--keyboard-monitor')
            if fetch_only:
                argv += ['--fetch-only', revision, identity]
            globals_ = MODULE['main'].__globals__
            with patch.dict(globals_, {'REPO': root, 'git': git, 'fetch_bounded': fetch}), \
                    patch('sys.argv', argv), patch('subprocess.run', side_effect=build):
                MODULE['main']()
            self.assertEqual(calls, ['fetch'] if fetch_only else ['build', 'fetch'])
            self.assertTrue((root/'artifacts/buildbox'/revision/(kind + '-' + identity)/'SHA256SUMS').is_file())
            self.assertFalse((root/'artifacts/buildbox'/revision/('.fetch-' + kind)).exists())

    def test_legacy_and_monitor_build_paths(self):
        for kind in ('userspace', 'keyboard-monitor'):
            with self.subTest(kind=kind):
                self.exercise(kind, False)

    def test_unlisted_branch_refuses_before_transport(self):
        with patch('sys.argv', ['buildbox_userspace.py', '--branch', 'unreviewed']), \
                patch('subprocess.run') as transport, patch('sys.stderr', io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                MODULE['main']()
            self.assertEqual(error.exception.code, 2)
            transport.assert_not_called()

    def test_main_build_and_fetch(self):
        self.exercise('keyboard-monitor', False, 'main')
        self.exercise('keyboard-monitor', True, 'main')

    def test_fetch_only_never_builds_either_kind(self):
        for kind in ('userspace', 'keyboard-monitor'):
            with self.subTest(kind=kind):
                self.exercise(kind, True)


if __name__ == '__main__':
    unittest.main()
