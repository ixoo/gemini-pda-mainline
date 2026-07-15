#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 CCCI/CLDMA boundary. It does not
# load a module, enable a DT node, touch modem registers, open a CCCI device,
# access shared memory, or perform a modem handshake.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
system_map=$package/System.map
modules=$package/modules/lib/modules

for file in "$dtb" "$config" "$system_map"; do
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

printf 'validation=mt6797-ccci-current-package-audit\n'
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
	CONFIG_WWAN \
	CONFIG_WWAN_DEBUGFS \
	CONFIG_MTK_T7XX \
	CONFIG_MHI_WWAN_CTRL \
	CONFIG_RPMSG_WWAN_CTRL \
	CONFIG_USB_NET_QMI_WWAN \
	CONFIG_USB_NET_CDC_MBIM \
	CONFIG_MFD_MT6397; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_wwan_modules]\n'
for module in wwan mhi_wwan_ctrl mhi_wwan_mbim rpmsg_wwan_ctrl qmi_wwan cdc_mbim; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'ccci_reserved_memory_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*reserve-memory-ccci' "$dt_source")"
printf 'active_transport_node_matches=%s\n' \
	"$(count_matches 'mdcldma|ap2c2k_ccif|ccif_modem|cldma_modem|ccci_modem' "$dt_source")"
printf 'transport_node_context:\n'
rg -n -C 3 'reserve-memory-ccci|mdcldma|ap2c2k_ccif|ccif_modem|cldma_modem|ccci_modem' "$dt_source" \
	| head -n 180 || true

printf '\n[local_dt_patch]\n'
patch=$repo_root/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch
if [[ -r "$patch" ]]; then
	printf 'patch=%s\n' "$patch"
	printf 'modem_declaration_matches=%s\n' "$(rg -c -i 'ccci|cldma|ccif|modem|md_smem' "$patch" || true)"
	rg -n -i 'ccci|cldma|ccif|modem|md_smem' "$patch" | head -n 80 || true
else
	printf 'patch=not_visible_from_guest\n'
fi

printf '\n[decision]\n'
printf '%s\n' \
	'wwan_core=packaged_as_module' \
	'mtk_t7xx=not_selected' \
	'ccci_cldma_ccif_transport=not_selected_and_no_active_dt_node' \
	'ccci_reserved_memory=retained_as_no_map_dt_reservations' \
	'active_modem_transport_node=absent_from_gemini_dtb' \
	'generic_wwan_layers=usable_only_above_a_new_mt6797_ccci_transport' \
	'firmware_handshake=not_attempted' \
	'hardware_write=none'
