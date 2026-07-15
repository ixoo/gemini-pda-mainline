#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only Gemini watchdog evidence collector. It reads sysfs, procfs, the
# live device tree, and filtered kernel messages. It never opens /dev/watchdog
# and never changes watchdog mode, timeout, keepalive, reset, or reboot state.

set -u
export LC_ALL=C

heading() {
	printf '\n===== %s =====\n' "$1"
}

first_line() {
	[[ -r "$1" ]] && head -n 1 "$1" 2>/dev/null
}

link_target() {
	if [[ -L "$1" ]]; then
		readlink -f "$1" 2>/dev/null || true
	fi
}

property_hex() {
	local path=$1
	[[ -r "$path" ]] || return 0
	printf '%s=' "${path##*/}"
	od -An -tx1 -v "$path" | tr -d ' \n'
	printf '\n'
}

heading "running kernel"
uname -a
if [[ -r /proc/device-tree/model ]]; then
	printf 'model='
	tr '\0' '\n' < /proc/device-tree/model
fi
if [[ -r /proc/device-tree/compatible ]]; then
	printf 'compatible='
	tr '\0' ',' < /proc/device-tree/compatible | sed 's/,$//'
	printf '\n'
fi

heading "standard watchdog interfaces"
for device in /sys/class/watchdog/*; do
	[[ -e "$device" ]] || continue
	printf '[%s]|device=%s|driver=%s\n' "${device##*/}" \
		"$(link_target "$device/device")" "$(link_target "$device/device/driver")"
	for field in identity state status timeout pretimeout nowayout bootstatus timeleft; do
		[[ -r "$device/$field" ]] || continue
		printf '%s=%s\n' "$field" "$(first_line "$device/$field")"
	done
done
if [[ -e /dev/watchdog || -e /dev/watchdog0 ]]; then
	ls -l /dev/watchdog /dev/watchdog0 2>/dev/null || true
else
	echo "device_nodes=none"
fi

heading "watchdog-related interrupts"
grep -Ei 'watchdog|wdt|toprgu|md_wdt|md2_wdt' /proc/interrupts 2>/dev/null || true

heading "watchdog device-tree metadata"
dt_base=/sys/firmware/devicetree/base
for node in "$dt_base/soc/toprgu@10007000" "$dt_base/soc/watchdog@10007000"; do
	[[ -d "$node" ]] || continue
	printf '[%s]\n' "${node#"$dt_base"/}"
	for property in compatible status name; do
		path="$node/$property"
		[[ -r "$path" ]] || continue
		printf '%s=' "$property"
		tr '\0' ',' < "$path" | sed 's/,$//'
		printf '\n'
	done
	for property in reg interrupts interrupt-parent; do
		property_hex "$node/$property"
	done
done

heading "watchdog configuration"
if [[ -r /proc/config.gz ]] && command -v zgrep >/dev/null 2>&1; then
	zgrep -Ei '(^CONFIG_(WATCHDOG|MTK_WATCHDOG|MTK_WATCHDOG_COMMON|WATCHDOG_CORE).*=|^# CONFIG_(WATCHDOG|MTK_WATCHDOG|MTK_WATCHDOG_COMMON|WATCHDOG_CORE) is not set)' \
		/proc/config.gz 2>/dev/null || true
fi

heading "focused kernel messages"
dmesg 2>/dev/null | grep -Ei '(^|[[:space:]])(watchdog|wdt|toprgu|\[WDK\]|md_wdt|md2_wdt)' | \
	grep -Ev '(serial|imei|mac)' | tail -n 80 || true
