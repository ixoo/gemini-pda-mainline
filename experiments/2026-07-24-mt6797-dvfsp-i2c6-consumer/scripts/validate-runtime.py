#!/usr/bin/env python3
"""Validate Candidate AP's handoff-gated childless-I2C6 runtime evidence."""

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
    "initcall_blacklist=mt6797_a72_power_driver_init fw_devlink=rpm"
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
    "handoff_access_controller_cells_hex": "00000000",
    "handoff_phandle_hex": "0000002c",
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
    "handoff_consumer_cleanup_mode": "444",
    "handoff_consumer_cleanup_uid": "0",
    "handoff_consumer_cleanup_gid": "0",
    "i2c6_dt_node_present": "1",
    "i2c6_status_hex": "6f6b617900",
    "i2c6_access_controllers_hex": "0000002c",
    "i2c6_child_count": "0",
    "i2c6_platform_count": "1",
    "i2c6_driver": "i2c-mt65xx",
    "i2c6_handoff_link_count": "1",
    "i2c6_handoff_link_status": "active",
    "i2c6_handoff_link_auto_remove_on": "never",
    "i2c6_handoff_link_runtime_pm": "1",
    "i2c6_handoff_link_sync_state_only": "0",
    "i2c6_handoff_link_inferred_attr_present": "0",
    "i2c6_handoff_status_mode": "444",
    "i2c6_handoff_status_uid": "0",
    "i2c6_handoff_status_gid": "0",
    "i2c6_adapter_count": "1",
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
INCONCLUSIVE_STATE_OVERRIDES = {
    "i2c6_driver": "unbound",
    "i2c6_handoff_link_status": "available",
    "i2c6_handoff_status_mode": "missing",
    "i2c6_handoff_status_uid": "missing",
    "i2c6_handoff_status_gid": "missing",
    "i2c6_adapter_count": "0",
}
FAULTED_STATE_OVERRIDES = dict(INCONCLUSIVE_STATE_OVERRIDES)
EXPECTED_HANDOFF_CLOCKS_HEX = "0000000300000036"
EXPECTED_HANDOFF_INFRACFG_HEX = "00000003"

HEX256 = re.compile(r"^[0-9a-f]{64}$")
RUNTIME_MARKER_PATTERN = r"__AP_[A-Z0-9]+_(?:BEGIN|END)__"
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
SAMPLE_ORDER = (
    "pre0",
    "pre1",
    "pre2",
    "enabled",
    "post",
    "late",
    "consumer-held",
    "consumer-post",
)
PRE_SAMPLE_ORDER = SAMPLE_ORDER[:3]

SNAPSHOT = re.compile(
    r"^sample=(pre0|pre1|pre2|enabled|post|late|consumer-held|consumer-post) "
    r"timer=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"con0=([0-9a-f]{8}) con1=([0-9a-f]{8}) "
    r"pwr_io=([0-9a-f]{8}) r15=([0-9a-f]{8}) "
    r"fsm=([0-9a-f]{8}) "
    r"rsv=([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}),"
    r"([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}),([0-9a-f]{8}) "
    r"gate_valid=([01]) gate=([0-9a-f]{8}) "
    r"dma_gate_valid=([01]) dma_gate=([0-9a-f]{8})$"
)
DMESG_SNAPSHOT = re.compile(
    r"^.*11015000\.dvfsp-handoff: "
    r"(sample=(?:pre0|pre1|pre2|enabled|post|late|consumer-held|consumer-post) "
    r"timer=[0-9a-f]{8}/[0-9a-f]{8} "
    r"con0=[0-9a-f]{8} con1=[0-9a-f]{8} "
    r"pwr_io=[0-9a-f]{8} r15=[0-9a-f]{8} fsm=[0-9a-f]{8} "
    r"rsv=[0-9a-f]{8},[0-9a-f]{8},[0-9a-f]{8},[0-9a-f]{8},"
    r"[0-9a-f]{8},[0-9a-f]{8},[0-9a-f]{8} "
    r"gate_valid=[01] gate=[0-9a-f]{8} "
    r"dma_gate_valid=[01] dma_gate=[0-9a-f]{8})$"
)
CLEANUP_SAMPLE = re.compile(
    r"^i=([0-9]{2}) main_valid=([01]) main=([0-9a-f]{8}) "
    r"dma_valid=([01]) dma=([0-9a-f]{8})$"
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
FORBIDDEN_I2C6_ACTIVITY = re.compile(
    r"^.*(?:1100e000\.i2c:.*(?:timeout|timed out|NACK|transfer failed|error)|"
    r"regulator@68|[0-9]+-0068|"
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
FORBIDDEN_COLLECTOR_ACTIONS = (
    "/sys/power/state",
    "/sysrq-trigger",
    "/dev/mmcblk",
    "/dev/mem",
    "/dev/port",
    "/dev/i2c-",
    "dd if=",
    "blockdev",
    "i2cget",
    "i2cset",
    "i2ctransfer",
    "devmem",
    "chcpu",
    "tee /sys/",
    ">/sys/",
    "> /sys/",
    "/bin/busybox reboot",
    "/bin/busybox poweroff",
    "/sbin/reboot",
    "/sbin/poweroff",
    "rtcwake",
    "pm-suspend",
    "systemctl suspend",
    "echo mem",
    "echo freeze",
)
COLLECTOR_SHA256 = (
    "57a9a9c13f8393ee7a6d441c28ca2b4307c6d23a8a76aef555cc3dfe4063fa02"
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
    dma_gate_valid: bool
    dma_gate: int

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
class CleanupSample:
    index: int
    main_valid: bool
    main: int
    dma_valid: bool
    dma: int


@dataclasses.dataclass(frozen=True)
class Cleanup:
    attempts: int
    samples: tuple[CleanupSample, ...]
    pcm_failures: int
    main_failures: int
    dma_invalid: int
    dma_gated: int
    selected: int
    result: str


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
    suspend_checks: int
    suspend_failures: int
    resume_checks: int
    resume_failures: int
    pm_fault: str
    consumer_ungated_checks: int
    consumer_gated_checks: int
    consumer_validation_failures: int
    supplier_bound: str
    access_grant: str
    cleanup_attempts: int
    cleanup_samples: int
    cleanup_pcm_failures: int
    cleanup_main_failures: int
    cleanup_dma_invalid: int
    cleanup_dma_gated: int
    cleanup_selected: int
    cleanup_result: str


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
        expected.extend((f"__AP_{name}_BEGIN__", f"__AP_{name}_END__"))
    markers = [
        line
        for line in text.splitlines()
        if RUNTIME_MARKER.fullmatch(line)
    ]
    if markers != expected:
        raise ValueError("runtime sections are missing, duplicated, reordered, or unknown")


def section(text: str, name: str) -> str:
    begin = f"__AP_{name}_BEGIN__"
    end = f"__AP_{name}_END__"
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
        dma_gate_valid=groups[17] == "1",
        dma_gate=int(groups[18], 16),
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


def token_map(line: str, label: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for token in line.split():
        key, separator, value = token.partition("=")
        if (
            not separator
            or re.fullmatch(r"[a-z][a-z0-9_]*", key) is None
            or not value
            or key in values
        ):
            raise ValueError(f"{label} token inventory is malformed or duplicated")
        values[key] = value
    return values


def decimal(values: dict[str, str], key: str, label: str) -> int:
    value = values[key]
    if not value.isdecimal():
        raise ValueError(f"{label} counter is malformed: {key}")
    return int(value)


def parse_cleanup(encoded: str, expected_sha256: str) -> Cleanup:
    if (
        not encoded
        or len(encoded) % 2
        or re.fullmatch(r"[0-9a-f]+", encoded) is None
        or HEX256.fullmatch(expected_sha256) is None
    ):
        raise ValueError("consumer cleanup payload or hash is malformed")
    raw = bytes.fromhex(encoded)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("consumer cleanup hash does not match its bytes")
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("consumer cleanup payload is not ASCII") from exc
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise ValueError("consumer cleanup termination changed")
    lines = text.splitlines()
    if not lines:
        raise ValueError("consumer cleanup payload is empty")

    header = token_map(lines[0], "consumer cleanup header")
    expected_header = {
        "attempts",
        "samples",
        "pcm_failures",
        "main_failures",
        "dma_invalid",
        "dma_gated",
        "selected",
        "result",
    }
    if set(header) != expected_header or header["result"] not in {
        "passed",
        "failed",
        "not-run",
    }:
        raise ValueError("consumer cleanup header inventory changed")
    samples: list[CleanupSample] = []
    for line in lines[1:]:
        match = CLEANUP_SAMPLE.fullmatch(line)
        if match is None:
            raise ValueError("consumer cleanup sample syntax changed")
        index, main_valid, main, dma_valid, dma = match.groups()
        samples.append(
            CleanupSample(
                index=int(index),
                main_valid=main_valid == "1",
                main=int(main, 16),
                dma_valid=dma_valid == "1",
                dma=int(dma, 16),
            )
        )
    if [sample.index for sample in samples] != list(range(len(samples))):
        raise ValueError("consumer cleanup sample indexes are not exact and ordered")
    declared_samples = decimal(header, "samples", "consumer cleanup header")
    if declared_samples != len(samples):
        raise ValueError("consumer cleanup line count differs from its header")
    return Cleanup(
        attempts=decimal(header, "attempts", "consumer cleanup header"),
        samples=tuple(samples),
        pcm_failures=decimal(header, "pcm_failures", "consumer cleanup header"),
        main_failures=decimal(header, "main_failures", "consumer cleanup header"),
        dma_invalid=decimal(header, "dma_invalid", "consumer cleanup header"),
        dma_gated=decimal(header, "dma_gated", "consumer cleanup header"),
        selected=decimal(header, "selected", "consumer cleanup header"),
        result=header["result"],
    )


def validate_ready_cleanup(cleanup: Cleanup, consumer_post: Snapshot) -> None:
    if (
        cleanup.attempts != 1
        or len(cleanup.samples) != 32
        or cleanup.pcm_failures
        or cleanup.main_failures
        or cleanup.dma_invalid
        or cleanup.result != "passed"
    ):
        raise ValueError("consumer cleanup did not pass its exact 32-sample oracle")
    if any(
        not sample.main_valid or sample.main & (1 << 1) == 0
        for sample in cleanup.samples
    ):
        raise ValueError("consumer cleanup did not keep I2C_APPM gated")
    if any(not sample.dma_valid for sample in cleanup.samples):
        raise ValueError("consumer cleanup contains an invalid AP_DMA read")
    gated = [
        sample.index for sample in cleanup.samples if sample.dma & (1 << 18)
    ]
    if (
        not gated
        or cleanup.dma_gated != len(gated)
        or cleanup.selected != gated[0]
    ):
        raise ValueError("consumer cleanup AP_DMA selection/count changed")
    selected = cleanup.samples[cleanup.selected]
    if (
        not consumer_post.gate_valid
        or consumer_post.gate != selected.main
        or not consumer_post.dma_gate_valid
        or consumer_post.dma_gate != selected.dma
    ):
        raise ValueError("consumer-post snapshot does not cross-link cleanup selection")


def validate_inconclusive_cleanup(cleanup: Cleanup) -> None:
    if cleanup != Cleanup(
        attempts=0,
        samples=(),
        pcm_failures=0,
        main_failures=0,
        dma_invalid=0,
        dma_gated=0,
        selected=0,
        result="not-run",
    ):
        raise ValueError("inconclusive terminal has unexpected cleanup activity")


def validate_faulted_cleanup(
    cleanup: Cleanup, consumer_post: Snapshot
) -> None:
    if (
        cleanup.attempts != 1
        or len(cleanup.samples) != 32
        or cleanup.pcm_failures
        or cleanup.main_failures
        or cleanup.dma_invalid
        or cleanup.dma_gated
        or cleanup.selected != 31
        or cleanup.result != "failed"
    ):
        raise ValueError(
            "faulted consumer cleanup is not the exact AP_DMA-ungated result"
        )
    if any(
        not sample.main_valid or sample.main & (1 << 1) == 0
        for sample in cleanup.samples
    ):
        raise ValueError("faulted cleanup did not keep I2C_APPM gated")
    if any(
        not sample.dma_valid or sample.dma & (1 << 18)
        for sample in cleanup.samples
    ):
        raise ValueError("faulted cleanup did not keep AP_DMA valid and ungated")
    selected = cleanup.samples[cleanup.selected]
    if (
        not consumer_post.gate_valid
        or consumer_post.gate != selected.main
        or not consumer_post.dma_gate_valid
        or consumer_post.dma_gate != selected.dma
    ):
        raise ValueError(
            "faulted consumer-post snapshot does not cross-link sample 31"
        )


def parse_status(line: str) -> Status:
    values = token_map(line, "handoff status")
    expected = {
        "state",
        "reason",
        "initial_gate",
        "supplier_bound",
        "access_grant",
        "transition_attempts",
        "enable_successes",
        "disable_count",
        "late",
        "late_checks",
        "faults",
        "suspend_checks",
        "suspend_failures",
        "resume_checks",
        "resume_failures",
        "pm_fault",
        "consumer_ungated_checks",
        "consumer_gated_checks",
        "consumer_validation_failures",
        "cleanup_attempts",
        "cleanup_samples",
        "cleanup_pcm_failures",
        "cleanup_main_failures",
        "cleanup_dma_invalid",
        "cleanup_dma_gated",
        "cleanup_selected",
        "cleanup_result",
        "i2c6_policy",
    }
    if set(values) != expected or values["i2c6_policy"] != "requires-ready":
        raise ValueError("handoff status field inventory or policy changed")
    return Status(
        state=values["state"],
        reason=values["reason"],
        initial_gate=values["initial_gate"],
        transition_attempts=decimal(values, "transition_attempts", "handoff status"),
        enable_successes=decimal(values, "enable_successes", "handoff status"),
        disable_count=decimal(values, "disable_count", "handoff status"),
        late=values["late"],
        late_checks=decimal(values, "late_checks", "handoff status"),
        faults=decimal(values, "faults", "handoff status"),
        suspend_checks=decimal(values, "suspend_checks", "handoff status"),
        suspend_failures=decimal(
            values, "suspend_failures", "handoff status"
        ),
        resume_checks=decimal(values, "resume_checks", "handoff status"),
        resume_failures=decimal(values, "resume_failures", "handoff status"),
        pm_fault=values["pm_fault"],
        consumer_ungated_checks=decimal(
            values, "consumer_ungated_checks", "handoff status"
        ),
        consumer_gated_checks=decimal(
            values, "consumer_gated_checks", "handoff status"
        ),
        consumer_validation_failures=decimal(
            values, "consumer_validation_failures", "handoff status"
        ),
        supplier_bound=values["supplier_bound"],
        access_grant=values["access_grant"],
        cleanup_attempts=decimal(
            values, "cleanup_attempts", "handoff status"
        ),
        cleanup_samples=decimal(values, "cleanup_samples", "handoff status"),
        cleanup_pcm_failures=decimal(
            values, "cleanup_pcm_failures", "handoff status"
        ),
        cleanup_main_failures=decimal(
            values, "cleanup_main_failures", "handoff status"
        ),
        cleanup_dma_invalid=decimal(
            values, "cleanup_dma_invalid", "handoff status"
        ),
        cleanup_dma_gated=decimal(
            values, "cleanup_dma_gated", "handoff status"
        ),
        cleanup_selected=decimal(
            values, "cleanup_selected", "handoff status"
        ),
        cleanup_result=values["cleanup_result"],
    )


def parse_i2c_guard(
    line: str, *, include_pm: bool, include_domains: bool = False
) -> dict[str, str]:
    values = token_map(line, "I2C6 handoff status")
    expected = {
        "handoff": "ready",
        "probe_attempts": "1",
        "init_attempts": "1",
        "init_successes": "1",
        "clock_ungated_checks": "1",
        "clock_gated_checks": "1",
        "clock_validation_failures": "0",
        "runtime_pm_link": "1",
        "transfer_attempts": "0",
        "dma_starts": "0",
        "nonzero_starts": "0",
        "irq_count": "0",
    }
    if include_pm:
        expected.update(
            {
                "suspend_checks": "0",
                "resume_checks": "0",
                "resume_failures": "0",
            }
        )
    if include_domains:
        expected["clock_domains"] = "i2c-appm,ap-dma"
    if values != expected:
        raise ValueError("I2C6 guarded-init counters or field inventory changed")
    return values


def parse_i2c_denial(line: str) -> dict[str, str]:
    values = token_map(line, "I2C6 denied handoff")
    expected = {
        "handoff": "denied",
        "probe_attempts": "1",
        "reason": "supplier-not-ready",
    }
    if values != expected:
        raise ValueError("I2C6 denied probe evidence changed")
    return values


def require_reset_stable(snapshots: tuple[Snapshot, ...]) -> None:
    baseline = snapshots[0]
    for snapshot in snapshots:
        if snapshot.timer_before != 0 or snapshot.timer_after != 0:
            raise ValueError(f"{snapshot.name}: PCM timer is not exact stopped value zero")
        if snapshot.pcm_con0 & ((1 << 0) | (1 << 1) | (1 << 15)):
            raise ValueError(f"{snapshot.name}: PCM_CON0 kick/reset bit is set")
        if snapshot.pcm_con1 != 0x00006C00:
            raise ValueError(f"{snapshot.name}: PCM_CON1 is not exact Candidate AO value")
        if snapshot.pcm_pwr_io_en != 0:
            raise ValueError(f"{snapshot.name}: PCM_PWR_IO_EN is nonzero")
        if snapshot.pcm_reg15_data != 0:
            raise ValueError(f"{snapshot.name}: PCM R15 is not exact stopped value zero")
        if snapshot.pcm_fsm_sta != 0x00048490:
            raise ValueError(f"{snapshot.name}: PCM FSM is not reset-like")
        if snapshot.sw_rsv != (0xBABEBABE,) * 7:
            raise ValueError(f"{snapshot.name}: PCM SW_RSV signature differs from Candidate AO")
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
        for name in ("pre0", "pre1", "pre2", "enabled", "consumer-held"):
            if gated[name]:
                raise ValueError(f"{name}: I2C_APPM was not physically ungated")
        for name in ("post", "late", "consumer-post"):
            if not gated[name]:
                raise ValueError(f"{name}: I2C_APPM was not physically gated")
        held = snapshots[SAMPLE_ORDER.index("consumer-held")]
        post = snapshots[SAMPLE_ORDER.index("consumer-post")]
        if not held.dma_gate_valid or held.dma_gate & (1 << 18):
            raise ValueError("consumer-held: AP_DMA was not valid and ungated")
        if not post.dma_gate_valid:
            raise ValueError("consumer-post: AP_DMA read was invalid")
        return "ready" if post.dma_gate & (1 << 18) else "faulted"
    if names == PRE_SAMPLE_ORDER:
        if not all(gated.values()):
            raise ValueError("short handoff evidence is not an initially gated result")
        return "inconclusive"
    raise ValueError("unsupported handoff sample inventory")


def validate_status(
    status: Status, classification: str, cleanup: Cleanup
) -> None:
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
            suspend_checks=0,
            suspend_failures=0,
            resume_checks=0,
            resume_failures=0,
            pm_fault="none",
            consumer_ungated_checks=1,
            consumer_gated_checks=1,
            consumer_validation_failures=0,
            supplier_bound="yes",
            access_grant="ready",
            cleanup_attempts=1,
            cleanup_samples=32,
            cleanup_pcm_failures=0,
            cleanup_main_failures=0,
            cleanup_dma_invalid=0,
            cleanup_dma_gated=cleanup.dma_gated,
            cleanup_selected=cleanup.selected,
            cleanup_result="passed",
        )
    elif classification == "inconclusive":
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
            suspend_checks=0,
            suspend_failures=0,
            resume_checks=0,
            resume_failures=0,
            pm_fault="none",
            consumer_ungated_checks=0,
            consumer_gated_checks=0,
            consumer_validation_failures=0,
            supplier_bound="yes",
            access_grant="denied",
            cleanup_attempts=0,
            cleanup_samples=0,
            cleanup_pcm_failures=0,
            cleanup_main_failures=0,
            cleanup_dma_invalid=0,
            cleanup_dma_gated=0,
            cleanup_selected=0,
            cleanup_result="not-run",
        )
    elif classification == "faulted":
        wanted = Status(
            state="faulted",
            reason="consumer-cleanup-validation-failed",
            initial_gate="ungated",
            transition_attempts=1,
            enable_successes=1,
            disable_count=1,
            late="passed",
            late_checks=1,
            faults=1,
            suspend_checks=0,
            suspend_failures=0,
            resume_checks=0,
            resume_failures=0,
            pm_fault="none",
            consumer_ungated_checks=1,
            consumer_gated_checks=1,
            consumer_validation_failures=1,
            supplier_bound="yes",
            access_grant="denied",
            cleanup_attempts=1,
            cleanup_samples=32,
            cleanup_pcm_failures=0,
            cleanup_main_failures=0,
            cleanup_dma_invalid=0,
            cleanup_dma_gated=0,
            cleanup_selected=31,
            cleanup_result="failed",
        )
    else:
        raise ValueError("unsupported handoff status classification")
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
    dmesg: str,
    snapshots: tuple[Snapshot, ...],
    cleanup: Cleanup,
    classification: str,
) -> tuple[Snapshot, ...]:
    scoped = [
        line for line in dmesg.splitlines() if "11015000.dvfsp-handoff:" in line
    ]
    sample_lines: list[str] = []
    events: list[str] = []
    exact_states = {
        "validating": (
            "state=validating operation=one-way-handoff "
            "i2c6_policy=requires-ready"
        ),
        "normalizing": (
            "state=normalizing transition=ccf-temporary-reference attempt=1"
        ),
        "provisional": (
            "state=provisional normalization=ungated-to-gated "
            "enable_successes=1 disable_count=1 late_validation=pending "
            "delay_ms=45000 i2c6_policy=requires-ready"
        ),
        "ready": (
            "state=ready normalization=ungated-to-gated "
            "late_validation=passed i2c6_policy=requires-ready"
        ),
        "inconclusive": (
            "state=inconclusive reason=initial-gate-already-gated "
            "transition_attempts=0 i2c6_policy=requires-ready"
        ),
        "supplier-denied": (
            "supplier_bound=yes access_grant=denied state=inconclusive "
            "reason=initial-gate-already-gated access_controller=enabled"
        ),
        "supplier": (
            "supplier_bound=yes access_grant=ready state=ready "
            "late_validation=passed "
            "access_controller=enabled"
        ),
        "consumer-ungated": (
            "consumer_clock_check=held clocks=i2c-appm,ap-dma "
            "validation=passed "
            "i2c6_policy=requires-ready"
        ),
        "consumer-gated": (
            "consumer_clock_check=cleanup clocks=i2c-appm,ap-dma "
            f"validation=passed samples=32 dma_gated={cleanup.dma_gated} "
            f"selected={cleanup.selected} "
            "i2c6_policy=requires-ready"
        ),
        "consumer-cleanup-failed": (
            "consumer_clock_check=cleanup clocks=i2c-appm,ap-dma "
            "validation=failed samples=32 pcm_failures=0 main_failures=0 "
            "dma_invalid=0 dma_gated=0 selected=31 "
            "i2c6_policy=requires-ready"
        ),
        "consumer-faulted": (
            "state=faulted reason=consumer-cleanup-validation-failed "
            "i2c6_policy=requires-ready"
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
    if snapshots and dmesg_snapshots != snapshots:
        raise ValueError("handoff dmesg samples differ from final read-only sysfs")
    if classify(dmesg_snapshots) != classification:
        raise ValueError("handoff dmesg samples disagree with terminal outcome")
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
            "state:supplier",
            "sample:consumer-held",
            "state:consumer-ungated",
            "sample:consumer-post",
            "state:consumer-gated",
        )
    elif classification == "inconclusive":
        wanted_events = (
            "state:validating",
            "sample:pre0",
            "sample:pre1",
            "sample:pre2",
            "state:inconclusive",
            "state:supplier-denied",
        )
    elif classification == "faulted":
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
            "state:supplier",
            "sample:consumer-held",
            "state:consumer-ungated",
            "sample:consumer-post",
            "state:consumer-cleanup-failed",
            "state:consumer-faulted",
        )
    else:
        raise ValueError("unsupported handoff dmesg classification")
    if tuple(events) != wanted_events:
        raise ValueError("handoff event chronology is incomplete, duplicated, or reordered")
    return dmesg_snapshots


def terminal_from_dmesg(dmesg: str) -> str:
    ready = (
        "supplier_bound=yes access_grant=ready state=ready "
        "late_validation=passed "
        "access_controller=enabled"
    )
    inconclusive = (
        "supplier_bound=yes access_grant=denied state=inconclusive "
        "reason=initial-gate-already-gated access_controller=enabled"
    )
    faulted = re.compile(
        r"supplier_bound=yes access_grant=denied state=faulted "
        r"reason=[a-z0-9-]+ access_controller=enabled(?:\s|$)"
    )
    cleanup_fault = (
        "state=faulted reason=consumer-cleanup-validation-failed "
        "i2c6_policy=requires-ready"
    )
    if (
        dmesg.count(ready) == 1
        and dmesg.count(cleanup_fault) == 1
        and inconclusive not in dmesg
        and not faulted.search(dmesg)
    ):
        return "faulted"
    if (
        dmesg.count(ready) == 1
        and cleanup_fault not in dmesg
        and inconclusive not in dmesg
        and not faulted.search(dmesg)
    ):
        return "ready"
    if (
        dmesg.count(inconclusive) == 1
        and ready not in dmesg
        and cleanup_fault not in dmesg
        and not faulted.search(dmesg)
    ):
        return "inconclusive"
    raise ValueError("provider terminal bind outcome is absent, duplicated, or conflicting")


def validate_state(
    text: str,
    *,
    expected_live_fdt_sha256: str,
    terminal: str,
) -> tuple[dict[str, str], tuple[Snapshot, ...], Status | None, str]:
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
        "handoff_consumer_cleanup_hex",
        "handoff_consumer_cleanup_sha256",
        "handoff_consumer_cleanup_line_count",
        "handoff_device_canonical",
        "i2c6_device_canonical",
        "i2c6_handoff_link_consumer_target",
        "i2c6_handoff_link_supplier_target",
        "i2c6_handoff_status",
        "ac_ready_count",
        "boot_id",
        "uptime_seconds",
    }
    if set(values) != set(EXPECTED_STATE) | dynamic:
        raise ValueError("Candidate AP runtime state inventory changed")
    wanted_state = dict(EXPECTED_STATE)
    if terminal == "inconclusive":
        wanted_state.update(INCONCLUSIVE_STATE_OVERRIDES)
    elif terminal == "faulted":
        wanted_state.update(FAULTED_STATE_OVERRIDES)
    for key, wanted in wanted_state.items():
        if values.get(key) != wanted:
            raise ValueError(f"Candidate AP live board/inheritance differs: {key}")
    if values["live_fdt_sha256"] != expected_live_fdt_sha256:
        raise ValueError("live FDT is not the exact expected Candidate AP identity")
    if not values["live_fdt_size"].isdecimal() or int(values["live_fdt_size"]) <= 0:
        raise ValueError("live FDT size is malformed")
    if (
        values["handoff_clocks_hex"] != EXPECTED_HANDOFF_CLOCKS_HEX
        or values["handoff_infracfg_hex"] != EXPECTED_HANDOFF_INFRACFG_HEX
    ):
        raise ValueError("handoff clock/syscon provider contract is not exact")
    handoff_canonical = values["handoff_device_canonical"]
    i2c6_canonical = values["i2c6_device_canonical"]
    if (
        not handoff_canonical.startswith("/sys/devices/")
        or not handoff_canonical.endswith("/11015000.dvfsp-handoff")
        or not i2c6_canonical.startswith("/sys/devices/")
        or not i2c6_canonical.endswith("/1100e000.i2c")
        or values["i2c6_handoff_link_consumer_target"] != i2c6_canonical
        or values["i2c6_handoff_link_supplier_target"] != handoff_canonical
    ):
        raise ValueError("device-link supplier/consumer targets are not exact")
    if UUID.fullmatch(values["boot_id"]) is None:
        raise ValueError("Candidate AP boot ID is malformed")
    if not values["uptime_seconds"].isdecimal():
        raise ValueError("Candidate AP uptime is malformed")
    if (
        not values["ac_ready_count"].isdecimal()
        or not 1 <= int(values["ac_ready_count"]) <= 64
    ):
        raise ValueError("USB shell ready count is malformed")
    if terminal in {"inconclusive", "faulted"}:
        missing = {
            "i2c6_handoff_status": "",
        }
        for key, wanted in missing.items():
            if values[key] != wanted:
                raise ValueError(f"denied terminal publication differs: {key}")
    elif terminal != "ready":
        raise ValueError("unsupported terminal state for read-only state validation")
    if HEX256.fullmatch(values["handoff_snapshots_sha256"]) is None:
        raise ValueError("handoff snapshot SHA-256 is malformed")
    snapshots = parse_snapshots(
        values["handoff_snapshots_hex"],
        values["handoff_snapshots_sha256"],
    )
    cleanup = parse_cleanup(
        values["handoff_consumer_cleanup_hex"],
        values["handoff_consumer_cleanup_sha256"],
    )
    classification = classify(snapshots)
    if values["handoff_snapshot_line_count"] != str(len(snapshots)):
        raise ValueError("handoff snapshot line count differs from the payload")
    if values["handoff_consumer_cleanup_line_count"] != str(len(cleanup.samples)):
        raise ValueError("consumer cleanup line count differs from the payload")
    if values["handoff_state"] != classification:
        raise ValueError("driver state differs from independent sample classification")
    if classification == "ready":
        validate_ready_cleanup(
            cleanup, snapshots[SAMPLE_ORDER.index("consumer-post")]
        )
    elif classification == "inconclusive":
        validate_inconclusive_cleanup(cleanup)
    elif classification == "faulted":
        validate_faulted_cleanup(
            cleanup, snapshots[SAMPLE_ORDER.index("consumer-post")]
        )
    else:
        raise ValueError("unsupported independent handoff classification")
    status = parse_status(values["handoff_status"])
    validate_status(status, classification, cleanup)
    if classification != terminal:
        raise ValueError("driver publication disagrees with terminal bind log")
    if terminal == "ready":
        parse_i2c_guard(
            values["i2c6_handoff_status"],
            include_pm=True,
            include_domains=True,
        )
    return values, snapshots, status, classification


def validate(
    text: str,
    expected_installed_full_sha256: str,
    expected_config_sha256: str,
    expected_live_fdt_sha256: str,
    expected_boot_id: str,
) -> ValidationResult:
    for name, value in (
        ("installed full-partition", expected_installed_full_sha256),
        ("resolved configuration", expected_config_sha256),
        ("live FDT", expected_live_fdt_sha256),
    ):
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"expected {name} SHA-256 is malformed")
    if UUID.fullmatch(expected_boot_id) is None:
        raise ValueError("expected live-FDT boot ID is malformed")

    text = normalize_capture(text)
    validate_structure(text)
    identity_begin = text.index("__AP_IDENTITY_BEGIN__")
    if USB_MARKER not in text[:identity_begin].splitlines():
        raise ValueError("exact inherited USB session banner is absent")

    host = key_values(section(text, "HOST"))
    expected_host = {
        "installed_full_sha256_input": expected_installed_full_sha256,
        "expected_boot_id_input": expected_boot_id,
        "attestation_basis": "caller-supplied-prior-full-partition-readback",
        "device_partition_read_during_collection": "no",
        "handoff_access_path": "platform-device-read-only-sysfs",
        "i2c_transaction_or_controller_control": "none",
        "regulator_control_or_value_read": "none",
        "cpu_online_control_access": "none",
        "watchdog_control_access": "none",
        "reboot_executed": "no",
        "power_state_transition_requested": "no",
        "keymap_helper_tty_open_mode": "O_RDWR",
        "keymap_helper_ioctl_scope": "KDGKBMODE-plus-KDGKBENT-readback-only",
        "keymap_helper_mutating_ioctl": "none",
        "mac": "42:00:15:19:82:00",
        "host_address": "10.15.19.1",
    }
    if set(host) != set(expected_host) | {"interface", "route_interface"}:
        raise ValueError("Candidate AP host attestation inventory changed")
    for key, wanted in expected_host.items():
        if host.get(key) != wanted:
            raise ValueError(f"Candidate AP host attestation differs: {key}")
    if re.fullmatch(r"[A-Za-z0-9]+", host["interface"]) is None:
        raise ValueError("Candidate AP host interface is malformed")
    if host["route_interface"] != host["interface"]:
        raise ValueError("device route differs from the exact USB interface")

    identity = key_values(section(text, "IDENTITY"))
    dynamic_identity = {"boot_id", "uptime_seconds", "config_sha256"}
    if set(identity) != set(EXPECTED_IDENTITY) | dynamic_identity:
        raise ValueError("Candidate AP identity inventory changed")
    for key, wanted in EXPECTED_IDENTITY.items():
        if identity.get(key) != wanted:
            raise ValueError(f"Candidate AP kernel/initramfs identity differs: {key}")
    if identity["config_sha256"] != expected_config_sha256:
        raise ValueError("resolved kernel configuration is not exact Candidate AP")
    if UUID.fullmatch(identity["boot_id"]) is None:
        raise ValueError("Candidate AP identity boot ID is malformed")
    if identity["boot_id"] != expected_boot_id:
        raise ValueError(
            "runtime capture boot ID differs from the validated live-FDT boot"
        )
    if not identity["uptime_seconds"].isdecimal() or int(identity["uptime_seconds"]) < 45:
        raise ValueError("Candidate AP collection predates the late-check boundary")
    tokens = identity["cmdline"].split()
    for token in (
        "maxcpus=8",
        "regulator_ignore_unused",
        BLACKLIST_TOKEN,
        "fw_devlink=rpm",
    ):
        if tokens.count(token) != 1:
            raise ValueError(f"Candidate AP command-line token differs: {token}")
    if "nosmp" in tokens or any(
        token in {"maxcpus=1", "maxcpus=9", "maxcpus=10"}
        or token.startswith("nr_cpus=")
        for token in tokens
    ):
        raise ValueError("Candidate AP live CPU policy contains a conflicting cap")

    dmesg = section(text, "DMESG")
    terminal = terminal_from_dmesg(dmesg)

    first, first_snapshots, first_status, classification = validate_state(
        section(text, "STATE1"),
        expected_live_fdt_sha256=expected_live_fdt_sha256,
        terminal=terminal,
    )
    second, second_snapshots, second_status, second_classification = validate_state(
        section(text, "STATE2"),
        expected_live_fdt_sha256=expected_live_fdt_sha256,
        terminal=terminal,
    )
    if (
        first["boot_id"] != identity["boot_id"]
        or second["boot_id"] != identity["boot_id"]
    ):
        raise ValueError("boot ID changed during Candidate AP collection")
    if int(first["uptime_seconds"]) < 45:
        raise ValueError("first Candidate AP state read predates 45 seconds")
    if int(second["uptime_seconds"]) < int(first["uptime_seconds"]) + 5:
        raise ValueError("Candidate AP state reads are not five seconds apart")
    stable_keys = set(first) - {"uptime_seconds"}
    if any(first[key] != second[key] for key in stable_keys):
        raise ValueError("Candidate AP final state changed across read-only reads")
    if (
        first_snapshots != second_snapshots
        or first_status != second_status
        or classification != second_classification
    ):
        raise ValueError("Candidate AP final publication is not stable")

    first_stat = stat_sample(section(text, "STAT1"))
    second_stat = stat_sample(section(text, "STAT2"))
    expected_cpus = set(range(8))
    if set(first_stat) != expected_cpus or set(second_stat) != expected_cpus:
        raise ValueError("per-CPU accounting inventory is not CPU0 through CPU7")
    stalled = [cpu for cpu in sorted(expected_cpus) if second_stat[cpu] <= first_stat[cpu]]
    if stalled:
        raise ValueError(f"per-CPU accounting did not advance: {stalled}")

    if dmesg.count(BLACKLIST_DMESG) != 1:
        raise ValueError("unique A72 observer initcall-blacklist line is absent")
    if dmesg.count("smp: Brought up 1 node, 8 CPUs") != 1:
        raise ValueError("unique eight-CPU SMP completion line is absent")
    for cpu, mpidr in EXPECTED_BOOT_NODES.items():
        pattern = rf"CPU{cpu}: Booted secondary processor 0x{mpidr} \[0x410fd034\]"
        if len(re.findall(pattern, dmesg)) != 1:
            raise ValueError(f"Candidate AP CPU{cpu} startup evidence differs")
        if dmesg.count(f"GICv3: CPU{cpu}:") != 1:
            raise ValueError(f"Candidate AP CPU{cpu} GIC evidence differs")

    require_unique_ordered_pair(dmesg, SIMPLEFB_CALL, SIMPLEFB_RETURN, "simplefb")
    require_unique_ordered_pair(dmesg, DA9211_CALL, DA9211_RETURN, "DA9211")
    require_unique_ordered_pair(dmesg, HANDOFF_CALL, HANDOFF_RETURN, "DVFSP handoff")
    if "mt6797_dvfsp_observer_driver_init" in dmesg or ".dvfsp-observer:" in dmesg:
        raise ValueError("superseded DVFSP observer activity is present")
    first_cleanup = parse_cleanup(
        first["handoff_consumer_cleanup_hex"],
        first["handoff_consumer_cleanup_sha256"],
    )
    validate_handoff_dmesg(
        dmesg, first_snapshots, first_cleanup, classification
    )
    fault_probe = re.compile(
        r"^\[[^]]+\] i2c-mt65xx 1100e000\.i2c: probe with driver "
        r"i2c-mt65xx failed with error -5$",
        re.MULTILINE,
    )
    fault_return = re.compile(
        r"^\[[^]]+\] probe of 1100e000\.i2c returned 5 after "
        r"[1-9][0-9]* usecs$",
        re.MULTILINE,
    )
    if terminal == "faulted":
        if len(fault_probe.findall(dmesg)) != 1 or len(
            fault_return.findall(dmesg)
        ) != 1:
            raise ValueError(
                "exact fail-closed I2C6 probe result is absent or duplicated"
            )
    else:
        handoff_error = HANDOFF_ERROR.search(dmesg)
        if handoff_error is not None:
            raise ValueError(
                "DVFSP handoff error/reprobe line is present: "
                f"{handoff_error.group(0)}"
            )
    dmesg_without_expected = "\n".join(
        line
        for line in dmesg.splitlines()
        if "GEMINI_MT6797_I2C6_GUARD " not in line
        and not (terminal == "faulted" and fault_probe.fullmatch(line))
    )
    i2c6_activity = FORBIDDEN_I2C6_ACTIVITY.search(dmesg_without_expected)
    if i2c6_activity is not None:
        raise ValueError(
            f"forbidden I2C6-client/DA9214 activity is present: {i2c6_activity.group(0)}"
        )

    supplier = (
        "supplier_bound=yes access_grant=ready state=ready "
        "late_validation=passed "
        "access_controller=enabled"
    )
    ungated = (
        "consumer_clock_check=held clocks=i2c-appm,ap-dma validation=passed "
        "i2c6_policy=requires-ready"
    )
    gated = (
        "consumer_clock_check=cleanup clocks=i2c-appm,ap-dma "
        f"validation=passed samples=32 dma_gated={first_cleanup.dma_gated} "
        f"selected={first_cleanup.selected} "
        "i2c6_policy=requires-ready"
    )
    failed_cleanup = (
        "consumer_clock_check=cleanup clocks=i2c-appm,ap-dma "
        "validation=failed samples=32 pcm_failures=0 main_failures=0 "
        "dma_invalid=0 dma_gated=0 selected=31 "
        "i2c6_policy=requires-ready"
    )
    faulted_state = (
        "state=faulted reason=consumer-cleanup-validation-failed "
        "i2c6_policy=requires-ready"
    )
    guard_marker = "GEMINI_MT6797_I2C6_GUARD "
    guard_lines = [line for line in dmesg.splitlines() if guard_marker in line]
    if terminal == "ready":
        if dmesg.count(supplier) != 1:
            raise ValueError("unique ready access-controller grant is absent")
        if dmesg.count(ungated) != 1 or dmesg.count(gated) != 1:
            raise ValueError("unique I2C6 clock validation pair is absent")
        if len(guard_lines) != 1:
            raise ValueError("unique I2C6 guarded-init publication is absent")
        guard_payload = guard_lines[0].split(guard_marker, 1)[1]
        parse_i2c_guard(
            guard_payload, include_pm=False, include_domains=True
        )
        positions = tuple(
            dmesg.index(token)
            for token in (supplier, ungated, gated, guard_marker)
        )
        if positions != tuple(sorted(positions)):
            raise ValueError(
                "I2C6 initialization preceded access-controller readiness"
            )
    elif terminal == "inconclusive":
        if supplier in dmesg or ungated in dmesg or gated in dmesg:
            raise ValueError("denied access-controller terminal still initialized I2C6")
        if len(guard_lines) != 1:
            raise ValueError("unique denied I2C6 probe publication is absent")
        denial_payload = guard_lines[0].split(guard_marker, 1)[1]
        parse_i2c_denial(denial_payload)
        denied_terminal = (
            "supplier_bound=yes access_grant=denied state=inconclusive "
            "reason=initial-gate-already-gated access_controller=enabled"
        )
        if dmesg.index(denied_terminal) >= dmesg.index(guard_marker):
            raise ValueError("I2C6 denial preceded the provider terminal result")
    elif terminal == "faulted":
        if (
            dmesg.count(supplier) != 1
            or dmesg.count(ungated) != 1
            or dmesg.count(failed_cleanup) != 1
            or dmesg.count(faulted_state) != 1
            or gated in dmesg
            or guard_lines
        ):
            raise ValueError(
                "fail-closed post-grant I2C6 chronology is incomplete or conflicting"
            )
        probe_match = fault_probe.search(dmesg)
        assert probe_match is not None
        positions = (
            dmesg.index(supplier),
            dmesg.index(ungated),
            dmesg.index(failed_cleanup),
            dmesg.index(faulted_state),
            probe_match.start(),
        )
        if positions != tuple(sorted(positions)):
            raise ValueError("fail-closed I2C6 chronology is reordered")
    else:
        raise ValueError("unsupported provider terminal result")

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

    outcome = {
        "ready": "PASS",
        "inconclusive": "INCONCLUSIVE",
        "faulted": "FAIL",
    }[terminal]
    return ValidationResult(
        outcome=outcome,
        boot_id=identity["boot_id"],
        uptime_seconds=int(second["uptime_seconds"]),
        snapshot_sha256=first["handoff_snapshots_sha256"],
    )


def regular_nonempty(path: pathlib.Path) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError("runtime capture is missing, empty, or unsafe")


def validate_collector_source(path: pathlib.Path) -> None:
    regular_nonempty(path)
    source_bytes = path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != COLLECTOR_SHA256:
        raise ValueError("runtime collector source identity changed")
    source = source_bytes.decode("utf-8", errors="strict")
    for token in FORBIDDEN_COLLECTOR_ACTIONS:
        if token in source:
            raise ValueError(
                f"runtime collector contains forbidden hardware action: {token}"
            )
    if source.count("power_state_transition_requested=no") != 1:
        raise ValueError("runtime collector lacks the explicit no-transition attestation")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", required=True, type=pathlib.Path)
    parser.add_argument("--expected-installed-full-sha256", required=True)
    parser.add_argument("--expected-config-sha256", required=True)
    parser.add_argument("--expected-live-fdt-sha256", required=True)
    parser.add_argument("--expected-boot-id", required=True)
    args = parser.parse_args()
    try:
        validate_collector_source(pathlib.Path(__file__).with_name("collect-runtime.sh"))
        regular_nonempty(args.capture)
        result = validate(
            args.capture.read_text(encoding="utf-8", errors="strict"),
            args.expected_installed_full_sha256,
            args.expected_config_sha256,
            args.expected_live_fdt_sha256,
            args.expected_boot_id,
        )
        print("validation=candidate-ap-mt6797-dvfsp-i2c6-consumer-runtime")
        print(f"outcome={result.outcome}")
        print(f"boot_id={result.boot_id}")
        print(f"uptime_seconds={result.uptime_seconds}")
        print(f"snapshot_sha256={result.snapshot_sha256}")
        print("installed_identity=caller-supplied-prior-full-readback")
        if result.outcome == "FAIL":
            print("next_action=return-to-known-good-os-and-inspect-fault")
            return 4
        if result.outcome == "INCONCLUSIVE":
            print("i2c6_controller=unbound-no-adapter-no-operation")
            print("next_action=do-not-repeat-without-decision-changing-evidence")
            return 3
        print("pcm_reset_contract=independently-classified")
        print("i2c6_controller=initialized-once-after-ready")
        print("i2c6_transfer_dma_start_irq=0")
        print("i2c6_children_clients_da9214_regulators=0")
        print("suspend_resume_checks_failures=0")
        print("a72_cpu8_cpu9_activity=absent")
        print("cpu0_cpu7_accounting=advanced")
        print("usb_keyboard_console_reboot=inherited-runtime-contract")
        print("reboot_executed_by_collector=no")
        print("clock_transition=ungated-enabled-to-post-and-late-gated")
        print("ccf_enable_disable=one-each")
        print("late_validation=passed")
        print("next_action=review-read-only-childless-controller-evidence")
        return 0
    except (OSError, UnicodeError, ValueError, KeyError) as exc:
        print(f"failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
