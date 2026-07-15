#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 CONSYS/WMT connectivity boundary. It
# does not load a radio module, touch firmware, open WMT/HCI/GNSS devices,
# change rfkill/network state, transmit, or alter a GPIO, regulator, or clock.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
modules=$package/modules/lib/modules

for file in "$dtb" "$config"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
[[ -d "$linux_tree" ]] || { printf 'missing_source_tree=%s\n' "$linux_tree" >&2; exit 1; }

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
dt_source=$tmpdir/gemini.dts
dtc_stderr=$tmpdir/dtc.stderr
dtc -I dtb -O dts -o "$dt_source" "$dtb" 2>"$dtc_stderr"

sha256() {
	sha256sum "$1" | awk '{print $1}'
}

count_matches() {
	local pattern=$1 file=$2 count
	count=$(rg -c "$pattern" "$file" || true)
	printf '%s' "${count:-0}"
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
	local module=$1
	[[ -d "$modules" ]] || return 0
	find "$modules" -type f -name "$module.ko" -print -quit 2>/dev/null || true
}

printf 'validation=mt6797-connectivity-current-package-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"
if [[ -d "$modules" ]]; then
	printf 'module_tree=present\n'
else
	printf 'module_tree=absent\n'
fi

printf '\n[configuration]\n'
for symbol in \
	CONFIG_BT \
	CONFIG_BT_MTK \
	CONFIG_BT_HCIUART \
	CONFIG_BT_HCIUART_SERDEV \
	CONFIG_BT_MTKUART \
	CONFIG_BT_MTKSDIO \
	CONFIG_BT_HCIBTSDIO \
	CONFIG_CFG80211 \
	CONFIG_MAC80211 \
	CONFIG_MT76_CORE \
	CONFIG_GNSS \
	CONFIG_GNSS_SERIAL \
	CONFIG_GNSS_MTK_SERIAL \
	CONFIG_MTK_WMT \
	CONFIG_MTK_BTIF \
	CONFIG_MT6797_CONSYS \
	CONFIG_MMC_MTK \
	CONFIG_FW_LOADER; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_connectivity_modules]\n'
for module in btmtk hci_uart btmtkuart btmtksdio gnss gnss-serial gnss-mtk mt76 mt76-connac-lib mt7921e; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'consys_reservation_matches=%s\n' \
	"$(count_matches '^[[:space:]]*consys-reserve-memory \{' "$dt_source")"
printf 'active_connectivity_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*(consys@|wifi@180f|btif(@|_)|gps(@|_)|gps_emi|stp|wmt)' "$dt_source")"
printf 'connectivity_resource_context:\n'
rg -n -A 12 -B 1 \
	'^(\s*consys-reserve-memory \{|\s*consys@|\s*wifi@180f|\s*btif(@|_)|\s*gps(@|_)|\s*gps_emi)' \
	"$dt_source" | head -n 180 || true

printf '\n[local_connectivity_patch]\n'
patch=$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch
if [[ -r "$patch" ]]; then
	printf 'patch=%s\n' "$patch"
	printf 'connectivity_match_lines=%s\n' \
		"$(rg -c -i 'consys|wifi|btif|gps|stp|wmt' "$patch" || true)"
	rg -n -i 'consys|wifi|btif|gps|stp|wmt' "$patch" | head -n 100 || true
else
	printf 'patch=not_visible_from_guest\n'
fi

printf '\n[decision]\n'
printf '%s\n' \
	'generic_hci_stp_layers=packaged' \
	'generic_cfg80211_mac80211_mt76_layers=packaged_but_not_gemini_match' \
	'generic_gnss_serial_layers=packaged' \
	'mt6797_btif_wmt_transport=absent' \
	'mt6797_consys_wifi_transport=absent' \
	'mt6797_combo_gnss_transport=absent' \
	'active_connectivity_dt_nodes=absent' \
	'consys_reserved_memory=retained_as_no_map_reservation' \
	'firmware_load=not_attempted' \
	'radio_transmit=none' \
	'hardware_write=none'
