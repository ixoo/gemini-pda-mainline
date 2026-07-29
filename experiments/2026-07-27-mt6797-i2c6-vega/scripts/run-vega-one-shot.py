#!/usr/bin/env python3
"""Run Candidate Vega's fixed debugfs diagnostic once and preserve evidence."""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import os
import pathlib
import re
import stat
import subprocess
import sys
from types import ModuleType
from typing import NamedTuple

sys.dont_write_bytecode = True

import candidate_vega as co


HOST_MAC = "42:00:15:19:82:00"
HOST_ADDRESS = "10.15.19.1"
DEVICE_ADDRESS = "10.15.19.82"
DEVICE_PORT = 2323
USB_BANNER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
USB_PROMPT = "GEMINI-AC-USB# "
ADAPTER_TOPOLOGY_CONTRACT = "canonical-adapter-target-direct-parent-v1"
ADAPTER_TOPOLOGY_ENTRY_LIMIT = 64
ADAPTER_TOPOLOGY_BEGIN = "__VEGA_ADAPTER_TOPOLOGY_BEGIN__"
ADAPTER_TOPOLOGY_END = "__VEGA_ADAPTER_TOPOLOGY_END__"
FINAL_REVALIDATION_BEGIN = "__VEGA_FINAL_REVALIDATION_BEGIN__"
FINAL_REVALIDATION_END = "__VEGA_FINAL_REVALIDATION_END__"
FINAL_REVALIDATION_STEPS = (
    "step=topology",
    "step=diagnostic-path",
    "step=diagnostic-type",
    "step=diagnostic-mode",
    "step=diagnostic-status",
    "step=i2c6-status",
)
GATE_FIELD_ORDER = (
    "kernel",
    "cmdline",
    "config_sha256",
    "rootfs_type",
    "run_mounts",
    "boot_id_pre",
    "cpu_possible",
    "cpu_present",
    "cpu_online",
    "cpu_offline",
    "nproc",
    "handoff_state",
    "i2c6_compatible_sha256",
    "i2c6_status_pre",
    "i2c6_adapter",
    "i2c6_of",
    "i2c6_clients",
    "i2c_chardev",
    "keyboard_devices",
    "tty1",
    "usb0_address",
    "usb0_carrier",
    "usb0_operstate",
    "usb0_ipv4_exact",
    "udc_name",
    "udc_state",
    "usb_service_count",
    "usb_ready_count",
    "pre_dmesg_fatal_count",
    "debugfs_mount",
    "debugfs_mount_count",
    "adapter_debugfs",
    "diagnostic_path",
    "diagnostic_mode",
    "diagnostic_pre",
)
TOPOLOGY_REPEAT_ABORT_REASONS = frozenset(
    {
        "i2c6-platform-repeat-link",
        "i2c6-driver-repeat",
        "i2c6-platform-repeat-target",
        "i2c6-dt-repeat-target",
        "i2c-adapter-repeat-token",
        "i2c6-adapter-repeat-link",
        "i2c6-adapter-repeat-name",
        "i2c6-adapter-repeat-target",
        "i2c6-adapter-repeat-of-node",
        "i2c-adapter-repeat-entry-limit",
        "i2c-adapter-repeat-link-count",
        "i2c-adapter-repeat-name-count",
        "i2c-adapter-repeat-canonical-count",
        "i2c6-adapter-repeat-parent-count",
        "i2c6-adapter-repeat-of-node-count",
        "i2c6-adapter-repeat-count",
        "i2c-adapter-repeat-entry-drift",
        "i2c-adapter-repeat-link-drift",
        "i2c-adapter-repeat-name-drift",
        "i2c-adapter-repeat-canonical-drift",
        "i2c-adapter-repeat-parent-drift",
        "i2c-adapter-repeat-of-canonical-drift",
        "i2c-adapter-repeat-of-match-drift",
        "i2c-adapter-repeat-match-drift",
        "i2c-child-link-type",
        "i2c-child-canonical-path",
        "i2c-adapter-self-target",
        "i2c-child-entry-limit",
        "i2c-child-canonical-count",
        "i2c-adapter-self-count",
        "i2c6-client-count",
    }
)
FINAL_REVALIDATION_ABORT_STEPS = {
    **{reason: 0 for reason in TOPOLOGY_REPEAT_ABORT_REASONS},
    "adapter-debugfs-repeat-path": 1,
    "diagnostic-repeat-path": 1,
    "adapter-debugfs-repeat-type": 2,
    "diagnostic-repeat-type": 2,
    "diagnostic-repeat-mode": 3,
    "diagnostic-repeat-read": 4,
    "diagnostic-repeat-exact": 4,
    "i2c6-status-repeat-absent": 5,
    "i2c6-status-repeat-read": 5,
    "i2c6-status-repeat-exact": 5,
}
USB_PRELUDE_PREFIX = (
    "Direct USB link only: device 10.15.19.82/24, TCP port 2323.",
    "Security: unauthenticated and unencrypted root shell; trusted host only.",
    "Candidate AC status follows:",
    (
        f"{USB_BANNER} entry profile=usb-gadget-ethernet "
        "baseline=candidate-AB storage_access=none "
        "runtime_networking=usb0-static"
    ),
    f"{USB_BANNER} usb0=present wait_seconds=0",
    (
        f"{USB_BANNER} services=launched usb_network=background "
        "worker_wait_seconds=30 address=10.15.19.82/24 tcp_port=2323 "
        "local_console=unchanged watchdog_userspace=none"
    ),
    (
        f"{USB_BANNER} usb0=configured address=10.15.19.82/24 "
        "operstate=up carrier=1 udc=11271000.usb udc_state=configured"
    ),
    (
        f"{USB_BANNER} service=nc status=listening address=10.15.19.82 "
        "port=2323 shell=/bin/usb-shell authentication=none encryption=none "
        "direct_link_only=yes"
    ),
)
USB_SESSION_PAIR = (
    (
        f"{USB_BANNER} usb_shell=session-entry usb0_operstate=up "
        "usb0_carrier=1 udc=11271000.usb udc_state=configured"
    ),
    (
        f"{USB_BANNER} usb_shell=ready reboot_dispatch=validated privilege=root "
        "authentication=none encryption=none direct_link_only=yes"
    ),
)
USB_PRELUDE_SUFFIX = (
    "",
    "",
    "BusyBox v1.36.1 (Ubuntu 1:1.36.1-6ubuntu3.1) built-in shell (ash)",
    "Enter 'help' for a list of built-in commands.",
    "",
)
PACKAGE_VALIDATOR_SHA256 = (
    "ef07f12d82c4db233f30a535500e0a688bcb13228b94fea7f8618fa4a6344eee"
)
KERNEL_RELEASE = "7.1.3-gemini-vega"
KERNEL_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Vega "
    "g_ether.iSerialNumber=GEMINI_VEGA_20260727 "
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
DIAGNOSTIC_STATUS_PRE = (
    "candidate=Orion state=ready one_shot=unused run_error=0 attempted=0 "
    "completed=0 address=0x69 transfer_attempts=0 dma_starts=0 "
    "nonzero_starts=0 irqs=0 retries_before=1 retries_during=1 "
    "retries_after=1 registers=05,06,47 "
    "modes=packed-fifo,packed-dma,aux-dma"
)

PRIVATE_RELATIVE_ROOT = pathlib.Path("artifacts/runtime-captures")
TRANSCRIPT_NAME = "vega-runtime-raw.txt"
STDERR_NAME = "vega-nc-stderr-raw.txt"
RESULT_NAME = "vega-final-debugfs-raw.txt"
SUMMARY_NAME = "vega-sanitized-summary.txt"
INTERFACE = re.compile(r"[A-Za-z0-9]+")
HEX256 = re.compile(r"[0-9a-f]{64}")
CANONICAL_PATH = re.compile(
    r"/[A-Za-z0-9._:@+-]+(?:/[A-Za-z0-9._:@+-]+)*"
)
SAFE_ADAPTER_TOKEN = re.compile(r"i2c-[A-Za-z0-9_-]{1,60}")
NUMERIC_ADAPTER_NAME = re.compile(r"i2c-[0-9]+")
REMOTE_TOKEN = re.compile(r"__[A-Z0-9_]+__")
RUNTIME_TOKENS = frozenset(
    {
        "__VEGA_ABORT__",
        "__VEGA_AC_STATUS_POST_BEGIN__",
        "__VEGA_AC_STATUS_POST_END__",
        "__VEGA_ADAPTER_TOPOLOGY_BEGIN__",
        "__VEGA_ADAPTER_TOPOLOGY_END__",
        "__VEGA_COMPLETE__",
        "__VEGA_DMESG_RAW_BEGIN__",
        "__VEGA_DMESG_RAW_END__",
        "__VEGA_FINAL_REVALIDATION_BEGIN__",
        "__VEGA_FINAL_REVALIDATION_END__",
        "__VEGA_FINAL_BEGIN__",
        "__VEGA_FINAL_END__",
        "__VEGA_GATE_BEGIN__",
        "__VEGA_GATE_END__",
        "__VEGA_GATE_PASS__",
        "__VEGA_I2C_STATUS_POST_BEGIN__",
        "__VEGA_I2C_STATUS_POST_END__",
        "__VEGA_POST_BEGIN__",
        "__VEGA_POST_END__",
    }
)
SUBSTITUTION_TOKEN_COUNTS = {
    "__VEGA_KERNEL__": 3,
    "__VEGA_CMDLINE__": 1,
    "__VEGA_CONFIG_SHA256__": 1,
    "__VEGA_I2C6_COMPATIBLE_SHA256__": 2,
    "__VEGA_I2C_STATUS_PRE__": 2,
    "__VEGA_STATUS_PRE__": 2,
}
RUNTIME_TOKEN_COUNTS = {
    token: 4 if token == "__VEGA_ABORT__" else 1
    for token in RUNTIME_TOKENS
}


REMOTE_TEMPLATE = r"""PS1=; PS2=; export PS1 PS2
set -eu
umask 077
LC_ALL=C
LANG=C
export LC_ALL LANG

guard_path=/run/vega-run-all.invoked
debugfs_root=/run/vega-debugfs
handoff=/sys/bus/platform/devices/11015000.dvfsp-handoff
i2c6=/sys/bus/platform/devices/1100e000.i2c
dt_i2c6=/sys/firmware/devicetree/base/i2c@1100e000
debugfs_mounted=no
abort_emitted=no
completion_emitted=no
abort_leading_newline=yes

cleanup() {
	if [ "$debugfs_mounted" = yes ]; then
		/bin/busybox umount "$debugfs_root" 2>/dev/null || true
	fi
	/bin/busybox rmdir "$debugfs_root" 2>/dev/null || true
}
on_exit() {
	exit_rc=$?
	trap - EXIT
	cleanup
	if [ "$abort_emitted" = no ] &&
	   [ "$completion_emitted" = no ]; then
		if [ "$abort_leading_newline" = yes ]; then
			printf '\n__VEGA_ABORT__ reason=unexpected-shell-exit rc=%s\n' \
				"$exit_rc"
		else
			printf '__VEGA_ABORT__ reason=unexpected-shell-exit rc=%s\n' \
				"$exit_rc"
		fi
	fi
	exit "$exit_rc"
}
abort() {
	abort_emitted=yes
	if [ "$abort_leading_newline" = yes ]; then
		printf '\n__VEGA_ABORT__ reason=%s\n' "$1"
	else
		printf '__VEGA_ABORT__ reason=%s\n' "$1"
	fi
	exit 90
}
require_equal() {
	[ "$1" = "$2" ] || abort "$3"
}
file_sha256() {
	/bin/busybox sha256sum "$1" | /bin/busybox awk '{ print $1 }'
}
adapter_token_safe() {
	[ "${#1}" -le 64 ] || return 1
	case "$1" in
	i2c-?*)
		case "$1" in
		*[!A-Za-z0-9_-]*) return 1 ;;
		esac
		;;
	*) return 1 ;;
	esac
}
on_signal() {
	trap - HUP INT TERM PIPE
	exit 91
}
trap on_exit EXIT
trap on_signal HUP INT TERM PIPE

require_equal "$(/bin/busybox id -u)" 0 not-root
require_equal "$(/bin/busybox uname -r)" "__VEGA_KERNEL__" kernel-identity
cmdline=$(/bin/busybox cat /proc/cmdline)
require_equal "$cmdline" "__VEGA_CMDLINE__" cmdline-identity
config_sha256=$(
	/bin/busybox zcat /proc/config.gz |
		/bin/busybox sha256sum |
		/bin/busybox awk '{ print $1 }'
)
require_equal "$config_sha256" "__VEGA_CONFIG_SHA256__" config-identity

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
	"__VEGA_I2C6_COMPATIBLE_SHA256__" i2c6-compatible
[ -L "$i2c6" ] || abort i2c6-platform-link-type
[ -d "$i2c6" ] || abort i2c6-platform-device-absent
[ -L "$i2c6/driver" ] || abort i2c6-driver-unbound
[ -r "$i2c6/handoff_status" ] || abort i2c6-status-absent
if ! i2c_status_pre=$(/bin/busybox cat "$i2c6/handoff_status"); then
	abort i2c6-status-read
fi
require_equal "$i2c_status_pre" "__VEGA_I2C_STATUS_PRE__" i2c6-pre-exact

i2c6_target=$(
	/bin/busybox readlink -f "$i2c6" 2>/dev/null
) || abort i2c6-platform-canonical-path
[ -n "$i2c6_target" ] &&
[ "${i2c6_target#/}" != "$i2c6_target" ] &&
[ "$i2c6_target" != / ] &&
[ -d "$i2c6_target" ] ||
	abort i2c6-platform-canonical-path
dt_i2c6_target=$(
	/bin/busybox readlink -f "$dt_i2c6" 2>/dev/null
) || abort i2c6-dt-canonical-path
[ -n "$dt_i2c6_target" ] &&
[ "${dt_i2c6_target#/}" != "$dt_i2c6_target" ] &&
[ "$dt_i2c6_target" != / ] &&
[ -d "$dt_i2c6_target" ] ||
	abort i2c6-dt-canonical-path

# Keep unsafe basenames out of the line-oriented topology frame. The
# inventory repeats this bounded check to close the preflight race.
preflight_adapter_count=0
for preflight_adapter in /sys/bus/i2c/devices/i2c-*; do
	if [ "$preflight_adapter" = '/sys/bus/i2c/devices/i2c-*' ] &&
	   [ ! -e "$preflight_adapter" ] &&
	   [ ! -L "$preflight_adapter" ]; then
		break
	fi
	if [ "$preflight_adapter_count" -ge 64 ]; then
		break
	fi
	preflight_adapter_count=$((preflight_adapter_count + 1))
	preflight_adapter_name=${preflight_adapter##*/}
	adapter_token_safe "$preflight_adapter_name" ||
		abort i2c-adapter-token
done

adapter_count=0
adapter_name=
adapter_link=
adapter_target_selected=
adapter_of_target_selected=
adapter_entry_count=0
adapter_link_count=0
adapter_name_count=0
adapter_canonical_count=0
adapter_parent_match_count=0
adapter_of_canonical_count=0
adapter_of_match_count=0
adapter_overflow=0
printf '\n__VEGA_ADAPTER_TOPOLOGY_BEGIN__\n'
printf 'contract=canonical-adapter-target-direct-parent-v1\n'
printf 'kernel=%s\n' "__VEGA_KERNEL__"
printf 'config_sha256=%s\n' "$config_sha256"
printf 'boot_id=%s\n' "$boot_id_pre"
printf 'platform_target=%s\n' "$i2c6_target"
printf 'dt_target=%s\n' "$dt_i2c6_target"
printf 'entry_limit=64\n'
for adapter in /sys/bus/i2c/devices/i2c-*; do
	if [ "$adapter" = '/sys/bus/i2c/devices/i2c-*' ] &&
	   [ ! -e "$adapter" ] && [ ! -L "$adapter" ]; then
		break
	fi
	if [ "$adapter_entry_count" -ge 64 ]; then
		adapter_overflow=1
		break
	fi
	adapter_entry_count=$((adapter_entry_count + 1))
	entry_adapter=${adapter##*/}
	adapter_token_safe "$entry_adapter" || abort i2c-adapter-token
	entry_link=0
	entry_name_valid=0
	entry_canonical=0
	entry_target=-
	entry_parent=-
	entry_parent_match=0
	entry_of_canonical=0
	entry_of_target=-
	entry_of_match=0
	entry_match=0
	if [ -L "$adapter" ]; then
		entry_link=1
		adapter_link_count=$((adapter_link_count + 1))
	fi
	entry_number=${entry_adapter#i2c-}
	case "$entry_number" in
	''|*[!0-9]*) ;;
	*)
		entry_name_valid=1
		adapter_name_count=$((adapter_name_count + 1))
		;;
	esac
	if [ "$entry_link" -eq 1 ] && [ "$entry_name_valid" -eq 1 ]; then
		adapter_target=$(
			/bin/busybox readlink -f "$adapter" 2>/dev/null ||
			true
		)
		if [ -n "$adapter_target" ] &&
		   [ "${adapter_target#/}" != "$adapter_target" ] &&
		   [ "$adapter_target" != / ]; then
			adapter_parent=${adapter_target%/*}
			if [ -n "$adapter_parent" ] &&
			   [ -d "$adapter_target" ] &&
			   [ -d "$adapter_parent" ]; then
				entry_canonical=1
				entry_target=$adapter_target
				entry_parent=$adapter_parent
				adapter_canonical_count=$((adapter_canonical_count + 1))
			fi
		fi
	fi
	if [ "$entry_canonical" -eq 1 ]; then
		if [ "$entry_parent" = "$i2c6_target" ]; then
			entry_parent_match=1
			adapter_parent_match_count=$((adapter_parent_match_count + 1))
		fi
		if [ -L "$adapter/of_node" ]; then
			adapter_of_target=$(
				/bin/busybox readlink -f "$adapter/of_node" \
					2>/dev/null ||
				true
			)
			if [ -n "$adapter_of_target" ] &&
			   [ "${adapter_of_target#/}" != "$adapter_of_target" ] &&
			   [ "$adapter_of_target" != / ] &&
			   [ -d "$adapter_of_target" ]; then
				entry_of_canonical=1
				entry_of_target=$adapter_of_target
				adapter_of_canonical_count=$((adapter_of_canonical_count + 1))
				if [ "$entry_of_target" = "$dt_i2c6_target" ]; then
					entry_of_match=1
					adapter_of_match_count=$((adapter_of_match_count + 1))
				fi
			fi
		fi
	fi
	if [ "$entry_parent_match" -eq 1 ] &&
	   [ "$entry_of_match" -eq 1 ]; then
		entry_match=1
		adapter_count=$((adapter_count + 1))
		adapter_name=$entry_adapter
		adapter_link=$adapter
		adapter_target_selected=$entry_target
		adapter_of_target_selected=$entry_of_target
	fi
	printf 'entry index=%s adapter=%s link=%s name_valid=%s canonical=%s ' \
		"$adapter_entry_count" "$entry_adapter" "$entry_link" \
		"$entry_name_valid" "$entry_canonical"
	printf 'target=%s parent=%s parent_match=%s of_canonical=%s ' \
		"$entry_target" "$entry_parent" "$entry_parent_match" \
		"$entry_of_canonical"
	printf 'of_target=%s of_match=%s match=%s\n' \
		"$entry_of_target" "$entry_of_match" "$entry_match"
done
printf 'summary entry_count=%s link_count=%s name_count=%s ' \
	"$adapter_entry_count" "$adapter_link_count" "$adapter_name_count"
printf 'canonical_count=%s parent_match_count=%s ' \
	"$adapter_canonical_count" "$adapter_parent_match_count"
printf 'of_canonical_count=%s of_match_count=%s match_count=%s overflow=%s\n' \
	"$adapter_of_canonical_count" "$adapter_of_match_count" \
	"$adapter_count" "$adapter_overflow"
printf '__VEGA_ADAPTER_TOPOLOGY_END__'
require_equal "$adapter_overflow" 0 i2c-adapter-entry-limit
require_equal "$adapter_link_count" "$adapter_entry_count" \
	i2c-adapter-link-type
require_equal "$adapter_name_count" "$adapter_entry_count" \
	i2c-adapter-name
require_equal "$adapter_canonical_count" "$adapter_entry_count" \
	i2c-adapter-canonical-path
require_equal "$adapter_parent_match_count" 1 \
	i2c6-adapter-parent-count
require_equal "$adapter_of_match_count" 1 \
	i2c6-adapter-of-node-count
require_equal "$adapter_count" 1 i2c6-adapter-count

scan_selected_children() {
	child_entry_count=0
	child_canonical_count=0
	child_self_count=0
	child_overflow=0
	client_count=0
	for child in /sys/bus/i2c/devices/*; do
		if [ "$child" = '/sys/bus/i2c/devices/*' ] &&
		   [ ! -e "$child" ] && [ ! -L "$child" ]; then
			break
		fi
		if [ "$child_entry_count" -ge 256 ]; then
			child_overflow=1
			break
		fi
		child_entry_count=$((child_entry_count + 1))
		[ -L "$child" ] || abort i2c-child-link-type
		child_target=$(
			/bin/busybox readlink -f "$child" 2>/dev/null ||
			true
		)
		[ -n "$child_target" ] &&
		[ "${child_target#/}" != "$child_target" ] &&
		[ "$child_target" != / ] &&
		[ -d "$child_target" ] ||
			abort i2c-child-canonical-path
		child_parent=${child_target%/*}
		[ -n "$child_parent" ] && [ -d "$child_parent" ] ||
			abort i2c-child-canonical-path
		child_canonical_count=$((child_canonical_count + 1))
		if [ "$child" = "$adapter_link" ]; then
			require_equal "$child_target" "$adapter_target_selected" \
				i2c-adapter-self-target
			child_self_count=$((child_self_count + 1))
		elif [ "$child_parent" = "$adapter_target_selected" ]; then
			client_count=$((client_count + 1))
		fi
	done
	require_equal "$child_overflow" 0 i2c-child-entry-limit
	require_equal "$child_canonical_count" "$child_entry_count" \
		i2c-child-canonical-count
	require_equal "$child_self_count" 1 i2c-adapter-self-count
	require_equal "$client_count" 0 i2c6-client-count
}
scan_selected_children

verify_selected_identity() {
	[ -L "$i2c6" ] || abort i2c6-platform-repeat-link
	[ -L "$i2c6/driver" ] || abort i2c6-driver-repeat
	repeat_i2c6_target=$(
		/bin/busybox readlink -f "$i2c6" 2>/dev/null ||
		true
	)
	require_equal "$repeat_i2c6_target" "$i2c6_target" \
		i2c6-platform-repeat-target
	repeat_dt_i2c6_target=$(
		/bin/busybox readlink -f "$dt_i2c6" 2>/dev/null ||
		true
	)
	require_equal "$repeat_dt_i2c6_target" "$dt_i2c6_target" \
		i2c6-dt-repeat-target

	repeat_entry_count=0
	repeat_link_count=0
	repeat_name_count=0
	repeat_canonical_count=0
	repeat_parent_match_count=0
	repeat_of_canonical_count=0
	repeat_of_match_count=0
	repeat_match_count=0
	repeat_overflow=0
	for repeat_adapter in /sys/bus/i2c/devices/i2c-*; do
		if [ "$repeat_adapter" = '/sys/bus/i2c/devices/i2c-*' ] &&
		   [ ! -e "$repeat_adapter" ] &&
		   [ ! -L "$repeat_adapter" ]; then
			break
		fi
		if [ "$repeat_entry_count" -ge 64 ]; then
			repeat_overflow=1
			break
		fi
		repeat_entry_count=$((repeat_entry_count + 1))
		repeat_adapter_name=${repeat_adapter##*/}
		adapter_token_safe "$repeat_adapter_name" ||
			abort i2c-adapter-repeat-token

		repeat_entry_link=0
		repeat_entry_name_valid=0
		repeat_entry_canonical=0
		repeat_entry_parent_match=0
		repeat_entry_of_match=0
		if [ -L "$repeat_adapter" ]; then
			repeat_entry_link=1
			repeat_link_count=$((repeat_link_count + 1))
		fi
		repeat_adapter_number=${repeat_adapter_name#i2c-}
		case "$repeat_adapter_number" in
		''|*[!0-9]*) ;;
		*)
			repeat_entry_name_valid=1
			repeat_name_count=$((repeat_name_count + 1))
			;;
		esac
		repeat_adapter_target=
		repeat_adapter_parent=
		repeat_adapter_of_target=
		if [ "$repeat_entry_link" -eq 1 ] &&
		   [ "$repeat_entry_name_valid" -eq 1 ]; then
			repeat_adapter_target=$(
				/bin/busybox readlink -f "$repeat_adapter" \
					2>/dev/null ||
				true
			)
			if [ -n "$repeat_adapter_target" ] &&
			   [ "${repeat_adapter_target#/}" != \
			     "$repeat_adapter_target" ] &&
			   [ "$repeat_adapter_target" != / ]; then
				repeat_adapter_parent=${repeat_adapter_target%/*}
				if [ -n "$repeat_adapter_parent" ] &&
				   [ -d "$repeat_adapter_target" ] &&
				   [ -d "$repeat_adapter_parent" ]; then
					repeat_entry_canonical=1
					repeat_canonical_count=$((repeat_canonical_count + 1))
				fi
			fi
		fi
		if [ "$repeat_entry_canonical" -eq 1 ]; then
			if [ "$repeat_adapter_parent" = \
			     "$repeat_i2c6_target" ]; then
				repeat_entry_parent_match=1
				repeat_parent_match_count=$((repeat_parent_match_count + 1))
			fi
			if [ -L "$repeat_adapter/of_node" ]; then
				repeat_adapter_of_target=$(
					/bin/busybox readlink -f \
						"$repeat_adapter/of_node" \
						2>/dev/null ||
					true
				)
				if [ -n "$repeat_adapter_of_target" ] &&
				   [ "${repeat_adapter_of_target#/}" != \
				     "$repeat_adapter_of_target" ] &&
				   [ "$repeat_adapter_of_target" != / ] &&
				   [ -d "$repeat_adapter_of_target" ]; then
					repeat_of_canonical_count=$((repeat_of_canonical_count + 1))
					if [ "$repeat_adapter_of_target" = \
					     "$repeat_dt_i2c6_target" ]; then
						repeat_entry_of_match=1
						repeat_of_match_count=$((repeat_of_match_count + 1))
					fi
				fi
			fi
		fi
		if [ "$repeat_entry_parent_match" -eq 1 ] &&
		   [ "$repeat_entry_of_match" -eq 1 ]; then
			repeat_match_count=$((repeat_match_count + 1))
			require_equal "$repeat_adapter" "$adapter_link" \
				i2c6-adapter-repeat-link
			require_equal "$repeat_adapter_name" "$adapter_name" \
				i2c6-adapter-repeat-name
			require_equal "$repeat_adapter_target" \
				"$adapter_target_selected" \
				i2c6-adapter-repeat-target
			require_equal "$repeat_adapter_of_target" \
				"$adapter_of_target_selected" \
				i2c6-adapter-repeat-of-node
		fi
	done
	require_equal "$repeat_overflow" 0 i2c-adapter-repeat-entry-limit
	require_equal "$repeat_link_count" "$repeat_entry_count" \
		i2c-adapter-repeat-link-count
	require_equal "$repeat_name_count" "$repeat_entry_count" \
		i2c-adapter-repeat-name-count
	require_equal "$repeat_canonical_count" "$repeat_entry_count" \
		i2c-adapter-repeat-canonical-count
	require_equal "$repeat_parent_match_count" 1 \
		i2c6-adapter-repeat-parent-count
	require_equal "$repeat_of_match_count" 1 \
		i2c6-adapter-repeat-of-node-count
	require_equal "$repeat_match_count" 1 i2c6-adapter-repeat-count
	require_equal "$repeat_entry_count" "$adapter_entry_count" \
		i2c-adapter-repeat-entry-drift
	require_equal "$repeat_link_count" "$adapter_link_count" \
		i2c-adapter-repeat-link-drift
	require_equal "$repeat_name_count" "$adapter_name_count" \
		i2c-adapter-repeat-name-drift
	require_equal "$repeat_canonical_count" "$adapter_canonical_count" \
		i2c-adapter-repeat-canonical-drift
	require_equal "$repeat_parent_match_count" \
		"$adapter_parent_match_count" \
		i2c-adapter-repeat-parent-drift
	require_equal "$repeat_of_canonical_count" \
		"$adapter_of_canonical_count" \
		i2c-adapter-repeat-of-canonical-drift
	require_equal "$repeat_of_match_count" "$adapter_of_match_count" \
		i2c-adapter-repeat-of-match-drift
	require_equal "$repeat_match_count" "$adapter_count" \
		i2c-adapter-repeat-match-drift
	scan_selected_children
}

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
vega_status_pre=$(/bin/busybox cat "$diag")
require_equal "$vega_status_pre" "__VEGA_STATUS_PRE__" diagnostic-pre-exact

printf '\n__VEGA_GATE_BEGIN__\n'
abort_leading_newline=no
printf 'kernel=%s\ncmdline=%s\nconfig_sha256=%s\n' \
	"__VEGA_KERNEL__" "$cmdline" "$config_sha256"
printf 'rootfs_type=%s\nrun_mounts=%s\nboot_id_pre=%s\n' \
	"$rootfs_type" "$run_mounts" "$boot_id_pre"
printf 'cpu_possible=0-9\ncpu_present=0-9\ncpu_online=0-7\n'
printf 'cpu_offline=8-9\nnproc=8\nhandoff_state=ready\n'
printf 'i2c6_compatible_sha256=%s\n' \
	"__VEGA_I2C6_COMPATIBLE_SHA256__"
printf 'i2c6_status_pre=%s\ni2c6_adapter=%s\ni2c6_of=%s\n' \
	"$i2c_status_pre" "$adapter_name" "$dt_i2c6"
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
printf 'diagnostic_pre=%s\n' "$vega_status_pre"

printf '__VEGA_FINAL_REVALIDATION_BEGIN__\n'
verify_selected_identity
printf 'step=topology\n'
require_equal "$adapter_debugfs" \
	"$debugfs_root/i2c/$adapter_name" adapter-debugfs-repeat-path
require_equal "$diag" \
	"$debugfs_root/i2c/$adapter_name/orion-run-all" diagnostic-repeat-path
printf 'step=diagnostic-path\n'
[ -d "$adapter_debugfs" ] && [ ! -L "$adapter_debugfs" ] ||
	abort adapter-debugfs-repeat-type
[ -f "$diag" ] && [ ! -L "$diag" ] || abort diagnostic-repeat-type
printf 'step=diagnostic-type\n'
require_equal "$(/bin/busybox stat -c '%a:%u:%g' "$diag")" \
	600:0:0 diagnostic-repeat-mode
printf 'step=diagnostic-mode\n'
vega_status_repeat=$(
	/bin/busybox cat "$diag" 2>/dev/null
) || abort diagnostic-repeat-read
require_equal "$vega_status_repeat" "__VEGA_STATUS_PRE__" \
	diagnostic-repeat-exact
printf 'step=diagnostic-status\n'
[ -r "$i2c6/handoff_status" ] || abort i2c6-status-repeat-absent
i2c_status_repeat=$(
	/bin/busybox cat "$i2c6/handoff_status" 2>/dev/null
) || abort i2c6-status-repeat-read
require_equal "$i2c_status_repeat" "__VEGA_I2C_STATUS_PRE__" \
	i2c6-status-repeat-exact
printf 'step=i2c6-status\n'
printf '__VEGA_FINAL_REVALIDATION_END__\n'

printf '__VEGA_GATE_END__\n__VEGA_GATE_PASS__\n'
( set -C; : >"$guard_path" ) 2>/dev/null || abort invocation-guard
/bin/busybox chmod 0400 "$guard_path"

# This is the sole diagnostic write. From this point onward set -e remains
# disabled so a negative debugfs write cannot skip any post-run capture.
set +e
printf 'run\n' >"$diag"
write_rc=$?
vega_final=$(/bin/busybox cat "$diag" 2>&1)
vega_final_rc=$?
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

printf '__VEGA_FINAL_BEGIN__\n%s\n__VEGA_FINAL_END__\n' "$vega_final"
printf '__VEGA_I2C_STATUS_POST_BEGIN__\n%s\n' "$i2c_status_post"
printf '__VEGA_I2C_STATUS_POST_END__\n'
printf '__VEGA_POST_BEGIN__\n'
printf 'write_rc=%s\nvega_final_rc=%s\ni2c_status_post_rc=%s\n' \
	"$write_rc" "$vega_final_rc" "$i2c_status_post_rc"
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
printf '__VEGA_POST_END__\n'
printf '__VEGA_AC_STATUS_POST_BEGIN__\n%s\n' "$ac_status_post"
printf '__VEGA_AC_STATUS_POST_END__\n'

# Keep this complete log only in the private raw transcript. In particular,
# timeout-path i2c_dump_register() lines can contain DMA memory addresses.
printf '__VEGA_DMESG_RAW_BEGIN__\n%s\n__VEGA_DMESG_RAW_END__\n' \
	"$kernel_log"
completion_emitted=yes
printf '__VEGA_COMPLETE__ write_rc=%s invocation_count=1 guard_mode=%s post_capture=unconditional\n' \
	"$write_rc" "$(/bin/busybox stat -c '%a:%u:%g' "$guard_path")"
exit 0
"""


class ContractError(ValueError):
    """A local or captured runtime contract did not match exactly."""


class AdapterTopology(NamedTuple):
    kernel: str
    config_sha256: str
    boot_id: str
    platform_target: str
    dt_target: str
    entry_count: int
    link_count: int
    name_count: int
    canonical_count: int
    parent_match_count: int
    of_canonical_count: int
    of_match_count: int
    match_count: int
    overflow: int
    matching_adapters: tuple[str, ...]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def expected_usb_envelope(session_count: int) -> tuple[str, ...]:
    if not 1 <= session_count <= 64:
        raise ContractError("USB service prelude session count is out of bounds")
    return (
        USB_BANNER,
        *USB_PRELUDE_PREFIX,
        *(USB_SESSION_PAIR * session_count),
        *USB_PRELUDE_SUFFIX,
        USB_PROMPT,
    )


def load_source_pinned_module(
    path: pathlib.Path,
    wanted_sha256: str,
    label: str,
    name: str,
) -> ModuleType:
    if HEX256.fullmatch(wanted_sha256) is None:
        raise ContractError(f"source pin is malformed: {label}")
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ContractError(f"source-pinned input is unsafe: {label}")
    data = path.read_bytes()
    if digest(data) != wanted_sha256:
        raise ContractError(f"source-pinned input changed: {label}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {label}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        exec(compile(data, os.fspath(path), "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def validate_package(repository: pathlib.Path, package: pathlib.Path) -> str:
    validator = load_source_pinned_module(
        pathlib.Path(__file__).with_name("validate-package-vega.py"),
        PACKAGE_VALIDATOR_SHA256,
        "Vega package validator",
        "vega_package_validator",
    )
    validator.validate(repository, package)
    config = validator.regular(package / "kernel.config", "kernel config")
    return digest(config)


def load_orion_result_validator(
    repository: pathlib.Path,
    filename: str,
    wanted_sha256: str,
    module_name: str,
) -> ModuleType:
    path = (
        repository
        / "experiments/2026-07-27-mt6797-i2c6-orion/scripts"
        / filename
    )
    sys.path.insert(0, os.fspath(path.parent))
    try:
        return load_source_pinned_module(
            path,
            wanted_sha256,
            f"Orion validator {filename}",
            module_name,
        )
    finally:
        del sys.path[0]


def require_canonical_adapter_mapping(program: str) -> None:
    required = (
        "LC_ALL=C\nLANG=C\nexport LC_ALL LANG",
        "adapter_token_safe() {",
        '[ "${#1}" -le 64 ] || return 1',
        '*[!A-Za-z0-9_-]*) return 1 ;;',
        '[ -L "$i2c6" ] || abort i2c6-platform-link-type',
        '[ -d "$i2c6" ] || abort i2c6-platform-device-absent',
        '[ -L "$i2c6/driver" ] || abort i2c6-driver-unbound',
        'i2c6_target=$(\n'
        '\t/bin/busybox readlink -f "$i2c6" 2>/dev/null\n'
        ') || abort i2c6-platform-canonical-path',
        '[ "${i2c6_target#/}" != "$i2c6_target" ]',
        'adapter_token_safe "$preflight_adapter_name" ||\n'
        '\t\tabort i2c-adapter-token',
        "printf '\\n__VEGA_ADAPTER_TOPOLOGY_BEGIN__\\n'",
        "printf 'contract=canonical-adapter-target-direct-parent-v1\\n'",
        "printf 'kernel=%s\\n'",
        "printf 'config_sha256=%s\\n'",
        "printf 'boot_id=%s\\n'",
        "printf 'entry_limit=64\\n'",
        'adapter_token_safe "$entry_adapter" || abort i2c-adapter-token',
        "[ -L \"$adapter\" ]",
        '/bin/busybox readlink -f "$adapter" 2>/dev/null',
        '[ "${adapter_target#/}" != "$adapter_target" ]',
        '[ "$adapter_target" != / ]',
        'adapter_parent=${adapter_target%/*}',
        'if [ "$entry_parent" = "$i2c6_target" ]; then',
        '[ -L "$adapter/of_node" ]',
        '/bin/busybox readlink -f "$adapter/of_node"',
        'if [ "$entry_of_target" = "$dt_i2c6_target" ]; then',
        'if [ "$entry_parent_match" -eq 1 ] &&\n'
        '\t   [ "$entry_of_match" -eq 1 ]; then',
        "printf 'summary entry_count=%s link_count=%s name_count=%s '",
        "printf 'canonical_count=%s parent_match_count=%s '",
        "printf 'of_canonical_count=%s of_match_count=%s "
        "match_count=%s overflow=%s\\n'",
        "printf '__VEGA_ADAPTER_TOPOLOGY_END__'",
        'require_equal "$adapter_overflow" 0 i2c-adapter-entry-limit',
        'require_equal "$adapter_link_count" "$adapter_entry_count"',
        'require_equal "$adapter_name_count" "$adapter_entry_count"',
        'require_equal "$adapter_canonical_count" "$adapter_entry_count"',
        'require_equal "$adapter_count" 1 i2c6-adapter-count',
        "scan_selected_children() {",
        'elif [ "$child_parent" = "$adapter_target_selected" ]; then',
        "verify_selected_identity() {",
        'adapter_token_safe "$repeat_adapter_name" ||\n'
        '\t\t\tabort i2c-adapter-repeat-token',
        'if [ "$repeat_adapter_parent" = \\\n'
        '\t\t\t     "$repeat_i2c6_target" ]; then',
        '\t\t\tfi\n\t\t\tif [ -L "$repeat_adapter/of_node" ]; then',
        'if [ "$repeat_adapter_of_target" = \\\n'
        '\t\t\t\t\t     "$repeat_dt_i2c6_target" ]; then',
        'if [ "$repeat_entry_parent_match" -eq 1 ] &&\n'
        '\t\t   [ "$repeat_entry_of_match" -eq 1 ]; then',
        'require_equal "$repeat_adapter_target"',
        'require_equal "$repeat_adapter_of_target"',
        'require_equal "$repeat_of_match_count" 1',
        'require_equal "$repeat_of_canonical_count" \\\n'
        '\t\t"$adapter_of_canonical_count"',
        'require_equal "$repeat_of_match_count" "$adapter_of_match_count"',
        '"$i2c_status_pre" "$adapter_name" "$dt_i2c6"',
    )
    forbidden = (
        '"$adapter/device"',
        '"$adapter/device/of_node"',
        'adapter_number=${adapter_name#i2c-}',
        '/sys/bus/i2c/devices/"$adapter_number"-*',
        "*/i2c@1100e000",
        "${adapter_parent##*/}",
        "${adapter_target##*/}",
        'case "$target" in',
        "adapter_of=",
    )
    if any(program.count(fragment) != 1 for fragment in required):
        raise ContractError("canonical I2C6 adapter mapping contract changed")
    if any(fragment in program for fragment in forbidden):
        raise ContractError("I2C6 adapter mapping regained a string heuristic")
    final_prewrite = r"""printf 'diagnostic_pre=%s\n' "$vega_status_pre"

printf '__VEGA_FINAL_REVALIDATION_BEGIN__\n'
verify_selected_identity
printf 'step=topology\n'
require_equal "$adapter_debugfs" \
	"$debugfs_root/i2c/$adapter_name" adapter-debugfs-repeat-path
require_equal "$diag" \
	"$debugfs_root/i2c/$adapter_name/orion-run-all" diagnostic-repeat-path
printf 'step=diagnostic-path\n'
[ -d "$adapter_debugfs" ] && [ ! -L "$adapter_debugfs" ] ||
	abort adapter-debugfs-repeat-type
[ -f "$diag" ] && [ ! -L "$diag" ] || abort diagnostic-repeat-type
printf 'step=diagnostic-type\n'
require_equal "$(/bin/busybox stat -c '%a:%u:%g' "$diag")" \
	600:0:0 diagnostic-repeat-mode
printf 'step=diagnostic-mode\n'
vega_status_repeat=$(
	/bin/busybox cat "$diag" 2>/dev/null
) || abort diagnostic-repeat-read
require_equal "$vega_status_repeat" "__VEGA_STATUS_PRE__" \
	diagnostic-repeat-exact
printf 'step=diagnostic-status\n'
[ -r "$i2c6/handoff_status" ] || abort i2c6-status-repeat-absent
i2c_status_repeat=$(
	/bin/busybox cat "$i2c6/handoff_status" 2>/dev/null
) || abort i2c6-status-repeat-read
require_equal "$i2c_status_repeat" "__VEGA_I2C_STATUS_PRE__" \
	i2c6-status-repeat-exact
printf 'step=i2c6-status\n'
printf '__VEGA_FINAL_REVALIDATION_END__\n'

printf '__VEGA_GATE_END__\n__VEGA_GATE_PASS__\n'
( set -C; : >"$guard_path" ) 2>/dev/null || abort invocation-guard
/bin/busybox chmod 0400 "$guard_path"

# This is the sole diagnostic write. From this point onward set -e remains
# disabled so a negative debugfs write cannot skip any post-run capture.
set +e
printf 'run\n' >"$diag"
write_rc=$?"""
    if program.count(final_prewrite) != 1:
        raise ContractError(
            "Vega final identity revalidation or write adjacency changed"
        )
    if program.count("scan_selected_children\n") != 2:
        raise ContractError("I2C6 childless identity is not checked twice")
    if program.count("\nverify_selected_identity\n") != 1:
        raise ContractError("I2C6 selected identity is not rechecked once")
    positions = tuple(program.index(fragment) for fragment in required)
    if positions != tuple(sorted(positions)):
        raise ContractError("canonical I2C6 adapter mapping order changed")


def build_remote_program(config_sha256: str) -> bytes:
    if HEX256.fullmatch(config_sha256) is None:
        raise ContractError("Vega configuration hash is malformed")
    replacements = {
        "__VEGA_KERNEL__": KERNEL_RELEASE,
        "__VEGA_CMDLINE__": KERNEL_CMDLINE,
        "__VEGA_CONFIG_SHA256__": config_sha256,
        "__VEGA_I2C6_COMPATIBLE_SHA256__": I2C6_COMPATIBLE_SHA256,
        "__VEGA_I2C_STATUS_PRE__": I2C_STATUS_PRE,
        "__VEGA_STATUS_PRE__": DIAGNOSTIC_STATUS_PRE,
    }
    program = REMOTE_TEMPLATE
    require_canonical_adapter_mapping(program)
    expected_counts = SUBSTITUTION_TOKEN_COUNTS | RUNTIME_TOKEN_COUNTS
    if set(replacements) != set(SUBSTITUTION_TOKEN_COUNTS):
        raise ContractError("remote replacement inventory changed")
    if collections.Counter(REMOTE_TOKEN.findall(program)) != expected_counts:
        raise ContractError("remote template token inventory changed")
    for token, value in replacements.items():
        if program.count(token) < 1:
            raise ContractError(f"remote template lost token {token}")
        program = program.replace(token, value)
    if collections.Counter(REMOTE_TOKEN.findall(program)) != (
        RUNTIME_TOKEN_COUNTS
    ):
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


def exact_line_section(
    text: str,
    begin: str,
    end: str,
    label: str,
) -> str:
    if text.count(begin) != 1 or text.count(end) != 1:
        raise ContractError(f"{label} marker is absent or duplicated")
    begin_offset = text.index(begin)
    content_start = begin_offset + len(begin)
    end_offset = text.index(end, content_start)
    if (
        end_offset <= content_start + 1
        or text[content_start : content_start + 1] != "\n"
        or text[end_offset - 1 : end_offset] != "\n"
    ):
        raise ContractError(f"{label} boundary adjacency changed")
    return text[content_start + 1 : end_offset - 1]


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
        "vega_ready": re.compile(
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
        raise ContractError("unknown Vega result classification")
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


def canonical_parent(path: str, label: str) -> str:
    if CANONICAL_PATH.fullmatch(path) is None or any(
        component in {".", ".."} for component in path.split("/")[1:]
    ):
        raise ContractError(f"{label} is not a canonical absolute path")
    parent, separator, _name = path.rpartition("/")
    if separator != "/" or not parent or parent == path:
        raise ContractError(f"{label} has no non-root direct parent")
    return parent


def parse_adapter_topology(
    body: str,
    config_sha256: str,
) -> tuple[AdapterTopology | None, str]:
    begin_prefix = ADAPTER_TOPOLOGY_BEGIN + "\n"
    end_boundary = "\n" + ADAPTER_TOPOLOGY_END + "\n"
    if not body.startswith(begin_prefix):
        if ADAPTER_TOPOLOGY_BEGIN in body or ADAPTER_TOPOLOGY_END in body:
            raise ContractError("Vega adapter topology framing changed")
        return None, body
    if (
        body.count(ADAPTER_TOPOLOGY_BEGIN) != 1
        or body.count(ADAPTER_TOPOLOGY_END) != 1
    ):
        raise ContractError("Vega adapter topology marker is duplicated")
    section, separator, remainder = body[
        len(begin_prefix) :
    ].partition(end_boundary)
    if not separator:
        raise ContractError("Vega adapter topology end framing changed")
    lines = section.split("\n")
    if len(lines) < 8:
        raise ContractError("Vega adapter topology inventory is incomplete")
    expected_headers = (
        f"contract={ADAPTER_TOPOLOGY_CONTRACT}",
        f"kernel={KERNEL_RELEASE}",
        f"config_sha256={config_sha256}",
    )
    if tuple(lines[:3]) != expected_headers:
        raise ContractError("Vega adapter topology identity changed")
    boot_prefix = "boot_id="
    platform_prefix = "platform_target="
    dt_prefix = "dt_target="
    if (
        not lines[3].startswith(boot_prefix)
        or not lines[4].startswith(platform_prefix)
        or not lines[5].startswith(dt_prefix)
        or lines[6] != f"entry_limit={ADAPTER_TOPOLOGY_ENTRY_LIMIT}"
    ):
        raise ContractError("Vega adapter topology header order changed")
    boot_id = lines[3].removeprefix(boot_prefix)
    if re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{12}",
        boot_id,
    ) is None:
        raise ContractError("Vega adapter topology boot ID is malformed")
    platform_target = lines[4].removeprefix(platform_prefix)
    dt_target = lines[5].removeprefix(dt_prefix)
    canonical_parent(platform_target, "Vega topology platform target")
    canonical_parent(dt_target, "Vega topology DT target")

    entry_pattern = re.compile(
        r"entry index=(0|[1-9][0-9]*) "
        r"adapter=(\S+) link=([01]) name_valid=([01]) "
        r"canonical=([01]) target=(\S+) parent=(\S+) "
        r"parent_match=([01]) of_canonical=([01]) "
        r"of_target=(\S+) of_match=([01]) match=([01])"
    )
    entry_lines = lines[7:-1]
    entries: list[tuple[str, int, int, int, int, int, int, int]] = []
    matching_adapters: list[str] = []
    seen_adapters: set[str] = set()
    for wanted_index, line in enumerate(entry_lines, 1):
        match = entry_pattern.fullmatch(line)
        if match is None or match.group(1) != str(wanted_index):
            raise ContractError("Vega adapter topology entry grammar changed")
        adapter = match.group(2)
        if SAFE_ADAPTER_TOKEN.fullmatch(adapter) is None:
            raise ContractError("Vega adapter topology token is unsafe")
        if adapter in seen_adapters:
            raise ContractError("Vega adapter topology duplicated an adapter")
        if entries and adapter <= entries[-1][0]:
            raise ContractError(
                "Vega adapter topology is not in C-locale order"
            )
        seen_adapters.add(adapter)
        link = int(match.group(3), 10)
        name_valid = int(match.group(4), 10)
        canonical = int(match.group(5), 10)
        target = match.group(6)
        parent = match.group(7)
        parent_match = int(match.group(8), 10)
        of_canonical = int(match.group(9), 10)
        of_target = match.group(10)
        of_match = int(match.group(11), 10)
        full_match = int(match.group(12), 10)
        expected_name_valid = int(
            NUMERIC_ADAPTER_NAME.fullmatch(adapter) is not None
        )
        if name_valid != expected_name_valid:
            raise ContractError("Vega topology name-valid bit changed")
        if canonical:
            if not link or not name_valid:
                raise ContractError(
                    "Vega topology canonical entry lacks link/name identity"
                )
            derived_parent = canonical_parent(
                target, "Vega topology adapter target"
            )
            if parent != derived_parent:
                raise ContractError(
                    "Vega topology adapter parent is not direct"
                )
        elif target != "-" or parent != "-":
            raise ContractError(
                "Vega topology noncanonical entry exposed path fields"
            )
        expected_parent_match = int(
            bool(canonical) and parent == platform_target
        )
        if parent_match != expected_parent_match:
            raise ContractError("Vega topology parent match bit changed")
        if of_canonical:
            canonical_parent(of_target, "Vega topology OF target")
            if not canonical:
                raise ContractError(
                    "Vega topology OF identity lacks adapter identity"
                )
        elif of_target != "-":
            raise ContractError(
                "Vega topology noncanonical OF entry exposed a path"
            )
        expected_of_match = int(
            bool(of_canonical) and of_target == dt_target
        )
        if of_match != expected_of_match:
            raise ContractError("Vega topology OF match bit changed")
        expected_full_match = int(bool(parent_match) and bool(of_match))
        if full_match != expected_full_match:
            raise ContractError("Vega topology full match bit changed")
        if full_match:
            matching_adapters.append(adapter)
        entries.append(
            (
                adapter,
                link,
                name_valid,
                canonical,
                parent_match,
                of_canonical,
                of_match,
                full_match,
            )
        )

    summary = re.fullmatch(
        r"summary entry_count=(0|[1-9][0-9]*) "
        r"link_count=(0|[1-9][0-9]*) "
        r"name_count=(0|[1-9][0-9]*) "
        r"canonical_count=(0|[1-9][0-9]*) "
        r"parent_match_count=(0|[1-9][0-9]*) "
        r"of_canonical_count=(0|[1-9][0-9]*) "
        r"of_match_count=(0|[1-9][0-9]*) "
        r"match_count=(0|[1-9][0-9]*) overflow=([01])",
        lines[-1],
    )
    if summary is None:
        raise ContractError("Vega adapter topology summary grammar changed")
    counts = tuple(int(value, 10) for value in summary.groups())
    (
        entry_count,
        link_count,
        name_count,
        canonical_count,
        parent_match_count,
        of_canonical_count,
        of_match_count,
        match_count,
        overflow,
    ) = counts
    computed = (
        len(entries),
        sum(entry[1] for entry in entries),
        sum(entry[2] for entry in entries),
        sum(entry[3] for entry in entries),
        sum(entry[4] for entry in entries),
        sum(entry[5] for entry in entries),
        sum(entry[6] for entry in entries),
        sum(entry[7] for entry in entries),
    )
    if counts[:8] != computed:
        raise ContractError("Vega adapter topology counts changed")
    if entry_count > ADAPTER_TOPOLOGY_ENTRY_LIMIT:
        raise ContractError("Vega adapter topology exceeded its entry limit")
    if overflow and entry_count != ADAPTER_TOPOLOGY_ENTRY_LIMIT:
        raise ContractError("Vega adapter topology overflow is inconsistent")
    return (
        AdapterTopology(
            kernel=KERNEL_RELEASE,
            config_sha256=config_sha256,
            boot_id=boot_id,
            platform_target=platform_target,
            dt_target=dt_target,
            entry_count=entry_count,
            link_count=link_count,
            name_count=name_count,
            canonical_count=canonical_count,
            parent_match_count=parent_match_count,
            of_canonical_count=of_canonical_count,
            of_match_count=of_match_count,
            match_count=match_count,
            overflow=overflow,
            matching_adapters=tuple(matching_adapters),
        ),
        remainder,
    )


def topology_is_ready(topology: AdapterTopology) -> bool:
    return (
        topology.overflow == 0
        and topology.link_count == topology.entry_count
        and topology.name_count == topology.entry_count
        and topology.canonical_count == topology.entry_count
        and topology.parent_match_count == 1
        and topology.of_match_count == 1
        and topology.match_count == 1
        and len(topology.matching_adapters) == 1
    )


def validate_topology_abort(
    reason: str,
    topology: AdapterTopology | None,
) -> None:
    predicates = {
        "i2c-adapter-entry-limit": lambda value: value.overflow == 1,
        "i2c-adapter-link-type": lambda value: (
            value.overflow == 0 and value.link_count != value.entry_count
        ),
        "i2c-adapter-name": lambda value: (
            value.overflow == 0
            and value.link_count == value.entry_count
            and value.name_count != value.entry_count
        ),
        "i2c-adapter-canonical-path": lambda value: (
            value.overflow == 0
            and value.link_count == value.entry_count
            and value.name_count == value.entry_count
            and value.canonical_count != value.entry_count
        ),
        "i2c6-adapter-parent-count": lambda value: (
            value.overflow == 0
            and value.canonical_count == value.entry_count
            and value.parent_match_count != 1
        ),
        "i2c6-adapter-of-node-count": lambda value: (
            value.overflow == 0
            and value.canonical_count == value.entry_count
            and value.parent_match_count == 1
            and value.of_match_count != 1
        ),
        "i2c6-adapter-count": lambda value: (
            value.overflow == 0
            and value.canonical_count == value.entry_count
            and value.parent_match_count == 1
            and value.of_match_count == 1
            and value.match_count != 1
        ),
    }
    predicate = predicates.get(reason)
    if predicate is None:
        if (
            reason != "unexpected-shell-exit"
            and topology is not None
            and not topology_is_ready(topology)
        ):
            raise ContractError(
                "Vega downstream abort contradicts non-ready "
                "adapter topology"
            )
        return
    if topology is None:
        raise ContractError("Vega mapping abort lacks adapter topology")
    if not predicate(topology):
        raise ContractError("Vega mapping abort contradicts adapter topology")


def parse_abort_line(abort_line: str) -> str:
    if not abort_line.startswith("__VEGA_ABORT__ "):
        raise ContractError("Vega pre-gate abort framing changed")
    abort = marker_values(abort_line.removeprefix("__VEGA_ABORT__ ").strip())
    reason = abort.get("reason", "")
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", reason) is None:
        raise ContractError("Vega pre-gate abort reason is malformed")
    if set(abort) == {"reason"}:
        expected_abort_line = f"__VEGA_ABORT__ reason={reason}"
    elif set(abort) == {"reason", "rc"} and reason == "unexpected-shell-exit":
        if (
            re.fullmatch(r"0|[1-9][0-9]{0,2}", abort["rc"]) is None
            or int(abort["rc"], 10) > 255
        ):
            raise ContractError("Vega pre-gate abort status is malformed")
        expected_abort_line = (
            "__VEGA_ABORT__ reason=unexpected-shell-exit "
            f"rc={abort['rc']}"
        )
    else:
        raise ContractError("Vega pre-gate abort field inventory changed")
    if abort_line != expected_abort_line:
        raise ContractError("Vega pre-gate abort framing changed")
    return reason


def parse_ordered_gate_fields(
    section: str,
    config_sha256: str,
    topology: AdapterTopology,
    session_count: int,
) -> dict[str, str]:
    lines = section.split("\n")
    if len(lines) != len(GATE_FIELD_ORDER):
        raise ContractError("Vega gate field count changed")
    gate: dict[str, str] = {}
    for key, line in zip(GATE_FIELD_ORDER, lines, strict=True):
        prefix = key + "="
        if not line.startswith(prefix):
            raise ContractError("Vega gate field order or grammar changed")
        gate[key] = line.removeprefix(prefix)

    exact_gate = {
        "kernel": KERNEL_RELEASE,
        "cmdline": KERNEL_CMDLINE,
        "config_sha256": config_sha256,
        "run_mounts": "0",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "nproc": "8",
        "handoff_state": "ready",
        "i2c6_compatible_sha256": I2C6_COMPATIBLE_SHA256,
        "i2c6_status_pre": I2C_STATUS_PRE,
        "i2c6_of": "/sys/firmware/devicetree/base/i2c@1100e000",
        "i2c6_clients": "0",
        "i2c_chardev": "absent",
        "keyboard_devices": "1",
        "tty1": "character-device",
        "usb0_address": "42:00:15:19:82:01",
        "usb0_carrier": "1",
        "usb0_operstate": "up",
        "usb0_ipv4_exact": "1",
        "udc_name": "11271000.usb",
        "udc_state": "configured",
        "usb_service_count": "1",
        "pre_dmesg_fatal_count": "0",
        "debugfs_mount": "/run/vega-debugfs",
        "debugfs_mount_count": "1",
        "diagnostic_mode": "600:0:0",
        "diagnostic_pre": DIAGNOSTIC_STATUS_PRE,
    }
    for key, wanted in exact_gate.items():
        if gate[key] != wanted:
            raise ContractError(f"Vega gate {key} changed")
    if gate["rootfs_type"] not in {"rootfs", "ramfs", "tmpfs"}:
        raise ContractError("Vega rootfs is not volatile")
    if re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
        r"[0-9a-f]{4}-[0-9a-f]{12}",
        gate["boot_id_pre"],
    ) is None:
        raise ContractError("Vega boot ID is not a canonical lowercase UUID")
    if topology.boot_id != gate["boot_id_pre"]:
        raise ContractError("Vega topology and gate boot IDs differ")
    adapter = gate["i2c6_adapter"]
    if NUMERIC_ADAPTER_NAME.fullmatch(adapter) is None:
        raise ContractError("Vega adapter identity is malformed")
    if topology.matching_adapters != (adapter,):
        raise ContractError("Vega topology and gate adapters differ")
    expected_adapter_debugfs = f"/run/vega-debugfs/i2c/{adapter}"
    if gate["adapter_debugfs"] != expected_adapter_debugfs:
        raise ContractError("Vega adapter debugfs path changed")
    if gate["diagnostic_path"] != (
        expected_adapter_debugfs + "/orion-run-all"
    ):
        raise ContractError("Vega diagnostic path changed")
    if re.fullmatch(r"[1-9][0-9]?", gate["usb_ready_count"]) is None:
        raise ContractError("Vega USB ready count is malformed")
    ready_count = int(gate["usb_ready_count"], 10)
    if ready_count > 64:
        raise ContractError("Vega USB ready count is out of bounds")
    if ready_count != session_count:
        raise ContractError("Vega USB prelude and ready count differ")
    return gate


def parse_gate_revalidation(
    section: str,
    config_sha256: str,
    topology: AdapterTopology,
    session_count: int,
    abort_reason: str | None,
) -> dict[str, str]:
    boundary = "\n" + FINAL_REVALIDATION_BEGIN + "\n"
    gate_fields, separator, revalidation = section.partition(boundary)
    if not separator:
        raise ContractError("Vega final revalidation begin framing changed")
    gate = parse_ordered_gate_fields(
        gate_fields,
        config_sha256,
        topology,
        session_count,
    )
    if abort_reason is None:
        expected = (
            "\n".join(FINAL_REVALIDATION_STEPS)
            + "\n"
            + FINAL_REVALIDATION_END
        )
        if revalidation != expected:
            raise ContractError("Vega final revalidation frame changed")
        return gate

    if abort_reason == "unexpected-shell-exit":
        allowed = {
            (
                ""
                if count == 0
                else "\n".join(FINAL_REVALIDATION_STEPS[:count]) + "\n"
            )
            for count in range(len(FINAL_REVALIDATION_STEPS) + 1)
        }
        allowed.add(
            "\n".join(FINAL_REVALIDATION_STEPS)
            + "\n"
            + FINAL_REVALIDATION_END
            + "\n"
        )
        if revalidation not in allowed:
            raise ContractError(
                "Vega unexpected-exit revalidation prefix changed"
            )
        return gate

    completed_steps = FINAL_REVALIDATION_ABORT_STEPS.get(abort_reason)
    if completed_steps is None:
        raise ContractError(
            "Vega gate abort is not attributable to final revalidation"
        )
    expected_prefix = (
        ""
        if completed_steps == 0
        else "\n".join(FINAL_REVALIDATION_STEPS[:completed_steps]) + "\n"
    )
    if revalidation != expected_prefix:
        raise ContractError(
            "Vega final revalidation abort prefix contradicts its reason"
        )
    return gate


def validate_capture_envelope(
    text: str,
    config_sha256: str,
) -> tuple[int, AdapterTopology]:
    if text.splitlines().count(USB_BANNER) != 1:
        raise ContractError("exact direct USB shell banner is absent or duplicated")
    matching_envelopes: list[tuple[int, str]] = []
    starts = (
        ADAPTER_TOPOLOGY_BEGIN + "\n",
        "__VEGA_GATE_BEGIN__\n",
        "__VEGA_ABORT__ ",
    )
    for count in range(1, 65):
        prefix = "\n".join(expected_usb_envelope(count)) + "\n"
        if text.startswith(prefix):
            body = text[len(prefix) :]
            if body.startswith(starts):
                matching_envelopes.append((count, body))
    if len(matching_envelopes) != 1:
        raise ContractError("exact inherited USB/BusyBox prelude changed")
    session_count, body = matching_envelopes[0]
    topology, body = parse_adapter_topology(body, config_sha256)

    lines = text.splitlines()
    complete_indices = tuple(
        index
        for index, line in enumerate(lines)
        if line.startswith("__VEGA_COMPLETE__")
    )
    abort_indices = tuple(
        index
        for index, line in enumerate(lines)
        if line.startswith("__VEGA_ABORT__")
    )
    if body.startswith("__VEGA_GATE_BEGIN__\n"):
        if topology is None:
            raise ContractError("Vega success capture lacks adapter topology")
        if not topology_is_ready(topology):
            raise ContractError("Vega success topology is not mapping-ready")
        if len(complete_indices) + len(abort_indices) != 1:
            raise ContractError(
                "Vega capture does not have exactly one terminal marker"
            )
        if abort_indices:
            if (
                "__VEGA_GATE_END__" in body
                or "__VEGA_GATE_PASS__" in body
            ):
                raise ContractError("aborted Vega gate claimed completion")
            abort_index = abort_indices[0]
            if any(line != "" for line in lines[abort_index + 1 :]):
                raise ContractError(
                    "Vega gate abort marker is not the final nonempty line"
                )
            abort_line = lines[abort_index]
            reason = parse_abort_line(abort_line)
            abort_offset = body.rfind(abort_line)
            gate_prefix = body[:abort_offset]
            trailing = body[abort_offset + len(abort_line) :]
            if (
                abort_offset < 0
                or not gate_prefix.endswith("\n")
                or any(line != "" for line in trailing.split("\n"))
            ):
                raise ContractError("Vega gate abort adjacency changed")
            parse_gate_revalidation(
                gate_prefix.removeprefix("__VEGA_GATE_BEGIN__\n"),
                config_sha256,
                topology,
                session_count,
                reason,
            )
            validate_topology_abort(reason, topology)
            raise ContractError(f"remote Vega gate aborted: {reason}")
        parse_gate_revalidation(
            exact_line_section(
                body,
                "__VEGA_GATE_BEGIN__",
                "__VEGA_GATE_END__",
                "Vega gate",
            ),
            config_sha256,
            topology,
            session_count,
            None,
        )
        complete_index = complete_indices[0]
        if any(line != "" for line in lines[complete_index + 1 :]):
            raise ContractError(
                "Vega completion marker is not the final nonempty line"
            )
        return session_count, topology

    if not body.startswith("__VEGA_ABORT__ "):
        raise ContractError(
            "Vega capture lacks an exact post-topology gate or abort boundary"
        )
    if complete_indices or len(abort_indices) != 1:
        raise ContractError(
            "pre-gate Vega capture does not have exactly one abort terminal"
        )
    abort_line, newline, trailing = body.partition("\n")
    if newline and any(line != "" for line in trailing.split("\n")):
        raise ContractError("Vega abort marker is not the final nonempty line")
    if lines[abort_indices[0]] != abort_line:
        raise ContractError("Vega pre-gate abort framing changed")
    reason = parse_abort_line(abort_line)
    validate_topology_abort(reason, topology)
    raise ContractError(f"remote Vega pre-gate aborted: {reason}")


def validate_success_transcript_framing(text: str) -> None:
    gate_prefix = "__VEGA_GATE_BEGIN__\n"
    gate_start = text.find(gate_prefix)
    if gate_start < 0:
        raise ContractError(
            "Vega success transcript framing changed at gate begin"
        )
    remainder = text[gate_start + len(gate_prefix) :]
    transitions = (
        (
            "gate end through final begin",
            "\n__VEGA_GATE_END__\n"
            "__VEGA_GATE_PASS__\n"
            "__VEGA_FINAL_BEGIN__\n",
        ),
        (
            "final end to I2C status begin",
            "\n__VEGA_FINAL_END__\n"
            "__VEGA_I2C_STATUS_POST_BEGIN__\n",
        ),
        (
            "I2C status end to post-state begin",
            "\n__VEGA_I2C_STATUS_POST_END__\n"
            "__VEGA_POST_BEGIN__\n",
        ),
        (
            "post-state end to AC status begin",
            "\n__VEGA_POST_END__\n"
            "__VEGA_AC_STATUS_POST_BEGIN__\n",
        ),
        (
            "AC status end to dmesg begin",
            "\n__VEGA_AC_STATUS_POST_END__\n"
            "__VEGA_DMESG_RAW_BEGIN__\n",
        ),
        (
            "dmesg end to completion",
            "\n__VEGA_DMESG_RAW_END__\n"
            "__VEGA_COMPLETE__",
        ),
    )
    for label, boundary in transitions:
        _section, separator, remainder = remainder.partition(boundary)
        if not separator:
            raise ContractError(
                f"Vega success transcript framing changed at {label}"
            )


def validate_capture(
    data: bytes,
    config_sha256: str,
    full_validator: ModuleType,
    partial_validator: ModuleType,
) -> tuple[str, bytes, str]:
    if not data or len(data) > 8 * 1024 * 1024 or b"\0" in data:
        raise ContractError("transport output is empty, oversized, or binary")
    text = data.decode("ascii", "strict")
    prelude_session_count, topology = validate_capture_envelope(
        text,
        config_sha256,
    )
    if "__VEGA_ABORT__" in text:
        raise ContractError("remote Vega gate aborted")
    validate_success_transcript_framing(text)

    ordered = (
        "__VEGA_ADAPTER_TOPOLOGY_BEGIN__",
        "__VEGA_ADAPTER_TOPOLOGY_END__",
        "__VEGA_GATE_BEGIN__",
        "__VEGA_FINAL_REVALIDATION_BEGIN__",
        "__VEGA_FINAL_REVALIDATION_END__",
        "__VEGA_GATE_END__",
        "__VEGA_GATE_PASS__",
        "__VEGA_FINAL_BEGIN__",
        "__VEGA_FINAL_END__",
        "__VEGA_I2C_STATUS_POST_BEGIN__",
        "__VEGA_I2C_STATUS_POST_END__",
        "__VEGA_POST_BEGIN__",
        "__VEGA_POST_END__",
        "__VEGA_AC_STATUS_POST_BEGIN__",
        "__VEGA_AC_STATUS_POST_END__",
        "__VEGA_DMESG_RAW_BEGIN__",
        "__VEGA_DMESG_RAW_END__",
        "__VEGA_COMPLETE__",
    )
    positions: list[int] = []
    for marker in ordered:
        if text.count(marker) != 1:
            raise ContractError(f"capture marker is absent or duplicated: {marker}")
        positions.append(text.index(marker))
    if positions != sorted(positions):
        raise ContractError("Vega capture marker order changed")

    gate = parse_gate_revalidation(
        exact_line_section(
            text,
            "__VEGA_GATE_BEGIN__",
            "__VEGA_GATE_END__",
            "Vega gate",
        ),
        config_sha256,
        topology,
        prelude_session_count,
        None,
    )

    final_text = unique_section(
        text, "__VEGA_FINAL_BEGIN__", "__VEGA_FINAL_END__"
    )
    final_data = (final_text + "\n").encode("ascii")
    classification: str
    validator_lines: list[str]
    try:
        tuples = full_validator.validate_text(final_data)
        classification = "complete-success"
        validator_lines = [
            "validation=vega-complete-success-transcript",
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
                "Vega final result is neither complete nor bounded partial: "
                f"complete={full_error}; partial={partial_error}"
            ) from partial_error
        classification = "bounded-stop-first-partial"
        validator_lines = [
            "validation=vega-bounded-stop-first-partial",
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
        "Vega final header",
    )
    i2c_status_post = unique_section(
        text,
        "__VEGA_I2C_STATUS_POST_BEGIN__",
        "__VEGA_I2C_STATUS_POST_END__",
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
        raise ContractError("Vega post-run I2C status inventory changed")
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
            raise ContractError(f"Vega post-run I2C status {key} changed")
    try:
        init_attempts = int(i2c_values["init_attempts"], 10)
        init_successes = int(i2c_values["init_successes"], 10)
        completed = int(header["completed"], 10)
        attempted = int(header["attempted"], 10)
        nonzero_starts = int(header["nonzero_starts"], 10)
    except ValueError as exc:
        raise ContractError("Vega reset-counter grammar changed") from exc
    if init_attempts != init_successes:
        raise ContractError("Vega reset attempts and successes differ")
    allowed_resets = allowed_init_counts(
        classification, completed, attempted, nonzero_starts
    )
    if init_attempts not in allowed_resets:
        raise ContractError("Vega reset-counter progression changed")

    post = key_values(
        unique_section(text, "__VEGA_POST_BEGIN__", "__VEGA_POST_END__"),
        "Vega post state",
    )
    required_post = {
        "vega_final_rc": "0",
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
    expected_post_fields = set(required_post) | {
        "boot_id_post",
        "write_rc",
    }
    if set(post) != expected_post_fields:
        raise ContractError("Vega post-run field inventory changed")
    for key, wanted in required_post.items():
        if post.get(key) != wanted:
            raise ContractError(f"Vega post-run state {key} changed")
    if post.get("boot_id_post") != gate["boot_id_pre"]:
        raise ContractError("Vega boot ID changed during the one-shot")
    write_rc = post.get("write_rc")
    if classification == "complete-success" and write_rc != "0":
        raise ContractError("successful Vega run had a negative debugfs write")
    if classification != "complete-success" and write_rc == "0":
        raise ContractError("partial Vega run had a successful debugfs write")
    if write_rc is None or not write_rc.isdecimal():
        raise ContractError("Vega debugfs write status is malformed")

    complete_line = next(
        line for line in text.splitlines() if line.startswith("__VEGA_COMPLETE__")
    )
    expected_complete_line = (
        f"__VEGA_COMPLETE__ write_rc={write_rc} "
        "invocation_count=1 guard_mode=400:0:0 "
        "post_capture=unconditional"
    )
    if complete_line != expected_complete_line:
        raise ContractError("Vega completion marker changed")

    log = unique_section(
        text, "__VEGA_DMESG_RAW_BEGIN__", "__VEGA_DMESG_RAW_END__"
    )
    log_counts = classify_kernel_log(log)
    if log_counts["vega_ready"] != 1:
        raise ContractError("Vega ready kernel marker is absent or duplicated")
    if log_counts["fatal"]:
        raise ContractError("Vega raw kernel log contains a fatal warning signature")
    sanitized = "\n".join(
        [
            "validation=vega-runtime-one-shot",
            f"classification={classification}",
            f"config_sha256={config_sha256}",
            f"raw_kernel_log_sha256={digest(log.encode('ascii'))}",
            f"raw_kernel_log_fatal_count={log_counts['fatal']}",
            f"raw_kernel_log_i2c_timeout_count={log_counts['i2c_timeout']}",
            f"raw_kernel_log_vega_ready_count={log_counts['vega_ready']}",
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
        full_validator = load_orion_result_validator(
            repository,
            "validate-orion-result.py",
            co.ORION_RESULT_VALIDATOR_SHA256,
            "vega_orion_full_validator",
        )
        partial_validator = load_orion_result_validator(
            repository,
            "validate-orion-partial.py",
            co.ORION_PARTIAL_VALIDATOR_SHA256,
            "vega_orion_partial_validator",
        )
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

    print("validation=vega-exact-serviceability-gated-one-shot")
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
