#!/usr/bin/env python3
"""Offline contract and mutation tests for Mariner's volatile runner."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
RUNNER_PATH = SCRIPT_DIR / "run-mariner-transfer.py"
SPEC = importlib.util.spec_from_file_location("mariner_transfer", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot import Mariner transfer runner")
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


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


def valid_capture(post0: str = "d0", post1: str = "c0") -> bytes:
    mask = (post0 != "3c") | ((post1 != "a6") << 1)
    result_class = RUNNER.classify_posts(post0, post1, mask)
    probe_rc = "0" if result_class == "raw-expected-live" else "2"
    lines = [
        RUNNER.USB_BANNER,
        "__MARINER_GATE_BEGIN__",
        f"kernel={RUNNER.CASSINI_KERNEL}",
        f"cmdline={RUNNER.CASSINI_CMDLINE}",
        f"config_sha256={RUNNER.CASSINI_CONFIG_SHA256}",
        f"cassini_helper_sha256={RUNNER.CASSINI_HELPER_SHA256}",
        f"cassini_helper_size={RUNNER.CASSINI_HELPER_SIZE}",
        "rootfs_type=rootfs",
        "run_mounts=0",
        f"boot_id={RUNNER.ck.ACCEPTED_BOOT_ID}",
        "cpu_possible=0-9",
        "cpu_present=0-9",
        "cpu_online=0-7",
        "cpu_offline=8-9",
        "nproc=8",
        "handoff_state=ready",
        f"i2c6_status_pre={i2c_status(14)}",
        "i2c6_adapter=i2c-1",
        "i2c6_of=/sys/firmware/devicetree/base/i2c@1100e000",
        "i2c6_clients=0",
        "prior_photon_guard=400:0:0",
        "prior_kepler_guard=400:0:0",
        "prior_voyager_guard=400:0:0",
        "usb0_address=42:00:15:19:82:01",
        "usb0_carrier=1",
        "usb0_operstate=up",
        "usb0_ipv4_exact=1",
        "udc_name=11271000.usb",
        "udc_state=configured",
        "usb_service_count=1",
        "usb_ready_count=4",
        "__MARINER_GATE_END__",
        "__MARINER_GATE_PASS__",
        (
            f"__MARINER_TRANSFER_PASS__ size={RUNNER.ck.PROBE_BINARY_SIZE} "
            f"sha256={RUNNER.ck.PROBE_BINARY_SHA256} mode=500:0:0 "
            "path=/run/mariner-probe"
        ),
        "__MARINER_PRE_BEGIN__",
        f"boot_id_pre={RUNNER.ck.ACCEPTED_BOOT_ID}",
        "cpu_online_pre=0-7",
        "cpu_offline_pre=8-9",
        "nproc_pre=8",
        "handoff_state_pre=ready",
        f"i2c6_status_pre={i2c_status(14)}",
        "usb_carrier_pre=1",
        "usb_operstate_pre=up",
        "udc_state_pre=configured",
        "__MARINER_PRE_END__",
        "__MARINER_PROBE_STDOUT_BEGIN__",
        (
            "GEMINI_MARINER_BEGIN adapter=i2c-1 of=/i2c@1100e000 "
            "address=0x69 registers=06,47 selection_ioctls=1 "
            "bus_syscalls=4 api=write-read"
        ),
        (
            "GEMINI_MARINER_SELECT call=1 request=I2C_SLAVE "
            "address=0x69 result=0 errno=0"
        ),
        (
            "GEMINI_MARINER_WRITE pair=1 bus_call=1 address=0x69 "
            "len=1 pointer=0x06 result=1 errno=0"
        ),
        (
            "GEMINI_MARINER_READ pair=1 bus_call=2 address=0x69 len=1 "
            f"user_pre=0x3c post=0x{post0} result=1 errno=0 "
            f"post_differs_user_pre={'no' if post0 == '3c' else 'yes'}"
        ),
        (
            "GEMINI_MARINER_WRITE pair=2 bus_call=3 address=0x69 "
            "len=1 pointer=0x47 result=1 errno=0"
        ),
        (
            "GEMINI_MARINER_READ pair=2 bus_call=4 address=0x69 len=1 "
            f"user_pre=0xa6 post=0x{post1} result=1 errno=0 "
            f"post_differs_user_pre={'no' if post1 == 'a6' else 'yes'}"
        ),
        (
            f"GEMINI_MARINER_RESULT class={result_class} error_stage=none "
            f"completed_pairs=2 completed_bus_calls=4 select_result=0 "
            f"transfer_result=1 errno=0 user_pre=3c,a6 post={post0},{post1} "
            f"post_diff_user_mask=0x{mask:02x} api=write-read "
            "page_con_access=none"
        ),
        "__MARINER_PROBE_STDOUT_END__",
        "__MARINER_POST_BEGIN__",
        f"boot_id_post={RUNNER.ck.ACCEPTED_BOOT_ID}",
        "cpu_online_post=0-7",
        "cpu_offline_post=8-9",
        "nproc_post=8",
        "handoff_state_post=ready",
        f"i2c6_status_post={i2c_status(18)}",
        "usb_carrier_post=1",
        "usb_operstate_post=up",
        "udc_state_post=configured",
        "__MARINER_POST_END__",
        (
            f"__MARINER_COMPLETE__ probe_rc={probe_rc} invocation_count=1 "
            "helper_removed=yes guard_mode=400:0:0"
        ),
    ]
    return ("\n".join(lines) + "\n").encode()


class MarinerTransferTests(unittest.TestCase):
    def test_remote_template_is_volatile_single_invocation(self) -> None:
        program = RUNNER.REMOTE_TEMPLATE
        self.assertEqual(program.count('\n"$probe_path"\n'), 1)
        self.assertEqual(program.count("( set -C; : >\"$guard_path\" )"), 1)
        self.assertEqual(program.count("trap cleanup EXIT\n"), 1)
        self.assertEqual(program.count("trap on_signal HUP INT TERM PIPE\n"), 1)
        self.assertIn('/bin/busybox rm -f "$stage_path" "$probe_path"', program)
        self.assertIn("prior_voyager_guard=400:0:0", program)
        for token in (
            "/dev/mmc",
            "/dev/watchdog",
            "/dev/mem",
            "/bin/busybox reboot",
            "\nreboot",
            "poweroff",
            "shutdown",
            "i2cset",
            "i2cget",
            "i2cdump",
            "/sys/class/regulator",
            "I2C_RDWR",
            "PAGE_CON",
        ):
            self.assertNotIn(token, program)
        self.assertNotIn("> /sys/devices/system/cpu", program)

    def test_valid_all_complete_classes(self) -> None:
        cases = {
            ("d0", "c0"): "raw-expected-live",
            ("06", "47"): "raw-pointer-echo",
            ("47", "06"): "raw-lag",
            ("05", "06"): "raw-other",
            ("00", "00"): "raw-zero",
            ("3c", "a6"): "raw-other",
            ("11", "22"): "raw-other",
        }
        for posts, wanted in cases.items():
            with self.subTest(posts=posts):
                parsed = RUNNER.validate_transcript(valid_capture(*posts))
                self.assertEqual(parsed["result_class"], wanted)

    def test_old_lag_tuple_cannot_claim_raw_lag(self) -> None:
        original = valid_capture("05", "06")
        self.assertEqual(
            RUNNER.validate_transcript(original)["result_class"], "raw-other"
        )
        false_claim = original.replace(
            b"class=raw-other", b"class=raw-lag", 1
        )
        with self.assertRaises(RUNNER.ContractError):
            RUNNER.validate_transcript(false_claim)

    def test_mutations_fail_closed(self) -> None:
        mutations = {
            "boot-id": (
                RUNNER.ck.ACCEPTED_BOOT_ID.encode(),
                b"01234567-89ab-4def-8123-456789abcdef",
            ),
            "pre-counter": (b"transfer_attempts=14", b"transfer_attempts=13"),
            "post-counter": (b"dma_starts=18", b"dma_starts=17"),
            "voyager-guard": (
                b"prior_voyager_guard=400:0:0",
                b"prior_voyager_guard=600:0:0",
            ),
            "client-count": (b"i2c6_clients=0", b"i2c6_clients=1"),
            "selection": (
                b"address=0x69 result=0 errno=0",
                b"address=0x69 result=-1 errno=16",
            ),
            "bus-call": (b"bus_call=3", b"bus_call=4"),
            "invocation": (b"invocation_count=1", b"invocation_count=2"),
        }
        original = valid_capture()
        for label, (old, new) in mutations.items():
            with self.subTest(label=label):
                changed = original.replace(old, new, 1)
                self.assertNotEqual(changed, original)
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_transcript(changed)

    def test_helper_line_and_section_reordering_fail_closed(self) -> None:
        original = valid_capture()
        lines = original.splitlines()
        write_index = next(
            index
            for index, line in enumerate(lines)
            if line.startswith(b"GEMINI_MARINER_WRITE pair=1 ")
        )
        read_index = next(
            index
            for index, line in enumerate(lines)
            if line.startswith(b"GEMINI_MARINER_READ pair=1 ")
        )
        lines[write_index], lines[read_index] = lines[read_index], lines[write_index]
        with self.assertRaises(RUNNER.ContractError):
            RUNNER.validate_transcript(b"\n".join(lines) + b"\n")

        changed = original.replace(
            b"__MARINER_PRE_BEGIN__", b"__MARINER_TEMP_BEGIN__", 1
        ).replace(
            b"__MARINER_PROBE_STDOUT_BEGIN__", b"__MARINER_PRE_BEGIN__", 1
        ).replace(
            b"__MARINER_TEMP_BEGIN__", b"__MARINER_PROBE_STDOUT_BEGIN__", 1
        )
        with self.assertRaises(RUNNER.ContractError):
            RUNNER.validate_transcript(changed)

    def test_error_and_partial_output_are_rejected(self) -> None:
        original = valid_capture()
        changed = original.replace(
            b"GEMINI_MARINER_SELECT call=1 request=I2C_SLAVE "
            b"address=0x69 result=0 errno=0\n"
            b"GEMINI_MARINER_WRITE pair=1",
            b"GEMINI_MARINER_SELECT call=1 request=I2C_SLAVE "
            b"address=0x69 result=-1 errno=16\n"
            b"GEMINI_MARINER_RESULT class=raw-error error_stage=select "
            b"completed_pairs=0 completed_bus_calls=0 select_result=-1 "
            b"transfer_result=-1 errno=16 user_pre=3c,a6 post=00,00 "
            b"post_diff_user_mask=0x00 api=write-read page_con_access=none\n"
            b"GEMINI_MARINER_WRITE pair=1",
            1,
        )
        with self.assertRaises(RUNNER.ContractError):
            RUNNER.validate_transcript(changed)

    def test_user_prefill_mask_is_only_a_logging_consistency_check(self) -> None:
        parsed = RUNNER.validate_transcript(valid_capture("00", "00"))
        self.assertEqual(parsed["result_class"], "raw-zero")
        with self.assertRaises(RUNNER.ContractError):
            RUNNER.classify_posts("00", "00", 0)

    def test_prior_voyager_capture_is_hash_mode_and_result_gated(self) -> None:
        data = (
            f"boot_id={RUNNER.ck.ACCEPTED_BOOT_ID}\n"
            "GEMINI_VOYAGER_RESULT class=split-pointer-echo completed_pairs=2 "
            "completed_calls=4 ioctl_result=1 errno=0 pre=3c,a6 post=06,47 "
            "post_diff_mask=0x03 stop_between_pointer_and_read=yes "
            "page_con_access=none\n"
            "__VOYAGER_COMPLETE__ probe_rc=2 invocation_count=1 "
            "helper_removed=yes guard_mode=400:0:0\n"
            "transfer_attempts=14 dma_starts=14 nonzero_starts=14 irq_count=14\n"
        ).encode()
        digest = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "prior-voyager.txt"
            path.write_bytes(data)
            path.chmod(0o600)
            with mock.patch.object(
                RUNNER.ck, "PRIOR_VOYAGER_CAPTURE_SHA256", digest
            ):
                self.assertEqual(RUNNER.read_prior_voyager_capture(path.resolve()), data)
                path.chmod(0o644)
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.read_prior_voyager_capture(path.resolve())

    def test_nonexact_prior_capture_and_helper_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            prior = pathlib.Path(temporary) / "prior"
            prior.write_bytes(b"wrong")
            prior.chmod(0o600)
            with self.assertRaises(RUNNER.ContractError):
                RUNNER.read_prior_voyager_capture(prior.resolve())
            helper = pathlib.Path(temporary) / "helper"
            helper.write_bytes(b"wrong")
            with (
                mock.patch.object(RUNNER.ck, "PROBE_BINARY_SHA256", "0" * 64),
                mock.patch.object(RUNNER.ck, "PROBE_BINARY_SIZE", 5),
            ):
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.read_exact_helper(helper.resolve())

    def test_prior_evidence_failure_precedes_host_or_transport(self) -> None:
        arguments = [
            "run-mariner-transfer.py",
            "--interface",
            "en99",
            "--helper",
            "/absolute/helper",
            "--prior-voyager-capture",
            "/absolute/prior",
            "--output-dir",
            "/absolute/output",
        ]
        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(
                RUNNER,
                "read_prior_voyager_capture",
                side_effect=RUNNER.ContractError("prior failed"),
            ),
            mock.patch.object(RUNNER, "verify_host_link") as host,
            mock.patch.object(RUNNER, "run_transport") as transport,
        ):
            self.assertEqual(RUNNER.main(), 2)
            host.assert_not_called()
            transport.assert_not_called()

    def test_capture_precedes_rejection_and_transport_is_single(self) -> None:
        arguments = [
            "run-mariner-transfer.py",
            "--interface",
            "en99",
            "--helper",
            "/absolute/helper",
            "--prior-voyager-capture",
            "/absolute/prior",
            "--output-dir",
            "/absolute/output",
        ]
        events: list[str] = []
        completed = RUNNER.subprocess.CompletedProcess(
            args=["nc"], returncode=0, stdout=b"incomplete\n", stderr=b""
        )

        def record_write(path: pathlib.Path, data: bytes) -> None:
            self.assertEqual(path, pathlib.Path("/private/capture"))
            self.assertIn(b"incomplete\n", data)
            events.append("write")

        def reject_capture(data: bytes) -> dict[str, str]:
            self.assertEqual(data, b"incomplete\n")
            events.append("validate")
            raise RUNNER.ContractError("incomplete")

        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(RUNNER, "read_prior_voyager_capture"),
            mock.patch.object(RUNNER, "read_exact_helper", return_value=b"elf"),
            mock.patch.object(RUNNER, "build_remote_program", return_value=b"program"),
            mock.patch.object(
                RUNNER,
                "prepare_output",
                return_value=pathlib.Path("/private/capture"),
            ),
            mock.patch.object(RUNNER, "verify_host_link"),
            mock.patch.object(
                RUNNER, "run_transport", return_value=completed
            ) as transport,
            mock.patch.object(RUNNER, "write_private", side_effect=record_write),
            mock.patch.object(
                RUNNER, "validate_transcript", side_effect=reject_capture
            ),
        ):
            self.assertEqual(RUNNER.main(), 2)
            transport.assert_called_once_with("en99", b"program")
            self.assertEqual(events, ["write", "validate"])

    def test_output_directory_must_be_new_private_direct_child(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = pathlib.Path(temporary)
            private = repository / RUNNER.PRIVATE_RELATIVE_ROOT
            private.mkdir(parents=True, mode=0o700)
            private.chmod(0o700)
            wanted = private / "mariner-test"
            transcript = RUNNER.prepare_output(repository, wanted.resolve())
            self.assertEqual(
                transcript.resolve(), (wanted / RUNNER.TRANSCRIPT_NAME).resolve()
            )
            self.assertEqual(stat.S_IMODE(wanted.stat().st_mode), 0o700)
            with self.assertRaises(RUNNER.ContractError):
                RUNNER.prepare_output(repository, wanted.resolve())


if __name__ == "__main__":
    unittest.main()
