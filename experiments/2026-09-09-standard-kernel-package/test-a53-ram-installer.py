#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Exercise the installer adapter using the existing inert host transport."""
import hashlib
from pathlib import Path
import runpy
import shlex
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
A = runpy.run_path(str(HERE / 'a53-ram-installer.py'))
sys.path.insert(0, str(A['BASELINE']))
OLD = runpy.run_path(str(A['BASELINE'] / 'test-installer.py'))
BASE = OLD['InstallerTests']
BOOT = OLD['BOOT']


class ServiceInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BASE.setUpClass.__func__(cls)
        cls.original = cls.source
        cls.adapter = cls.repo / (HERE / 'a53-ram-installer.py').relative_to(A['REPO'])
        cls.adapter.parent.mkdir(parents=True)
        # Validation is injected for the synthetic zero-filled image. Receipt
        # parsing uses the real adapter. Every SSH request remains inert.
        cls.adapter.write_text('import runpy,sys\nrunpy.run_path(' +
                               repr(str(cls.tools / 'validate-candidate.py')) +
                               ' if sys.argv[1] == "validate" else ' +
                               repr(str(HERE / 'a53-ram-installer.py')) + ', run_name="__main__")\n')
        result_dir = cls.adapter.parent / 'results'
        result_dir.mkdir()
        (result_dir / 'a53-service-ram-candidate.json').write_bytes(
            (HERE / 'results/a53-service-ram-candidate.json').read_bytes())
        cls.source = A['adapt'](cls.original, cls.repo, cls.candidate, BOOT)
        cls.script.write_text(cls.source)
        cls.evidence = cls.evidence_root / A['RECEIPT_NAME']
        subprocess.run(['bash', '-n', str(cls.script)], check=True)
        subprocess.run(['shellcheck', str(cls.script)], check=True)

    @classmethod
    def tearDownClass(cls):
        BASE.tearDownClass.__func__(cls)

    def run_case(self, case, evidence_name=None):
        return BASE.run_case(self, case, evidence_name=evidence_name or A['RECEIPT_NAME'])

    def parse(self, raw, previous=BOOT):
        return A['receipt'](raw, self.sha, self.manifest_sha, previous)

    def test_success_and_matching_image_skip(self):
        for case in ('pass', 'already-current', 'poweroff-disconnect'):
            with self.subTest(case=case):
                result, actions = self.run_case(case)
                self.assertEqual(result.returncode, 0, result.stderr)
                count = 0 if case == 'already-current' else 1
                self.assertEqual(actions.count('write-attempt'), count)
                self.assertEqual(actions.count('upload'), count)
                self.assertLess(actions.index('readback'), actions.index('poweroff'))
                self.assertFalse((self.root / 'stage').exists())
                self.assertEqual(self.parse((self.evidence / 'deployment-summary.txt').read_text()), BOOT)

    def test_failures_and_interruptions(self):
        cases = ('validator-refused', 'existing-evidence', 'symlink-evidence', 'ssh-refused', 'bad-boot',
                 'probe-refused', 'duplicate-probe', 'stage-refused', 'upload-refused',
                 'upload-term', 'upload-int', 'upload-hup', 'write-refused', 'write-signal',
                 'cleanup-refused', 'post-refused', 'readback-short', 'readback-corrupt',
                 'readback-signal', 'poweroff-refused', 'still-reachable')
        for case in cases:
            with self.subTest(case=case):
                result, actions = self.run_case(case)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertLessEqual(actions.count('write-attempt'), 1)
                if case not in ('poweroff-refused', 'still-reachable'):
                    self.assertNotIn('poweroff', actions)
                if case in ('validator-refused', 'existing-evidence', 'symlink-evidence'):
                    self.assertNotIn('preflight', actions)
                if case != 'cleanup-refused':
                    self.assertFalse((self.root / 'stage').exists())
                self.assertFalse((self.evidence / '.boot2-readback.partial').exists())
                summary = self.evidence / 'deployment-summary.txt'
                if summary.is_file():
                    with self.assertRaises(ValueError):
                        self.parse(summary.read_text())

    def test_boot_and_receipt_namespace_refuse_before_gate(self):
        for case in ('changed-boot', 'old-receipt-name'):
            with self.subTest(case=case):
                source = self.source.replace('"$initial_boot_id" == ' + BOOT,
                    '"$initial_boot_id" == 22222222-2222-4222-8222-222222222222') if case == 'changed-boot' else self.source
                self.script.write_text(source)
                try:
                    result, actions = self.run_case(case, OLD['RECEIPT_NAME'] if case == 'old-receipt-name' else None)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn('gate-probe', actions)
                    self.assertNotIn('stage-prepare', actions)
                finally:
                    self.script.write_text(self.source)

    def test_new_local_inputs_refuse_before_transport(self):
        for path in (self.adapter, self.adapter.parent / 'results/a53-service-ram-candidate.json'):
            saved = path.read_bytes()
            try:
                path.write_bytes(saved + b'\n')
                result, actions = self.run_case('changed-local-input')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(actions, [])
            finally:
                path.write_bytes(saved)

    def test_receipt_binding(self):
        result, _ = self.run_case('pass')
        self.assertEqual(result.returncode, 0, result.stderr)
        raw = (self.evidence / 'deployment-summary.txt').read_text()
        for key in ('experiment', 'candidate_manifest_sha256', 'boot_id'):
            entry = next(line for line in raw.splitlines() if line.startswith(key + '='))
            for changed in (raw.replace(entry + '\n', ''), raw + entry + '\n', raw.replace(entry, key + '=wrong')):
                with self.subTest(key=key):
                    with self.assertRaises(ValueError):
                        self.parse(changed)
        for previous in ('00000000-0000-0000-0000-000000000000', '22222222-2222-4222-8222-222222222222'):
            with self.assertRaises(ValueError):
                self.parse(raw, previous)
        with self.assertRaises(ValueError):
            self.parse(raw.replace('experiment=' + A['EXPERIMENT'], 'experiment=a53-authenticated-baseline'))

    def test_inverse_delta_preserves_entire_original(self):
        source = self.source
        def restore(new, old):
            nonlocal source
            self.assertIn(new, source)
            source = source.replace(new, old)
        validator = self.tools / 'validate-candidate.py'
        restore(shlex.join(['python3', str(self.adapter), 'validate', '--previous-gemian-boot', BOOT]),
                shlex.join(['python3', str(validator), '--foundation', str(self.candidate), '--userspace', str(self.candidate)]))
        def check(path):
            return ('[[ "$(sha256sum ' + shlex.quote(str(path)) + " | awk '{print $1}')\" == " +
                    hashlib.sha256(path.read_bytes()).hexdigest() + " ]] || die 'validation tool changed'\n")
        restore(check(self.adapter) + check(self.adapter.parent / 'results/a53-service-ram-candidate.json'), check(validator))
        restore(shlex.join(['python3', str(self.adapter), 'receipt', '--previous-gemian-boot', BOOT, '--candidate-sha256']),
                shlex.join(['python3', str(self.tools / 'deployment_receipt.py'), '--candidate-sha256']))
        restore(A['RECEIPT_NAME'], OLD['RECEIPT_NAME'])
        restore("printf 'experiment=" + A['EXPERIMENT'] + "\\n", "printf 'experiment=a53-authenticated-baseline\\n")
        restore('[[ "$initial_boot_id" == ' + BOOT + " ]] || die 'preceding Gemian boot changed'\n", '')
        self.assertEqual(source, self.original)
        self.assertEqual(source.count('of="$target"'), 1)

    def test_cli_has_no_execute_mode(self):
        for extra in ([], ['--execute'], ['prepare', '--execute']):
            result = subprocess.run([sys.executable, '-B', str(HERE / 'a53-ram-installer.py'), *extra],
                                    capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main(defaultTest='ServiceInstallerTests', verbosity=2)
