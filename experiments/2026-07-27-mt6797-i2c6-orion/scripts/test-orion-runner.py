#!/usr/bin/env python3
"""Source and reset-accounting tests for the Orion one-shot collector."""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
RUNNER_PATH = SCRIPT_DIR / "run-orion-one-shot.py"
SPEC = importlib.util.spec_from_file_location("orion_runner", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Orion runner")
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FULL = load("orion_runner_full", "validate-orion-result.py")
PARTIAL = load("orion_runner_partial", "validate-orion-partial.py")
FIXTURE = load("orion_runner_fixture", "test-orion-result.py")
PARTIAL_FIXTURE = load("orion_runner_partial_fixture", "test-orion-partial.py")


def valid_capture(config_hash: str = "a" * 64) -> bytes:
    adapter = "i2c-1"
    adapter_debugfs = f"/run/orion-debugfs/i2c/{adapter}"
    gate = {
        "kernel": RUNNER.KERNEL_RELEASE,
        "cmdline": RUNNER.KERNEL_CMDLINE,
        "config_sha256": config_hash,
        "rootfs_type": "rootfs",
        "run_mounts": "0",
        "boot_id_pre": "00000000-0000-0000-0000-000000000001",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "nproc": "8",
        "handoff_state": "ready",
        "i2c6_compatible_sha256": RUNNER.I2C6_COMPATIBLE_SHA256,
        "i2c6_status_pre": RUNNER.I2C_STATUS_PRE,
        "i2c6_adapter": adapter,
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
        "debugfs_mount": "/run/orion-debugfs",
        "debugfs_mount_count": "1",
        "adapter_debugfs": adapter_debugfs,
        "diagnostic_path": adapter_debugfs + "/orion-run-all",
        "diagnostic_mode": "600:0:0",
        "diagnostic_pre": RUNNER.ORION_STATUS_PRE,
    }
    gate_text = "\n".join(f"{key}={value}" for key, value in gate.items())
    result = FIXTURE.valid_result().decode("ascii").rstrip("\n")
    i2c_status = (
        "handoff=ready probe_attempts=1 init_attempts=4 init_successes=4 "
        "clock_ungated_checks=1 clock_gated_checks=1 "
        "clock_validation_failures=0 runtime_pm_link=1 "
        "clock_domains=i2c-appm,ap-dma transfer_attempts=9 dma_starts=6 "
        "nonzero_starts=9 irq_count=9 suspend_checks=0 resume_checks=0 "
        "resume_failures=0"
    )
    post = {
        "write_rc": "0",
        "orion_final_rc": "0",
        "i2c_status_post_rc": "0",
        "dmesg_rc": "0",
        "boot_id_post": gate["boot_id_pre"],
        "boot_id_post_rc": "0",
        "cpu_online_post": "0-7",
        "cpu_online_post_rc": "0",
        "cpu_offline_post": "8-9",
        "cpu_offline_post_rc": "0",
        "nproc_post": "8",
        "nproc_post_rc": "0",
        "handoff_state_post": "ready",
        "handoff_state_post_rc": "0",
        "usb_carrier_post": "1",
        "usb_carrier_post_rc": "0",
        "usb_operstate_post": "up",
        "usb_operstate_post_rc": "0",
        "udc_state_post": "configured",
        "udc_state_post_rc": "0",
        "ac_status_post_rc": "0",
    }
    post_text = "\n".join(f"{key}={value}" for key, value in post.items())
    log = (
        "[    1.0] GEMINI_ORION_DIAGNOSTIC state=ready one_shot=unused\n"
        "[   10.0] i2c register snapshot dma_tx_mem=0xdeadbeef"
    )
    text = "\n".join(
        (
            RUNNER.USB_BANNER,
            "__ORION_GATE_BEGIN__",
            gate_text,
            "__ORION_GATE_END__",
            "__ORION_GATE_PASS__",
            "__ORION_FINAL_BEGIN__",
            result,
            "__ORION_FINAL_END__",
            "__ORION_I2C_STATUS_POST_BEGIN__",
            i2c_status,
            "__ORION_I2C_STATUS_POST_END__",
            "__ORION_POST_BEGIN__",
            post_text,
            "__ORION_POST_END__",
            "__ORION_AC_STATUS_POST_BEGIN__",
            "usb_shell=ready reboot_dispatch=validated privilege=root",
            "__ORION_AC_STATUS_POST_END__",
            "__ORION_DMESG_RAW_BEGIN__",
            log,
            "__ORION_DMESG_RAW_END__",
            "__ORION_COMPLETE__ write_rc=0 invocation_count=1 "
            "guard_mode=400:0:0 post_capture=unconditional",
            "",
        )
    )
    return text.encode("ascii")


def partial_capture(result: bytes, init_count: int) -> bytes:
    text = valid_capture().decode("ascii")
    final_start = text.index("__ORION_FINAL_BEGIN__\n") + len(
        "__ORION_FINAL_BEGIN__\n"
    )
    final_stop = text.index("\n__ORION_FINAL_END__", final_start)
    text = text[:final_start] + result.decode("ascii").rstrip("\n") + text[final_stop:]
    header = dict(
        token.split("=", 1)
        for token in result.decode("ascii").splitlines()[0].split()
    )
    old_status = (
        "handoff=ready probe_attempts=1 init_attempts=4 init_successes=4 "
        "clock_ungated_checks=1 clock_gated_checks=1 "
        "clock_validation_failures=0 runtime_pm_link=1 "
        "clock_domains=i2c-appm,ap-dma transfer_attempts=9 dma_starts=6 "
        "nonzero_starts=9 irq_count=9 suspend_checks=0 resume_checks=0 "
        "resume_failures=0"
    )
    new_status = (
        f"handoff=ready probe_attempts=1 init_attempts={init_count} "
        f"init_successes={init_count} clock_ungated_checks=1 "
        "clock_gated_checks=1 clock_validation_failures=0 "
        "runtime_pm_link=1 clock_domains=i2c-appm,ap-dma "
        f"transfer_attempts={header['transfer_attempts']} "
        f"dma_starts={header['dma_starts']} "
        f"nonzero_starts={header['nonzero_starts']} "
        f"irq_count={header['irqs']} suspend_checks=0 resume_checks=0 "
        "resume_failures=0"
    )
    text = text.replace(old_status, new_status, 1)
    text = text.replace("write_rc=0", "write_rc=1", 2)
    return text.encode("ascii")


class OrionRunnerContracts(unittest.TestCase):
    def test_remote_program_resolves_only_placeholders(self) -> None:
        config_hash = "a" * 64
        program = RUNNER.build_remote_program(config_hash).decode("ascii")
        self.assertEqual(
            set(RUNNER.REMOTE_TOKEN.findall(program)),
            RUNNER.RUNTIME_TOKENS,
        )
        self.assertIn(config_hash, program)
        self.assertNotIn("__ORION_CONFIG_SHA256__", program)

        original = RUNNER.REMOTE_TEMPLATE
        try:
            RUNNER.REMOTE_TEMPLATE = original + "\n__ORION_UNKNOWN__\n"
            with self.assertRaises(RUNNER.ContractError):
                RUNNER.build_remote_program(config_hash)
        finally:
            RUNNER.REMOTE_TEMPLATE = original

    def test_exact_write_then_unconditional_capture_order(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        ordered = (
            "set +e\nprintf 'run\\n' >\"$diag\"\nwrite_rc=$?",
            'orion_final=$(/bin/busybox cat "$diag" 2>&1)',
            'i2c_status_post=$(/bin/busybox cat "$i2c6/handoff_status" 2>&1)',
            "\nkernel_log=$(/bin/busybox dmesg 2>&1)",
            "__ORION_FINAL_BEGIN__",
            "__ORION_I2C_STATUS_POST_BEGIN__",
            "__ORION_DMESG_RAW_BEGIN__",
            "__ORION_COMPLETE__",
        )
        positions = [source.index(value) for value in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count("printf 'run\\n' >\"$diag\""), 1)
        self.assertIn("post_capture=unconditional", source)

    def test_prewrite_fatal_gate_precedes_guard_and_write(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        ordered = (
            "pre_kernel_log=$(/bin/busybox dmesg 2>&1)",
            'require_equal "$pre_dmesg_fatal_count" 0 pre-dmesg-fatal',
            '( set -C; : >"$guard_path" )',
            "printf 'run\\n' >\"$diag\"",
        )
        positions = [source.index(value) for value in ordered]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("pre_dmesg_fatal_count=0", source)

    def test_write_target_is_exact_adapter_debugfs_child(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        self.assertIn(
            'adapter_debugfs="$debugfs_root/i2c/$adapter_name"', source
        )
        self.assertIn(
            'diag="$adapter_debugfs/orion-run-all"', source
        )
        self.assertNotIn('find "$debugfs_root"', source)

    def test_raw_log_is_private_and_not_sanitized(self) -> None:
        source = RUNNER_PATH.read_text()
        self.assertIn("The transcript's dmesg section may contain DMA addresses", source)
        self.assertIn("raw_dmesg_address_lines=private-not-copied", source)
        self.assertNotIn("*log.splitlines()", source)

    def test_valid_capture_sanitizes_address_bearing_log(self) -> None:
        classification, result, sanitized = RUNNER.validate_capture(
            valid_capture(), "a" * 64, FULL, PARTIAL
        )
        self.assertEqual(classification, "complete-success")
        self.assertEqual(result, FIXTURE.valid_result())
        self.assertNotIn("deadbeef", sanitized)
        self.assertNotIn("dma_tx_mem", sanitized)
        self.assertIn("raw_dmesg_address_lines=private-not-copied", sanitized)

    def test_rejects_noncanonical_boot_id_or_wrong_of_path(self) -> None:
        for old, new in (
            (
                b"boot_id_pre=00000000-0000-0000-0000-000000000001",
                b"boot_id_pre=NOT-A-UUID",
            ),
            (
                b"i2c6_of=/sys/firmware/devicetree/base/i2c@1100e000",
                b"i2c6_of=/other/i2c@1100e000",
            ),
        ):
            with self.assertRaises(RUNNER.ContractError):
                RUNNER.validate_capture(
                    valid_capture().replace(old, new, 1),
                    "a" * 64,
                    FULL,
                    PARTIAL,
                )

    def test_started_partial_capture_uses_error_reset(self) -> None:
        data = partial_capture(PARTIAL_FIXTURE.started_dma_timeout(), 4)
        classification, _result, sanitized = RUNNER.validate_capture(
            data, "a" * 64, FULL, PARTIAL
        )
        self.assertEqual(classification, "bounded-stop-first-partial")
        self.assertIn("failing_mode=packed-dma", sanitized)

    def test_new_mode_prestart_accepts_before_or_after_pending_reset(self) -> None:
        for init_count in (2, 3):
            data = partial_capture(
                PARTIAL_FIXTURE.prestart_dma_failure(), init_count
            )
            classification, _result, _sanitized = RUNNER.validate_capture(
                data, "a" * 64, FULL, PARTIAL
            )
            self.assertEqual(classification, "bounded-stop-first-partial")

    def test_full_success_reset_count(self) -> None:
        self.assertEqual(
            RUNNER.allowed_init_counts("complete-success", 9, 9, 9),
            {4},
        )

    def test_started_partial_reset_counts(self) -> None:
        expected = {
            0: {3},
            1: {3},
            2: {3},
            3: {4},
            4: {4},
            5: {4},
            6: {5},
            7: {5},
            8: {5},
        }
        for completed, wanted in expected.items():
            attempted = completed + 1
            self.assertEqual(
                RUNNER.allowed_init_counts(
                    "bounded-stop-first-partial",
                    completed,
                    attempted,
                    attempted,
                ),
                wanted,
            )

    def test_prestart_partial_reset_counts(self) -> None:
        expected = {
            0: {1, 2},
            1: {2},
            2: {2},
            3: {2, 3},
            4: {3},
            5: {3},
            6: {3, 4},
            7: {4},
            8: {4},
        }
        for completed, wanted in expected.items():
            self.assertEqual(
                RUNNER.allowed_init_counts(
                    "bounded-stop-first-partial",
                    completed,
                    completed + 1,
                    completed,
                ),
                wanted,
            )


if __name__ == "__main__":
    unittest.main()
