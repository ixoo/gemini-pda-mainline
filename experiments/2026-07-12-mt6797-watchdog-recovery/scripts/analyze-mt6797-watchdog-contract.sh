#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the archived MT6797 TOPRGU/WDK contract with Linux 7.1.3.  This is
# a source-only audit and never starts, stops, pings, or resets a watchdog.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/gemian-linux-kernel-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
REPO_ROOT=${REPO_ROOT:-/mnt/gemini-pda-mainline}
LOCAL_PATCH=${LOCAL_PATCH:-"$REPO_ROOT/patches/v7.1.3/0053-arm64-dts-mediatek-gemini-add-toprgu-watchdog-irq.patch"}

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

vendor_blob() {
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

vendor_anchor() {
	local path=$1
	local pattern=$2
	if vendor_exists "$path"; then
		git -C "$VENDOR_TREE" show "HEAD:$path" | rg -n -m 24 "$pattern" || true
	else
		echo "(missing: $path)"
	fi
}

linux_hash() {
	if [[ -f "$LINUX_TREE/$1" ]]; then
		sha256sum "$LINUX_TREE/$1" | awk '{print $1}'
	else
		echo missing
	fi
}

linux_anchor() {
	local path=$1
	local pattern=$2
	if [[ -f "$LINUX_TREE/$path" ]]; then
		rg -n -m 24 "$pattern" "$LINUX_TREE/$path" || true
	else
		echo "(missing: $path)"
	fi
}

echo "MT6797 TOPRGU watchdog contract audit"
echo "vendor_tree=$VENDOR_TREE"
echo "vendor_commit=$(git -C "$VENDOR_TREE" rev-parse HEAD)"
echo "linux_tree=$LINUX_TREE"
if [[ -f "$LINUX_TREE/Makefile" ]]; then
	printf 'linux_version='
	make -s -C "$LINUX_TREE" kernelversion
fi
if [[ -f "$LOCAL_PATCH" ]]; then
	printf 'local_patch_sha256='
	sha256sum "$LOCAL_PATCH" | awk '{print $1}'
else
	echo "local_patch_sha256=missing"
fi

echo
echo "[source identities]"
for path in \
	drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c \
	drivers/watchdog/mediatek/wdt/mt6797/mt_wdt.h \
	drivers/watchdog/mediatek/wdt/common/mtk_wdt.c \
	drivers/watchdog/mediatek/wdt/common/mt_wdt.h \
	arch/arm64/boot/dts/mt6797.dts; do
	printf 'vendor_blob %s %s\n' "$path" "$(vendor_blob "$path")"
done
for path in \
	drivers/watchdog/mtk_wdt.c \
	drivers/watchdog/Kconfig \
	drivers/watchdog/Makefile \
	Documentation/devicetree/bindings/watchdog/mediatek,mtk-wdt.yaml \
	arch/arm64/boot/dts/mediatek/mt6797.dtsi; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor MT6797 TOPRGU]"
vendor_anchor drivers/watchdog/mediatek/wdt/mt6797/mtk_wdt.c \
	'compatible|mtk_wdt_set_time_out_value|mtk_wdt_mode_config|mtk_wdt_enable|mtk_wdt_confirm_hwreboot|mtk_wdt_restart|wdt_arch_reset|request_(en|mode)|wdt_dump_reg|spm_wdt'
vendor_anchor drivers/watchdog/mediatek/wdt/mt6797/mt_wdt.h \
	'MTK_WDT_(MODE|LENGTH|RESTART|STATUS|SWRST|SWSYSRST|REQ_MODE|REQ_IRQ|EXT_REQ|DRAMC|LATCH|DEBUG)|HWWDT|SWWDT|THERMAL'
vendor_anchor drivers/watchdog/mediatek/wdt/common/mtk_wdt.c \
	'toprgu_reset|reset_controller|nr_resets|mtk_wdt_set_time_out_value|mtk_wdt_mode_config|mtk_wdt_restart|wdt_arch_reset|SWSYSRST'
vendor_anchor arch/arm64/boot/dts/mt6797.dts \
	'toprgu:|mt6797-toprgu|10007000|GIC_SPI 137|wdt_irq|reg_len_pol0'

echo
echo "[Linux watchdog core]"
linux_anchor drivers/watchdog/mtk_wdt.c \
	'WDT_(MAX|MIN|LENGTH|RST|MODE|SWRST|SWSYSRST)|mtk_wdt_(start|stop|ping|set_timeout|restart|isr)|platform_get_irq_optional|watchdog_(init|register)|reset_controller|mt6795_data|mtk_wdt_dt_ids'
linux_anchor drivers/watchdog/Kconfig 'config MEDIATEK_WATCHDOG|WATCHDOG_CORE|RESET_CONTROLLER'
linux_anchor Documentation/devicetree/bindings/watchdog/mediatek,mtk-wdt.yaml \
	'mt6797-wdt|mt6589-wdt|interrupts|disable-extrst|reset-by-toprgu|timeout-sec|reg:'
linux_anchor arch/arm64/boot/dts/mediatek/mt6797.dtsi \
	'watchdog:|mt6797-wdt|10007000|interrupts|reset-cells'

echo
echo "[decision]"
echo "Reuse Linux drivers/watchdog/mtk_wdt.c and the standard watchdog core."
echo "The existing mt6797-wdt/mt6589-wdt compatible pair already covers the"
echo "MT6797 register protocol and TOPRGU reset-controller shape. The Gemini"
echo "board-specific missing resource is the vendor-confirmed bark IRQ: SPI137"
echo "with IRQ_TYPE_EDGE_FALLING. Keep vendor WDK/WD_API character interfaces,"
echo "SPM request side channels, modem watchdogs, and reset policy out of the"
echo "mainline ABI. Do not test start/stop/restart until an external console,"
echo "known-good boot image, and recovery owner are ready."
