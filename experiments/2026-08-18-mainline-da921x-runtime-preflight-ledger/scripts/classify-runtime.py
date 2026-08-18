#!/usr/bin/env python3
"""Classify retained pre-trigger and optional post-trigger runtime captures."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


EXPECTED_RELEASE = "7.1.3-gemini-da921x-preflight-rt"
TOKEN = "run-readonly-preflight-20260818-a"
PRE_SEQUENCE = (
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0xD7), (0x68, 0xD9),
    (0x68, 0xD7), (0x68, 0x5D), (0x68, 0xD9), (0x68, 0x5E),
)
TRIGGER_SEQUENCE = (
    (0x68, 0x56), (0x68, 0x51), (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0x56), (0x68, 0x51), (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
)
ENTRY = re.compile(
    r"entry(?P<index>\d+) n=(?P<num>\d+) a0=(?P<a0>[0-9a-f]{2}) "
    r"f0=(?P<f0>[0-9a-f]{4}) l0=(?P<l0>\d+) p0=(?P<p0>[0-9a-f]{2}) "
    r"pv=(?P<pv>\d+) a1=(?P<a1>[0-9a-f]{2}) f1=(?P<f1>[0-9a-f]{4}) "
    r"l1=(?P<l1>\d+) ret=(?P<ret>-?\d+) done=(?P<done>\d+)"
)
PROVIDER = re.compile(
    r"da921x-observer-v1 event=bound valid=(?P<valid>\d+) "
    r"identity_reads=(?P<identity>\d+) providers=(?P<providers>\d+) "
    r"provider_read_attempts=(?P<attempts>\d+) provider_read_completed=(?P<completed>\d+) "
    r"register_data_writes=(?P<writes>\d+)"
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def exact_field(lines: list[str], name: str) -> str:
    values = [line.removeprefix(f"{name}=") for line in lines if line.startswith(f"{name}=")]
    require(len(values) == 1, f"field count changed: {name}")
    return values[0]


def block(lines: list[str], begin: str, end: str) -> list[str]:
    require(lines.count(begin) == 1 and lines.count(end) == 1, f"marker count changed: {begin}")
    first = lines.index(begin)
    last = lines.index(end)
    require(first < last, f"marker order changed: {begin}")
    return lines[first + 1:last]


def decode_dmesg(lines: list[str], begin: str, end: str) -> str:
    encoded = "".join(block(lines, begin, end))
    return base64.b64decode(encoded, validate=True).decode("utf-8", errors="replace")


def validate_state(lines: list[str], *, passed: bool) -> None:
    text = "\n".join(lines)
    state = "passed" if passed else "idle"
    attempts = 1 if passed else 0
    valid = 1 if passed else 0
    passes = 2 if passed else 0
    stable = 1 if passed else 0
    preflight = 10 if passed else 0
    require(
        f"runtime_preflight=v1 state={state} attempts={attempts} last_error=0" in text,
        "runtime preflight state changed",
    )
    require(f"trigger_token={TOKEN}" in text, "trigger token identity changed")
    require(
        f"valid={valid} passes={passes} stable={stable} registration_reads=2 "
        f"observer_reads=4 preflight_reads={preflight}" in text,
        "runtime preflight accounting changed",
    )
    require("register_data_writes=0" in text, "DA921x register-data write observed")
    if passed:
        require("control_a=0x00 v_lock_clear=1" in text, "V_LOCK prestate changed")
        require("buckb_cont=0x00 vbuckb_a=0x46 vbuckb_b=0x46" in text,
                "Buck B prestate changed")
        require("safe_prestate=1" in text, "safe prestate rejected")
    else:
        require("safe_prestate=0" in text, "idle state unexpectedly valid")


def validate_status(lines: list[str], sequence: tuple[tuple[int, int], ...]) -> None:
    text = "\n".join(lines)
    count = len(sequence)
    primary = sum(address == 0x68 for address, _ in sequence)
    page2 = sum(address == 0x69 for address, _ in sequence)
    scalars = {
        "handoff": "ready",
        "oracle_combined_pointer_reads": str(count),
        "oracle_primary_pointer_reads": str(primary),
        "oracle_page2_pointer_reads": str(page2),
        "oracle_write_only_messages": "0",
        "oracle_register_data_write_messages": "0",
        "oracle_other_transfers": "0",
        "oracle_other_address_transfers": "0",
    }
    for key, expected in scalars.items():
        values = re.findall(rf"(?:^|\s){re.escape(key)}=([^\s]+)", text)
        require(values == [expected], f"I2C6 status changed: {key}")
    require(
        re.findall(r"entry_ledger=v1 count=(\d+) capacity=(\d+) overflow=(\d+)", text)
        == [(str(count), "32", "0")],
        "ledger header changed",
    )
    entries = list(ENTRY.finditer(text))
    require(len(entries) == count, "ledger entry count changed")
    for index, (match, expected) in enumerate(zip(entries, sequence, strict=True)):
        values = match.groupdict()
        address, pointer = expected
        require(int(values["index"]) == index, f"ledger index changed: {index}")
        require(values["num"] == "2", f"message count changed: {index}")
        require(int(values["a0"], 16) == address and int(values["a1"], 16) == address,
                f"address changed: {index}")
        require(values["f0"] == "0000" and values["f1"] == "0001",
                f"flags changed: {index}")
        require(values["l0"] == "1" and values["l1"] == "1", f"length changed: {index}")
        require(int(values["p0"], 16) == pointer and values["pv"] == "1",
                f"register pointer changed: {index}")
        require(values["ret"] == "2" and values["done"] == "1",
                f"completion changed: {index}")


def validate_dmesg(dmesg: str, *, passed: bool) -> None:
    providers = list(PROVIDER.finditer(dmesg))
    require(len(providers) == 1, "exactly one complete provider record is required")
    provider = {key: int(value) for key, value in providers[0].groupdict().items()}
    require(provider == {
        "valid": 1, "identity": 14, "providers": 2,
        "attempts": 4, "completed": 4, "writes": 0,
    }, "provider accounting changed")
    preflights = list(PREFLIGHT.finditer(dmesg))
    require(len(preflights) == (1 if passed else 0), "preflight publication count changed")
    if passed:
        values = preflights[0].groupdict()
        require({key: int(values[key]) for key in (
            "valid", "passes", "stable", "registration", "observer", "preflight",
            "v_lock", "safe", "writes",
        )} == {
            "valid": 1, "passes": 2, "stable": 1, "registration": 2,
            "observer": 4, "preflight": 10, "v_lock": 1, "safe": 1, "writes": 0,
        }, "published preflight accounting changed")
        require(values["control_a"] == "00" and values["buckb"] == "00",
                "published lock/control prestate changed")
        require(values["vbuckb_a"] == "46" and values["vbuckb_b"] == "46",
                "published selector prestate changed")
    for fatal in ("Kernel panic", "Internal error:", "Oops:"):
        require(fatal not in dmesg, f"kernel fault marker found: {fatal}")
    require(dmesg.count("input: keyboard-matrix as ") == 1, "keyboard registration changed")
    require(dmesg.count("matrix-keypad keyboard-matrix: polling mode, interval 20 ms") == 1,
            "polling keyboard evidence changed")


def validate_pretrigger(path: Path) -> tuple[list[str], str]:
    lines = path.read_text(encoding="ascii", errors="strict").splitlines()
    require(lines.count("__DA921X_RUNTIME_PRETRIGGER_BEGIN__") == 1, "pretrigger begin changed")
    require(lines.count("__DA921X_RUNTIME_PRETRIGGER_END__") == 1, "pretrigger end changed")
    require(exact_field(lines, "kernel_release") == EXPECTED_RELEASE, "kernel identity mismatch")
    require(exact_field(lines, "architecture") == "aarch64", "architecture mismatch")
    require(exact_field(lines, "cpu_possible") == "0-9", "possible CPU set changed")
    require(exact_field(lines, "cpu_present") == "0-9", "present CPU set changed")
    require(exact_field(lines, "cpu_online") == "0-7", "online CPU set changed")
    require(exact_field(lines, "cpu_offline") == "8-9", "offline CPU set changed")
    require("maxcpus=8" in exact_field(lines, "cmdline").split(), "maxcpus=8 is absent")
    boot_hash = exact_field(lines, "boot_id_sha256")
    require(re.fullmatch(r"[0-9a-f]{64}", boot_hash) is not None, "boot hash malformed")
    require(exact_field(lines, "post_probe_boot_id_sha256") == boot_hash, "boot changed")
    require(int(exact_field(lines, "udc_devices")) >= 1, "USB gadget controller absent")
    require(int(exact_field(lines, "keyboard_matrix_inputs")) >= 1, "keyboard absent")
    require(exact_field(lines, "da921x_i2c_clients") == "1", "DA921x client count changed")
    require(exact_field(lines, "block_mounts") == "0", "block device unexpectedly mounted")
    validate_state(block(lines, "__RUNTIME_PREFLIGHT_STATE_BEGIN__",
                         "__RUNTIME_PREFLIGHT_STATE_END__"), passed=False)
    validate_status(block(lines, "__I2C6_STATUS_BEGIN__", "__I2C6_STATUS_END__"), PRE_SEQUENCE)
    dmesg = decode_dmesg(lines, "__DA921X_RUNTIME_DMESG_BASE64_BEGIN__",
                         "__DA921X_RUNTIME_DMESG_BASE64_END__")
    validate_dmesg(dmesg, passed=False)
    return lines, boot_hash


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrigger", type=Path, required=True)
    parser.add_argument("--trigger", type=Path)
    args = parser.parse_args()

    _, boot_hash = validate_pretrigger(args.pretrigger)
    if args.trigger is None:
        print("runtime_classification=pretrigger-exact-20")
        print(f"kernel_release={EXPECTED_RELEASE}")
        print("I2C6_ledger_count=20")
        print("runtime_preflight_state=idle")
        print("trigger_permitted=once")
        print("DA921x_register_data_writes=0")
        print("CPU8_CPU9_admission=closed")
        print("result=pass")
        return

    lines = args.trigger.read_text(encoding="ascii", errors="strict").splitlines()
    require(lines.count("__DA921X_RUNTIME_TRIGGER_BEGIN__") == 1, "trigger begin changed")
    require(lines.count("__DA921X_RUNTIME_TRIGGER_END__") == 1, "trigger end changed")
    require(exact_field(lines, "kernel_release") == EXPECTED_RELEASE, "trigger kernel mismatch")
    require(exact_field(lines, "architecture") == "aarch64", "trigger architecture mismatch")
    require(exact_field(lines, "boot_id_sha256") == boot_hash, "boot changed before trigger")
    require(exact_field(lines, "post_trigger_boot_id_sha256") == boot_hash, "boot changed during trigger")
    require(exact_field(lines, "sysfs_mount_before") == "ro", "sysfs was not initially read-only")
    require(exact_field(lines, "sysfs_remount_rw_status") == "0", "sysfs writable remount failed")
    require(exact_field(lines, "sysfs_mount_during") == "rw", "sysfs writable window absent")
    require(exact_field(lines, "trigger_command_started") == "yes", "trigger did not start")
    require(exact_field(lines, "trigger_command_status") == "0", "trigger command failed")
    require(exact_field(lines, "sysfs_remount_ro_status") == "0", "sysfs read-only restore failed")
    require(exact_field(lines, "sysfs_mount_after") == "ro", "sysfs was not restored read-only")
    validate_state(block(lines, "__RUNTIME_PREFLIGHT_BEFORE_BEGIN__",
                         "__RUNTIME_PREFLIGHT_BEFORE_END__"), passed=False)
    validate_state(block(lines, "__RUNTIME_PREFLIGHT_AFTER_BEGIN__",
                         "__RUNTIME_PREFLIGHT_AFTER_END__"), passed=True)
    validate_status(block(lines, "__I2C6_POSTTRIGGER_STATUS_BEGIN__",
                          "__I2C6_POSTTRIGGER_STATUS_END__"), PRE_SEQUENCE + TRIGGER_SEQUENCE)
    dmesg = decode_dmesg(lines, "__DA921X_RUNTIME_POSTTRIGGER_DMESG_BASE64_BEGIN__",
                         "__DA921X_RUNTIME_POSTTRIGGER_DMESG_BASE64_END__")
    validate_dmesg(dmesg, passed=True)

    print("runtime_classification=success-runtime-preflight-ledger")
    print(f"kernel_release={EXPECTED_RELEASE}")
    print("cpu_online=0-7")
    print("cpu_offline=8-9")
    print("I2C6_pretrigger_sequence=exact-20-of-20")
    print("I2C6_posttrigger_sequence=exact-30-of-30")
    print("I2C6_ledger_capacity=32")
    print("I2C6_ledger_overflow=0")
    print("DA921x_triggered_preflight_reads=10")
    print("DA921x_register_data_writes=0")
    print("runtime_preflight_state=passed")
    print("CPU8_CPU9_admission=closed")
    print("Gate6_B3=closed-by-exact-transfer-attribution")
    print("Gate6_B4=closed-by-stable-safe-preflight")
    print("Gate6_B1=blocking")
    print("Gate6_B2=blocking")
    print("result=pass")


if __name__ == "__main__":
    main()
