#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 thermal/AUXADC implementation.  It
# does not load a module, enable a DT node, change a thermal policy, or access
# a physical register.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
live_capture=/mnt/gemini-pda-mainline/artifacts/device-inventory/20260714-live/thermal-auxadc.txt
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
system_map=$package/System.map
modules=$package/modules/lib/modules

for file in "$dtb" "$config" "$system_map"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
[[ -d "$linux_tree" ]] || { printf 'missing_source_tree=%s\n' "$linux_tree" >&2; exit 1; }

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
dt_source=$tmpdir/gemini.dts
dtc_stderr=$tmpdir/dtc.stderr
dtc -I dtb -O dts -o "$dt_source" "$dtb" 2>"$dtc_stderr"

sha256() {
	sha256sum "$1" | awk '{print $1}'
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

image_state() {
	local symbol=$1 module=$2
	if rg -q "[[:space:]]${symbol}$" "$system_map"; then
		printf 'builtin'
	elif [[ -n "$(module_path "$module")" ]]; then
		printf 'module'
	else
		printf 'absent-from-package'
	fi
}

source_hash() {
	local path=$1
	sha256 "$linux_tree/$path"
}

anchor() {
	local path=$1 pattern=$2
	printf '\n[%s]\n' "$path"
	rg -n "$pattern" "$linux_tree/$path" | tail -n 35 || true
}

printf 'validation=mt6797-thermal-current-package-policy-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"
if [[ -r "$live_capture" ]]; then
	printf 'live_capture=%s\n' "$live_capture"
	printf 'live_capture_sha256=%s\n' "$(sha256 "$live_capture")"
else
	printf 'live_capture=absent\n'
fi

printf '\n[configuration_and_image]\n'
for symbol in \
	CONFIG_THERMAL \
	CONFIG_THERMAL_OF \
	CONFIG_MTK_THERMAL \
	CONFIG_MTK_SOC_THERMAL \
	CONFIG_MEDIATEK_MT6577_AUXADC; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done
printf 'probe_symbol=mtk_thermal_probe|image=%s\n' \
	"$(image_state mtk_thermal_probe auxadc_thermal)"
printf 'probe_symbol=mt6577_auxadc_probe|image=%s\n' \
	"$(image_state mt6577_auxadc_probe mt6577_auxadc)"
printf 'module=auxadc_thermal|path=%s\n' "$(module_path auxadc_thermal)"
printf 'module=mt6577_auxadc|path=%s\n' "$(module_path mt6577_auxadc)"

printf '\n[device_tree]\n'
for node in adc@11001000 thermal@1100b000; do
	printf 'node=%s\n' "$node"
	rg -n -A 15 -B 1 "^\s*${node//./\\.} \{" "$dt_source" | sed -n '1,24p'
done

printf '\n[live_contract]\n'
if [[ -r "$live_capture" ]]; then
	printf 'live_disabled_zone_lines=%s\n' \
		"$(rg -c 'mode=disabled' "$live_capture" || true)"
	printf 'live_zone_lines=%s\n' \
		"$(rg -c '^zone=' "$live_capture" || true)"
	rg -m 1 '^current temp:' "$live_capture" || true
	rg -m 1 '^\[cal\] g_adc_ge_t' "$live_capture" || true
	rg -m 1 '^\[cal\] g_adc_oe_t' "$live_capture" || true
	rg -m 1 '^\[cal\] g_degc_cali' "$live_capture" || true
	rg -m 1 '^110:.*mtk-thermal' "$live_capture" || true
	rg -m 1 '^clock=infra_therm' "$live_capture" || true
fi

printf '\n[probe_policy_anchors]\n'
anchor drivers/thermal/mediatek/auxadc_thermal.c \
	'mtk_thermal_get_calibration_data|mtk_thermal_release_periodic_ts|mtk_thermal_turn_on_buffer|mtk_thermal_init_bank|mtk_thermal_probe|raw_to_mcelsius_v4|MTK_THERMAL_V4'
anchor drivers/iio/adc/mt6577_auxadc.c \
	'mt6577_auxadc_probe|devm_clk_get_enabled|mt6577_power_off|mt6577_auxadc_of_match'
anchor drivers/thermal/mediatek/Makefile 'MTK_SOC_THERMAL'

printf '\n[source_hashes]\n'
for path in \
	drivers/thermal/mediatek/auxadc_thermal.c \
	drivers/thermal/mediatek/Makefile \
	drivers/thermal/mediatek/Kconfig \
	drivers/iio/adc/mt6577_auxadc.c \
	Documentation/devicetree/bindings/thermal/mediatek,thermal.yaml \
	Documentation/devicetree/bindings/iio/adc/mediatek,mt2701-auxadc.yaml \
	arch/arm64/boot/dts/mediatek/mt6797.dtsi \
	arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts; do
	printf '%s=%s\n' "$path" "$(source_hash "$path")"
done

printf '\n[decision]\n'
printf '%s\n' \
	'reuse_generic_mtk_thermal_framework=confirmed_at_source_and_data_model' \
	'mt6797_variant_data_and_formula=required' \
	'package_thermal_driver_present_only_when_CONFIG_MTK_SOC_THERMAL_is_set' \
	'gemini_thermal_and_auxadc_nodes=disabled' \
	'probe_writes_clocks_auxadc_buffer_and_thermal_registers_if_node_is_enabled' \
	'live_vendor_zones_are_disabled_and_do_not_validate_mainline_runtime' \
	'calibration_efuse_provider_and_runtime_reading=unproven' \
	'hardware_write=none' \
	'runtime_mainline_boot=not_attempted'
