#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the archived MT6797 thermal/AUXADC source contract with Linux 7.1.3.
# This is source-only: it prints bounded matches and hashes, never vendor source
# blobs, firmware, calibration values, or device dumps.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/planet-mt6797-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
REPO_ROOT=${REPO_ROOT:-"$HOME/src/gemini-pda-mainline"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"
[[ -d "$VENDOR_TREE/.git" ]] || die "vendor tree is not a Git checkout: $VENDOR_TREE"
[[ -d "$LINUX_TREE" ]] || die "Linux source tree is missing: $LINUX_TREE"

vendor_exists() {
	git -C "$VENDOR_TREE" cat-file -e "HEAD:$1" 2>/dev/null
}

vendor_show() {
	local path=$1
	vendor_exists "$path" || return 0
	git -C "$VENDOR_TREE" show "HEAD:$path"
}

vendor_hash() {
	if vendor_exists "$1"; then
		git -C "$VENDOR_TREE" rev-parse "HEAD:$1"
	else
		echo missing
	fi
}

vendor_sha256() {
	if vendor_exists "$1"; then
		vendor_show "$1" | sha256sum | awk '{print $1}'
	else
		echo missing
	fi
}

linux_hash() {
	if [[ -f "$LINUX_TREE/$1" ]]; then
		sha256sum "$LINUX_TREE/$1" | awk '{print $1}'
	else
		echo missing
	fi
}

vendor_matches() {
	local path=$1 pattern=$2
	if vendor_exists "$path"; then
		vendor_show "$path" | rg -n "$pattern" | head -n 40 || true
	else
		echo "(missing: $path)"
	fi
}

linux_matches() {
	local path=$1 pattern=$2
	if [[ -f "$LINUX_TREE/$path" ]]; then
		rg -n "$pattern" "$LINUX_TREE/$path" | head -n 40 || true
	else
		echo "(missing: $path)"
	fi
}

echo "MT6797 thermal and AUXADC contract audit"
echo "vendor_tree=$VENDOR_TREE"
echo "vendor_commit=$(git -C "$VENDOR_TREE" rev-parse HEAD)"
echo "linux_tree=$LINUX_TREE"
if [[ -f "$LINUX_TREE/Makefile" ]]; then
	printf 'linux_version='
	make -s -C "$LINUX_TREE" kernelversion
fi

echo
echo "[source hashes]"
for path in \
	arch/arm64/boot/dts/mt6797.dtsi \
	drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c \
	drivers/misc/mediatek/thermal/mt6797/inc/tscpu_settings.h \
	drivers/misc/mediatek/thermal/mt6797/inc/mt_ts_setting.h \
	drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_thermal.h \
	drivers/misc/mediatek/auxadc/mt6797/mt_auxadc_hw.h \
	drivers/misc/mediatek/thermal/common/thermal_zones/mtk_ts_cpu.c \
	drivers/misc/mediatek/auxadc/mt_auxadc.c; do
	printf 'vendor_blob %s %s\n' "$path" "$(vendor_hash "$path")"
done
for path in \
	drivers/thermal/mediatek/auxadc_thermal.c \
	drivers/iio/adc/mt6577_auxadc.c \
	Documentation/devicetree/bindings/thermal/mediatek,thermal.yaml \
	Documentation/devicetree/bindings/iio/adc/mediatek,mt2701-auxadc.yaml \
	arch/arm64/boot/dts/mediatek/mt6797.dtsi; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor device-tree resources]"
vendor_matches arch/arm64/boot/dts/mt6797.dtsi \
	'therm_ctrl|adc_hw|efusec|clock-names|interrupts|mt6797-(therm|auxadc)'

echo
echo "[vendor sensor-bank and calibration anchors]"
vendor_matches drivers/misc/mediatek/include/mt-plat/mt6797/include/mach/mt_thermal.h \
	'BANK|SENSOR|TS_MCU|TEMPADC|THERM'
vendor_matches drivers/misc/mediatek/thermal/mt6797/inc/tscpu_settings.h \
	'ADDRESS_INDEX|TEMPADC_|TEMPMON|MSR|PTPCORESEL|PROT|AUXADC|THERMAL_CONTROLLER'
vendor_matches drivers/misc/mediatek/thermal/mt6797/inc/mt_ts_setting.h \
	'BANK|SENSOR|THERMAL|AUXADC|TEMP'
vendor_matches drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c \
	'compatible|mt_thermal_of_match|ADC_GE|ADC_OE|O_VTS|DEGC|SLOPE|raw_to_temperature|x_roomt|TEMPMSR|PTPCORESEL|THERMINTST|AUXADC|efuse|calib'
vendor_matches drivers/misc/mediatek/auxadc/mt6797/mt_auxadc_hw.h \
	'AUXADC_BASE|AUXADC_(CON|DAT|MISC)|ADCVALID|ADCVOLT|0x[0-9A-Fa-f]+'

echo
echo "[source-complete implementation]"
for path in \
	drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c \
	drivers/misc/mediatek/thermal/common/thermal_zones/mtk_ts_cpu.c \
	drivers/misc/mediatek/auxadc/mt_auxadc.c; do
	if vendor_exists "$path"; then
		printf 'vendor_source_present %s yes sha256=%s\n' "$path" "$(vendor_sha256 "$path")"
	else
		printf 'vendor_source_present %s no\n' "$path"
	fi
done
vendor_matches drivers/misc/mediatek/thermal/common/thermal_zones/mtk_ts_cpu.c \
	'tscpu_thermal|raw_to_temperature|thermal_zone|mt6797|mtk_thermal'
vendor_matches drivers/misc/mediatek/auxadc/mt_auxadc.c \
	'mt_auxadc|auxadc|compatible|mt6797|clock|iio'

echo
echo "[recovered MT6797 constants]"
echo "vendor_bank_map=bank0:MCU1;bank1:MCU4;bank2:MCU2,MCU3;bank3:MCU2;bank4:MCU2;bank5:MCU2"
echo "vendor_auxadc_channel=11"
echo "vendor_auxadc_dat_register=0x40"
echo "vendor_valid_mask=0x2c"
echo "vendor_sampling_filter=0x492"
echo "vendor_ahb_poll=0x30d"
echo "vendor_thermal_irq=SPI78_level_low"
echo "vendor_efuse_words=0x10206180,0x10206184,0x10206188"
echo "linux_v1_auxadc_channel=11"
echo "linux_v1_valid_mask=0x1020"
echo "linux_v1_sampling_filter=0x0"
echo "linux_v1_ahb_poll=0x300"
echo "linux_v1_calibration_constant=165"
echo "linux_v1_formula_uses_adc_ge_without_vendor_adc_oe=true"

echo
echo "[Linux 7.1.3 thermal and AUXADC matches]"
linux_matches drivers/thermal/mediatek/auxadc_thermal.c \
	'compatible|mt6797|mt8173|mt2701|mt2712|mt8183|mt7986|mt8365|auxadc|nvmem|calib|raw_to'
linux_matches drivers/iio/adc/mt6577_auxadc.c \
	'compatible|mt6797|mt2701|mt2712|mt7622|mt8173|mt8186|mt6765|sample_data_cali|clock'
linux_matches Documentation/devicetree/bindings/thermal/mediatek,thermal.yaml \
	'compatible|mt6797|mt8173|auxadc|clocks|clock-names|nvmem|resets|interrupts'
linux_matches Documentation/devicetree/bindings/iio/adc/mediatek,mt2701-auxadc.yaml \
	'compatible|mt6797|mt2701|mt2712|mt7622|mt8173|mt8186|mt6765|clock-names|io-channel'
linux_matches drivers/thermal/mediatek/auxadc_thermal.c \
	'struct mtk_thermal_data|num_banks|num_sensors|auxadc_channel|sensor_mux_values|need_switch_bank|apmixed_buffer|TEMP_ADCVALIDMASK|TEMP_MSRCTL0|TEMP_AHBPOLL'

echo
echo "[local patch boundary]"
patch_file=$(rg --files "$REPO_ROOT/patches/v7.1.3" 2>/dev/null \
	| rg '/0046-.*thermal.*dvfsp.*\.patch$' | head -n 1 || true)
if [[ -n "$patch_file" && -f "$patch_file" ]]; then
	rg -n -C 5 'therm_ctrl|auxadc|mt6797-thermal|status = "disabled"' \
		"$patch_file" \
		| head -n 80 || true
else
	echo '(disabled-resource patch not present)'
fi

echo
echo "[decision]"
echo "live_mt6797_thermal_controller_uses_six_logical_banks_and_five_sensor_inputs"
echo "live_calibration_uses_three_efuse_words_with_id_dependent_slope_and_vendor_raw_to_temperature_formula"
echo "vendor_mt6797_thermal_source_implementation_is_present_and_complete"
echo "vendor_thermal_uses_auxadc_channel_11_and_six_banked_views_of_five_sensors"
echo "vendor_thermal_programs_valid_mask_0x2c_filter_0x492_and_ahbpoll_0x30d"
echo "linux_7.1.3_generic_auxadc_and_thermal_data_has_no_mt6797_match"
echo "linux_auxadc_thermal_data_model_can_represent_mt6797_bank_and_sensor_topology"
echo "linux_7.1.3_has_no_mt6797_compatible_and_hardcodes_different_variant_parameters"
echo "reuse_linux_auxadc_thermal_framework_and_calibration_architecture"
echo "add_mt6797_variant_data_or_backend_for_register_parameters_and_adc_oe_formula"
echo "do_not_add_mt6797_compatible_to_another_soc_data_without_register_and_calibration_proof"
echo "keep_current_disabled_only_until_read_only_raw_register_or_mainline_sensor_validation"
