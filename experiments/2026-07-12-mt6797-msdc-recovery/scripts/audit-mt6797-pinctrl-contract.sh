#!/usr/bin/env bash

# Audit the MT6797 pinconf surface against the Gemini MSDC device-tree patch.
# This is source-only: it reads the prepared Linux tree and patch text and
# never accesses device registers or changes hardware state.

set -euo pipefail
export LC_ALL=C

linux_tree=${1:-${HOME}/src/gemini-pda/linux-7.1.3}
repo_root=${2:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}
pinctrl_file=${linux_tree}/drivers/pinctrl/mediatek/pinctrl-mt6797.c
base_patch=${repo_root}/patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch
fix_patch=${repo_root}/patches/v7.1.3/0071-arm64-dts-mediatek-gemini-use-pinmux-only-for-MT6797-MSDC.patch

for path in "${pinctrl_file}" "${base_patch}" "${fix_patch}"; do
	[[ -r "${path}" ]] || {
		printf 'missing input: %s\n' "${path}" >&2
		exit 1
	}
done

printf 'audit=mt6797-pinctrl-msdc\n'
printf 'linux_tree=%s\n' "${linux_tree}"
printf 'pinctrl_sha256=%s\n' "$(sha256sum "${pinctrl_file}" | awk '{print $1}')"
printf 'base_dts_patch_sha256=%s\n' "$(sha256sum "${base_patch}" | awk '{print $1}')"
printf 'pinmux_only_fix_patch_sha256=%s\n' "$(sha256sum "${fix_patch}" | awk '{print $1}')"

printf '\n[mt6797 register maps]\n'
sed -n '/static const struct mtk_pin_reg_calc mt6797_reg_cals/,/};/p' \
	"${pinctrl_file}"

printf '\n[mt6797 pinconf callbacks]\n'
if grep -qE 'bias_(set|set_combo)|drive_(set|set_combo)|adv_drive_set|spec_pull_set' \
	"${pinctrl_file}"; then
	printf 'descriptor_callbacks=present\n'
else
	printf 'descriptor_callbacks=absent\n'
fi

printf '\n[base Gemini MSDC pinconf]\n'
grep -nE 'input-enable|drive-strength|bias-pull-(up|down)' "${base_patch}" || true

printf '\n[follow-up patch removals]\n'
grep -nE '^[+-].*(input-enable|drive-strength|bias-pull-(up|down))' "${fix_patch}" || true

printf '\n[decision]\n'
printf '%s\n' \
	'Linux 7.1.3 can parse generic pinconf syntax, but MT6797 has no source-backed pull, IES, or drive register maps/callbacks.' \
	'Keep the first Gemini MSDC state pinmux-only and retain boot-firmware pad configuration.' \
	'Revisit pinconf only after recovering and validating MT6797-specific register fields; do not infer them from a neighboring SoC.'
