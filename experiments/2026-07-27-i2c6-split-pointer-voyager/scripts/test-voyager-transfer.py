#!/usr/bin/env python3
"""Offline contract and mutation tests for Voyager's volatile runner."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
RUNNER_PATH = SCRIPT_DIR / "run-voyager-transfer.py"
SPEC = importlib.util.spec_from_file_location("voyager_transfer", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot import Voyager transfer runner")
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
    probe_rc = "0" if result_class == "split-expected-live" else "2"
    lines = [
        RUNNER.USB_BANNER,
        "__VOYAGER_GATE_BEGIN__",
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
        f"i2c6_status_pre={i2c_status(10)}",
        "i2c6_adapter=i2c-1",
        "i2c6_of=/sys/firmware/devicetree/base/i2c@1100e000",
        "i2c6_clients=0",
        "prior_photon_guard=400:0:0",
        "prior_photon_begin=1",
        "prior_photon_pre=6",
        "prior_photon_result=post-all-equal-pre",
        "prior_photon_total=8",
        "prior_kepler_guard=400:0:0",
        "usb0_address=42:00:15:19:82:01",
        "usb0_carrier=1",
        "usb0_operstate=up",
        "usb0_ipv4_exact=1",
        "udc_name=11271000.usb",
        "udc_state=configured",
        "usb_service_count=1",
        "usb_ready_count=1",
        "__VOYAGER_GATE_END__",
        "__VOYAGER_GATE_PASS__",
        (
            f"__VOYAGER_TRANSFER_PASS__ size={RUNNER.ck.PROBE_BINARY_SIZE} "
            f"sha256={RUNNER.ck.PROBE_BINARY_SHA256} mode=500:0:0 "
            "path=/run/voyager-probe"
        ),
        "__VOYAGER_PRE_BEGIN__",
        f"boot_id_pre={RUNNER.ck.ACCEPTED_BOOT_ID}",
        "cpu_online_pre=0-7",
        "cpu_offline_pre=8-9",
        "nproc_pre=8",
        "handoff_state_pre=ready",
        f"i2c6_status_pre={i2c_status(10)}",
        "usb_carrier_pre=1",
        "usb_operstate_pre=up",
        "udc_state_pre=configured",
        "__VOYAGER_PRE_END__",
        "__VOYAGER_PROBE_STDOUT_BEGIN__",
        (
            "GEMINI_VOYAGER_BEGIN adapter=i2c-1 of=/i2c@1100e000 "
            "address=0x69 registers=06,47 pairs=2 calls=4 layout=split"
        ),
        (
            "GEMINI_VOYAGER_TX pair=1 call=1 address=0x69 flags=0x0000 "
            "len=1 pointer=0x06 result=1 errno=0"
        ),
        (
            "GEMINI_VOYAGER_RX pair=1 call=2 address=0x69 flags=0x0001 "
            f"len=1 pre=0x3c post=0x{post0} result=1 errno=0 "
            f"post_differs_pre={'no' if post0 == '3c' else 'yes'}"
        ),
        (
            "GEMINI_VOYAGER_TX pair=2 call=3 address=0x69 flags=0x0000 "
            "len=1 pointer=0x47 result=1 errno=0"
        ),
        (
            "GEMINI_VOYAGER_RX pair=2 call=4 address=0x69 flags=0x0001 "
            f"len=1 pre=0xa6 post=0x{post1} result=1 errno=0 "
            f"post_differs_pre={'no' if post1 == 'a6' else 'yes'}"
        ),
        (
            f"GEMINI_VOYAGER_RESULT class={result_class} completed_pairs=2 "
            f"completed_calls=4 ioctl_result=1 errno=0 pre=3c,a6 "
            f"post={post0},{post1} post_diff_mask=0x{mask:02x} "
            "stop_between_pointer_and_read=yes page_con_access=none"
        ),
        "__VOYAGER_PROBE_STDOUT_END__",
        "__VOYAGER_POST_BEGIN__",
        f"boot_id_post={RUNNER.ck.ACCEPTED_BOOT_ID}",
        "cpu_online_post=0-7",
        "cpu_offline_post=8-9",
        "nproc_post=8",
        "handoff_state_post=ready",
        f"i2c6_status_post={i2c_status(14)}",
        "usb_carrier_post=1",
        "usb_operstate_post=up",
        "udc_state_post=configured",
        "__VOYAGER_POST_END__",
        (
            f"__VOYAGER_COMPLETE__ probe_rc={probe_rc} invocation_count=1 "
            "helper_removed=yes guard_mode=400:0:0"
        ),
    ]
    return ("\n".join(lines) + "\n").encode("ascii")


class VoyagerRunnerContracts(unittest.TestCase):
    def test_exact_pins(self) -> None:
        RUNNER.ck.require_pins()
        self.assertEqual(
            RUNNER.ck.ACCEPTED_BOOT_ID,
            "cdd23c48-0bd3-4980-95c8-5e054be860d9",
        )
        self.assertEqual(RUNNER.ck.PRE_COUNTER, 10)
        self.assertEqual(RUNNER.ck.POST_COUNTER, 14)
        self.assertEqual(RUNNER.ck.PROBE_BINARY_SIZE, 537_584)
        self.assertEqual(RUNNER.I2C_PRE_STATUS, i2c_status(10))

    def test_remote_payload_roundtrip_and_one_invocation(self) -> None:
        helper = b"fixed-voyager-test-payload"
        digest = hashlib.sha256(helper).hexdigest()
        with (
            mock.patch.object(RUNNER.ck, "PROBE_BINARY_SHA256", digest),
            mock.patch.object(RUNNER.ck, "PROBE_BINARY_SIZE", len(helper)),
        ):
            program = RUNNER.build_remote_program(helper).decode("ascii")
        payload = program.split(
            "<<'__VOYAGER_PAYLOAD__'\n", 1
        )[1].split("\n__VOYAGER_PAYLOAD__\n", 1)[0]
        self.assertEqual(base64.b64decode(payload), helper)
        self.assertEqual(program.count('\n"$probe_path"\n'), 1)
        self.assertLess(
            program.index("__VOYAGER_GATE_PASS__"),
            program.index('\n"$probe_path"\n'),
        )
        self.assertLess(
            program.index("( set -C; : >\"$guard_path\" )"),
            program.index('\n"$probe_path"\n'),
        )
        self.assertIn(
            f'require_equal "$i2c_status_pre" "{RUNNER.I2C_PRE_STATUS}" '
            "i2c-pre-exact",
            program,
        )
        self.assertEqual(program.count("prior-photon-exact-marker"), 1)

    def test_remote_forbidden_scope(self) -> None:
        program = RUNNER.REMOTE_TEMPLATE
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
        ):
            self.assertNotIn(token, program)
        self.assertNotIn("> /sys/devices/system/cpu", program)
        self.assertNotIn("PAGE_CON", program)

    def test_disconnect_and_signal_cleanup_is_fail_closed(self) -> None:
        program = RUNNER.REMOTE_TEMPLATE
        self.assertIn(
            '/bin/busybox rm -f "$stage_path" "$probe_path"', program
        )
        self.assertEqual(program.count("trap cleanup EXIT\n"), 1)
        self.assertEqual(program.count("trap on_signal HUP INT TERM PIPE\n"), 1)
        self.assertEqual(program.count("trap - HUP INT TERM PIPE\n"), 1)
        self.assertIn("on_signal() {\n\ttrap - HUP INT TERM PIPE\n\texit 91\n}", program)
        self.assertNotIn("trap cleanup EXIT HUP", program)
        self.assertEqual(
            program.count('/bin/busybox rm -f "$probe_path"\n'), 1
        )
        self.assertEqual(
            program.count(
                '[ ! -e "$probe_path" ] && [ ! -L "$probe_path" ] '
                "|| abort probe-cleanup"
            ),
            1,
        )

    def test_valid_all_complete_classes(self) -> None:
        cases = {
            ("3c", "a6"): "split-all-equal-pre",
            ("3c", "d0"): "split-mixed-equal-pre",
            ("d0", "c0"): "split-expected-live",
            ("06", "47"): "split-pointer-echo",
            ("33", "33"): "split-stable-other",
            ("11", "22"): "split-unstable-other",
        }
        for posts, wanted in cases.items():
            with self.subTest(posts=posts):
                parsed = RUNNER.validate_transcript(valid_capture(*posts))
                self.assertEqual(parsed["result_class"], wanted)

    def test_mutations_fail_closed(self) -> None:
        mutations = {
            b"boot-id": (
                RUNNER.ck.ACCEPTED_BOOT_ID.encode(),
                b"01234567-89ab-4def-8123-456789abcdef",
                1,
            ),
            b"pre-counter": (b"transfer_attempts=10", b"transfer_attempts=9", 1),
            b"post-counter": (b"dma_starts=14", b"dma_starts=13", 1),
            b"photon-result": (
                b"prior_photon_result=post-all-equal-pre",
                b"prior_photon_result=post-reference-tuple",
                1,
            ),
            b"photon-guard": (
                b"prior_photon_guard=400:0:0",
                b"prior_photon_guard=600:0:0",
                1,
            ),
            b"kepler-guard": (
                b"prior_kepler_guard=400:0:0",
                b"prior_kepler_guard=600:0:0",
                1,
            ),
            b"invocation": (b"invocation_count=1", b"invocation_count=2", 1),
        }
        original = valid_capture()
        for label, (old, new, count) in mutations.items():
            with self.subTest(label=label):
                changed = original.replace(old, new, count)
                self.assertNotEqual(changed, original)
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_transcript(changed)

    def test_section_and_helper_line_reordering_fail_closed(self) -> None:
        original = valid_capture()
        section_reordered = original.replace(
            b"__VOYAGER_PRE_BEGIN__", b"__VOYAGER_TEMP_BEGIN__", 1
        ).replace(
            b"__VOYAGER_PROBE_STDOUT_BEGIN__", b"__VOYAGER_PRE_BEGIN__", 1
        ).replace(
            b"__VOYAGER_TEMP_BEGIN__", b"__VOYAGER_PROBE_STDOUT_BEGIN__", 1
        )
        with self.assertRaises(RUNNER.ContractError):
            RUNNER.validate_transcript(section_reordered)

        lines = original.splitlines()
        tx_index = next(
            index
            for index, line in enumerate(lines)
            if line.startswith(b"GEMINI_VOYAGER_TX pair=1 ")
        )
        rx_index = next(
            index
            for index, line in enumerate(lines)
            if line.startswith(b"GEMINI_VOYAGER_RX pair=1 ")
        )
        lines[tx_index], lines[rx_index] = lines[rx_index], lines[tx_index]
        helper_reordered = b"\n".join(lines) + b"\n"
        with self.assertRaises(RUNNER.ContractError):
            RUNNER.validate_transcript(helper_reordered)

    def test_incomplete_tx_and_rx_results_are_intentionally_rejected(self) -> None:
        original = valid_capture()
        begin = original.index(b"__VOYAGER_PROBE_STDOUT_BEGIN__\n")
        end = original.index(b"__VOYAGER_PROBE_STDOUT_END__\n")
        prefix = original[:begin] + b"__VOYAGER_PROBE_STDOUT_BEGIN__\n"
        suffix = original[end:]
        error_sequences = (
            (
                b"GEMINI_VOYAGER_BEGIN adapter=i2c-1 of=/i2c@1100e000 "
                b"address=0x69 registers=06,47 pairs=2 calls=4 layout=split\n"
                b"GEMINI_VOYAGER_TX pair=1 call=1 address=0x69 flags=0x0000 "
                b"len=1 pointer=0x06 result=-1 errno=5\n"
                b"GEMINI_VOYAGER_RESULT class=tx-result-not-one "
                b"completed_pairs=0 completed_calls=0 ioctl_result=-1 errno=5 "
                b"pre=3c,a6 post=00,00 post_diff_mask=0x00 "
                b"stop_between_pointer_and_read=yes page_con_access=none\n"
            ),
            (
                b"GEMINI_VOYAGER_BEGIN adapter=i2c-1 of=/i2c@1100e000 "
                b"address=0x69 registers=06,47 pairs=2 calls=4 layout=split\n"
                b"GEMINI_VOYAGER_TX pair=1 call=1 address=0x69 flags=0x0000 "
                b"len=1 pointer=0x06 result=1 errno=0\n"
                b"GEMINI_VOYAGER_RX pair=1 call=2 address=0x69 flags=0x0001 "
                b"len=1 pre=0x3c post=0x3c result=-1 errno=5 "
                b"post_differs_pre=no\n"
                b"GEMINI_VOYAGER_RESULT class=rx-result-not-one "
                b"completed_pairs=0 completed_calls=1 ioctl_result=-1 errno=5 "
                b"pre=3c,a6 post=3c,00 post_diff_mask=0x00 "
                b"stop_between_pointer_and_read=yes page_con_access=none\n"
            ),
        )
        for output in error_sequences:
            with self.subTest(output=output.splitlines()[-1]):
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.validate_transcript(prefix + output + suffix)

    def test_nonexact_helper_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "not-voyager"
            path.write_bytes(b"wrong")
            with self.assertRaises(RUNNER.ContractError):
                RUNNER.read_exact_helper(path.resolve())

    def test_prior_kepler_capture_is_hash_mode_and_result_gated(self) -> None:
        data = (
            f"boot_id={RUNNER.ck.ACCEPTED_BOOT_ID}\n"
            "GEMINI_KEPLER_RESULT class=split-stable-other completed_pairs=2 "
            "completed_calls=4 ioctl_result=1 errno=0 pre=a5,5a post=05,05 "
            "post_diff_mask=0x03 stop_between_pointer_and_read=yes "
            "page_con_access=none\n"
            "__KEPLER_COMPLETE__ probe_rc=2 invocation_count=1 "
            "helper_removed=yes guard_mode=400:0:0\n"
            "transfer_attempts=10 dma_starts=10 nonzero_starts=10 irq_count=10\n"
        ).encode()
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "prior-kepler.txt"
            path.write_bytes(data)
            path.chmod(0o600)
            with mock.patch.object(
                RUNNER.ck,
                "PRIOR_KEPLER_CAPTURE_SHA256",
                hashlib.sha256(data).hexdigest(),
            ):
                self.assertEqual(RUNNER.read_prior_kepler_capture(path.resolve()), data)
                path.write_bytes(data + b"tamper\n")
                with self.assertRaises(RUNNER.ContractError):
                    RUNNER.read_prior_kepler_capture(path.resolve())

    def test_main_uses_one_transport(self) -> None:
        capture = valid_capture()
        completed = subprocess.CompletedProcess(
            args=["nc"], returncode=0, stdout=capture, stderr=b""
        )
        with (
            mock.patch.object(sys, "argv", ["runner", "--interface", "en7",
                                           "--helper", "/exact/helper",
                                           "--prior-kepler-capture", "/exact/prior",
                                           "--output-dir", "/exact/output"]),
            mock.patch.object(
                RUNNER, "read_prior_kepler_capture", return_value=b"prior"
            ),
            mock.patch.object(RUNNER, "read_exact_helper", return_value=b"helper"),
            mock.patch.object(RUNNER, "build_remote_program", return_value=b"remote"),
            mock.patch.object(RUNNER, "prepare_output",
                              return_value=pathlib.Path("/capture/transcript")),
            mock.patch.object(RUNNER, "verify_host_link"),
            mock.patch.object(RUNNER, "run_transport", return_value=completed) as run,
            mock.patch.object(RUNNER, "write_private"),
        ):
            self.assertEqual(RUNNER.main(), 0)
        run.assert_called_once_with("en7", b"remote")

    def test_main_preserves_raw_capture_before_rejecting_incomplete_result(self) -> None:
        events: list[str] = []
        completed = subprocess.CompletedProcess(
            args=["nc"], returncode=0, stdout=b"incomplete\n", stderr=b""
        )

        def write_first(path: pathlib.Path, data: bytes) -> None:
            del path, data
            events.append("write")

        def reject_after_write(data: bytes) -> dict[str, str]:
            del data
            events.append("validate")
            raise RUNNER.ContractError("incomplete helper result")

        with (
            mock.patch.object(sys, "argv", ["runner", "--interface", "en7",
                                           "--helper", "/exact/helper",
                                           "--prior-kepler-capture", "/exact/prior",
                                           "--output-dir", "/exact/output"]),
            mock.patch.object(
                RUNNER, "read_prior_kepler_capture", return_value=b"prior"
            ),
            mock.patch.object(RUNNER, "read_exact_helper", return_value=b"helper"),
            mock.patch.object(RUNNER, "build_remote_program", return_value=b"remote"),
            mock.patch.object(RUNNER, "prepare_output",
                              return_value=pathlib.Path("/capture/transcript")),
            mock.patch.object(RUNNER, "verify_host_link"),
            mock.patch.object(RUNNER, "run_transport", return_value=completed),
            mock.patch.object(RUNNER, "write_private", side_effect=write_first),
            mock.patch.object(
                RUNNER, "validate_transcript", side_effect=reject_after_write
            ),
        ):
            self.assertEqual(RUNNER.main(), 2)
        self.assertEqual(events, ["write", "validate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
