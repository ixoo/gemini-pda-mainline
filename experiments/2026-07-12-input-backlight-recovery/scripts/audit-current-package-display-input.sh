#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged Gemini display/input boundary. It does not
# load input, DRM, panel, PWM, or expander modules; open PCM/I2C paths; write
# touch/keyboard/display/brightness state; or enable a DT consumer.

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
	[[ -n "$count" ]] || count=0
	printf '%s' "$count"
}

count_matches_i() {
	local pattern=$1 file=$2 count
	count=$(rg -i -c "$pattern" "$file" || true)
	[[ -n "$count" ]] || count=0
	printf '%s' "$count"
}

count_in_context() {
	local node_pattern=$1 lines=$2 property_pattern=$3 count
	count=$(rg -n -A "$lines" "$node_pattern" "$dt_source" |
		rg -c "$property_pattern" || true)
	[[ -n "$count" ]] || count=0
	printf '%s' "$count"
}

config_state() {
	local symbol=$1 value
	value=$(rg -m1 "^$symbol=" "$config" | cut -d= -f2- || true)
	if [[ -n "$value" ]]; then
		printf '%s' "$value"
	elif rg -q "^# $symbol is not set$" "$config"; then
		printf 'unset'
	else
		printf 'absent'
	fi
}

module_path() {
	local module=$1
	find "$modules" -type f -name "$module.ko" -print -quit 2>/dev/null || true
}

printf 'validation=gemini-display-input-current-package-audit\n'
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
	CONFIG_INPUT_TOUCHSCREEN \
	CONFIG_TOUCHSCREEN_NOVATEK_NVT_TS \
	CONFIG_TOUCHSCREEN_NOVATEK_NT36XXX \
	CONFIG_PINCTRL_AW9523 \
	CONFIG_KEYBOARD_GPIO \
	CONFIG_KEYBOARD_MATRIX \
	CONFIG_BACKLIGHT_PWM \
	CONFIG_PWM_MEDIATEK \
	CONFIG_PWM_MTK_DISP \
	CONFIG_DRM_MEDIATEK \
	CONFIG_DRM_MIPI_DSI \
	CONFIG_PHY_MTK_MIPI_DSI \
	CONFIG_DRM_PANEL_NOVATEK_NT36672E \
	CONFIG_MTK_CMDQ CONFIG_MTK_IOMMU CONFIG_MTK_MMSYS CONFIG_MTK_SMI; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_modules]\n'
for module in \
	pinctrl-aw9523 matrix_keypad gpio_keys pwm-mtk-disp pwm-mediatek pwm_bl \
	mediatek-drm panel-novatek-nt36672e phy-mtk-mipi-dsi-drv novatek-nvt-ts \
	novatek-nt36xxx; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[keyboard_tree]\n'
printf 'i2c5_node_matches=%s\n' "$(count_matches '^[[:space:]]*i2c@1101c000 \{' "$dt_source")"
printf 'i2c5_disabled_status_matches=%s\n' "$(count_in_context '^[[:space:]]*i2c@1101c000 \{' 16 'status = "disabled"')"
printf 'aw9523_node_matches=%s\n' "$(count_matches '^[[:space:]]*gpio-expander@5b \{' "$dt_source")"
printf 'aw9523_disabled_status_matches=%s\n' "$(count_in_context '^[[:space:]]*gpio-expander@5b \{' 16 'status = "disabled"')"
printf 'keyboard_matrix_node_matches=%s\n' "$(count_matches '^[[:space:]]*keyboard-matrix \{' "$dt_source")"
printf 'keyboard_matrix_disabled_status_matches=%s\n' "$(count_in_context '^[[:space:]]*keyboard-matrix \{' 16 'status = "disabled"')"
printf 'keyboard_matrix_keymap_matches=%s\n' "$(count_in_context '^[[:space:]]*keyboard-matrix \{' 14 'linux,keymap')"

printf '\n[hall_tree]\n'
printf 'gpio_keys_node_matches=%s\n' "$(count_matches '^[[:space:]]*gpio-keys \{' "$dt_source")"
printf 'gpio_keys_disabled_status_matches=%s\n' "$(count_in_context '^[[:space:]]*gpio-keys \{' 18 'status = \"disabled\"')"
printf 'hall_switch_child_matches=%s\n' "$(count_in_context '^[[:space:]]*gpio-keys \{' 18 'hall-switch \{')"
# dtc canonicalizes labels, GPIO flags, and Linux constants in a decompiled
# DTB. Match the resulting cells: GPIO66 on the pio controller, active-low
# flag 1; 64 ms debounce; and SW_LID (EV_SW code 0).
printf 'hall_switch_gpio_matches=%s\n' "$(count_in_context '^[[:space:]]*gpio-keys \{' 18 'gpios = <0x[[:xdigit:]]+ 0x42 0x01>')"
printf 'hall_switch_debounce_matches=%s\n' "$(count_in_context '^[[:space:]]*gpio-keys \{' 18 'debounce-interval = <0x40>')"
printf 'hall_switch_code_matches=%s\n' "$(count_in_context '^[[:space:]]*gpio-keys \{' 18 'linux,code = <0x00>')"

printf '\n[display_tree]\n'
printf 'display_pwm_node_matches=%s\n' "$(count_matches '^[[:space:]]*pwm@1100f000 \{' "$dt_source")"
printf 'display_pwm_disabled_status_matches=%s\n' "$(count_in_context '^[[:space:]]*pwm@1100f000 \{' 14 'status = "disabled"')"
printf 'dsi_node_matches=%s\n' "$(count_matches '^[[:space:]]*dsi@1401c000 \{' "$dt_source")"
printf 'dsi_disabled_status_matches=%s\n' "$(count_in_context '^[[:space:]]*dsi@1401c000 \{' 18 'status = "disabled"')"
printf 'dsi_phy_node_matches=%s\n' "$(count_matches '^[[:space:]]*dsi-phy@10215000 \{' "$dt_source")"
printf 'dsi_phy_disabled_status_matches=%s\n' "$(count_in_context '^[[:space:]]*dsi-phy@10215000 \{' 12 'status = "disabled"')"
printf 'display_component_node_matches=%s\n' "$(count_matches '^[[:space:]]*(ovl@1400b000|ovl@1400d000|ovl@1400e000|rdma@1400f000|color@14013000|ccorr@14014000|aal@14015000|gamma@14016000|od@14017000|dither@14018000|ufoe@14019000) \{' "$dt_source")"
printf 'display_component_disabled_status_matches=%s\n' "$(count_in_context '^[[:space:]]*(ovl@1400b000|ovl@1400d000|ovl@1400e000|rdma@1400f000|color@14013000|ccorr@14014000|aal@14015000|gamma@14016000|od@14017000|dither@14018000|ufoe@14019000) \{' 14 'status = "disabled"')"
printf 'panel_consumer_matches=%s\n' "$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(panel|backlight|display)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'touchscreen_node_matches=%s\n' "$(count_matches_i '^[[:space:]]*[[:alnum:]_.-]*(touch|cap_touch|novatek|nt36)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'display_resource_context:\n'
rg -n -A 18 -B 2 \
	'^[[:space:]]*(pwm@1100f000|dsi-phy@10215000|dsi@1401c000|ovl@1400b000|ovl@1400d000|ovl@1400e000|rdma@1400f000|panel|backlight|touch|gpio-expander@5b|keyboard-matrix) \{' \
	"$dt_source" | head -n 360 || true

printf '\n[source_contract]\n'
printf 'input_validation=experiments/2026-07-12-input-backlight-recovery/results/mainline-input-current-71-validation-20260714.txt\n'
printf 'display_validation=experiments/2026-07-12-mt6797-drm-component-recovery/results/mainline-display-current-71-validation-20260714.txt\n'
printf 'touch_protocol=live_NT36772_identity_observed;vendor_transport_runtime_unvalidated\n'
printf 'keyboard_reuse=AW9523_pinctrl_plus_gpio_matrix_keypad\n'
printf 'backlight_reuse=MT6797_display_PWM_plus_standard_pwm_backlight\n'
printf 'display_reuse=MT6797_specific_DRM_DSI_PHY_platform_data\n'

printf '\n[local_display_input_patches]\n'
for patch in \
	"$repo_root/patches/v7.1.3/0054-arm64-dts-mediatek-add-disabled-Gemini-AW9523-keyboard-candidate.patch" \
	"$repo_root/patches/v7.1.3/0074-arm64-dts-mediatek-gemini-add-disabled-hall-gpio-keys-candidate.patch" \
	"$repo_root/patches/v7.1.3/0075-input-touchscreen-novatek-add-NT36772-backend.patch" \
	"$repo_root/patches/v7.1.3/0060-drm-mediatek-add-MT6797-DPI-platform-data.patch" \
	"$repo_root/patches/v7.1.3/0061-arm64-dts-mediatek-add-disabled-MT6797-DPI-node.patch"; do
	if [[ -r "$patch" ]]; then
		printf 'patch=%s\nsha256=%s\nmatch_lines=%s\n' \
			"$patch" "$(sha256 "$patch")" "$(rg -c -i 'display|dsi|pwm|keyboard|aw9523|panel|dpi|mt6797' "$patch" || true)"
	else
		printf 'patch=%s\nstatus=not_visible_from_guest\n' "$patch"
	fi
done

printf '\n[decision]\n'
printf '%s\n' \
	'keyboard=packaged_upstream_AW9523_and_matrix_keypad_with_disabled_bus_expander_consumer' \
	'hall=packaged_disabled_gpio_keys_SW_LID_candidate_on_GPIO66_active_low_64ms' \
	'touch=separate_NT36772_backend_compile_only;vendor_transport_runtime_unvalidated' \
	'backlight=packaged_PWM_providers_but_no_standard_backlight_consumer' \
	'display=packaged_MT6797_DRM_DSI_PHY_panel_objects_but_all_consumers_disabled' \
	'panel=nt36672e_module_packaged_but_panel_node_absent' \
	'display_runtime=not_attempted' \
	'input_runtime=not_attempted' \
	'hardware_write=none'
