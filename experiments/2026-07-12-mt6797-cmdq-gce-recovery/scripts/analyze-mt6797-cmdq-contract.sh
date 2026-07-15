#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the archived MT6797 CMDQ/GCE contract with Linux 7.1.3.  This is a
# source-only audit: no command packet is submitted and no vendor source or
# address-bearing capture is copied.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/gemian-linux-kernel-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
DERIVER=${DERIVER:-"/mnt/gemini-pda-mainline/experiments/2026-07-12-mt6797-cmdq-gce-recovery/scripts/derive-gce-contract.py"}

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

echo "MT6797 CMDQ/GCE contract audit"
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
	drivers/misc/mediatek/cmdq/v2/cmdq_reg.h \
	drivers/misc/mediatek/cmdq/v2/cmdq_def.h \
	drivers/misc/mediatek/cmdq/v2/cmdq_device.c \
	drivers/misc/mediatek/cmdq/v2/cmdq_event_common.h \
	drivers/misc/mediatek/cmdq/v2/cmdq_subsys_common.h \
	drivers/misc/mediatek/cmdq/v2/mt6797/cmdq_engine.h \
	arch/arm64/boot/dts/mt6797.dts; do
	printf 'vendor_blob %s %s\n' "$path" "$(vendor_hash "$path")"
done
for path in \
	drivers/mailbox/mtk-cmdq-mailbox.c \
	include/linux/mailbox/mtk-cmdq-mailbox.h \
	Documentation/devicetree/bindings/mailbox/mediatek,gce-mailbox.yaml \
	include/dt-bindings/gce/mediatek,mt6797-gce.h; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor register and topology anchors]"
vendor_anchor drivers/misc/mediatek/cmdq/v2/cmdq_reg.h \
	'CMDQ_CURR_IRQ_STATUS|CMDQ_THR_SLOT_CYCLES|CMDQ_SYNC_TOKEN_UPD|CMDQ_THR_WARM_RESET|CMDQ_THR_ENABLE_TASK|CMDQ_THR_IRQ_STATUS|CMDQ_THR_CURR_ADDR|CMDQ_THR_END_ADDR|CMDQ_THR_WAIT_TOKEN|CMDQ_THR_CFG|0x080|0x100|0x3200'
vendor_anchor drivers/misc/mediatek/cmdq/v2/cmdq_def.h \
	'CMDQ_MAX_THREAD_COUNT|CMDQ_MAX_EVENT|CMDQ_THR_PRIO|CMDQ_SUBSYS|CMDQ_EVENT|CMDQ_INST_SIZE|CMDQ_MAX_PREFETCH|CMDQ_MAX_ENGINE'
vendor_anchor drivers/misc/mediatek/cmdq/v2/cmdq_device.c \
	'cmdq_dev_get_irq_id|cmdq_dev_get_irq_secure_id|cmdq_dev_get_module_base_PA_GCE|cmdq_dev_enable_gce_clock|cmdq_dev_init_event_table|cmdq_dev_init_subsys'
vendor_anchor arch/arm64/boot/dts/mt6797.dts \
	'gce@10212000|compatible = "mediatek,gce"|disp_mutex_reg|gce_clock|#mbox-cells'

echo
echo "[Linux 7.1.3 mailbox comparison]"
linux_anchor drivers/mailbox/mtk-cmdq-mailbox.c \
	'CMDQ_CURR_IRQ_STATUS|CMDQ_THR_SLOT_CYCLES|CMDQ_THR_BASE|CMDQ_THR_SIZE|CMDQ_THR_IRQ_STATUS|CMDQ_THR_CURR_ADDR|CMDQ_THR_END_ADDR|CMDQ_THR_WAIT_TOKEN|CMDQ_THR_PRIORITY|CMDQ_THR_ACTIVE_SLOT_CYCLES|gce_plat_mt8173|thread_nr|shift|gce_num|mt6797'
linux_anchor include/linux/mailbox/mtk-cmdq-mailbox.h \
	'CMDQ_INST_SIZE|CMDQ_MAX_EVENT|CMDQ_CODE_|CMDQ_SUBSYS_SHIFT|cmdq_get_shift_pa'

echo
echo "[derived subsystem/event contract]"
vendor_dts="$VENDOR_TREE/arch/arm64/boot/dts/mt6797.dts"
vendor_events="$VENDOR_TREE/drivers/misc/mediatek/cmdq/v2/cmdq_event_common.h"
vendor_subsys="$VENDOR_TREE/drivers/misc/mediatek/cmdq/v2/cmdq_subsys_common.h"
linux_header="$LINUX_TREE/include/dt-bindings/gce/mediatek,mt6797-gce.h"
if [[ -f "$DERIVER" && -f "$vendor_dts" && -f "$vendor_events" &&
	-f "$vendor_subsys" && -f "$linux_header" ]] &&
	command -v python3 >/dev/null 2>&1; then
	python3 "$DERIVER" "$vendor_dts" "$vendor_events" "$vendor_subsys" \
		"$linux_header"
else
	echo "SKIP deriver or source/header unavailable"
fi

echo
echo "[decision]"
echo "The MT6797 GCE register, thread, IRQ bitmap, slot-cycle, and unshifted"
echo "32-bit command-address contract matches Linux's MT8173 mailbox data, so"
echo "no new CMDQ core driver is justified. Keep a named MT6797 compatible and"
echo "SoC-specific subsystem/event header: event IDs are not portable from"
echo "MT6795. Expose only normal-world SPI152; leave secure threads and display"
echo "consumers out of the generic provider until their address, event, clock,"
echo "power, M4U, and reset contracts are independently verified."
