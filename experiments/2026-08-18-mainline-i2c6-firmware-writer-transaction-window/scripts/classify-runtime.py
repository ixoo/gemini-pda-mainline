#!/usr/bin/env python3
"""Classify and sanitize one private transaction-window runtime capture."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


EXPECTED_RELEASE = "7.1.3-gemini-i2c6-fwtxn"
BEGIN = "__I2C6_FWTXN_BEGIN__"
END = "__I2C6_FWTXN_END__"
ATTESTATION_BEGIN = "__I2C6_FWTXN_ATTESTATION_BEGIN__"
ATTESTATION_END = "__I2C6_FWTXN_ATTESTATION_END__"
STATUS_BEGIN = "__I2C6_FWTXN_STATUS_BEGIN__"
STATUS_END = "__I2C6_FWTXN_STATUS_END__"
DMESG_BEGIN = "__I2C6_FWTXN_DMESG_BASE64_BEGIN__"
DMESG_END = "__I2C6_FWTXN_DMESG_BASE64_END__"
EXPECTED_SEQUENCE = (
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0xD7), (0x68, 0xD9), (0x68, 0xD7), (0x68, 0x5D),
    (0x68, 0xD9), (0x68, 0x5E),
)
HEADER = re.compile(
    r"enabled=(?P<enabled>[01]) transaction_window_enabled=(?P<window>[01]) "
    r"captured=(?P<captured>[01]) decision=(?P<decision>passed|failed|not-captured) "
    r"probe_reset_decision=(?P<probe>passed|failed|not-captured) "
    r"register_state_stable=(?P<stable>[01]) sample_delay_us=10000\.\.11000 "
    r"register_writes=0 i2c6_attestation_transfers=0"
)
SAMPLE = re.compile(
    r"sample=(?P<sample>[01]) scp_reset_control=(?P<reset>[0-9a-f]{8}) "
    r"scp_debug_pc=(?P<pc>[0-9a-f]{8}) "
    r"devapc_i2c6_permission_raw=(?P<permissions>[0-9a-f,]+) "
    r"master_domain_raw=(?P<masters>[0-9a-f,]+) "
    r"devapc_control=(?P<control>[0-9a-f]{8})"
)
DECODED = re.compile(
    r"decoded_domain0=(?P<d0>[0-3]) decoded_domain1=(?P<d1>[0-3]) "
    r"required_domain0=0 required_domain1=3"
)
TRANSACTION = re.compile(
    r"transaction_entry_checks=(?P<entry>\d+) transaction_exit_checks=(?P<exit>\d+) "
    r"transaction_last_entry_reset_control=(?P<entry_reset>[0-9a-f]{8}) "
    r"transaction_last_exit_reset_control=(?P<exit_reset>[0-9a-f]{8}) "
    r"transaction_reset_failures=(?P<failures>\d+)"
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
    r"provider_read_attempts=(?P<attempts>\d+) "
    r"provider_read_completed=(?P<completed>\d+) "
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


def exact_section(lines: list[str], begin: str, end: str) -> list[str]:
    require(lines.count(begin) == 1 and lines.count(end) == 1,
            f"section markers changed: {begin}")
    start = lines.index(begin)
    finish = lines.index(end)
    require(start < finish, f"section marker order changed: {begin}")
    return lines[start + 1:finish]


def hex_words(value: str, count: int, name: str) -> tuple[int, ...]:
    words = value.split(",")
    require(len(words) == count, f"{name} word count changed")
    require(all(re.fullmatch(r"[0-9a-f]{8}", word) for word in words),
            f"{name} encoding changed")
    return tuple(int(word, 16) for word in words)


def scalar(text: str, name: str) -> str:
    values = re.findall(rf"(?:^|\s){re.escape(name)}=([^\s]+)", text)
    require(len(values) == 1, f"status scalar changed: {name}")
    return values[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()

    lines = args.capture.read_text(encoding="ascii", errors="strict").splitlines()
    require(sum(line.endswith(BEGIN) for line in lines) == 1,
            "probe begin marker changed")
    require(sum(line.endswith(END) for line in lines) == 1,
            "probe end marker changed")
    require(exact_field(lines, "kernel_release") == EXPECTED_RELEASE,
            "kernel identity mismatch")
    require(exact_field(lines, "architecture") == "aarch64",
            "architecture mismatch")
    require(exact_field(lines, "cpu_possible") == "0-9", "possible CPUs changed")
    require(exact_field(lines, "cpu_present") == "0-9", "present CPUs changed")
    require(exact_field(lines, "cpu_online") == "0-7", "online CPUs changed")
    require(exact_field(lines, "cpu_offline") == "8-9", "offline CPUs changed")
    require("maxcpus=8" in exact_field(lines, "cmdline").split(),
            "maxcpus=8 is absent")
    boot_hash = exact_field(lines, "boot_id_sha256")
    require(re.fullmatch(r"[0-9a-f]{64}", boot_hash) is not None,
            "boot hash malformed")
    require(exact_field(lines, "post_probe_boot_id_sha256") == boot_hash,
            "boot changed during probe")
    require(int(exact_field(lines, "udc_devices")) >= 1, "USB gadget absent")
    require(int(exact_field(lines, "keyboard_matrix_inputs")) >= 1,
            "keyboard input absent")
    require(exact_field(lines, "da921x_i2c_clients") == "1",
            "DA921x client count changed")
    require(exact_field(lines, "block_mounts") == "0",
            "block device unexpectedly mounted")
    require(exact_field(lines, "attestation_readable") == "1",
            "attestation attribute unreadable")

    attestation = exact_section(lines, ATTESTATION_BEGIN, ATTESTATION_END)
    require(len(attestation) == 5, "attestation line count changed")
    header = HEADER.fullmatch(attestation[0])
    require(header is not None, "attestation header changed")
    assert header is not None
    require(header["enabled"] == "1" and header["window"] == "1" and
            header["captured"] == "1", "transaction attestation not active")
    samples = []
    for index, line in enumerate(attestation[1:3]):
        match = SAMPLE.fullmatch(line)
        require(match is not None, f"attestation sample changed: {index}")
        assert match is not None
        require(int(match["sample"]) == index, "sample order changed")
        samples.append({
            "reset": int(match["reset"], 16),
            "pc": int(match["pc"], 16),
            "permissions": hex_words(match["permissions"], 8, "permissions"),
            "masters": hex_words(match["masters"], 4, "master domains"),
            "control": int(match["control"], 16),
        })
    decoded = DECODED.fullmatch(attestation[3])
    require(decoded is not None, "decoded diagnostic line changed")
    assert decoded is not None
    d0 = int(decoded["d0"])
    d1 = int(decoded["d1"])
    require(d0 == (samples[0]["permissions"][0] >> 4) & 3,
            "domain-0 diagnostic decode changed")
    require(d1 == (samples[0]["permissions"][1] >> 4) & 3,
            "domain-1 diagnostic decode changed")
    raw_stable = all(samples[0][name] == samples[1][name]
                     for name in ("reset", "pc", "permissions", "masters", "control"))
    require(int(header["stable"]) == int(raw_stable),
            "reported diagnostic stability changed")
    require(all(sample["reset"] == 0 for sample in samples),
            "probe reset control is not asserted")
    require(header["probe"] == "passed", "probe reset decision failed")

    transaction = TRANSACTION.fullmatch(attestation[4])
    require(transaction is not None, "transaction edge line changed")
    assert transaction is not None
    require(transaction["entry"] == "20" and transaction["exit"] == "20",
            "transaction edge counts changed")
    require(transaction["entry_reset"] == "00000000" and
            transaction["exit_reset"] == "00000000",
            "transaction edge reset changed")
    require(transaction["failures"] == "0", "transaction reset failure observed")
    require(header["decision"] == "passed", "transaction decision failed")

    require(exact_field(lines, "handoff_state") == "ready",
            "handoff did not reach ready")
    handoff = exact_field(lines, "handoff_status")
    for name, expected in (
        ("state", "ready"), ("supplier_bound", "yes"),
        ("access_grant", "ready"), ("late", "passed"),
        ("late_checks", "1"), ("faults", "0"),
        ("i2c6_policy", "requires-ready"),
    ):
        require(scalar(handoff, name) == expected, f"handoff changed: {name}")

    status_lines = exact_section(lines, STATUS_BEGIN, STATUS_END)
    status = "\n".join(status_lines)
    for name, expected in (
        ("handoff", "ready"), ("transfer_attempts", "20"),
        ("dma_starts", "0"), ("nonzero_starts", "20"),
        ("irq_count", "20"), ("oracle_combined_pointer_reads", "20"),
        ("oracle_primary_pointer_reads", "14"),
        ("oracle_page2_pointer_reads", "6"),
        ("oracle_write_only_messages", "0"),
        ("oracle_register_data_write_messages", "0"),
        ("oracle_other_transfers", "0"),
        ("oracle_other_address_transfers", "0"),
    ):
        require(scalar(status, name) == expected, f"I2C6 status changed: {name}")
    require(re.findall(r"entry_ledger=v1 count=(\d+) capacity=(\d+) overflow=(\d+)",
                       status) == [("20", "32", "0")], "ledger header changed")
    entries = list(ENTRY.finditer(status))
    require(len(entries) == len(EXPECTED_SEQUENCE), "ledger count changed")
    for index, (match, expected) in enumerate(zip(entries, EXPECTED_SEQUENCE, strict=True)):
        values = match.groupdict()
        address, pointer = expected
        require(int(values["index"]) == index, f"ledger index changed: {index}")
        require(values["num"] == "2", f"message count changed: {index}")
        require(int(values["a0"], 16) == address and
                int(values["a1"], 16) == address, f"address changed: {index}")
        require(values["f0"] == "0000" and values["f1"] == "0001",
                f"flags changed: {index}")
        require(values["l0"] == "1" and values["l1"] == "1",
                f"length changed: {index}")
        require(int(values["p0"], 16) == pointer and values["pv"] == "1",
                f"pointer changed: {index}")
        require(values["ret"] == "2" and values["done"] == "1",
                f"completion changed: {index}")

    encoded = "".join(exact_section(lines, DMESG_BEGIN, DMESG_END))
    dmesg = base64.b64decode(encoded, validate=True).decode("utf-8", errors="replace")
    providers = list(PROVIDER.finditer(dmesg))
    require(len(providers) == 1, "exactly one provider record is required")
    provider = {key: int(value) for key, value in providers[0].groupdict().items()}
    require(provider == {
        "valid": 1, "identity": 14, "providers": 2,
        "attempts": 4, "completed": 4, "writes": 0,
    }, "provider accounting changed")
    require(dmesg.count("input: keyboard-matrix as ") == 1,
            "keyboard registration changed")
    require(dmesg.count("matrix-keypad keyboard-matrix: polling mode, interval 20 ms") == 1,
            "polling keyboard evidence changed")
    for fatal in ("Kernel panic", "Internal error:", "Oops:"):
        require(fatal not in dmesg, f"kernel fault marker found: {fatal}")

    print("runtime_classification=success-firmware-writer-transaction-window")
    print("roadmap_decision=close-B1-proceed-to-B2-design")
    print(f"kernel_release={EXPECTED_RELEASE}")
    print("cpu_online=0-7")
    print("cpu_offline=8-9")
    print("probe_reset_decision=passed")
    print("transaction_window_decision=passed")
    print("transaction_entry_checks=20")
    print("transaction_exit_checks=20")
    print("transaction_reset_failures=0")
    print("I2C6_ledger_count=20")
    print("I2C6_ledger_capacity=32")
    print("I2C6_ledger_overflow=0")
    print("I2C6_sequence=exact-20-of-20")
    print("DA921x_identity_reads=14")
    print("DA921x_provider_reads=4")
    print("DA921x_register_data_writes=0")
    print(f"register_state_stable={int(raw_stable)}")
    for index, sample in enumerate(samples):
        print(f"sample{index}_scp_reset_control={sample['reset']:08x}")
        print(f"sample{index}_scp_debug_pc={sample['pc']:08x}")
    print(f"decoded_domain0={d0}")
    print(f"decoded_domain1={d1}")
    print("USB_gadget=present")
    print("polling_keyboard=present")
    print("block_mounts=0")
    print("kernel_fault_markers=absent")
    print("CPU8_CPU9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
