#!/usr/bin/env python3
"""Classify and sanitize one private DA921x preflight/ledger capture."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


PROBE_BEGIN = "__DA921X_PREFLIGHT_BEGIN__"
PROBE_END = "__DA921X_PREFLIGHT_END__"
STATUS_BEGIN = "__I2C6_STATUS_BEGIN__"
STATUS_END = "__I2C6_STATUS_END__"
DMESG_BEGIN = "__DA921X_PREFLIGHT_DMESG_BASE64_BEGIN__"
DMESG_END = "__DA921X_PREFLIGHT_DMESG_BASE64_END__"
EXPECTED_RELEASE = "7.1.3-gemini-da921x-preflight"
EXPECTED_SEQUENCE = (
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0x5D), (0x68, 0x5E),
    (0x68, 0xD7), (0x68, 0x5D), (0x68, 0xD9), (0x68, 0x5E),
    (0x68, 0x56), (0x68, 0x51), (0x68, 0x5E), (0x68, 0xD9),
    (0x68, 0xDA), (0x68, 0x56), (0x68, 0x51), (0x68, 0x5E),
    (0x68, 0xD9), (0x68, 0xDA),
)
PROVIDER = re.compile(
    r"da921x-observer-v1 event=bound valid=(?P<valid>\d+) "
    r"identity_reads=(?P<identity>\d+) providers=(?P<providers>\d+) "
    r"provider_read_attempts=(?P<attempts>\d+) "
    r"provider_read_completed=(?P<completed>\d+) "
    r"register_data_writes=(?P<writes>\d+) "
    r"buck0_selector=(?P<s0>\d+) buck0_uv=(?P<uv0>\d+) buck0_enabled=(?P<e0>\d+) "
    r"buck1_selector=(?P<s1>\d+) buck1_uv=(?P<uv1>\d+) buck1_enabled=(?P<e1>\d+)"
)
PREFLIGHT = re.compile(
    r"da921x-preflight-v1 valid=(?P<valid>\d+) passes=(?P<passes>\d+) "
    r"stable=(?P<stable>\d+) registration_reads=(?P<registration>\d+) "
    r"observer_reads=(?P<observer>\d+) preflight_reads=(?P<preflight>\d+) "
    r"control_a=0x(?P<control_a>[0-9a-f]{2}) v_lock_clear=(?P<v_lock>\d+) "
    r"status_b=0x(?P<status_b>[0-9a-f]{2}) buckb_cont=0x(?P<buckb>[0-9a-f]{2}) "
    r"vbuckb_a=0x(?P<vbuckb_a>[0-9a-f]{2}) vbuckb_b=0x(?P<vbuckb_b>[0-9a-f]{2}) "
    r"safe_prestate=(?P<safe>\d+) register_data_writes=(?P<writes>\d+)"
)
ENTRY = re.compile(
    r"entry(?P<index>\d+) n=(?P<num>\d+) a0=(?P<a0>[0-9a-f]{2}) "
    r"f0=(?P<f0>[0-9a-f]{4}) l0=(?P<l0>\d+) p0=(?P<p0>[0-9a-f]{2}) "
    r"pv=(?P<pv>\d+) a1=(?P<a1>[0-9a-f]{2}) f1=(?P<f1>[0-9a-f]{4}) "
    r"l1=(?P<l1>\d+) ret=(?P<ret>-?\d+) done=(?P<done>\d+)"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def exact_field(lines: list[str], name: str) -> str:
    values = [line.removeprefix(f"{name}=") for line in lines if line.startswith(f"{name}=")]
    require(len(values) == 1, f"field count changed: {name}")
    return values[0]


def bounded_block(lines: list[str], begin: str, end: str) -> list[str]:
    require(lines.count(begin) == 1 and lines.count(end) == 1, f"marker count changed: {begin}")
    first = lines.index(begin)
    last = lines.index(end)
    require(first < last, f"marker order changed: {begin}")
    return lines[first + 1:last]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()

    text = args.capture.read_text(encoding="ascii", errors="strict")
    lines = text.splitlines()
    require(sum(line.endswith(PROBE_BEGIN) for line in lines) == 1, "probe begin marker changed")
    require(sum(line.endswith(PROBE_END) for line in lines) == 1, "probe end marker changed")
    status_lines = bounded_block(lines, STATUS_BEGIN, STATUS_END)
    dmesg_encoded = "".join(bounded_block(lines, DMESG_BEGIN, DMESG_END))
    dmesg = base64.b64decode(dmesg_encoded, validate=True).decode("utf-8", errors="replace")

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
    require(int(exact_field(lines, "keyboard_matrix_inputs")) >= 1, "keyboard input is absent")
    require(int(exact_field(lines, "da921x_i2c_clients")) == 1, "DA921x client count changed")
    require(int(exact_field(lines, "block_mounts")) == 0, "block device unexpectedly mounted")

    status = "\n".join(status_lines)
    expected_scalars = {
        "handoff": "ready",
        "oracle_combined_pointer_reads": "30",
        "oracle_primary_pointer_reads": "24",
        "oracle_page2_pointer_reads": "6",
        "oracle_write_only_messages": "0",
        "oracle_register_data_write_messages": "0",
        "oracle_other_transfers": "0",
        "oracle_other_address_transfers": "0",
    }
    for key, expected in expected_scalars.items():
        values = re.findall(rf"(?:^|\s){re.escape(key)}=([^\s]+)", status)
        require(values == [expected], f"I2C6 status changed: {key}")
    ledger_headers = re.findall(r"entry_ledger=v1 count=(\d+) capacity=(\d+) overflow=(\d+)", status)
    require(ledger_headers == [("30", "32", "0")], "ledger header changed")
    entries = list(ENTRY.finditer(status))
    require(len(entries) == len(EXPECTED_SEQUENCE), "ledger entry count changed")
    for index, (match, expected) in enumerate(zip(entries, EXPECTED_SEQUENCE, strict=True)):
        values = match.groupdict()
        address, pointer = expected
        require(int(values["index"]) == index, f"ledger index changed: {index}")
        require(int(values["num"]) == 2, f"message count changed: {index}")
        require(int(values["a0"], 16) == address and int(values["a1"], 16) == address,
                f"address changed: {index}")
        require(values["f0"] == "0000" and values["f1"] == "0001",
                f"flags changed: {index}")
        require(values["l0"] == "1" and values["l1"] == "1", f"length changed: {index}")
        require(int(values["p0"], 16) == pointer and values["pv"] == "1",
                f"register pointer changed: {index}")
        require(values["ret"] == "2" and values["done"] == "1",
                f"completion changed: {index}")

    provider_matches = list(PROVIDER.finditer(dmesg))
    require(len(provider_matches) == 1, "exactly one complete provider record is required")
    provider = {key: int(value) for key, value in provider_matches[0].groupdict().items()}
    require(provider["valid"] == 1 and provider["identity"] == 14, "provider identity changed")
    require(provider["providers"] == 2, "provider count changed")
    require(provider["attempts"] == 4 and provider["completed"] == 4,
            "provider read accounting changed")
    require(provider["writes"] == 0, "DA921x register-data write observed")
    for buck in (0, 1):
        selector = provider[f"s{buck}"]
        require(provider[f"uv{buck}"] == 300_000 + selector * 10_000,
                f"buck{buck} selector/voltage mismatch")
        require(provider[f"e{buck}"] in (0, 1), f"buck{buck} enable state changed")

    preflight_matches = list(PREFLIGHT.finditer(dmesg))
    require(len(preflight_matches) == 1, "exactly one complete preflight record is required")
    raw_preflight = preflight_matches[0].groupdict()
    decimal_keys = ("valid", "passes", "stable", "registration", "observer", "preflight",
                    "v_lock", "safe", "writes")
    preflight = {key: int(value) for key, value in raw_preflight.items() if key in decimal_keys}
    hex_values = {key: int(value, 16) for key, value in raw_preflight.items() if key not in decimal_keys}
    require(preflight == {
        "valid": 1, "passes": 2, "stable": 1, "registration": 2,
        "observer": 4, "preflight": 10, "v_lock": 1, "safe": 1, "writes": 0,
    }, "preflight accounting or classification changed")
    require(hex_values["control_a"] & 0x80 == 0, "V_LOCK is set")
    require(hex_values["buckb"] == 0x00, "Buck B control prestate changed")
    require(hex_values["vbuckb_a"] == 0x46 and hex_values["vbuckb_b"] == 0x46,
            "Buck B selector prestate changed")

    require("da921x-observer-v1 event=failed-probe" not in dmesg, "provider failed-probe found")
    require("da921x-observer-v1 event=unbind" not in dmesg, "provider unbound during capture")
    require(dmesg.count("input: keyboard-matrix as ") == 1, "keyboard registration changed")
    require(dmesg.count("matrix-keypad keyboard-matrix: polling mode, interval 20 ms") == 1,
            "polling keyboard evidence changed")
    require(dmesg.count("matrix_platform_device=keyboard-matrix driver=matrix-keypad") == 1,
            "keyboard binding evidence changed")
    require(dmesg.count("matrix_input_name=keyboard-matrix event_node=/dev/input/event0") == 1,
            "keyboard event-node evidence changed")
    for fatal in ("Kernel panic", "Internal error:", "Oops:"):
        require(fatal not in dmesg, f"kernel fault marker found: {fatal}")

    print("runtime_classification=success-readonly-preflight-ledger")
    print(f"kernel_release={EXPECTED_RELEASE}")
    print("cpu_possible=0-9")
    print("cpu_present=0-9")
    print("cpu_online=0-7")
    print("cpu_offline=8-9")
    print("maxcpus=8")
    print("I2C6_handoff=ready")
    print("I2C6_ledger_count=30")
    print("I2C6_ledger_capacity=32")
    print("I2C6_ledger_overflow=0")
    print("I2C6_sequence=exact-30-of-30")
    for key, expected in expected_scalars.items():
        if key != "handoff":
            print(f"{key}={expected}")
    print("DA921x_identity_reads=14")
    print("DA921x_registration_reads=2")
    print("DA921x_observer_reads=4")
    print("DA921x_preflight_reads=10")
    print(f"control_a=0x{hex_values['control_a']:02x}")
    print("v_lock_clear=1")
    print(f"status_b=0x{hex_values['status_b']:02x}")
    print("buckb_cont=0x00")
    print("vbuckb_a=0x46")
    print("vbuckb_b=0x46")
    print("safe_prestate=1")
    print("DA921x_register_data_writes=0")
    print("USB_gadget=present")
    print("polling_keyboard=present")
    print("block_mounts=0")
    print("kernel_fault_markers=absent")
    print("CPU8_CPU9_admission=closed")
    print("Gate6_B3=closed-by-exact-transfer-attribution")
    print("Gate6_B4=closed-by-stable-safe-preflight")
    print("Gate6_B1=blocking")
    print("Gate6_B2=blocking")
    print("result=pass")


if __name__ == "__main__":
    main()
