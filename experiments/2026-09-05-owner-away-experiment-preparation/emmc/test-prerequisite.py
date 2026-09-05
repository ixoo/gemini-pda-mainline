#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fixed selector/disable boundary; synthetic archive fixture reuse only."""
from pathlib import Path
import importlib.util
import sys
import unittest
from unittest.mock import patch
import prerequisite as P

sys.path.insert(0, str(P.BASE))
spec = importlib.util.spec_from_file_location('emmc_supplemental_fixture', P.BASE / 'test-supplemental-recovery.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


class PrerequisiteTests(T.SupplementalTests):
    # Reuse archive construction, not the parent's test inventory.
    test_supplement_distinct_while_original_refuses = None
    test_exact_request_mutations_refuse_even_with_refreshed_manifests = None
    test_missing_owner_failed_confirmation_and_incomplete_priors_refuse = None
    test_source_and_binding_changes_refuse = None

    def test_explicit_supplemental_and_no_strict_fallback(self):
        result = P.verify_prerequisite(self.root, 'reviewed-supplemental', self.bindings)
        self.assertTrue(result['preparation_only'])
        self.assertFalse(result['execution_enabled'])
        strict = {k: v for k, v in self.bindings.items() if k != 'phase_manifests'}
        with self.assertRaises(ValueError):
            P.verify_prerequisite(self.root, 'original-strict', strict)
        with self.assertRaises(ValueError):
            P.verify_prerequisite(self.root, 'auto', self.bindings)
        strict_root = self.root.parent / 'strict-evidence'
        strict_bindings, _, _ = T.T.make_archive(strict_root)
        strict_result = P.verify_prerequisite(strict_root, 'original-strict', strict_bindings)
        self.assertEqual(strict_result['prerequisite_selector'], 'original-strict')
        self.assertFalse(strict_result['execution_enabled'])

    def test_pins_and_missing_evidence_refuse(self):
        with patch.object(P, 'SELECTORS', {'reviewed-supplemental':
                ('supplemental_recovery.py', '0' * 64, 'unused')}):
            with self.assertRaises(ValueError):
                P.verify_prerequisite(self.root, 'reviewed-supplemental', self.bindings)
        (self.sessions / 'preserve-log/result.json').unlink()
        with self.assertRaises((ValueError, OSError)):
            P.verify_prerequisite(self.root, 'reviewed-supplemental', self.bindings)

    def test_execution_unconditionally_refuses_before_io(self):
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unexpected IO')):
            for arguments in ((), (self.root, 'reviewed-supplemental', self.bindings)):
                with self.assertRaisesRegex(ValueError, 'execution disabled'):
                    P.execute(*arguments, execute=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
