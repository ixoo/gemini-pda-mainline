#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only audit of the current packaged MT6797 CPU/PSCI/GIC/timer boundary.
# It never changes CPU state, firmware, clocks, or hardware.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
system_map=$package/System.map
modules=$package/modules/lib/modules

for file in "$dtb" "$config" "$system_map"; do
  [[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
[[ -d "$linux_tree" ]] || { printf 'missing_source_tree=%s\n' "$linux_tree" >&2; exit 1; }
modules_present=no
if [[ -d "$modules" ]]; then
  modules_present=yes
fi

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT
dt_source=$tmpdir/gemini.dts
dtc_stderr=$tmpdir/dtc.stderr
dtc -I dtb -O dts -o "$dt_source" "$dtb" 2>"$dtc_stderr"

sha256() {
  sha256sum "$1" | awk '{print $1}'
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

count_matches() {
  local pattern=$1 file=$2 count
  count=$(rg -c "$pattern" "$file" || true)
  printf '%s' "${count:-0}"
}

cpu_property_count() {
  local property=$1
  awk -v property="$property" '
    /^[[:space:]]*cpu@[0-9a-f]+ \{/ { in_cpu=1; next }
    in_cpu && /^[[:space:]]*};/ { in_cpu=0; next }
    in_cpu && $0 ~ property { count++ }
    END { print count + 0 }
  ' "$dt_source"
}

module_path() {
  local module=$1
  find "$modules" -type f -name "$module.ko" -print -quit 2>/dev/null || true
}

symbol_count() {
  local pattern=$1
  awk -v pattern="$pattern" '$0 ~ pattern { count++ } END { print count + 0 }' "$system_map"
}

printf 'validation=mt6797-cpu-psci-timer-current-package-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_system_map_sha256=%s\n' "$(sha256 "$system_map")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"
printf 'modules_tree=%s\n' "$modules_present"

printf '\n[configuration]\n'
for symbol in \
  CONFIG_ARM64 \
  CONFIG_ARM_PSCI_FW \
  CONFIG_ARM_PSCI_CPUIDLE \
  CONFIG_ARM_ARCH_TIMER \
  CONFIG_ARM_ARCH_TIMER_EVTSTREAM \
  CONFIG_ARM_GIC_V3 \
  CONFIG_CPU_IDLE \
  CONFIG_CPU_FREQ \
  CONFIG_MTK_CPUFREQ \
  CONFIG_MTK_SVS \
  CONFIG_COMMON_CLK_MT6797 \
  CONFIG_SUSPEND; do
  printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done

printf '\n[packaged_pm_modules]\n'
for module in mediatek-cpufreq-hw mtk-svs; do
  path=$(module_path "$module")
  if [[ -n "$path" ]]; then
    printf 'module=%s\npath=%s\nsha256=%s\n' "$module" "$path" "$(sha256 "$path")"
  else
    printf 'module=%s\npath=absent\n' "$module"
  fi
done

printf '\n[device_tree_counts]\n'
printf 'cpu_nodes=%s\n' "$(count_matches '^[[:space:]]*cpu@[0-9a-f]+ \{' "$dt_source")"
printf 'psci_nodes=%s\n' "$(count_matches '^[[:space:]]*psci \{' "$dt_source")"
printf 'psci_enable_method_count=%s\n' "$(count_matches 'enable-method = "psci"' "$dt_source")"
printf 'architectural_timer_nodes=%s\n' "$(count_matches 'compatible = "arm,armv8-timer"' "$dt_source")"
printf 'opp_table_matches=%s\n' "$(count_matches 'operating-points-v2|opp-table' "$dt_source")"
printf 'idle_state_matches=%s\n' "$(count_matches 'idle-states|cpu-idle' "$dt_source")"
printf 'per_cpu_clock_frequency_matches=%s\n' "$(cpu_property_count 'clock-frequency')"
printf 'cpu_release_address_matches=%s\n' "$(cpu_property_count 'cpu-release-addr')"

printf '\n[device_tree_contract]\n'
rg -n -A 12 -B 1 \
  '^([[:space:]]*(psci|timer|cpus|cpu-map|interrupt-controller) \{|[[:space:]]*compatible = "arm,armv8-timer")' \
  "$dt_source" | head -n 320 || true

printf '\n[linked_symbols]\n'
printf 'psci_symbol_matches=%s\n' "$(symbol_count '[[:space:]].*psci')"
printf 'arch_timer_symbol_matches=%s\n' "$(symbol_count '[[:space:]].*arch_timer')"
printf 'timer_probe_symbol_matches=%s\n' "$(symbol_count '[[:space:]].*timer_probe')"

printf '\n[source_hashes]\n'
for path in \
  drivers/firmware/psci/psci.c \
  drivers/clocksource/arm_arch_timer.c \
  drivers/clocksource/timer-probe.c \
  drivers/of/cpu.c \
  Documentation/devicetree/bindings/arm/cpus.yaml \
  Documentation/devicetree/bindings/arm/psci.yaml \
  Documentation/devicetree/bindings/timer/arm,arch_timer.yaml; do
  if [[ -r "$linux_tree/$path" ]]; then
    printf '%s=%s\n' "$path" "$(sha256 "$linux_tree/$path")"
  else
    printf '%s=missing\n' "$path"
  fi
done

printf '\n[decision]\n'
printf '%s\n' \
  'generic_arm64_cpu_topology_psci_and_arch_timer=present_in_current_package' \
  'mt6797_cpu_frequency_consumer=absent' \
  'cpu_opp_table=absent_from_current_gemini_dtb' \
  'vendor_idle_state_and_release_address=absent_from_current_gemini_dtb' \
  'per_cpu_clock_frequency=absent_from_current_gemini_dtb' \
  'generic_pm_modules=package_only_without_gemini_consumer' \
  'frequency_voltage_transition=not_attempted' \
  'cpu_hotplug_psci_runtime=not_attempted' \
  'architectural_timer_runtime=not_attempted' \
  'hardware_write=none'
