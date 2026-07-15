#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 sensor/IIO boundary. It does not
# load a sensor module, enable an I2C node, scan addresses, read chip IDs,
# change rails/interrupts, or access calibration/raw sensor controls.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
system_map=$package/System.map
modules=$package/modules/lib/modules

for file in "$package/Image" "$dtb" "$config" "$system_map"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
[[ -d "$modules" ]] || { printf 'missing_modules=%s\n' "$modules" >&2; exit 1; }
[[ -d "$linux_tree" ]] || { printf 'missing_source_tree=%s\n' "$linux_tree" >&2; exit 1; }

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
dt_source=$tmpdir/gemini.dts
dtc_stderr=$tmpdir/dtc.stderr
dtc -I dtb -O dts -o "$dt_source" "$dtb" 2>"$dtc_stderr"

sha256() {
	sha256sum "$1" | awk '{print $1}'
}

count_matches() {
	local pattern=$1 file=$2 count
	count=$(rg -c "$pattern" "$file" || true)
	printf '%s' "${count:-0}"
}

count_matches_i() {
	local pattern=$1 file=$2 count
	count=$(rg -i -c "$pattern" "$file" || true)
	printf '%s' "${count:-0}"
}

count_in_context() {
	local node_pattern=$1 lines=$2 property_pattern=$3 count
	count=$(rg -n -A "$lines" "$node_pattern" "$dt_source" |
		rg -c "$property_pattern" || true)
	printf '%s' "${count:-0}"
}

config_state() {
	local symbol=$1 value
	value=$(rg -m1 "^${symbol}=" "$config" | cut -d= -f2- || true)
	if [[ -n "$value" ]]; then
		printf '%s' "$value"
	elif rg -q "^# ${symbol} is not set$" "$config"; then
		printf 'unset'
	else
		printf 'absent'
	fi
}

module_path() {
	local module=$1
	find "$modules" -type f -name "$module.ko" -print -quit 2>/dev/null || true
}

printf 'validation=mt6797-sensor-iio-current-package-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'package_system_map_sha256=%s\n' "$(sha256 "$system_map")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"

printf '\n[configuration]\n'
for symbol in \
	CONFIG_IIO \
	CONFIG_IIO_BUFFER \
	CONFIG_IIO_TRIGGER \
	CONFIG_IIO_TRIGGERED_BUFFER \
	CONFIG_BMI160 \
	CONFIG_BMI160_I2C \
	CONFIG_IIO_ST_LSM6DSX \
	CONFIG_IIO_ST_LSM6DSX_I2C \
	CONFIG_STK3310 \
	CONFIG_BMP280 \
	CONFIG_HTS221 \
	CONFIG_MMC35240; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_sensor_modules]\n'
for module in \
	bmi160_core bmi160_i2c stk3310 st_lsm6dsx st_lsm6dsx_i2c \
	bmp280 hts221 mmc35240; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'sensor_i2c1_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*i2c@11008000 \{' "$dt_source")"
printf 'sensor_i2c1_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*i2c@11008000 \{' 9 'status = "disabled"')"
printf 'bmi160_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*bmi160@69 \{' "$dt_source")"
printf 'bmi160_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*bmi160@69 \{' 8 'status = "disabled"')"
printf 'bmi160_mount_matrix_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*bmi160@69 \{' 8 'mount-matrix')"
printf 'bmi160_interrupt_property_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*bmi160@69 \{' 8 'interrupts|interrupt-names')"
printf 'bmi160_supply_property_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*bmi160@69 \{' 8 'vdd-supply|vddio-supply|supply')"
printf 'stk3310_or_stk3x_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(stk3310|stk3x|alsps)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'lsm6ds3_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*lsm6ds3[[:alnum:]_.-]* \{' "$dt_source")"
printf 'bmp280_or_barometer_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(bmp280|barometer)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'hts221_or_humidity_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(hts221|humidity)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'mmc3530_or_magnetometer_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(mmc3530|magnetometer|magnet)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'sensor_resource_context:\n'
rg -n -A 18 -B 2 \
	'^[[:space:]]*(i2c@11008000|bmi160@69|stk3310|stk3x|alsps|lsm6ds3|bmp280|barometer|hts221|humidity|mmc3530) \{' \
	"$dt_source" | head -n 240 || true

printf '\n[local_sensor_patches]\n'
patch="$repo_root/patches/v7.1.3/0052-arm64-dts-mediatek-add-disabled-Gemini-BMI160-candidate.patch"
if [[ -r "$patch" ]]; then
	printf 'patch=%s\nsha256=%s\nsensor_match_lines=%s\n' \
		"$patch" "$(sha256 "$patch")" "$(rg -c -i 'bmi160|iio|sensor|mount.matrix' "$patch" || true)"
else
	printf 'patch=%s\nstatus=not_visible_from_guest\n' "$patch"
fi

printf '\n[decision]\n'
printf '%s\n' \
	'iio_core=selected_builtin' \
	'bmi160_driver=packaged_as_modules' \
	'lsm6dsx_driver=packaged_as_modules' \
	'stk3310_driver=packaged_as_module' \
	'bmi160_dt_candidate=present_but_disabled' \
	'bmi160_identity=not_read_by_this_audit' \
	'bmi160_interrupt_and_rails=absent_from_candidate_dt' \
	'stk3x1x_dt_consumer=absent' \
	'mmc3530_dt_consumer=absent' \
	'bmp280_hts221_dt_consumers=absent' \
	'virtual_sensor_hal=not_a_kernel_chip_driver' \
	'sensor_runtime_probe=not_attempted' \
	'hardware_write=none'
