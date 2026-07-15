#!/usr/bin/env bash

# Read-only Gemini sensor inventory.
#
# This records driver/topology metadata only.  It does not probe I2C addresses,
# read sensor values or calibration blobs, enable IIO channels, change input
# state, or write any sysfs/debug interface.

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
if [[ -r /proc/device-tree/model ]]; then
	printf 'model='
	tr '\0' '\n' < /proc/device-tree/model
fi

heading "sensor-related Android properties"
if command -v getprop >/dev/null 2>&1; then
	getprop 2>/dev/null | grep -Ei \
		'\[(ro\.hardware\.sensor|ro\.mediatek\.platform|ro\.board\.platform|persist\.vendor\.sensor|persist\.sys\.sensor|ro\.mtk\.sensor|ro\.config\.hwrotation)\]:' \
		|| true
fi

heading "I2C sensor devices"
for device in /sys/bus/i2c/devices/*; do
	[[ -e "$device" ]] || continue
	name="$(first_line "$device/name")"
	modalias="$(first_line "$device/modalias")"
	of_node="$(link_target "$device/of_node")"
	case "${name,,}|${modalias,,}|${of_node,,}" in
		*bmi160*|*stk3x1x*|*mmc3530*|*bmp28*|*bmp08*|*hts221*|*humid*|*gyro*|*accel*|*mag*|*baro*|*alsps*|*sensor*)
			printf '%s|name=%s|modalias=%s|driver=%s|of_node=%s\n' \
				"${device##*/}" "$name" "$modalias" \
				"$(link_target "$device/driver")" "$of_node"
			;;
	esac
done

heading "IIO device metadata"
for device in /sys/bus/iio/devices/iio:device*; do
	[[ -e "$device" ]] || continue
	name="$(first_line "$device/name")"
	modalias="$(first_line "$device/modalias")"
	printf '[%s]|name=%s|modalias=%s|driver=%s|of_node=%s\n' \
		"${device##*/}" "$name" "$modalias" \
		"$(link_target "$device/device/driver")" \
		"$(link_target "$device/device/of_node")"
	printf 'channels='
	find "$device/scan_elements" -maxdepth 1 -type f -name '*_en' \
		-printf '%f,' 2>/dev/null | sort
	printf '\n'
done

heading "input sensor metadata"
for device in /sys/class/input/input*; do
	[[ -e "$device" ]] || continue
	name="$(first_line "$device/name")"
	phys="$(first_line "$device/phys")"
	case "${name,,}|${phys,,}" in
		*accel*|*gyro*|*mag*|*compass*|*light*|*proximity*|*pressure*|*humidity*|*alsps*|*m_acc*|*m_step*|*sensor*|*rotation*|*orientation*|*step*|*pedometer*)
			printf '[%s]|name=%s|phys=%s|modalias=%s|device=%s|driver=%s\n' \
				"${device##*/}" "$name" "$phys" "$(first_line "$device/modalias")" \
				"$(link_target "$device/device")" \
				"$(link_target "$device/device/driver")"
			for field in capabilities/ev capabilities/key capabilities/abs capabilities/rel; do
				[[ -r "$device/$field" ]] || continue
				printf '%s/%s=' "${device##*/}" "$field"
				tr '\n' ' ' < "$device/$field"
				printf '\n'
			done
			;;
	esac
done

heading "vendor sensor classes"
for class in /sys/class/sensor /sys/class/misc /sys/class/m_*; do
	[[ -e "$class" ]] || continue
	for device in "$class"/*; do
		[[ -e "$device" ]] || continue
		base="${device##*/}"
		case "${base,,}" in
			*accel*|*gyro*|*mag*|*compass*|*light*|*proximity*|*pressure*|*humidity*|*sensor*|*rotation*|*orientation*|*step*|*pedometer*)
				printf '%s|device=%s|driver=%s\n' "$device" \
					"$(link_target "$device/device")" \
					"$(link_target "$device/device/driver")"
				;;
		esac
	done
done

heading "legacy sensor ABI metadata"
for class in /sys/class/misc/m_alsps_misc /sys/class/misc/m_acc_misc \
	/sys/class/misc/m_gyro_misc /sys/class/misc/hwmsensor; do
	[[ -e "$class" ]] || continue
	printf '[%s] attributes=' "$class"
	find -L "$class" -maxdepth 1 -type f -printf '%f,' 2>/dev/null | sort
	printf '\n'
	for attribute in "$class"/*devnum "$class"/*active "$class"/*delay; do
		[[ -r "$attribute" ]] || continue
		printf '%s=' "${attribute##*/}"
		head -n 1 "$attribute" 2>/dev/null || true
	done
done

heading "vendor IMU identity metadata"
for driver in /sys/bus/platform/drivers/gsensor /sys/bus/platform/drivers/gyroscope; do
	[[ -d "$driver" ]] || continue
	printf '[%s]\n' "$driver"
	for attribute in chipinfo status acc_range gyro_range acc_op_mode gyro_op_mode; do
		path="$driver/$attribute"
		[[ -r "$path" ]] || continue
		printf '%s=' "$attribute"
		if [[ "$attribute" == status ]]; then
			head -n 2 "$path" 2>/dev/null || true
		else
			head -n 1 "$path" 2>/dev/null || true
		fi
	done
done

heading "vendor sensor symbols when exposed"
if [[ -r /proc/kallsyms ]]; then
	awk '{print $3}' /proc/kallsyms 2>/dev/null | grep -Ei \
		'^(stk3x1x|mmc3530|bmi160|hwmsen|alsps|msensor)' | sort -u | head -n 320 || true
fi

heading "sensor device-tree nodes"
dt_base=/sys/firmware/devicetree/base
while IFS= read -r node; do
	base="${node##*/}"
	case "${base,,}" in
		*bmi160*|*stk3x1x*|*mmc3530*|*bmp28*|*bmp08*|*hts221*|*humid*|*gyro*|*accel*|*mag*|*baro*|*alsps*|*sensor*)
			printf '[%s]\n' "${node#"$dt_base"/}"
			for property in compatible status name model i2c_num direction polling_mode_ps polling_mode_als; do
				property_text "$node/$property"
			done
			for property in reg interrupts interrupt-parent gpios pinctrl-0 pinctrl-1 \
				mount-matrix vdd-supply vddio-supply power-supply firlen batch; do
				property_hex "$node/$property"
			done
			printf 'properties='
			find "$node" -maxdepth 1 -type f -printf '%f,' 2>/dev/null | sort
			printf '\n'
			;;
	esac
done < <(find "$dt_base" -type d 2>/dev/null)

heading "sensor and I2C interrupts"
grep -Ei 'bmi160|stk3x1x|mmc3530|bmp2|bmp08|hts221|humid|gyro|accel|mag|baro|alsps|sensor|i2c1|mt-i2c|eint' \
	/proc/interrupts 2>/dev/null || true

heading "focused kernel messages"
dmesg 2>/dev/null | grep -Ei \
	'(bmi160|stk3x1x|mmc3530|bmp2|bmp08|hts221|humid|gyro|accel|mag|baro|alsps|sensor|iio|mt-i2c)' | \
	grep -Ev '(temp|thermal|calib|current|value|data)' | head -n 260 || true

heading "Linux config symbols when exposed"
if [[ -r /proc/config.gz ]] && command -v zgrep >/dev/null 2>&1; then
	zgrep -Ei '(^CONFIG_(IIO|INPUT|SENSORS|MTK|MEDIATEK|BMI|BMP|HTS|STK|MMC).*=|^# CONFIG_(IIO|INPUT|SENSORS|MTK|MEDIATEK|BMI|BMP|HTS|STK|MMC) is not set)' \
		/proc/config.gz 2>/dev/null || true
fi
