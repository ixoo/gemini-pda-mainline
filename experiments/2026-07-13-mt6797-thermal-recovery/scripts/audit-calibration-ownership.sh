#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the MT6797 thermal calibration ownership boundary. It
# compares the vendor bootloader/devinfo path with Linux NVMEM providers and
# does not print calibration values or read hardware.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
vendor_tree=${VENDOR_TREE:-/home/julien.guest/src/reference/planet-mt6797-3.18}
lk_tree=${LK_TREE:-/home/julien.guest/src/reference/dguidipc-gemini-lk-android8}
thermal_source=$linux_tree/drivers/thermal/mediatek/auxadc_thermal.c
efuse_source=$linux_tree/drivers/nvmem/mtk-efuse.c
efuse_binding=$linux_tree/Documentation/devicetree/bindings/nvmem/mediatek,efuse.yaml
thermal_dtsi=$linux_tree/arch/arm64/boot/dts/mediatek/mt6797.dtsi
thermal_dts=$linux_tree/arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts
config=$package/kernel.config

for file in "$thermal_source" "$efuse_source" "$efuse_binding" \
	"$thermal_dtsi" "$thermal_dts" "$config"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
git -C "$vendor_tree" rev-parse --verify HEAD >/dev/null
git -C "$lk_tree" rev-parse --verify HEAD >/dev/null

sha256() {
	sha256sum "$1" | awk '{print $1}'
}

git_blob_sha256() {
	git -C "$1" show "HEAD:$2" | sha256sum | awk '{print $1}'
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

vendor_anchor() {
	local path=$1 pattern=$2
	printf '\n[vendor:%s]\n' "$path"
	git -C "$vendor_tree" show "HEAD:$path" | rg -n "$pattern" || true
}

lk_anchor() {
	local path=$1 pattern=$2
	printf '\n[lk:%s]\n' "$path"
	git -C "$lk_tree" show "HEAD:$path" | rg -n "$pattern" || true
}

linux_anchor() {
	local path=$1 pattern=$2
	printf '\n[linux:%s]\n' "$path"
	rg -n "$pattern" "$path" || true
}

printf 'validation=mt6797-thermal-calibration-ownership-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'vendor_tree=%s\n' "$vendor_tree"
printf 'vendor_commit='; git -C "$vendor_tree" rev-parse HEAD
printf 'lk_tree=%s\n' "$lk_tree"
printf 'lk_commit='; git -C "$lk_tree" rev-parse HEAD
printf 'linux_version='; make -s -C "$linux_tree" kernelversion

printf '\n[linux_configuration]\n'
for symbol in CONFIG_NVMEM CONFIG_NVMEM_MTK_EFUSE CONFIG_THERMAL \
	CONFIG_THERMAL_OF CONFIG_MTK_SOC_THERMAL; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[vendor_calibration_contract]\n'
vendor_anchor drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c \
	'ADDRESS_INDEX_[012]|get_devinfo_with_index|0x1020618|ADC_GE_T|ADC_OE_T|O_VTSMCU|DEGC_cali|ADC_CALI_EN_T|O_SLOPE_SIGN|g_id'
vendor_anchor drivers/misc/mediatek/thermal/mt6797/inc/tscpu_settings.h \
	'ADDRESS_INDEX_[012]'
vendor_anchor drivers/misc/mediatek/devinfo/v1/devinfo.c \
	'devinfo_parse_dt|atag,devinfo|g_devinfo_data|memcpy|init_devinfo_exclusive'
vendor_anchor drivers/misc/mediatek/auxadc/mt_auxadc.c \
	'EFUSE_CALI|mt_auxadc_update_cali|mt_auxadc_cal_prepare|auxadc_efuse_base|of_find_compatible_node'
vendor_anchor drivers/misc/mediatek/auxadc/mt6797/mt_auxadc_hw.h \
	'EFUSE_CALI|NEW_EFUSE_CALI_REG|ADC_CALI_EN_A_REG|ADC_GE_A_REG|ADC_OE_A_REG'
printf 'vendor_calibration_word_addresses=0x10206180,0x10206184,0x10206188\n'
printf 'vendor_word_indices=31,32,33\n'
printf 'vendor_calibration_source=bootloader_atag_devinfo_payload\n'
printf 'vendor_auxadc_direct_efuse_calibration=compile_time_disabled_in_source\n'

printf '\n[lk_handoff_contract]\n'
lk_anchor lk/platform/mt6797/atags.c \
	'ATAG_DEVINFO_DATA_SIZE|target_atag_devinfo_data|get_devinfo_with_index'
lk_anchor lk/app/mt_boot/mt_boot.c \
	'target_atag_devinfo_data|fdt_setprop|atag,devinfo'
printf 'lk_payload_words=100\n'
printf 'lk_payload_property=/chosen/atag,devinfo\n'
printf 'lk_payload_contains_raw_values=no_values_printed_by_this_audit=yes\n'

printf '\n[linux_mmio_efuse_candidate]\n'
linux_anchor "$efuse_source" \
	'mtk_reg_read|mtk_efuse_probe|mt8173-efuse|mediatek,efuse|MODULE_DEVICE_TABLE|readb'
linux_anchor "$efuse_binding" \
	'mt8173-efuse|mediatek,efuse|mt6797-efuse|compatible|reg'
printf 'linux_mmio_provider_mt6797_match=absent\n'
printf 'linux_mmio_provider_read_shape=byte_read_of_mapped_resource\n'
printf 'direct_mmio_efuse_runtime_safety=unproven\n'

printf '\n[current_dt_wiring]\n'
linux_anchor "$thermal_dtsi" \
	'efusec@10206000|mediatek,efuse|adc@11001000|thermal@1100b000|nvmem-cells|calibration-data|status = "disabled"'
linux_anchor "$thermal_dts" \
	'efusec@10206000|mediatek,efuse|nvmem-cells|calibration-data|thermal|auxadc'
linux_anchor "$thermal_source" \
	'nvmem_cell_get|calibration-data|Device not calibrated|ret = 0;'
printf 'current_dt_bootloader_devinfo_consumer=absent\n'
printf 'current_dt_mmio_efuse_provider=absent\n'
printf 'current_thermal_nvmem_cell=absent\n'

printf '\n[source_hashes]\n'
for path in \
	drivers/thermal/mediatek/auxadc_thermal.c \
	drivers/nvmem/mtk-efuse.c \
	Documentation/devicetree/bindings/nvmem/mediatek,efuse.yaml \
	arch/arm64/boot/dts/mediatek/mt6797.dtsi \
	arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts; do
	printf '%s=%s\n' "$path" "$(sha256 "$linux_tree/$path")"
done
for path in \
	drivers/misc/mediatek/thermal/mt6797/src/mtk_tc.c \
	drivers/misc/mediatek/thermal/mt6797/inc/tscpu_settings.h \
	drivers/misc/mediatek/devinfo/v1/devinfo.c \
	drivers/misc/mediatek/auxadc/mt_auxadc.c \
	drivers/misc/mediatek/auxadc/mt6797/mt_auxadc_hw.h; do
	printf 'vendor:%s=%s\n' "$path" "$(git_blob_sha256 "$vendor_tree" "$path")"
done
for path in lk/platform/mt6797/atags.c lk/app/mt_boot/mt_boot.c; do
	printf 'lk:%s=%s\n' "$path" "$(git_blob_sha256 "$lk_tree" "$path")"
done

printf '\n[decision]\n'
printf '%s\n' \
	'vendor_thermal_calibration=bootloader_devinfo_words_31_32_33' \
	'lk_injects_atag_devinfo_into_final_chosen_fdt=confirmed_at_source' \
	'vendor_auxadc_efuse_mmio_reader=present_only_under_disabled_EFUSE_CALI_guard' \
	'generic_linux_mmio_efuse_provider=not_an_MT6797_match_and_not_runtime_proven' \
	'current_linux_thermal_calibration_nvmem_path=unwired' \
	'preferred_future_boundary=bootloader_backed_read_only_NVMEM_or_explicit_thermal_parser' \
	'direct_efuse_mmio_enablement=do_not_assume_from_compatible_name' \
	'thermal_nodes=disabled' \
	'hardware_write=none' \
	'runtime_mainline_boot=not_attempted'
