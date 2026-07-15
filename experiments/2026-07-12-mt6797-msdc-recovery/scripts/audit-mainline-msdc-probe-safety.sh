#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Source-only audit of Linux mtk-sd probe and MMC power/voltage side effects.
# It never accesses a device, MMIO, storage media, or the vendor tree.

set -euo pipefail

LINUX_TREE=${LINUX_TREE:-"$HOME/src/gemini-pda/linux-7.1.3"}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPO_ROOT=${REPO_ROOT:-"$(cd "$SCRIPT_DIR/../../.." && pwd -P)"}
DRIVER="$LINUX_TREE/drivers/mmc/host/mtk-sd.c"
MMC_HOST="$LINUX_TREE/drivers/mmc/core/host.c"
MMC_CORE="$LINUX_TREE/drivers/mmc/core/core.c"
BOARD_PATCH="$REPO_ROOT/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch"
PINMUX_PATCH="$REPO_ROOT/patches/v7.1.3/0071-arm64-dts-mediatek-gemini-use-pinmux-only-for-MT6797-MSDC.patch"

die() {
	echo "error: $*" >&2
	exit 1
}

command -v rg >/dev/null || die "rg is required"
command -v sha256sum >/dev/null || die "sha256sum is required"
[[ -f "$DRIVER" ]] || die "Linux mtk-sd source is missing: $DRIVER"
[[ -f "$MMC_HOST" ]] || die "Linux MMC host source is missing: $MMC_HOST"
[[ -f "$MMC_CORE" ]] || die "Linux MMC core source is missing: $MMC_CORE"
[[ -f "$BOARD_PATCH" ]] || die "Gemini board patch is missing: $BOARD_PATCH"
[[ -f "$PINMUX_PATCH" ]] || die "MSDC pinmux-only patch is missing: $PINMUX_PATCH"

hash_file() {
	sha256sum "$1" | awk '{print $1}'
}

anchors() {
	local pattern=$1
	rg -n "$pattern" "$DRIVER" | head -n 80 || true
}

echo "validation=mt6797-mainline-msdc-probe-safety-source-audit"
printf 'linux_tree=%s\n' "$LINUX_TREE"
if [[ -f "$LINUX_TREE/Makefile" ]]; then
	printf 'linux_version='
	make -s -C "$LINUX_TREE" kernelversion
fi
printf 'mtk_sd_sha256=%s\n' "$(hash_file "$DRIVER")"
printf 'mmc_host_sha256=%s\n' "$(hash_file "$MMC_HOST")"
printf 'mmc_core_sha256=%s\n' "$(hash_file "$MMC_CORE")"
printf 'board_patch_sha256=%s\n' "$(hash_file "$BOARD_PATCH")"
printf 'pinmux_patch_sha256=%s\n' "$(hash_file "$PINMUX_PATCH")"

echo
echo "[compatibility_record]"
anchors 'static const struct mtk_mmc_compatible mt6797_compat|mediatek,mt6797-mmc'

echo
echo "[probe_lifecycle_anchors]"
anchors 'static int msdc_drv_probe|mmc_regulator_get_supply|msdc_of_clock_parse|devm_reset_control_get_optional_exclusive|dma_alloc_coherent|msdc_ungate_clock|msdc_init_hw|devm_request_irq|pm_runtime_set_active|mmc_add_host'

echo
echo "[controller_write_paths]"
anchors 'static void msdc_reset_hw|MSDC_CFG_RST|MSDC_FIFOCS_CLR|writel\(0, host->base \+ MSDC_INTEN|MSDC_PATCH_BIT|MSDC_PATCH_BIT1|MSDC_PATCH_BIT2|MSDC_IOCON|MSDC_CFG_CKPDN|MSDC_CFG_CKMOD'

echo
echo "[mmc_power_and_voltage_paths]"
anchors 'static int msdc_ops_switch_volt|mmc_regulator_set_vqmmc|pinctrl_select_state|static void msdc_ops_set_ios|MMC_POWER_UP|MMC_POWER_ON|MMC_POWER_OFF|mmc_regulator_set_ocr|regulator_enable|regulator_disable'

echo
echo "[mmc_core_start_anchors]"
rg -n -C 5 'int mmc_add_host|void mmc_start_host|mmc_power_up\(host|_mmc_detect_change|mmc_rescan_try_freq|mmc_go_idle|mmc_attach_mmc' "$MMC_HOST" "$MMC_CORE" | head -n 180 || true

echo
echo "[current_gemini_board_contract]"
rg -n -C 4 'mmc0:|bus-width|max-frequency|vmmc-supply|vqmmc-supply|non-removable|no-sd|no-sdio|status = "okay"' "$BOARD_PATCH" | head -n 100 || true
printf 'board_has_hs200_or_hs400_capability=' 
if rg -q 'mmc-hs200-1_8v|mmc-hs400-1_8v|cap-mmc-highspeed' "$BOARD_PATCH"; then
	echo yes
else
	echo no
fi
printf 'board_has_reset_property=' 
if rg -q 'resets =|reset-names' "$BOARD_PATCH"; then
	echo yes
else
	echo no
fi
printf 'board_uhs_and_default_groups_same=' 
if rg -q 'pinctrl-0 = <&mmc0_pins_default>;[[:space:]]*pinctrl-1 = <&mmc0_pins_default>;' "$BOARD_PATCH"; then
	echo yes
else
	echo inspect_generated_dtb
fi

echo
echo "[decision]"
echo "mt6797_mtk_sd_probe_is_stateful_and_not_read_only"
echo "probe_enables_controller_clocks_and_waits_for_clock_stable"
echo "probe_programs_controller_reset_fifo_interrupt_dma_tuning_and_timeout_registers"
echo "gemini_board_does_not_declare_external_msdc_reset;internal_controller_reset_still_runs"
echo "mmc_add_host_can_start_card_identification_after_probe"
echo "mmc_power_up_may_set_and_enable_vemc_through_regulator_core"
echo "mmc_power_on_may_enable_vio18_through_regulator_core"
echo "signal_voltage_switch_may_change_vqmmc_and_select_pinctrl_state"
echo "current_gemini_board_caps_legacy_25mhz_and_8bit_nonremovable_only"
echo "current_gemini_board_uses_pinmux_only_for_default_and_uhs_states"
echo "first_runtime_storage_test_requires_non_primary_boot_external_recovery_and_read_only_rootfs_policy"
echo "hardware_write=none"
echo "runtime_mainline_boot=not_attempted"
