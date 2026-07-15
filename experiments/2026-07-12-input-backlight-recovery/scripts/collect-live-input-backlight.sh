#!/usr/bin/env bash

# Read-only Gemini PDA input, keyboard-expander, touchscreen, and backlight
# evidence collector. Run this script on the device through SSH; it never
# writes sysfs, I2C, input, PWM, framebuffer, or debug interfaces.

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

heading "input capabilities"
for device in /sys/class/input/input*; do
	[[ -e "$device" ]] || continue
	for field in capabilities/ev capabilities/key capabilities/abs \
		capabilities/rel capabilities/sw capabilities/msc; do
		[[ -r "$device/$field" ]] || continue
		printf '%s/%s=%s\n' "${device##*/}" "${field#*/}" \
			"$(tr '\n' ' ' < "$device/$field")"
	done
done

heading "I2C devices"
for device in /sys/bus/i2c/devices/*; do
	[[ -e "$device" ]] || continue
	name="$(first_line "$device/name")"
	modalias="$(first_line "$device/modalias")"
	[[ -n "$name$modalias" ]] || continue
	printf '%s|name=%s|modalias=%s|driver=%s|of_node=%s\n' \
		"${device##*/}" "$name" "$modalias" \
		"$(readlink -f "$device/driver" 2>/dev/null || true)" \
		"$(readlink -f "$device/of_node" 2>/dev/null || true)"
done

heading "focused I2C bindings"
for device in /sys/bus/i2c/devices/4-0062 \
	/sys/bus/i2c/devices/5-005b /sys/bus/i2c/devices/1-003e; do
	[[ -e "$device" ]] || continue
	printf '[%s]\n' "${device##*/}"
	for field in name modalias uevent; do
		[[ -r "$device/$field" ]] || continue
		printf '%s=' "$field"
		tr '\n' ';' < "$device/$field"
		printf '\n'
	done
	printf 'driver=%s\nof_node=%s\n' \
		"$(readlink -f "$device/driver" 2>/dev/null || true)" \
		"$(readlink -f "$device/of_node" 2>/dev/null || true)"
done

heading "device-tree input and PWM nodes"
dt_base=/sys/firmware/devicetree/base
for node in \
	"$dt_base/soc/i2c@11011000/cap_touch@62" \
	"$dt_base/soc/i2c@11011000/cap_touch@62/novatek-mp-criteria-nvtpid@0" \
	"$dt_base/soc/i2c@1101c000/aw9523_key@5b" \
	"$dt_base/soc/touch@" \
	"$dt_base/soc/aw9523" \
	"$dt_base/soc/aw9523_key@" \
	"$dt_base/soc/pwm@11006000" \
	"$dt_base/soc/pwm_disp@1100f000"; do
	[[ -d "$node" ]] || continue
	printf '[%s]\n' "${node#"$dt_base"/}"
	for property in compatible status name clock-names pinctrl-names; do
		property_text "$node/$property"
	done
	for property in reg interrupts interrupt-parent debounce clocks \
		vtouch-supply pinctrl-0 pinctrl-1 pinctrl-2 pinctrl-3 pinctrl-4 pinctrl-5 \
		X_Channel Y_Channel AIN_X AIN_Y AIN_KEY IC_X_CFG_SIZE IC_Y_CFG_SIZE \
		IC_KEY_CFG_SIZE; do
		property_hex "$node/$property"
	done
	printf 'properties='
	find "$node" -maxdepth 1 -type f -printf '%f,' 2>/dev/null | sort
	printf '\n'
done

heading "PWM and backlight sysfs"
for device in /sys/devices/soc/1100f000.pwm_disp \
	/sys/devices/soc/11006000.pwm; do
	[[ -e "$device" ]] || continue
	printf '[%s]\n' "${device##*/}"
	for field in modalias uevent pwm_debug; do
		[[ -r "$device/$field" ]] || continue
		printf '%s=' "$field"
		tr '\0' ' ' < "$device/$field"
		printf '\n'
	done
done
for device in /sys/class/backlight/*; do
	[[ -e "$device" ]] || continue
	printf '[backlight:%s]' "${device##*/}"
	for field in brightness max_brightness actual_brightness power; do
		value="$(first_line "$device/$field")"
		[[ -n "$value" ]] && printf '|%s=%s' "$field" "$value"
	done
	printf '\n'
done
for device in /sys/class/leds/*; do
	[[ -e "$device" ]] || continue
	printf '[led:%s]' "${device##*/}"
	for field in brightness max_brightness trigger; do
		[[ -r "$device/$field" ]] || continue
		printf '|%s=%s' "$field" "$(tr '\n' ' ' < "$device/$field")"
	done
	printf '\n'
done

heading "input and EINT interrupts"
grep -Ei 'mtk-kpd|cap_touch|aw9523|mt-eint|mt-i2c' /proc/interrupts 2>/dev/null || true

heading "focused kernel messages"
dmesg 2>/dev/null | grep -Ei \
	'(NVT-ts|cap_touch|mtk-tpd|AW9523|aw9523|Integrated keyboard|lp3101|lcd bias|disp_pwm_set_backlight_cmdq|backlight is (on|off))' \
	|| true
