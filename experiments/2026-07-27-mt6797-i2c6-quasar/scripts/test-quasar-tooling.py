#!/usr/bin/env python3
"""Offline production and mutation contracts for Quasar host tooling."""

from __future__ import annotations

import hashlib
import importlib.util
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REPOSITORY = SCRIPT_DIR.parents[2]
sys.path.insert(0, os.fspath(SCRIPT_DIR))

import candidate_quasar as co
import installer_quasar as io


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


assembler = load("quasar_candidate_deriver_test", "derive-candidate.py")
installer = load("quasar_installer_deriver_test", "derive-installer.py")
repro = load("quasar_reproducibility_test", "verify-quasar-reproducibility.py")
runner = load("quasar_runner_test", "run-quasar-one-shot.py")
result_fixture = load("quasar_result_fixture", "test-quasar-result.py")


def fixture_pins() -> io.ArtifactPins:
    return io.ArtifactPins(
        raw_sha256="1" * 64,
        raw_size=7_800_001,
        padded_sha256="2" * 64,
        manifest_sha256="3" * 64,
    )


def valid_reproducibility_record(pins: io.ArtifactPins) -> bytes:
    package_inventory = {
        "Image": repro.InventoryMember(0o600, 123, "4" * 64)
    }
    candidate_inventory = {
        io.BOOT_MEMBER: repro.InventoryMember(
            0o600,
            pins.raw_size,
            pins.raw_sha256,
        )
    }
    packages = (
        repro.PackageResult(
            "linux-7.1.3-gemini-quasar-fixture",
            "5" * 64,
            "2026-07-27T01:00:00Z",
            b'{"fixture":true}\n',
            package_inventory,
        ),
        repro.PackageResult(
            "linux-7.1.3-gemini-quasar-fixture",
            "6" * 64,
            "2026-07-27T02:00:00Z",
            b'{"fixture":true}\n',
            package_inventory,
        ),
    )
    candidate = repro.CandidateResult(
        pins.artifact_dir,
        candidate_inventory,
        pins.raw_size,
        pins.raw_sha256,
        pins.padded_sha256,
        pins.manifest_sha256,
        "9" * 64,
    )
    return repro.render_record(
        io.REPRODUCIBILITY_VERIFIER_SHA256,
        packages,
        (candidate, candidate, candidate, candidate),
    )


def synthetic_runtime_capture(config_sha256: str) -> bytes:
    base = runner._BASE
    boot_id = "11111111-2222-4333-8444-555555555555"
    prefix = "\n".join(base.expected_usb_envelope(1)) + "\n"
    topology = "\n".join(
        (
            "__QUASAR_ADAPTER_TOPOLOGY_BEGIN__",
            "contract=canonical-adapter-target-direct-parent-v1",
            f"kernel={base.KERNEL_RELEASE}",
            f"config_sha256={config_sha256}",
            f"boot_id={boot_id}",
            "platform_target=/sys/devices/platform/1100e000.i2c",
            "dt_target=/sys/firmware/devicetree/base/i2c@1100e000",
            "entry_limit=64",
            (
                "entry index=1 adapter=i2c-0 link=1 name_valid=1 canonical=1 "
                "target=/sys/devices/platform/1101c000.i2c/i2c-0 "
                "parent=/sys/devices/platform/1101c000.i2c parent_match=0 "
                "of_canonical=1 "
                "of_target=/sys/firmware/devicetree/base/i2c@1101c000 "
                "of_match=0 match=0"
            ),
            (
                "entry index=2 adapter=i2c-1 link=1 name_valid=1 canonical=1 "
                "target=/sys/devices/platform/1100e000.i2c/i2c-1 "
                "parent=/sys/devices/platform/1100e000.i2c parent_match=1 "
                "of_canonical=1 "
                "of_target=/sys/firmware/devicetree/base/i2c@1100e000 "
                "of_match=1 match=1"
            ),
            (
                "summary entry_count=2 link_count=2 name_count=2 "
                "canonical_count=2 parent_match_count=1 "
                "of_canonical_count=2 of_match_count=1 match_count=1 "
                "overflow=0"
            ),
            "__QUASAR_ADAPTER_TOPOLOGY_END__",
        )
    )
    gate_values = {
        "kernel": base.KERNEL_RELEASE,
        "cmdline": base.KERNEL_CMDLINE,
        "config_sha256": config_sha256,
        "rootfs_type": "rootfs",
        "run_mounts": "0",
        "boot_id_pre": boot_id,
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "nproc": "8",
        "handoff_state": "ready",
        "i2c6_compatible_sha256": base.I2C6_COMPATIBLE_SHA256,
        "i2c6_status_pre": base.I2C_STATUS_PRE,
        "i2c6_adapter": "i2c-1",
        "i2c6_of": "/sys/firmware/devicetree/base/i2c@1100e000",
        "i2c6_clients": "0",
        "i2c_chardev": "absent",
        "keyboard_devices": "1",
        "tty1": "character-device",
        "usb0_address": "42:00:15:19:82:01",
        "usb0_carrier": "1",
        "usb0_operstate": "up",
        "usb0_ipv4_exact": "1",
        "udc_name": "11271000.usb",
        "udc_state": "configured",
        "usb_service_count": "1",
        "usb_ready_count": "1",
        "pre_dmesg_fatal_count": "0",
        "debugfs_mount": "/run/quasar-debugfs",
        "debugfs_mount_count": "1",
        "adapter_debugfs": "/run/quasar-debugfs/i2c/i2c-1",
        "diagnostic_path": (
            "/run/quasar-debugfs/i2c/i2c-1/quasar-run-native"
        ),
        "diagnostic_mode": "600:0:0",
        "diagnostic_pre": base.DIAGNOSTIC_STATUS_PRE,
    }
    gate = "\n".join(
        (
            "__QUASAR_GATE_BEGIN__",
            *(f"{key}={gate_values[key]}" for key in base.GATE_FIELD_ORDER),
            "__QUASAR_FINAL_REVALIDATION_BEGIN__",
            *base.FINAL_REVALIDATION_STEPS,
            "__QUASAR_FINAL_REVALIDATION_END__",
            "__QUASAR_GATE_END__",
            "__QUASAR_GATE_PASS__",
        )
    )
    final = result_fixture.success_result().decode("ascii").rstrip("\n")
    status = (
        "handoff=ready probe_attempts=1 init_attempts=1 init_successes=1 "
        "clock_ungated_checks=1 clock_gated_checks=1 "
        "clock_validation_failures=0 runtime_pm_link=1 "
        "clock_domains=i2c-appm,ap-dma transfer_attempts=6 dma_starts=0 "
        "nonzero_starts=6 irq_count=6 suspend_checks=0 resume_checks=0 "
        "resume_failures=0"
    )
    post = "\n".join(
        (
            "write_rc=0",
            "quasar_final_rc=0",
            "i2c_status_post_rc=0",
            "dmesg_rc=0",
            f"boot_id_post={boot_id}",
            "boot_id_post_rc=0",
            "cpu_online_post=0-7",
            "cpu_online_post_rc=0",
            "cpu_offline_post=8-9",
            "cpu_offline_post_rc=0",
            "nproc_post=8",
            "nproc_post_rc=0",
            "handoff_state_post=ready",
            "handoff_state_post_rc=0",
            "usb_carrier_post=1",
            "usb_carrier_post_rc=0",
            "usb_operstate_post=up",
            "usb_operstate_post_rc=0",
            "udc_state_post=configured",
            "udc_state_post_rc=0",
            "ac_status_post_rc=0",
        )
    )
    tail = "\n".join(
        (
            "__QUASAR_FINAL_BEGIN__",
            final,
            "__QUASAR_FINAL_END__",
            "__QUASAR_I2C_STATUS_POST_BEGIN__",
            status,
            "__QUASAR_I2C_STATUS_POST_END__",
            "__QUASAR_POST_BEGIN__",
            post,
            "__QUASAR_POST_END__",
            "__QUASAR_AC_STATUS_POST_BEGIN__",
            "synthetic-ac-status=retained",
            "__QUASAR_AC_STATUS_POST_END__",
            "__QUASAR_DMESG_RAW_BEGIN__",
            (
                "i2c-mt65xx 1100e000.i2c: "
                "GEMINI_QUASAR_NATIVE_DIAGNOSTIC state=ready "
                "one_shot=unused mode=none forced_length_mode=none "
                "forced_engine=none reset_pending=0"
            ),
            "__QUASAR_DMESG_RAW_END__",
            (
                "__QUASAR_COMPLETE__ write_rc=0 invocation_count=1 "
                "guard_mode=400:0:0 post_capture=unconditional"
            ),
            "",
        )
    )
    return (prefix + topology + "\n" + gate + "\n" + tail).encode("ascii")


class QuasarHostToolingContracts(unittest.TestCase):
    def test_exact_source_and_profile_pins(self) -> None:
        co.require_input_pins()
        self.assertEqual(
            io.REPRODUCIBILITY_VERIFIER_SHA256,
            hashlib.sha256(
                (
                    REPOSITORY / io.REPRODUCIBILITY_VERIFIER
                ).read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(
            co.digest_path(REPOSITORY / co.SERIES),
            co.SERIES_SHA256,
        )
        self.assertEqual(
            co.digest_path(REPOSITORY / co.CONFIG_FRAGMENT),
            co.CONFIG_FRAGMENT_SHA256,
        )
        for relative, wanted in zip(
            co.QUASAR_PATCHES,
            co.QUASAR_PATCH_SHA256S,
            strict=True,
        ):
            self.assertEqual(
                co.digest_path(REPOSITORY / "patches" / relative),
                wanted,
            )
        vega_entries = [
            line
            for line in (
                REPOSITORY / "patches/series-vega-i2c6-idvfs-fifo"
            ).read_text().splitlines()
            if line and not line.startswith("#")
        ]
        quasar_entries = [
            line
            for line in (REPOSITORY / co.SERIES).read_text().splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(quasar_entries, vega_entries + [co.QUASAR_PATCH])
        self.assertEqual(len(quasar_entries), 108)

    def test_assembler_is_exact_storage_inert_vega_derivative(self) -> None:
        source_path = REPOSITORY / assembler.VEGA_BUILDER
        source = source_path.read_text(encoding="utf-8")
        self.assertEqual(
            hashlib.sha256(source.encode()).hexdigest(),
            assembler.VEGA_BUILDER_SHA256,
        )
        derived = assembler.derive_text(source)
        assembler.validate_contract(derived)
        self.assertEqual(derived.count('printf \'run\\n\''), 0)
        self.assertNotIn("of=/dev/", derived)
        mutations = (
            source.replace("Candidate Vega", "Candidate Changed", 1),
            source.replace("candidate_vega", "candidate_changed", 1),
            source.replace("--lk-android8", "--not-lk", 1),
            source.replace("hardware_write=none", "hardware_write=yes", 1),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(ValueError):
                    assembler.derive_text(mutated)

    def test_reproducibility_derivative_and_record_mutations(self) -> None:
        source = (
            REPOSITORY / repro.VEGA_VERIFIER
        ).read_text(encoding="utf-8")
        self.assertEqual(
            hashlib.sha256(source.encode()).hexdigest(),
            repro.VEGA_VERIFIER_SHA256,
        )
        derived = repro.derive_source(source)
        self.assertIn("quasar-two-build-2x2-reproducibility", derived)
        self.assertNotIn("candidate=Vega", derived)
        self.assertEqual(
            repro.CANDIDATE_MODULE_SHA256,
            hashlib.sha256(
                (SCRIPT_DIR / "candidate_quasar.py").read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(
            repro.PACKAGE_VALIDATOR_SHA256,
            hashlib.sha256(
                (SCRIPT_DIR / "validate-package-quasar.py").read_bytes()
            ).hexdigest(),
        )
        pins = fixture_pins()
        record = valid_reproducibility_record(pins)
        fields = io.validate_reproducibility_record(record, pins)
        self.assertEqual(fields["package_lane_count"], "2")
        self.assertEqual(fields["candidate_lane_count"], "4")
        mutations = (
            record.replace(b"package_lane_count=2", b"package_lane_count=1", 1),
            record.replace(
                f"candidate_raw_sha256={pins.raw_sha256}".encode(),
                b"candidate_raw_sha256=" + b"7" * 64,
                1,
            ),
            record.replace(
                b"candidate_b_b_inventory_sha256="
                + fields["candidate_inventory_sha256"].encode(),
                b"candidate_b_b_inventory_sha256=" + b"8" * 64,
                1,
            ),
            record + b"candidate_lane_count=4\n",
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(ValueError):
                    io.validate_reproducibility_record(mutated, pins)

    def test_reproducibility_requires_distinct_lanes_and_exact_padding(self) -> None:
        with tempfile.TemporaryDirectory(prefix="quasar-repro-test.") as raw:
            root = pathlib.Path(raw)
            packages = (root / "package-a", root / "package-b")
            candidates = tuple(root / f"candidate-{index}" for index in range(4))
            for path in packages + candidates:
                path.mkdir()
            repro.require_distinct_lanes(packages, candidates)
            with self.assertRaises(repro.ContractError):
                repro.require_distinct_lanes(
                    packages,
                    candidates[:3] + (candidates[0],),
                )

            raw_image = root / "raw.img"
            padded = root / "padded.img"
            raw_data = b"Quasar synthetic raw"
            padded_data = raw_data + b"\0" * 97
            raw_image.write_bytes(raw_data)
            padded.write_bytes(padded_data)
            repro.verify_padded_construction(
                raw_image,
                padded,
                len(raw_data),
                len(padded_data),
                "synthetic Quasar",
            )
            mutation = bytearray(padded_data)
            mutation[-1] = 1
            padded.write_bytes(mutation)
            with self.assertRaises(repro.ContractError):
                repro.verify_padded_construction(
                    raw_image,
                    padded,
                    len(raw_data),
                    len(padded_data),
                    "synthetic Quasar",
                )

    def test_installer_predecessor_and_all_critical_gates(self) -> None:
        self.assertEqual(
            io.require_predecessor_evidence(REPOSITORY),
            io.VEGA_INSTALL_RECORD_SHA256,
        )
        pins = fixture_pins()
        with tempfile.TemporaryDirectory(prefix="quasar-installer-test.") as raw:
            root = pathlib.Path(raw)
            source = installer.reconstruct_vega(root)
            self.assertEqual(
                hashlib.sha256(source.encode()).hexdigest(),
                io.VEGA_INSTALLER_SHA256,
            )
            derived = installer.derive_text(source, pins)
            installer.validate_contract(derived, pins)
            generated = root / "install-candidate-quasar-boot2.sh"
            generated.write_text(derived, encoding="utf-8")
            generated.chmod(0o700)
            syntax = subprocess.run(
                ["bash", "-n", os.fspath(generated)],
                check=False,
                capture_output=True,
            )
            self.assertEqual(syntax.returncode, 0, syntax.stderr)
            for index, token in enumerate(
                installer.CRITICAL_TOKEN_COUNTS,
                1,
            ):
                mutated = derived.replace(
                    token,
                    f"QUASAR_MUTATED_GATE_{index}",
                    1,
                )
                with self.subTest(gate=token):
                    with self.assertRaises(ValueError):
                        installer.validate_contract(mutated, pins)
            forbidden = derived + "\nreboot now\n"
            with self.assertRaises(ValueError):
                installer.validate_contract(forbidden, pins)

    def test_production_installer_fails_closed_until_reproduced(self) -> None:
        pins = io.production_pins()
        with tempfile.TemporaryDirectory(prefix="quasar-unresolved-cli.") as raw:
            output = pathlib.Path(raw) / "install-candidate-quasar-boot2.sh"
            result = subprocess.run(
                [
                    sys.executable,
                    os.fspath(SCRIPT_DIR / "derive-installer.py"),
                    "--output",
                    os.fspath(output),
                ],
                cwd=REPOSITORY,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                check=False,
                capture_output=True,
            )
            if io.pins_resolved(pins):
                io.require_artifact_pins(pins)
                self.assertEqual(result.returncode, 0, result.stderr)
                info = output.lstat()
                self.assertFalse(output.is_symlink())
                self.assertTrue(stat.S_ISREG(info.st_mode))
                self.assertEqual(stat.S_IMODE(info.st_mode), 0o700)
                if io.INSTALLER_SHA256 != "UNRESOLVED":
                    self.assertEqual(
                        io.digest_path(output),
                        io.INSTALLER_SHA256,
                    )
            else:
                with self.assertRaises(ValueError):
                    io.require_artifact_pins(pins)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(output.exists())

    def test_runner_is_one_session_one_write_and_mutation_closed(self) -> None:
        validator = runner.load_result_validator()
        program = runner.static_runtime_contract(validator)
        text = program.decode("ascii")
        self.assertEqual(text.count("printf 'run\\n' >\"$diag\""), 1)
        self.assertEqual(text.count("quasar-run-native"), 2)
        self.assertNotIn("orion-run-all", text)
        self.assertNotIn("/bin/busybox nc ", text)
        self.assertNotIn("reboot ", text)
        source = (REPOSITORY / runner.VEGA_RUNNER).read_text(encoding="utf-8")
        mutations = (
            source.replace("printf 'run\\n' >\"$diag\"", "true", 1),
            source.replace("orion-run-all", "changed-endpoint", 1),
            source.replace(
                "run_transport(args.interface, program)",
                "run_transport(args.interface, program + program)",
                1,
            ),
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(ValueError):
                    runner.derive_base_source(mutated)

    def test_runner_accepts_one_exact_capture_and_rejects_mutations(self) -> None:
        validator = runner.load_result_validator()
        runner.configure_base(validator)
        config_sha256 = "a" * 64
        capture = synthetic_runtime_capture(config_sha256)
        classification, final, summary = runner.validate_capture(
            capture,
            config_sha256,
            validator,
        )
        self.assertEqual(classification, "complete-success")
        self.assertEqual(
            validator.validate_text(final).classification,
            "complete-success",
        )
        self.assertIn("invocation_count=1\n", summary)
        self.assertIn("raw_kernel_log_orion_ready_count=0\n", summary)
        mutations = (
            capture.replace(
                b"quasar-run-native",
                b"orion-run-all",
                1,
            ),
            capture.replace(
                b"pre_dma_en=00000000",
                b"pre_dma_en=00000001",
                1,
            ),
            capture.replace(
                b"transfer_attempts=6 dma_starts=0",
                b"transfer_attempts=5 dma_starts=0",
                1,
            ),
            capture.replace(
                b"cpu_online_post=0-7",
                b"cpu_online_post=0-6",
                1,
            ),
            capture.replace(
                b"__QUASAR_COMPLETE__ write_rc=0",
                b"__QUASAR_COMPLETE__ write_rc=1",
                1,
            ),
            capture.replace(
                b"GEMINI_QUASAR_NATIVE_DIAGNOSTIC",
                b"GEMINI_ORION_DIAGNOSTIC",
                1,
            ),
            capture + b"__QUASAR_COMPLETE__ write_rc=0\n",
        )
        for index, mutated in enumerate(mutations, 1):
            with self.subTest(mutation=index):
                with self.assertRaises(ValueError):
                    runner.validate_capture(
                        mutated,
                        config_sha256,
                        validator,
                    )

    def test_runner_accepts_bounded_failure_with_unconditional_post_capture(
        self,
    ) -> None:
        validator = runner.load_result_validator()
        runner.configure_base(validator)
        config_sha256 = "b" * 64
        capture = synthetic_runtime_capture(config_sha256)
        success = result_fixture.success_result().rstrip(b"\n")
        failure = result_fixture.bounded_failure().rstrip(b"\n")
        capture = capture.replace(success, failure, 1)
        success_status = (
            b"handoff=ready probe_attempts=1 init_attempts=1 "
            b"init_successes=1 clock_ungated_checks=1 "
            b"clock_gated_checks=1 clock_validation_failures=0 "
            b"runtime_pm_link=1 clock_domains=i2c-appm,ap-dma "
            b"transfer_attempts=6 dma_starts=0 nonzero_starts=6 "
            b"irq_count=6 suspend_checks=0 resume_checks=0 "
            b"resume_failures=0"
        )
        failure_status = success_status.replace(
            b"init_attempts=1 init_successes=1",
            b"init_attempts=2 init_successes=2",
        ).replace(
            (
                b"transfer_attempts=6 dma_starts=0 "
                b"nonzero_starts=6 irq_count=6"
            ),
            (
                b"transfer_attempts=1 dma_starts=0 "
                b"nonzero_starts=0 irq_count=0"
            ),
        )
        capture = capture.replace(success_status, failure_status, 1)
        capture = capture.replace(b"write_rc=0", b"write_rc=1")
        classification, final, summary = runner.validate_capture(
            capture,
            config_sha256,
            validator,
        )
        self.assertEqual(classification, "bounded-stop-first-failure")
        self.assertEqual(
            validator.validate_text(final).classification,
            "bounded-stop-first-failure",
        )
        self.assertIn("write_rc=1\n", summary)
        self.assertIn("post_capture=unconditional\n", summary)

    def test_output_scripts_have_safe_modes(self) -> None:
        expected = {
            "build-candidate-quasar.sh": 0o755,
            "derive-candidate.py": 0o755,
            "derive-installer.py": 0o755,
            "run-quasar-one-shot.py": 0o755,
            "validate-package-quasar.py": 0o755,
            "validate-quasar-result.py": 0o755,
            "verify-quasar-reproducibility.py": 0o755,
        }
        # Git records executable scripts; this local check accepts an
        # uncommitted 0644 only until chmod is applied by the preparation step.
        for name, wanted in expected.items():
            mode = stat.S_IMODE((SCRIPT_DIR / name).stat().st_mode)
            self.assertIn(mode, {0o644, wanted})


if __name__ == "__main__":
    unittest.main()
