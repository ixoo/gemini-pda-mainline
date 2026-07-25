#!/usr/bin/env python3
"""Validate Candidate AG's bounded, read-only USB simplefb runtime capture."""

# Source foundation: Candidate AF validator SHA-256
# 4accaf9bdea011b0dea31550fd0e1473c920c7008abd38fe57555b75e2d2463b.
# Candidate AG adds only the restored live-DT/simplefb/fb0 contract and a
# caller-supplied prior full-partition-readback checksum attestation.

from __future__ import annotations

import argparse
import pathlib
import re
import stat
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
EXPECTED_INSTALLED_FULL_SHA256 = (
    "63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14"
)
EXPECTED_SIMPLEFB_OF_NODE = (
    "/sys/firmware/devicetree/base/chosen/framebuffer@7dfb0000"
)
EXPECTED_SIMPLEFB_COMPATIBLE_HEX = "73696d706c652d6672616d6562756666657200"
EXPECTED_RUNTIME_FB_COMPATIBLE_HEX = "6d6564696174656b2c6672616d6562756666657200"
EXPECTED_FB_REG_HEX = "000000007dfb00000000000001f90000"
EXPECTED_SIMPLEFB_CLOCKS_HEX = "000000030000002d0000000600000006"
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
SIMPLEFB_CALL = re.compile(r"calling\s+simplefb_driver_init(?:\+|\s)")
SIMPLEFB_RETURN = re.compile(
    r"initcall simplefb_driver_init(?:\+[^ ]+)? returned 0"
)
SIMPLEFB_ERROR = re.compile(
    r"^.*(?:simple-framebuffer|simplefb).*(?:"
    r"clock[^\n]*(?:fail|error|not found|invalid|defer|unavailable)|"
    r"(?:fail|error|defer|unable)[^\n]*clock|"
    r"probe[^\n]*(?:fail|error|defer)|"
    r"(?:fail|error|defer)[^\n]*probe).*$",
    re.IGNORECASE | re.MULTILINE,
)
RAW_BEACON = re.compile(
    r"(?:GEMINI[-_ ]AG[-_ ].*(?:RAW|EARLY).*(?:FRAMEBUFFER|FB).*(?:BEACON|MARKER)|"
    r"RAW_FRAMEBUFFER_BEACON)",
    re.IGNORECASE,
)
SECTION_ORDER = ("HOST", "IDENTITY", "STATE1", "STAT1", "STATE2", "STAT2", "DMESG")


def validate_structure(text: str) -> None:
    previous_end = -1
    for name in SECTION_ORDER:
        begin = f"__AG_{name}_BEGIN__"
        end = f"__AG_{name}_END__"
        if text.count(begin) != 1 or text.count(end) != 1:
            raise ValueError(f"runtime marker is not unique: {name}")
        begin_at = text.index(begin)
        end_at = text.index(end)
        if begin_at <= previous_end or end_at <= begin_at:
            raise ValueError("runtime section chronology is not exact")
        previous_end = end_at + len(end)


def section(text: str, name: str) -> str:
    begin = f"__AG_{name}_BEGIN__"
    end = f"__AG_{name}_END__"
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
        "chosen_framebuffer_child_count": "1",
        "chosen_simplefb_compatible_count": "1",
        "simplefb_node_present": "1",
        "chosen_address_cells_hex": "00000002",
        "chosen_size_cells_hex": "00000002",
        "chosen_ranges_hex": "",
        "simplefb_compatible_hex": EXPECTED_SIMPLEFB_COMPATIBLE_HEX,
        "simplefb_reg_hex": EXPECTED_FB_REG_HEX,
        "simplefb_width_hex": "00000438",
        "simplefb_height_hex": "00000870",
        "simplefb_stride_hex": "00001100",
        "simplefb_format_hex": "613872386738623800",
        "simplefb_clocks_hex": EXPECTED_SIMPLEFB_CLOCKS_HEX,
        "simplefb_memory_region_present": "0",
        "simplefb_child_count": "0",
        "simplefb_unexpected_entry_count": "0",
        "runtime_framebuffer_reservation_count": "1",
        "runtime_framebuffer_reservation_present": "1",
        "runtime_framebuffer_compatible_hex": EXPECTED_RUNTIME_FB_COMPATIBLE_HEX,
        "runtime_framebuffer_reg_hex": EXPECTED_FB_REG_HEX,
        "runtime_framebuffer_name_hex": (
            "6d626c6f636b2d332d6672616d6562756666657200"
        ),
        "runtime_framebuffer_no_map_present": "1",
        "runtime_framebuffer_no_map_hex": "",
        "runtime_framebuffer_child_count": "0",
        "runtime_framebuffer_unexpected_entry_count": "0",
        "simplefb_platform_count": "1",
        "simplefb_platform_present": "1",
        "simplefb_platform_driver": "simple-framebuffer",
        "simplefb_platform_of_node": EXPECTED_SIMPLEFB_OF_NODE,
        "fb_count": "1",
        "fb0_present": "1",
        "fb0_name": "simple",
        "fb0_virtual_size": "1080,2160",
        "fb0_bits_per_pixel": "32",
        "fb0_stride": "4352",
        "fb0_platform_device": "7dfb0000.framebuffer",
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
            raise ValueError(
                "AG simplefb, observer, I2C6, DA9214, CPU, or watchdog "
                f"state differs: {key}"
            )
    if values.get("simplefb_name_hex") not in (
        "missing",
        "6672616d6562756666657200",
    ):
        raise ValueError("live simplefb generated name property is unexpected")
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
        "simplefb_name_hex",
        "boot_id",
        "uptime_seconds",
    }
    if set(values) != required_keys:
        raise ValueError("AG state inventory changed")
    if UUID.fullmatch(values["boot_id"]) is None:
        raise ValueError("AG state boot ID is malformed")
    if not values["uptime_seconds"].isdecimal():
        raise ValueError("AG state uptime is malformed")
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        capture_info = args.capture.lstat()
        if (
            args.capture.is_symlink()
            or not stat.S_ISREG(capture_info.st_mode)
            or capture_info.st_size == 0
        ):
            raise ValueError("runtime capture is missing, empty, or unsafe")
        text = args.capture.read_text(encoding="utf-8", errors="strict")
        if text.count("GEMINI_USB_GADGET_ETHERNET_20260721_AC") != 1:
            raise ValueError("exact inherited Candidate AD USB marker is not unique")
        validate_structure(text)

        host = key_values(section(text, "HOST"))
        expected_host = {
            "installed_full_sha256_input": EXPECTED_INSTALLED_FULL_SHA256,
            "attestation_basis": "caller-supplied-prior-full-partition-readback",
            "device_partition_read_during_collection": "no",
        }
        if host != expected_host:
            raise ValueError("AG host-side installed-image attestation is not exact")

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
            "config_simplefb": "CONFIG_FB_SIMPLE=y",
        }
        for key, expected in expected_identity.items():
            if identity.get(key) != expected:
                raise ValueError(f"Candidate AG identity differs: {key}")
        required_identity = set(expected_identity) | {
            "boot_id",
            "uptime_seconds",
            "cpu8_enable_method",
            "cpu9_enable_method",
        }
        if set(identity) != required_identity:
            raise ValueError("Candidate AG identity inventory changed")
        if UUID.fullmatch(identity["boot_id"]) is None:
            raise ValueError("Candidate AG boot ID is malformed")
        if not identity["uptime_seconds"].isdecimal():
            raise ValueError("Candidate AG uptime is malformed")
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
            raise ValueError("boot ID changed during Candidate AG collection")
        if int(first["uptime_seconds"]) < 45:
            raise ValueError("first AG state read predates the 45-second boundary")
        if int(second["uptime_seconds"]) < int(first["uptime_seconds"]) + 5:
            raise ValueError("AG state reads are not separated by five seconds")
        stable_keys = set(first) - {"uptime_seconds"}
        if any(first[key] != second[key] for key in stable_keys):
            raise ValueError(
                "AG simplefb, observer, regulator, CPU, or boot state changed across reads"
            )

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
        reserved_line = (
            "OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff "
            "(32320 KiB) nomap non-reusable mblock-3-framebuffer"
        )
        if dmesg.count(reserved_line) != 1:
            raise ValueError("unique exact LK-injected framebuffer reservation line is absent")
        simplefb_lines = (
            "simple-framebuffer 7dfb0000.framebuffer: framebuffer at "
            "0x7dfb0000, 0x1f90000 bytes",
            "simple-framebuffer 7dfb0000.framebuffer: format=a8r8g8b8, "
            "mode=1080x2160x32, linelength=4352",
            "simple-framebuffer 7dfb0000.framebuffer: fb0: simplefb registered!",
        )
        for line in simplefb_lines:
            if dmesg.count(line) != 1:
                raise ValueError(f"unique exact simplefb registration line is absent: {line}")
        simplefb_calls = list(SIMPLEFB_CALL.finditer(dmesg))
        simplefb_returns = list(SIMPLEFB_RETURN.finditer(dmesg))
        if len(simplefb_calls) != 1 or len(simplefb_returns) != 1:
            raise ValueError("simplefb initcall markers are not unique and successful")
        first_simplefb_log = dmesg.index(simplefb_lines[0])
        last_simplefb_log = dmesg.index(simplefb_lines[-1])
        if not (
            simplefb_calls[0].start()
            < first_simplefb_log
            < last_simplefb_log
            < simplefb_returns[0].start()
        ):
            raise ValueError("simplefb initcall and registration chronology is not exact")
        simplefb_error = SIMPLEFB_ERROR.search(dmesg)
        if simplefb_error is not None:
            raise ValueError(
                f"simplefb clock or probe error is present: {simplefb_error.group(0)}"
            )
        if RAW_BEACON.search(text) is not None:
            raise ValueError("superseded raw-framebuffer beacon marker is present")
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
            raise ValueError("a Cortex-A72 online request occurred during AG")
        fault = FAULT.search(dmesg)
        if fault is not None:
            raise ValueError(f"kernel fault signature present: {fault.group(0)}")

        print("validation=candidate-ag-simplefb-observation-restoration-runtime")
        print(f"boot_id={identity['boot_id']}")
        print(f"uptime_seconds={second['uptime_seconds']}")
        print("installed_full_sha256_input=exact-prior-readback-attestation")
        print("installed_full_hash_reverified_during_collection=no")
        print("chosen_simplefb=exact-live-node")
        print("chosen_simplefb_clocks=infracfg-45+topckgen-6")
        print("lk_runtime_framebuffer_reservation=exact-no-map")
        print("simplefb_platform=bound")
        print("fb0=1080x2160x32-stride4352-simple")
        print("simplefb_clock_or_probe_errors=absent")
        print("raw_framebuffer_beacon=absent")
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
        print("visual_only_result=insufficient-for-pass")
        print("pass_basis=exact-usb-runtime-at-45-plus-5-seconds")
        return 0
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
