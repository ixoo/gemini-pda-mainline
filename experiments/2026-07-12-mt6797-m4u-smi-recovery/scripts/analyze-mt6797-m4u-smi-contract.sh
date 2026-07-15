#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the archived MT6797 M4U/SMI source contract with the prepared
# Linux 7.1.3 tree.  The analyzer reads source and Git metadata only; it does
# not copy vendor code, access MMIO, or exercise a multimedia consumer.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/gemian-linux-kernel-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
PORT_CHECKER=${PORT_CHECKER:-"/mnt/gemini-pda-mainline/experiments/2026-07-12-mt6797-m4u-smi-recovery/scripts/compare-port-table.py"}

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
		vendor_show "$path" | rg -n -m 6 "$pattern" || true
	else
		echo "(missing: $path)"
	fi
}

linux_anchor() {
	local path=$1
	local pattern=$2
	if [[ -f "$LINUX_TREE/$path" ]]; then
		rg -n -m 12 "$pattern" "$LINUX_TREE/$path" || true
	else
		echo "(missing: $path)"
	fi
}

echo "MT6797 M4U/SMI contract audit"
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
	drivers/misc/mediatek/m4u/mt6797/m4u_platform.h \
	drivers/misc/mediatek/m4u/mt6797/m4u_hw.c \
	drivers/misc/mediatek/m4u/mt6797/m4u_hw.h \
	drivers/misc/mediatek/m4u/mt6797/m4u_reg.h \
	drivers/misc/mediatek/m4u/mt6797/m4u_port.h \
	drivers/misc/mediatek/m4u/2.0/m4u_debug.c \
	drivers/misc/mediatek/smi/smi_common.c \
	drivers/misc/mediatek/smi/smi_configuration.c \
	drivers/misc/mediatek/smi/variant/smi_variant.c \
	drivers/misc/mediatek/smi/variant/smi_reg.h; do
	printf 'vendor_blob %s %s\n' "$path" "$(vendor_hash "$path")"
done
for path in \
	drivers/iommu/mtk_iommu.c \
	drivers/memory/mtk-smi.c \
	Documentation/devicetree/bindings/iommu/mediatek,iommu.yaml \
	Documentation/devicetree/bindings/memory-controllers/mediatek,smi-common.yaml \
	Documentation/devicetree/bindings/memory-controllers/mediatek,smi-larb.yaml \
	include/dt-bindings/memory/mt6797-larb-port.h; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor port topology]"
if vendor_exists drivers/misc/mediatek/m4u/mt6797/m4u_platform.h; then
	vendor_show drivers/misc/mediatek/m4u/mt6797/m4u_platform.h |
		awk -F'[(),]' '
			/M4U0_PORT_INIT\("/ && $0 !~ /UNKNOWN/ {
				count++;
				slave = $3 + 0;
				larb = $4 + 0;
				port = $5 + 0;
				if (slave == 0) slave0++;
				if (slave == 1) slave1++;
				if (larb > max_larb) max_larb = larb;
				if (port > max_port) max_port = port;
			}
			END {
				printf "ports=%d slave0=%d slave1=%d max_larb=%d max_port=%d\n",
					count, slave0, slave1, max_larb, max_port;
			}'
	vendor_anchor drivers/misc/mediatek/m4u/mt6797/m4u_platform.h \
		'M4U0_PORT_INIT|\(\(larb\)<<7\)|gM4U_SMILARB'
else
	echo "(missing vendor port table)"
fi

echo
echo "[vendor M4U register contract]"
vendor_anchor drivers/misc/mediatek/m4u/mt6797/m4u_reg.h \
	'M4U_BASE0|LARB[0-6]_BASE|REG_INVLID_SEL|REG_MMU_STANDARD_AXI_MODE|REG_MMU_DCM_DIS|REG_MMU_WR_LEN|REG_MMU_MMU_COHERENCE_EN|REG_MMU_IN_ORDER_WR_EN|REG_MMU_MMU_TABLE_WALK_DIS|SMI_LARB_MMU_EN|REG_MMU_CTRL'
vendor_anchor drivers/misc/mediatek/m4u/mt6797/m4u_reg.h \
	'^#define[[:space:]]+SMI_LARB_MMU_EN'
vendor_anchor drivers/misc/mediatek/m4u/mt6797/m4u_hw.c \
	'F_MMU_INV|m4uHw_set_field_by_mask|REG_MMU_COHERENCE|REG_MMU_IN_ORDER|REG_MMU_TABLE|REG_MMU_WR_LEN|SMI_LARB_MMU_EN|m4u_larb_clock'
vendor_anchor drivers/misc/mediatek/m4u/mt6797/m4u_hw.h \
	'TOTAL_M4U_NUM|M4U_SLAVE_NUM|M4U0_MAU_NR|M4U_PGSIZES|larb_id|larb_port'

echo
echo "[vendor SMI contract]"
vendor_anchor drivers/misc/mediatek/smi/variant/smi_reg.h \
	'SMI_LARB_MMU_EN|REG_OFFSET_SMI_L1ARB|REG_SMI_L1ARB|SMI_COMMON_EXT_BASE|SMI_LARB_OSTDL'
vendor_anchor drivers/misc/mediatek/smi/variant/smi_reg.h \
	'^#define[[:space:]]+SMI_LARB_MMU_EN'
vendor_anchor drivers/misc/mediatek/smi/smi_common.c \
	'get_larb_base_addr|larb_base|larb_nr|SMI_LARB_CON|SMI_LARB_OSTDL|0x200|0x2c'
vendor_anchor drivers/misc/mediatek/smi/smi_configuration.c \
	'SMI_LARB[0-9]_PORT_NUM|REG_OFFSET_SMI_L1ARB|SMI_SETTING|0x234|0x220'

echo
echo "[Linux 7.1.3 comparison]"
echo "MT6797 IOMMU platform data:"
linux_anchor drivers/iommu/mtk_iommu.c \
	'MT6797|mt6797_data|HAS_LEGACY_MMU_MISC|REG_MMU_COHERENCE_EN|REG_MMU_IN_ORDER_WR_EN|REG_MMU_TABLE_WALK_DIS|HAS_BCLK|TF_PORT_TO_ADDR_MT8173'
echo "MT6797 SMI platform data and reused larb register generation:"
linux_anchor drivers/memory/mtk-smi.c \
	'mt6797|mtk_smi_common_mt6797|F_MMU1_LARB|mtk_smi_larb_mt8167|MT8167_SMI_LARB_MMU_EN|MT8173_SMI_LARB_MMU_EN|config_port'
echo "binding coverage:"
linux_anchor Documentation/devicetree/bindings/iommu/mediatek,iommu.yaml \
	'mt6797|larb-port'
linux_anchor Documentation/devicetree/bindings/memory-controllers/mediatek,smi-common.yaml \
	'mt6797'
linux_anchor Documentation/devicetree/bindings/memory-controllers/mediatek,smi-larb.yaml \
	'mt6797'

echo
echo "[mechanical port comparison]"
vendor_port="$VENDOR_TREE/drivers/misc/mediatek/m4u/mt6797/m4u_platform.h"
linux_header="$LINUX_TREE/include/dt-bindings/memory/mt6797-larb-port.h"
if [[ -f "$PORT_CHECKER" && -f "$linux_header" && -f "$vendor_port" ]] &&
	command -v python3 >/dev/null 2>&1; then
	python3 "$PORT_CHECKER" "$vendor_port" "$linux_header"
else
	echo "SKIP checker or source/header unavailable"
fi

echo
echo "[decision]"
echo "Reuse the Linux generation-two IOMMU/SMI frameworks, but retain a"
echo "dedicated MT6797 platform record: one M4U, seven larbs, legacy INV_SEL"
echo "and MMU-misc writes, 4-GiB remapping, no bclk, and the generic fault"
echo "protection field. Reuse the MT8167 SMI larb register helper (0xfc0),"
echo "not the MT8173 helper (0xf00). Keep all fabric nodes disabled until one"
echo "consumer has independently verified clocks, power, reset, M4U port, and"
echo "DMA behavior. Do not attach a GPU iommus property by analogy."
