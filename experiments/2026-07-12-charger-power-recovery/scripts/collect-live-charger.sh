#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only Gemini charger and fuel-gauge evidence collector. Run this script
# on the device through SSH. It reads sysfs, the live device tree, procfs, and
# kernel messages only; it never scans I2C, changes a power-supply property, or
# writes a charger/regulator register.

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

property_text() {
	local path=$1
	[[ -r "$path" ]] || return 0
	printf '%s=' "${path##*/}"

	tr '\0' ',' < "$path" | sed 's/,$//'
	printf '\n'
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

heading "bound charger and PMIC I2C devices"
for device in /sys/bus/i2c/devices/0-006b /sys/bus/i2c/devices/0-0070 \
	/sys/bus/i2c/devices/0-0053 /sys/bus/i2c/devices/1-006b; do
	[[ -e "$device" ]] || continue
	printf '[%s]|name=%s|modalias=%s|driver=%s|of_node=%s\n' \
		"${device##*/}" "$(first_line "$device/name")" \
		"$(first_line "$device/modalias")" "$(link_target "$device/driver")" \
		"$(link_target "$device/of_node")"
	if [[ -r "$device/uevent" ]]; then
		printf 'uevent='
		tr '\0' ';' < "$device/uevent"
		printf '\n'
	fi
done

heading "power-supply telemetry"
for supply in /sys/class/power_supply/*; do
	[[ -d "$supply" ]] || continue
	case "${supply##*/}" in
		ac|battery|usb|wireless|*charger*|*fuel*|*bms*) ;;
		*) continue ;;
	esac
	printf '[%s]|device=%s|driver=%s\n' "${supply##*/}" \
		"$(link_target "$supply/device")" "$(link_target "$supply/device/driver")"
	for field in type status health capacity online present voltage_now voltage_min_design \
		voltage_max_design current_now current_max charge_now charge_full charge_full_design \
		charge_type input_current_limit constant_charge_current constant_charge_voltage \
		manufacturer model_name technology; do
		[[ -r "$supply/$field" ]] || continue
		printf '%s=%s\n' "$field" "$(head -n 1 "$supply/$field" 2>/dev/null)"
	done
done

heading "charger and fuel-gauge device-tree nodes"
dt_base=/sys/firmware/devicetree/base
while IFS= read -r node; do
	base=${node##*/}
	case "${base,,}" in
		*bq24261*|*sw_charger*|*bq25890*|*buck_boost*|*fan49101*|*rt9466*|*battery*|*bat_metter*|*fuel*|*charger*) ;;
		*) continue ;;
	esac
	printf '[%s]\n' "${node#"$dt_base"/}"
	for property in compatible status name charger_name interrupt-names; do
		property_text "$node/$property"
	done
	for property in reg interrupts interrupt-parent gpios pinctrl-0 pinctrl-1 \
		ichg aicr mivr cv ieoc safety_timer ircmp_resistor ircmp_vclamp \
		charger_current; do
		property_hex "$node/$property"
	done
done < <(find "$dt_base" -type d 2>/dev/null)

heading "charger-related interrupts"
grep -Ei 'bq25890|bq24261|fan49101|rt9466|charger|battery|fuel|mtk-charger|mtk_charger' \
	/proc/interrupts 2>/dev/null || true

heading "focused kernel messages"
dmesg 2>/dev/null | grep -Ei \
	'(bq25890|bq24261|fan49101|rt9466|charger|battery|fuel.?gauge|mtk_charger|charging)' | \
	grep -Ev '(serial|imei|mac|calib)' | head -n 320 || true

heading "power and charger config symbols"
if [[ -r /proc/config.gz ]] && command -v zgrep >/dev/null 2>&1; then
	zgrep -Ei '(^CONFIG_(POWER_SUPPLY|CHARGER|BATTERY|FUEL|IIO|MTK|MEDIATEK).*=|^# CONFIG_(POWER_SUPPLY|CHARGER|BATTERY|FUEL|IIO|MTK|MEDIATEK) is not set)' \
		/proc/config.gz 2>/dev/null || true
fi
