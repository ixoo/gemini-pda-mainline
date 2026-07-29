#!/usr/bin/env python3
"""Run Candidate Orion's fixed debugfs diagnostic once and preserve evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import pathlib
import re
import stat
import subprocess
import sys
from types import ModuleType

sys.dont_write_bytecode = True

import candidate_orion as co


HOST_MAC = "42:00:15:19:82:00"
HOST_ADDRESS = "10.15.19.1"
DEVICE_ADDRESS = "10.15.19.82"
DEVICE_PORT = 2323
USB_BANNER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
KERNEL_RELEASE = "7.1.3-gemini-orion"
KERNEL_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Orion "
    "g_ether.iSerialNumber=GEMINI_ORION_20260727 "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused "
    "initcall_blacklist=mt6797_a72_power_driver_init fw_devlink=rpm"
)
I2C6_COMPATIBLE_SHA256 = (
    "3201dae040836f855ff7c039a1f41a77e428793aa500122dc4fce27c7484dbaf"
)
I2C_STATUS_PRE = (
    "handoff=ready probe_attempts=1 init_attempts=1 init_successes=1 "
    "clock_ungated_checks=1 clock_gated_checks=1 "
    "clock_validation_failures=0 runtime_pm_link=1 "
    "clock_domains=i2c-appm,ap-dma transfer_attempts=0 dma_starts=0 "
    "nonzero_starts=0 irq_count=0 suspend_checks=0 resume_checks=0 "
    "resume_failures=0"
)
ORION_STATUS_PRE = (
    "candidate=Orion state=ready one_shot=unused run_error=0 attempted=0 "
    "completed=0 address=0x69 transfer_attempts=0 dma_starts=0 "
    "nonzero_starts=0 irqs=0 retries_before=1 retries_during=1 "
    "retries_after=1 registers=05,06,47 "
    "modes=packed-fifo,packed-dma,aux-dma"
)

PRIVATE_RELATIVE_ROOT = pathlib.Path("artifacts/runtime-captures")
TRANSCRIPT_NAME = "orion-runtime-raw.txt"
STDERR_NAME = "orion-nc-stderr-raw.txt"
RESULT_NAME = "orion-final-debugfs-raw.txt"
SUMMARY_NAME = "orion-sanitized-summary.txt"
INTERFACE = re.compile(r"[A-Za-z0-9]+")
HEX256 = re.compile(r"[0-9a-f]{64}")
REMOTE_TOKEN = re.compile(r"__[A-Z0-9_]+__")
RUNTIME_TOKENS = frozenset(
    {
        "__ORION_ABORT__",
        "__ORION_AC_STATUS_POST_BEGIN__",
        "__ORION_AC_STATUS_POST_END__",
        "__ORION_COMPLETE__",
        "__ORION_DMESG_RAW_BEGIN__",
        "__ORION_DMESG_RAW_END__",
        "__ORION_FINAL_BEGIN__",
        "__ORION_FINAL_END__",
        "__ORION_GATE_BEGIN__",
        "__ORION_GATE_END__",
        "__ORION_GATE_PASS__",
        "__ORION_I2C_STATUS_POST_BEGIN__",
        "__ORION_I2C_STATUS_POST_END__",
        "__ORION_POST_BEGIN__",
        "__ORION_POST_END__",
        "__ORION_REMOTE__",
    }
)


REMOTE_TEMPLATE = r"""/bin/busybox sh <<'__ORION_REMOTE__'
set -eu
umask 077

guard_path=/run/orion-run-all.invoked
debugfs_root=/run/orion-debugfs
handoff=/sys/bus/platform/devices/11015000.dvfsp-handoff
i2c6=/sys/bus/platform/devices/1100e000.i2c
dt_i2c6=/sys/firmware/devicetree/base/i2c@1100e000
debugfs_mounted=no

cleanup() {
	if [ "$debugfs_mounted" = yes ]; then
		/bin/busybox umount "$debugfs_root" 2>/dev/null || true
	fi
	/bin/busybox rmdir "$debugfs_root" 2>/dev/null || true
}
abort() {
	printf '\n__ORION_ABORT__ reason=%s\n' "$1"
	exit 90
}
require_equal() {
	[ "$1" = "$2" ] || abort "$3"
}
file_sha256() {
	/bin/busybox sha256sum "$1" | /bin/busybox awk '{ print $1 }'
}
on_signal() {
	trap - HUP INT TERM PIPE
	exit 91
}
trap cleanup EXIT
trap on_signal HUP INT TERM PIPE

require_equal "$(/bin/busybox id -u)" 0 not-root
require_equal "$(/bin/busybox uname -r)" "__ORION_KERNEL__" kernel-identity
cmdline=$(/bin/busybox cat /proc/cmdline)
require_equal "$cmdline" "__ORION_CMDLINE__" cmdline-identity
config_sha256=$(
	/bin/busybox zcat /proc/config.gz |
		/bin/busybox sha256sum |
		/bin/busybox awk '{ print $1 }'
)
require_equal "$config_sha256" "__ORION_CONFIG_SHA256__" config-identity

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
[ ! -e "$guard_path" ] && [ ! -L "$guard_path" ] ||
	abort prior-invocation-guard
[ ! -e "$debugfs_root" ] && [ ! -L "$debugfs_root" ] ||
	abort prior-debugfs-path

boot_id_pre=$(/bin/busybox cat /proc/sys/kernel/random/boot_id)
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
[ -f "$dt_i2c6/compatible" ] && [ ! -L "$dt_i2c6/compatible" ] ||
	abort i2c6-compatible-type
require_equal "$(file_sha256 "$dt_i2c6/compatible")" \
	"__ORION_I2C6_COMPATIBLE_SHA256__" i2c6-compatible
[ -d "$i2c6" ] || abort i2c6-platform-device-absent
[ -r "$i2c6/handoff_status" ] || abort i2c6-status-absent
if ! i2c_status_pre=$(/bin/busybox cat "$i2c6/handoff_status"); then
	abort i2c6-status-read
fi
require_equal "$i2c_status_pre" "__ORION_I2C_STATUS_PRE__" i2c6-pre-exact

adapter_count=0
adapter_name=
adapter_of=
for adapter in /sys/bus/i2c/devices/i2c-*; do
	[ -d "$adapter" ] || continue
	target=$(/bin/busybox readlink -f "$adapter/device/of_node" 2>/dev/null ||
		true)
	case "$target" in
	*/i2c@1100e000)
		adapter_count=$((adapter_count + 1))
		adapter_name=${adapter##*/}
		adapter_of=$target
		;;
	esac
done
require_equal "$adapter_count" 1 i2c6-adapter-count
client_count=0
adapter_number=${adapter_name#i2c-}
for client in /sys/bus/i2c/devices/"$adapter_number"-*; do
	[ ! -d "$client" ] || client_count=$((client_count + 1))
done
require_equal "$client_count" 0 i2c6-client-count
for i2c_dev in /dev/i2c-*; do
	[ ! -e "$i2c_dev" ] && [ ! -L "$i2c_dev" ] ||
		abort i2c-chardev-present
done

keyboard_count=0
for input_name in /sys/class/input/input*/name; do
	[ -f "$input_name" ] || continue
	if [ "$(/bin/busybox cat "$input_name")" = keyboard-matrix ]; then
		keyboard_count=$((keyboard_count + 1))
	fi
done
require_equal "$keyboard_count" 1 keyboard-device-count
[ -c /dev/tty1 ] || abort tty1-device-type

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

# README makes any pre-existing fatal/warning signature a stop condition.
# Inspect it before the one-shot, emit only the count, and discard the raw
# variable; the sole preserved raw kernel log is still the post-run capture.
set +e
pre_kernel_log=$(/bin/busybox dmesg 2>&1)
pre_dmesg_rc=$?
set -e
require_equal "$pre_dmesg_rc" 0 pre-dmesg-read
pre_dmesg_fatal_count=$(
	printf '%s\n' "$pre_kernel_log" |
		/bin/busybox awk \
		'/BUG:|WARNING:|Oops:|Kernel panic|Call trace:|Unhandled fault|Internal error/ {
			count++
		}
		END { print count + 0 }'
)
unset pre_kernel_log
require_equal "$pre_dmesg_fatal_count" 0 pre-dmesg-fatal

/bin/busybox mkdir -m 0700 "$debugfs_root"
/bin/busybox mount -t debugfs -o nosuid,nodev,noexec \
	debugfs "$debugfs_root" || abort debugfs-mount
debugfs_mounted=yes
debugfs_mounts=$(
	/bin/busybox awk -v path="$debugfs_root" \
	'$2 == path && $3 == "debugfs" { count++ }
	 END { print count + 0 }' /proc/mounts
)
require_equal "$debugfs_mounts" 1 debugfs-mount-identity
adapter_debugfs="$debugfs_root/i2c/$adapter_name"
[ -d "$adapter_debugfs" ] && [ ! -L "$adapter_debugfs" ] ||
	abort adapter-debugfs-type
diag="$adapter_debugfs/orion-run-all"
[ -f "$diag" ] && [ ! -L "$diag" ] || abort diagnostic-type
require_equal "$(/bin/busybox stat -c '%a:%u:%g' "$diag")" \
	600:0:0 diagnostic-mode
orion_status_pre=$(/bin/busybox cat "$diag")
require_equal "$orion_status_pre" "__ORION_STATUS_PRE__" diagnostic-pre-exact

printf '\n__ORION_GATE_BEGIN__\n'
printf 'kernel=%s\ncmdline=%s\nconfig_sha256=%s\n' \
	"__ORION_KERNEL__" "$cmdline" "$config_sha256"
printf 'rootfs_type=%s\nrun_mounts=%s\nboot_id_pre=%s\n' \
	"$rootfs_type" "$run_mounts" "$boot_id_pre"
printf 'cpu_possible=0-9\ncpu_present=0-9\ncpu_online=0-7\n'
printf 'cpu_offline=8-9\nnproc=8\nhandoff_state=ready\n'
printf 'i2c6_compatible_sha256=%s\n' \
	"__ORION_I2C6_COMPATIBLE_SHA256__"
printf 'i2c6_status_pre=%s\ni2c6_adapter=%s\ni2c6_of=%s\n' \
	"$i2c_status_pre" "$adapter_name" "$adapter_of"
printf 'i2c6_clients=0\ni2c_chardev=absent\n'
printf 'keyboard_devices=1\ntty1=character-device\n'
printf 'usb0_address=42:00:15:19:82:01\nusb0_carrier=1\n'
printf 'usb0_operstate=up\nusb0_ipv4_exact=1\n'
printf 'udc_name=%s\nudc_state=configured\n' "$udc_name"
printf 'usb_service_count=1\nusb_ready_count=%s\n' "$ready_count"
printf 'pre_dmesg_fatal_count=0\n'
printf 'debugfs_mount=%s\ndebugfs_mount_count=1\n' "$debugfs_root"
printf 'adapter_debugfs=%s\ndiagnostic_path=%s\n' "$adapter_debugfs" "$diag"
printf 'diagnostic_mode=600:0:0\n'
printf 'diagnostic_pre=%s\n' "$orion_status_pre"
printf '__ORION_GATE_END__\n__ORION_GATE_PASS__\n'

( set -C; : >"$guard_path" ) 2>/dev/null || abort invocation-guard
/bin/busybox chmod 0400 "$guard_path"

# This is the sole diagnostic write. From this point onward set -e remains
# disabled so a negative debugfs write cannot skip any post-run capture.
set +e
printf 'run\n' >"$diag"
write_rc=$?
orion_final=$(/bin/busybox cat "$diag" 2>&1)
orion_final_rc=$?
i2c_status_post=$(/bin/busybox cat "$i2c6/handoff_status" 2>&1)
i2c_status_post_rc=$?
kernel_log=$(/bin/busybox dmesg 2>&1)
dmesg_rc=$?
boot_id_post=$(/bin/busybox cat /proc/sys/kernel/random/boot_id 2>&1)
boot_id_post_rc=$?
cpu_online_post=$(
	/bin/busybox cat /sys/devices/system/cpu/online 2>&1
)
cpu_online_post_rc=$?
cpu_offline_post=$(
	/bin/busybox cat /sys/devices/system/cpu/offline 2>&1
)
cpu_offline_post_rc=$?
nproc_post=$(/bin/busybox nproc 2>&1)
nproc_post_rc=$?
handoff_state_post=$(/bin/busybox cat "$handoff/state" 2>&1)
handoff_state_post_rc=$?
usb_carrier_post=$(
	/bin/busybox cat /sys/class/net/usb0/carrier 2>&1
)
usb_carrier_post_rc=$?
usb_operstate_post=$(
	/bin/busybox cat /sys/class/net/usb0/operstate 2>&1
)
usb_operstate_post_rc=$?
udc_state_post=$(
	/bin/busybox cat /sys/class/udc/"$udc_name"/state 2>&1
)
udc_state_post_rc=$?
ac_status_post=$(/bin/busybox cat /run/ac-status 2>&1)
ac_status_post_rc=$?

printf '__ORION_FINAL_BEGIN__\n%s\n__ORION_FINAL_END__\n' "$orion_final"
printf '__ORION_I2C_STATUS_POST_BEGIN__\n%s\n' "$i2c_status_post"
printf '__ORION_I2C_STATUS_POST_END__\n'
printf '__ORION_POST_BEGIN__\n'
printf 'write_rc=%s\norion_final_rc=%s\ni2c_status_post_rc=%s\n' \
	"$write_rc" "$orion_final_rc" "$i2c_status_post_rc"
printf 'dmesg_rc=%s\nboot_id_post=%s\nboot_id_post_rc=%s\n' \
	"$dmesg_rc" "$boot_id_post" "$boot_id_post_rc"
printf 'cpu_online_post=%s\ncpu_online_post_rc=%s\n' \
	"$cpu_online_post" "$cpu_online_post_rc"
printf 'cpu_offline_post=%s\ncpu_offline_post_rc=%s\n' \
	"$cpu_offline_post" "$cpu_offline_post_rc"
printf 'nproc_post=%s\nnproc_post_rc=%s\n' "$nproc_post" "$nproc_post_rc"
printf 'handoff_state_post=%s\nhandoff_state_post_rc=%s\n' \
	"$handoff_state_post" "$handoff_state_post_rc"
printf 'usb_carrier_post=%s\nusb_carrier_post_rc=%s\n' \
	"$usb_carrier_post" "$usb_carrier_post_rc"
printf 'usb_operstate_post=%s\nusb_operstate_post_rc=%s\n' \
	"$usb_operstate_post" "$usb_operstate_post_rc"
printf 'udc_state_post=%s\nudc_state_post_rc=%s\n' \
	"$udc_state_post" "$udc_state_post_rc"
printf 'ac_status_post_rc=%s\n' "$ac_status_post_rc"
printf '__ORION_POST_END__\n'
printf '__ORION_AC_STATUS_POST_BEGIN__\n%s\n' "$ac_status_post"
printf '__ORION_AC_STATUS_POST_END__\n'

# Keep this complete log only in the private raw transcript. In particular,
# timeout-path i2c_dump_register() lines can contain DMA memory addresses.
printf '__ORION_DMESG_RAW_BEGIN__\n%s\n__ORION_DMESG_RAW_END__\n' \
	"$kernel_log"
printf '__ORION_COMPLETE__ write_rc=%s invocation_count=1 guard_mode=%s post_capture=unconditional\n' \
	"$write_rc" "$(/bin/busybox stat -c '%a:%u:%g' "$guard_path")"
exit 0
__ORION_REMOTE__
exit
"""


class ContractError(ValueError):
    """A local or captured runtime contract did not match exactly."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path.name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def validate_package(repository: pathlib.Path, package: pathlib.Path) -> str:
    validator = load_module(
        pathlib.Path(__file__).with_name("validate-package-orion.py"),
        "orion_package_validator",
    )
    validator.validate(repository, package)
    config = validator.regular(package / "kernel.config", "kernel config")
    return digest(config)


def build_remote_program(config_sha256: str) -> bytes:
    if HEX256.fullmatch(config_sha256) is None:
        raise ContractError("Orion configuration hash is malformed")
    replacements = {
        "__ORION_KERNEL__": KERNEL_RELEASE,
        "__ORION_CMDLINE__": KERNEL_CMDLINE,
        "__ORION_CONFIG_SHA256__": config_sha256,
        "__ORION_I2C6_COMPATIBLE_SHA256__": I2C6_COMPATIBLE_SHA256,
        "__ORION_I2C_STATUS_PRE__": I2C_STATUS_PRE,
        "__ORION_STATUS_PRE__": ORION_STATUS_PRE,
    }
    program = REMOTE_TEMPLATE
    if set(REMOTE_TOKEN.findall(program)) != set(replacements) | RUNTIME_TOKENS:
        raise ContractError("remote template token inventory changed")
    for token, value in replacements.items():
        if program.count(token) < 1:
            raise ContractError(f"remote template lost token {token}")
        program = program.replace(token, value)
    if set(REMOTE_TOKEN.findall(program)) != RUNTIME_TOKENS:
        raise ContractError(
            "remote template retained a placeholder or lost a runtime marker"
        )
    return program.encode("ascii")


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
    return output_dir


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


def run_transport(
    interface: str, program: bytes
) -> subprocess.CompletedProcess[bytes]:
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


def unique_section(text: str, begin: str, end: str) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ContractError(f"capture marker is absent or duplicated: {begin}")
    start = text.index(begin) + len(begin)
    stop = text.index(end, start)
    if stop <= start:
        raise ContractError(f"capture marker order is invalid: {begin}")
    return text[start:stop].strip("\n")


def key_values(section: str, label: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in section.splitlines():
        if line.count("=") < 1:
            raise ContractError(f"{label} contains a non-key/value line")
        key, value = line.split("=", 1)
        if not key or key in values:
            raise ContractError(f"{label} key is empty or duplicated")
        values[key] = value
    return values


def marker_values(line: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for token in line.split():
        if token.count("=") != 1:
            raise ContractError("completion marker grammar changed")
        key, value = token.split("=", 1)
        if not key or key in values:
            raise ContractError("completion marker key is empty or duplicated")
        values[key] = value
    return values


def classify_kernel_log(log: str) -> dict[str, int]:
    patterns = {
        "fatal": re.compile(
            r"BUG:|WARNING:|Oops:|Kernel panic|Call trace:|"
            r"Unhandled fault|Internal error"
        ),
        "i2c_timeout": re.compile(r"i2c.*timeout|timeout.*i2c", re.IGNORECASE),
        "orion_ready": re.compile(
            r"GEMINI_ORION_DIAGNOSTIC state=ready one_shot=unused"
        ),
    }
    return {
        label: sum(bool(pattern.search(line)) for line in log.splitlines())
        for label, pattern in patterns.items()
    }


def allowed_init_counts(
    classification: str,
    completed: int,
    attempted: int,
    nonzero_starts: int,
) -> set[int]:
    if classification == "complete-success":
        return {4}
    if classification != "bounded-stop-first-partial":
        raise ContractError("unknown Orion result classification")
    if nonzero_starts == attempted:
        # Probe reset, one reset per entered mode, then the started
        # transport-error reset in mtk_i2c_do_transfer().
        return {completed // 3 + 3}
    if completed % 3:
        # The current mode was reset by its first completed sample.
        return {1 + (completed + 2) // 3}
    # A first sample of a new mode may fail clock enable before the pending
    # mode reset, or fail later before START after that reset.
    base = 1 + completed // 3
    return {base, base + 1}


def validate_capture(
    data: bytes,
    config_sha256: str,
    full_validator: ModuleType,
    partial_validator: ModuleType,
) -> tuple[str, bytes, str]:
    if not data or len(data) > 8 * 1024 * 1024 or b"\0" in data:
        raise ContractError("transport output is empty, oversized, or binary")
    text = data.decode("ascii", "strict")
    if text.splitlines().count(USB_BANNER) != 1:
        raise ContractError("exact direct USB shell banner is absent or duplicated")
    if "__ORION_ABORT__" in text:
        raise ContractError("remote Orion gate aborted")

    ordered = (
        "__ORION_GATE_BEGIN__",
        "__ORION_GATE_END__",
        "__ORION_GATE_PASS__",
        "__ORION_FINAL_BEGIN__",
        "__ORION_FINAL_END__",
        "__ORION_I2C_STATUS_POST_BEGIN__",
        "__ORION_I2C_STATUS_POST_END__",
        "__ORION_POST_BEGIN__",
        "__ORION_POST_END__",
        "__ORION_AC_STATUS_POST_BEGIN__",
        "__ORION_AC_STATUS_POST_END__",
        "__ORION_DMESG_RAW_BEGIN__",
        "__ORION_DMESG_RAW_END__",
        "__ORION_COMPLETE__",
    )
    positions: list[int] = []
    for marker in ordered:
        if text.count(marker) != 1:
            raise ContractError(f"capture marker is absent or duplicated: {marker}")
        positions.append(text.index(marker))
    if positions != sorted(positions):
        raise ContractError("Orion capture marker order changed")

    gate = key_values(
        unique_section(text, "__ORION_GATE_BEGIN__", "__ORION_GATE_END__"),
        "Orion gate",
    )
    exact_gate = {
        "kernel": KERNEL_RELEASE,
        "cmdline": KERNEL_CMDLINE,
        "config_sha256": config_sha256,
        "rootfs_type": gate.get("rootfs_type", ""),
        "run_mounts": "0",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "nproc": "8",
        "handoff_state": "ready",
        "i2c6_compatible_sha256": I2C6_COMPATIBLE_SHA256,
        "i2c6_status_pre": I2C_STATUS_PRE,
        "i2c6_clients": "0",
        "i2c_chardev": "absent",
        "keyboard_devices": "1",
        "tty1": "character-device",
        "usb0_address": "42:00:15:19:82:01",
        "usb0_carrier": "1",
        "usb0_operstate": "up",
        "usb0_ipv4_exact": "1",
        "udc_state": "configured",
        "usb_service_count": "1",
        "pre_dmesg_fatal_count": "0",
        "debugfs_mount": "/run/orion-debugfs",
        "debugfs_mount_count": "1",
        "diagnostic_mode": "600:0:0",
        "diagnostic_pre": ORION_STATUS_PRE,
    }
    dynamic_gate_fields = {
        "boot_id_pre",
        "i2c6_adapter",
        "i2c6_of",
        "udc_name",
        "usb_ready_count",
        "adapter_debugfs",
        "diagnostic_path",
    }
    if set(gate) != set(exact_gate) | dynamic_gate_fields:
        raise ContractError("Orion gate field inventory changed")
    if gate.get("rootfs_type") not in {"rootfs", "ramfs", "tmpfs"}:
        raise ContractError("Orion rootfs is not volatile")
    for key, wanted in exact_gate.items():
        if gate.get(key) != wanted:
            raise ContractError(f"Orion gate {key} changed")
    if re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{12}",
        gate.get("boot_id_pre", ""),
    ) is None:
        raise ContractError("Orion boot ID is not a canonical lowercase UUID")
    if gate.get("i2c6_of") != (
        "/sys/firmware/devicetree/base/i2c@1100e000"
    ):
        raise ContractError("Orion I2C6 OF path changed")
    if not re.fullmatch(r"i2c-[0-9]+", gate.get("i2c6_adapter", "")):
        raise ContractError("Orion adapter identity is malformed")
    expected_adapter_debugfs = (
        f"/run/orion-debugfs/i2c/{gate['i2c6_adapter']}"
    )
    if gate.get("adapter_debugfs") != expected_adapter_debugfs:
        raise ContractError("Orion adapter debugfs path changed")
    if gate.get("diagnostic_path") != (
        expected_adapter_debugfs + "/orion-run-all"
    ):
        raise ContractError("Orion diagnostic path changed")
    try:
        ready_count = int(gate.get("usb_ready_count", ""), 10)
    except ValueError as exc:
        raise ContractError("Orion USB ready count is malformed") from exc
    if not 1 <= ready_count <= 64:
        raise ContractError("Orion USB ready count is out of bounds")

    final_text = unique_section(
        text, "__ORION_FINAL_BEGIN__", "__ORION_FINAL_END__"
    )
    final_data = (final_text + "\n").encode("ascii")
    classification: str
    validator_lines: list[str]
    try:
        tuples = full_validator.validate_text(final_data)
        classification = "complete-success"
        validator_lines = [
            "validation=orion-complete-success-transcript",
            "physical_transfers=9",
            "adapter_retries=1,0,1",
        ]
        for mode in co.MODE_ORDER:
            validator_lines.append(
                f"{mode}_tuple="
                + ",".join(f"{value:02x}" for value in tuples[mode])
            )
    except ValueError as full_error:
        try:
            partial = partial_validator.validate_partial(final_data)
        except ValueError as partial_error:
            raise ContractError(
                "Orion final result is neither complete nor bounded partial: "
                f"complete={full_error}; partial={partial_error}"
            ) from partial_error
        classification = "bounded-stop-first-partial"
        validator_lines = [
            "validation=orion-bounded-stop-first-partial",
            *(
                f"{key}={value:02x}"
                if key == "failing_register"
                else f"{key}={value}"
                for key, value in partial.items()
            ),
        ]

    header = full_validator.fields(
        final_text.splitlines()[0],
        full_validator.HEADER_FIELDS,
        "Orion final header",
    )
    i2c_status_post = unique_section(
        text,
        "__ORION_I2C_STATUS_POST_BEGIN__",
        "__ORION_I2C_STATUS_POST_END__",
    )
    i2c_values = marker_values(i2c_status_post)
    expected_status_fields = {
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
    if set(i2c_values) != expected_status_fields:
        raise ContractError("Orion post-run I2C status inventory changed")
    fixed_i2c_status = {
        "handoff": "ready",
        "probe_attempts": "1",
        "clock_ungated_checks": "1",
        "clock_gated_checks": "1",
        "clock_validation_failures": "0",
        "runtime_pm_link": "1",
        "clock_domains": "i2c-appm,ap-dma",
        "transfer_attempts": header["transfer_attempts"],
        "dma_starts": header["dma_starts"],
        "nonzero_starts": header["nonzero_starts"],
        "irq_count": header["irqs"],
        "suspend_checks": "0",
        "resume_checks": "0",
        "resume_failures": "0",
    }
    for key, wanted in fixed_i2c_status.items():
        if i2c_values.get(key) != wanted:
            raise ContractError(f"Orion post-run I2C status {key} changed")
    try:
        init_attempts = int(i2c_values["init_attempts"], 10)
        init_successes = int(i2c_values["init_successes"], 10)
        completed = int(header["completed"], 10)
        attempted = int(header["attempted"], 10)
        nonzero_starts = int(header["nonzero_starts"], 10)
    except ValueError as exc:
        raise ContractError("Orion reset-counter grammar changed") from exc
    if init_attempts != init_successes:
        raise ContractError("Orion reset attempts and successes differ")
    allowed_resets = allowed_init_counts(
        classification, completed, attempted, nonzero_starts
    )
    if init_attempts not in allowed_resets:
        raise ContractError("Orion reset-counter progression changed")

    post = key_values(
        unique_section(text, "__ORION_POST_BEGIN__", "__ORION_POST_END__"),
        "Orion post state",
    )
    required_post = {
        "orion_final_rc": "0",
        "i2c_status_post_rc": "0",
        "dmesg_rc": "0",
        "boot_id_post_rc": "0",
        "cpu_online_post": "0-7",
        "cpu_online_post_rc": "0",
        "cpu_offline_post": "8-9",
        "cpu_offline_post_rc": "0",
        "nproc_post": "8",
        "nproc_post_rc": "0",
        "handoff_state_post": "ready",
        "handoff_state_post_rc": "0",
        "usb_carrier_post": "1",
        "usb_carrier_post_rc": "0",
        "usb_operstate_post": "up",
        "usb_operstate_post_rc": "0",
        "udc_state_post": "configured",
        "udc_state_post_rc": "0",
        "ac_status_post_rc": "0",
    }
    for key, wanted in required_post.items():
        if post.get(key) != wanted:
            raise ContractError(f"Orion post-run state {key} changed")
    if post.get("boot_id_post") != gate["boot_id_pre"]:
        raise ContractError("Orion boot ID changed during the one-shot")
    write_rc = post.get("write_rc")
    if classification == "complete-success" and write_rc != "0":
        raise ContractError("successful Orion run had a negative debugfs write")
    if classification != "complete-success" and write_rc == "0":
        raise ContractError("partial Orion run had a successful debugfs write")
    if write_rc is None or not write_rc.isdecimal():
        raise ContractError("Orion debugfs write status is malformed")

    complete_line = next(
        line for line in text.splitlines() if line.startswith("__ORION_COMPLETE__")
    )
    complete = marker_values(
        complete_line.removeprefix("__ORION_COMPLETE__").strip()
    )
    if complete != {
        "write_rc": write_rc,
        "invocation_count": "1",
        "guard_mode": "400:0:0",
        "post_capture": "unconditional",
    }:
        raise ContractError("Orion completion marker changed")

    log = unique_section(
        text, "__ORION_DMESG_RAW_BEGIN__", "__ORION_DMESG_RAW_END__"
    )
    log_counts = classify_kernel_log(log)
    if log_counts["orion_ready"] != 1:
        raise ContractError("Orion ready kernel marker is absent or duplicated")
    if log_counts["fatal"]:
        raise ContractError("Orion raw kernel log contains a fatal warning signature")
    sanitized = "\n".join(
        [
            "validation=orion-runtime-one-shot",
            f"classification={classification}",
            f"config_sha256={config_sha256}",
            f"raw_kernel_log_sha256={digest(log.encode('ascii'))}",
            f"raw_kernel_log_fatal_count={log_counts['fatal']}",
            f"raw_kernel_log_i2c_timeout_count={log_counts['i2c_timeout']}",
            f"raw_kernel_log_orion_ready_count={log_counts['orion_ready']}",
            f"boot_id_sha256={digest(gate['boot_id_pre'].encode('ascii'))}",
            f"write_rc={write_rc}",
            "post_capture=unconditional",
            "raw_dmesg_address_lines=private-not-copied",
            *validator_lines,
            "",
        ]
    )
    return classification, final_data, sanitized


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", required=True)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()

    try:
        repository = repository_root().resolve(strict=True)
        package = args.package.resolve(strict=True)
        config_sha256 = validate_package(repository, package)
        program = build_remote_program(config_sha256)
        verify_host_link(args.interface)
        output = prepare_output(repository, args.output_dir)
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result: subprocess.CompletedProcess[bytes]
    try:
        result = run_transport(args.interface, program)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        write_private(output / TRANSCRIPT_NAME, stdout)
        write_private(output / STDERR_NAME, stderr)
        print(
            f"error: transport timed out; private raw evidence preserved in {output}",
            file=sys.stderr,
        )
        return 2

    # These raw files are always durable before parsing or invoking a result
    # validator. The transcript's dmesg section may contain DMA addresses.
    write_private(output / TRANSCRIPT_NAME, result.stdout)
    write_private(output / STDERR_NAME, result.stderr or b"\n")

    try:
        full_validator = load_module(
            pathlib.Path(__file__).with_name("validate-orion-result.py"),
            "orion_full_validator",
        )
        partial_validator = load_module(
            pathlib.Path(__file__).with_name("validate-orion-partial.py"),
            "orion_partial_validator",
        )
        classification, final_data, sanitized = validate_capture(
            result.stdout,
            config_sha256,
            full_validator,
            partial_validator,
        )
        write_private(output / RESULT_NAME, final_data)
        write_private(output / SUMMARY_NAME, sanitized.encode("ascii"))
        if result.returncode != 0:
            raise ContractError(
                f"network transport exited {result.returncode} after capture"
            )
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(
            f"error: {exc}; private raw evidence preserved in {output}",
            file=sys.stderr,
        )
        return 2

    print("validation=orion-exact-serviceability-gated-one-shot")
    print(f"classification={classification}")
    print(f"config_sha256={config_sha256}")
    print(f"raw_transcript_sha256={digest(result.stdout)}")
    stderr_data = result.stderr or b"\n"
    print(f"raw_stderr_sha256={digest(stderr_data)}")
    print(f"private_output={output}")
    print("invocation_count=1")
    print("post_capture=unconditional-even-after-negative-write")
    print("raw_dmesg=private-only-address-bearing-lines-not-sanitized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
