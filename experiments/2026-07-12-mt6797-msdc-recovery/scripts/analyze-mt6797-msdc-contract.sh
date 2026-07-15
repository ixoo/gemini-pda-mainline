#!/usr/bin/env bash

# Emit the MT6797 MSDC contract without copying vendor code into the
# repository. Vendor files are read from Git objects because the reference
# checkout may be sparse. This report is source-only and never touches a card,
# tuning register, clock, or regulator.

set -euo pipefail
export LC_ALL=C

vendor_tree=${1:-${HOME}/src/reference/planet-mt6797-3.18}
linux_tree=${2:-${HOME}/src/gemini-pda/linux-7.1.3}
vendor_files=(
	drivers/mmc/host/mediatek/mt6797/msdc_reg.h
	drivers/mmc/host/mediatek/mt6797/msdc_io.c
	drivers/mmc/host/mediatek/mt6797/msdc_io.h
	drivers/mmc/host/mediatek/mt6797/msdc_tune.c
	drivers/mmc/host/mediatek/mt6797/sd.c
	drivers/mmc/host/mediatek/mt6797/mt_sd.h
	drivers/mmc/host/mediatek/mt6797/dbg.c
	arch/arm64/boot/dts/mt6797.dtsi
)
linux_files=(
	drivers/mmc/host/mtk-sd.c
	Documentation/devicetree/bindings/mmc/mtk-sd.yaml
)

[[ -d "${vendor_tree}/.git" ]] || {
	printf 'vendor tree is not a Git checkout: %s\n' "${vendor_tree}" >&2
	exit 1
}
[[ -r "${linux_tree}/drivers/mmc/host/mtk-sd.c" ]] || {
	printf 'Linux mtk-sd sources are missing below: %s\n' "${linux_tree}" >&2
	exit 1
}

vendor_show() {
	git -C "${vendor_tree}" show "HEAD:$1"
}

blob_hash() {
	local path=$1
	vendor_show "${path}" | sha256sum | awk '{print $1}'
}

printf 'vendor_tree=%s\n' "${vendor_tree}"
printf 'vendor_commit=%s\n' "$(git -C "${vendor_tree}" rev-parse HEAD)"
for path in "${vendor_files[@]}"; do
	printf 'vendor_blob_sha256[%s]=%s\n' "${path}" "$(blob_hash "${path}")"
done
printf 'linux_tree=%s\n' "${linux_tree}"
printf 'linux_revision=7.1.3 (prepared source; no Git metadata required)\n'
for path in "${linux_files[@]}"; do
	printf 'linux_blob_sha256[%s]=%s\n' "${path}" "$(sha256sum "${linux_tree}/${path}" | awk '{print $1}')"
done

printf '\n[vendor register contract]\n'
vendor_show "${vendor_files[0]}" |
	grep -nE 'OFFSET_MSDC_(CFG|DMA_SA_HIGH|DMA_SA|DMA_CA|DMA_CTRL|DMA_CFG|DMA_LEN|PATCH_BIT[0-2]|PAD_TUNE[01])|MSDC_CFG_(CKDIV|CKMOD_HS400)|MSDC_EMMC50_BLOCK_LENGTH|SDC_(FIFO_CFG|ADV_CFG0)' |
	head -n 220 || true
vendor_show "${vendor_files[5]}" |
	grep -nE 'HOST_MAX_MCLK|SUPPORT64G|STOP_CLK|ENHANCE|ASYNC|DATA_TUNE|PAD_TUNE|PATCH_BIT|CLK' |
	head -n 180 || true

printf '\n[vendor DT and controller setup]\n'
vendor_show "${vendor_files[7]}" |
	grep -nE -A22 -B3 'msdc0|msdc1|11230000|11240000|CLK_INFRA_MSDC|MSDC50|MSDC30|clock-names|bus-width|non-removable|cap-' |
	head -n 220 || true
vendor_show "${vendor_files[4]}" |
	grep -nE 'MSDC_(CFG|PATCH|PAD_TUNE|EMMC50|DMA)|clk|clock|support|64g|tune|HS400|busy|enhance|stop' |
	head -n 180 || true

printf '\n[Linux compatibility data]\n'
grep -nE -A16 -B2 'static const struct mtk_mmc_compatible mt6795_compat|mt6797_compat|mediatek,mt6797-mmc' \
	"${linux_tree}/drivers/mmc/host/mtk-sd.c" |
	head -n 180 || true
grep -nE 'mediatek,mt6797-mmc|clock-names|source_cg|vmmc-supply|vqmmc-supply|bus-width|cap-' \
	"${linux_tree}/Documentation/devicetree/bindings/mmc/mtk-sd.yaml" |
	head -n 180 || true

printf '\n[decision]\n'
printf '%s\n' \
	'MT6797 uses the existing Linux mtk-sd protocol with a distinct compatibility record; a new storage controller driver is not indicated.' \
	'Use 12-bit clock divider, PAD_TUNE0, asynchronous FIFO, and data tuning; keep stop_clk_fix and enhance_rx disabled because 0x228 is EMMC50_BLOCK_LENGTH and SDC_ADV_CFG0 is absent.' \
	'Keep support_64g disabled until descriptor high-address use is proven; the downstream driver truncates descriptors and the live high-address register is zero.' \
	'Reuse Linux MMC core, mtk-sd, regulator, and pinctrl layers; the first Gemini board path remains conservative eMMC legacy timing with no HS200/HS400 flags.' \
	'Keep MSDC1 and voltage switching disabled until card-detect polarity, VMCH/VMC rails, pin drive, and removable-card behavior are validated.'
