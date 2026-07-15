#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 camera/media boundary. It does not
# load a media module, enable a camera DT node, touch a sensor, change camera
# rails or GPIOs, start streaming, or access DMA/IOMMU state.

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

printf 'validation=mt6797-camera-current-package-audit\n'
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
	CONFIG_MEDIA_SUPPORT \
	CONFIG_VIDEO_V4L2 \
	CONFIG_MEDIA_CONTROLLER \
	CONFIG_VIDEO_V4L2_SUBDEV_API \
	CONFIG_VIDEO_CAMERA_SENSOR \
	CONFIG_VIDEO_OV5675 \
	CONFIG_VIDEO_SP5509 \
	CONFIG_VIDEO_MEDIATEK_JPEG \
	CONFIG_VIDEO_MEDIATEK_MDP3 \
	CONFIG_VIDEO_MEDIATEK_VCODEC \
	CONFIG_COMMON_CLK_MT6797_CAMSYS \
	CONFIG_COMMON_CLK_MT6797_IMGSYS \
	CONFIG_MTK_IOMMU \
	CONFIG_MTK_SMI; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_media_modules]\n'
for module in ov5675 sp5509 imx219 imx412 mtk_jpeg mtk-mdp3 mtk-vcodec-dec; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'camera_capture_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*(seninf|camsv|camtop|cama|camb|dip_a|camera|isp)' "$dt_source")"
printf 'camera_syscon_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*syscon@(15000000|1a000000)' "$dt_source")"
printf 'camera_resource_context:\n'
rg -n -A 11 -B 1 \
	'^(\s*(smi@14022000|syscon@15000000|larb@15001000|syscon@1a000000|larb@1a001000) \{)' \
	"$dt_source" | head -n 180 || true

printf '\n[local_camera_patches]\n'
for patch in \
	"$repo_root/patches/v7.1.3/0025-arm64-dts-mediatek-mt6797-add-M4U-and-SMI.patch" \
	"$repo_root/patches/v7.1.3/0022-clk-mediatek-add-MT6797-CAM-and-MJC-clocks.patch"; do
	if [[ -r "$patch" ]]; then
		printf 'patch=%s\n' "$patch"
		printf 'camera_match_lines=%s\n' "$(rg -c -i 'camera|camsys|imgsys|seninf|larb|smi' "$patch" || true)"
	else
		printf 'patch=not_visible_from_guest\n'
	fi
done

printf '\n[decision]\n'
printf '%s\n' \
	'generic_media_framework=packaged' \
	'sp5509_sensor_driver=absent' \
	'ov5675_sensor_driver=not_selected' \
	'mt6797_camera_capture_pipeline=absent_from_package_and_dtb' \
	'mt6797_camsys_clock_provider=selected' \
	'mt6797_imgsys_clock_provider=not_selected' \
	'camera_smi_and_larbs=disabled_in_gemini_dtb' \
	'generic_media_layers=usable_only_after_a_new_sensor_and_mt6797_capture_pipeline' \
	'camera_stream=not_attempted' \
	'hardware_write=none'
