#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only census of MT6797 source coverage in Linux 7.1.3 versus the local
# patch series. It never copies source, loads modules, requests firmware, or
# touches hardware.

set -euo pipefail
export LC_ALL=C

linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}
package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
patch_dir=$repo_root/patches/v7.1.3
config=$package/kernel.config

[[ -d "$linux_tree" ]] || { printf 'missing_source_tree=%s\n' "$linux_tree" >&2; exit 1; }
[[ -d "$patch_dir" ]] || { printf 'missing_patch_dir=%s\n' "$patch_dir" >&2; exit 1; }
[[ -r "$config" ]] || { printf 'missing_config=%s\n' "$config" >&2; exit 1; }

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
source_list=$tmpdir/source-list
patch_list=$tmpdir/patch-list

{
	rg -l -i 'mt6797' \
		"$linux_tree/arch/arm64/boot/dts/mediatek" \
		"$linux_tree/drivers" \
		"$linux_tree/include/dt-bindings" \
		"$linux_tree/sound" 2>/dev/null || true
} | sed "s#^$linux_tree/##" | sort -u > "$source_list"

rg -N -o '^diff --git a/[^ ]+ b/[^ ]+' "$patch_dir"/*.patch 2>/dev/null |
	sed -E 's|^.*diff --git a/([^ ]+) b/[^ ]+$|\1|' |
	sort -u > "$patch_list"

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

source_match() {
	local pattern=$1
	if rg -l -i "$pattern" \
		"$linux_tree/drivers" "$linux_tree/sound" \
		"$linux_tree/arch/arm64/boot/dts/mediatek" 2>/dev/null | head -n 1 |
		grep -q .; then
		printf 'present'
	else
		printf 'absent'
	fi
}

printf 'validation=mt6797-source-coverage-current-72\n'
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'package=%s\n' "$package"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'patch_count=%s\n' "$(awk '!/^[[:space:]]*(#|$)/ { count++ } END { print count + 0 }' "$patch_dir/../series")"
printf 'mt6797_source_file_count=%s\n' "$(grep -c . "$source_list" || true)"
printf 'patch_touched_path_count=%s\n' "$(grep -c . "$patch_list" || true)"

printf '\n[configuration]\n'
for symbol in \
	CONFIG_COMMON_CLK_MT6797 CONFIG_COMMON_CLK_MT6797_CAMSYS \
	CONFIG_COMMON_CLK_MT6797_IMGSYS CONFIG_SND_SOC_MT6797 \
	CONFIG_MMC_MTK CONFIG_MTK_IOMMU CONFIG_MTK_SMI CONFIG_USB_MTU3 \
	CONFIG_USB_XHCI_MTK CONFIG_DRM_MEDIATEK CONFIG_DRM_PANFROST \
	CONFIG_MTK_SOC_THERMAL CONFIG_MTK_SOC_THERMAL CONFIG_MTK_SCP \
	CONFIG_MTK_WMT CONFIG_MTK_BTIF CONFIG_MT6797_CONSYS \
	CONFIG_VIDEO_SP5509 CONFIG_MTK_CPUFREQ; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[mt6797_source_paths]\n'
while IFS= read -r path; do
	[[ -n "$path" ]] || continue
	if grep -Fqx "$path" "$patch_list"; then
		class=local_series_touched
	else
		class=preexisting_or_unmodified_by_series
	fi
	printf 'path=%s\nclass=%s\nsha256=%s\n' \
		"$path" "$class" "$(sha256 "$linux_tree/$path")"
done < "$source_list"

printf '\n[vendor_only_pattern_scan]\n'
printf 'mt6797_consys_wmt_btif=%s\n' "$(source_match 'mt6797.*(consys|wmt|btif)|(consys|wmt|btif).*mt6797')"
printf 'mt6797_ccci_cldma_ccif=%s\n' "$(source_match 'mt6797.*(ccci|cldma|ccif)|(ccci|cldma|ccif).*mt6797')"
printf 'mt6797_seninf_cam_isp=%s\n' "$(source_match 'mt6797.*(seninf|camsv|camtop|camera_isp)|(seninf|camsv|camtop|camera_isp).*mt6797')"
printf 'sp5509_sensor=%s\n' "$(source_match 'sp5509')"
printf 'nt36xxx_touch=%s\n' "$(source_match 'nt36xxx|nt36772|nt36525|nt36870|nt36676f')"
printf 'mt6797_cpufreq_eem=%s\n' "$(source_match 'mt6797.*(cpufreq|eem)|((cpufreq|eem).*mt6797)')"

printf '\n[decision]\n'
printf '%s\n' \
	'reuse_or_data_extension=clock_audio_mmc_iommu_smi_usb_drm_panfrost_input_sensor_frameworks' \
	'new_backend=MT6797_CONSYS_WMT_BTIF' \
	'new_backend=MT6797_CCCI_CLDMA_CCIF' \
	'new_backend=MT6797_SENINF_CAM_ISP_and_SP5509' \
	'new_backend=NT36xxx_touch_protocol' \
	'new_backend=MT6797_CPU_PLL_MUX_CCI_DVFS' \
	'compile_or_source_census_is_not_runtime_support' \
	'hardware_write=none'
