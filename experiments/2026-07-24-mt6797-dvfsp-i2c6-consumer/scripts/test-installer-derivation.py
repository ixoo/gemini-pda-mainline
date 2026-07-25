#!/usr/bin/env python3
"""Storage-inert tests for Candidate AP's exact installer derivation."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

SOURCE = pathlib.Path(__file__).with_name("derive-installer.py")
SPEC = importlib.util.spec_from_file_location(
    "candidate_ap_installer_derivation_test", SOURCE
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AP installer deriver")
DERIVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DERIVER
SPEC.loader.exec_module(DERIVER)

CALIBRATION = DERIVER.Calibration(
    raw_sha256="d" * 64,
    raw_size="8000000",
    manifest_sha256="e" * 64,
    padded_sha256="f" * 64,
)


class InstallerDerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="candidate-ap-installer-test-"
        )
        source_path = DERIVER.reconstruct_ao(pathlib.Path(cls.temporary.name))
        cls.source = source_path.read_text(encoding="utf-8", errors="strict")
        cls.derived = DERIVER.derive_text(cls.source, CALIBRATION)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_exact_ao_foundation_is_source_pinned(self) -> None:
        self.assertEqual(
            DERIVER.AO_INSTALLER_SHA256,
            "cbb6b8da36ec7f6a48726b9e5304667068719bd406e9df642376b98c0e6bd730",
        )
        self.assertEqual(
            DERIVER.ap.digest_path(
                pathlib.Path(
                    DERIVER.repository_root()
                    / "experiments/2026-07-24-mt6797-dvfsp-one-way-handoff/"
                    "scripts/derive-installer.py"
                )
            ),
            DERIVER.AO_DERIVER_SHA256,
        )

    def test_derived_identity_and_predecessor_are_exact(self) -> None:
        expected = (
            f"readonly EXPECTED_CURRENT_AO_PADDED_SHA256="
            f"{DERIVER.ap.AO_PADDED_SHA256}",
            f"readonly AP_RAW_SHA256={CALIBRATION.raw_sha256}",
            f"readonly AP_RAW_SIZE={CALIBRATION.raw_size}",
            f"readonly AP_PADDED_SHA256={CALIBRATION.padded_sha256}",
            f"readonly AP_ARTIFACT_MANIFEST_SHA256="
            f"{CALIBRATION.manifest_sha256}",
            f'expected_artifact_name="{DERIVER.artifact_directory(CALIBRATION)}"',
            f'[[ "$candidate_name" == {DERIVER.ap.BOOT_MEMBER} ]]',
        )
        for token in expected:
            with self.subTest(token=token):
                self.assertIn(token, self.derived)

    def test_only_boot2_guarded_write_and_no_reboot_remain(self) -> None:
        self.assertIn(
            'dd if="$root_stage_file" of="$target" bs=4M iflag=fullblock count=4',
            self.derived,
        )
        self.assertIn('$2 == "boot2"', self.derived)
        self.assertIn('[[ "$label" == boot2', self.derived)
        self.assertIn("reboot_or_shutdown_performed=no", self.derived)
        self.assertNotIn("boot3", self.derived)
        self.assertNotIn("preloader", self.derived)
        self.assertNotIn("NVRAM", self.derived)

    def test_exact_target_and_identity_are_not_overridable(self) -> None:
        self.assertEqual(self.derived.count(DERIVER.TARGET_CHECK), 1)
        self.assertIn(f"--target {DERIVER.TARGET}", self.derived)
        self.assertIn("IdentitiesOnly=yes", self.derived)
        self.assertIn("IdentityAgent=none", self.derived)
        self.assertIn("StrictHostKeyChecking=yes", self.derived)

    def test_derivation_is_exactly_reversible(self) -> None:
        restored = self.derived
        for old, new in reversed(DERIVER.pin_replacements(CALIBRATION)):
            restored = DERIVER.replace_exact(restored, new, old, 1)
        for old, new, count in reversed(
            DERIVER.identity_replacements(CALIBRATION)
        ):
            restored = DERIVER.replace_exact(restored, new, old, count)
        self.assertEqual(restored, self.source)

    def test_bad_calibration_and_mutated_source_fail_closed(self) -> None:
        bad_values = (
            DERIVER.Calibration("x", "8000000", "e" * 64, "f" * 64),
            DERIVER.Calibration("d" * 64, "0", "e" * 64, "f" * 64),
            DERIVER.Calibration(
                DERIVER.ap.AO_RAW_SHA256, "8000000", "e" * 64, "f" * 64
            ),
            DERIVER.Calibration(
                "d" * 64, "8000000", "e" * 64, DERIVER.ap.AO_PADDED_SHA256
            ),
        )
        for calibration in bad_values:
            with self.subTest(calibration=calibration):
                with self.assertRaises(ValueError):
                    DERIVER.validate_calibration(calibration)
        mutated = self.source.replace("Candidate AO", "Candidate A0", 1)
        with self.assertRaises(ValueError):
            DERIVER.derive_text(mutated, CALIBRATION)


if __name__ == "__main__":
    unittest.main(verbosity=2)
