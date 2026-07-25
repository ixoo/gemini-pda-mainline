#!/usr/bin/env python3
"""Validate a bounded Candidate AD runtime capture from the USB shell."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


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
EXPECTED_BOOT_NODES = {
    1: "0000000001",
    2: "0000000002",
    3: "0000000003",
    4: "0000000100",
    5: "0000000101",
    6: "0000000102",
    7: "0000000103",
}
EXPECTED_USB_PROMPT = "GEMINI-AC-USB# "
FAULT = re.compile(
    r"(?:Kernel panic|\bOops:|\bBUG:|\bSError\b|RCU stall|rcu:.*stall|hung task|"
    r"CPU[0-9]+: failed|failed to boot|psci.*(?:fail|error))",
    re.IGNORECASE,
)


def section(text: str, name: str) -> str:
    match = re.search(
        rf"__AD_{re.escape(name)}_BEGIN__\r?\n(.*?)__AD_{re.escape(name)}_END__",
        text,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"missing runtime section: {name}")
    lines = []
    for raw_line in match.group(1).replace("\r", "").splitlines():
        line = raw_line
        while line.startswith(EXPECTED_USB_PROMPT):
            line = line.removeprefix(EXPECTED_USB_PROMPT)
        lines.append(line)
    return "\n".join(lines).strip()


def stat_sample(text: str) -> dict[int, int]:
    values: dict[int, int] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"cpu([0-9]+)\s+(.+)", line.strip())
        if match is None:
            continue
        fields = match.group(2).split()
        if not fields or any(not field.isdecimal() for field in fields):
            raise ValueError("malformed per-CPU accounting line")
        values[int(match.group(1))] = sum(int(field) for field in fields)
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        text = args.capture.read_text(encoding="utf-8", errors="strict")
        if "GEMINI_USB_GADGET_ETHERNET_20260721_AC" not in text:
            raise ValueError("exact inherited AC USB marker is absent")
        identity = section(text, "IDENTITY")
        required = {
            f"cmdline={EXPECTED_CMDLINE}",
            "possible=0-9",
            "present=0-9",
            "online=0-7",
            "offline=8-9",
            "nproc=8",
            "kernel=7.1.3-gemini-observability-L",
            f'config_cmdline=CONFIG_CMDLINE="{EXPECTED_CMDLINE}"',
            "config_force=CONFIG_CMDLINE_FORCE=y",
        }
        identity_lines = set(identity.splitlines())
        if not required <= identity_lines:
            raise ValueError("Candidate AD identity or CPU masks are not exact")
        cmdline = next(line.removeprefix("cmdline=") for line in identity_lines if line.startswith("cmdline="))
        if cmdline.split().count("maxcpus=8") != 1 or any(token in cmdline for token in ("maxcpus=1", "nosmp", "nr_cpus=")):
            raise ValueError("live CPU policy contains a conflicting cap")

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
        fault = FAULT.search(dmesg)
        if fault is not None:
            raise ValueError(f"kernel fault signature present: {fault.group(0)}")

        print("validation=candidate-ad-runtime-smp8")
        print("cmdline=maxcpus-8-exact")
        print("possible_present=0-9")
        print("online=0-7")
        print("offline=8-9")
        print("nproc=8")
        print("cpu0_cpu7_accounting=advanced")
        print("cpu1_cpu7_boot_lines=present")
        print("cpu1_cpu7_gicv3_lines=present")
        print("cpu8_cpu9=offline-not-booted")
        print("fault_signatures=absent")
        return 0
    except (OSError, UnicodeError, ValueError, StopIteration) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
