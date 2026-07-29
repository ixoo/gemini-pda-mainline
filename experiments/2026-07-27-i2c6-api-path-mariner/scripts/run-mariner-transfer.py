#!/usr/bin/env python3
"""Transfer and invoke exact Mariner once on the accepted Hubble boot."""

from __future__ import annotations

import argparse
import base64
import os
import pathlib
import re
import stat
import subprocess
import sys
import textwrap

sys.dont_write_bytecode = True
import candidate_mariner as ck


HOST_MAC = "42:00:15:19:82:00"
HOST_ADDRESS = "10.15.19.1"
DEVICE_ADDRESS = "10.15.19.82"
DEVICE_PORT = 2323
USB_BANNER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
CASSINI_HELPER_SHA256 = (
    "30073f6ea7d0b57d3654ece5c6212da1c94ff4d24514b62d07331136a4efaf0e"
)
CASSINI_HELPER_SIZE = 537_584
CASSINI_CONFIG_SHA256 = (
    "83c85429cdcb7d66cb96df2c9005456afd67fc5c7dbfe5d76e9879bf45c1759b"
)
CASSINI_KERNEL = "7.1.3-gemini-cassini"
CASSINI_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Cassini "
    "g_ether.iSerialNumber=GEMINI_CASSINI_20260727 "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused "
    "initcall_blacklist=mt6797_a72_power_driver_init fw_devlink=rpm"
)
I2C_PRE_STATUS = (
    "handoff=ready probe_attempts=1 init_attempts=1 init_successes=1 "
    "clock_ungated_checks=1 clock_gated_checks=1 "
    "clock_validation_failures=0 runtime_pm_link=1 "
    "clock_domains=i2c-appm,ap-dma transfer_attempts=14 dma_starts=14 "
    "nonzero_starts=14 irq_count=14 suspend_checks=0 resume_checks=0 "
    "resume_failures=0"
)

PRIVATE_RELATIVE_ROOT = pathlib.Path("artifacts/runtime-captures")
TRANSCRIPT_NAME = "mariner-runtime-transfer.txt"
STDERR_NAME = "mariner-nc-stderr.txt"
INTERFACE = re.compile(r"[A-Za-z0-9]+")
HEX_BYTE = re.compile(r"[0-9a-f]{2}")


REMOTE_TEMPLATE = r"""/bin/busybox sh <<'__MARINER_REMOTE__'
set -eu
umask 077

probe_path=/run/mariner-probe
stage_path=/run/.mariner-probe.stage
guard_path=/run/mariner-probe.invoked
photon_path=/run/hubble-photon-r2
photon_stage=/run/.hubble-photon-r2.stage
photon_guard=/run/hubble-photon-r2.invoked
kepler_path=/run/kepler-probe
kepler_stage=/run/.kepler-probe.stage
kepler_guard=/run/kepler-probe.invoked
voyager_path=/run/voyager-probe
voyager_stage=/run/.voyager-probe.stage
voyager_guard=/run/voyager-probe.invoked
handoff=/sys/bus/platform/devices/11015000.dvfsp-handoff
i2c6=/sys/bus/platform/devices/1100e000.i2c

abort() {
	printf '\n__MARINER_ABORT__ reason=%s\n' "$1"
	exit 90
}
require_equal() {
	[ "$1" = "$2" ] || abort "$3"
}
file_sha256() {
	/bin/busybox sha256sum "$1" | /bin/busybox awk '{ print $1 }'
}
cleanup() {
	/bin/busybox rm -f "$stage_path" "$probe_path"
}
on_signal() {
	trap - HUP INT TERM PIPE
	exit 91
}
trap cleanup EXIT
trap on_signal HUP INT TERM PIPE

require_equal "$(/bin/busybox id -u)" 0 not-root
require_equal "$(/bin/busybox uname -r)" "__CASSINI_KERNEL__" kernel-identity
cmdline=$(/bin/busybox cat /proc/cmdline)
require_equal "$cmdline" "__CASSINI_CMDLINE__" cmdline-identity
config_sha256=$(
	/bin/busybox zcat /proc/config.gz |
		/bin/busybox sha256sum |
		/bin/busybox awk '{ print $1 }'
)
require_equal "$config_sha256" "__CASSINI_CONFIG_SHA256__" config-identity
[ -f /bin/cassini-probe ] && [ ! -L /bin/cassini-probe ] ||
	abort cassini-helper-type
require_equal "$(/bin/busybox stat -c '%s' /bin/cassini-probe)" \
	"__CASSINI_HELPER_SIZE__" cassini-helper-size
require_equal "$(file_sha256 /bin/cassini-probe)" \
	"__CASSINI_HELPER_SHA256__" cassini-helper-identity
require_equal "$(/bin/busybox stat -c '%a:%u:%g' /bin/cassini-probe)" \
	"755:0:0" cassini-helper-mode

rootfs_type=$(
	/bin/busybox awk \
	'$2 == "/" { print $3; count++ } END { if (count != 1) exit 1 }' \
	/proc/mounts
)
case "$rootfs_type" in rootfs|ramfs|tmpfs) ;; *) abort nonvolatile-rootfs ;; esac
run_mounts=$(
	/bin/busybox awk '$2 == "/run" { count++ } END { print count + 0 }' \
	/proc/mounts
)
require_equal "$run_mounts" 0 separate-run-mount
[ -d /run ] && [ ! -L /run ] || abort run-type
for path in "$probe_path" "$stage_path" "$guard_path"; do
	[ ! -e "$path" ] && [ ! -L "$path" ] || abort prior-mariner-path
done
for prior_path in "$photon_path" "$photon_stage" "$kepler_path" \
	"$kepler_stage" "$voyager_path" "$voyager_stage"; do
	[ ! -e "$prior_path" ] && [ ! -L "$prior_path" ] ||
		abort prior-helper-or-stage-present
done
for prior_guard in "$photon_guard" "$kepler_guard" "$voyager_guard"; do
	[ -f "$prior_guard" ] && [ ! -L "$prior_guard" ] ||
		abort prior-guard-type
	require_equal "$(/bin/busybox stat -c '%s' "$prior_guard")" 0 \
		prior-guard-size
	require_equal "$(/bin/busybox stat -c '%a:%u:%g' "$prior_guard")" \
		400:0:0 prior-guard-mode
done

boot_id=$(/bin/busybox cat /proc/sys/kernel/random/boot_id)
require_equal "$boot_id" "__ACCEPTED_BOOT_ID__" accepted-hubble-boot-id
require_equal "$(/bin/busybox cat /sys/devices/system/cpu/possible)" \
	0-9 cpu-possible
require_equal "$(/bin/busybox cat /sys/devices/system/cpu/present)" \
	0-9 cpu-present
require_equal "$(/bin/busybox cat /sys/devices/system/cpu/online)" \
	0-7 cpu-online
require_equal "$(/bin/busybox cat /sys/devices/system/cpu/offline)" \
	8-9 cpu-offline
require_equal "$(/bin/busybox nproc)" 8 cpu-nproc
[ ! -e /sys/devices/system/cpu/cpu8/online ] || abort cpu8-control-present
[ ! -e /sys/devices/system/cpu/cpu9/online ] || abort cpu9-control-present

require_equal "$(/bin/busybox cat "$handoff/state")" ready handoff-state
i2c_status_pre=$(/bin/busybox cat "$i2c6/handoff_status")
require_equal "$i2c_status_pre" "__I2C_PRE_STATUS__" i2c-pre-exact

adapter_count=0
adapter_name=
adapter_of=
for adapter in /sys/class/i2c-dev/i2c-*; do
	[ -d "$adapter" ] || continue
	target=$(/bin/busybox readlink -f "$adapter/device/of_node" 2>/dev/null || true)
	case "$target" in
	*/i2c@1100e000)
		adapter_count=$((adapter_count + 1))
		adapter_name=${adapter##*/}
		adapter_of=$target
		;;
	esac
done
require_equal "$adapter_count" 1 i2c6-adapter-count
require_equal "$adapter_name" i2c-1 accepted-i2c6-adapter
[ -c "/dev/$adapter_name" ] || abort i2c6-device-type
client_count=0
adapter_number=${adapter_name#i2c-}
for client in /sys/bus/i2c/devices/"$adapter_number"-*; do
	[ ! -d "$client" ] || client_count=$((client_count + 1))
done
require_equal "$client_count" 0 i2c6-client-count

require_equal "$(/bin/busybox cat /sys/class/net/usb0/address)" \
	42:00:15:19:82:01 usb-address
require_equal "$(/bin/busybox cat /sys/class/net/usb0/carrier)" 1 usb-carrier
require_equal "$(/bin/busybox cat /sys/class/net/usb0/operstate)" up usb-operstate
usb_ipv4=$(
	/bin/busybox ip -o -4 address show dev usb0 |
		/bin/busybox awk \
		'$4 == "10.15.19.82/24" { count++ } END { print count + 0 }'
)
require_equal "$usb_ipv4" 1 usb-ipv4
udc_count=0
udc_name=
udc_state=
for udc in /sys/class/udc/*; do
	[ -d "$udc" ] || continue
	udc_count=$((udc_count + 1))
	udc_name=${udc##*/}
	udc_state=$(/bin/busybox cat "$udc/state")
done
require_equal "$udc_count" 1 udc-count
require_equal "$udc_state" configured udc-state
service_count=$(
	/bin/busybox grep -c \
	'service=nc status=listening address=10.15.19.82 port=2323' \
	/run/ac-status || true
)
require_equal "$service_count" 1 usb-service-count
ready_count=$(
	/bin/busybox grep -c \
	'usb_shell=ready reboot_dispatch=validated privilege=root' \
	/run/ac-status || true
)
[ "$ready_count" -ge 1 ] && [ "$ready_count" -le 64 ] ||
	abort usb-ready-count

printf '\n__MARINER_GATE_BEGIN__\n'
printf 'kernel=%s\ncmdline=%s\nconfig_sha256=%s\n' \
	"__CASSINI_KERNEL__" "$cmdline" "$config_sha256"
printf 'cassini_helper_sha256=%s\ncassini_helper_size=%s\n' \
	"__CASSINI_HELPER_SHA256__" "__CASSINI_HELPER_SIZE__"
printf 'rootfs_type=%s\nrun_mounts=%s\nboot_id=%s\n' \
	"$rootfs_type" "$run_mounts" "$boot_id"
printf 'cpu_possible=0-9\ncpu_present=0-9\ncpu_online=0-7\n'
printf 'cpu_offline=8-9\nnproc=8\nhandoff_state=ready\n'
printf 'i2c6_status_pre=%s\ni2c6_adapter=%s\ni2c6_of=%s\n' \
	"$i2c_status_pre" "$adapter_name" "$adapter_of"
printf 'i2c6_clients=0\nprior_photon_guard=400:0:0\n'
printf 'prior_kepler_guard=400:0:0\nprior_voyager_guard=400:0:0\n'
printf 'usb0_address=42:00:15:19:82:01\nusb0_carrier=1\n'
printf 'usb0_operstate=up\nusb0_ipv4_exact=1\n'
printf 'udc_name=%s\nudc_state=configured\n' "$udc_name"
printf 'usb_service_count=1\nusb_ready_count=%s\n' "$ready_count"
printf '__MARINER_GATE_END__\n__MARINER_GATE_PASS__\n'

/bin/busybox base64 -d >"$stage_path" <<'__MARINER_PAYLOAD__'
__PAYLOAD_BASE64__
__MARINER_PAYLOAD__
[ -f "$stage_path" ] && [ ! -L "$stage_path" ] || abort stage-type
require_equal "$(/bin/busybox stat -c '%s' "$stage_path")" \
	"__MARINER_SIZE__" stage-size
require_equal "$(file_sha256 "$stage_path")" "__MARINER_SHA256__" stage-hash
/bin/busybox chmod 0500 "$stage_path"
/bin/busybox mv "$stage_path" "$probe_path"
[ -f "$probe_path" ] && [ ! -L "$probe_path" ] || abort probe-type
require_equal "$(/bin/busybox stat -c '%s' "$probe_path")" \
	"__MARINER_SIZE__" probe-size
require_equal "$(file_sha256 "$probe_path")" "__MARINER_SHA256__" probe-hash
require_equal "$(/bin/busybox stat -c '%a:%u:%g' "$probe_path")" \
	500:0:0 probe-mode
printf '__MARINER_TRANSFER_PASS__ size=%s sha256=%s mode=500:0:0 path=/run/mariner-probe\n' \
	"__MARINER_SIZE__" "__MARINER_SHA256__"

printf '__MARINER_PRE_BEGIN__\n'
printf 'boot_id_pre=%s\ncpu_online_pre=%s\ncpu_offline_pre=%s\nnproc_pre=%s\n' \
	"$boot_id" \
	"$(/bin/busybox cat /sys/devices/system/cpu/online)" \
	"$(/bin/busybox cat /sys/devices/system/cpu/offline)" \
	"$(/bin/busybox nproc)"
printf 'handoff_state_pre=%s\ni2c6_status_pre=%s\n' \
	"$(/bin/busybox cat "$handoff/state")" \
	"$(/bin/busybox cat "$i2c6/handoff_status")"
printf 'usb_carrier_pre=%s\nusb_operstate_pre=%s\nudc_state_pre=%s\n' \
	"$(/bin/busybox cat /sys/class/net/usb0/carrier)" \
	"$(/bin/busybox cat /sys/class/net/usb0/operstate)" "$udc_state"
printf '__MARINER_PRE_END__\n'

( set -C; : >"$guard_path" ) 2>/dev/null || abort invocation-guard
/bin/busybox chmod 0400 "$guard_path"
printf '__MARINER_PROBE_STDOUT_BEGIN__\n'
set +e
"$probe_path"
probe_rc=$?
set -e
printf '__MARINER_PROBE_STDOUT_END__\n'
/bin/busybox rm -f "$probe_path"
[ ! -e "$probe_path" ] && [ ! -L "$probe_path" ] || abort probe-cleanup

printf '__MARINER_POST_BEGIN__\n'
boot_id_post=$(/bin/busybox cat /proc/sys/kernel/random/boot_id)
i2c_status_post=$(/bin/busybox cat "$i2c6/handoff_status")
printf 'boot_id_post=%s\ncpu_online_post=%s\ncpu_offline_post=%s\nnproc_post=%s\n' \
	"$boot_id_post" \
	"$(/bin/busybox cat /sys/devices/system/cpu/online)" \
	"$(/bin/busybox cat /sys/devices/system/cpu/offline)" \
	"$(/bin/busybox nproc)"
printf 'handoff_state_post=%s\ni2c6_status_post=%s\n' \
	"$(/bin/busybox cat "$handoff/state")" "$i2c_status_post"
printf 'usb_carrier_post=%s\nusb_operstate_post=%s\nudc_state_post=%s\n' \
	"$(/bin/busybox cat /sys/class/net/usb0/carrier)" \
	"$(/bin/busybox cat /sys/class/net/usb0/operstate)" \
	"$(/bin/busybox cat /sys/class/udc/"$udc_name"/state)"
printf '__MARINER_POST_END__\n'
printf '__MARINER_COMPLETE__ probe_rc=%s invocation_count=1 helper_removed=yes guard_mode=%s\n' \
	"$probe_rc" "$(/bin/busybox stat -c '%a:%u:%g' "$guard_path")"
exit
__MARINER_REMOTE__
exit
"""


class ContractError(ValueError):
    """A local or captured runtime contract did not match exactly."""


def read_exact_helper(path: pathlib.Path) -> bytes:
    ck.require_pins()
    if not path.is_absolute():
        raise ContractError("helper path must be absolute")
    data = ck.regular(path, "Mariner helper")
    if len(data) != ck.PROBE_BINARY_SIZE or ck.digest(data) != ck.PROBE_BINARY_SHA256:
        raise ContractError("helper is not the exact Mariner ELF")
    return data


def read_prior_voyager_capture(path: pathlib.Path) -> bytes:
    if not path.is_absolute():
        raise ContractError("prior Voyager capture path must be absolute")
    info = path.lstat()
    if (
        path.is_symlink()
        or not stat.S_ISREG(info.st_mode)
        or stat.S_IMODE(info.st_mode) != 0o600
    ):
        raise ContractError("prior Voyager capture is not exact private mode-0600 data")
    data = path.read_bytes()
    if ck.digest(data) != ck.PRIOR_VOYAGER_CAPTURE_SHA256:
        raise ContractError("prior Voyager capture identity differs")
    text = data.decode("ascii", "strict")
    required = (
        f"boot_id={ck.ACCEPTED_BOOT_ID}",
        (
            "GEMINI_VOYAGER_RESULT class=split-pointer-echo "
            "completed_pairs=2 completed_calls=4 ioctl_result=1 errno=0 "
            "pre=3c,a6 post=06,47 post_diff_mask=0x03 "
            "stop_between_pointer_and_read=yes page_con_access=none"
        ),
        (
            "__VOYAGER_COMPLETE__ probe_rc=2 invocation_count=1 "
            "helper_removed=yes guard_mode=400:0:0"
        ),
        (
            "transfer_attempts=14 dma_starts=14 nonzero_starts=14 "
            "irq_count=14"
        ),
    )
    for marker in required:
        if text.count(marker) < 1:
            raise ContractError("prior Voyager capture lost required result evidence")
    return data


def build_remote_program(helper: bytes) -> bytes:
    ck.require_pins()
    if (
        len(helper) != ck.PROBE_BINARY_SIZE
        or ck.digest(helper) != ck.PROBE_BINARY_SHA256
    ):
        raise ContractError("refusing to serialize non-Mariner helper bytes")
    payload = "\n".join(textwrap.wrap(base64.b64encode(helper).decode("ascii"), 76))
    replacements = {
        "__CASSINI_KERNEL__": CASSINI_KERNEL,
        "__CASSINI_CMDLINE__": CASSINI_CMDLINE,
        "__CASSINI_CONFIG_SHA256__": CASSINI_CONFIG_SHA256,
        "__CASSINI_HELPER_SHA256__": CASSINI_HELPER_SHA256,
        "__CASSINI_HELPER_SIZE__": str(CASSINI_HELPER_SIZE),
        "__ACCEPTED_BOOT_ID__": ck.ACCEPTED_BOOT_ID,
        "__I2C_PRE_STATUS__": I2C_PRE_STATUS,
        "__MARINER_SHA256__": ck.PROBE_BINARY_SHA256,
        "__MARINER_SIZE__": str(ck.PROBE_BINARY_SIZE),
        "__PAYLOAD_BASE64__": payload,
    }
    program = REMOTE_TEMPLATE
    for token, value in replacements.items():
        if program.count(token) < 1:
            raise ContractError(f"remote template lost token {token}")
        program = program.replace(token, value)
    return program.encode("ascii")


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def prepare_output(repository: pathlib.Path, output_dir: pathlib.Path) -> pathlib.Path:
    root = (repository / PRIVATE_RELATIVE_ROOT).resolve()
    if not root.is_dir() or root.is_symlink():
        raise ContractError("private runtime-capture root is missing or unsafe")
    if stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise ContractError("private runtime-capture root must be mode 0700")
    if not output_dir.is_absolute() or output_dir.parent.resolve() != root:
        raise ContractError(
            "output must be one new direct child of artifacts/runtime-captures"
        )
    if output_dir.exists() or output_dir.is_symlink():
        raise ContractError("refusing to reuse runtime output directory")
    output_dir.mkdir(mode=0o700)
    return output_dir / TRANSCRIPT_NAME


def run_checked(command: list[str]) -> bytes:
    result = subprocess.run(command, check=False, capture_output=True, timeout=20)
    if result.returncode != 0:
        raise ContractError(f"host command failed: {command[0]}")
    return result.stdout


def verify_host_link(interface: str) -> None:
    if INTERFACE.fullmatch(interface) is None:
        raise ContractError("interface contains unsupported characters")
    ifconfig = run_checked(["ifconfig", interface]).decode("ascii", "strict")
    macs = re.findall(r"^\s*ether\s+([0-9a-f:]+)\s*$", ifconfig, re.MULTILINE)
    if macs != [HOST_MAC]:
        raise ContractError("interface is not the exact Gemini USB host MAC")
    addresses = re.findall(r"^\s*inet\s+(\S+)", ifconfig, re.MULTILINE)
    if addresses.count(HOST_ADDRESS) != 1:
        raise ContractError("exact host USB IPv4 address is absent or duplicated")
    route = run_checked(["route", "-n", "get", DEVICE_ADDRESS]).decode(
        "ascii", "strict"
    )
    routes = re.findall(r"^\s*interface:\s*(\S+)\s*$", route, re.MULTILINE)
    if routes != [interface]:
        raise ContractError("device route is not the exact Gemini USB interface")
    run_checked(
        ["ping", "-b", interface, "-c", "3", "-S", HOST_ADDRESS, DEVICE_ADDRESS]
    )


def run_transport(interface: str, program: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            "nc",
            "-4",
            "-b",
            interface,
            "-s",
            HOST_ADDRESS,
            "-G",
            "5",
            "-w",
            "120",
            DEVICE_ADDRESS,
            str(DEVICE_PORT),
        ],
        input=program,
        check=False,
        capture_output=True,
        timeout=150,
    )


def write_private(path: pathlib.Path, data: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def unique_section(text: str, begin: str, end: str) -> list[str]:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ContractError(f"capture marker is absent or duplicated: {begin}")
    start = text.index(begin) + len(begin)
    stop = text.index(end, start)
    if stop <= start:
        raise ContractError(f"capture marker order is invalid: {begin}")
    return [line for line in text[start:stop].splitlines() if line]


def key_values(lines: list[str], label: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        if "=" not in line:
            raise ContractError(f"{label} contains a non-key/value line")
        key, value = line.split("=", 1)
        if not key or key in values:
            raise ContractError(f"{label} key is empty or duplicated")
        values[key] = value
    return values


def marker_values(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for field in line.split():
        if field.count("=") != 1:
            raise ContractError("marker field grammar changed")
        key, value = field.split("=", 1)
        if not key or key in values:
            raise ContractError("marker field is empty or duplicated")
        values[key] = value
    return values


def status_values(line: str) -> dict[str, str]:
    values = marker_values(line)
    expected = {
        "handoff",
        "probe_attempts",
        "init_attempts",
        "init_successes",
        "clock_ungated_checks",
        "clock_gated_checks",
        "clock_validation_failures",
        "runtime_pm_link",
        "clock_domains",
        "transfer_attempts",
        "dma_starts",
        "nonzero_starts",
        "irq_count",
        "suspend_checks",
        "resume_checks",
        "resume_failures",
    }
    if set(values) != expected:
        raise ContractError("I2C6 status field inventory changed")
    return values


def classify_posts(post0: str, post1: str, mask: int) -> str:
    computed = (post0 != "3c") | ((post1 != "a6") << 1)
    if mask != computed:
        raise ContractError("post-diff mask does not match receive bytes")
    if (post0, post1) == ("d0", "c0"):
        return "raw-expected-live"
    if (post0, post1) == ("06", "47"):
        return "raw-pointer-echo"
    if (post0, post1) == ("47", "06"):
        return "raw-lag"
    if (post0, post1) == ("00", "00"):
        return "raw-zero"
    return "raw-other"


def validate_transcript(data: bytes) -> dict[str, str]:
    if not data or len(data) > 1_048_576 or b"\0" in data:
        raise ContractError("transport output is empty, oversized, or binary")
    text = data.decode("ascii", "strict")
    if text.splitlines().count(USB_BANNER) != 1:
        raise ContractError("exact direct USB shell banner is absent or duplicated")
    if "__MARINER_ABORT__" in text:
        raise ContractError("remote Hubble/serviceability gate aborted")
    ordered_markers = (
        "__MARINER_GATE_BEGIN__",
        "__MARINER_GATE_END__",
        "__MARINER_GATE_PASS__",
        "__MARINER_TRANSFER_PASS__",
        "__MARINER_PRE_BEGIN__",
        "__MARINER_PRE_END__",
        "__MARINER_PROBE_STDOUT_BEGIN__",
        "__MARINER_PROBE_STDOUT_END__",
        "__MARINER_POST_BEGIN__",
        "__MARINER_POST_END__",
        "__MARINER_COMPLETE__",
    )
    positions: list[int] = []
    for marker in ordered_markers:
        if text.count(marker) != 1:
            raise ContractError(f"runtime completion marker differs: {marker}")
        positions.append(text.index(marker))
    if positions != sorted(positions) or len(set(positions)) != len(positions):
        raise ContractError("runtime section order differs")

    gate = key_values(
        unique_section(text, "__MARINER_GATE_BEGIN__", "__MARINER_GATE_END__"),
        "Hubble gate",
    )
    expected_gate = {
        "kernel": CASSINI_KERNEL,
        "cmdline": CASSINI_CMDLINE,
        "config_sha256": CASSINI_CONFIG_SHA256,
        "cassini_helper_sha256": CASSINI_HELPER_SHA256,
        "cassini_helper_size": str(CASSINI_HELPER_SIZE),
        "rootfs_type": "rootfs",
        "run_mounts": "0",
        "boot_id": ck.ACCEPTED_BOOT_ID,
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "nproc": "8",
        "handoff_state": "ready",
        "i2c6_adapter": "i2c-1",
        "i2c6_clients": "0",
        "prior_photon_guard": "400:0:0",
        "prior_kepler_guard": "400:0:0",
        "prior_voyager_guard": "400:0:0",
        "usb0_address": "42:00:15:19:82:01",
        "usb0_carrier": "1",
        "usb0_operstate": "up",
        "usb0_ipv4_exact": "1",
        "udc_state": "configured",
        "usb_service_count": "1",
    }
    for key, wanted in expected_gate.items():
        if gate.get(key) != wanted:
            raise ContractError(f"exact accepted Hubble gate differs: {key}")
    variable_gate = {"i2c6_status_pre", "i2c6_of", "udc_name", "usb_ready_count"}
    if set(gate) != set(expected_gate) | variable_gate:
        raise ContractError("Hubble gate field inventory changed")
    if not gate["i2c6_of"].endswith("/i2c@1100e000"):
        raise ContractError("I2C6 OF identity differs")
    if not gate["usb_ready_count"].isdecimal() or not (
        1 <= int(gate["usb_ready_count"]) <= 64
    ):
        raise ContractError("USB ready count is malformed")

    transfer = next(
        line for line in text.splitlines() if line.startswith("__MARINER_TRANSFER_PASS__")
    )
    if marker_values(transfer.split(" ", 1)[1]) != {
        "size": str(ck.PROBE_BINARY_SIZE),
        "sha256": ck.PROBE_BINARY_SHA256,
        "mode": "500:0:0",
        "path": "/run/mariner-probe",
    }:
        raise ContractError("volatile Mariner helper identity differs")

    pre = key_values(
        unique_section(text, "__MARINER_PRE_BEGIN__", "__MARINER_PRE_END__"),
        "pre-probe state",
    )
    post = key_values(
        unique_section(text, "__MARINER_POST_BEGIN__", "__MARINER_POST_END__"),
        "post-probe state",
    )
    if pre.get("boot_id_pre") != ck.ACCEPTED_BOOT_ID:
        raise ContractError("pre-probe boot ID differs")
    if post.get("boot_id_post") != ck.ACCEPTED_BOOT_ID:
        raise ContractError("boot ID changed around Mariner")
    for values, suffix in ((pre, "pre"), (post, "post")):
        expected = {
            f"cpu_online_{suffix}": "0-7",
            f"cpu_offline_{suffix}": "8-9",
            f"nproc_{suffix}": "8",
            f"handoff_state_{suffix}": "ready",
            f"usb_carrier_{suffix}": "1",
            f"usb_operstate_{suffix}": "up",
            f"udc_state_{suffix}": "configured",
        }
        for key, wanted in expected.items():
            if values.get(key) != wanted:
                raise ContractError(f"service state differs: {key}")

    i2c_pre = status_values(pre["i2c6_status_pre"])
    i2c_post = status_values(post["i2c6_status_post"])
    if i2c_pre != status_values(gate["i2c6_status_pre"]):
        raise ContractError("I2C6 gate/pre status changed before invocation")
    static_status = {
        "handoff": "ready",
        "probe_attempts": "1",
        "init_attempts": "1",
        "init_successes": "1",
        "clock_ungated_checks": "1",
        "clock_gated_checks": "1",
        "clock_validation_failures": "0",
        "runtime_pm_link": "1",
        "clock_domains": "i2c-appm,ap-dma",
        "suspend_checks": "0",
        "resume_checks": "0",
        "resume_failures": "0",
    }
    for key, wanted in static_status.items():
        if i2c_pre[key] != wanted or i2c_post[key] != wanted:
            raise ContractError(f"I2C6 invariant changed: {key}")
    for key in ("transfer_attempts", "dma_starts", "nonzero_starts", "irq_count"):
        if (
            i2c_pre[key] != str(ck.PRE_COUNTER)
            or i2c_post[key] != str(ck.POST_COUNTER)
        ):
            raise ContractError(f"I2C6 exact four-call delta differs: {key}")

    stdout = unique_section(
        text, "__MARINER_PROBE_STDOUT_BEGIN__", "__MARINER_PROBE_STDOUT_END__"
    )
    if len(stdout) != 7:
        raise ContractError("Mariner successful stdout must contain exactly seven lines")
    wanted_line_order = (
        "GEMINI_MARINER_BEGIN ",
        "GEMINI_MARINER_SELECT ",
        "GEMINI_MARINER_WRITE pair=1 ",
        "GEMINI_MARINER_READ pair=1 ",
        "GEMINI_MARINER_WRITE pair=2 ",
        "GEMINI_MARINER_READ pair=2 ",
        "GEMINI_MARINER_RESULT ",
    )
    if tuple(
        next((prefix for prefix in wanted_line_order if line.startswith(prefix)), "")
        for line in stdout
    ) != wanted_line_order:
        raise ContractError("Mariner helper line order differs")
    begin = marker_values(stdout[0].split(" ", 1)[1])
    if begin != {
        "adapter": "i2c-1",
        "of": "/i2c@1100e000",
        "address": "0x69",
        "registers": "06,47",
        "selection_ioctls": "1",
        "bus_syscalls": "4",
        "api": "write-read",
    }:
        raise ContractError("Mariner BEGIN contract differs")
    if marker_values(stdout[1].split(" ", 1)[1]) != {
        "call": "1",
        "request": "I2C_SLAVE",
        "address": "0x69",
        "result": "0",
        "errno": "0",
    }:
        raise ContractError("Mariner selection contract differs")

    posts: list[str] = []
    for index in range(2):
        write_line = stdout[index * 2 + 2]
        read_line = stdout[index * 2 + 3]
        if marker_values(write_line.split(" ", 1)[1]) != {
            "pair": str(index + 1),
            "bus_call": str(index * 2 + 1),
            "address": "0x69",
            "len": "1",
            "pointer": f"0x{('06', '47')[index]}",
            "result": "1",
            "errno": "0",
        }:
            raise ContractError("Mariner pointer-write contract differs")
        values = marker_values(read_line.split(" ", 1)[1])
        prefill = ("3c", "a6")[index]
        post_byte = values.get("post", "").removeprefix("0x")
        if HEX_BYTE.fullmatch(post_byte) is None:
            raise ContractError("Mariner read byte is malformed")
        differs = "no" if post_byte == prefill else "yes"
        if values != {
            "pair": str(index + 1),
            "bus_call": str(index * 2 + 2),
            "address": "0x69",
            "len": "1",
            "user_pre": f"0x{prefill}",
            "post": f"0x{post_byte}",
            "result": "1",
            "errno": "0",
            "post_differs_user_pre": differs,
        }:
            raise ContractError("Mariner one-byte read contract differs")
        posts.append(post_byte)

    result = marker_values(stdout[6].split(" ", 1)[1])
    if not re.fullmatch(r"0x0[0-3]", result.get("post_diff_user_mask", "")):
        raise ContractError("Mariner result mask is malformed")
    mask = int(result["post_diff_user_mask"], 16)
    wanted_class = classify_posts(posts[0], posts[1], mask)
    if result != {
        "class": wanted_class,
        "error_stage": "none",
        "completed_pairs": "2",
        "completed_bus_calls": "4",
        "select_result": "0",
        "transfer_result": "1",
        "errno": "0",
        "user_pre": "3c,a6",
        "post": f"{posts[0]},{posts[1]}",
        "post_diff_user_mask": f"0x{mask:02x}",
        "api": "write-read",
        "page_con_access": "none",
    }:
        raise ContractError("Mariner aggregate RESULT contract differs")

    complete = next(
        line for line in text.splitlines() if line.startswith("__MARINER_COMPLETE__")
    )
    wanted_rc = "0" if wanted_class == "raw-expected-live" else "2"
    if marker_values(complete.split(" ", 1)[1]) != {
        "probe_rc": wanted_rc,
        "invocation_count": "1",
        "helper_removed": "yes",
        "guard_mode": "400:0:0",
    }:
        raise ContractError("Mariner one-shot completion contract differs")
    return {
        "boot_id": ck.ACCEPTED_BOOT_ID,
        "result_class": wanted_class,
        "probe_rc": wanted_rc,
        "post": ",".join(posts),
    }


def host_header(interface: str) -> bytes:
    return (
        "__MARINER_HOST_BEGIN__\n"
        f"interface={interface}\n"
        f"host_mac={HOST_MAC}\n"
        f"host_address={HOST_ADDRESS}\n"
        f"device_endpoint={DEVICE_ADDRESS}:{DEVICE_PORT}\n"
        "transport=direct-usb-nc-shell\n"
        "authentication=none\n"
        "encryption=none\n"
        f"accepted_boot_id={ck.ACCEPTED_BOOT_ID}\n"
        f"prior_voyager_capture_sha256={ck.PRIOR_VOYAGER_CAPTURE_SHA256}\n"
        f"helper_sha256={ck.PROBE_BINARY_SHA256}\n"
        f"helper_size={ck.PROBE_BINARY_SIZE}\n"
        "remote_destination=/run/mariner-probe\n"
        "persistent_storage_access=none\n"
        "watchdog_control=none\n"
        "reboot_or_slot_control=none\n"
        "__MARINER_HOST_END__\n"
    ).encode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", required=True)
    parser.add_argument("--helper", required=True, type=pathlib.Path)
    parser.add_argument(
        "--prior-voyager-capture", required=True, type=pathlib.Path
    )
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    transcript_path: pathlib.Path | None = None
    try:
        read_prior_voyager_capture(args.prior_voyager_capture)
        helper = read_exact_helper(args.helper)
        program = build_remote_program(helper)
        transcript_path = prepare_output(repository_root(), args.output_dir)
        verify_host_link(args.interface)
        transport = run_transport(args.interface, program)
        write_private(
            transcript_path, host_header(args.interface) + transport.stdout
        )
        if transport.stderr:
            write_private(transcript_path.parent / STDERR_NAME, transport.stderr)
        if transport.returncode != 0:
            raise ContractError("bounded direct-USB nc session failed")
        parsed = validate_transcript(transport.stdout)
    except (
        OSError,
        UnicodeError,
        ValueError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        if transcript_path is not None:
            print(f"capture={transcript_path}", file=sys.stderr)
        return 2
    print("validation=mariner-exact-hubble-volatile-api-path-one-shot")
    print(f"capture={transcript_path}")
    print(f"boot_id={parsed['boot_id']}")
    print(f"result_class={parsed['result_class']}")
    print(f"post={parsed['post']}")
    print(f"probe_rc={parsed['probe_rc']}")
    print("invocations=1")
    print("i2c6_counters=14-to-18")
    print("persistent_storage_watchdog_reboot_slot_control=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
