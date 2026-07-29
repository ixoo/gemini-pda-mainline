#!/usr/bin/env python3
"""Offline contract tests for Hubble's direct-USB volatile transfer."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import pathlib
import re
import sys
import unittest
from unittest import mock


sys.dont_write_bytecode = True
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
RUNNER_PATH = SCRIPT_DIR / "run-hubble-transfer.py"
SPEC = importlib.util.spec_from_file_location("hubble_transfer", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot import Hubble transfer runner")
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)

BOOT_ID = "01234567-89ab-4def-8123-456789abcdef"


def i2c_status(transfers: int) -> str:
    return (
        "handoff=ready probe_attempts=1 init_attempts=1 init_successes=1 "
        "clock_ungated_checks=1 clock_gated_checks=1 "
        "clock_validation_failures=0 runtime_pm_link=1 "
        "clock_domains=i2c-appm,ap-dma "
        f"transfer_attempts={transfers} dma_starts={transfers} "
        f"nonzero_starts={transfers} irq_count={transfers} "
        "suspend_checks=0 resume_checks=0 resume_failures=0"
    )


def valid_capture() -> bytes:
    stdout = [
        (
            "GEMINI_PHOTON_BEGIN adapter=i2c-1 of=/i2c@1100e000 "
            "address=0x69 transactions=6"
        ),
    ]
    kmsg = ["[  20.000] " + stdout[0]]
    registers = ("05", "06", "47", "05", "06", "47")
    prefills = ("a1", "b2", "c3", "d4", "e5", "f6")
    for transaction, (register, prefill) in enumerate(
        zip(registers, prefills, strict=True), start=1
    ):
        pre = (
            f"GEMINI_PHOTON_PRE transaction={transaction} "
            f"pass={(transaction - 1) // 3 + 1} register=0x{register} "
            f"prefill=0x{prefill} address=0x69 messages=2"
        )
        stdout.extend(
            (
                pre,
                (
                    f"GEMINI_PHOTON_READ transaction={transaction} "
                    f"pass={(transaction - 1) // 3 + 1} register=0x{register} "
                    f"pre=0x{prefill} post=0x{prefill} post_differs_pre=no"
                ),
            )
        )
        kmsg.append(f"[  20.00{transaction}] {pre}")
    result = (
        "GEMINI_PHOTON_RESULT class=post-all-equal-pre completed=6 "
        "ioctl_result=2 errno=0 pre=a1,b2,c3,d4,e5,f6 "
        "post=a1,b2,c3,d4,e5,f6 post_diff_mask=0x00 "
        "page_con_access=none"
    )
    stdout.append(result)
    kmsg.append("[  20.007] " + result)
    lines = [
        RUNNER.USB_BANNER,
        "__HUBBLE_GATE_BEGIN__",
        f"kernel={RUNNER.CASSINI_KERNEL}",
        f"cmdline={RUNNER.CASSINI_CMDLINE}",
        f"config_sha256={RUNNER.CASSINI_CONFIG_SHA256}",
        f"cassini_helper_sha256={RUNNER.CASSINI_HELPER_SHA256}",
        "rootfs_type=rootfs",
        "run_mounts=0",
        f"boot_id={BOOT_ID}",
        "cpu_possible=0-9",
        "cpu_present=0-9",
        "cpu_online=0-7",
        "cpu_offline=8-9",
        "nproc=8",
        "handoff_state=ready",
        f"i2c6_status_pre={i2c_status(0)}",
        "i2c6_adapter=i2c-1",
        "i2c6_of=/sys/firmware/devicetree/base/i2c@1100e000",
        "i2c6_clients=0",
        "usb0_address=42:00:15:19:82:01",
        "usb0_carrier=1",
        "usb0_operstate=up",
        "usb0_ipv4_exact=1",
        "udc_name=11271000.usb",
        "udc_state=configured",
        "usb_service_count=1",
        "usb_ready_count=1",
        "prior_photon_markers=0",
        "__HUBBLE_GATE_END__",
        "__HUBBLE_GATE_PASS__",
        (
            f"__HUBBLE_TRANSFER_PASS__ size={RUNNER.HELPER_SIZE} "
            f"sha256={RUNNER.HELPER_SHA256} mode=500:0:0 "
            "path=/run/hubble-photon-r2"
        ),
        "__HUBBLE_PRE_BEGIN__",
        f"boot_id_pre={BOOT_ID}",
        "cpu_online_pre=0-7",
        "cpu_offline_pre=8-9",
        "nproc_pre=8",
        "handoff_state_pre=ready",
        f"i2c6_status_pre={i2c_status(0)}",
        "usb_carrier_pre=1",
        "usb_operstate_pre=up",
        "udc_state_pre=configured",
        "__HUBBLE_PRE_END__",
        "__HUBBLE_PROBE_STDOUT_BEGIN__",
        *stdout,
        "__HUBBLE_PROBE_STDOUT_END__",
        "__HUBBLE_POST_BEGIN__",
        f"boot_id_post={BOOT_ID}",
        "cpu_online_post=0-7",
        "cpu_offline_post=8-9",
        "nproc_post=8",
        "handoff_state_post=ready",
        f"i2c6_status_post={i2c_status(6)}",
        "usb_carrier_post=1",
        "usb_operstate_post=up",
        "udc_state_post=configured",
        "__HUBBLE_POST_END__",
        "__HUBBLE_KMSG_BEGIN__",
        *kmsg,
        "__HUBBLE_KMSG_END__",
        (
            "__HUBBLE_COMPLETE__ probe_rc=2 invocation_count=1 "
            "helper_removed=yes guard_mode=400:0:0"
        ),
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


class HubbleTransferContracts(unittest.TestCase):
    def test_exact_pins_and_endpoint(self) -> None:
        self.assertEqual(
            RUNNER.HELPER_SHA256,
            "b36cefe50227f8fe6a838cba0c8757279dcd0766b804afa77de5518c263cbdf4",
        )
        self.assertEqual(RUNNER.HELPER_SIZE, 537_584)
        self.assertEqual(RUNNER.DEVICE_ADDRESS, "10.15.19.82")
        self.assertEqual(RUNNER.DEVICE_PORT, 2323)
        self.assertEqual(RUNNER.CASSINI_KERNEL, "7.1.3-gemini-cassini")

    def test_mock_helper_serialization_round_trips(self) -> None:
        fixture = b"offline-photon-fixture"
        with (
            mock.patch.object(RUNNER, "HELPER_SIZE", len(fixture)),
            mock.patch.object(
                RUNNER, "HELPER_SHA256", hashlib.sha256(fixture).hexdigest()
            ),
        ):
            program = RUNNER.build_remote_program(fixture).decode("ascii")
        payload = program.split(
            "<<'__HUBBLE_PAYLOAD__'\n", 1
        )[1].split("\n__HUBBLE_PAYLOAD__\n", 1)[0]
        self.assertEqual(base64.b64decode(payload, validate=True), fixture)

    def test_remote_gate_precedes_transfer_and_one_invocation(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        self.assertLess(source.index("__HUBBLE_GATE_PASS__"), source.index("base64 -d"))
        guard = '( set -C; : >"$guard_path" )'
        self.assertLess(source.index("__HUBBLE_TRANSFER_PASS__"), source.index(guard))
        self.assertEqual(source.count('\n"$probe_path"\n'), 1)
        self.assertLess(source.index(guard), source.index('\n"$probe_path"\n'))
        self.assertIn('/bin/busybox rm -f "$probe_path"', source)
        self.assertIn("invocation_count=1 helper_removed=yes", source)

    def test_remote_scope_has_no_persistent_or_platform_control_paths(self) -> None:
        source = RUNNER.REMOTE_TEMPLATE
        forbidden = (
            "/dev/mmc",
            "/sys/block",
            "/proc/partitions",
            "/dev/watchdog",
            "/sys/class/watchdog",
            "/sys/power",
            "/boot/",
            "boot2",
            "boot3",
            "poweroff",
            "shutdown",
            "\ndd ",
            "blkdiscard",
            "fw_setenv",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, source)
        self.assertIsNone(
            re.search(r"(?:^|[;&|]\s*)(?:/bin/busybox\s+)?reboot(?:\s|$)", source)
        )
        write_redirections = re.findall(r'>\s*"?([^"\s]+)', source)
        self.assertEqual(
            set(write_redirections),
            {"$stage_path", "$guard_path", "/dev/null"},
        )
        self.assertNotIn("/cpu8/online >", source)
        self.assertNotIn("/cpu9/online >", source)

    def test_transport_is_mockable_and_exactly_one_nc_call(self) -> None:
        completed = mock.Mock(returncode=0, stdout=b"capture", stderr=b"")
        with mock.patch.object(RUNNER.subprocess, "run", return_value=completed) as run:
            result = RUNNER.run_transport("en7", b"program")
        self.assertIs(result, completed)
        run.assert_called_once()
        args = run.call_args.args[0]
        self.assertEqual(args[0], "nc")
        self.assertEqual(args[-2:], ["10.15.19.82", "2323"])
        self.assertEqual(run.call_args.kwargs["input"], b"program")

    def test_nonexact_helper_is_rejected_before_transport(self) -> None:
        with self.assertRaises(RUNNER.ContractError):
            RUNNER.build_remote_program(b"wrong")

    def test_host_header_declares_inert_boundaries(self) -> None:
        header = RUNNER.host_header("en7").decode("ascii")
        self.assertIn("transport=direct-usb-nc-shell", header)
        self.assertIn("remote_destination=/run/hubble-photon-r2", header)
        self.assertIn("persistent_storage_access=none", header)
        self.assertIn("watchdog_control=none", header)
        self.assertIn("reboot_or_slot_control=none", header)

    def test_offline_runtime_fixture_passes_strict_parser(self) -> None:
        parsed = RUNNER.validate_transcript(valid_capture())
        self.assertEqual(
            parsed,
            {
                "boot_id": BOOT_ID,
                "result_class": "post-all-equal-pre",
                "probe_rc": "2",
                "i2c6_adapter": "i2c-1",
            },
        )

    def test_runtime_identity_transfer_delta_and_one_shot_mutations_fail(self) -> None:
        valid = valid_capture()
        mutations = (
            valid.replace(
                RUNNER.CASSINI_KERNEL.encode(),
                b"7.1.3-gemini-not-cassini",
                1,
            ),
            valid.replace(RUNNER.HELPER_SHA256.encode(), b"0" * 64, 1),
            valid.replace(b"transfer_attempts=6", b"transfer_attempts=5", 1),
            valid.replace(b"invocation_count=1", b"invocation_count=2", 1),
            valid.replace(
                b"GEMINI_PHOTON_BEGIN ",
                b"GEMINI_PHOTON_BEGIN duplicate=yes\nGEMINI_PHOTON_BEGIN ",
                1,
            ),
        )
        for capture in mutations:
            with self.subTest():
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_transcript(capture)


if __name__ == "__main__":
    unittest.main()
