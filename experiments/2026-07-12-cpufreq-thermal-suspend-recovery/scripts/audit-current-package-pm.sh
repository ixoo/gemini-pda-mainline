#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the packaged MT6797 CPU/thermal/idle boundary. It does
# not change a governor, frequency, voltage, trip, idle state, suspend state,
# CPU online mask, or PMIC/thermal register.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
modules=$package/modules/lib/modules

for file in "$dtb" "$config"; do
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

printf 'validation=mt6797-pm-current-package-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"

printf '\n[configuration]\n'
for symbol in \
	CONFIG_CPU_FREQ \
	CONFIG_CPU_FREQ_DEFAULT_GOV_SCHEDUTIL \
	CONFIG_CPU_IDLE \
	CONFIG_ARM_PSCI_CPUIDLE \
	CONFIG_PM_SLEEP \
	CONFIG_SUSPEND \
	CONFIG_MTK_CPUFREQ \
	CONFIG_MTK_SVS \
	CONFIG_THERMAL \
	CONFIG_MTK_SOC_THERMAL \
	CONFIG_COMMON_CLK_MT6797 \
	CONFIG_COMMON_CLK_MT6797_CAMSYS \
	CONFIG_COMMON_CLK_MT6797_IMGSYS \
	CONFIG_REGULATOR_MT6351; do
	printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_pm_modules]\n'
for module in mediatek-cpufreq-hw mtk-svs auxadc_thermal mt6577_auxadc; do
	path=$(module_path "$module")
	if [[ -n "$path" ]]; then
		printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
	else
		printf 'module=%s\npath=absent\n' "$module"
	fi
done

printf '\n[device_tree]\n'
printf 'psci_nodes=%s\n' "$(count_matches '^[[:space:]]*psci \{' "$dt_source")"
printf 'cpu_nodes=%s\n' "$(count_matches '^[[:space:]]*cpu@[0-9a-f]+ \{' "$dt_source")"
printf 'opp_table_matches=%s\n' "$(count_matches 'operating-points-v2|opp-table' "$dt_source")"
printf 'idle_state_matches=%s\n' "$(count_matches 'idle-states|cpu-idle' "$dt_source")"
printf 'thermal_node_matches=%s\n' \
	"$(count_matches '^[[:space:]]*thermal@1100b000 \{' "$dt_source")"
thermal_disabled=$(rg -n -A 12 '^[[:space:]]*thermal@1100b000 \{' "$dt_source" \
	| rg -c 'status = "disabled"' || true)
printf 'thermal_disabled_status_matches=%s\n' "${thermal_disabled:-0}"
printf 'pm_resource_context:\n'
rg -n -A 13 -B 1 \
	'^(\s*(psci|thermal@1100b000|adc@11001000|cpu-map|cpus) \{)' \
	"$dt_source" | head -n 240 || true

printf '\n[decision]\n'
printf '%s\n' \
	'generic_psci_cpu_topology=present' \
	'mt6797_cpufreq_driver=not_selected' \
	'cpu_opp_table=absent_from_gemini_dtb' \
	'cpu_idle_state_table=absent_from_gemini_dtb' \
	'generic_svs_module=packaged_but_no_mt6797_consumer' \
	'mt6797_thermal_variant=packaged_as_disabled_module_and_node' \
	'mt6797_voltage_pll_calibration=not_enabled' \
	'deep_idle_and_suspend=not_enabled_by_board_dt' \
	'frequency_voltage_transition=not_attempted' \
	'hardware_write=none'
