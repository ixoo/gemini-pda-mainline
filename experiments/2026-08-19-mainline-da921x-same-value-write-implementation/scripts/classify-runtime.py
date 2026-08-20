#!/usr/bin/env python3
"""Classify retained pre-trigger and one-shot same-value-write captures."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


EXPECTED_RELEASE = "7.1.3-gemini-da921x-same-write"
TOKEN = "run-same-value-write-20260819-a"
PRE_SEQUENCE = (
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0xD7), (0x68, 0xD9), (0x68, 0xD7), (0x68, 0x5D),
    (0x68, 0xD9), (0x68, 0x5E),
)
ACTIONS = (
    ("read", 0x56), ("read", 0x51), ("read", 0x5E), ("read", 0xD9),
    ("read", 0xDA), ("write", 0xDA), ("read", 0xDA), ("read", 0xDA),
    ("read", 0x56), ("read", 0x51), ("read", 0x5E), ("read", 0xD9),
)
ENTRY = re.compile(
    r"entry(?P<index>\d+) n=(?P<num>\d+) a0=(?P<a0>[0-9a-f]{2}) "
    r"f0=(?P<f0>[0-9a-f]{4}) l0=(?P<l0>\d+) p0=(?P<p0>[0-9a-f]{2}) "
    r"pv=(?P<pv>\d+) p1=(?P<p1>[0-9a-f]{2}) p1v=(?P<p1v>\d+) "
    r"a1=(?P<a1>[0-9a-f]{2}) f1=(?P<f1>[0-9a-f]{4}) "
    r"l1=(?P<l1>\d+) ret=(?P<ret>-?\d+) done=(?P<done>\d+)"
)
STATE = re.compile(
    r"same_value_write=v1 state=(?P<state>idle|running|passed|failed-no-write|"
    r"faulted-no-further-i2c) attempts=(?P<attempts>\d+) last_error=(?P<error>-?\d+)"
)
COUNTS = re.compile(r"action_transfers=(?P<actions>\d+) write_attempts=(?P<writes>\d+)")
VALUES = re.compile(
    r"preflight=(?P<p0>[0-9a-f]{2}),(?P<p1>[0-9a-f]{2}),"
    r"(?P<p2>[0-9a-f]{2}),(?P<p3>[0-9a-f]{2}),(?P<p4>[0-9a-f]{2}) "
    r"immediate=(?P<immediate>[0-9a-f]{2}) delayed=(?P<delayed>[0-9a-f]{2}) "
    r"poststate=(?P<s0>[0-9a-f]{2}),(?P<s1>[0-9a-f]{2}),"
    r"(?P<s2>[0-9a-f]{2}),(?P<s3>[0-9a-f]{2})"
)
PROVIDER = re.compile(
    r"da921x-observer-v1 event=bound valid=(?P<valid>\d+) "
    r"identity_reads=(?P<identity>\d+) providers=(?P<providers>\d+) "
    r"provider_read_attempts=(?P<attempts>\d+) provider_read_completed=(?P<completed>\d+) "
    r"register_data_writes=(?P<writes>\d+)"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def exact_field(lines: list[str], name: str) -> str:
    values = [line.removeprefix(f"{name}=") for line in lines
              if line.startswith(f"{name}=")]
    require(len(values) == 1, f"field count changed: {name}")
    return values[0]


def section(lines: list[str], begin: str, end: str) -> list[str]:
    require(lines.count(begin) == 1 and lines.count(end) == 1,
            f"section markers changed: {begin}")
    start = lines.index(begin)
    finish = lines.index(end)
    require(start < finish, f"section order changed: {begin}")
    return lines[start + 1:finish]


def decode_dmesg(lines: list[str], begin: str, end: str) -> str:
    encoded = "".join(section(lines, begin, end))
    return base64.b64decode(encoded, validate=True).decode("utf-8", errors="replace")


def scalar(text: str, name: str) -> str:
    values = re.findall(rf"(?:^|\s){re.escape(name)}=([^\s]+)", text)
    require(len(values) == 1, f"status scalar changed: {name}")
    return values[0]


def validate_state(lines: list[str], expected: str) -> tuple[int, int, int]:
    text = "\n".join(lines)
    states = list(STATE.finditer(text))
    counts = list(COUNTS.finditer(text))
    values = list(VALUES.finditer(text))
    require(len(states) == len(counts) == len(values) == 1, "state schema changed")
    state = states[0].groupdict()
    action_count = int(counts[0]["actions"])
    write_count = int(counts[0]["writes"])
    error = int(state["error"])
    require(state["state"] == expected, "same-value state changed")
    require(f"trigger_token={TOKEN}" in text, "trigger token changed")
    require("cpu_online=0-7 cpu_offline=8-9 page_con_accesses=0 " in text,
            "CPU or PAGE_CON closure changed")
    require("consumer_requests=0 cpu_requests=0 second_writes=0" in text,
            "consumer/CPU/second-write closure changed")
    if expected == "idle":
        require(state["attempts"] == "0" and error == 0, "idle accounting changed")
        require(action_count == 0 and write_count == 0, "idle transfer accounting changed")
        require(set(values[0].groupdict().values()) == {"00"}, "idle values changed")
    elif expected == "passed":
        require(state["attempts"] == "1" and error == 0, "success accounting changed")
        require(action_count == 12 and write_count == 1, "success transfer count changed")
        require(tuple(values[0].groupdict().values()) ==
                ("7b", "c1", "00", "46", "46", "46", "46", "7b", "c1", "00", "46"),
                "success values changed")
    else:
        require(state["attempts"] == "1" and error != 0, "failure accounting changed")
        require(0 <= action_count <= 12, "failure action count changed")
        require(write_count == int(action_count >= 6), "failure write count changed")
        if expected == "failed-no-write":
            require(action_count <= 5 and write_count == 0, "pre-write failure boundary changed")
        else:
            require(6 <= action_count <= 12 and write_count == 1,
                    "post-write failure boundary changed")
    return action_count, write_count, error


def validate_entry(match: re.Match[str], index: int, kind: str, pointer: int,
                   *, terminal: bool) -> None:
    value = match.groupdict()
    require(int(value["index"]) == index, f"ledger index changed: {index}")
    require(value["a0"] == "68" and value["f0"] == "0000" and value["pv"] == "1",
            f"ledger primary shape changed: {index}")
    require(int(value["p0"], 16) == pointer and value["done"] == "1",
            f"ledger payload/completion changed: {index}")
    if kind == "read":
        require(value["num"] == "2" and value["l0"] == "1" and value["p1v"] == "0",
                f"read request shape changed: {index}")
        require(value["a1"] == "68" and value["f1"] == "0001" and value["l1"] == "1",
                f"read response shape changed: {index}")
        if not terminal:
            require(value["ret"] == "2", f"completed read result changed: {index}")
    else:
        require(value["num"] == "1" and value["l0"] == "2",
                f"write shape changed: {index}")
        require(value["p1"] == "46" and value["p1v"] == "1",
                "write payload attribution changed")
        require(value["a1"] == "00" and value["f1"] == "0000" and value["l1"] == "0",
                "write gained a second message")
        if not terminal:
            require(value["ret"] == "1", "completed write result changed")


def validate_status(lines: list[str], action_count: int, *, terminal_failure: bool) -> None:
    text = "\n".join(lines)
    total = 20 + action_count
    reads = sum(1 for kind, _ in ACTIONS[:action_count] if kind == "read")
    writes = int(action_count >= 6)
    for name, expected in (
        ("handoff", "ready"),
        ("oracle_combined_pointer_reads", str(20 + reads)),
        ("oracle_primary_pointer_reads", str(14 + reads)),
        ("oracle_page2_pointer_reads", "6"),
        ("oracle_write_only_messages", str(writes)),
        ("oracle_register_data_write_messages", str(writes)),
        ("oracle_other_transfers", "0"), ("oracle_other_address_transfers", "0"),
        ("transaction_entry_checks", str(total)),
        ("transaction_exit_checks", str(total)),
        ("transaction_reset_failures", "0"),
    ):
        require(scalar(text, name) == expected, f"I2C6 status changed: {name}")
    require(re.findall(r"entry_ledger=v2 count=(\d+) capacity=(\d+) overflow=(\d+)", text)
            == [(str(total), "32", "0")], "ledger v2 header changed")
    entries = list(ENTRY.finditer(text))
    require(len(entries) == total, "ledger entry count changed")
    for index, (address, pointer) in enumerate(PRE_SEQUENCE):
        value = entries[index].groupdict()
        require(value["num"] == "2" and int(value["a0"], 16) == address and
                int(value["a1"], 16) == address and int(value["p0"], 16) == pointer,
                f"pretrigger ledger identity changed: {index}")
        require(value["f0"] == "0000" and value["f1"] == "0001" and
                value["l0"] == value["l1"] == "1" and value["pv"] == "1" and
                value["p1v"] == "0" and value["ret"] == "2" and value["done"] == "1",
                f"pretrigger ledger shape changed: {index}")
    for offset, (kind, pointer) in enumerate(ACTIONS[:action_count]):
        is_terminal = terminal_failure and offset == action_count - 1
        validate_entry(entries[20 + offset], 20 + offset, kind, pointer,
                       terminal=is_terminal)


def validate_dmesg(dmesg: str, state: str) -> None:
    providers = list(PROVIDER.finditer(dmesg))
    require(len(providers) == 1, "provider record count changed")
    require({key: int(value) for key, value in providers[0].groupdict().items()} == {
        "valid": 1, "identity": 14, "providers": 2,
        "attempts": 4, "completed": 4, "writes": 0,
    }, "provider accounting changed")
    success = "same-value Gate-6 action passed with 12 transfers"
    require(dmesg.count(success) == int(state == "passed"), "success publication changed")
    require(dmesg.count("input: keyboard-matrix as ") == 1, "keyboard registration changed")
    for fatal in ("Kernel panic", "Internal error:", "Oops:"):
        require(fatal not in dmesg, f"kernel fault marker found: {fatal}")


def validate_pretrigger(path: Path) -> tuple[list[str], str]:
    lines = path.read_text(encoding="ascii", errors="strict").splitlines()
    require(lines.count("__DA921X_SAME_VALUE_PRETRIGGER_BEGIN__") == 1,
            "pretrigger begin changed")
    require(lines.count("__DA921X_SAME_VALUE_PRETRIGGER_END__") == 1,
            "pretrigger end changed")
    header = lines[:lines.index("__SAME_VALUE_STATE_BEGIN__")]
    require(exact_field(header, "kernel_release") == EXPECTED_RELEASE, "kernel changed")
    require(exact_field(header, "architecture") == "aarch64", "architecture changed")
    require(exact_field(header, "cpu_possible") == "0-9", "possible CPUs changed")
    require(exact_field(header, "cpu_present") == "0-9", "present CPUs changed")
    require(exact_field(header, "cpu_online") == "0-7", "online CPUs changed")
    require(exact_field(header, "cpu_offline") == "8-9", "offline CPUs changed")
    require("maxcpus=8" in exact_field(header, "cmdline").split(), "maxcpus=8 absent")
    boot_hash = exact_field(header, "boot_id_sha256")
    require(re.fullmatch(r"[0-9a-f]{64}", boot_hash) is not None, "boot hash malformed")
    require(exact_field(lines, "post_probe_boot_id_sha256") == boot_hash, "boot changed")
    require(int(exact_field(header, "udc_devices")) >= 1, "USB gadget absent")
    require(int(exact_field(header, "keyboard_matrix_inputs")) >= 1, "keyboard absent")
    require(exact_field(header, "da921x_i2c_clients") == "1", "DA921x client changed")
    require(exact_field(header, "block_mounts") == "0", "block device mounted")
    validate_state(section(lines, "__SAME_VALUE_STATE_BEGIN__", "__SAME_VALUE_STATE_END__"),
                   "idle")
    validate_status(section(lines, "__I2C6_STATUS_BEGIN__", "__I2C6_STATUS_END__"), 0,
                    terminal_failure=False)
    validate_dmesg(decode_dmesg(lines, "__DA921X_SAME_VALUE_DMESG_BASE64_BEGIN__",
                                "__DA921X_SAME_VALUE_DMESG_BASE64_END__"), "idle")
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
        print("I2C6_ledger_schema=v2")
        print("I2C6_ledger_count=20")
        print("same_value_write_state=idle")
        print("trigger_permitted=once")
        print("CPU8_CPU9_admission=closed")
        print("result=pass")
        return

    lines = args.trigger.read_text(encoding="ascii", errors="strict").splitlines()
    require(lines.count("__DA921X_SAME_VALUE_TRIGGER_BEGIN__") == 1, "trigger begin changed")
    require(lines.count("__DA921X_SAME_VALUE_TRIGGER_END__") == 1, "trigger end changed")
    require(exact_field(lines, "kernel_release") == EXPECTED_RELEASE, "trigger kernel changed")
    require(exact_field(lines, "architecture") == "aarch64", "trigger arch changed")
    require(exact_field(lines, "boot_id_sha256") == boot_hash, "boot changed before token")
    require(exact_field(lines, "post_trigger_boot_id_sha256") == boot_hash,
            "boot changed during token")
    require(exact_field(lines, "sysfs_mount_before") == "ro" and
            exact_field(lines, "sysfs_remount_rw_status") == "0" and
            exact_field(lines, "sysfs_mount_during") == "rw" and
            exact_field(lines, "sysfs_remount_ro_status") == "0" and
            exact_field(lines, "sysfs_mount_after") == "ro", "sysfs window changed")
    require(exact_field(lines, "trigger_command_started") == "yes", "token did not start")
    require(exact_field(lines, "same_value_write_writable") == "1",
            "same-value attribute was not writable inside the bounded window")
    validate_state(section(lines, "__SAME_VALUE_BEFORE_BEGIN__", "__SAME_VALUE_BEFORE_END__"),
                   "idle")
    after = section(lines, "__SAME_VALUE_AFTER_BEGIN__", "__SAME_VALUE_AFTER_END__")
    after_text = "\n".join(after)
    state_match = STATE.search(after_text)
    require(state_match is not None, "post-trigger state absent")
    assert state_match is not None
    state = state_match["state"]
    require(state in ("passed", "failed-no-write", "faulted-no-further-i2c"),
            "post-trigger state is not terminal")
    action_count, write_count, error = validate_state(after, state)
    trigger_status = int(exact_field(lines, "trigger_command_status"))
    require((state == "passed" and trigger_status == 0) or
            (state != "passed" and trigger_status != 0), "token return status changed")
    validate_status(section(lines, "__I2C6_POSTTRIGGER_STATUS_BEGIN__",
                            "__I2C6_POSTTRIGGER_STATUS_END__"), action_count,
                    terminal_failure=state != "passed" and action_count > 0)
    dmesg = decode_dmesg(lines, "__DA921X_SAME_VALUE_POSTTRIGGER_DMESG_BASE64_BEGIN__",
                         "__DA921X_SAME_VALUE_POSTTRIGGER_DMESG_BASE64_END__")
    validate_dmesg(dmesg, state)

    classification = {
        "passed": "success-same-value-write",
        "failed-no-write": "terminal-failed-no-write",
        "faulted-no-further-i2c": "terminal-faulted-no-further-i2c",
    }[state]
    print(f"runtime_classification={classification}")
    print(f"kernel_release={EXPECTED_RELEASE}")
    print("cpu_online=0-7")
    print("cpu_offline=8-9")
    print("I2C6_pretrigger_sequence=exact-20-of-20")
    print(f"I2C6_posttrigger_count={20 + action_count}")
    print(f"action_transfers={action_count}")
    print(f"write_attempts={write_count}")
    print(f"last_error={error}")
    print(f"same_value_write_state={state}")
    print("trigger_attempts=1")
    print("trigger_retries=0")
    print("second_writes=0")
    print("CPU8_CPU9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
