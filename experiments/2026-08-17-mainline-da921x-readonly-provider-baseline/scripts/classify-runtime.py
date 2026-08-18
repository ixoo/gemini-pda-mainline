#!/usr/bin/env python3
"""Classify and sanitize one private read-only provider runtime capture."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


BEGIN = "__DA921X_LKRO_DMESG_BASE64_BEGIN__"
END = "__DA921X_LKRO_DMESG_BASE64_END__"
EXPECTED_RELEASE = "7.1.3-gemini-da921x-lkro"
PROVIDER = re.compile(
    r"da921x-observer-v1 event=bound valid=(?P<valid>\d+) "
    r"identity_reads=(?P<identity>\d+) providers=(?P<providers>\d+) "
    r"provider_read_attempts=(?P<attempts>\d+) "
    r"provider_read_completed=(?P<completed>\d+) "
    r"register_data_writes=(?P<writes>\d+) "
    r"buck0_selector=(?P<s0>\d+) buck0_uv=(?P<uv0>\d+) buck0_enabled=(?P<e0>\d+) "
    r"buck1_selector=(?P<s1>\d+) buck1_uv=(?P<uv1>\d+) buck1_enabled=(?P<e1>\d+)"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def exact_field(lines: list[str], name: str) -> str:
    values = [line.removeprefix(f"{name}=") for line in lines if line.startswith(f"{name}=")]
    require(len(values) == 1, f"field count changed: {name}")
    return values[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()

    text = args.capture.read_text(encoding="ascii", errors="strict")
    lines = text.splitlines()
    require(lines.count("__DA921X_LKRO_BEGIN__") == 1, "probe begin marker changed")
    require(lines.count("__DA921X_LKRO_END__") == 1, "probe end marker changed")
    require(lines.count(BEGIN) == 1 and lines.count(END) == 1, "dmesg markers changed")
    begin = lines.index(BEGIN)
    end = lines.index(END)
    require(begin < end, "dmesg marker order changed")
    dmesg = base64.b64decode("".join(lines[begin + 1:end]), validate=True).decode(
        "utf-8", errors="replace"
    )

    require(exact_field(lines, "kernel_release") == EXPECTED_RELEASE, "kernel identity mismatch")
    require(exact_field(lines, "architecture") == "aarch64", "architecture mismatch")
    require(exact_field(lines, "cpu_possible") == "0-9", "possible CPU set changed")
    require(exact_field(lines, "cpu_present") == "0-9", "present CPU set changed")
    require(exact_field(lines, "cpu_online") == "0-7", "online CPU set changed")
    require(exact_field(lines, "cpu_offline") == "8-9", "offline CPU set changed")
    require("maxcpus=8" in exact_field(lines, "cmdline").split(), "maxcpus=8 is absent")
    boot_hash = exact_field(lines, "boot_id_sha256")
    require(re.fullmatch(r"[0-9a-f]{64}", boot_hash) is not None, "boot hash malformed")
    require(exact_field(lines, "post_probe_boot_id_sha256") == boot_hash, "boot changed during probe")
    require(int(exact_field(lines, "udc_devices")) >= 1, "USB gadget controller is absent")
    require(int(exact_field(lines, "gpio_matrix_keyboards")) >= 1, "polling keyboard is absent")
    require(int(exact_field(lines, "da921x_i2c_clients")) == 1, "DA921x client count changed")
    require(int(exact_field(lines, "block_mounts")) == 0, "block device unexpectedly mounted")

    matches = list(PROVIDER.finditer(dmesg))
    require(len(matches) == 1, "exactly one complete DA921x bound record is required")
    values = {name: int(value) for name, value in matches[0].groupdict().items()}
    require(values["valid"] == 1, "provider record is invalid")
    require(values["identity"] == 14, "identity read count changed")
    require(values["providers"] == 2, "provider count changed")
    require(values["attempts"] == 4 and values["completed"] == 4,
            "provider read accounting changed")
    require(values["writes"] == 0, "DA921x register-data write observed")
    for buck in (0, 1):
        selector = values[f"s{buck}"]
        microvolts = values[f"uv{buck}"]
        enabled = values[f"e{buck}"]
        require(0 <= selector <= 127, f"buck{buck} selector is invalid")
        require(microvolts == 300_000 + selector * 10_000,
                f"buck{buck} voltage does not match selector")
        require(microvolts <= 1_570_000, f"buck{buck} voltage is out of range")
        require(enabled in (0, 1), f"buck{buck} enable state is invalid")
    require("da921x-observer-v1 event=failed-probe" not in dmesg, "provider failed-probe event found")
    require("da921x-observer-v1 event=unbind" not in dmesg, "provider unbound during capture")
    for fatal in ("Kernel panic", "Internal error:", "Oops:"):
        require(fatal not in dmesg, f"kernel fault marker found: {fatal}")

    print("runtime_classification=success-read-only-provider")
    print(f"kernel_release={EXPECTED_RELEASE}")
    print("cpu_possible=0-9")
    print("cpu_present=0-9")
    print("cpu_online=0-7")
    print("cpu_offline=8-9")
    print("maxcpus=8")
    print("LK_devinfo_handoff=ready-by-bound-provider")
    print("I2C6_access_controller=ready-by-bound-client")
    print("DA921x_event=bound")
    print("DA921x_valid=1")
    print("DA921x_identity_reads=14")
    print("DA921x_providers=2")
    print("DA921x_provider_read_attempts=4")
    print("DA921x_provider_read_completed=4")
    print("DA921x_register_data_writes=0")
    for buck in (0, 1):
        print(f"buck{buck}_selector={values[f's{buck}']}")
        print(f"buck{buck}_uv={values[f'uv{buck}']}")
        print(f"buck{buck}_enabled={values[f'e{buck}']}")
    print("USB_gadget=present")
    print("netcat_probe=passed")
    print("polling_keyboard=present")
    print("block_mounts=0")
    print("kernel_fault_markers=absent")
    print("CPU8_CPU9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
