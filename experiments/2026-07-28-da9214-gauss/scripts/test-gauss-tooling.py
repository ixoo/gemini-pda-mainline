#!/usr/bin/env python3
"""Static contracts for Gauss assembly, runner, verifier, and installer."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
import io
from unittest import mock

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPOSITORY = SCRIPT_DIR.parents[2]
sys.path.insert(0, str(SCRIPT_DIR))


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def derived_assembler():
    dc = load("gauss_candidate_deriver_test", "derive-candidate.py")
    fermi = dc.load_fermi_deriver(REPOSITORY)
    quasar = fermi.load_quasar_deriver(REPOSITORY)
    source = (REPOSITORY / quasar.VEGA_BUILDER).read_text(encoding="utf-8")
    return dc, dc.derive_text(fermi.derive_text(quasar.derive_text(source)))


class GaussToolingContract(unittest.TestCase):
    def test_scripts_are_private_executables(self) -> None:
        names = (
            "audit-gauss-binary.py",
            "build-candidate-gauss.sh",
            "derive-candidate.py",
            "derive-installer.py",
            "run-gauss-one-shot.py",
            "test-gauss-contract.py",
            "test-gauss-package.py",
            "test-gauss-result.py",
            "test-gauss-tooling.py",
            "validate-gauss-result.py",
            "validate-package-gauss.py",
            "verify-gauss-reproducibility.py",
        )
        for name in names:
            with self.subTest(name=name):
                mode = stat.S_IMODE((SCRIPT_DIR / name).stat().st_mode)
                self.assertEqual(mode, 0o755)

    def test_assembler_retains_exact_fermi_lk_identity(self) -> None:
        _module, text = derived_assembler()
        self.assertIn("--name gemini-fermi", text)
        self.assertIn("--expected-name gemini-fermi", text)
        self.assertIn("boot_cmdline=bootopt=64S3,32N2,64N2", text)
        self.assertIn("candidate=Gauss", text)
        self.assertIn("validate-package-gauss.py", text)
        self.assertIn("--fermi-object", text)
        self.assertIn("--gauss-vmlinux", text)
        self.assertNotIn("--name gemini-gauss", text)
        self.assertNotIn("candidate=Fermi\n", text)
        syntax = subprocess.run(
            ["bash", "-n"],
            input=text.encode(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(syntax.returncode, 0, syntax.stderr.decode())

    def test_runner_uses_gauss_result_over_fermi_endpoint(self) -> None:
        runner = load("gauss_runner_tooling_test", "run-gauss-one-shot.py")
        source = runner.load_source()
        self.assertIn("import candidate_gauss as co", source)
        self.assertIn("validate-gauss-result.py", source)
        self.assertIn("fermi-run-native", source)
        self.assertIn('KERNEL_RELEASE = "7.1.3-gemini-fermi"', source)
        self.assertIn("GEMINI_FERMI_20260728", source)
        self.assertIn("validation=gauss-runtime-one-shot", source)
        self.assertNotIn("gauss-run-native", source)
        runner.static_runtime_contract(runner.load_result_validator())

    def test_verifier_retains_fermi_header_and_requires_binary_audit(self) -> None:
        verifier = load(
            "gauss_reproducibility_tooling_test",
            "verify-gauss-reproducibility.py",
        )
        self.assertEqual(verifier.LK_EXPECTED_NAME, "gemini-fermi")
        self.assertEqual(
            verifier.LK_EXPECTED_CMDLINE,
            "bootopt=64S3,32N2,64N2",
        )
        source = (SCRIPT_DIR / "verify-gauss-reproducibility.py").read_text()
        for token in (
            "--fermi-object",
            "--gauss-object-a",
            "--gauss-object-b",
            "--fermi-vmlinux",
            "--gauss-vmlinux-a",
            "--gauss-vmlinux-b",
            "binary_delta=exact-five-source-deltas-plus-gnu-build-id",
        ):
            self.assertIn(token, source)

    def test_verifier_main_validates_and_writes_output(self) -> None:
        verifier = load(
            "gauss_reproducibility_main_test",
            "verify-gauss-reproducibility.py",
        )
        with tempfile.TemporaryDirectory(prefix="gauss-verifier-main.") as raw:
            root = pathlib.Path(raw)
            repository = root / "repository"
            repository.mkdir()
            directories = {
                name: root / name
                for name in (
                    "fermi-package",
                    "package-a",
                    "package-b",
                    "candidate-a-a",
                    "candidate-a-b",
                    "candidate-b-a",
                    "candidate-b-b",
                )
            }
            for directory in directories.values():
                directory.mkdir()
            files = {
                name: root / name
                for name in (
                    "fermi-object",
                    "fermi-vmlinux",
                    "gauss-object-a",
                    "gauss-object-b",
                    "gauss-vmlinux-a",
                    "gauss-vmlinux-b",
                )
            }
            for path in files.values():
                path.write_bytes(b"synthetic nonempty input\n")
            output = root / "build-reproducibility.txt"
            argv = [
                "verify-gauss-reproducibility.py",
                "--repository",
                str(repository),
                "--fermi-package",
                str(directories["fermi-package"]),
                "--fermi-object",
                str(files["fermi-object"]),
                "--fermi-vmlinux",
                str(files["fermi-vmlinux"]),
                "--package-a",
                str(directories["package-a"]),
                "--package-b",
                str(directories["package-b"]),
                "--gauss-object-a",
                str(files["gauss-object-a"]),
                "--gauss-object-b",
                str(files["gauss-object-b"]),
                "--gauss-vmlinux-a",
                str(files["gauss-vmlinux-a"]),
                "--gauss-vmlinux-b",
                str(files["gauss-vmlinux-b"]),
                "--candidate-a-a",
                str(directories["candidate-a-a"]),
                "--candidate-a-b",
                str(directories["candidate-a-b"]),
                "--candidate-b-a",
                str(directories["candidate-b-a"]),
                "--candidate-b-b",
                str(directories["candidate-b-b"]),
                "--output",
                str(output),
            ]
            record = b"validation=synthetic-gauss-main-test\n"
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(verifier, "verify", return_value=record),
                redirect_stdout(io.StringIO()) as stdout,
            ):
                self.assertEqual(verifier.main(), 0)
            self.assertEqual(output.read_bytes(), record)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertIn(
                f"record_sha256={hashlib.sha256(record).hexdigest()}",
                stdout.getvalue(),
            )
            with self.assertRaises(verifier.ContractError):
                verifier.validate_output(output)

    def test_installer_is_fermi_derived_curie_guarded_boot2_only(self) -> None:
        installer = load("gauss_installer_tooling_test", "derive-installer.py")
        fermi = installer.load_fermi_installer(REPOSITORY)
        fields = fermi.parse_record(REPOSITORY)
        fermi_pins = fermi.ArtifactPins(
            fields["candidate_directory_name"],
            fields["candidate_raw_sha256"],
            int(fields["candidate_raw_size"], 10),
            fields["candidate_padded_sha256"],
            fields["candidate_manifest_sha256"],
        )
        quasar = fermi.load_quasar_deriver(REPOSITORY)
        with tempfile.TemporaryDirectory(prefix="gauss-installer-test.") as raw:
            source = quasar.reconstruct_vega(pathlib.Path(raw))
        quasar_text = quasar.derive_text(source, quasar.io.production_pins())
        fermi_text = fermi.derive_text(quasar_text, fermi_pins, quasar)
        gauss_pins = installer.ArtifactPins(
            "candidate-Gauss-da9214-deadbeef",
            "1" * 64,
            7_750_000,
            "2" * 64,
            "3" * 64,
        )
        text = installer.derive_text(fermi_text, gauss_pins, fermi_pins)
        self.assertIn(
            "EXPECTED_CURRENT_CURIE_PADDED_SHA256="
            "824c3391f55cc932d146ef2e573642a51fb5c077932c7b6d17316fd34020d52d",
            text,
        )
        self.assertIn("Curie-installed-readback-verified", text)
        self.assertIn('$2 == "boot2"', text)
        self.assertIn('[[ "$label" == boot2', text)
        self.assertIn("reboot_or_shutdown_performed=no", text)
        self.assertNotIn("derive-installer-curie", text)
        for forbidden in ("reboot ", "shutdown ", "poweroff ", "of=/dev/mmc"):
            self.assertNotIn(forbidden, text)

    def test_source_pins_match(self) -> None:
        files = {
            "../fermi/scripts/derive-candidate.py": (
                REPOSITORY
                / "experiments/2026-07-28-da9214-fermi/scripts/derive-candidate.py",
                "82577a304377b86bd6b687504185e6c2c2ec371038a3545138468d380e052eee",
            ),
            "../fermi/scripts/run-fermi-one-shot.py": (
                REPOSITORY
                / "experiments/2026-07-28-da9214-fermi/scripts/run-fermi-one-shot.py",
                "e391f02ff5cc99296e1508e4a7b5bc4211c025a1e65f7f7a85adc6caa6fe7e11",
            ),
            "../fermi/scripts/derive-installer.py": (
                REPOSITORY
                / "experiments/2026-07-28-da9214-fermi/scripts/derive-installer.py",
                "aed6e8b17efe5cd5ea029977a0d17e83986e98ef091c7411b1569fb34470762b",
            ),
        }
        for label, (path, wanted) in files.items():
            with self.subTest(label=label):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), wanted)


if __name__ == "__main__":
    unittest.main(verbosity=2)
