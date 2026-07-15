#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only comparison of the private Gemian firmware inventory with the
# firmware-loader and transport boundaries present in Linux 7.1.3. It never
# opens a firmware file, requests firmware, loads a module, or touches a
# device.

set -euo pipefail
export LC_ALL=C

linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}
manifest=${FIRMWARE_MANIFEST:-$repo_root/experiments/2026-07-11-gemian-firmware-inventory/results/manifest.sha256}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
module_root=$(find "$package/modules/lib/modules" -mindepth 1 -maxdepth 1 -type d -print -quit 2>/dev/null || true)

[[ -d "$linux_tree" ]] || { printf 'missing_source_tree=%s\n' "$linux_tree" >&2; exit 1; }
for file in "$manifest" "$dtb" "$config"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
# Image/DTB-only packages intentionally have no modules/ tree. Treat that as
# an empty optional-module set instead of rejecting an otherwise valid package.

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
dt_source=$tmpdir/gemini.dts
dtc -I dtb -O dts -o "$dt_source" "$dtb" 2>"$tmpdir/dtc.stderr"

sha256() {
	sha256sum "$1" | awk '{print $1}'
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

module_state() {
	local name=$1 path
	[[ -n "$module_root" ]] || { printf 'absent'; return; }
	path=$(find "$module_root" -type f \( -name "$name.ko" -o -name "${name//-/_}.ko" \) -print -quit 2>/dev/null || true)
	if [[ -n "$path" ]]; then
		printf 'present:%s:%s' "${path#"$module_root"/}" "$(sha256 "$path")"
	else
		printf 'absent'
	fi
}

source_hash() {
	local path=$1
	if [[ -r "$linux_tree/$path" ]]; then
		printf '%s' "$(sha256 "$linux_tree/$path")"
	else
		printf 'missing'
	fi
}

source_count() {
	local path=$1 pattern=$2 count
	if [[ -r "$linux_tree/$path" ]]; then
		count=$(rg -c "$pattern" "$linux_tree/$path" || true)
		printf '%s' "${count:-0}"
	else
		printf 'missing'
	fi
}

source_match() {
	local path=$1 pattern=$2
	if [[ -r "$linux_tree/$path" ]] && rg -q "$pattern" "$linux_tree/$path"; then
		printf 'yes'
	else
		printf 'no'
	fi
}

manifest_has() {
	local name=$1
	if rg -q "/${name}$" "$manifest"; then
		printf 'present'
	else
		printf 'absent'
	fi
}

printf 'validation=firmware-loader-boundary-current-package\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'firmware_manifest_sha256=%s\n' "$(sha256 "$manifest")"
printf 'firmware_manifest_file_count=%s\n' "$(wc -l < "$manifest" | tr -d ' ')"

printf '\n[source_hashes]\n'
for path in \
	drivers/input/touchscreen/novatek-nvt-ts.c \
	drivers/bluetooth/btmtkuart.c \
	drivers/bluetooth/btmtksdio.c \
	drivers/remoteproc/mtk_scp.c \
	drivers/rpmsg/mtk_rpmsg.c \
	drivers/media/platform/mediatek/vpu/mtk_vpu.c; do
	printf '%s=%s\n' "$path" "$(source_hash "$path")"
done

printf '\n[upstream_loader_contract]\n'
printf 'novatek_request_firmware_calls=%s\n' "$(source_count drivers/input/touchscreen/novatek-nvt-ts.c 'request_firmware')"
printf 'novatek_firmware_name_properties=%s\n' "$(source_count drivers/input/touchscreen/novatek-nvt-ts.c 'firmware-name')"
printf 'novatek_nt36672a_match=%s\n' "$(source_match drivers/input/touchscreen/novatek-nvt-ts.c 'nt36672a')"
printf 'btmtkuart_mt6797_match=%s\n' "$(source_match drivers/bluetooth/btmtkuart.c 'mt6797')"
printf 'btmtksdio_mt6797_match=%s\n' "$(source_match drivers/bluetooth/btmtksdio.c 'mt6797')"
printf 'btmtkuart_request_firmware_calls=%s\n' "$(source_count drivers/bluetooth/btmtkuart.c 'request_firmware')"
printf 'btmtksdio_request_firmware_calls=%s\n' "$(source_count drivers/bluetooth/btmtksdio.c 'request_firmware')"
printf 'scp_request_firmware_calls=%s\n' "$(source_count drivers/remoteproc/mtk_scp.c 'request_firmware')"
printf 'rpmsg_firmware_name_properties=%s\n' "$(source_count drivers/rpmsg/mtk_rpmsg.c 'firmware-name')"
printf 'vpu_request_firmware_calls=%s\n' "$(source_count drivers/media/platform/mediatek/vpu/mtk_vpu.c 'request_firmware')"

printf '\n[packaged_modules_and_configuration]\n'
for symbol in CONFIG_TOUCHSCREEN_NOVATEK_NVT_TS CONFIG_BT_MTK CONFIG_BT_MTKUART \
	CONFIG_BT_MTKSDIO CONFIG_MTK_SCP CONFIG_RPMSG_MTK_SCP CONFIG_VIDEO_MEDIATEK_VPU \
	CONFIG_MT6797_CONSYS CONFIG_MTK_WMT CONFIG_MTK_BTIF; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done
for module in novatek-nvt-ts btmtkuart btmtksdio mtk_scp mtk_rpmsg mtk-vpu; do
	printf '%s=%s\n' "$module" "$(module_state "$module")"
done

printf '\n[vendor_firmware_manifest]\n'
for name in novatek_ts_fw.bin WMT_SOC.cfg ROMv3_patch_1_0_hdr.bin ROMv3_patch_1_1_hdr.bin \
	WIFI_RAM_CODE_6797 modem_3_3g_n.img fm_cust.cfg pcm_suspend.bin pcm_deepidle.bin; do
	printf '%s=%s\n' "$name" "$(manifest_has "$name")"
done

printf '\n[packaged_dtb]\n'
firmware_name_count=$(rg -c 'firmware-name' "$dt_source" || true)
transport_node_count=$(rg -c '^[[:space:]]*(consys|wmt|btif|ccci|cldma|ccif|camera|seninf[0-9]*|camsv[0-9]*)@[^[:space:]]* \{' "$dt_source" || true)
active_transport_status_okay=$(awk -v node_re='^[[:space:]]*(consys|wmt|btif|ccci|cldma|ccif|camera|seninf[0-9]*|camsv[0-9]*)@' '
function brace_delta(line, copy, opens, closes) {
	copy = line
	opens = gsub(/[^\{]/, "", copy)
	copy = line
	closes = gsub(/[^\}]/, "", copy)
	return opens - closes
}
{
	if (!inside && $0 ~ node_re && $0 ~ /\{/) {
		inside = 1
		depth = brace_delta($0)
		next
	}
	if (inside && depth == 1 && $0 ~ /^[[:space:]]*status = "okay";/)
		count++
	if (inside) {
		depth += brace_delta($0)
		if (depth <= 0) inside = 0
	}
}
END { print count + 0 }
' "$dt_source")
printf 'firmware_name_properties=%s\n' "${firmware_name_count:-0}"
printf 'transport_or_camera_node_name_matches=%s\n' "${transport_node_count:-0}"
printf 'active_transport_status_okay=%s\n' "${active_transport_status_okay:-0}"

printf '\n[decision]\n'
printf '%s\n' \
	'novatek_ts_fw=vendor_only;upstream_novatek_driver_has_no_firmware_loader' \
	'WMT_ROMv3_WIFI=vendor_only;Linux_btmtkuart_btmtksdio_mt76_have_no_MT6797_match' \
	'pcm_spm=vendor_power_firmware_only;no_active_mainline_SCP_or_SPM_consumer' \
	'modem=vendor_CCCI_CLDMA_boundary;never_load_from_mainline_without_transport_and_EMI_MPU_contract' \
	'fm=vendor_configuration_and_patch;no_active_mainline_Gemini_consumer' \
	'firmware_files=private_unloaded_license_and_applicability_unresolved' \
	'no_firmware_request_or_hardware_write_performed'
