#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged Gemini kernel's MSDC/eMMC boundary.
# This checks package metadata and the generated DTB; it never accesses a
# device, mounts storage, binds a driver, or changes hardware state.

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

printf 'validation=mt6797-msdc-current-package-audit\n'
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
	CONFIG_MMC \
	CONFIG_MMC_MTK \
	CONFIG_PINCTRL_MT6797 \
	CONFIG_MTK_PMIC_WRAP \
	CONFIG_MFD_MT6397 \
	CONFIG_REGULATOR_MT6351; do
	value=$(rg -m1 "^${symbol}=" "${config}" || true)
	printf '%s\n' "${value:-${symbol}=unset}"
done

printf '\n[gemini_msdc0_dtb]\n'
rg -n -A 36 'mmc@11230000' "${dt_source}" | sed -n '1,42p'

printf '\n[gemini_msdc1_dtb]\n'
rg -n -A 12 'mmc@11240000' "${dt_source}" | sed -n '1,18p'

printf '\n[contract_checks]\n'
for marker in \
	'max-frequency = <0x17d7840>' \
	'bus-width = <0x0*8>' \
	'non-removable;' \
	'no-sd;' \
	'no-sdio;' \
	'vmmc-supply = <0x' \
	'vqmmc-supply = <0x'; do
	if rg -q -- "${marker}" "${dt_source}"; then
		printf '%s=present\n' "${marker}"
	else
		printf '%s=absent\n' "${marker}"
	fi
done

for marker in mmc-hs200-1_8v mmc-hs400-1_8v cap-mmc-highspeed; do
	if rg -q -- "${marker}" "${dt_source}"; then
		printf '%s=present\n' "${marker}"
	else
		printf '%s=absent\n' "${marker}"
	fi
done

printf '\n[decision]\n'
printf '%s\n' \
	'current_package_contains_builtin_mmc_pmic_pinctrl_chain' \
	'current_gemini_node_is_conservative_8bit_nonremovable_25mhz_eMMC' \
	'mmc1_remains_disabled_and_no_high_speed_flags_are_declared' \
	'generated_DTB_contract_is_static_evidence_only' \
	'mmc_probe_is_stateful: clocks_registers_IRQ_regulators_and_card_identification' \
	'first_storage_test_requires_non_primary_boot_external_recovery_and_read_only_policy' \
	'runtime_mainline_boot=not_attempted' \
	'hardware_write=none'
