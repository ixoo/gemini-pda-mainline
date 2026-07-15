#!/usr/bin/env bash

# Read-only Gemini camera identity collector. It does not open a camera,
# access I2C registers, change GPIO/regulator state, or start streaming.

set -u
export LC_ALL=C

heading() {
	printf '\n===== %s =====\n' "$1"
}

first_line() {
	[[ -r "$1" ]] && head -n 1 "$1" 2>/dev/null
}

heading "running kernel"
uname -a

heading "camera I2C devices"
for device in \
	/sys/bus/i2c/devices/2-002d \
	/sys/bus/i2c/devices/2-0072 \
	/sys/bus/i2c/devices/3-000c \
	/sys/bus/i2c/devices/3-0036 \
	/sys/bus/i2c/devices/8-0036; do
	[[ -e "$device" ]] || continue
	printf '[%s]|name=%s|modalias=%s|driver=%s|of_node=%s\n' \
		"${device##*/}" "$(first_line "$device/name")" \
		"$(first_line "$device/modalias")" \
		"$(readlink -f "$device/driver" 2>/dev/null || true)" \
		"$(readlink -f "$device/of_node" 2>/dev/null || true)"
	if [[ -r "$device/uevent" ]]; then
		printf '%s/uevent=' "${device##*/}"
		tr '\0' ';' < "$device/uevent"
		printf '\n'
	fi
done

heading "camera I2C adapter topology"
for adapter in /sys/bus/i2c/devices/i2c-[0-9]*; do
	[[ -d "$adapter" ]] || continue
	printf '[%s]|name=%s|of_node=%s\n' "${adapter##*/}" \
		"$(first_line "$adapter/name")" \
		"$(readlink -f "$adapter/of_node" 2>/dev/null || true)"
done

heading "candidate sensor device presence"
# This only checks whether a kernel I2C client object already exists. It does
# not scan the bus or issue a transaction.
for bus in 2 3 8; do
	for address in 20 28; do
		device="/sys/bus/i2c/devices/${bus}-${address}"
		if [[ -e "$device" ]]; then
			printf '[%s]|name=%s|modalias=%s|driver=%s\n' \
				"${device##*/}" "$(first_line "$device/name")" \
				"$(first_line "$device/modalias")" \
				"$(readlink -f "$device/driver" 2>/dev/null || true)"
		else
			printf '[%s]|absent\n' "${device##*/}"
		fi
	done
done

heading "camera platform devices"
for device in /sys/bus/platform/devices/*camera* \
	/sys/bus/platform/devices/*seninf* \
	/sys/class/video4linux/*; do
	[[ -e "$device" ]] || continue
	printf '[%s]|driver=%s|modalias=%s\n' "${device##*/}" \
		"$(readlink -f "$device/driver" 2>/dev/null || true)" \
		"$(first_line "$device/modalias")"
done

heading "vendor camera diagnostics"
for file in /proc/AEON_CAMERA0 /proc/AEON_CAMERA1 \
	/proc/AEON_CAMERA0_TUNING_VERSION /proc/AEON_CAMERA1_TUNING_VERSION; do
	[[ -r "$file" ]] || continue
	printf '%s=' "${file##*/}"
	head -c 256 "$file" 2>/dev/null | tr '\000\n' ' '
	printf '\n'
done

heading "camera kernel symbols"
if [[ -r /proc/kallsyms ]]; then
	grep -Ei '(sp5509|ov5675|s5k5e2|imgsensor|image_sensor|camera_hw|seninf)' \
		/proc/kallsyms | head -n 180 || true
fi

heading "camera device nodes"
find /dev -maxdepth 1 \( -type c -o -type l \) -print 2>/dev/null | \
	grep -Ei '(video|camera|isp|img|v4l|sen|af|flash)' | head -n 120 || true

heading "camera kernel messages"
dmesg 2>/dev/null | grep -Ei \
	'(camera|imgsensor|image.?sensor|seninf|isp|sp5509|ov5675|s5k5e2|af)' | \
	tail -n 160 || true
