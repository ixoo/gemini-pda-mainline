#!/usr/bin/env python3
"""Validate Candidate AI's bounded, read-only USB runtime attribution."""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation
import pathlib
import re
import sys

sys.dont_write_bytecode = True


EXPECTED_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32"
)
EXPECTED_CONFIG_SHA256 = "32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46"
EXPECTED_INSTALLED_FULL_SHA256 = (
    "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86"
)
EXPECTED_USB_MARKER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
EXPECTED_USB_PROMPT = "GEMINI-AC-USB# "
EXPECTED_HOST_MAC = "42:00:15:19:82:00"
EXPECTED_HOST_ADDRESS = "10.15.19.1/24"
EXPECTED_DEVICE_ENDPOINT = "10.15.19.82:2323"
HEX256 = re.compile(r"[0-9a-f]{64}")
DECIMAL_SECONDS = re.compile(r"[0-9]+(?:\.[0-9]+)?")
EXPECTED_BOOT_NODES = {
    1: "0000000001",
    2: "0000000002",
    3: "0000000003",
    4: "0000000100",
    5: "0000000101",
    6: "0000000102",
    7: "0000000103",
}
FAULT = re.compile(
    r"(?:Kernel panic|\bOops:|\bBUG:|\bSError\b|RCU stall|rcu:.*stall|hung task|"
    r"CPU[0-9]+: failed|failed to boot|psci.*(?:fail|error))",
    re.IGNORECASE,
)


def section(text: str, name: str) -> str:
    matches = re.findall(
        rf"__AI_{re.escape(name)}_BEGIN__\r?\n(.*?)__AI_{re.escape(name)}_END__",
        text,
        re.DOTALL,
    )
    if len(matches) != 1:
        raise ValueError(f"runtime section is absent or duplicated: {name}")
    lines: list[str] = []
    for raw_line in matches[0].replace("\r", "").splitlines():
        line = raw_line
        while line.startswith(EXPECTED_USB_PROMPT):
            line = line.removeprefix(EXPECTED_USB_PROMPT)
        lines.append(line)
    return "\n".join(lines).strip()


def key_values(text: str, label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise ValueError(f"{label} is malformed or duplicated")
        result[key] = value
    return result


def decimal_seconds(value: str, label: str) -> Decimal:
    if DECIMAL_SECONDS.fullmatch(value) is None:
        raise ValueError(f"{label} is malformed")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{label} is malformed") from exc
    if not result.is_finite():
        raise ValueError(f"{label} is not finite")
    return result


def stat_sample(text: str) -> dict[int, int]:
    values: dict[int, int] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"cpu([0-9]+)\s+(.+)", line.strip())
        if match is None:
            continue
        fields = match.group(2).split()
        if not fields or any(not field.isdecimal() for field in fields):
            raise ValueError("malformed per-CPU accounting line")
        cpu = int(match.group(1))
        if cpu in values:
            raise ValueError("duplicate per-CPU accounting line")
        values[cpu] = sum(int(field) for field in fields)
    return values


def validate(text: str, expected_installed_full_sha256: str) -> None:
    if HEX256.fullmatch(expected_installed_full_sha256) is None:
        raise ValueError("expected installed full-partition SHA-256 is malformed")
    if expected_installed_full_sha256 != EXPECTED_INSTALLED_FULL_SHA256:
        raise ValueError("expected installed full-partition SHA-256 is not Candidate AI")

    standalone_banners = sum(
        line == EXPECTED_USB_MARKER for line in text.replace("\r", "").splitlines()
    )
    if standalone_banners != 1:
        raise ValueError("exact inherited AC standalone USB banner is absent or duplicated")

    host = key_values(section(text, "HOST"), "runtime host attestation")
    expected_host = {
        "installed_full_sha256_input": expected_installed_full_sha256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "installed_full_hash_reverified_during_collection": "no",
        "device_partition_read_during_collection": "no",
        "mac": EXPECTED_HOST_MAC,
        "host_address": EXPECTED_HOST_ADDRESS,
        "device_endpoint": EXPECTED_DEVICE_ENDPOINT,
    }
    if set(host) != set(expected_host) | {"interface", "route_interface"}:
        raise ValueError("runtime host attestation inventory changed")
    for key, value in expected_host.items():
        if host[key] != value:
            raise ValueError(f"runtime host attestation changed: {key}")
    if re.fullmatch(r"[A-Za-z0-9]+", host["interface"]) is None:
        raise ValueError("runtime host interface is malformed")
    if host["route_interface"] != host["interface"]:
        raise ValueError("runtime route is not bound to the exact USB interface")

    identity = key_values(section(text, "IDENTITY"), "runtime identity")
    expected = {
        "cmdline": EXPECTED_CMDLINE,
        "possible": "0-9",
        "present": "0-9",
        "online": "0-7",
        "offline": "8-9",
        "nproc": "8",
        "kernel": "7.1.3-gemini-observability-L",
        "config_sha256": EXPECTED_CONFIG_SHA256,
        "cpu8_enable_method": "mediatek,mt6797-psci",
        "cpu9_enable_method": "mediatek,mt6797-psci",
        "boot_gate_symbol_count": "1",
        "disable_gate_symbol_count": "1",
        "ops_symbol_count": "1",
        "cpu8_online_control": "absent",
        "cpu9_online_control": "absent",
    }
    if set(identity) != set(expected) | {"boot_id", "uptime_before"}:
        raise ValueError("Candidate AI live identity inventory changed")
    for key, value in expected.items():
        if identity[key] != value:
            raise ValueError(f"Candidate AI live identity changed: {key}")
    if re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        identity["boot_id"],
    ) is None:
        raise ValueError("live boot ID is malformed")
    tokens = identity["cmdline"].split()
    if tokens.count("maxcpus=8") != 1 or any(
        token == "nosmp" or token == "maxcpus=1" or token.startswith("nr_cpus=")
        for token in tokens
    ):
        raise ValueError("live CPU policy contains a conflicting cap")

    stability = key_values(section(text, "STABILITY"), "runtime stability sample")
    expected_stability = {
        "boot_id_after": identity["boot_id"],
        "online_after": "0-7",
        "offline_after": "8-9",
        "cpu8_online_control_after": "absent",
        "cpu9_online_control_after": "absent",
    }
    if set(stability) != set(expected_stability) | {"uptime_after"}:
        raise ValueError("runtime stability inventory changed")
    for key, value in expected_stability.items():
        if stability[key] != value:
            raise ValueError(f"runtime stability sample changed: {key}")
    before = decimal_seconds(identity["uptime_before"], "first uptime sample")
    after = decimal_seconds(stability["uptime_after"], "second uptime sample")
    if before < Decimal("45.0") or after < before or after - before < Decimal("4.5"):
        raise ValueError("runtime did not satisfy the 45+5-second stability window")

    first = stat_sample(section(text, "STAT1"))
    second = stat_sample(section(text, "STAT2"))
    expected_cpus = set(range(8))
    if set(first) != expected_cpus or set(second) != expected_cpus:
        raise ValueError("per-CPU accounting inventory is not CPU0 through CPU7")
    stalled = [cpu for cpu in sorted(expected_cpus) if second[cpu] <= first[cpu]]
    if stalled:
        raise ValueError(f"per-CPU accounting did not advance: {stalled}")

    dmesg = section(text, "DMESG")
    if "smp: Brought up 1 node, 8 CPUs" not in dmesg:
        raise ValueError("eight-CPU SMP completion line is absent")
    for cpu, mpidr in EXPECTED_BOOT_NODES.items():
        pattern = rf"CPU{cpu}: Booted secondary processor 0x{mpidr} \[0x410fd034\]"
        if re.search(pattern, dmesg) is None:
            raise ValueError(f"CPU{cpu} Cortex-A53 boot line is absent")
        if f"GICv3: CPU{cpu}:" not in dmesg:
            raise ValueError(f"CPU{cpu} GICv3 redistributor line is absent")
    if re.search(r"CPU(?:8|9): Booted secondary processor", dmesg):
        raise ValueError("a deferred Cortex-A72 CPU booted unexpectedly")
    if "boot rejected: A72 power sequence inactive" in dmesg:
        raise ValueError("the no-request experiment unexpectedly executed the reject gate")
    fault = FAULT.search(dmesg)
    if fault is not None:
        raise ValueError(f"kernel fault signature present: {fault.group(0)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path, required=True)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    args = parser.parse_args()
    try:
        text = args.capture.read_text(encoding="utf-8", errors="strict")
        validate(text, args.expected_installed_full_sha256)
        print("validation=candidate-ai-runtime-attribution")
        print("installed_full_hash=caller-attested-prior-readback")
        print("inherited_usb_banner=one-standalone-candidate-ac-line")
        print("live_config_sha256=exact-candidate-ad")
        print("cpu8_cpu9_enable_method=mediatek-mt6797-psci")
        print("compiled_gate_symbols=present")
        print("possible_present=0-9")
        print("online=0-7")
        print("offline=8-9")
        print("cpu8_cpu9_online_control=absent")
        print("cpu0_cpu7_accounting=advanced")
        print("stability_window=45-plus-5-seconds")
        print("gate_execution=absent")
        print("fault_signatures=absent")
        return 0
    except (OSError, UnicodeError, ValueError, KeyError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
