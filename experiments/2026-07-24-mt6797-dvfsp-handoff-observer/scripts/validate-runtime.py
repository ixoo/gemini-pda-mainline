#!/usr/bin/env python3
"""Validate Candidate AN's exact, read-only DVFSP handoff observation."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import pathlib
import re
import stat
import sys
from types import ModuleType


sys.dont_write_bytecode = True


def load_candidate_an() -> ModuleType:
    source = pathlib.Path(__file__).resolve().with_name("candidate_an.py")
    info = source.lstat()
    if source.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise RuntimeError("Candidate AN identity module is missing, empty, or unsafe")
    spec = importlib.util.spec_from_file_location("candidate_an_runtime_identity", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AN identity module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


AN = load_candidate_an()
EXPECTED_INSTALLED_FULL_SHA256 = AN.PADDED_SHA256
EXPECTED_CONFIG_SHA256 = AN.CONFIG_SHA256
EXPECTED_ARTIFACT_DTB_SHA256 = AN.FINAL_DTB_SHA256
# LK expands the appended, pre-LK Candidate AN DT before Linux enters.  This
# identity is the exact private live FDT whose semantic delta from
# EXPECTED_ARTIFACT_DTB_SHA256 was independently allowlist-validated.  It is
# deliberately separate from the packaged DTB identity.
EXPECTED_LIVE_FDT_SHA256 = (
    "1ffc67486e68a08da3d946d7fd0bb43d83a92bbc44c7d2fef6c2e77d8c9d4b50"
)
EXPECTED_LIVE_FDT_SIZE = "52547"
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
USB_MARKER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
USB_PROMPT = "GEMINI-AC-USB# "
REJECTING_METHOD = "mediatek,mt6797-psci"
HEX256 = re.compile(r"^[0-9a-f]{64}$")
UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
SECTION_ORDER = ("HOST", "IDENTITY", "STATE1", "STAT1", "STATE2", "STAT2", "DMESG")

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
    "config_dvfsp_observer": "CONFIG_MTK_MT6797_DVFSP_HANDOFF_OBSERVER=y",
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
    "live_fdt_sha256": EXPECTED_LIVE_FDT_SHA256,
    "live_fdt_size": EXPECTED_LIVE_FDT_SIZE,
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
    "runtime_framebuffer_compatible_hex": (
        "6d6564696174656b2c6672616d6562756666657200"
    ),
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
    "dvfsp_observer_dt_count": "1",
    "observer_dt_node_present": "1",
    "observer_compatible_hex": (
        "6d6564696174656b2c6d74363739372d64766673702d68616e646f66662d"
        "6f6273657276657200"
    ),
    "observer_reg_hex": "00000000110150000000000000001000",
    "observer_infracfg_hex": "00000003",
    "observer_status_hex": "6f6b617900",
    "observer_platform_count": "1",
    "observer_device": "11015000.dvfsp-observer",
    "observer_driver": "mt6797-dvfsp-handoff-observer",
    "observer_of_node_target": (
        "/sys/firmware/devicetree/base/dvfsp-observer@11015000"
    ),
    "observer_driver_target": (
        "/sys/bus/platform/drivers/mt6797-dvfsp-handoff-observer"
    ),
    "observer_of_node_is_symlink": "1",
    "observer_driver_is_symlink": "1",
    "observer_driver_present": "1",
    "observer_snapshot_line_count": "3",
    "observer_state_mode": "444",
    "observer_state_uid": "0",
    "observer_state_gid": "0",
    "observer_snapshots_mode": "444",
    "observer_snapshots_uid": "0",
    "observer_snapshots_gid": "0",
    "observer_snapshots_capture_ok": "1",
    "observer_probe_log_line_count": "4",
    "i2c6_dt_node_present": "1",
    "i2c6_status_hex": "64697361626c656400",
    "i2c6_child_count": "0",
    "i2c6_platform_count": "0",
    "i2c6_adapter_count": "0",
    "i2c6_adapter": "unavailable",
    "i2c6_client_count": "0",
    "i2c6_regulator_count": "0",
    "address_0068_client_count": "0",
    "address_0068_bound_driver_count": "0",
    "address_0068_regulator_count": "0",
    "da9214_live_client_count": "0",
    "da9214_dt_count": "0",
    "da9214_named_node_present": "0",
    "a72_power_dt_count": "0",
    "a72_power_named_node_present": "0",
    "aw9523_compatible_hex": (
        "6177696e69632c6177393532332d70696e6374726c00"
    ),
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
    "watchdog_fd_count": "0",
    "online": "0-7",
    "offline": "8-9",
}

FAULT = re.compile(
    r"(?:Kernel panic|\bOops:|\bBUG:|\bSError\b|RCU stall|rcu:.*stall|"
    r"hung task|CPU[0-9]+: failed|failed to boot|psci.*(?:fail|error))",
    re.IGNORECASE,
)
A72_REQUEST = re.compile(
    r"(?:mt6797-psci: CPU(?:8|9) boot rejected|"
    r"CPU(?:8|9): Booted secondary processor|"
    r"(?:CPU_ON|cpu_on).*(?:CPU(?:8|9)|0x20[01])|"
    r"(?:CPU(?:8|9)|0x20[01]).*(?:CPU_ON|cpu_on))"
)
SIMPLEFB_CALL = re.compile(r"calling\s+simplefb_driver_init(?:\+|\s)")
SIMPLEFB_RETURN = re.compile(
    r"initcall simplefb_driver_init(?:\+[^ ]+)? returned 0"
)
DA9211_CALL = re.compile(r"calling\s+da9211_regulator_driver_init(?:\+|\s)")
DA9211_RETURN = re.compile(
    r"initcall da9211_regulator_driver_init(?:\+[^ ]+)? returned 0"
)
OBSERVER_CALL = re.compile(
    r"calling\s+mt6797_dvfsp_observer_driver_init(?:\+|\s)"
)
OBSERVER_RETURN = re.compile(
    r"initcall mt6797_dvfsp_observer_driver_init(?:\+[^ ]+)? returned 0"
)
SIMPLEFB_ERROR = re.compile(
    r"^.*(?:simple-framebuffer|simplefb).*(?:"
    r"clock[^\n]*(?:fail|error|not found|invalid|defer|unavailable)|"
    r"(?:fail|error|defer|unable)[^\n]*clock|"
    r"probe[^\n]*(?:fail|error|defer)|"
    r"(?:fail|error|defer)[^\n]*probe).*$",
    re.IGNORECASE | re.MULTILINE,
)
OBSERVER_ERROR = re.compile(
    r"^.*(?:mt6797-dvfsp-handoff-observer|11015000\.dvfsp-observer)"
    r".*(?:defer|failed|failure|error|cannot|unbound|unbind|remove).*$",
    re.IGNORECASE | re.MULTILINE,
)
I2C6_ACTIVITY = re.compile(
    r"^.*(?:1100e000\.i2c|regulator@68|[0-9]+-0068|"
    r"\bda9214(?:-bucka)?\b|\bvproc-big\b).*$",
    re.IGNORECASE | re.MULTILINE,
)

SYSFS_SNAPSHOT = re.compile(
    r"^snapshot=([0-9]+) "
    r"timer_before=([0-9a-f]{8}) timer_after=([0-9a-f]{8}) "
    r"pcm_con1=([0-9a-f]{8}) pcm_pwr_io_en=([0-9a-f]{8}) "
    r"pcm_reg15_data=([0-9a-f]{8}) pcm_fsm_sta=([0-9a-f]{8}) "
    r"sw_rsv=([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}),"
    r"([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}) "
    r"infra2_pdn_sta_valid=([01]) infra2_pdn_sta=([0-9a-f]{8})$"
)
DMESG_SNAPSHOT = re.compile(
    r"^.*11015000\.dvfsp-observer: snapshot=([0-9]+) "
    r"timer=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"con1=([0-9a-f]{8}) pwr_io=([0-9a-f]{8}) "
    r"pc=([0-9a-f]{8}) fsm=([0-9a-f]{8}) "
    r"rsv=([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}),"
    r"([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}) "
    r"gate_valid=([01]) gate=([0-9a-f]{8})$",
    re.MULTILINE,
)
DMESG_STATE = re.compile(
    r"^.*11015000\.dvfsp-observer: state="
    r"(active|quiescent-stopped|unknown) i2c6_policy=disabled$",
    re.MULTILINE,
)
USB_SESSION_ENTRY = re.compile(
    rf"^.*{re.escape(USB_MARKER)} usb_shell=session-entry "
    r"usb0_operstate=up usb0_carrier=1 udc=11271000\.usb "
    r"udc_state=configured$",
    re.MULTILINE,
)
USB_SESSION_READY = re.compile(
    rf"^.*{re.escape(USB_MARKER)} usb_shell=ready "
    r"reboot_dispatch=validated privilege=root authentication=none "
    r"encryption=none direct_link_only=yes$",
    re.MULTILINE,
)


@dataclasses.dataclass(frozen=True)
class Snapshot:
    index: int
    timer_before: int
    timer_after: int
    pcm_con1: int
    pcm_pwr_io_en: int
    pcm_reg15_data: int
    pcm_fsm_sta: int
    sw_rsv: tuple[int, ...]
    infra2_pdn_sta_valid: bool
    infra2_pdn_sta: int


@dataclasses.dataclass(frozen=True)
class Calibration:
    installed_full_sha256: str
    config_sha256: str
    artifact_dtb_sha256: str


def resolve_calibration(
    expected_installed_full_sha256: str,
) -> Calibration:
    AN.require_artifact_pins()
    calibration = Calibration(
        installed_full_sha256=AN.PADDED_SHA256,
        config_sha256=AN.CONFIG_SHA256,
        artifact_dtb_sha256=AN.FINAL_DTB_SHA256,
    )
    if expected_installed_full_sha256 != calibration.installed_full_sha256:
        raise ValueError("expected installed hash is not exact Candidate AN")
    return calibration


def validate_structure(text: str) -> None:
    previous_end = -1
    for name in SECTION_ORDER:
        begin = f"__AN_{name}_BEGIN__"
        end = f"__AN_{name}_END__"
        if text.count(begin) != 1 or text.count(end) != 1:
            raise ValueError(f"runtime marker is not unique: {name}")
        begin_at = text.index(begin)
        end_at = text.index(end)
        if begin_at <= previous_end or end_at <= begin_at:
            raise ValueError("runtime section chronology is not exact")
        previous_end = end_at + len(end)


def section(text: str, name: str) -> str:
    begin = f"__AN_{name}_BEGIN__"
    end = f"__AN_{name}_END__"
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
        key, separator, value = line.partition("=")
        if not separator or not key or key in result:
            raise ValueError("runtime key/value inventory is malformed or duplicated")
        result[key] = value
    return result


def stat_sample(text: str) -> dict[int, int]:
    values: dict[int, int] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"cpu([0-9]+)\s+(.+)", line.strip())
        if match is None:
            raise ValueError("malformed per-CPU accounting line")
        cpu = int(match.group(1))
        fields = match.group(2).split()
        if cpu in values or not fields or any(not field.isdecimal() for field in fields):
            raise ValueError("per-CPU accounting is duplicated or malformed")
        values[cpu] = sum(int(field) for field in fields)
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


def parse_snapshot_match(match: re.Match[str]) -> Snapshot:
    groups = match.groups()
    if len(groups) != 16:
        raise ValueError("snapshot field inventory changed")
    return Snapshot(
        index=int(groups[0], 10),
        timer_before=int(groups[1], 16),
        timer_after=int(groups[2], 16),
        pcm_con1=int(groups[3], 16),
        pcm_pwr_io_en=int(groups[4], 16),
        pcm_reg15_data=int(groups[5], 16),
        pcm_fsm_sta=int(groups[6], 16),
        sw_rsv=tuple(int(value, 16) for value in groups[7:14]),
        infra2_pdn_sta_valid=groups[14] == "1",
        infra2_pdn_sta=int(groups[15], 16),
    )


def parse_sysfs_snapshots(encoded: str, expected_sha256: str) -> tuple[Snapshot, ...]:
    if not encoded or len(encoded) % 2 or re.fullmatch(r"[0-9a-f]+", encoded) is None:
        raise ValueError("observer snapshot hex payload is malformed")
    raw = bytes.fromhex(encoded)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("observer snapshot payload hash does not match its bytes")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("observer snapshot payload is not ASCII") from exc
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ValueError("observer snapshot payload termination changed")
    lines = text.splitlines()
    if len(lines) != 3:
        raise ValueError("observer sysfs did not publish exactly three lines")
    snapshots: list[Snapshot] = []
    for line in lines:
        match = SYSFS_SNAPSHOT.fullmatch(line)
        if match is None:
            raise ValueError("observer sysfs snapshot syntax changed")
        snapshots.append(parse_snapshot_match(match))
    if [snapshot.index for snapshot in snapshots] != [0, 1, 2]:
        raise ValueError("observer sysfs snapshots are not exactly ordered 0,1,2")
    return tuple(snapshots)


def parse_dmesg_snapshots(text: str) -> tuple[Snapshot, ...]:
    snapshots = tuple(parse_snapshot_match(match) for match in DMESG_SNAPSHOT.finditer(text))
    if len(snapshots) != 3 or [snapshot.index for snapshot in snapshots] != [0, 1, 2]:
        raise ValueError("observer dmesg snapshots are not exactly three ordered lines")
    return snapshots


def firmware_changed(left: Snapshot, right: Snapshot) -> bool:
    return left.pcm_reg15_data != right.pcm_reg15_data or left.sw_rsv != right.sw_rsv


def quiescent_changed(left: Snapshot, right: Snapshot) -> bool:
    if (
        left.pcm_con1 != right.pcm_con1
        or left.pcm_pwr_io_en != right.pcm_pwr_io_en
        or left.pcm_fsm_sta != right.pcm_fsm_sta
        or left.infra2_pdn_sta_valid != right.infra2_pdn_sta_valid
        or (
            left.infra2_pdn_sta_valid
            and ((left.infra2_pdn_sta ^ right.infra2_pdn_sta) & (1 << 1))
        )
    ):
        return True
    return firmware_changed(left, right)


def classify(snapshots: tuple[Snapshot, ...]) -> str:
    if len(snapshots) != 3:
        raise ValueError("classification requires exactly three snapshots")
    first = snapshots[0]
    active = False
    stopped = True
    for index, snapshot in enumerate(snapshots):
        active |= bool(snapshot.pcm_fsm_sta & (1 << 21))
        active |= bool(snapshot.pcm_pwr_io_en & (1 << 7))
        active |= snapshot.timer_before != snapshot.timer_after

        stopped &= snapshot.pcm_fsm_sta == 0x00048490
        stopped &= not bool(snapshot.pcm_con1 & (1 << 5))
        stopped &= snapshot.pcm_pwr_io_en == 0
        stopped &= snapshot.timer_before == snapshot.timer_after
        stopped &= snapshot.infra2_pdn_sta_valid
        stopped &= bool(snapshot.infra2_pdn_sta & (1 << 1))

        if index == 0:
            continue
        previous = snapshots[index - 1]
        active |= previous.timer_after != snapshot.timer_before
        active |= firmware_changed(previous, snapshot)

        stopped &= first.timer_before == snapshot.timer_before
        stopped &= not quiescent_changed(first, snapshot)

    if active:
        return "active"
    if stopped:
        return "quiescent-stopped"
    return "unknown"


def validate_state(
    text: str, expected_live_fdt_sha256: str
) -> tuple[dict[str, str], tuple[Snapshot, ...]]:
    values = key_values(text)
    dynamic = {
        "observer_state",
        "observer_snapshots_hex",
        "observer_snapshots_sha256",
        "observer_probe_log_sha256",
        "ac_ready_count",
        "boot_id",
        "uptime_seconds",
    }
    expected = dict(EXPECTED_STATE)
    expected["live_fdt_sha256"] = expected_live_fdt_sha256
    if set(values) != set(expected) | dynamic:
        raise ValueError("Candidate AN runtime state inventory changed")
    for key, wanted in expected.items():
        if values.get(key) != wanted:
            raise ValueError(f"Candidate AN live board/observer contract differs: {key}")
    if (
        not values["ac_ready_count"].isdecimal()
        or not 1 <= int(values["ac_ready_count"]) <= 64
    ):
        raise ValueError("Candidate AN USB shell ready count is malformed")
    if values["observer_state"] not in {
        "active",
        "quiescent-stopped",
        "unknown",
    }:
        raise ValueError("observer state is not one of the three defined results")
    if HEX256.fullmatch(values["observer_snapshots_sha256"]) is None:
        raise ValueError("observer snapshot SHA-256 is malformed")
    if HEX256.fullmatch(values["observer_probe_log_sha256"]) is None:
        raise ValueError("observer probe-log SHA-256 is malformed")
    if UUID.fullmatch(values["boot_id"]) is None:
        raise ValueError("Candidate AN boot ID is malformed")
    if not values["uptime_seconds"].isdecimal():
        raise ValueError("Candidate AN uptime is malformed")
    snapshots = parse_sysfs_snapshots(
        values["observer_snapshots_hex"],
        values["observer_snapshots_sha256"],
    )
    computed = classify(snapshots)
    if values["observer_state"] != computed:
        raise ValueError("driver state differs from independent C-equivalent classification")
    return values, snapshots


def validate(
    text: str,
    expected_installed_full_sha256: str,
) -> dict[str, str]:
    calibration = resolve_calibration(expected_installed_full_sha256)
    validate_structure(text)

    identity_begin = text.index("__AN_IDENTITY_BEGIN__")
    if USB_MARKER not in text[:identity_begin].replace("\r", "").splitlines():
        raise ValueError("exact inherited AD USB session banner is absent")

    host = key_values(section(text, "HOST"))
    expected_host = {
        "installed_full_sha256_input": expected_installed_full_sha256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "device_partition_read_during_collection": "no",
        "observer_access_path": "platform-device-read-only-sysfs",
        "i2c_transaction_or_controller_control": "none",
        "regulator_control_or_value_read": "none",
        "cpu_online_control_access": "none",
        "watchdog_control_access": "none",
        "reboot_executed": "no",
        "keymap_helper_tty_open_mode": "O_RDWR",
        "keymap_helper_ioctl_scope": "KDGKBMODE-plus-KDGKBENT-readback-only",
        "keymap_helper_mutating_ioctl": "none",
        "mac": "42:00:15:19:82:00",
        "host_address": "10.15.19.1",
    }
    if set(host) != set(expected_host) | {"interface", "route_interface"}:
        raise ValueError("Candidate AN host attestation inventory changed")
    for key, wanted in expected_host.items():
        if host[key] != wanted:
            raise ValueError(f"Candidate AN host attestation differs: {key}")
    if re.fullmatch(r"[A-Za-z0-9]+", host["interface"]) is None:
        raise ValueError("Candidate AN host interface is malformed")
    if host["route_interface"] != host["interface"]:
        raise ValueError("Candidate AN route differs from the exact USB interface")

    identity = key_values(section(text, "IDENTITY"))
    expected_identity = dict(EXPECTED_IDENTITY)
    expected_identity["config_sha256"] = calibration.config_sha256
    if set(identity) != set(expected_identity) | {"boot_id", "uptime_seconds"}:
        raise ValueError("Candidate AN identity inventory changed")
    for key, wanted in expected_identity.items():
        if identity.get(key) != wanted:
            raise ValueError(f"Candidate AN kernel/initramfs identity differs: {key}")
    if UUID.fullmatch(identity["boot_id"]) is None:
        raise ValueError("Candidate AN identity boot ID is malformed")
    if not identity["uptime_seconds"].isdecimal() or int(identity["uptime_seconds"]) < 45:
        raise ValueError("Candidate AN capture predates the 45-second boundary")
    tokens = identity["cmdline"].split()
    for token in ("maxcpus=8", "regulator_ignore_unused", BLACKLIST_TOKEN):
        if tokens.count(token) != 1:
            raise ValueError(f"Candidate AN forced-command-line token differs: {token}")
    if "nosmp" in tokens or any(
        token in {"maxcpus=1", "maxcpus=9", "maxcpus=10"}
        or token.startswith("nr_cpus=")
        for token in tokens
    ):
        raise ValueError("Candidate AN live CPU policy contains a conflicting cap")

    first, first_snapshots = validate_state(
        section(text, "STATE1"), EXPECTED_LIVE_FDT_SHA256
    )
    second, second_snapshots = validate_state(
        section(text, "STATE2"), EXPECTED_LIVE_FDT_SHA256
    )
    if first["boot_id"] != identity["boot_id"] or second["boot_id"] != identity["boot_id"]:
        raise ValueError("boot ID changed during Candidate AN collection")
    if int(first["uptime_seconds"]) < 45:
        raise ValueError("first Candidate AN state sample predates 45 seconds")
    if int(second["uptime_seconds"]) < int(first["uptime_seconds"]) + 5:
        raise ValueError("Candidate AN state samples are not five seconds apart")
    stable = set(first) - {"uptime_seconds"}
    if any(first[key] != second[key] for key in stable):
        raise ValueError(
            "Candidate AN device, links, latched publication, or board state changed"
        )
    if first_snapshots != second_snapshots:
        raise ValueError("observer snapshot structures changed across sysfs reads")

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
        raise ValueError("unique A72 observer initcall-blacklist line is absent")
    if dmesg.count("smp: Brought up 1 node, 8 CPUs") != 1:
        raise ValueError("unique eight-CPU SMP completion line is absent")
    for cpu, mpidr in EXPECTED_BOOT_NODES.items():
        pattern = rf"CPU{cpu}: Booted secondary processor 0x{mpidr} \[0x410fd034\]"
        if len(re.findall(pattern, dmesg)) != 1:
            raise ValueError(f"Candidate AN CPU{cpu} startup evidence differs")
        if dmesg.count(f"GICv3: CPU{cpu}:") != 1:
            raise ValueError(f"Candidate AN CPU{cpu} GIC evidence differs")

    require_unique_ordered_pair(dmesg, SIMPLEFB_CALL, SIMPLEFB_RETURN, "simplefb")
    require_unique_ordered_pair(dmesg, DA9211_CALL, DA9211_RETURN, "DA9211")
    require_unique_ordered_pair(dmesg, OBSERVER_CALL, OBSERVER_RETURN, "DVFSP observer")
    if SIMPLEFB_ERROR.search(dmesg):
        raise ValueError("Candidate AN simplefb clock/probe error is present")
    observer_error = OBSERVER_ERROR.search(dmesg)
    if observer_error is not None:
        raise ValueError(
            "Candidate AN observer error/reprobe line is present: "
            f"{observer_error.group(0)}"
        )
    i2c6_activity = I2C6_ACTIVITY.search(dmesg)
    if i2c6_activity is not None:
        raise ValueError(
            "Candidate AN forbidden I2C6/DA9214 activity is present: "
            f"{i2c6_activity.group(0)}"
        )

    dmesg_snapshots = parse_dmesg_snapshots(dmesg)
    if dmesg_snapshots != first_snapshots:
        raise ValueError("observer dmesg snapshots differ from read-only sysfs")
    state_lines = DMESG_STATE.findall(dmesg)
    if state_lines != [first["observer_state"]]:
        raise ValueError("observer dmesg state is not unique or differs from sysfs")
    probe_lines = [
        line for line in dmesg.splitlines() if "11015000.dvfsp-observer:" in line
    ]
    if len(probe_lines) != 4:
        raise ValueError("observer emitted anything other than three snapshots and one state")
    normalized_probe_logs = ("\n".join(probe_lines) + "\n").encode("utf-8")
    if hashlib.sha256(normalized_probe_logs).hexdigest() != first[
        "observer_probe_log_sha256"
    ]:
        raise ValueError("observer dmesg changed after repeated read-only sysfs reads")

    inherited_lines = (
        "OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff "
        "(32320 KiB) nomap non-reusable mblock-3-framebuffer",
        "simple-framebuffer 7dfb0000.framebuffer: fb0: simplefb registered!",
        "input: keyboard-matrix as /devices/platform/keyboard-matrix/input/input0",
        "matrix-keypad keyboard-matrix: polling mode, interval 20 ms",
        "aw9523_client=0-005b driver=aw9523-pinctrl",
        "matrix_platform_device=keyboard-matrix driver=matrix-keypad",
        "matrix_input_name=keyboard-matrix event_node=/dev/input/event0",
        (
            "GEMINI_MT6797_KERNEL_RESTART_20260720_AB services=launched "
            "probe=independent tty1_shell=supervised "
            "clean_tty1_background=yes reboot_dispatch=env-alias "
            "watchdog_userspace=none keyboard_map=tty1-synchronous "
            "manual_reboot=busybox-no-sync-force "
            "usb_network=background-nc-2323"
        ),
        (
            f"{USB_MARKER} services=launched usb_network=background "
            "worker_wait_seconds=30 address=10.15.19.82/24 tcp_port=2323 "
            "local_console=unchanged watchdog_userspace=none"
        ),
    )
    for line in inherited_lines:
        if dmesg.count(line) != 1:
            raise ValueError(f"unique inherited AH runtime line is absent: {line}")
    keymap = re.compile(
        r"keyboard_map=loaded.*sha256="
        r"02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
        r".*tty1_shell=ready.*prompt=GEMINI-AB#.*reboot_dispatch=validated"
    )
    if len(keymap.findall(dmesg)) != 1:
        raise ValueError("unique inherited keymap/readback/reboot marker is absent")
    usb_service = (
        f"{USB_MARKER} service=nc status=listening address=10.15.19.82 "
        "port=2323 shell=/bin/usb-shell authentication=none encryption=none "
        "direct_link_only=yes"
    )
    if dmesg.count(usb_service) != 1:
        raise ValueError("unique inherited USB listener line is absent")
    expected_sessions = int(first["ac_ready_count"])
    session_entries = list(USB_SESSION_ENTRY.finditer(dmesg))
    session_ready = list(USB_SESSION_READY.finditer(dmesg))
    if (
        len(session_entries) != expected_sessions
        or len(session_ready) != expected_sessions
    ):
        raise ValueError(
            "USB shell session/ready logs do not match the captured ready count"
        )
    for index, (entry, ready) in enumerate(zip(session_entries, session_ready)):
        if entry.start() >= ready.start():
            raise ValueError("USB shell ready log precedes its session entry")
        if (
            index + 1 < expected_sessions
            and ready.start() >= session_entries[index + 1].start()
        ):
            raise ValueError("USB shell session logs are not paired in order")
    request = A72_REQUEST.search(dmesg)
    if request is not None:
        raise ValueError(f"CPU8/9 request or startup activity is present: {request.group(0)}")
    fault = FAULT.search(dmesg)
    if fault is not None:
        raise ValueError(f"kernel fault signature is present: {fault.group(0)}")

    return {
        "boot_id": identity["boot_id"],
        "uptime_seconds": second["uptime_seconds"],
        "state": first["observer_state"],
        "snapshot_sha256": first["observer_snapshots_sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=pathlib.Path)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    args = parser.parse_args()
    try:
        info = args.capture.lstat()
        if args.capture.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
            raise ValueError("runtime capture is missing, empty, or unsafe")
        result = validate(
            args.capture.read_text(encoding="utf-8", errors="strict"),
            args.expected_installed_full_sha256,
        )
        print("validation=candidate-an-mt6797-dvfsp-handoff-observer-runtime")
        print(f"boot_id={result['boot_id']}")
        print(f"uptime_seconds={result['uptime_seconds']}")
        print("installed_full_sha256_input=exact-prior-readback-attestation")
        print(f"artifact_dtb_sha256={EXPECTED_ARTIFACT_DTB_SHA256}")
        print(f"live_fdt_sha256={EXPECTED_LIVE_FDT_SHA256}")
        print("live_fdt_identity=exact-LK-expanded-Candidate-AN")
        print("a72_power_observer=initcall-blacklisted-and-dt-absent")
        print("dvfsp_handoff_observer=enabled-bound-read-only-sysfs")
        print(f"dvfsp_state={result['state']}")
        print(f"snapshot_sha256={result['snapshot_sha256']}")
        print("snapshot_schedule=probe-time-approximately-0ms-2ms-20ms")
        print("classification_scope=boot-handoff-probe-window-only")
        print("latched_publication=stable-at-45-plus-5-seconds")
        print("continuous_firmware_ownership_claim=none")
        print("i2c6=dt-disabled-no-platform-adapter-client-or-regulator")
        print("da9214=dt-and-live-client-absent")
        print("possible_present=0-9")
        print("online=0-7")
        print("offline=8-9")
        print("cpu0_cpu7_accounting=advanced-proven-ah-method")
        print("cpu8_cpu9_request=none")
        print("simplefb_console_contract=live-sysfs-and-log-inheritance-only")
        print("physical_console_visibility=not-observed-by-remote-collector")
        print("keyboard_contract=bound-event-node-plus-keymap-readback-only")
        print("physical_keypress_execution=not-observed-by-remote-collector")
        print("native_reboot_path=payload-plus-dispatch-marker-only-not-executed")
        print("physical_reboot_execution=not-observed-by-remote-collector")
        print("keymap_helper_tty_open=O_RDWR")
        print("keymap_helper_ioctls=KDGKBMODE-plus-KDGKBENT-readback-only")
        print("keymap_helper_mutating_ioctl=none")
        print("watchdog_userspace_fd=absent")
        print("observer_reprobe_or_read_side_effect=absent")
        print("device_partition_read=none")
        print("collector_hardware_control_or_persistent_mutation=none")
        if result["state"] == "quiescent-stopped":
            print(
                "next_action=separate-read-only-legacy-da9214-resource-candidate;"
                "no-rail-write-or-cpu8-request"
            )
        elif result["state"] == "active":
            print(
                "next_action=keep-i2c6-disabled-and-design-firmware-arbitration"
            )
        else:
            print("next_action=improve-observation-path-and-keep-i2c6-disabled")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, KeyError) as exc:
        print(f"inconclusive: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
