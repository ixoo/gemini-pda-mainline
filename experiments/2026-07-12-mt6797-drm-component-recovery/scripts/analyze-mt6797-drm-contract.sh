#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the archived MT6797 display register/platform contract with the
# prepared Linux 7.1.3 DRM tree. This script is source-only and never sends a
# panel command, changes a clock, or reads display MMIO.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/gemian-linux-kernel-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
SCRIPT_DIR=${SCRIPT_DIR:-"/mnt/gemini-pda-mainline/experiments/2026-07-12-mt6797-drm-component-recovery/scripts"}

die() {
	echo "error: $*" >&2
	exit 1
}

command -v git >/dev/null || die "git is required"
command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"

[[ -d "$VENDOR_TREE/.git" ]] || die "vendor tree is not a Git checkout: $VENDOR_TREE"
[[ -d "$LINUX_TREE" ]] || die "Linux tree is missing: $LINUX_TREE"

vendor_exists() {
	git -C "$VENDOR_TREE" cat-file -e "HEAD:$1" 2>/dev/null
}

vendor_hash() {
	if vendor_exists "$1"; then
		git -C "$VENDOR_TREE" rev-parse "HEAD:$1"
	else
		echo missing
	fi
}

vendor_show() {
	vendor_exists "$1" || return 0
	git -C "$VENDOR_TREE" show "HEAD:$1"
}

linux_hash() {
	if [[ -f "$LINUX_TREE/$1" ]]; then
		sha256sum "$LINUX_TREE/$1" | awk '{print $1}'
	else
		echo missing
	fi
}

vendor_anchor() {
	local path=$1
	local pattern=$2
	if vendor_exists "$path"; then
		vendor_show "$path" | rg -n -m 12 "$pattern" || true
	else
		echo "(missing: $path)"
	fi
}

linux_anchor() {
	local path=$1
	local pattern=$2
	if [[ -f "$LINUX_TREE/$path" ]]; then
		rg -n -m 18 "$pattern" "$LINUX_TREE/$path" || true
	else
		echo "(missing: $path)"
	fi
}

echo "MT6797 DRM component contract audit"
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
	drivers/misc/mediatek/video/mt6797/dispsys/ddp_reg.h \
	drivers/misc/mediatek/video/mt6797/dispsys/ddp_ovl.c \
	drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c \
	drivers/misc/mediatek/video/mt6797/dispsys/ddp_path.c \
	drivers/misc/mediatek/video/mt6797/dispsys/ddp_info.c; do
	printf 'vendor_blob %s %s\n' "$path" "$(vendor_hash "$path")"
done
for path in \
	drivers/gpu/drm/mediatek/mtk_disp_ovl.c \
	drivers/gpu/drm/mediatek/mtk_disp_rdma.c \
	drivers/gpu/drm/mediatek/mtk_disp_aal.c \
	drivers/gpu/drm/mediatek/mtk_disp_ccorr.c \
	drivers/gpu/drm/mediatek/mtk_disp_gamma.c \
	drivers/gpu/drm/mediatek/mtk_ddp_comp.c \
	drivers/gpu/drm/mediatek/mtk_drm_drv.c \
	drivers/gpu/drm/mediatek/mtk_dsi.c \
	drivers/phy/mediatek/phy-mtk-mipi-dsi-mt6797.c; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor fixed-function anchors]"
vendor_anchor drivers/misc/mediatek/video/mt6797/dispsys/ddp_reg.h \
	'DISP_AAL_SIZE|DISP_AAL_OUTPUT_SIZE|DISP_REG_CCORR_CFG|DISP_REG_CCORR_COEF_0|CCORR_0_FLD_CCORR_C00|DISP_REG_GAMMA_LUT|LUT_FLD_GAMMA_LUT_R|DISP_REG_DITHER_CFG|DISP_REG_DITHER_15|DISP_REG_OD_CFG|DISP_REG_OD_DITHER_15|START_FLD_DISP_UFO_BYPASS'
vendor_anchor drivers/misc/mediatek/video/mt6797/dispsys/ddp_ovl.c \
	'LAYER_SMI_ID_EN|OVL_RDMA_FIFO|FIFO|0xF40|0x20|GMC'
vendor_anchor drivers/misc/mediatek/video/mt6797/dispsys/ddp_path.c \
	'DDP_SCENARIO_PRIMARY_DISP|DISP_MODULE_OVL0|DISP_MODULE_AAL|DISP_MODULE_UFOE|DISP_MODULE_DSI0|DISP_PATH0|DISP_MODULE_PWM0'

echo
echo "[vendor DSI/MIPI-TX anchors]"
vendor_anchor drivers/misc/mediatek/video/mt6797/dispsys/ddp_reg.h \
	'MIPITX_DSI_TOP_CON|MIPITX_DSI_BG_CON|MIPITX_DSI_PLL_CON0|MIPITX_DSI_PLL_CON2|MIPITX_DSI_PLL_CHG|MIPITX_DSI_PLL_PWR|RG_DSI0_MPPLL_PREDIV|RG_DSI0_MPPLL_POSDIV|RG_DSI_MPPLL_S2QDIV|RG_DSI0_MPPLL_SDM_PCW_CHG'
vendor_anchor drivers/misc/mediatek/video/mt6797/dispsys/ddp_dsi.c \
	'pcw_ratio|S2Qdiv|RG_DSI0_MPPLL_SDM_PCW_CHG|MIPITX|0x130|lane|burst'

echo
echo "[Linux 7.1.3 platform comparison]"
linux_anchor drivers/gpu/drm/mediatek/mtk_disp_ovl.c \
	'LAYER_SMI_ID_EN|mt6797|ovl-2l|fifo|gmc|format'
linux_anchor drivers/gpu/drm/mediatek/mtk_disp_aal.c \
	'skip_output_size|default_relay|0x4d8|mt6797'
linux_anchor drivers/gpu/drm/mediatek/mtk_disp_ccorr.c \
	'matrix_bits|CCORR_RELAY_MODE|mt6797|ENGINE_EN'
linux_anchor drivers/gpu/drm/mediatek/mtk_disp_gamma.c \
	'lut_bank_size|lut_bits|lut_size|GAMMA_RELAY_MODE|mt6797'
linux_anchor drivers/gpu/drm/mediatek/mtk_ddp_comp.c \
	'no_od_dither|UFO_BYPASS|DITHER_ENGINE_EN'
linux_anchor drivers/gpu/drm/mediatek/mtk_drm_drv.c \
	'mt6797_mtk_ddp_main|mt6797-mmsys|mt6797-disp|DDP_COMPONENT_DSI0'
linux_anchor drivers/gpu/drm/mediatek/mtk_dsi.c \
	'mt6797_dsi_driver_data|reg_cmdq_off|reg_vm_cmd_off|mt6797-dsi'
linux_anchor drivers/phy/mediatek/phy-mtk-mipi-dsi-mt6797.c \
	'RG_DSI_MPPLL_PREDIV|RG_DSI_MPPLL_POSDIV|RG_DSI_MPPLL_S2QDIV|PCW_CHG|PAD_TIE_LOW|mt6797_mipitx_data'

echo
echo "[mechanical source checks]"
if command -v python3 >/dev/null 2>&1 &&
	[[ -f "$SCRIPT_DIR/check-fixed-function-contract.py" &&
	-f "$SCRIPT_DIR/check-dsi-phy-contract.py" ]]; then
	python3 "$SCRIPT_DIR/check-fixed-function-contract.py" \
		--vendor "$VENDOR_TREE" --linux "$LINUX_TREE"
	python3 "$SCRIPT_DIR/check-dsi-phy-contract.py" \
		--vendor "$VENDOR_TREE" --linux "$LINUX_TREE"
else
	echo "SKIP checker or Python unavailable"
fi

echo
echo "[decision]"
echo "Reuse Linux MT8173/MT8167 DRM component generations only where the"
echo "register contract matches. MT6797 needs dedicated OVL/OVL-2L/RDMA data,"
echo "AAL output-size suppression, relay-safe PQ defaults, 2.10 CCORR, 512x10"
echo "gamma, separate-DITHER behavior, and native MIPI-TX PLL fields. Reuse"
echo "common DRM/DSI/PHY frameworks, but do not copy vendor PQ state or enable"
echo "the panel path until the complete clock/power/reset/M4U/graph contract is"
echo "validated on hardware."
