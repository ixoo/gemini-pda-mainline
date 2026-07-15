#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 Panfrost/GPU boundary. It does not
# load Panfrost, enable a GPU DT node, touch GPU/MFG registers, change clocks,
# power domains, regulator state, OPPs, I2C state, or submit a GPU job.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
repo_root=${REPO_ROOT:-/mnt/gemini-pda-mainline}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
system_map=$package/System.map
modules=$package/modules/lib/modules

for file in "$package/Image" "$dtb" "$config" "$system_map"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
[[ -d "$modules" ]] || { printf 'missing_modules=%s\n' "$modules" >&2; exit 1; }
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

count_in_context() {
	local node_pattern=$1 lines=$2 property_pattern=$3 count
	count=$(rg -n -A "$lines" "$node_pattern" "$dt_source" |
		rg -c "$property_pattern" || true)
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
	find "$modules" -type f -name "$module.ko" -print -quit 2>/dev/null || true
}

printf 'validation=mt6797-panfrost-current-package-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'package_system_map_sha256=%s\n' "$(sha256 "$system_map")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"

printf '\n[configuration]\n'
for symbol in \
	CONFIG_DRM \
	CONFIG_DRM_PANFROST \
	CONFIG_DRM_MEDIATEK \
	CONFIG_MTK_SCPSYS \
	CONFIG_MTK_SCPSYS_PM_DOMAINS \
	CONFIG_MTK_MFG_PM_DOMAIN \
	CONFIG_COMMON_CLK_MT6797_MFGSYS \
	CONFIG_REGULATOR_RT5735 \
	CONFIG_REGULATOR_FAN53555 \
	CONFIG_PM_GENERIC_DOMAINS \
	CONFIG_MTK_IOMMU; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_gpu_modules]\n'
for module in panfrost mali-dp rt5735-regulator fan53555; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'gpu_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*gpu@13040000 \{' "$dt_source")"
printf 'gpu_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*gpu@13040000 \{' 16 'status = "disabled"')"
printf 'gpu_compatible_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*gpu@13040000 \{' 16 'mediatek,mt6797-mali|arm,mali-t880')"
printf 'gpu_opp_property_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*gpu@13040000 \{' 20 'operating-points-v2|opp-table')"
printf 'gpu_reset_property_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*gpu@13040000 \{' 20 '(^|[[:space:]])resets|reset-names')"
printf 'gpu_iommu_property_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*gpu@13040000 \{' 20 'iommus|mediatek,larbs')"
printf 'mfg_clock_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*syscon@13000000 \{' "$dt_source")"
printf 'mfg_clock_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*syscon@13000000 \{' 10 'status = "disabled"')"
printf 'mfg_power_domain_provider_matches=%s\n' \
	"$(count_matches '^[[:space:]]*power-controller@10006000 \{' "$dt_source")"
printf 'mfg_power_domain_provider_status=implicit-okay\n'
printf 'rt5735_parent_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*i2c@11010000 \{' "$dt_source")"
printf 'rt5735_parent_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*i2c@11010000 \{' 9 'status = "disabled"')"
printf 'rt5735_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*regulator@1c \{' "$dt_source")"
printf 'rt5735_node_disabled_status_matches=%s\n' \
	"$(count_in_context '^[[:space:]]*regulator@1c \{' 10 'status = "disabled"')"
printf 'gpu_resource_context:\n'
rg -n -A 28 -B 2 \
	'^[[:space:]]*(power-controller@10006000|syscon@13000000|gpu@13040000|i2c@11010000|regulator@1c) \{' \
	"$dt_source" | head -n 260 || true

printf '\n[local_gpu_patches]\n'
for patch in \
	"$repo_root/patches/v7.1.3/0047-pmdomain-mediatek-add-MT6797-MFG-domains.patch" \
	"$repo_root/patches/v7.1.3/0048-clk-mediatek-add-MT6797-MFGSYS.patch" \
	"$repo_root/patches/v7.1.3/0049-arm64-dts-mediatek-mt6797-add-disabled-MFG-clock.patch" \
	"$repo_root/patches/v7.1.3/0050-pmdomain-mediatek-use-MT6797-MFG-52MHz-preclock.patch" \
	"$repo_root/patches/v7.1.3/0051-regulator-add-Richtek-RT5735-VSEL0-support.patch" \
	"$repo_root/patches/v7.1.3/0058-drm-panfrost-add-MT6797-platform-data.patch" \
	"$repo_root/patches/v7.1.3/0059-arm64-dts-mediatek-add-disabled-MT6797-Panfrost-node.patch"; do
	if [[ -r "$patch" ]]; then
		printf 'patch=%s\nsha256=%s\ngpu_match_lines=%s\n' \
			"$patch" "$(sha256 "$patch")" "$(rg -c -i 'gpu|mfg|panfrost|rt5735|scpsys|power.domain' "$patch" || true)"
	else
		printf 'patch=%s\nstatus=not_visible_from_guest\n' "$patch"
	fi
done

printf '\n[decision]\n'
printf '%s\n' \
	'panfrost_core=packaged_as_module' \
	'live_gpu_model_reuse=midgard_t880_product_0x0880' \
	'mt6797_panfrost_platform_data=packaged_in_panfrost_module' \
	'mt6797_mfg_clock_provider=packaged_built_in_but_dt_disabled' \
	'mt6797_mfg_power_domains=packaged_built_in_provider' \
	'rt5735_vgpu=packaged_built_in_but_i2c_parent_and_node_disabled' \
	'gpu_dt_consumer=present_but_disabled' \
	'gpu_opp_contract=absent' \
	'gpu_reset_contract=absent' \
	'gpu_iommu_contract=absent' \
	'gpu_runtime_probe=not_attempted' \
	'gpu_job_submission=not_attempted' \
	'hardware_write=none'
