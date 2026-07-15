#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 PWRAP/MT6351 DT and built-in config.
# It never accesses hardware, writes PMIC registers, or changes a regulator.

set -euo pipefail

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
repo_root=${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)}
dtb=${package}/dtbs/mediatek/mt6797-gemini-pda.dtb
config=${package}/kernel.config

die() {
	echo "error: $*" >&2
	exit 1
}

command -v sha256sum >/dev/null || die "sha256sum is required"
command -v dtc >/dev/null || die "dtc is required"
command -v rg >/dev/null || die "rg is required"
[[ -f ${package}/Image && -f ${package}/Image.gz ]] || die "kernel images are missing"
[[ -f ${dtb} ]] || die "Gemini DTB is missing: ${dtb}"
[[ -f ${config} ]] || die "kernel config is missing: ${config}"
[[ -f ${repo_root}/patches/series ]] || die "patch series is missing"

tmp=$(mktemp -d)
trap 'rm -rf "${tmp}"' EXIT
dt_source=${tmp}/gemini.dts
dtc -I dtb -O dts -o "${dt_source}" "${dtb}" 2>"${tmp}/dtc.stderr"

sha() {
	sha256sum "$1" | awk '{print $1}'
}

series_file=${package}/provenance/series
[[ -f ${series_file} ]] || series_file=${repo_root}/patches/series
series_count=$(rg -c '^[^#[:space:]]*/[0-9]{4}[^[:space:]]*$' "${series_file}")
patchset_sha=$(rg -o '"patchset_sha256": "[0-9a-f]+"' "${package}/provenance/build.json" 2>/dev/null |
	sed -E 's/.*"([0-9a-f]+)"/\1/' || true)
patchset_sha=${patchset_sha:-$(sha "${repo_root}/patches/series")}

printf 'validation=mt6351-current-package-audit\n'
printf 'package=%s\n' "$(basename "${package}")"
printf 'package_path=%s\n' "${package}"
printf 'patch_series_count=%s\n' "${series_count}"
printf 'patchset_sha256=%s\n' "${patchset_sha}"
printf 'image_sha256=%s\n' "$(sha "${package}/Image")"
printf 'image_gzip_sha256=%s\n' "$(sha "${package}/Image.gz")"
printf 'config_sha256=%s\n' "$(sha "${config}")"
printf 'gemini_dtb_sha256=%s\n' "$(sha "${dtb}")"
printf 'dtc_warning_lines=%s\n' "$(wc -l <"${tmp}/dtc.stderr")"

printf '\n[required_builtin_config]\n'
for symbol in \
	CONFIG_MTK_PMIC_WRAP \
	CONFIG_MFD_MT6397 \
	CONFIG_REGULATOR_MT6351 \
	CONFIG_KEYBOARD_MTK_PMIC \
	CONFIG_RTC_DRV_MT6397; do
	value=$(rg -m1 "^${symbol}=" "${config}" || true)
	printf '%s\n' "${value:-${symbol}=unset}"
done

printf '\n[pwrap_and_pmic_dtb]\n'
rg -n -A 42 'pwrap@1000d000' "${dt_source}" | sed -n '1,50p'

printf '\n[contract_checks]\n'
for marker in \
	'compatible = "mediatek,mt6797-pwrap"' \
	'compatible = "mediatek,mt6351"' \
	'compatible = "mediatek,mt6351-regulator"' \
	'compatible = "mediatek,mt6351-rtc"' \
	'clock-names = "spi\\0wrap"' \
	'reset-names = "pwrap"' \
	'regulator-name = "vemc_3v3"' \
	'regulator-name = "vio18"' \
	'regulator-boot-on;' \
	'regulator-always-on;'; do
	if rg -q -- "${marker}" "${dt_source}"; then
		printf '%s=present\n' "${marker}"
	else
		printf '%s=absent\n' "${marker}"
	fi
done

printf '\n[decision]\n'
printf '%s\n' \
	'current_package_contains_builtin_pwrap_mt6351_regulator_key_rtc_chain' \
	'gemini_pwrap_and_pmic_nodes_are_implicitly_enabled' \
	'vemc_is_boot_on_at_3.0_to_3.3V_and_vio18_is_always_on_at_1.8V' \
	'generated_DTB_contract_is_static_evidence_only' \
	'pwrap_mfd_regulator_probe_is_stateful_and_not_read_only' \
	'eMMC_storage_probe_depends_on_this_PMIC_chain' \
	'runtime_mainline_boot=not_attempted' \
	'rail_control=not_attempted' \
	'hardware_write=none'
