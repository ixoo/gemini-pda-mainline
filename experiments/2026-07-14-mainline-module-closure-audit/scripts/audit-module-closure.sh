#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of built-in and packaged-module availability. It never loads
# a module, requests firmware, accesses a device node, or changes hardware.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
config=$package/kernel.config
system_map=$package/System.map
module_root=$(find "$package/modules/lib/modules" -mindepth 1 -maxdepth 1 -type d -print -quit 2>/dev/null || true)

for file in "$package/Image" "$config" "$system_map" "$module_root/modules.builtin" \
	"$module_root/modules.dep" "$module_root/modules.order"; do
	[[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done

sha256() {
	sha256sum "$1" | awk '{print $1}'
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
	local name=$1 path
	path=$(find "$module_root" -type f \( -name "$name.ko" -o \
		-name "${name//-/_}.ko" \) -print | LC_ALL=C sort | head -n 1 || true)
	if [[ -n "$path" ]]; then
		printf '%s' "${path#"$module_root"/}"
	fi
}

builtin_paths() {
	local name=$1 base
	base=${name//-/_}
	rg -N "(^|/)(${name}|${base})\\.ko$" "$module_root/modules.builtin" || true
}

dep_paths() {
	local rel=$1
	awk -F': ' -v key="$rel" '$1 == key { print $2 }' "$module_root/modules.dep"
}

declare -A seen
emit_closure() {
	local rel=$1 dep
	[[ -n "${seen[$rel]+set}" ]] && return
	seen[$rel]=1
	printf 'closure_module=%s\n' "$rel"
	printf 'closure_sha256=%s\n' "$(sha256 "$module_root/$rel")"
	while read -r dep_line; do
		for dep in $dep_line; do
			[[ -n "$dep" ]] || continue
			emit_closure "$dep"
		done
	done < <(dep_paths "$rel")
}

printf 'validation=mt6797-mainline-module-closure-current-72\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_system_map_sha256=%s\n' "$(sha256 "$system_map")"
printf 'module_root=%s\n' "$module_root"
printf 'modules_builtin_sha256=%s\n' "$(sha256 "$module_root/modules.builtin")"
printf 'modules_dep_sha256=%s\n' "$(sha256 "$module_root/modules.dep")"
printf 'modules_order_sha256=%s\n' "$(sha256 "$module_root/modules.order")"
printf 'module_file_count=%s\n' "$(find "$module_root" -type f -name '*.ko' | wc -l | tr -d ' ')"
printf 'closure_scope=packaged_module_edges_only;built_in_symbols_dt_firmware_and_userspace_not_resolved\n'

printf '\n[configuration]\n'
for symbol in \
	CONFIG_PINCTRL_MT6797 \
	CONFIG_MEDIATEK_WATCHDOG \
	CONFIG_MMC_MTK \
	CONFIG_SERIAL_8250_MT6577 \
	CONFIG_I2C_MT65XX \
	CONFIG_PINCTRL_AW9523 \
	CONFIG_KEYBOARD_MATRIX \
	CONFIG_TYPEC_FUSB301 \
	CONFIG_MTK_SOC_THERMAL \
	CONFIG_VIDEO_MEDIATEK_JPEG \
	CONFIG_SND_SOC_MT6797 \
	CONFIG_DRM_PANFROST \
	CONFIG_USB_MTU3 \
	CONFIG_USB_XHCI_MTK \
	CONFIG_BT_MTK \
	CONFIG_WWAN; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

symbol_state() {
	local symbol=$1
	if rg -q "[[:space:]]${symbol}$" "$system_map"; then
		printf 'present'
	else
		printf 'absent'
	fi
}

printf '\n[builtin_symbol_evidence]\n'
for symbol in mt6797_pinctrl_init mt6797_pinctrl_driver mt6797_pinctrl_of_match; do
	printf '%s=%s\n' "$symbol" "$(symbol_state "$symbol")"
done

printf '\n[target_availability]\n'
targets=(
	pinctrl-mt6797
	mtk-wdt
	mtk-sd
	8250_mtk
	i2c-mt65xx
	pinctrl-aw9523
	matrix-keypad
	fusb301
	auxadc_thermal
	mtk_jpeg
	snd-soc-mt6797-afe
	panfrost
	mtu3
	xhci-mtk-hcd
	btmtk
	wwan
)

for target in "${targets[@]}"; do
	rel=$(module_path "$target")
	if [[ "$target" == pinctrl-mt6797 && "$(config_state CONFIG_PINCTRL_MT6797)" == y ]]; then
		printf 'target=%s\nstate=builtin_by_config\nconfig=CONFIG_PINCTRL_MT6797=y\n' "$target"
	elif [[ -n "$rel" ]]; then
		printf 'target=%s\nstate=module\npath=%s\nsha256=%s\n' \
			"$target" "$rel" "$(sha256 "$module_root/$rel")"
		unset 'seen'
		declare -A seen
		emit_closure "$rel"
	elif builtin=$(builtin_paths "$target"); [[ -n "$builtin" ]]; then
		printf 'target=%s\nstate=builtin\nbuiltin_paths=%s\n' \
			"$target" "$(printf '%s' "$builtin" | tr '\n' ',' | sed 's/,$//')"
	else
		printf 'target=%s\nstate=absent\n' "$target"
	fi
done

printf '\n[safety]\n'
printf 'module_insert=not_attempted\n'
printf 'firmware_request=not_attempted\n'
printf 'hardware_write=none\n'
printf 'runtime_rootfs_load=not_attempted\n'
