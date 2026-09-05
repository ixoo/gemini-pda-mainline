#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic archives and original immutable closure; no device operations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import supplemental_recovery as S

A = S.original_verifier()
T = A.module('supplemental_fixture', Path(__file__).with_name('test-verified-baseline.py'))


class SupplementalTests(unittest.TestCase):
    def setUp(self):
        work = A.REPO / 'artifacts/a53-authenticated/development/supplemental-tests'
        work.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=work)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'evidence'
        self.bindings, self.context, self.sessions = T.make_archive(self.root)
        request = self.sessions / 'request-recovery'
        raw = (request / 'native-reboot/stdout.txt').read_bytes() + S.ANNOUNCEMENT
        T.write(request / 'native-reboot/stdout.txt', raw)
        T.write(request / 'native-reboot/stderr.txt', b'')
        proc = json.loads((request / 'native-reboot/process.json').read_text())
        proc.update(reason='outer-timeout', elapsed_seconds=14.011, stdout_bytes=len(raw), stderr_bytes=0)
        T.save(request / 'native-reboot/process.json', proc)
        T.save(request / 'result.json', S.FAILED)
        self.resign()

    def resign(self):
        pins = {action: T.refresh(self.sessions / action) for action in T.F.PRIOR_FIELDS}
        final = self.sessions / 'confirm-recovery'
        admission = json.loads((final / 'admission.json').read_text())
        for action, field in T.F.PRIOR_FIELDS.items():
            admission[field] = pins[action]
        T.save(final / 'admission.json', admission)
        context = {**self.context, 'admission': admission, 'admission_raw': T.F.json_bytes(admission)}
        T.save(final / 'claim.json', T.F.phase_claim(context))
        result = json.loads((final / 'result.json').read_text())
        for action in pins:
            result['prior_proof'][action]['manifest_sha256'] = pins[action]
        result['prior_proof']['request-recovery'] = {'classification': 'incomplete',
            'manifest_sha256': pins['request-recovery'], 'reason': S.FAILED['reason']}
        result['baseline_classification'] = 'recovered-with-baseline-incomplete'
        T.save(final / 'result.json', result)
        self.bindings.update(phase_manifests=pins, confirmation_manifest_sha256=T.refresh(final))

    def test_supplement_distinct_while_original_refuses(self):
        result = S.verify(self.root, self.bindings)
        self.assertEqual(result['classification'], 'supplemental-authenticated-baseline-recovery-verified')
        self.assertFalse(result['dependent_admission'])
        with self.assertRaises(ValueError):
            A.verify(self.root, {k: v for k, v in self.bindings.items() if k != 'phase_manifests'})

    def test_exact_request_mutations_refuse_even_with_refreshed_manifests(self):
        directory = self.sessions / 'request-recovery' / 'native-reboot'
        out = (directory / 'stdout.txt').read_bytes()
        proc = json.loads((directory / 'process.json').read_text())
        cases = [(out[:-1], {}), (out + b'extra\n', {}),
                 (out.replace(b'Candidate AB', b'Candidate XX'), {}),
                 (out.replace(self.context['baseline']['boot_id'].encode(), T.NEW.encode()), {}),
                 (out, {'reason': 'interrupted'}), (out, {'reason': None}),
                 (out, {'elapsed_seconds': 1}), (out, {'exit_status': -15}),
                 (out, {'stdin_complete': False})]
        for raw, changes in cases:
            with self.subTest(changes=changes, raw=raw[-30:]):
                T.write(directory / 'stdout.txt', raw)
                T.save(directory / 'process.json', {**proc, 'stdout_bytes': len(raw), **changes})
                self.resign()
                with self.assertRaises(ValueError): S.verify(self.root, self.bindings)
        T.write(directory / 'stdout.txt', out)
        T.save(directory / 'process.json', proc)

    def test_missing_owner_failed_confirmation_and_incomplete_priors_refuse(self):
        mutations = [('confirm-recovery/admission.json', 'physical_recovery_confirmed', False),
                     ('confirm-recovery/admission.json', 'owner_console_accepted', False),
                     ('confirm-recovery/known-good-probe/process.json', 'exit_status', 1),
                     ('auth-checks/positive-probe/process.json', 'reason', 'outer-timeout'),
                     ('preserve-log/result.json', 'classification', 'inconclusive'),
                     ('request-recovery/admission.json', 'steps_source_sha256', '0' * 64)]
        for name, key, value in mutations:
            with self.subTest(name=name, key=key):
                path = self.sessions / name
                original = path.read_bytes()
                data = json.loads(original); data[key] = value; T.save(path, data)
                self.resign()
                with self.assertRaises(ValueError): S.verify(self.root, self.bindings)
                T.write(path, original); self.resign()

    def test_source_and_binding_changes_refuse(self):
        with patch.object(S, 'AGGREGATE_SHA', '0' * 64):
            with self.assertRaises(ValueError): S.verify(self.root, self.bindings)
        altered = copy.deepcopy(self.bindings)
        altered['phase_manifests']['request-recovery'] = '0' * 64
        with self.assertRaises(ValueError): S.verify(self.root, altered)
        with patch.object(A, 'SOURCE_PINS', {**A.SOURCE_PINS,
                A.BASELINE + 'session_steps.py': '0' * 64}):
            with patch.object(S, 'original_verifier', return_value=A):
                with self.assertRaises(ValueError): S.verify(self.root, self.bindings)


if __name__ == '__main__':
    unittest.main(verbosity=2)
