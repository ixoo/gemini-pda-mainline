#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 charger/fuel-gauge boundary. It does
# not load a charger or regulator module, enable an I2C node, scan addresses,
# read charger IDs, change rails/current/voltage, or alter charge state.

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

printf 'validation=mt6797-charger-current-package-audit\n'
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
	CONFIG_POWER_SUPPLY \
	CONFIG_CHARGER_BQ25890 \
	CONFIG_REGULATOR_FAN49101 \
	CONFIG_REGULATOR_FAN53555 \
	CONFIG_CHARGER_RT9467 \
	CONFIG_CHARGER_RT9466 \
	CONFIG_BATTERY_BQ27XXX \
	CONFIG_BATTERY_BQ27XXX_I2C \
	CONFIG_BATTERY_MAX17042 \
	CONFIG_IIO \
	CONFIG_MTK_PMIC_WRAP; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_charger_modules]\n'
for module in \
	bq25890_charger fan49101 bq27xxx_battery max17042_battery \
	rt9467_charger fan53555; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'charger_i2c0_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*i2c@11007000 \{' "$dt_source")"
printf 'charger_i2c0_and_child_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*i2c@11007000 \{' 18 'status = "disabled"')"
printf 'fan49101_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*regulator@70 \{' "$dt_source")"
printf 'fan49101_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*regulator@70 \{' 8 'status = "disabled"')"
printf 'fan49101_regulator_child_matches=%s\n' \
	"$(count_matches '^[[:space:]]*vout \{' "$dt_source")"
printf 'bq25890_or_sw_charger_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(bq25890|sw_charger)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'rt9466_or_primary_charger_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(rt9466|primary_charger)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'battery_power_supply_node_matches=%s\n' \
	"$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(battery|fuel|power-supply)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'charger_resource_context:\n'
rg -n -A 24 -B 2 \
	'^[[:space:]]*(i2c@11007000|regulator@70|vout|bq25890|sw_charger|rt9466|primary_charger|battery|fuel) \{' \
	"$dt_source" | head -n 260 || true

printf '\n[source_contract]\n'
printf 'charger_source_audit=experiments/2026-07-12-charger-power-recovery/results/mt6797-charger-source-audit.txt\n'
printf 'bq25890_reuse_audit=experiments/2026-07-12-charger-power-recovery/results/bq25890-reuse-audit-20260713.txt\n'
printf 'fan49101_contract=experiments/2026-07-12-charger-power-recovery/results/fan49101-register-contract.txt\n'
printf 'vendor_bq_identity_gate=register_0x03_nonzero_only\n'
printf 'linux_bq_identity_gate=register_0x14_PN_and_DEV_REV\n'
printf 'vendor_fan_identity_gate=dedicated_manufacturer_and_die_ID_registers\n'

printf '\n[local_charger_patches]\n'
patch="$repo_root/patches/v7.1.3/0055-regulator-add-FAN49101-buck-boost-driver-and-Gemini-node.patch"
if [[ -r "$patch" ]]; then
	printf 'patch=%s\nsha256=%s\ncharger_match_lines=%s\n' \
		"$patch" "$(sha256 "$patch")" "$(rg -c -i 'fan49101|regulator|charger|battery|vout' "$patch" || true)"
else
	printf 'patch=%s\nstatus=not_visible_from_guest\n' "$patch"
fi

printf '\n[decision]\n'
printf '%s\n' \
	'power_supply_core=selected_builtin' \
	'bq25890_driver=packaged_as_module_but_no_gemini_dt_consumer' \
	'fan49101_driver=packaged_as_module_with_disabled_gemini_node' \
	'fan53555_driver=packaged_but_not_protocol_equivalent' \
	'rt9467_driver=not_selected' \
	'rt9466_consumer=absent_from_package_dtb' \
	'bq27xxx_battery_core=packaged_builtin_without_board_consumer' \
	'charger_runtime_probe=not_attempted' \
	'charge_control=not_attempted' \
	'hardware_write=none'
