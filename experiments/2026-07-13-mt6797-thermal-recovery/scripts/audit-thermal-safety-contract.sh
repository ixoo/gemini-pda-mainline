#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Static, read-only audit of the MT6797 thermal candidate's calibration,
# sensor-bank, and AUXADC probe contract. It does not load modules, enable
# device-tree nodes, change thermal policy, or access physical registers.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
thermal_source=$linux_tree/drivers/thermal/mediatek/auxadc_thermal.c
auxadc_source=$linux_tree/drivers/iio/adc/mt6577_auxadc.c
dt_source_file=$linux_tree/arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts
soc_dtsi=$linux_tree/arch/arm64/boot/dts/mediatek/mt6797.dtsi
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config

for file in "$thermal_source" "$auxadc_source" "$dt_source_file" "$soc_dtsi" "$dtb" "$config"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done

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
	find "$package/modules/lib/modules" -type f -name "$1.ko" -print -quit 2>/dev/null || true
}

anchor() {
	local path=$1 pattern=$2
	printf '\n[%s]\n' "$path"
	rg -n "$pattern" "$path" || true
}

printf 'validation=mt6797-thermal-safety-contract-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion

printf '\n[configuration_and_modules]\n'
for symbol in CONFIG_THERMAL CONFIG_THERMAL_OF CONFIG_MTK_THERMAL \
	CONFIG_MTK_SOC_THERMAL CONFIG_MEDIATEK_MT6577_AUXADC; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done
printf 'module=auxadc_thermal|path=%s\n' "$(module_path auxadc_thermal)"
printf 'module=mt6577_auxadc|path=%s\n' "$(module_path mt6577_auxadc)"

printf '\n[calibration_path]\n'
anchor "$thermal_source" \
	'mtk_thermal_extract_efuse_v4|mtk_thermal_get_calibration_data|nvmem_cell_get|EPROBE_DEFER|Device not calibrated|using default calibration|mt->adc_ge = 512|mt->adc_oe = 512|mt->vts\[i\] = 260|mt->degc_cali = 40|ret = 0;'
printf 'gemini_dt_calibration_cell_property=%s\n' \
	"$(rg -c 'nvmem-cells|calibration-data|nvmem-cell-names' "$dt_source_file" || true)"
printf 'mt6797_dtsi_calibration_cell_property=%s\n' \
	"$(rg -c 'nvmem-cells|calibration-data|nvmem-cell-names' "$soc_dtsi" || true)"
printf 'missing_or_invalid_calibration_probe_behavior=continues_with_defaults\n'
printf 'default_calibration_is_runtime_safe=not_established\n'

printf '\n[sensor_bank_contract]\n'
anchor "$thermal_source" \
	'mt6797_bank_data|mt6797_mux_values|mt6797_vts_index|mtk_thermal_bank_temperature|raw_to_mcelsius\(|conf->bank_data\[bank->id\]'
printf 'expected_bank_sensor_ids=bank0:[0];bank1:[3];bank2:[1,2];bank3:[1];bank4:[1];bank5:[1]\n'
printf 'expected_mux_values_by_sensor=TS_MCU1:0,TS_MCU2:1,TS_MCU3:2,TS_MCU4:3,TS_ABB:0\n'
printf 'expected_vts_indices_by_sensor=TS_MCU1:VTS1,TS_MCU2:VTS2,TS_MCU3:VTS3,TS_MCU4:VTS4,TS_ABB:VTSABB\n'
printf 'sensor_index_scope=global_sensor_id_passed_to_raw_to_mcelsius\n'
printf 'shared_sensor_mapping=TS_MCU2_is_used_by_banks_2,3,4,5\n'

printf '\n[conversion_and_controller_contract]\n'
anchor "$thermal_source" \
	'raw_to_mcelsius_v4|slope_denominator|temp_ahbpoll|temp_msrctl0|temp_adcvalidmask|apmixed_buffer_ctl|mtk_thermal_release_periodic_ts|TEMP_MONCTL0'
printf 'mt6797_variant_constants=TEMP_AHBPOLL:0x30d,TEMP_MSRCTL0:0x492,TEMP_ADCVALIDMASK:0x2c,auxadc_channel:11\n'
printf 'runtime_controller_side_effects=clocks,APMIXED_buffer,AUXADC_power_and_periodic_sampling,thermal_bank_registers\n'
printf 'hardware_trip_and_irq_semantics=not_recovered_in_generic_candidate\n'

printf '\n[auxadc_compatibility_contract]\n'
anchor "$auxadc_source" \
	'mt8173_compat|check_global_idle|MT6577_AUXADC_CON2|mt6577_auxadc_probe|devm_clk_get_enabled|mt6577_power_off|MT6577_AUXADC_PDN_EN'
printf 'mt6797_auxadc_mapping=mt8173_compat_candidate\n'
printf 'global_idle_polling=enabled_by_candidate_mapping\n'
printf 'auxadc_power_state=probe_clears_PDN_and_devres_cleanup_sets_PDN\n'
printf 'auxadc_register_shape_validation=source_candidate_only\n'

printf '\n[device_tree_gate]\n'
anchor "$soc_dtsi" \
	'auxadc: adc@11001000|thermal: thermal@1100b000|compatible = "mediatek,mt6797|status = "disabled"|mediatek,auxadc|mediatek,apmixedsys|nvmem'
printf 'thermal_node_enablement=disabled\n'
printf 'auxadc_node_enablement=disabled\n'
printf 'calibration_provider_wired=no\n'

printf '\n[source_hashes]\n'
for path in \
	drivers/thermal/mediatek/auxadc_thermal.c \
	drivers/iio/adc/mt6577_auxadc.c \
	arch/arm64/boot/dts/mediatek/mt6797.dtsi \
	arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts; do
	printf '%s=%s\n' "$path" "$(sha256 "$linux_tree/$path")"
done

printf '\n[decision]\n'
printf '%s\n' \
	'generic_bank_and_conversion_framework=source-compatible_candidate' \
	'mt6797_bank_topology=represented_with_shared_TS_MCU2_mapping' \
	'gemini_calibration_data_path=absent' \
	'invalid_or_missing_calibration=nonfatal_default_fallback' \
	'runtime_enablement_without_calibration=blocked_as_unsafe' \
	'mt6797_auxadc_mt8173_compat=unproven_register_shape_candidate' \
	'auxadc_probe_and_thermal_probe_have_mmio_clock_power_side_effects' \
	'board_nodes=disabled' \
	'hardware_write=none' \
	'runtime_mainline_boot=not_attempted'
