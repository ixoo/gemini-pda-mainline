#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Audit probe-time side effects in the pinned MT6797/MT6351 Linux path. This is
# source-only: it reads the prepared tree and emits line-numbered anchors; it
# does not contact hardware or execute a driver.

set -euo pipefail
export LC_ALL=C

linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}

die() {
	printf 'error: %s\n' "$*" >&2
	exit 1
}

[[ -d "$linux_tree" ]] || die "Linux tree not found: $linux_tree"

hash_file() {
	local path=$1
	[[ -f "$linux_tree/$path" ]] || die "missing source: $path"
	sha256sum "$linux_tree/$path" | awk '{print $1}'
}

anchor() {
	local path=$1
	local pattern=$2
	printf '\n[%s]\n' "$path"
	rg -n -C 2 "$pattern" "$linux_tree/$path" || true
}

printf 'validation=mt6351-mainline-probe-safety-source-audit\n'
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='
make -s -C "$linux_tree" kernelversion

printf '\n[source_hashes]\n'
for path in \
	drivers/soc/mediatek/mtk-pmic-wrap.c \
	drivers/mfd/mt6397-core.c \
	drivers/mfd/mt6397-irq.c \
	drivers/regulator/mt6351-regulator.c \
	drivers/input/keyboard/mtk-pmic-keys.c \
	drivers/rtc/rtc-mt6397.c; do
	printf '%s=%s\n' "$path" "$(hash_file "$path")"
done

anchor drivers/soc/mediatek/mtk-pmic-wrap.c \
	'PWRAP_INIT_DONE2|devm_clk_bulk_get_all_enabled|static int pwrap_init|reset_control_reset|PWRAP_WDT_UNIT|PWRAP_WDT_SRC_EN|PWRAP_TIMER_EN|PWRAP_INT_EN'
anchor drivers/mfd/mt6397-core.c \
	'static int mt6397_probe|regmap_read\(pmic->regmap|mt6397_irq_init|devm_mfd_add_devices'
anchor drivers/mfd/mt6397-irq.c \
	'Mask all interrupt sources|regmap_write\(chip->regmap, chip->int_con|static int mt6397_irq_init'
anchor drivers/regulator/mt6351-regulator.c \
	'static int mt6351_regulator_probe|regmap_read\(mt6351->regmap|regulator_register'
anchor drivers/input/keyboard/mtk-pmic-keys.c \
	'static int mtk_pmic_keys_probe|regmap_update_bits\(keys->regmap|mtk_pmic_keys_lp_reset_setup'
anchor drivers/rtc/rtc-mt6397.c \
	'static int mtk_rtc_probe|regmap_write|regmap_bulk_write|mtk_rtc_write_trigger'

printf '\n[decision]\n'
printf '%s\n' \
	'pwrap_probe_is_stateful_and_not_read_only' \
	'mt6397_irq_init_masks_all_four_mt6351_interrupt_banks' \
	'mt6351_regulator_probe_reads_revision_and_vsel_control_without_rail_enable' \
	'key_and_rtc_write_paths_are_conditional_or_later_operations' \
	'first_runtime_test_requires_external_recovery_and_before_after_register_capture'
