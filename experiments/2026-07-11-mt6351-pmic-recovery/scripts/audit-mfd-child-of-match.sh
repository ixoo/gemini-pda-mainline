#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Audit how Linux MFD cells with of_compatible are converted into platform
# devices, and whether the MT6351 children in the Gemini DT can bind without a
# matching child node.  This is source-only; it never contacts hardware.

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

printf 'validation=mt6351-mfd-child-of-match-source-audit\n'
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='
make -s -C "$linux_tree" kernelversion

printf '\n[source_hashes]\n'
for path in \
	drivers/mfd/mfd-core.c \
	drivers/mfd/mt6397-core.c \
	drivers/input/keyboard/mtk-pmic-keys.c \
	sound/soc/codecs/mt6351.c \
	arch/arm64/boot/dts/mediatek/mt6797.dtsi \
	arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts; do
	printf '%s=%s\n' "$path" "$(hash_file "$path")"
done

anchor drivers/mfd/mfd-core.c \
	'if \(IS_ENABLED\(CONFIG_OF\).*cell->of_compatible|Skip .disabled. devices|if \(!pdev->dev.of_node\)|platform_device_add\(pdev\)'
anchor drivers/mfd/mt6397-core.c \
	'mt6351_devs|\.name = "mt6351-(regulator|rtc|sound|keys)"|\.of_compatible = "mediatek,mt6351-(regulator|rtc|sound|keys)"'
anchor drivers/input/keyboard/mtk-pmic-keys.c \
	'of_match_device\(of_mtk_pmic_keys_match_tbl|mtk_pmic_regs = of_id->data|\.name = "mtk-pmic-keys"'
anchor sound/soc/codecs/mt6351.c \
	'mt6351_codec_driver_probe|devm_snd_soc_register_component|\.name = "mt6351-sound"'
anchor arch/arm64/boot/dts/mediatek/mt6797.dtsi \
	'mt6351-regulator|mt6351-rtc|mt6351-sound|mt6351-keys|compatible = "mediatek,mt6351"'
anchor arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts \
	'&mt6351regulator|mt6351-keys|mt6351-sound|mt6351-rtc'

printf '\n[decision]\n'
printf '%s\n' \
	'mfd_missing_compatible_child: platform_device_is_still_registered_without_of_node' \
	'mfd_disabled_compatible_child: cell_is_not_registered' \
	'mt6351_regulator: platform-id_match_allows_probe_without_of_node' \
	'mt6351_rtc_and_mtk_pmic_keys: of_match_only; missing_of_node_does_not_bind' \
	'mt6351_sound: platform-name_match_allows_probe_without_of_node' \
	'gemini_dts_has_regulator_and_rtc_children_but_no_sound_or_keys_children' \
	'no_runtime_probe_or_register_write_was_performed'
