#!/usr/bin/env bash

# Read-only Gemini USB, SuperSpeed PHY, and Type-C evidence collector. Run this
# script on the device through SSH; it never writes sysfs, I2C, GPIO, USB, or
# PHY controls and never scans unbound I2C addresses.

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

platform_summary() {
	local device name
	for device in /sys/bus/platform/devices/*; do
		[[ -e "$device" ]] || continue
		name="${device##*/}"
		case "$name" in
			*usb*|xhci*) ;;
			*) continue ;;
		esac
		printf '[%s]|modalias=%s|driver=%s|of_node=%s\n' "$name" \
			"$(first_line "$device/modalias")" \
			"$(readlink -f "$device/driver" 2>/dev/null || true)" \
			"$(readlink -f "$device/of_node" 2>/dev/null || true)"
		for field in uevent resource resource0 resource1 resource2 \
			power/runtime_status power/control; do
			[[ -r "$device/$field" ]] || continue
			printf '%s/%s=' "$name" "$field"
			tr '\0' ';' < "$device/$field"
			printf '\n'
		done
	done
}

heading "running kernel"
uname -a

heading "platform USB, PHY, and Type-C devices"
platform_summary

heading "Type-C I2C controllers"
for device in /sys/bus/i2c/devices/*-0025; do
	[[ -e "$device" ]] || continue
	printf '[%s]|name=%s|modalias=%s|driver=%s|of_node=%s\n' \
		"${device##*/}" "$(first_line "$device/name")" \
		"$(first_line "$device/modalias")" \
		"$(readlink -f "$device/driver" 2>/dev/null || true)" \
		"$(readlink -f "$device/of_node" 2>/dev/null || true)"
	field=uevent
	if [[ -r "$device/$field" ]]; then
		printf '%s/%s=' "${device##*/}" "$field"
		tr '\0' ';' < "$device/$field"
		printf '\n'
	fi
done

heading "Type-C, USB-role, and PHY class state"
for device in /sys/class/typec/* /sys/class/usb_role/* /sys/class/phy/*; do
	[[ -e "$device" ]] || continue
	name="${device##*/}"
	printf '[%s]|subsystem=%s|driver=%s\n' "$name" \
		"$(readlink -f "$device/subsystem" 2>/dev/null || true)" \
		"$(readlink -f "$device/driver" 2>/dev/null || true)"
	for field in uevent role data_role power_role port_type orientation \
		preferred_role current_role type power runtime_status; do
		[[ -r "$device/$field" ]] || continue
		printf '%s/%s=' "$name" "$field"
		tr '\0' ';' < "$device/$field"
		printf '\n'
	done
done

heading "USB buses and devices"
for device in /sys/bus/usb/devices/*; do
	[[ -e "$device" ]] || continue
	printf '[%s]' "${device##*/}"
	for field in manufacturer product idVendor idProduct busnum devnum speed \
		version maxchild authorized; do
		value="$(first_line "$device/$field")"
		[[ -n "$value" ]] && printf '|%s=%s' "$field" "$value"
	done
	printf '|driver=%s\n' "$(readlink -f "$device/driver" 2>/dev/null || true)"
done

heading "device-tree USB and Type-C nodes"
dt_base=/sys/firmware/devicetree/base
for node in \
	"$dt_base/soc/usb1@11200000" \
	"$dt_base/soc/usb1p_sif@11210000" \
	"$dt_base/soc/usb3@11270000" \
	"$dt_base/soc/usb3_xhci@11270000" \
	"$dt_base/soc/usb3_xhci@11270000/eint_usb_iddig@181" \
	"$dt_base/soc/usb3_phy" \
	"$dt_base/soc/usb3_sif@11280000" \
	"$dt_base/soc/usb3_sif2@11290000" \
	"$dt_base/soc/usb_c_pinctrl@0" \
	"$dt_base/soc/usbphy@0" \
	"$dt_base/soc/fusb301@" \
	"$dt_base/soc/fusb301a@" \
	"$dt_base/soc/i2c@11007000/fusb301a@25" \
	"$dt_base/soc/i2c@11008000/fusb301@25"; do
	[[ -d "$node" ]] || continue
	printf '[%s]\n' "${node#"$dt_base"/}"
	for property in compatible status name clock-names reg-names interrupt-names \
		pinctrl-names phy-names dr_mode; do
		property_text "$node/$property"
	done
	for property in reg interrupts interrupt-parent debounce clocks phys \
		pinctrl-0 pinctrl-1 pinctrl-2 pinctrl-3 pinctrl-4 pinctrl-5 \
		vbus-supply phy-supply id-gpios vbus-gpios extcon usb-role-switch; do
		property_hex "$node/$property"
	done
	printf 'properties='
	find "$node" -maxdepth 1 -type f -printf '%f,' 2>/dev/null | sort
	printf '\n'
done

heading "USB and Type-C interrupts"
grep -Ei 'usb|musb|xhci|fusb|iddig|mu3phy|phy' /proc/interrupts 2>/dev/null || true

heading "focused kernel messages"
dmesg 2>/dev/null | grep -Ei \
	'(usb|musb|xhci|fusb|type.?c|iddig|mu3phy|phy)' || true
