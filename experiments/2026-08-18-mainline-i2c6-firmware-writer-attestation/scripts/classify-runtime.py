#!/usr/bin/env python3
"""Classify and sanitize one private firmware-writer attestation capture."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import re


EXPECTED_RELEASE = "7.1.3-gemini-i2c6-fwatt"
BEGIN = "__I2C6_FWATT_BEGIN__"
END = "__I2C6_FWATT_END__"
SYSFS_BEGIN = "__I2C6_FWATT_SYSFS_BEGIN__"
SYSFS_END = "__I2C6_FWATT_SYSFS_END__"
DMESG_BEGIN = "__I2C6_FWATT_DMESG_BASE64_BEGIN__"
DMESG_END = "__I2C6_FWATT_DMESG_BASE64_END__"
HEADER = re.compile(
    r"enabled=(?P<enabled>[01]) captured=(?P<captured>[01]) "
    r"decision=(?P<decision>passed|failed|not-captured) "
    r"register_state_stable=(?P<stable>[01]) "
    r"sample_delay_us=10000\.\.11000 register_writes=0 i2c6_transfers=0"
)
SAMPLE = re.compile(
    r"sample=(?P<sample>[01]) "
    r"scp_reset_control=(?P<reset>[0-9a-f]{8}) "
    r"scp_debug_pc=(?P<pc>[0-9a-f]{8}) "
    r"devapc_i2c6_permission_raw=(?P<permissions>[0-9a-f,]+) "
    r"master_domain_raw=(?P<masters>[0-9a-f,]+) "
    r"devapc_control=(?P<control>[0-9a-f]{8})"
)
DECODED = re.compile(
    r"decoded_domain0=(?P<d0>[0-3]) decoded_domain1=(?P<d1>[0-3]) "
    r"required_domain0=0 required_domain1=3"
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()

    text = args.capture.read_text(encoding="ascii", errors="strict")
    lines = text.splitlines()
    require(sum(line.endswith(BEGIN) for line in lines) == 1,
            "probe begin marker changed")
    require(sum(line.endswith(END) for line in lines) == 1,
            "probe end marker changed")
    require(exact_field(lines, "kernel_release") == EXPECTED_RELEASE,
            "kernel identity mismatch")
    require(exact_field(lines, "architecture") == "aarch64",
            "architecture mismatch")
    require(exact_field(lines, "cpu_possible") == "0-9",
            "possible CPU set changed")
    require(exact_field(lines, "cpu_present") == "0-9",
            "present CPU set changed")
    require(exact_field(lines, "cpu_online") == "0-7",
            "online CPU set changed")
    require(exact_field(lines, "cpu_offline") == "8-9",
            "offline CPU set changed")
    require("maxcpus=8" in exact_field(lines, "cmdline").split(),
            "maxcpus=8 is absent")
    boot_hash = exact_field(lines, "boot_id_sha256")
    require(re.fullmatch(r"[0-9a-f]{64}", boot_hash) is not None,
            "boot hash malformed")
    require(exact_field(lines, "post_probe_boot_id_sha256") == boot_hash,
            "boot changed during probe")
    require(int(exact_field(lines, "udc_devices")) >= 1,
            "USB gadget controller is absent")
    require(int(exact_field(lines, "keyboard_matrix_inputs")) >= 1,
            "keyboard-matrix input is absent")
    require(exact_field(lines, "attestation_readable") == "1",
            "attestation attribute is not readable")
    require(int(exact_field(lines, "block_mounts")) == 0,
            "block device unexpectedly mounted")

    sysfs = exact_section(lines, SYSFS_BEGIN, SYSFS_END)
    require(len(sysfs) == 4, "attestation line count changed")
    header = HEADER.fullmatch(sysfs[0])
    require(header is not None, "attestation header changed")
    assert header is not None
    require(header["enabled"] == "1" and header["captured"] == "1",
            "attestation was not captured")
    require(header["decision"] in ("passed", "failed"),
            "attestation decision is incomplete")

    samples = []
    for index, line in enumerate(sysfs[1:3]):
        match = SAMPLE.fullmatch(line)
        require(match is not None, f"attestation sample {index} changed")
        assert match is not None
        require(int(match["sample"]) == index, "sample order changed")
        samples.append({
            "reset": int(match["reset"], 16),
            "pc": int(match["pc"], 16),
            "permissions": hex_words(match["permissions"], 8,
                                      f"sample{index} permissions"),
            "masters": hex_words(match["masters"], 4,
                                  f"sample{index} master domains"),
            "control": int(match["control"], 16),
        })
    decoded = DECODED.fullmatch(sysfs[3])
    require(decoded is not None, "decoded permission line changed")
    assert decoded is not None
    d0 = int(decoded["d0"])
    d1 = int(decoded["d1"])
    require(d0 == (samples[0]["permissions"][0] >> 4) & 3,
            "domain-0 decode does not match raw value")
    require(d1 == (samples[0]["permissions"][1] >> 4) & 3,
            "domain-1 decode does not match raw value")

    raw_stable = all(samples[0][name] == samples[1][name]
                     for name in ("permissions", "masters", "control"))
    require(int(header["stable"]) == int(raw_stable),
            "reported stability does not match raw samples")
    scp_zero = all(sample["reset"] == 0 and sample["pc"] == 0
                   for sample in samples)
    pass_condition = scp_zero and raw_stable and d0 == 0 and d1 == 3
    require((header["decision"] == "passed") == pass_condition,
            "decision does not match immutable pass condition")

    dmesg_lines = exact_section(lines, DMESG_BEGIN, DMESG_END)
    dmesg = base64.b64decode("".join(dmesg_lines), validate=True).decode(
        "utf-8", errors="replace"
    )
    for fatal in ("Kernel panic", "Internal error:", "Oops:"):
        require(fatal not in dmesg, f"kernel fault marker found: {fatal}")
    clients = int(exact_field(lines, "da921x_i2c_clients"))
    require(clients in (0, 1), "DA921x client count is invalid")
    if pass_condition:
        require(clients == 1, "passed attestation did not reach DA921x client")
        require(re.search(r"da921x-observer-v1 event=bound .*register_data_writes=0 ",
                          dmesg) is not None,
                "zero-write DA921x bound record is absent")

    decision = "close-B1-proceed-to-B2" if pass_condition else "keep-B1-open"
    print("runtime_classification=success-firmware-writer-attestation")
    print(f"attestation_decision={header['decision']}")
    print(f"roadmap_decision={decision}")
    print("kernel_release=" + EXPECTED_RELEASE)
    print("cpu_online=0-7")
    print("cpu_offline=8-9")
    print("register_writes=0")
    print("i2c6_attestation_transfers=0")
    print(f"register_state_stable={int(raw_stable)}")
    print(f"decoded_domain0={d0}")
    print(f"decoded_domain1={d1}")
    for index, sample in enumerate(samples):
        print(f"sample{index}_scp_reset_control={sample['reset']:08x}")
        print(f"sample{index}_scp_debug_pc={sample['pc']:08x}")
        print("sample{}_devapc_i2c6_permission_raw={}".format(
            index, ",".join(f"{word:08x}" for word in sample["permissions"])
        ))
        print("sample{}_master_domain_raw={}".format(
            index, ",".join(f"{word:08x}" for word in sample["masters"])
        ))
        print(f"sample{index}_devapc_control={sample['control']:08x}")
    print(f"da921x_i2c_clients={clients}")
    print("CPU8_CPU9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
