#!/usr/bin/env python3
"""Device-inert tests for Candidate AP's private live-FDT acquisition."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import os
import pathlib
import re
import stat
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock


sys.dont_write_bytecode = True

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
DECODER_PATH = SCRIPT_DIR / "decode-live-fdt.py"
COLLECTOR_PATH = SCRIPT_DIR / "collect-live-fdt.sh"
SPEC = importlib.util.spec_from_file_location(
    "candidate_ap_live_fdt_decoder",
    DECODER_PATH,
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load Candidate AP live-FDT decoder")
DECODER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DECODER
SPEC.loader.exec_module(DECODER)

CONFIG_SHA256 = "a" * 64
BOOT_ID = "01234567-89ab-4def-8123-456789abcdef"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fdt_fixture(*, magic: int = DECODER.FDT_MAGIC, total_override: int | None = None) -> bytes:
    total = 64
    header_total = total if total_override is None else total_override
    header = struct.pack(
        ">10I",
        magic,
        header_total,
        56,
        64,
        40,
        17,
        16,
        0,
        0,
        8,
    )
    return header + b"\0" * (total - len(header))


def wrapped_base64(data: bytes) -> list[str]:
    return textwrap.wrap(base64.b64encode(data).decode("ascii"), width=76)


def transcript_fixture(
    data: bytes,
    *,
    config_sha256: str = CONFIG_SHA256,
    boot_id_pre: str = BOOT_ID,
    boot_id_post: str = BOOT_ID,
    sha_pre: str | None = None,
    sha_post: str | None = None,
    size_pre: int | None = None,
    size_post: int | None = None,
    payload_lines: list[str] | None = None,
) -> str:
    wanted_hash = digest(data)
    lines = [
        DECODER.HOST_BEGIN,
        "interface=en7",
        "route_interface=en7",
        f"mac={DECODER.HOST_MAC}",
        f"host_address={DECODER.HOST_ADDRESS}",
        f"device_address={DECODER.DEVICE_ADDRESS}",
        "capture_transport=direct-usb-tcp-2323",
        "authentication=none",
        "encryption=none",
        "fdt_source=/sys/firmware/fdt",
        "device_partition_read=no",
        "hardware_write=no",
        "i2c_transaction_or_controller_control=none",
        "regulator_control=none",
        "cpu_hotplug_control=none",
        "watchdog_control=none",
        "reboot_executed=no",
        "power_state_transition_requested=no",
        DECODER.HOST_END,
        DECODER.USB_BANNER,
        "Direct USB link only: synthetic device-inert fixture.",
        "GEMINI-AC-USB# > > >",
        DECODER.CAPTURE_BEGIN,
        f"boot_id_pre={boot_id_pre}",
        f"config_sha256={config_sha256}",
        f"fdt_sha256_pre={sha_pre or wanted_hash}",
        f"fdt_size_pre={len(data) if size_pre is None else size_pre}",
        DECODER.PAYLOAD_BEGIN,
        *(wrapped_base64(data) if payload_lines is None else payload_lines),
        DECODER.PAYLOAD_END,
        f"boot_id_post={boot_id_post}",
        f"fdt_sha256_post={sha_post or wanted_hash}",
        f"fdt_size_post={len(data) if size_post is None else size_post}",
        DECODER.CAPTURE_END,
        "GEMINI-AC-USB# ",
    ]
    return "\n".join(lines) + "\n"


class PrivateRepository:
    def __init__(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="candidate-ap-fdt-")
        self.base = pathlib.Path(self.temporary.name).resolve()
        self.repository = self.base / "repository"
        self.repository.mkdir()
        (self.repository / ".gitignore").write_text(
            "/artifacts/\n",
            encoding="utf-8",
        )
        self.private_root = (
            self.repository / DECODER.PRIVATE_RELATIVE_ROOT
        )
        self.private_root.mkdir(parents=True)
        self.private_root.chmod(0o700)
        self.counter = 0

    def close(self) -> None:
        self.temporary.cleanup()

    def new_case(
        self,
        transcript: str | bytes | None = None,
    ) -> pathlib.Path:
        self.counter += 1
        output = self.private_root / f"case-{self.counter}"
        DECODER.prepare_output_dir(self.repository, output)
        if transcript is not None:
            path = output / DECODER.TRANSCRIPT_NAME
            if isinstance(transcript, str):
                path.write_text(transcript, encoding="ascii")
            else:
                path.write_bytes(transcript)
            path.chmod(0o600)
        return output


class LiveFdtCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private = PrivateRepository()
        self.addCleanup(self.private.close)
        self.data = fdt_fixture()

    def assert_rejected(
        self,
        transcript: str | bytes,
        expected_config: str = CONFIG_SHA256,
    ) -> None:
        output = self.private.new_case(transcript)
        with self.assertRaises((OSError, ValueError)):
            DECODER.decode_capture(
                self.private.repository,
                output,
                expected_config,
            )
        self.assertFalse((output / DECODER.FDT_NAME).exists())

    def test_exact_capture_is_decoded_privately(self) -> None:
        output = self.private.new_case(transcript_fixture(self.data))
        result = DECODER.decode_capture(
            self.private.repository,
            output,
            CONFIG_SHA256,
        )
        self.assertEqual(result.boot_id, BOOT_ID)
        self.assertEqual(result.live_fdt_sha256, digest(self.data))
        self.assertEqual(result.live_fdt_size, len(self.data))
        fdt = output / DECODER.FDT_NAME
        self.assertEqual(fdt.read_bytes(), self.data)
        self.assertEqual(stat.S_IMODE(fdt.stat().st_mode), 0o600)
        self.assertEqual(
            stat.S_IMODE((output / DECODER.TRANSCRIPT_NAME).stat().st_mode),
            0o600,
        )

    def test_interactive_prompt_before_leading_newline_is_accepted(self) -> None:
        text = transcript_fixture(self.data)
        self.assertIn(
            "GEMINI-AC-USB# > > >\n" + DECODER.CAPTURE_BEGIN + "\n",
            text,
        )
        output = self.private.new_case(text)
        result = DECODER.decode_capture(
            self.private.repository,
            output,
            CONFIG_SHA256,
        )
        self.assertEqual(result.boot_id, BOOT_ID)

    def test_cli_emits_only_boot_id_hash_and_size(self) -> None:
        output = self.private.new_case(transcript_fixture(self.data))
        result = subprocess.run(
            [
                sys.executable,
                os.fspath(DECODER_PATH),
                "decode",
                "--repository",
                os.fspath(self.private.repository),
                "--output-dir",
                os.fspath(output),
                "--expected-config-sha256",
                CONFIG_SHA256,
            ],
            check=False,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                f"boot_id={BOOT_ID}",
                f"live_fdt_sha256={digest(self.data)}",
                f"live_fdt_size={len(self.data)}",
            ],
        )
        self.assertEqual(result.stderr, "")

    def test_markers_must_be_unique_exact_and_ordered(self) -> None:
        valid = transcript_fixture(self.data)
        cases = {
            "missing": valid.replace(DECODER.PAYLOAD_BEGIN + "\n", "", 1),
            "duplicate": valid.replace(
                DECODER.PAYLOAD_BEGIN + "\n",
                DECODER.PAYLOAD_BEGIN + "\n" + DECODER.PAYLOAD_BEGIN + "\n",
                1,
            ),
            "out-of-order": valid.replace(
                DECODER.PAYLOAD_BEGIN,
                "__TEMP_MARKER__",
                1,
            )
            .replace(DECODER.PAYLOAD_END, DECODER.PAYLOAD_BEGIN, 1)
            .replace("__TEMP_MARKER__", DECODER.PAYLOAD_END, 1),
            "prompt-contaminated": valid.replace(
                DECODER.CAPTURE_BEGIN,
                "GEMINI-AC-USB# " + DECODER.CAPTURE_BEGIN,
                1,
            ),
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                self.assert_rejected(text)

    def test_capture_metadata_grammar_is_exact(self) -> None:
        valid = transcript_fixture(self.data)
        cases = (
            valid.replace(
                "config_sha256=",
                "unexpected=value\nconfig_sha256=",
                1,
            ),
            valid.replace("fdt_size_pre=", "fdt_size_post=", 1),
            valid.replace("boot_id_post=", "boot_id_pre=", 1),
        )
        for text in cases:
            with self.subTest():
                self.assert_rejected(text)

    def test_invalid_base64_alphabet_padding_and_wrapping_are_rejected(self) -> None:
        payload = wrapped_base64(self.data)
        invalid = (
            ["!" + payload[0][1:], *payload[1:]],
            [*payload[:-1], payload[-1][:-1]],
            ["".join(payload)],
            [payload[0] + "=", *payload[1:]],
            [payload[0], "", *payload[1:]],
        )
        for lines in invalid:
            with self.subTest(lines=lines):
                self.assert_rejected(
                    transcript_fixture(self.data, payload_lines=lines)
                )

    def test_remote_and_local_hashes_and_sizes_must_all_match(self) -> None:
        cases = (
            transcript_fixture(self.data, sha_pre="0" * 64),
            transcript_fixture(self.data, sha_post="0" * 64),
            transcript_fixture(self.data, size_pre=len(self.data) + 1),
            transcript_fixture(self.data, size_post=len(self.data) + 1),
            transcript_fixture(
                self.data,
                payload_lines=wrapped_base64(self.data[:-1] + b"\1"),
            ),
        )
        for text in cases:
            with self.subTest():
                self.assert_rejected(text)

    def test_expected_ap_configuration_is_mandatory_and_exact(self) -> None:
        self.assert_rejected(
            transcript_fixture(self.data, config_sha256="b" * 64)
        )
        self.assert_rejected(
            transcript_fixture(self.data),
            expected_config="not-a-sha256",
        )

    def test_boot_id_must_be_canonical_stable_uuid(self) -> None:
        cases = (
            transcript_fixture(self.data, boot_id_pre="not-a-uuid"),
            transcript_fixture(
                self.data,
                boot_id_post="fedcba98-7654-4abc-8123-fedcba987654",
            ),
            transcript_fixture(self.data, boot_id_pre=BOOT_ID.upper()),
            transcript_fixture(
                self.data,
                boot_id_pre="01234567-89ab-0def-8123-456789abcdef",
            ),
            transcript_fixture(
                self.data,
                boot_id_pre="01234567-89ab-4def-7123-456789abcdef",
            ),
        )
        for text in cases:
            with self.subTest():
                self.assert_rejected(text)

    def test_fdt_magic_totalsize_and_bounds_are_checked(self) -> None:
        malformed = (
            fdt_fixture(magic=0xDEADBEEF),
            fdt_fixture(total_override=63),
            self.data[:39],
        )
        for data in malformed:
            with self.subTest(length=len(data)):
                self.assert_rejected(transcript_fixture(data))

    def test_exact_usb_banner_and_host_route_contract_are_required(self) -> None:
        valid = transcript_fixture(self.data)
        cases = (
            valid.replace(DECODER.USB_BANNER + "\n", "", 1),
            valid.replace(f"mac={DECODER.HOST_MAC}", "mac=00:00:00:00:00:00"),
            valid.replace("route_interface=en7", "route_interface=en8"),
            valid.replace("hardware_write=no", "hardware_write=yes"),
        )
        for text in cases:
            with self.subTest():
                self.assert_rejected(text)

    def test_ascii_and_control_framing_is_strict(self) -> None:
        valid = transcript_fixture(self.data).encode("ascii")
        for raw in (
            valid.replace(b"\n", b"\r\n", 1),
            valid + b"\0",
            valid + b"\xff",
        ):
            with self.subTest():
                self.assert_rejected(raw)

    def test_output_must_be_new_private_direct_child(self) -> None:
        relative = pathlib.Path("artifacts/runtime-captures/case")
        with self.assertRaises(ValueError):
            DECODER.prepare_output_dir(self.private.repository, relative)

        nested_parent = self.private.private_root / "nested"
        nested_parent.mkdir(mode=0o700)
        with self.assertRaises(ValueError):
            DECODER.prepare_output_dir(
                self.private.repository,
                nested_parent / "case",
            )

        existing = self.private.private_root / "existing"
        existing.mkdir(mode=0o700)
        with self.assertRaises(ValueError):
            DECODER.prepare_output_dir(self.private.repository, existing)

        symlink = self.private.private_root / "symlink"
        symlink.symlink_to(existing, target_is_directory=True)
        with self.assertRaises(ValueError):
            DECODER.prepare_output_dir(self.private.repository, symlink)

    def test_private_root_and_gitignore_are_enforced(self) -> None:
        self.private.private_root.chmod(0o755)
        output = self.private.private_root / "wrong-mode"
        with self.assertRaises(ValueError):
            DECODER.prepare_output_dir(self.private.repository, output)
        self.private.private_root.chmod(0o700)

        (self.private.repository / ".gitignore").write_text(
            "/something-else/\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            DECODER.prepare_output_dir(
                self.private.repository,
                self.private.private_root / "not-ignored",
            )

    def test_transcript_must_be_regular_owned_mode_0600(self) -> None:
        output = self.private.new_case(transcript_fixture(self.data))
        transcript = output / DECODER.TRANSCRIPT_NAME
        transcript.chmod(0o644)
        with self.assertRaises(ValueError):
            DECODER.decode_capture(
                self.private.repository,
                output,
                CONFIG_SHA256,
            )

        output = self.private.new_case()
        transcript = output / DECODER.TRANSCRIPT_NAME
        target = output / "target"
        target.write_text(transcript_fixture(self.data), encoding="ascii")
        target.chmod(0o600)
        transcript.symlink_to(target)
        with self.assertRaises(ValueError):
            DECODER.decode_capture(
                self.private.repository,
                output,
                CONFIG_SHA256,
            )

    def test_decoded_fdt_is_never_overwritten(self) -> None:
        for kind in ("regular", "symlink"):
            with self.subTest(kind=kind):
                output = self.private.new_case(transcript_fixture(self.data))
                fdt = output / DECODER.FDT_NAME
                if kind == "regular":
                    fdt.write_bytes(b"existing")
                else:
                    target = output / "target-fdt"
                    target.write_bytes(b"existing")
                    fdt.symlink_to(target)
                with self.assertRaises(ValueError):
                    DECODER.decode_capture(
                        self.private.repository,
                        output,
                        CONFIG_SHA256,
                    )
                self.assertNotEqual(fdt.read_bytes(), self.data)

    def test_failed_post_write_readback_removes_decoded_fdt(self) -> None:
        output = self.private.new_case(transcript_fixture(self.data))
        fdt = output / DECODER.FDT_NAME
        real_digest = DECODER.digest
        calls = 0

        def mismatching_digest(data: bytes) -> str:
            nonlocal calls
            calls += 1
            if calls == 2:
                return "0" * 64
            return real_digest(data)

        with mock.patch.object(DECODER, "digest", side_effect=mismatching_digest):
            with self.assertRaises(ValueError):
                DECODER.decode_capture(
                    self.private.repository,
                    output,
                    CONFIG_SHA256,
                )
        self.assertFalse(fdt.exists())

    def test_collector_remote_scope_is_read_only_and_usb_bound(self) -> None:
        source = COLLECTOR_PATH.read_text(encoding="utf-8")
        self.assertIn("umask 077", source)
        self.assertIn("readonly HOST_MAC=42:00:15:19:82:00", source)
        self.assertIn('[[ "$route_interface" == "$interface" ]]', source)
        self.assertIn("ping -b \"$interface\"", source)
        self.assertIn("/bin/busybox sh <<'__AP_LIVE_FDT_REMOTE__'", source)
        self.assertIn('/bin/busybox base64 "$fdt"', source)
        self.assertNotIn("dtc -I fs", source)

        remote = source.split(
            "/bin/busybox sh <<'__AP_LIVE_FDT_REMOTE__'",
            1,
        )[1].split("\n__AP_LIVE_FDT_REMOTE__\n", 1)[0]
        forbidden = (
            "/dev/mmc",
            "/dev/mem",
            "/sys/power",
            "/sys/devices/system/cpu",
            "/dev/watchdog",
            "reboot",
            "shutdown",
            "poweroff",
            "i2cget",
            "i2cset",
            "devmem",
            "\ndd ",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, remote)
        allowed_paths = (
            "/sys/firmware/fdt",
            "/proc/config.gz",
            "/proc/sys/kernel/random/boot_id",
        )
        for path in allowed_paths:
            self.assertIn(path, remote)

    def test_collector_source_pins_decoder_before_network_probe(self) -> None:
        source = COLLECTOR_PATH.read_text(encoding="utf-8")
        match = re.search(
            r"^readonly DECODER_SHA256=([0-9a-f]{64})$",
            source,
            re.MULTILINE,
        )
        self.assertIsNotNone(match)
        decoder_data = DECODER_PATH.read_bytes()
        self.assertEqual(match.group(1), digest(decoder_data))
        self.assertNotEqual(match.group(1), digest(decoder_data + b"\n"))
        pin_check = source.index("source-pinned live-FDT decoder changed")
        self.assertLess(pin_check, source.index('mac="$(ifconfig'))
        self.assertLess(pin_check, source.index("ping -b"))
        self.assertRegex(
            source,
            r"for command in [^\n]*\\\n\tshasum; do",
        )
        self.assertIn("awk cat chmod", source)

    def test_decoder_source_does_not_publish_private_values_or_paths(self) -> None:
        source = DECODER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("/private/tmp/", source)
        self.assertNotIn("serialno=", source)
        self.assertNotIn("bootargs=", source)
        self.assertNotIn("atag,cmdline", source)
        expected_prints = {
            'print(f"boot_id={result.boot_id}")',
            'print(f"live_fdt_sha256={result.live_fdt_sha256}")',
            'print(f"live_fdt_size={result.live_fdt_size}")',
        }
        self.assertTrue(
            expected_prints.issubset(
                {line.strip() for line in source.splitlines()}
            )
        )


if __name__ == "__main__":
    unittest.main()
