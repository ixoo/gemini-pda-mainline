#!/usr/bin/env python3
"""Validate Candidate AE's bounded read-only USB runtime capture."""

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
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused"
)
EXPECTED_USB_PROMPT = "GEMINI-AC-USB# "
UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
FAULT = re.compile(
    r"(?:Kernel panic|\bOops:|\bBUG:|\bSError\b|RCU stall|rcu:.*stall|"
    r"hung task|CPU[0-9]+: failed|failed to boot|psci.*(?:fail|error))",
    re.IGNORECASE,
)
SNAPSHOT = re.compile(
    r"cpus=8,9 pwrap_reset_acquired=1\n"
    r"vproc_enabled=1 vproc_uv=1000000\n"
    r"spm_poweron=0x[0-9a-f]{8} spm_ext_buck_iso=0x[0-9a-f]{8}\n"
    r"mp2_sync_dcm=0x[0-9a-f]{8} big_armpll=0x[0-9a-f]{8}"
)


def section(text: str, name: str) -> str:
    match = re.search(
        rf"__AE_{re.escape(name)}_BEGIN__\r?\n(.*?)__AE_{re.escape(name)}_END__",
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


def key_values(text: str, excluded: tuple[str, str] | None = None) -> dict[str, str]:
    working = text
    if excluded is not None:
        begin, end = excluded
        match = re.search(
            rf"^{re.escape(begin)}\n.*?^{re.escape(end)}$",
            working,
            re.MULTILINE | re.DOTALL,
        )
        if match is None:
            raise ValueError(f"missing nested section: {begin}")
        working = working[: match.start()] + working[match.end() :]
    result: dict[str, str] = {}
    for line in working.splitlines():
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"malformed runtime key/value line: {line}")
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError(f"duplicate runtime key: {key}")
        result[key] = value
    return result


def observer(text: str) -> tuple[dict[str, str], str]:
    match = re.search(
        r"^snapshot_begin\n(.*?)^snapshot_end$", text, re.MULTILINE | re.DOTALL
    )
    if match is None:
        raise ValueError("observer snapshot section is absent")
    snapshot = match.group(1).strip()
    values = key_values(text, ("snapshot_begin", "snapshot_end"))
    required = {
        "observer_count": "1",
        "observer_device": "10222000.a72-power",
        "ready": "0",
        "resources_ready": "1",
        "abi": "observer-v1",
        "hooks_armed": "0",
        "provider_mode": "observe-only",
        "online": "0-7",
        "offline": "8-9",
    }
    if any(values.get(key) != value for key, value in required.items()):
        raise ValueError("observer ABI, mode, or CPU masks are not exact")
    if set(values) != set(required) | {"boot_id", "uptime_seconds"}:
        raise ValueError("observer runtime inventory changed")
    if UUID.fullmatch(values["boot_id"]) is None:
        raise ValueError("observer boot ID is malformed")
    if not values["uptime_seconds"].isdecimal():
        raise ValueError("observer uptime is malformed")
    if SNAPSHOT.fullmatch(snapshot) is None:
        raise ValueError("observer resource snapshot is not the expected fixed state")
    return values, snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        text = args.capture.read_text(encoding="utf-8", errors="strict")
        if "GEMINI_USB_GADGET_ETHERNET_20260721_AC" not in text:
            raise ValueError("exact inherited Candidate AD USB marker is absent")

        identity = key_values(section(text, "IDENTITY"))
        expected_identity = {
            "cmdline": EXPECTED_CMDLINE,
            "possible": "0-9",
            "present": "0-9",
            "online": "0-7",
            "offline": "8-9",
            "nproc": "8",
            "kernel": "7.1.3-gemini-observability-L",
            "config_cmdline": f'CONFIG_CMDLINE="{EXPECTED_CMDLINE}"',
            "config_force": "CONFIG_CMDLINE_FORCE=y",
            "config_da9211": "CONFIG_REGULATOR_DA9211=y",
            "config_a72_observer": "CONFIG_MTK_MT6797_A72_POWER=y",
        }
        for key, expected in expected_identity.items():
            if identity.get(key) != expected:
                raise ValueError(f"Candidate AE identity differs: {key}")
        if set(identity) != set(expected_identity) | {
            "boot_id",
            "uptime_seconds",
            "cpu8_enable_method",
            "cpu9_enable_method",
        }:
            raise ValueError("Candidate AE identity inventory changed")
        if UUID.fullmatch(identity["boot_id"]) is None:
            raise ValueError("Candidate AE boot ID is malformed")
        if not identity["uptime_seconds"].isdecimal():
            raise ValueError("Candidate AE uptime is malformed")
        if int(identity["uptime_seconds"]) < 45:
            raise ValueError("runtime capture predates the 45-second observation boundary")
        if (
            identity["cpu8_enable_method"] != "mediatek,mt6797-psci"
            or identity["cpu9_enable_method"] != "mediatek,mt6797-psci"
        ):
            raise ValueError("Cortex-A72 rejecting enable methods are not exact")
        tokens = identity["cmdline"].split()
        if tokens.count("maxcpus=8") != 1 or tokens.count("regulator_ignore_unused") != 1:
            raise ValueError("live CPU cap or regulator preservation token is not exact")
        if "maxcpus=1" in tokens or "nosmp" in tokens or any(
            token.startswith("nr_cpus=") for token in tokens
        ):
            raise ValueError("live CPU policy contains a conflicting cap")

        first, snapshot_first = observer(section(text, "OBSERVER1"))
        second, snapshot_second = observer(section(text, "OBSERVER2"))
        if first["boot_id"] != identity["boot_id"] or second["boot_id"] != identity["boot_id"]:
            raise ValueError("boot ID changed during Candidate AE collection")
        if int(first["uptime_seconds"]) < 45:
            raise ValueError("first observer read predates the 45-second boundary")
        if int(second["uptime_seconds"]) < int(first["uptime_seconds"]) + 5:
            raise ValueError("observer reads are not separated by five seconds")
        if snapshot_first != snapshot_second:
            raise ValueError("observer snapshot changed across repeated reads")

        dmesg = section(text, "DMESG")
        if "smp: Brought up 1 node, 8 CPUs" not in dmesg:
            raise ValueError("eight-CPU SMP completion line is absent")
        observer_lines = [
            line
            for line in dmesg.splitlines()
            if "observer resources ready: vproc=1000000uV enabled=1; CPU_ON denied"
            in line
        ]
        if len(observer_lines) != 1 or "mt6797-a72-power" not in observer_lines[0]:
            raise ValueError("unique successful observer probe line is absent")
        if re.search(r"CPU(?:8|9): Booted secondary processor", dmesg):
            raise ValueError("a deferred Cortex-A72 CPU booted unexpectedly")
        if re.search(r"mt6797-psci: CPU(?:8|9) boot rejected", dmesg):
            raise ValueError("a Cortex-A72 online request occurred during observer-only AE")
        fault = FAULT.search(dmesg)
        if fault is not None:
            raise ValueError(f"kernel fault signature present: {fault.group(0)}")

        print("validation=candidate-ae-a72-observer-runtime")
        print(f"boot_id={identity['boot_id']}")
        print(f"uptime_seconds={second['uptime_seconds']}")
        print("possible_present=0-9")
        print("online=0-7")
        print("offline=8-9")
        print("observer_ready=0")
        print("observer_resources_ready=1")
        print("observer_hooks_armed=0")
        print("observer_mode=observe-only")
        print("vproc_big=enabled-1000000uV")
        print("cpu8_cpu9=offline-not-requested")
        print("fault_signatures=absent")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
