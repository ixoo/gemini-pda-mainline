#!/usr/bin/env python3
"""Storage-inert tests for Candidate AO's exact installer derivation."""

from __future__ import annotations

import difflib
import importlib.util
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPOSITORY = SCRIPT_DIR.parents[2]
DERIVER_PATH = SCRIPT_DIR / "derive-installer.py"
TARGET = "gemini@192.168.1.50"
SYNTHETIC = {
    "raw_sha256": "a" * 64,
    "raw_size": "7388000",
    "manifest_sha256": "b" * 64,
    "padded_sha256": "c" * 64,
}
TARGET_CHECK = (
    f'[[ "$target" == {TARGET} ]] || \\\n'
    f"\tdie 'target must be exact {TARGET}'"
)


def load_deriver():
    sys.path.insert(0, os.fspath(SCRIPT_DIR))
    try:
        spec = importlib.util.spec_from_file_location(
            "candidate_ao_installer_derivation_test", DERIVER_PATH
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load Candidate AO installer deriver")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(os.fspath(SCRIPT_DIR))


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"foundation token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def independently_expected_derivation(source: str) -> str:
    """Apply the complete permitted AN-to-AO textual delta."""

    replacements = (
        (
            'expected_artifact_name="'
            "candidate-AN-mt6797-dvfsp-handoff-observer-b30bd183"
            '"',
            'expected_artifact_name="'
            "candidate-AO-mt6797-dvfsp-handoff-owner-aaaaaaaa"
            '"',
            1,
        ),
        (
            "gemini-mt6797-dvfsp-handoff-observer.boot.img",
            "gemini-mt6797-dvfsp-handoff-owner.boot.img",
            1,
        ),
        (
            "2026-07-24-mt6797-dvfsp-handoff-observer",
            "2026-07-24-mt6797-dvfsp-one-way-handoff",
            2,
        ),
        ("Candidate AN", "Candidate AO", 8),
        ("candidate-an", "candidate-ao", 14),
        ("AN_RAW", "AO_RAW", 16),
        ("AN_PADDED", "AO_PADDED", 11),
        ("AN_ARTIFACT", "AO_ARTIFACT", 4),
        (
            "EXPECTED_CURRENT_AL_PADDED_SHA256",
            "EXPECTED_CURRENT_AN_PADDED_SHA256",
            8,
        ),
        ("candidate_label=AN", "candidate_label=AO", 2),
        ("AL-installed-readback-verified", "AN-installed-readback-verified", 4),
    )
    result = source
    for old, new, count in replacements:
        result = replace_exact(result, old, new, count)

    pins = (
        (
            "readonly AO_RAW_SHA256="
            "b30bd1830ac8b6d01a6d030815969c89239a40a742f008338899925508987933",
            f"readonly AO_RAW_SHA256={SYNTHETIC['raw_sha256']}",
        ),
        (
            "readonly AO_RAW_SIZE=7387136",
            f"readonly AO_RAW_SIZE={SYNTHETIC['raw_size']}",
        ),
        (
            "readonly AO_PADDED_SHA256="
            "1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb",
            f"readonly AO_PADDED_SHA256={SYNTHETIC['padded_sha256']}",
        ),
        (
            "readonly AO_ARTIFACT_MANIFEST_SHA256="
            "5c4210cf657928c8d487fb720ac55ad80bb3b3bfe5afa98018582d2cd667a3e9",
            "readonly AO_ARTIFACT_MANIFEST_SHA256="
            f"{SYNTHETIC['manifest_sha256']}",
        ),
        (
            "readonly EXPECTED_CURRENT_AN_PADDED_SHA256="
            "5f022a8b4d6ed19a248d21b8cebdbfa2190e86675714eab49adfc57de9a7f794",
            "readonly EXPECTED_CURRENT_AN_PADDED_SHA256="
            "1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb",
        ),
    )
    for old, new in pins:
        result = replace_exact(result, old, new, 1)
    return result


class InstallerDerivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.deriver = load_deriver()
        cls.workspace = tempfile.TemporaryDirectory(
            prefix="candidate-ao-installer-test."
        )
        cls.work = pathlib.Path(cls.workspace.name)
        cls.foundation = cls.deriver.reconstruct_an(cls.work)
        cls.source = cls.foundation.read_text(encoding="utf-8", errors="strict")
        cls.calibration = cls.deriver.Calibration(**SYNTHETIC)
        cls.derived = cls.deriver.derive_text(cls.source, cls.calibration)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.workspace.cleanup()

    def test_exact_foundation_and_identity_pin_only_delta(self) -> None:
        self.assertEqual(
            self.deriver.ao.digest_path(self.foundation),
            self.deriver.AN_INSTALLER_SHA256,
        )
        self.assertEqual(stat.S_IMODE(self.foundation.stat().st_mode), 0o700)
        self.assertEqual(self.deriver.TARGET, TARGET)

        expected = independently_expected_derivation(self.source)
        if self.derived != expected:
            delta = "".join(
                difflib.unified_diff(
                    expected.splitlines(keepends=True),
                    self.derived.splitlines(keepends=True),
                    fromfile="permitted-transform",
                    tofile="actual-transform",
                )
            )
            self.fail(f"derived installer has a non-permitted delta:\n{delta}")

        self.assertEqual(self.derived.count(TARGET_CHECK), 1)
        self.assertIn(f"--target {TARGET}", self.derived)
        self.assertNotIn("--target USER@HOST", self.derived)
        self.assertNotIn("Candidate AN", self.derived)
        self.assertNotIn("candidate-an", self.derived)

    def test_mode_bash_syntax_and_hardware_write_boundary(self) -> None:
        output = self.work / "install-candidate-ao-boot2.sh"
        self.deriver.publish(output, self.derived)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
        syntax = subprocess.run(
            ["bash", "-n", os.fspath(output)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

        write = (
            'dd if="$root_stage_file" of="$target" '
            "bs=4M iflag=fullblock count=4"
        )
        self.assertEqual(self.derived.count(write), 1)
        self.assertEqual(self.derived.count('of="$target"'), 1)
        self.assertIn("conv=fsync,notrunc status=none", self.derived)
        self.assertIn("reboot_or_shutdown_performed=no", self.derived)
        self.assertIn("reboot=none", self.derived)
        self.assertIn("never reboots, and never\nselects boot2", self.derived)
        self.assertIn(
            "EXPECTED_CURRENT_AN_PADDED_SHA256="
            "1ef53a25c274ed6f0df265fbc4f4e3a64150d5b7fd4cd1e0cde1db53ffb18ccb",
            self.derived,
        )

        dangerous = re.compile(
            r"^\s*(?:(?:sudo|doas)\s+(?:-\S+\s+)*)?"
            r"(?:/[A-Za-z0-9_.-]+/)*(?:reboot|shutdown|poweroff|halt|"
            r"kexec|bootctl|fastboot|efibootmgr|fw_setenv|mtk)(?:\s|$)"
        )
        commands = [
            line
            for line in self.derived.splitlines()
            if dangerous.match(line) is not None
        ]
        self.assertEqual(commands, [])

    def test_placeholders_and_overwrite_fail_closed(self) -> None:
        placeholder = self.deriver.Calibration(
            "TO_PIN_RAW_SHA256",
            "TO_PIN_RAW_SIZE",
            "TO_PIN_ARTIFACT_MANIFEST_SHA256",
            "TO_PIN_PADDED_SHA256",
        )
        with self.assertRaisesRegex(ValueError, "unresolved or malformed"):
            self.deriver.derive_text(self.source, placeholder)

        if self.deriver.ao.artifact_pin_state() == "ready-to-pin":
            with self.assertRaisesRegex(ValueError, "unresolved or malformed"):
                self.deriver.production_calibration()
        else:
            production = self.deriver.production_calibration()
            self.assertEqual(production.raw_sha256, self.deriver.ao.RAW_SHA256)
            self.assertEqual(production.raw_size, self.deriver.ao.RAW_SIZE)
            self.assertEqual(
                production.manifest_sha256,
                self.deriver.ao.ARTIFACT_MANIFEST_SHA256,
            )
            self.assertEqual(
                production.padded_sha256,
                self.deriver.ao.PADDED_SHA256,
            )

        existing = self.work / "existing-installer.sh"
        existing.write_text("do-not-overwrite\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.deriver.validate_output(existing)
        with self.assertRaises(FileExistsError):
            self.deriver.publish(existing, self.derived)
        self.assertEqual(existing.read_text(encoding="utf-8"), "do-not-overwrite\n")

    def test_only_named_target_is_accepted_before_any_remote_action(self) -> None:
        output = self.work / "target-contract-installer.sh"
        self.deriver.publish(output, self.derived)
        fake_repository = self.work / "isolated-repository"
        (fake_repository / "artifacts/device-partitions").mkdir(parents=True)
        credentials = fake_repository / "artifacts/credentials"
        credentials.mkdir()
        identity = credentials / "gemini_ed25519"
        identity.write_text("synthetic-test-identity\n", encoding="utf-8")
        identity.chmod(0o600)
        common = [
            os.fspath(output),
            "--candidate",
            os.fspath(self.work / "deliberately-absent-candidate"),
            "--backup-dir",
            "artifacts/device-partitions/deliberately-unused-ao-test",
        ]
        environment = {
            **os.environ,
            "GEMINI_REPO_ROOT": os.fspath(fake_repository),
        }
        wrong = subprocess.run(
            [*common, "--target", "gemini@192.168.1.51"],
            cwd=REPOSITORY,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(wrong.returncode, 2)
        self.assertIn(f"target must be exact {TARGET}", wrong.stderr)

        exact = subprocess.run(
            [*common, "--target", TARGET],
            cwd=REPOSITORY,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(exact.returncode, 2)
        self.assertNotIn("target must be exact", exact.stderr)
        self.assertIn("candidate must be a regular non-symlink file", exact.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
