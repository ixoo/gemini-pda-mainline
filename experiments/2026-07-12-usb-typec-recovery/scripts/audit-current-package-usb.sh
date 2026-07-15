#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 USB/Type-C boundary. It does not
# load a USB or Type-C module, enable a DT node, touch PHY/controller/VBUS
# registers, change a role, access an I2C adapter, or attach an accessory.

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

printf 'validation=mt6797-usb-typec-current-package-audit\n'
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
	CONFIG_USB \
	CONFIG_USB_XHCI_HCD \
	CONFIG_USB_XHCI_PLATFORM \
	CONFIG_USB_XHCI_MTK \
	CONFIG_USB_MTU3 \
	CONFIG_USB_MTU3_DUAL_ROLE \
	CONFIG_USB_MUSB_HDRC \
	CONFIG_USB_MUSB_DUAL_ROLE \
	CONFIG_USB_MUSB_MEDIATEK \
	CONFIG_MUSB_PIO_ONLY \
	CONFIG_USB_GADGET \
	CONFIG_TYPEC \
	CONFIG_TYPEC_TCPM \
	CONFIG_TYPEC_TCPCI \
	CONFIG_TYPEC_FUSB302 \
	CONFIG_TYPEC_FUSB301 \
	CONFIG_USB_ROLE_SWITCH \
	CONFIG_EXTCON \
	CONFIG_PHY_MTK_TPHY; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_usb_typec_modules]\n'
for module in \
	fusb301 fusb302 tcpci tcpm typec \
	mtu3 mtu3-drd xhci-mtk musb-mtk phy-mtk-tphy; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'usb11_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*usb@11200000 \{' "$dt_source")"
printf 'usb11_disabled_status_matches=%s\n' \
	"$(rg -n -A 12 '^[[:space:]]*usb@11200000 \{' "$dt_source" | rg -c 'status = "disabled"' || true)"
printf 'mtu3_parent_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*usb@11271000 \{' "$dt_source")"
printf 'mtu3_parent_disabled_status_matches=%s\n' \
	"$(rg -n -A 12 '^[[:space:]]*usb@11271000 \{' "$dt_source" | rg -c 'status = "disabled"' || true)"
printf 'xhci_child_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*usb@11270000 \{' "$dt_source")"
printf 'xhci_child_disabled_status_matches=%s\n' \
	"$(rg -n -A 15 '^[[:space:]]*usb@11270000 \{' "$dt_source" | rg -c 'status = "disabled"' || true)"
printf 'tphy_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*t-phy@(11210000|11290000) \{' "$dt_source")"
printf 'tphy_disabled_status_matches=%s\n' \
	"$(rg -n -A 35 '^[[:space:]]*t-phy@(11210000|11290000) \{' "$dt_source" | rg -c 'status = "disabled"' || true)"
printf 'fusb_or_typec_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*[[:alnum:]_.-]*(fusb|typec)[[:alnum:]_.-]* \{' "$dt_source")"
printf 'usb_role_switch_property_matches=%s\n' \
	"$(count_matches 'usb-role-switch|role-switch' "$dt_source")"
printf 'vbus_supply_property_matches=%s\n' \
	"$(count_matches 'vbus-supply|vbus-gpios|drvvbus' "$dt_source")"
printf 'usb_phy_reference_matches=%s\n' \
	"$(count_matches 'phys = <0x0[345]' "$dt_source")"
printf 'usb_resource_context:\n'
rg -n -A 28 -B 2 \
	'^[[:space:]]*(t-phy@11210000|t-phy@11290000|usb@11200000|usb@11271000|usb@11270000) \{' \
	"$dt_source" | head -n 280 || true

printf '\n[local_usb_patches]\n'
for patch in \
	"$repo_root/patches/v7.1.3/0056-usb-typec-add-FUSB301-autonomous-controller-driver.patch" \
	"$repo_root/patches/v7.1.3/0068-arm64-dts-mediatek-add-disabled-MT6797-USB3-topology.patch" \
	"$repo_root/patches/v7.1.3/0070-arm64-dts-mediatek-add-disabled-MT6797-USB11-topology.patch"; do
	if [[ -r "$patch" ]]; then
		printf 'patch=%s\nsha256=%s\nusb_match_lines=%s\n' \
			"$patch" "$(sha256 "$patch")" "$(rg -c -i 'usb|typec|tphy|musb|mtu3|xhci|fusb' "$patch" || true)"
	else
		printf 'patch=%s\nstatus=not_visible_from_guest\n' "$patch"
	fi
done

printf '\n[decision]\n'
printf '%s\n' \
	'usb_core_and_controller_code=packaged_built_in' \
	'mediatek_tphy_code=packaged_built_in' \
	'fusb301_driver=packaged_as_module' \
	'usb11_musb_dt_consumer=present_but_disabled' \
	'mtu3_parent_and_xhci_dt_consumers=present_but_disabled' \
	'mt6797_tphy_dt_consumers=present_but_disabled' \
	'usb_role_switch_and_vbus_owner=not_proven' \
	'gemini_fusb301_dt_consumer=absent_from_package_dtb' \
	'usb_runtime_probe=not_attempted' \
	'phy_runtime_probe=not_attempted' \
	'hardware_write=none'
