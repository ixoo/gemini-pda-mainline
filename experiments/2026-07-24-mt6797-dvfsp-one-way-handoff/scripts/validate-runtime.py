#!/usr/bin/env python3
"""Validate Candidate AO's one-way MT6797 DVFSP handoff runtime evidence."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import pathlib
import re
import stat
import sys


sys.dont_write_bytecode = True

USB_MARKER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
USB_PROMPT = "GEMINI-AC-USB# "
BLACKLIST_TOKEN = "initcall_blacklist=mt6797_a72_power_driver_init"
BLACKLIST_DMESG = "initcall mt6797_a72_power_driver_init blacklisted"
REJECTING_METHOD = "mediatek,mt6797-psci"
EXPECTED_KERNEL = "7.1.3-gemini-observability-L"
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
EXPECTED_KEYMAP_OUTPUT = (
    "keymap_readback=verified tables=8 payload_entries=1024 "
    "kernel_entries=2048 high_halves=K_HOLE table3=K_ALLOCATED "
    "undeclared_tables=K_NOSUCHMAP unicode_mode=K_UNICODE"
)
EXPECTED_KEYMAP_OUTPUT_HEX = EXPECTED_KEYMAP_OUTPUT.encode("ascii").hex()
EXPECTED_IDENTITY = {
    "cmdline": EXPECTED_CMDLINE,
    "possible": "0-9",
    "present": "0-9",
    "online": "0-7",
    "offline": "8-9",
    "nproc": "8",
    "kernel": EXPECTED_KERNEL,
    "config_cmdline": f'CONFIG_CMDLINE="{EXPECTED_CMDLINE}"',
    "config_force": "y",
    "config_a72_power": "y",
    "config_dvfsp_handoff": "y",
    "config_dvfsp_observer": "n",
    "config_da9211": "y",
    "config_simplefb": "y",
    "config_aw9523": "y",
    "config_matrix": "y",
    "config_suspend": "n",
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
    "keymap_verifier_sha256": (
        "29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238"
    ),
    "unicode_helper_sha256": (
        "5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650"
    ),
    "input_helper_sha256": (
        "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
    ),
}
EXPECTED_STATE = {
    "handoff_dt_count": "1",
    "handoff_dt_node_present": "1",
    "handoff_compatible_hex": (
        "6d6564696174656b2c6d74363739372d64766673702d68616e646f666600"
    ),
    "handoff_reg_hex": "00000000110150000000000000001000",
    "handoff_clock_names_hex": "69326300",
    "handoff_status_hex": "6f6b617900",
    "handoff_platform_count": "1",
    "handoff_device": "11015000.dvfsp-handoff",
    "handoff_driver": "mt6797-dvfsp-handoff",
    "handoff_of_node_target": (
        "/sys/firmware/devicetree/base/dvfsp-handoff@11015000"
    ),
    "handoff_driver_target": (
        "/sys/bus/platform/drivers/mt6797-dvfsp-handoff"
    ),
    "handoff_of_node_is_symlink": "1",
    "handoff_driver_is_symlink": "1",
    "handoff_driver_present": "1",
    "handoff_bind_present": "0",
    "handoff_unbind_present": "0",
    "handoff_state_mode": "444",
    "handoff_state_uid": "0",
    "handoff_state_gid": "0",
    "handoff_status_mode": "444",
    "handoff_status_uid": "0",
    "handoff_status_gid": "0",
    "handoff_snapshots_mode": "444",
    "handoff_snapshots_uid": "0",
    "handoff_snapshots_gid": "0",
    "i2c6_dt_node_present": "1",
    "i2c6_status_hex": "64697361626c656400",
    "i2c6_child_count": "0",
    "i2c6_platform_count": "0",
    "i2c6_adapter_count": "0",
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
    "simplefb_platform_count": "1",
    "simplefb_platform_driver": "simple-framebuffer",
    "fb_count": "1",
    "fb0_name": "simple",
    "fb0_virtual_size": "1080,2160",
    "fb0_bits_per_pixel": "32",
    "fb0_stride": "4352",
    "tty1_char_device": "1",
    "tty1_shell_ready_count": "1",
    "aw9523_client_count": "1",
    "aw9523_driver": "aw9523-pinctrl",
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
EXPECTED_HANDOFF_CLOCKS_HEX = "0000000300000036"
EXPECTED_HANDOFF_INFRACFG_HEX = "00000003"

HEX256 = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_MARKER_PATTERN = r"__AO_[A-Z0-9]+_(?:BEGIN|END)__"
RUNTIME_MARKER = re.compile(rf"^{RUNTIME_MARKER_PATTERN}$")
PROMPTED_RUNTIME_MARKER = re.compile(
    rf"^(?:{re.escape(USB_PROMPT)}|> )+({RUNTIME_MARKER_PATTERN})$"
)
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
SAMPLE_ORDER = ("pre0", "pre1", "pre2", "enabled", "post", "late")
PRE_SAMPLE_ORDER = SAMPLE_ORDER[:3]

SNAPSHOT = re.compile(
    r"^sample=(pre0|pre1|pre2|enabled|post|late) "
    r"timer=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"con0=([0-9a-f]{8}) con1=([0-9a-f]{8}) "
    r"pwr_io=([0-9a-f]{8}) r15=([0-9a-f]{8}) "
    r"fsm=([0-9a-f]{8}) "
    r"rsv=([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}),"
    r"([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}) "
    r"gate_valid=([01]) gate=([0-9a-f]{8})$"
)
DMESG_SNAPSHOT = re.compile(
    r"^.*11015000\.dvfsp-handoff: (sample=(?:pre0|pre1|pre2|enabled|post|late) "
    r"timer=[0-9a-f]{8}/[0-9a-f]{8} "
    r"con0=[0-9a-f]{8} con1=[0-9a-f]{8} "
    r"pwr_io=[0-9a-f]{8} r15=[0-9a-f]{8} fsm=[0-9a-f]{8} "
    r"rsv=[0-9a-f]{8},[0-9a-f]{8},[0-9a-f]{8},[0-9a-f]{8},"
    r"[0-9a-f]{8},[0-9a-f]{8},[0-9a-f]{8} "
    r"gate_valid=[01] gate=[0-9a-f]{8})$"
)
STATUS = re.compile(
    r"^state=(ready|inconclusive|faulted|provisional) "
    r"reason=([a-z0-9-]+) initial_gate=(ungated|gated|unknown) "
    r"transition_attempts=([0-9]+) enable_successes=([0-9]+) "
    r"disable_count=([0-9]+) late=(passed|failed|pending|not-scheduled) "
    r"late_checks=([0-9]+) faults=([0-9]+) i2c6_policy=disabled$"
)
SIMPLEFB_CALL = re.compile(r"calling\s+simplefb_driver_init(?:\+|\s)")
SIMPLEFB_RETURN = re.compile(r"initcall simplefb_driver_init(?:\+[^ ]+)? returned 0")
DA9211_CALL = re.compile(r"calling\s+da9211_regulator_driver_init(?:\+|\s)")
DA9211_RETURN = re.compile(
    r"initcall da9211_regulator_driver_init(?:\+[^ ]+)? returned 0"
)
HANDOFF_CALL = re.compile(
    r"calling\s+mt6797_dvfsp_handoff_driver_init(?:\+|\s)"
)
HANDOFF_RETURN = re.compile(
    r"initcall mt6797_dvfsp_handoff_driver_init(?:\+[^ ]+)? returned 0"
)
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
I2C6_ACTIVITY = re.compile(
    r"^.*(?:1100e000\.i2c|regulator@68|[0-9]+-0068|"
    r"\bda9214(?:-bucka)?\b|\bvproc-big\b).*$",
    re.IGNORECASE | re.MULTILINE,
)
HANDOFF_ERROR = re.compile(
    r"^.*(?:mt6797-dvfsp-handoff|11015000\.dvfsp-handoff).*(?:"
    r"state=faulted|cannot|failed|failure|error|defer|unbound|unbind|remove).*$",
    re.IGNORECASE | re.MULTILINE,
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
    name: str
    timer_before: int
    timer_after: int
    pcm_con0: int
    pcm_con1: int
    pcm_pwr_io_en: int
    pcm_reg15_data: int
    pcm_fsm_sta: int
    sw_rsv: tuple[int, ...]
    gate_valid: bool
    gate: int

    def pcm_tuple(self) -> tuple[object, ...]:
        return (
            self.timer_before,
            self.timer_after,
            self.pcm_con0,
            self.pcm_con1,
            self.pcm_pwr_io_en,
            self.pcm_reg15_data,
            self.pcm_fsm_sta,
            self.sw_rsv,
        )


@dataclasses.dataclass(frozen=True)
class Status:
    state: str
    reason: str
    initial_gate: str
    transition_attempts: int
    enable_successes: int
    disable_count: int
    late: str
    late_checks: int
    faults: int


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    outcome: str
    boot_id: str
    uptime_seconds: int
    snapshot_sha256: str


def normalize_capture(text: str) -> str:
    lines: list[str] = []
    for raw in text.replace("\r", "").splitlines():
        line = raw
        prompted_marker = PROMPTED_RUNTIME_MARKER.fullmatch(line)
        if prompted_marker is not None:
            lines.append(prompted_marker.group(1))
            continue
        while line.startswith(USB_PROMPT):
            line = line.removeprefix(USB_PROMPT)
        lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith(("\n", "\r")) else "")


def validate_structure(text: str) -> None:
    expected: list[str] = []
    for name in SECTION_ORDER:
        expected.extend((f"__AO_{name}_BEGIN__", f"__AO_{name}_END__"))
    markers = [
        line
        for line in text.splitlines()
        if RUNTIME_MARKER.fullmatch(line)
    ]
    if markers != expected:
        raise ValueError("runtime sections are missing, duplicated, reordered, or unknown")


def section(text: str, name: str) -> str:
    begin = f"__AO_{name}_BEGIN__"
    end = f"__AO_{name}_END__"
    begin_at = text.index(begin) + len(begin)
    end_at = text.index(end, begin_at)
    return text[begin_at:end_at].lstrip("\n").rstrip("\n")


def key_values(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line:
            continue
        key, separator, value = line.partition("=")
        if (
            not separator
            or re.fullmatch(r"[a-z][a-z0-9_]*", key) is None
            or key in result
        ):
            raise ValueError("runtime key/value inventory is malformed or duplicated")
        result[key] = value
    return result


def parse_snapshot_line(line: str) -> Snapshot:
    match = SNAPSHOT.fullmatch(line)
    if match is None:
        raise ValueError("handoff snapshot syntax changed")
    groups = match.groups()
    return Snapshot(
        name=groups[0],
        timer_before=int(groups[1], 16),
        timer_after=int(groups[2], 16),
        pcm_con0=int(groups[3], 16),
        pcm_con1=int(groups[4], 16),
        pcm_pwr_io_en=int(groups[5], 16),
        pcm_reg15_data=int(groups[6], 16),
        pcm_fsm_sta=int(groups[7], 16),
        sw_rsv=tuple(int(value, 16) for value in groups[8:15]),
        gate_valid=groups[15] == "1",
        gate=int(groups[16], 16),
    )


def parse_snapshots(encoded: str, expected_sha256: str) -> tuple[Snapshot, ...]:
    if (
        not encoded
        or len(encoded) % 2
        or re.fullmatch(r"[0-9a-f]+", encoded) is None
        or HEX256.fullmatch(expected_sha256) is None
    ):
        raise ValueError("handoff snapshot payload or hash is malformed")
    raw = bytes.fromhex(encoded)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("handoff snapshot hash does not match its bytes")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("handoff snapshot payload is not ASCII") from exc
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ValueError("handoff snapshot termination changed")
    snapshots = tuple(parse_snapshot_line(line) for line in text.splitlines())
    names = tuple(snapshot.name for snapshot in snapshots)
    if names not in {SAMPLE_ORDER, PRE_SAMPLE_ORDER}:
        raise ValueError("handoff snapshots are incomplete, duplicated, or reordered")
    return snapshots


def parse_status(line: str) -> Status:
    match = STATUS.fullmatch(line)
    if match is None:
        raise ValueError("handoff status syntax changed")
    groups = match.groups()
    return Status(
        state=groups[0],
        reason=groups[1],
        initial_gate=groups[2],
        transition_attempts=int(groups[3]),
        enable_successes=int(groups[4]),
        disable_count=int(groups[5]),
        late=groups[6],
        late_checks=int(groups[7]),
        faults=int(groups[8]),
    )


def require_reset_stable(snapshots: tuple[Snapshot, ...]) -> None:
    baseline = snapshots[0]
    for snapshot in snapshots:
        if snapshot.timer_before != 0 or snapshot.timer_after != 0:
            raise ValueError(f"{snapshot.name}: PCM timer is not exact stopped value zero")
        if snapshot.pcm_con0 & ((1 << 0) | (1 << 1) | (1 << 15)):
            raise ValueError(f"{snapshot.name}: PCM_CON0 kick/reset bit is set")
        if snapshot.pcm_con1 != 0x00006C00:
            raise ValueError(f"{snapshot.name}: PCM_CON1 is not exact Candidate AN value")
        if snapshot.pcm_pwr_io_en != 0:
            raise ValueError(f"{snapshot.name}: PCM_PWR_IO_EN is nonzero")
        if snapshot.pcm_reg15_data != 0:
            raise ValueError(f"{snapshot.name}: PCM R15 is not exact stopped value zero")
        if snapshot.pcm_fsm_sta != 0x00048490:
            raise ValueError(f"{snapshot.name}: PCM FSM is not reset-like")
        if snapshot.sw_rsv != (0xBABEBABE,) * 7:
            raise ValueError(f"{snapshot.name}: PCM SW_RSV signature differs from Candidate AN")
        if snapshot.pcm_tuple() != baseline.pcm_tuple():
            raise ValueError(f"{snapshot.name}: stopped PCM state changed")
        if not snapshot.gate_valid:
            raise ValueError(f"{snapshot.name}: independent clock gate read is invalid")


def classify(snapshots: tuple[Snapshot, ...]) -> str:
    """Independently classify the driver publication from raw samples."""
    require_reset_stable(snapshots)
    gated = {snapshot.name: bool(snapshot.gate & (1 << 1)) for snapshot in snapshots}
    names = tuple(snapshot.name for snapshot in snapshots)
    if names == SAMPLE_ORDER:
        for name in ("pre0", "pre1", "pre2", "enabled"):
            if gated[name]:
                raise ValueError(f"{name}: I2C_APPM was not physically ungated")
        for name in ("post", "late"):
            if not gated[name]:
                raise ValueError(f"{name}: I2C_APPM was not physically gated")
        return "ready"
    if names == PRE_SAMPLE_ORDER:
        if not all(gated.values()):
            raise ValueError("short handoff evidence is not an initially gated result")
        return "inconclusive"
    raise ValueError("unsupported handoff sample inventory")


def validate_status(status: Status, classification: str) -> None:
    if classification == "ready":
        wanted = Status(
            state="ready",
            reason="late-validation-passed",
            initial_gate="ungated",
            transition_attempts=1,
            enable_successes=1,
            disable_count=1,
            late="passed",
            late_checks=1,
            faults=0,
        )
    else:
        wanted = Status(
            state="inconclusive",
            reason="initial-gate-already-gated",
            initial_gate="gated",
            transition_attempts=0,
            enable_successes=0,
            disable_count=0,
            late="not-scheduled",
            late_checks=0,
            faults=0,
        )
    if status != wanted:
        raise ValueError("driver status disagrees with independent handoff classification")


def stat_sample(text: str) -> dict[int, int]:
    values: dict[int, int] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"cpu([0-9]+)\s+(.+)", line.strip())
        if match is None:
            raise ValueError("per-CPU accounting line is malformed")
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
    if len(calls) != 1 or len(returns) != 1 or calls[0].start() >= returns[0].start():
        raise ValueError(f"{label} initcall evidence is not uniquely ordered/successful")


def validate_handoff_dmesg(
    dmesg: str, snapshots: tuple[Snapshot, ...], classification: str
) -> None:
    scoped = [
        line for line in dmesg.splitlines() if "11015000.dvfsp-handoff:" in line
    ]
    sample_lines: list[str] = []
    events: list[str] = []
    exact_states = {
        "validating": (
            "state=validating operation=one-way-handoff "
            "i2c6_policy=disabled"
        ),
        "normalizing": (
            "state=normalizing transition=ccf-temporary-reference attempt=1"
        ),
        "provisional": (
            "state=provisional normalization=ungated-to-gated "
            "enable_successes=1 disable_count=1 late_validation=pending "
            "delay_ms=45000 i2c6_policy=disabled"
        ),
        "ready": (
            "state=ready normalization=ungated-to-gated "
            "late_validation=passed i2c6_policy=disabled"
        ),
        "inconclusive": (
            "state=inconclusive reason=initial-gate-already-gated "
            "transition_attempts=0 i2c6_policy=disabled"
        ),
    }
    for line in scoped:
        match = DMESG_SNAPSHOT.fullmatch(line)
        if match is not None:
            parsed = parse_snapshot_line(match.group(1))
            sample_lines.append(match.group(1))
            events.append(f"sample:{parsed.name}")
            continue
        matched_state = False
        for name, suffix in exact_states.items():
            if line.endswith(f"11015000.dvfsp-handoff: {suffix}"):
                events.append(f"state:{name}")
                matched_state = True
                break
        if not matched_state:
            raise ValueError(f"unexpected or malformed handoff log line: {line}")

    dmesg_snapshots = tuple(parse_snapshot_line(line) for line in sample_lines)
    if dmesg_snapshots != snapshots:
        raise ValueError("handoff dmesg samples differ from final read-only sysfs")
    if classification == "ready":
        wanted_events = (
            "state:validating",
            "sample:pre0",
            "sample:pre1",
            "sample:pre2",
            "state:normalizing",
            "sample:enabled",
            "sample:post",
            "state:provisional",
            "sample:late",
            "state:ready",
        )
    else:
        wanted_events = (
            "state:validating",
            "sample:pre0",
            "sample:pre1",
            "sample:pre2",
            "state:inconclusive",
        )
    if tuple(events) != wanted_events:
        raise ValueError("handoff event chronology is incomplete, duplicated, or reordered")


def validate_state(
    text: str,
    *,
    expected_live_fdt_sha256: str,
) -> tuple[dict[str, str], tuple[Snapshot, ...], Status, str]:
    values = key_values(text)
    dynamic = {
        "live_fdt_sha256",
        "live_fdt_size",
        "handoff_clocks_hex",
        "handoff_infracfg_hex",
        "handoff_state",
        "handoff_status",
        "handoff_snapshots_hex",
        "handoff_snapshots_sha256",
        "handoff_snapshot_line_count",
        "ac_ready_count",
        "boot_id",
        "uptime_seconds",
    }
    if set(values) != set(EXPECTED_STATE) | dynamic:
        raise ValueError("Candidate AO runtime state inventory changed")
    for key, wanted in EXPECTED_STATE.items():
        if values.get(key) != wanted:
            raise ValueError(f"Candidate AO live board/inheritance differs: {key}")
    if values["live_fdt_sha256"] != expected_live_fdt_sha256:
        raise ValueError("live FDT is not the exact expected Candidate AO identity")
    if not values["live_fdt_size"].isdecimal() or int(values["live_fdt_size"]) <= 0:
        raise ValueError("live FDT size is malformed")
    if (
        values["handoff_clocks_hex"] != EXPECTED_HANDOFF_CLOCKS_HEX
        or values["handoff_infracfg_hex"] != EXPECTED_HANDOFF_INFRACFG_HEX
    ):
        raise ValueError("handoff clock/syscon provider contract is not exact")
    if UUID.fullmatch(values["boot_id"]) is None:
        raise ValueError("Candidate AO boot ID is malformed")
    if not values["uptime_seconds"].isdecimal():
        raise ValueError("Candidate AO uptime is malformed")
    if (
        not values["ac_ready_count"].isdecimal()
        or not 1 <= int(values["ac_ready_count"]) <= 64
    ):
        raise ValueError("USB shell ready count is malformed")
    if HEX256.fullmatch(values["handoff_snapshots_sha256"]) is None:
        raise ValueError("handoff snapshot SHA-256 is malformed")
    snapshots = parse_snapshots(
        values["handoff_snapshots_hex"],
        values["handoff_snapshots_sha256"],
    )
    classification = classify(snapshots)
    if values["handoff_snapshot_line_count"] != str(len(snapshots)):
        raise ValueError("handoff snapshot line count differs from the payload")
    if values["handoff_state"] != classification:
        raise ValueError("driver state differs from independent sample classification")
    status = parse_status(values["handoff_status"])
    validate_status(status, classification)
    return values, snapshots, status, classification


def validate(
    text: str,
    expected_installed_full_sha256: str,
    expected_config_sha256: str,
    expected_live_fdt_sha256: str,
) -> ValidationResult:
    for name, value in (
        ("installed full-partition", expected_installed_full_sha256),
        ("resolved configuration", expected_config_sha256),
        ("live FDT", expected_live_fdt_sha256),
    ):
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"expected {name} SHA-256 is malformed")

    text = normalize_capture(text)
    validate_structure(text)
    identity_begin = text.index("__AO_IDENTITY_BEGIN__")
    if USB_MARKER not in text[:identity_begin].splitlines():
        raise ValueError("exact inherited USB session banner is absent")

    host = key_values(section(text, "HOST"))
    expected_host = {
        "installed_full_sha256_input": expected_installed_full_sha256,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "device_partition_read_during_collection": "no",
        "handoff_access_path": "platform-device-read-only-sysfs",
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
        raise ValueError("Candidate AO host attestation inventory changed")
    for key, wanted in expected_host.items():
        if host.get(key) != wanted:
            raise ValueError(f"Candidate AO host attestation differs: {key}")
    if re.fullmatch(r"[A-Za-z0-9]+", host["interface"]) is None:
        raise ValueError("Candidate AO host interface is malformed")
    if host["route_interface"] != host["interface"]:
        raise ValueError("device route differs from the exact USB interface")

    identity = key_values(section(text, "IDENTITY"))
    dynamic_identity = {"boot_id", "uptime_seconds", "config_sha256"}
    if set(identity) != set(EXPECTED_IDENTITY) | dynamic_identity:
        raise ValueError("Candidate AO identity inventory changed")
    for key, wanted in EXPECTED_IDENTITY.items():
        if identity.get(key) != wanted:
            raise ValueError(f"Candidate AO kernel/initramfs identity differs: {key}")
    if identity["config_sha256"] != expected_config_sha256:
        raise ValueError("resolved kernel configuration is not exact Candidate AO")
    if UUID.fullmatch(identity["boot_id"]) is None:
        raise ValueError("Candidate AO identity boot ID is malformed")
    if not identity["uptime_seconds"].isdecimal() or int(identity["uptime_seconds"]) < 45:
        raise ValueError("Candidate AO collection predates the late-check boundary")
    tokens = identity["cmdline"].split()
    for token in ("maxcpus=8", "regulator_ignore_unused", BLACKLIST_TOKEN):
        if tokens.count(token) != 1:
            raise ValueError(f"Candidate AO command-line token differs: {token}")
    if "nosmp" in tokens or any(
        token in {"maxcpus=1", "maxcpus=9", "maxcpus=10"}
        or token.startswith("nr_cpus=")
        for token in tokens
    ):
        raise ValueError("Candidate AO live CPU policy contains a conflicting cap")

    first, first_snapshots, first_status, classification = validate_state(
        section(text, "STATE1"),
        expected_live_fdt_sha256=expected_live_fdt_sha256,
    )
    second, second_snapshots, second_status, second_classification = validate_state(
        section(text, "STATE2"),
        expected_live_fdt_sha256=expected_live_fdt_sha256,
    )
    if (
        first["boot_id"] != identity["boot_id"]
        or second["boot_id"] != identity["boot_id"]
    ):
        raise ValueError("boot ID changed during Candidate AO collection")
    if int(first["uptime_seconds"]) < 45:
        raise ValueError("first Candidate AO state read predates 45 seconds")
    if int(second["uptime_seconds"]) < int(first["uptime_seconds"]) + 5:
        raise ValueError("Candidate AO state reads are not five seconds apart")
    stable_keys = set(first) - {"uptime_seconds"}
    if any(first[key] != second[key] for key in stable_keys):
        raise ValueError("Candidate AO final state changed across read-only reads")
    if (
        first_snapshots != second_snapshots
        or first_status != second_status
        or classification != second_classification
    ):
        raise ValueError("Candidate AO final publication is not stable")

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
            raise ValueError(f"Candidate AO CPU{cpu} startup evidence differs")
        if dmesg.count(f"GICv3: CPU{cpu}:") != 1:
            raise ValueError(f"Candidate AO CPU{cpu} GIC evidence differs")

    require_unique_ordered_pair(dmesg, SIMPLEFB_CALL, SIMPLEFB_RETURN, "simplefb")
    require_unique_ordered_pair(dmesg, DA9211_CALL, DA9211_RETURN, "DA9211")
    require_unique_ordered_pair(dmesg, HANDOFF_CALL, HANDOFF_RETURN, "DVFSP handoff")
    if "mt6797_dvfsp_observer_driver_init" in dmesg or ".dvfsp-observer:" in dmesg:
        raise ValueError("superseded DVFSP observer activity is present")
    handoff_error = HANDOFF_ERROR.search(dmesg)
    if handoff_error is not None:
        raise ValueError(f"DVFSP handoff error/reprobe line is present: {handoff_error.group(0)}")
    i2c6_activity = I2C6_ACTIVITY.search(dmesg)
    if i2c6_activity is not None:
        raise ValueError(
            f"forbidden I2C6/DA9214 activity is present: {i2c6_activity.group(0)}"
        )
    validate_handoff_dmesg(dmesg, first_snapshots, classification)

    inherited_lines = (
        (
            "OF: reserved mem: 0x000000007dfb0000..0x000000007ff3ffff "
            "(32320 KiB) nomap non-reusable mblock-3-framebuffer"
        ),
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
        raise ValueError("unique inherited keyboard/console/reboot marker is absent")
    usb_service = (
        f"{USB_MARKER} service=nc status=listening address=10.15.19.82 "
        "port=2323 shell=/bin/usb-shell authentication=none encryption=none "
        "direct_link_only=yes"
    )
    if dmesg.count(usb_service) != 1:
        raise ValueError("unique inherited USB listener line is absent")
    expected_sessions = int(first["ac_ready_count"])
    entries = list(USB_SESSION_ENTRY.finditer(dmesg))
    ready = list(USB_SESSION_READY.finditer(dmesg))
    if len(entries) != expected_sessions or len(ready) != expected_sessions:
        raise ValueError("USB session/ready logs differ from the captured count")
    for index, (entry, done) in enumerate(zip(entries, ready)):
        if entry.start() >= done.start():
            raise ValueError("USB ready log precedes its session entry")
        if index + 1 < expected_sessions and done.start() >= entries[index + 1].start():
            raise ValueError("USB session logs are not paired in order")

    request = A72_REQUEST.search(dmesg)
    if request is not None:
        raise ValueError(f"CPU8/9 request or startup activity is present: {request.group(0)}")
    fault = FAULT.search(dmesg)
    if fault is not None:
        raise ValueError(f"kernel fault signature is present: {fault.group(0)}")

    return ValidationResult(
        outcome="PASS" if classification == "ready" else "INCONCLUSIVE",
        boot_id=identity["boot_id"],
        uptime_seconds=int(second["uptime_seconds"]),
        snapshot_sha256=first["handoff_snapshots_sha256"],
    )


def regular_nonempty(path: pathlib.Path) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError("runtime capture is missing, empty, or unsafe")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=pathlib.Path)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    parser.add_argument("--expected-config-sha256", required=True)
    parser.add_argument("--expected-live-fdt-sha256", required=True)
    args = parser.parse_args()
    try:
        regular_nonempty(args.capture)
        result = validate(
            args.capture.read_text(encoding="utf-8", errors="strict"),
            args.expected_installed_full_sha256,
            args.expected_config_sha256,
            args.expected_live_fdt_sha256,
        )
        print("validation=candidate-ao-mt6797-dvfsp-one-way-handoff-runtime")
        print(f"outcome={result.outcome}")
        print(f"boot_id={result.boot_id}")
        print(f"uptime_seconds={result.uptime_seconds}")
        print(f"snapshot_sha256={result.snapshot_sha256}")
        print("installed_identity=caller-supplied-prior-full-readback")
        print("pcm_reset_contract=independently-classified")
        print("i2c6_da9214_a72_cpu8_cpu9_activity=absent")
        print("cpu0_cpu7_accounting=advanced")
        print("usb_keyboard_console_reboot=inherited-runtime-contract")
        print("reboot_executed_by_collector=no")
        if result.outcome == "PASS":
            print("clock_transition=ungated-enabled-to-post-and-late-gated")
            print("ccf_enable_disable=one-each")
            print("late_validation=passed")
            print("next_action=separate-I2C6-consumer-dependency-candidate")
            return 0
        print("clock_transition=none-initially-gated")
        print("late_validation=not-scheduled")
        print("next_action=do-not-enable-I2C6;obtain-attributable-ungated-handoff")
        return 3
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
