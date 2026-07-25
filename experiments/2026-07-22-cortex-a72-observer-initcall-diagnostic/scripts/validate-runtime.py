#!/usr/bin/env python3
"""Validate Candidate AF's bounded, read-only USB runtime capture."""

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
    "regulator_ignore_unused "
    "initcall_blacklist=mt6797_a72_power_driver_init"
)
BLACKLIST_TOKEN = "initcall_blacklist=mt6797_a72_power_driver_init"
BLACKLIST_DMESG = "initcall mt6797_a72_power_driver_init blacklisted"
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
DA9211_CALL = re.compile(r"calling\s+da9211_regulator_driver_init(?:\+|\s)")
DA9211_RETURN = re.compile(
    r"initcall da9211_regulator_driver_init(?:\+[^ ]+)? returned 0"
)
SECTION_ORDER = ("IDENTITY", "STATE1", "STAT1", "STATE2", "STAT2", "DMESG")


def validate_structure(text: str) -> None:
    previous_end = -1
    for name in SECTION_ORDER:
        begin = f"__AF_{name}_BEGIN__"
        end = f"__AF_{name}_END__"
        if text.count(begin) != 1 or text.count(end) != 1:
            raise ValueError(f"runtime marker is not unique: {name}")
        begin_at = text.index(begin)
        end_at = text.index(end)
        if begin_at <= previous_end or end_at <= begin_at:
            raise ValueError("runtime section chronology is not exact")
        previous_end = end_at + len(end)


def section(text: str, name: str) -> str:
    begin = f"__AF_{name}_BEGIN__"
    end = f"__AF_{name}_END__"
    begin_at = text.index(begin) + len(begin)
    end_at = text.index(end, begin_at)
    body = text[begin_at:end_at].lstrip("\r\n")
    lines = []
    for raw_line in body.replace("\r", "").splitlines():
        line = raw_line
        while line.startswith(EXPECTED_USB_PROMPT):
            line = line.removeprefix(EXPECTED_USB_PROMPT)
        lines.append(line)
    return "\n".join(lines).strip()


def key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"malformed runtime key/value line: {line}")
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError(f"duplicate runtime key: {key}")
        result[key] = value
    return result


def stat_sample(text: str) -> dict[int, int]:
    values: dict[int, int] = {}
    for line in text.splitlines():
        if not line:
            continue
        match = re.fullmatch(r"cpu([0-9]+)\s+(.+)", line.strip())
        if match is None:
            raise ValueError("malformed per-CPU accounting line")
        cpu = int(match.group(1))
        if cpu in values:
            raise ValueError(f"duplicate per-CPU accounting line: CPU{cpu}")
        fields = match.group(2).split()
        if not fields or any(not field.isdecimal() for field in fields):
            raise ValueError("malformed per-CPU accounting counter")
        values[cpu] = sum(int(field) for field in fields)
    return values


def validate_state(text: str) -> dict[str, str]:
    values = key_values(text)
    expected = {
        "observer_device_present": "1",
        "observer_device_driver": "unbound",
        "observer_driver_present": "0",
        "observer_attr_count": "0",
        "i2c6_count": "1",
        "da9214_count": "1",
        "da9214_compatible": "dlg,da9214",
        "da9214_parent": "i2c@1100e000",
        "da9214_driver": "da9211",
        "da9214_bucka_total": "1",
        "da9214_bucka_count": "1",
        "vproc_big_total": "1",
        "vproc_big_count": "1",
        "watchdog_fd_count": "0",
        "online": "0-7",
        "offline": "8-9",
    }
    for key, expected_value in expected.items():
        if values.get(key) != expected_value:
            raise ValueError(f"AF observer, I2C6, DA9214, CPU, or watchdog state differs: {key}")
    if values.get("i2c6_device") in (None, "", "unavailable"):
        raise ValueError("I2C6 platform device identity is absent")
    if values.get("i2c6_driver") in (None, "", "unavailable", "unbound"):
        raise ValueError("I2C6 platform controller is not bound")
    if re.fullmatch(r"[0-9]+-0068", values.get("da9214_device", "")) is None:
        raise ValueError("DA9214 I2C client identity is malformed")
    if values.get("da9214_bucka_parent") != values["da9214_device"]:
        raise ValueError("DA9214 BUCKA regulator belongs to another device")
    if values.get("vproc_big_parent") != values["da9214_device"]:
        raise ValueError("DA9214 BUCKB regulator belongs to another device")
    required_keys = set(expected) | {
        "i2c6_device",
        "i2c6_driver",
        "da9214_device",
        "da9214_bucka_parent",
        "vproc_big_parent",
        "boot_id",
        "uptime_seconds",
    }
    if set(values) != required_keys:
        raise ValueError("AF state inventory changed")
    if UUID.fullmatch(values["boot_id"]) is None:
        raise ValueError("AF state boot ID is malformed")
    if not values["uptime_seconds"].isdecimal():
        raise ValueError("AF state uptime is malformed")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        text = args.capture.read_text(encoding="utf-8", errors="strict")
        if text.count("GEMINI_USB_GADGET_ETHERNET_20260721_AC") != 1:
            raise ValueError("exact inherited Candidate AD USB marker is not unique")
        validate_structure(text)

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
            "config_kallsyms": "CONFIG_KALLSYMS=y",
            "config_da9211": "CONFIG_REGULATOR_DA9211=y",
            "config_a72_observer": "CONFIG_MTK_MT6797_A72_POWER=y",
        }
        for key, expected in expected_identity.items():
            if identity.get(key) != expected:
                raise ValueError(f"Candidate AF identity differs: {key}")
        required_identity = set(expected_identity) | {
            "boot_id",
            "uptime_seconds",
            "cpu8_enable_method",
            "cpu9_enable_method",
        }
        if set(identity) != required_identity:
            raise ValueError("Candidate AF identity inventory changed")
        if UUID.fullmatch(identity["boot_id"]) is None:
            raise ValueError("Candidate AF boot ID is malformed")
        if not identity["uptime_seconds"].isdecimal():
            raise ValueError("Candidate AF uptime is malformed")
        if int(identity["uptime_seconds"]) < 45:
            raise ValueError("runtime capture predates the 45-second observation boundary")
        if (
            identity["cpu8_enable_method"] != "mediatek,mt6797-psci"
            or identity["cpu9_enable_method"] != "mediatek,mt6797-psci"
        ):
            raise ValueError("Cortex-A72 rejecting enable methods are not exact")
        tokens = identity["cmdline"].split()
        for token in ("maxcpus=8", "regulator_ignore_unused", BLACKLIST_TOKEN):
            if tokens.count(token) != 1:
                raise ValueError(f"live forced-command-line token is not exact: {token}")
        if "maxcpus=1" in tokens or "nosmp" in tokens or any(
            token.startswith("nr_cpus=") for token in tokens
        ):
            raise ValueError("live CPU policy contains a conflicting cap")

        first = validate_state(section(text, "STATE1"))
        second = validate_state(section(text, "STATE2"))
        if first["boot_id"] != identity["boot_id"] or second["boot_id"] != identity["boot_id"]:
            raise ValueError("boot ID changed during Candidate AF collection")
        if int(first["uptime_seconds"]) < 45:
            raise ValueError("first AF state read predates the 45-second boundary")
        if int(second["uptime_seconds"]) < int(first["uptime_seconds"]) + 5:
            raise ValueError("AF state reads are not separated by five seconds")
        stable_keys = set(first) - {"uptime_seconds"}
        if any(first[key] != second[key] for key in stable_keys):
            raise ValueError("AF observer, regulator, CPU, or boot state changed across reads")

        first_stat = stat_sample(section(text, "STAT1"))
        second_stat = stat_sample(section(text, "STAT2"))
        expected_cpus = set(range(8))
        if set(first_stat) != expected_cpus or set(second_stat) != expected_cpus:
            raise ValueError("per-CPU accounting inventory is not CPU0 through CPU7")
        stalled = [
            cpu for cpu in sorted(expected_cpus) if second_stat[cpu] <= first_stat[cpu]
        ]
        if stalled:
            raise ValueError(f"per-CPU accounting did not advance: {stalled}")

        dmesg = section(text, "DMESG")
        if "smp: Brought up 1 node, 8 CPUs" not in dmesg:
            raise ValueError("eight-CPU SMP completion line is absent")
        if dmesg.count(BLACKLIST_DMESG) != 1:
            raise ValueError("unique exact observer initcall-blacklist line is absent")
        da9211_calls = list(DA9211_CALL.finditer(dmesg))
        da9211_returns = list(DA9211_RETURN.finditer(dmesg))
        if len(da9211_calls) != 1 or len(da9211_returns) != 1:
            raise ValueError("independent DA9211 initcall markers are not unique")
        if da9211_calls[0].start() >= da9211_returns[0].start():
            raise ValueError("DA9211 initcall return precedes its call")
        if "observer resources ready:" in dmesg or re.search(
            r"mt6797-a72-power.*(?:probe|resources ready)", dmesg, re.IGNORECASE
        ):
            raise ValueError("observer registered or probed despite its blacklisted initcall")
        if re.search(r"CPU(?:8|9): Booted secondary processor", dmesg):
            raise ValueError("a deferred Cortex-A72 CPU booted unexpectedly")
        if re.search(r"mt6797-psci: CPU(?:8|9) boot rejected", dmesg):
            raise ValueError("a Cortex-A72 online request occurred during AF")
        fault = FAULT.search(dmesg)
        if fault is not None:
            raise ValueError(f"kernel fault signature present: {fault.group(0)}")

        print("validation=candidate-af-a72-observer-initcall-runtime")
        print(f"boot_id={identity['boot_id']}")
        print(f"uptime_seconds={second['uptime_seconds']}")
        print("cmdline_blacklist_token=exact")
        print("observer_initcall=blacklisted")
        print("observer_device=present-unbound")
        print("observer_driver_sysfs=absent")
        print("observer_attributes=absent")
        print("i2c6=present-bound")
        print("da9211_initcall=returned-0")
        print("da9214_client=bound-da9211")
        print("da9214_regulators=bucka-plus-vproc-big")
        print("possible_present=0-9")
        print("online=0-7")
        print("offline=8-9")
        print("cpu0_cpu7_accounting=advanced")
        print("watchdog_userspace_fd=absent")
        print("automatic_reboot_through_observation_boundary=absent")
        print("fault_signatures=absent")
        print("collector_operations=read-only")
        print("active_a72_power_write=none")
        print("regulator_voltage_or_enable_request=none")
        print("known_supplier_side_effects=da9211-page-selector-write+scpsys-clock-gating")
        return 0
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
