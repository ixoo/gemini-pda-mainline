#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Source-only audit of Linux USB11 MUSB/T-PHY probe and VBUS side effects.
# It never accesses a device, PHY registers, I2C, GPIO, VBUS, or role switch.

set -euo pipefail

LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=${REPO_ROOT:-"$(cd "$SCRIPT_DIR/../../.." && pwd -P)"}
MUSB_GLUE="$LINUX_TREE/drivers/usb/musb/mediatek.c"
MUSB_CORE="$LINUX_TREE/drivers/usb/musb/musb_core.c"
MUSB_HOST="$LINUX_TREE/drivers/usb/musb/musb_host.c"
TPHY="$LINUX_TREE/drivers/phy/mediatek/phy-mtk-tphy.c"
USB11_PATCH="$REPO_ROOT/patches/v7.1.3/0069-usb-musb-mediatek-add-MT6797-USB11-data.patch"
USB11_DTS_PATCH="$REPO_ROOT/patches/v7.1.3/0070-arm64-dts-mediatek-add-disabled-MT6797-USB11-topology.patch"

die() {
	echo "error: $*" >&2
	exit 1
}

command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"
for path in "$MUSB_GLUE" "$MUSB_CORE" "$MUSB_HOST" "$TPHY" \
	"$USB11_PATCH" "$USB11_DTS_PATCH"; do
	[[ -f "$path" ]] || die "required source is missing: $path"
done

hash_file() {
	sha256sum "$1" | awk '{print $1}'
}

anchors() {
	local file=$1
	local pattern=$2
	rg -n "$pattern" "$file" | head -n 100 || true
}

echo "validation=mt6797-mainline-usb11-probe-safety-source-audit"
printf 'linux_tree=%s\n' "$LINUX_TREE"
if [[ -f "$LINUX_TREE/Makefile" ]]; then
	printf 'linux_version='
	make -s -C "$LINUX_TREE" kernelversion
fi
printf 'musb_mediatek_sha256=%s\n' "$(hash_file "$MUSB_GLUE")"
printf 'musb_core_sha256=%s\n' "$(hash_file "$MUSB_CORE")"
printf 'musb_host_sha256=%s\n' "$(hash_file "$MUSB_HOST")"
printf 'tphy_sha256=%s\n' "$(hash_file "$TPHY")"
printf 'usb11_data_patch_sha256=%s\n' "$(hash_file "$USB11_PATCH")"
printf 'usb11_dts_patch_sha256=%s\n' "$(hash_file "$USB11_DTS_PATCH")"

echo
echo "[mt6797_data_and_dt]"
anchors "$MUSB_GLUE" 'mt6797_usb11_data|mt6797_usb11_clock_names|mt6797_usb11_hdrc_config|mt6797-usb11'
anchors "$USB11_DTS_PATCH" 'usb11_tphy|usb11_u2|usb11:|mediatek,mt6797-usb11|clocks =|clock-names|phys =|dr_mode|status =|mediatek,eye-src'

echo
echo "[glue_probe]"
anchors "$MUSB_GLUE" 'static int mtk_musb_probe|of_platform_populate|mtk_musb_clks_get|pm_runtime_enable|pm_runtime_get_sync|clk_bulk_prepare_enable|platform_device_register_full|mtk_musb_init'

echo
echo "[musb_and_phy_init]"
anchors "$MUSB_GLUE" 'static int mtk_musb_init|phy_init|phy_power_on|phy_set_mode|MUSB_HSDMA_INTR|USB_L1INTM'
anchors "$MUSB_CORE" 'musb_init_controller|usb_phy_init|musb_disable_interrupts|MUSB_DEVCTL|MUSB_POWER|musb_core_init|request_irq|musb_start'
anchors "$TPHY" 'static int mtk_phy_init|static int mtk_phy_power_on|hs_slew_rate_calibrate|u2_phy_instance_init|u2_phy_instance_power_on|writel|clk_bulk_prepare_enable'

echo
echo "[host_and_vbus]"
anchors "$MUSB_HOST" 'static int musb_host_setup|usb_add_hcd|hcd->power_budget|musb_start'
printf 'mediatek_glue_vbus_callback='
if rg -q 'set_vbus|platform_set_vbus' "$MUSB_GLUE"; then
	echo present
else
	echo absent
fi
printf 'usb11_vbus_supply_in_dt='
if rg -q 'vbus-supply|usb-vbus|vbus' "$USB11_DTS_PATCH"; then
	echo present
else
	echo absent
fi

echo
echo "[decision]"
echo "mt6797_usb11_musb_core_reuse_remains_correct"
echo "mtk_musb_probe_enables_parent_clocks_and_registers_a_musb_child"
echo "musb_child_init_calls_phy_init_and_phy_power_on_before_host_setup"
echo "generic_tphy_probe_is_resource_setup_but_phy_init_and_power_on_are_stateful_register_writes"
echo "musb_core_initialization_writes_controller_interrupt_power_and_session_registers"
echo "host_setup_registers_a_hcd;actual_vbus_drive_is_not_provided_by_current_mtk_glue"
echo "current_usb11_dt_has_no_vbus_supply_and_is_explicitly_disabled"
echo "current_usb11_dr_mode_host_is_not_a_safe_runtime_enablement_contract"
echo "first_runtime_test_requires_explicit_vbus_owner_or_device_only_gadget_candidate"
echo "keep_usb11_tphy_musb_typec_and_vbus_nodes_disabled_until_role_and_power_contracts_are_proven"
echo "hardware_write=none"
echo "runtime_mainline_probe=not_attempted"
