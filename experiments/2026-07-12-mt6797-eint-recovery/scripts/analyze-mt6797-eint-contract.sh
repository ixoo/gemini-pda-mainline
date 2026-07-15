#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Compare the archived MT6797 EINT/pinctrl contract with the prepared Linux
# 7.1.3 tree.  This is a source-only audit: it reads Git objects and the
# prepared source tree, and optionally validates the authored map against the
# private local device-tree capture.

set -euo pipefail

VENDOR_TREE=${VENDOR_TREE:-"$HOME/src/reference/gemian-linux-kernel-3.18"}
LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
EINT_CAPTURE=${EINT_CAPTURE:-"/mnt/gemini-pda-mainline/artifacts/device-inventory/20260711-live/device-tree-v5.txt"}
DECODER=${DECODER:-"/mnt/gemini-pda-mainline/experiments/2026-07-11-gemian-hardware-inventory/scripts/decode-eint-capture.py"}

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

vendor_count() {
	local path=$1
	local pattern=$2
	if vendor_exists "$path"; then
		vendor_show "$path" | rg -c "$pattern" || true
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
		rg -n -m 12 "$pattern" "$LINUX_TREE/$path" || true
	else
		echo "(missing: $path)"
	fi
}

echo "MT6797 EINT/pinctrl contract audit"
echo "vendor_tree=$VENDOR_TREE"
echo "vendor_commit=$(git -C "$VENDOR_TREE" rev-parse HEAD)"
echo "linux_tree=$LINUX_TREE"
if [[ -f "$LINUX_TREE/Makefile" ]]; then
	printf 'linux_version='
	make -s -C "$LINUX_TREE" kernelversion
fi

echo
echo "[source identities]"
for path in \
	drivers/pinctrl/mediatek/pinctrl-mt6797.c \
	drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h \
	arch/arm64/boot/dts/mt6797.dts \
	arch/arm64/boot/dts/cust_eint.dtsi; do
	printf 'vendor_blob %s %s\n' "$path" "$(vendor_blob "$path")"
done
for path in \
	drivers/pinctrl/mediatek/pinctrl-mt6797.c \
	drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h \
	drivers/pinctrl/mediatek/mtk-eint.c \
	drivers/pinctrl/mediatek/pinctrl-mtk-common-v2.c \
	Documentation/devicetree/bindings/pinctrl/mediatek,mt6779-pinctrl.yaml; do
	printf 'linux_sha256 %s %s\n' "$path" "$(linux_hash "$path")"
done

echo
echo "[vendor EINT and pinctrl baseline]"
vendor_anchor arch/arm64/boot/dts/mt6797.dts \
	'eintc:|compatible = "mediatek,mt-eic"|reg = <0x1000b000|interrupts = <GIC_SPI 170|max_eint_num|max_deint_cnt|deint_possible_irq|mapping_table_entry|debtime_setting_entry'
vendor_anchor drivers/pinctrl/mediatek/pinctrl-mt6797.c \
	'type1_start|eint_offsets|ap_num|mt6797_pinctrl_data|compatible'
printf 'vendor_no_eint_support=%s\n' "$(vendor_count drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h 'MTK_EINT_FUNCTION\(NO_EINT_SUPPORT')"
printf 'vendor_explicit_eint_entries=%s\n' "$(vendor_count drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h 'MTK_EINT_FUNCTION\([^N]')"
vendor_anchor arch/arm64/boot/dts/cust_eint.dtsi \
	'MSDC1_INS|TOUCH_PANEL|ALS@|GYRO@|interrupts =|debounce ='

echo
echo "[authored Linux MT6797 data]"
linux_anchor drivers/pinctrl/mediatek/pinctrl-mt6797.c \
	'mt6797_debounce_time|port_mask|\.ports|\.ap_num|\.db_cnt|\.eint_hw|compatible'
printf 'linux_explicit_eint_entries=%s\n' "$(rg -c 'MTK_EINT_FUNCTION\(0,' "$LINUX_TREE/drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h")"
printf 'linux_no_eint_support=%s\n' "$(rg -c 'MTK_EINT_FUNCTION\(NO_EINT_SUPPORT' "$LINUX_TREE/drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h")"
echo "selected GPIO/EINT entries:"
rg -n -A 2 -B 1 \
	'"GPIO(61|65|67|68|85|88|93|107|181)"|MTK_EINT_FUNCTION\(0, (176|186)\)' \
	"$LINUX_TREE/drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h" || true

echo
echo "[generic Linux EINT register contract]"
linux_anchor drivers/pinctrl/mediatek/mtk-eint.c \
	'MTK_EINT_DBNC|\.stat|\.ack|\.mask|\.sens|\.pol|\.dbnc_ctrl|\.dbnc_set|\.dbnc_clr'
linux_anchor drivers/pinctrl/mediatek/pinctrl-mtk-common-v2.c \
	'virtual|gpio_xlate|set_gpio_as_eint|eint_hw|request_resources'

echo
echo "[private capture cross-check]"
if [[ -f "$EINT_CAPTURE" && -f "$DECODER" && -f "$LINUX_TREE/drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h" ]] && command -v python3 >/dev/null 2>&1; then
	python3 "$DECODER" "$EINT_CAPTURE" \
		--kernel-header "$LINUX_TREE/drivers/pinctrl/mediatek/pinctrl-mtk-mt6797.h" \
		--gpio 67 --gpio 85 --gpio 88 --gpio 262 --eint 186
else
	echo "SKIP private capture or decoder unavailable"
fi

echo
echo "[decision]"
echo "Reuse the Linux MediaTek Paris pinctrl and generic mtk-eint core,"
echo "but retain dedicated MT6797 controller data and the recovered map."
echo "The vendor pinctrl header is not a usable map: it marks pins as"
echo "NO_EINT_SUPPORT and leaves its EINT offsets commented. The vendor DT"
echo "and live capture establish the 192-line block, six banks, parent SPI170,"
echo "ten debounce steps, 16 hardware-debounce channels, and 172 map entries."
echo "Keep GPIO0..261 as the physical range; represent pseudo-GPIO262/EINT176"
echo "and built-in EINT186 through the existing virtual-GPIO path. Do not enable"
echo "direct GIC routing until a consumer proves its mode and wake behavior."
