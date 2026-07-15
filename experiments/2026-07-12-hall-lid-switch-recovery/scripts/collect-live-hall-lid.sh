#!/usr/bin/env bash

# Read-only hall/lid and toggle-switch evidence collector. It reads sysfs, the
# flattened device tree, /proc/interrupts, and filtered kernel messages. It
# never reads input event streams, changes GPIO direction/polarity, enables
# wake sources, or stimulates either physical switch.

set -u
export LC_ALL=C

heading() {
	printf '\n===== %s =====\n' "$1"
}

first_line() {
	[[ -r "$1" ]] && head -n 1 "$1" 2>/dev/null
}

property_text() {
	local path="$1"
	[[ -r "$path" ]] || return 0
	printf '%s=' "${path##*/}"
	tr '\0' ',' < "$path" | sed 's/,$//'
	printf '\n'
}

property_hex() {
	local path="$1"
	[[ -r "$path" ]] || return 0
	printf '%s=' "${path##*/}"
	od -An -tx1 -v "$path" | tr -d ' \n'
	printf '\n'
}

heading "running kernel"
uname -a

heading "Android switch classes"
for device in /sys/class/switch/*; do
	[[ -e "$device" ]] || continue
	printf '[%s]' "${device##*/}"
	for field in state name uevent; do
		[[ -r "$device/$field" ]] || continue
		printf '|%s=' "$field"
		tr '\n' ';' < "$device/$field"
	done
	printf '\n'
done

heading "input devices"
for device in /sys/class/input/input*; do
	[[ -e "$device" ]] || continue
	printf '[%s]' "${device##*/}"
	for field in name phys modalias; do
		value="$(first_line "$device/$field")"
		[[ -n "$value" ]] && printf '|%s=%s' "$field" "$value"
	done
	printf '|device=%s|driver=%s\n' \
		"$(readlink -f "$device/device" 2>/dev/null || true)" \
		"$(readlink -f "$device/device/driver" 2>/dev/null || true)"
done

heading "switch input capabilities"
for device in /sys/class/input/input*; do
	[[ -e "$device" ]] || continue
	for field in capabilities/ev capabilities/key capabilities/sw; do
		[[ -r "$device/$field" ]] || continue
		printf '%s/%s=%s\n' "${device##*/}" "${field#*/}" \
			"$(tr '\n' ' ' < "$device/$field")"
	done
done

heading "hall and switch device-tree nodes"
dt_base=/sys/firmware/devicetree/base
for node in \
	"$dt_base/hall" \
	"$dt_base/switch" \
	"$dt_base/soc/pinctrl@10005000/hallpincfg" \
	"$dt_base/soc/pinctrl@10005000/halldefaultcfg" \
	"$dt_base/soc/pinctrl@10005000/switchpincfg" \
	"$dt_base/soc/pinctrl@10005000/switchdefaultcfg"; do
	[[ -d "$node" ]] || continue
	printf '[%s]\n' "${node#"$dt_base"/}"
	for property in compatible status name pinctrl-names; do
		property_text "$node/$property"
	done
	for property in debounce interrupt-parent interrupts pinctrl-0 pinctrl-1; do
		property_hex "$node/$property"
	done
	for child in "$node"/*; do
		[[ -d "$child" ]] || continue
		printf '[%s/%s]\n' "${node#"$dt_base"/}" "${child##*/}"
		for property in pins pinmux bias-pull-up bias-pull-down bias-disable output-low output-high input-schmitt-enable slew-rate; do
			property_hex "$child/$property"
		done
	done
	printf 'properties='
	for property in "$node"/*; do
		[[ -f "$property" ]] || continue
		printf '%s,' "${property##*/}"
	done
	printf '\n'
done

heading "hall and switch interrupts"
grep -Ei 'hall-eint|switch-eint|mtk-kpd|mt-eint' /proc/interrupts 2>/dev/null || true

heading "filtered kernel messages"
dmesg 2>/dev/null | grep -Ei \
	'(hall|fcover|switch-eint|mtk-toggle|anti.?tamper|mtk-kpd|power.?key|SW_LID)' || true
