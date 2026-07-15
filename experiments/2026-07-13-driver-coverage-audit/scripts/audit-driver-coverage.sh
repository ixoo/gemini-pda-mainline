#!/usr/bin/env bash

# Static package/live ownership comparison. This script never touches hardware.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
live_capture=${LIVE_CAPTURE:-/mnt/gemini-pda-mainline/artifacts/device-inventory/20260713-live/driver-resource-current-20260713.txt}
source_tree=${SOURCE_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
config=$package/kernel.config
system_map=$package/System.map
module_root=$package/modules/lib/modules

for file in "$config" "$system_map" "$live_capture"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done

config_state() {
	local symbol=$1
	local value
	value=$(rg -m1 "^${symbol}=" "$config" | cut -d= -f2- || true)
	printf '%s' "${value:-unset}"
}

symbol_state() {
	local symbol=$1
	if rg -q "[[:space:]]${symbol}$" "$system_map"; then
		printf builtin
	else
		printf absent-from-image
	fi
}

live_driver() {
	local pattern=$1
	local value awk_pattern
	value=$(rg -m1 "$pattern" "$live_capture" | sed -n 's/.*|driver=\([^|]*\).*/\1/p' || true)
	if [[ -z "$value" ]]; then
		# awk implementations warn about a backslash-escaped dot imported
		# through -v; use a character class for the same literal match.
		awk_pattern=${pattern//\\./[.]}
		value=$(awk -v pattern="$awk_pattern" '
			/^platform_device=/ {
				device=$0
				sub(/^platform_device=/, "", device)
				wanted=(device ~ pattern)
				next
			}
			wanted && /^platform_driver=/ {
				sub(/^platform_driver=/, "")
				print
				exit
			}
		' "$live_capture")
	fi
	printf '%s' "${value:-unbound-or-not-captured}"
}

source_hash() {
	local path=$1
	if [[ -r "$source_tree/$path" ]]; then
		sha256sum "$source_tree/$path" | awk '{print $1}'
	else
		printf missing
	fi
}

module_path() {
	local name=$1
	local path
	path=$(find "$module_root" -type f -name "$name.ko*" -print -quit 2>/dev/null || true)
	printf '%s' "${path:-absent}"
}

printf 'package=%s\n' "$package"
printf 'package_sha256=%s\n' "$(sha256sum "$package/Image" | awk '{print $1}')"
printf 'config_sha256=%s\n' "$(sha256sum "$config" | awk '{print $1}')"
printf 'dtb_sha256=%s\n' "$(sha256sum "$package/dtbs/mediatek/mt6797-gemini-pda.dtb" | awk '{print $1}')"
printf 'live_capture_sha256=%s\n' "$(sha256sum "$live_capture" | awk '{print $1}')"
printf 'modules_built=%s\n' "$(jq -er '.modules_built // false' "$package/provenance/build.json")"
printf 'module_auxadc_thermal=%s\n' "$(module_path auxadc_thermal)"
printf 'module_mt6577_auxadc=%s\n' "$(module_path mt6577_auxadc)"
printf 'module_mt6797_afe=%s\n' "$(module_path snd-soc-mt6797-afe)"
printf 'module_mt6797_mt6351=%s\n' "$(module_path mt6797-mt6351)"

printf '\n[coverage]\n'
printf 'uart|live=%s|config_SERIAL_8250_MT6577=%s|config_MTK_UART_APDMA=%s|image_mtk8250_probe=%s|decision=8250_mtk_pio_reuse_dma_deferred\n' \
	"$(live_driver '11002000\.apuart0')" "$(config_state CONFIG_SERIAL_8250_MT6577)" \
	"$(config_state CONFIG_MTK_UART_APDMA)" "$(symbol_state mtk8250_probe)"
printf 'msdc|live=%s|config_MMC_MTK=%s|image_msdc_drv_probe=%s|decision=mtk_sd_reuse_with_mt6797_data\n' \
	"$(live_driver '11230000\.msdc0')" "$(config_state CONFIG_MMC_MTK)" "$(symbol_state msdc_drv_probe)"
printf 'watchdog|live=%s|config_MEDIATEK_WATCHDOG=%s|image_mtk_wdt_probe=%s|decision=mtk_wdt_reuse\n' \
	"$(live_driver '10007000\.toprgu')" "$(config_state CONFIG_MEDIATEK_WATCHDOG)" "$(symbol_state mtk_wdt_probe)"
printf 'pinctrl|live=%s|config_PINCTRL_MT6797=%s|image_pinctrl_init=%s|decision=framework_reuse_with_mt6797_eint_data\n' \
	"$(live_driver '10005000\.pinctrl')" "$(config_state CONFIG_PINCTRL_MT6797)" "$(symbol_state mt6797_pinctrl_init)"
printf 'pmic|live_pwrap=%s|config_MTK_PMIC_WRAP=%s|config_MFD_MT6397=%s|config_REGULATOR_MT6351=%s|image_pwrap_probe=%s|image_mt6351_regulator_probe=%s|decision=upstream_pwrap_framework_plus_local_mt6351_mfd_regulator_rtc;consumers_deferred\n' \
	"$(live_driver '1000d000\.pwrap')" "$(config_state CONFIG_MTK_PMIC_WRAP)" \
	"$(config_state CONFIG_MFD_MT6397)" "$(config_state CONFIG_REGULATOR_MT6351)" \
	"$(symbol_state pwrap_probe)" "$(symbol_state mt6351_regulator_probe)"
printf 'usb|live_usb11=%s|live_usb3=%s|config_USB_MUSB_MEDIATEK=%s|config_USB_MTU3=%s|config_USB_XHCI_MTK=%s|image_mtk_musb_probe=%s|image_mtu3_probe=%s|image_xhci_mtk_probe=%s|decision=generic_core_plus_mt6797_glue_gadget_first\n' \
	"$(live_driver '11200000\.usb1')" "$(live_driver '11270000\.usb3')" \
	"$(config_state CONFIG_USB_MUSB_MEDIATEK)" "$(config_state CONFIG_USB_MTU3)" \
	"$(config_state CONFIG_USB_XHCI_MTK)" "$(symbol_state mtk_musb_probe)" \
	"$(symbol_state mtu3_probe)" "$(symbol_state xhci_mtk_probe)"
printf 'display_audio_thermal|config_DRM_MEDIATEK=%s|config_SND_SOC_MT6797=%s|config_MTK_THERMAL=%s|module_auxadc_thermal=%s|module_mt6797_afe=%s|module_mt6797_mt6351=%s|decision=build_only_until_boot_and_calibration\n' \
	"$(config_state CONFIG_DRM_MEDIATEK)" "$(config_state CONFIG_SND_SOC_MT6797)" "$(config_state CONFIG_MTK_THERMAL)" \
	"$(module_path auxadc_thermal)" "$(module_path snd-soc-mt6797-afe)" "$(module_path mt6797-mt6351)"
printf 'fabric|live_m4u=%s|live_gce=%s|config_MTK_IOMMU=%s|config_MTK_SMI=%s|config_MTK_CMDQ=%s|config_MTK_MMSYS=%s|image_mtk_iommu_probe=%s|image_mtk_smi_larb_probe=%s|decision=framework_reuse_consumer_by_consumer\n' \
	"$(live_driver '10205000\.m4u')" "$(live_driver '10212000\.gce')" \
	"$(config_state CONFIG_MTK_IOMMU)" "$(config_state CONFIG_MTK_SMI)" \
	"$(config_state CONFIG_MTK_CMDQ)" "$(config_state CONFIG_MTK_MMSYS)" \
	"$(symbol_state mtk_iommu_probe)" "$(symbol_state mtk_smi_larb_probe)"
printf 'deferred_vendor_abi|live_wmt=%s|live_ccci=%s|live_camera=%s|config_MTK_SCP=%s|decision=new_transport_or_firmware_boundary_deferred\n' \
	"$(live_driver '18070000\.consys')" "$(live_driver '10014000\.mdcldma')" \
	"$(live_driver '15000000\.imgsys_config')" "$(config_state CONFIG_MTK_SCP)"

printf '\n[source_hashes]\n'
for path in \
	drivers/tty/serial/8250/8250_mtk.c \
	drivers/mmc/host/mtk-sd.c \
	drivers/watchdog/mtk_wdt.c \
	drivers/mfd/mt6397-core.c \
	drivers/regulator/mt6351-regulator.c \
	drivers/usb/musb/mediatek.c \
	drivers/usb/mtu3/mtu3_plat.c \
	drivers/usb/host/xhci-mtk.c \
	drivers/iommu/mtk_iommu.c \
	drivers/memory/mtk-smi.c \
	drivers/thermal/mediatek/auxadc_thermal.c \
	sound/soc/mediatek/mt6797/mt6797-afe-pcm.c; do
	printf '%s=%s\n' "$path" "$(source_hash "$path")"
done

printf '\nvalidation=driver-coverage-static-live-correlation\n'
printf 'runtime_mainline_boot=not_attempted\n'
printf 'hardware_write=none\n'
