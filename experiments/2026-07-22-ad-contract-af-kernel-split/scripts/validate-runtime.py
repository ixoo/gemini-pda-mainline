#!/usr/bin/env python3
"""Validate Candidate AH's bounded, read-only exact-USB runtime capture."""

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
EXPECTED_CONFIG_SHA256 = (
    "bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63"
)
BLACKLIST_TOKEN = "initcall_blacklist=mt6797_a72_power_driver_init"
BLACKLIST_DMESG = "initcall mt6797_a72_power_driver_init blacklisted"
USB_MARKER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
USB_PROMPT = "GEMINI-AC-USB# "
REJECTING_METHOD = "mediatek,mt6797-psci"
EXPECTED_INSTALLED_FULL_SHA256 = (
    "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012"
)
UUID = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}"
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
EXPECTED_KEYMAP_OUTPUT_HEX = (
    "6b65796d61705f726561646261636b3d7665726966696564207461626c65733d38"
    "207061796c6f61645f656e74726965733d31303234206b65726e656c5f656e7472"
    "6965733d3230343820686967685f68616c7665733d4b5f484f4c45207461626c65"
    "333d4b5f414c4c4f434154454420756e6465636c617265645f7461626c65733d4b"
    "5f4e4f535543484d415020756e69636f64655f6d6f64653d4b5f554e49434f4445"
)
EXPECTED_IDENTITY = {
    "cmdline": EXPECTED_CMDLINE,
    "possible": "0-9",
    "present": "0-9",
    "online": "0-7",
    "offline": "8-9",
    "nproc": "8",
    "kernel": "7.1.3-gemini-observability-L",
    "config_sha256": EXPECTED_CONFIG_SHA256,
    "config_cmdline": f'CONFIG_CMDLINE="{EXPECTED_CMDLINE}"',
    "config_force": "CONFIG_CMDLINE_FORCE=y",
    "config_a72_observer": "CONFIG_MTK_MT6797_A72_POWER=y",
    "config_da9211": "CONFIG_REGULATOR_DA9211=y",
    "config_simplefb": "CONFIG_FB_SIMPLE=y",
    "config_aw9523": "CONFIG_PINCTRL_AW9523=y",
    "config_matrix": "CONFIG_KEYBOARD_MATRIX=y",
    "cpu8_enable_method": REJECTING_METHOD,
    "cpu9_enable_method": REJECTING_METHOD,
    "init_sha256": "c938a65e963dae815c5fa9e51442026b8464d470a10bb9615d8de73599295222",
    "busybox_sha256": "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933",
    "ac_record_sha256": "56a2e0944e77cbf18ab9b1146c14ee0bc3a3ac800fb13a72fe8136aa32ae608a",
    "usb_net_sha256": "2144721bf4344f5af04fe59133f9848e54bd9315a9b51cd96534774242603ead",
    "usb_shell_sha256": "a16caea4c54196041175254bef26d165b214efd1c1f9bc1d0e2ecad83670aa71",
    "local_shell_sha256": "2569bb4ebe8f1617e5e3c7f0885d9a487f36a4a687a663851b5f21240583047d",
    "reboot_sha256": "3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7",
    "keymap_sha256": "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c",
    "keymap_verifier_sha256": "29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238",
    "unicode_helper_sha256": "5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650",
    "input_helper_sha256": "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602",
}
EXPECTED_STATE = {
    "chosen_framebuffer_child_count": "1",
    "chosen_simplefb_compatible_count": "1",
    "simplefb_node_present": "1",
    "chosen_address_cells_hex": "00000002",
    "chosen_size_cells_hex": "00000002",
    "chosen_ranges_hex": "",
    "simplefb_compatible_hex": "73696d706c652d6672616d6562756666657200",
    "simplefb_reg_hex": "000000007dfb00000000000001f90000",
    "simplefb_width_hex": "00000438",
    "simplefb_height_hex": "00000870",
    "simplefb_stride_hex": "00001100",
    "simplefb_format_hex": "613872386738623800",
    "simplefb_clocks_hex": "000000030000002d0000000600000006",
    "simplefb_memory_region_present": "0",
    "runtime_framebuffer_reservation_count": "1",
    "runtime_framebuffer_reservation_present": "1",
    "runtime_framebuffer_compatible_hex": "6d6564696174656b2c6672616d6562756666657200",
    "runtime_framebuffer_reg_hex": "000000007dfb00000000000001f90000",
    "runtime_framebuffer_no_map_present": "1",
    "simplefb_platform_count": "1",
    "simplefb_platform_present": "1",
    "simplefb_platform_driver": "simple-framebuffer",
    "fb_count": "1",
    "fb0_present": "1",
    "fb0_name": "simple",
    "fb0_virtual_size": "1080,2160",
    "fb0_bits_per_pixel": "32",
    "fb0_stride": "4352",
    "observer_dt_node_present": "0",
    "observer_device_present": "0",
    "observer_driver_present": "0",
    "i2c6_dt_node_present": "1",
    "i2c6_status_hex": "64697361626c656400",
    "i2c6_platform_count": "0",
    "da9214_dt_count": "0",
    "da9214_client_count": "0",
    "da9214_bucka_count": "0",
    "vproc_big_count": "0",
    "aw9523_compatible_hex": "6177696e69632c6177393532332d70696e6374726c00",
    "aw9523_status_hex": "6f6b617900",
    "aw9523_client_count": "1",
    "aw9523_driver": "aw9523-pinctrl",
    "matrix_compatible_hex": "6770696f2d6d61747269782d6b657970616400",
    "matrix_status_hex": "6f6b617900",
    "matrix_poll_interval_hex": "00000014",
    "matrix_col_scan_delay_hex": "00000002",
    "matrix_device_present": "1",
    "matrix_driver": "matrix-keypad",
    "matrix_event_count": "1",
    "matrix_event_node": "/dev/input/event0",
    "matrix_event_char_device": "1",
    "keymap_verify_rc": "0",
    "keymap_verify_output_hex": EXPECTED_KEYMAP_OUTPUT_HEX,
    "keymap_ready_count": "1",
    "usb0_count": "1",
    "usb0_address": "42:00:15:19:82:01",
    "usb0_carrier": "1",
    "usb0_operstate": "up",
    "usb0_ipv4_total": "1",
    "usb0_ipv4_exact": "1",
    "udc_count": "1",
    "udc_name": "11271000.usb",
    "udc_state": "configured",
    "ac_service_count": "1",
    "ac_ready_count": "1",
    "watchdog_fd_count": "0",
    "online": "0-7",
    "offline": "8-9",
}

FAULT = re.compile(
    r"(?:Kernel panic|\bOops:|\bBUG:|\bSError\b|RCU stall|rcu:.*stall|"
    r"hung task|CPU[0-9]+: failed|failed to boot|psci.*(?:fail|error))",
    re.IGNORECASE,
)
SIMPLEFB_CALL = re.compile(r"calling\s+simplefb_driver_init(?:\+|\s)")
SIMPLEFB_RETURN = re.compile(
    r"initcall simplefb_driver_init(?:\+[^ ]+)? returned 0"
)
DA9211_CALL = re.compile(r"calling\s+da9211_regulator_driver_init(?:\+|\s)")
DA9211_RETURN = re.compile(
    r"initcall da9211_regulator_driver_init(?:\+[^ ]+)? returned 0"
)
SIMPLEFB_ERROR = re.compile(
    r"^.*(?:simple-framebuffer|simplefb).*(?:"
    r"clock[^\n]*(?:fail|error|not found|invalid|defer|unavailable)|"
    r"(?:fail|error|defer|unable)[^\n]*clock|"
    r"probe[^\n]*(?:fail|error|defer)|"
    r"(?:fail|error|defer)[^\n]*probe).*$",
    re.IGNORECASE | re.MULTILINE,
)
A72_REQUEST = re.compile(
    r"(?:mt6797-psci: CPU(?:8|9) boot rejected|"
    r"CPU(?:8|9): Booted secondary processor|"
    r"(?:CPU_ON|cpu_on).*(?:CPU(?:8|9)|0x20[01])|"
    r"(?:CPU(?:8|9)|0x20[01]).*(?:CPU_ON|cpu_on))"
)
SECTION_ORDER = ("HOST", "IDENTITY", "STATE1", "STAT1", "STATE2", "STAT2", "DMESG")


def validate_structure(text: str) -> None:
    previous_end = -1
    for name in SECTION_ORDER:
        begin = f"__AH_{name}_BEGIN__"
        end = f"__AH_{name}_END__"
        if text.count(begin) != 1 or text.count(end) != 1:
            raise ValueError(f"runtime marker is not unique: {name}")
        begin_at = text.index(begin)
        end_at = text.index(end)
        if begin_at <= previous_end or end_at <= begin_at:
            raise ValueError("runtime section chronology is not exact")
        previous_end = end_at + len(end)


def section(text: str, name: str) -> str:
    begin = f"__AH_{name}_BEGIN__"
    end = f"__AH_{name}_END__"
    begin_at = text.index(begin) + len(begin)
    end_at = text.index(end, begin_at)
    body = text[begin_at:end_at].lstrip("\r\n")
    lines: list[str] = []
    for raw_line in body.replace("\r", "").splitlines():
        line = raw_line
        while line.startswith(USB_PROMPT):
            line = line.removeprefix(USB_PROMPT)
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
    for key, expected in EXPECTED_STATE.items():
        if values.get(key) != expected:
            raise ValueError(f"Candidate AH AD-board runtime contract differs: {key}")
    required = set(EXPECTED_STATE) | {"boot_id", "uptime_seconds"}
    if set(values) != required:
        raise ValueError("Candidate AH state inventory changed")
    if UUID.fullmatch(values["boot_id"]) is None:
        raise ValueError("Candidate AH state boot ID is malformed")
    if not values["uptime_seconds"].isdecimal():
        raise ValueError("Candidate AH state uptime is malformed")
    return values


def require_unique_ordered_pair(
    text: str, call: re.Pattern[str], returned: re.Pattern[str], label: str
) -> None:
    calls = list(call.finditer(text))
    returns = list(returned.finditer(text))
    if len(calls) != 1 or len(returns) != 1:
        raise ValueError(f"{label} initcall markers are not uniquely successful")
    if calls[0].start() >= returns[0].start():
        raise ValueError(f"{label} initcall return precedes its call")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        info = args.capture.lstat()
        if args.capture.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size == 0:
            raise ValueError("runtime capture is missing, empty, or unsafe")
        text = args.capture.read_text(encoding="utf-8", errors="strict")
        validate_structure(text)

        identity_begin = text.index("__AH_IDENTITY_BEGIN__")
        pre_identity_lines = text[:identity_begin].replace("\r", "").splitlines()
        if USB_MARKER not in pre_identity_lines:
            raise ValueError("exact inherited AD USB session banner is absent")

        host = key_values(section(text, "HOST"))
        expected_host_keys = {
            "installed_full_sha256_input",
            "attestation_basis",
            "device_partition_read_during_collection",
            "interface",
            "mac",
            "host_address",
            "route_interface",
        }
        if set(host) != expected_host_keys:
            raise ValueError("Candidate AH host attestation inventory changed")
        if host["installed_full_sha256_input"] != EXPECTED_INSTALLED_FULL_SHA256:
            raise ValueError("installed full-partition hash is not exact validated AH")
        if host["attestation_basis"] != "caller-supplied-prior-full-partition-readback":
            raise ValueError("installed full-partition attestation basis changed")
        if host["device_partition_read_during_collection"] != "no":
            raise ValueError("runtime collection unexpectedly read the device partition")
        if re.fullmatch(r"[A-Za-z0-9]+", host["interface"]) is None:
            raise ValueError("host interface identity is malformed")
        if host["route_interface"] != host["interface"]:
            raise ValueError("host route is not the exact collected interface")
        if host["mac"] != "42:00:15:19:82:00" or host["host_address"] != "10.15.19.1":
            raise ValueError("host exact-MAC/address identity changed")

        identity = key_values(section(text, "IDENTITY"))
        for key, expected in EXPECTED_IDENTITY.items():
            if identity.get(key) != expected:
                raise ValueError(f"Candidate AH AF-kernel or AD-userspace identity differs: {key}")
        required_identity = set(EXPECTED_IDENTITY) | {"boot_id", "uptime_seconds"}
        if set(identity) != required_identity:
            raise ValueError("Candidate AH identity inventory changed")
        if UUID.fullmatch(identity["boot_id"]) is None:
            raise ValueError("Candidate AH boot ID is malformed")
        if not identity["uptime_seconds"].isdecimal() or int(identity["uptime_seconds"]) < 45:
            raise ValueError("runtime capture predates the 45-second observation boundary")
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
            raise ValueError("boot ID changed during Candidate AH collection")
        if int(first["uptime_seconds"]) < 45:
            raise ValueError("first Candidate AH state read predates 45 seconds")
        if int(second["uptime_seconds"]) < int(first["uptime_seconds"]) + 5:
            raise ValueError("Candidate AH state reads are not separated by five seconds")
        stable_keys = set(first) - {"uptime_seconds"}
        if any(first[key] != second[key] for key in stable_keys):
            raise ValueError("Candidate AH board, USB, keyboard, CPU, or owner state changed")

        first_stat = stat_sample(section(text, "STAT1"))
        second_stat = stat_sample(section(text, "STAT2"))
        expected_cpus = set(range(8))
        if set(first_stat) != expected_cpus or set(second_stat) != expected_cpus:
            raise ValueError("per-CPU accounting inventory is not CPU0 through CPU7")
        stalled = [cpu for cpu in sorted(expected_cpus) if second_stat[cpu] <= first_stat[cpu]]
        if stalled:
            raise ValueError(f"per-CPU accounting did not advance: {stalled}")

        dmesg = section(text, "DMESG")
        if dmesg.count(BLACKLIST_DMESG) != 1:
            raise ValueError("unique exact observer initcall-blacklist line is absent")
        if "smp: Brought up 1 node, 8 CPUs" not in dmesg:
            raise ValueError("eight-CPU SMP completion line is absent")
        for cpu, mpidr in EXPECTED_BOOT_NODES.items():
            pattern = rf"CPU{cpu}: Booted secondary processor 0x{mpidr} \[0x410fd034\]"
            if re.search(pattern, dmesg) is None:
                raise ValueError(f"CPU{cpu} Cortex-A53 boot line is absent")
            if f"GICv3: CPU{cpu}:" not in dmesg:
                raise ValueError(f"CPU{cpu} GICv3 redistributor line is absent")

        reserved_line = (
            "OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff "
            "(32320 KiB) nomap non-reusable mblock-3-framebuffer"
        )
        if dmesg.count(reserved_line) != 1:
            raise ValueError("unique exact LK framebuffer reservation line is absent")
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
        require_unique_ordered_pair(dmesg, SIMPLEFB_CALL, SIMPLEFB_RETURN, "simplefb")
        simplefb_error = SIMPLEFB_ERROR.search(dmesg)
        if simplefb_error is not None:
            raise ValueError(f"simplefb clock or probe error is present: {simplefb_error.group(0)}")

        require_unique_ordered_pair(dmesg, DA9211_CALL, DA9211_RETURN, "DA9211")
        if re.search(r"(?:da9211|da9214).*(?:[0-9]+-0068|regulator@68)", dmesg, re.IGNORECASE):
            raise ValueError("DA9214 client activity is present despite exact AD DT")
        if "observer resources ready:" in dmesg or re.search(
            r"mt6797-a72-power.*(?:probe|resources ready)", dmesg, re.IGNORECASE
        ):
            raise ValueError("A72 observer registered or probed despite blacklist/absent DT")

        keyboard_lines = (
            "input: keyboard-matrix as /devices/platform/keyboard-matrix/input/input0",
            "matrix-keypad keyboard-matrix: polling mode, interval 20 ms",
            "aw9523_client=0-005b driver=aw9523-pinctrl",
            "matrix_platform_device=keyboard-matrix driver=matrix-keypad",
            "matrix_input_name=keyboard-matrix event_node=/dev/input/event0",
        )
        for line in keyboard_lines:
            if dmesg.count(line) != 1:
                raise ValueError(f"unique inherited AD keyboard line is absent: {line}")
        keymap_pattern = re.compile(
            r"keyboard_map=loaded.*sha256="
            r"02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
            r".*tty1_shell=ready.*prompt=GEMINI-AB#.*reboot_dispatch=validated"
        )
        if len(keymap_pattern.findall(dmesg)) != 1:
            raise ValueError("unique inherited AD keymap/readback marker is absent")

        usb_service = (
            f"{USB_MARKER} service=nc status=listening address=10.15.19.82 "
            "port=2323 shell=/bin/usb-shell authentication=none encryption=none "
            "direct_link_only=yes"
        )
        if dmesg.count(usb_service) != 1:
            raise ValueError("unique inherited AD USB listener line is absent")
        if re.search(
            rf"{USB_MARKER} usb0=configured address=10\.15\.19\.82/24 .*"
            r"carrier=1 udc=11271000\.usb udc_state=configured",
            dmesg,
        ) is None:
            raise ValueError("inherited AD USB gadget configuration line is absent")
        ready_lines = re.findall(
            rf"{USB_MARKER} usb_shell=ready reboot_dispatch=validated privilege=root "
            r"authentication=none encryption=none direct_link_only=yes",
            dmesg,
        )
        if len(ready_lines) != 1:
            raise ValueError("exact sole Candidate AH USB shell session is not unique")
        if "watchdog_userspace=none" not in dmesg:
            raise ValueError("inherited no-userspace-watchdog ownership marker is absent")

        request = A72_REQUEST.search(dmesg)
        if request is not None:
            raise ValueError(f"Cortex-A72 CPU_ON/rejection activity is present: {request.group(0)}")
        fault = FAULT.search(dmesg)
        if fault is not None:
            raise ValueError(f"kernel fault signature present: {fault.group(0)}")

        print("validation=candidate-ah-ad-contract-af-kernel-runtime")
        print(f"boot_id={identity['boot_id']}")
        print(f"uptime_seconds={second['uptime_seconds']}")
        print("installed_full_sha256_input=exact-prior-readback-attestation")
        print("af_kernel_config_and_cmdline=exact")
        print("ad_initramfs_critical_payload=exact-live-files")
        print("chosen_simplefb_and_lk_reservation=exact-live-contract")
        print("usb_gadget_shell=exact-sole-session")
        print("aw9523_matrix_event_keymap=bound-and-verified")
        print("observer=dt-device-driver-absent")
        print("i2c6=dt-disabled-platform-absent")
        print("da9214=dt-client-regulators-absent")
        print("possible_present=0-9")
        print("online=0-7")
        print("offline=8-9")
        print("cpu0_cpu7_accounting=advanced")
        print("cpu8_cpu9_enable_method=rejecting-exact")
        print("cpu8_cpu9_cpu_on_or_rejection=absent")
        print("watchdog_userspace_fd=absent")
        print("automatic_reboot_through_observation_boundary=absent")
        print("fault_signatures=absent")
        print("collector_explicit_operations=read-only")
        print("visual_only_result=insufficient-for-pass")
        print("pass_basis=exact-usb-runtime-at-45-plus-5-seconds")
        return 0
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
