#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Static first-boot dependency audit for the exact Gemini package. This script
# decompiles only the packaged DTB and reads the prepared source/configuration;
# it never contacts hardware, binds drivers, or writes a device.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
dtb=$package/dtbs/mediatek/mt6797-gemini-pda.dtb
config=$package/kernel.config
system_map=$package/System.map

for file in "$dtb" "$config" "$system_map"; do
  [[ -r "$file" ]] || { printf 'missing_input=%s\n' "$file" >&2; exit 1; }
done
[[ -d "$linux_tree" ]] || { printf 'missing_source_tree=%s\n' "$linux_tree" >&2; exit 1; }

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
  printf '%s' "${value:-unset}"
}

symbol_state() {
  local symbol=$1
  if rg -q "[[:space:]]${symbol}$" "$system_map"; then
    printf builtin
  else
    printf absent-from-image
  fi
}

dt_string() {
  local node=$1 property=$2 value
  value=$(fdtget -t s "$dtb" "$node" "$property" 2>/dev/null || true)
  if [[ -n "$value" ]]; then
    printf '%s' "$value"
  else
    printf absent
  fi
}

dt_has() {
  local node=$1 property=$2
  if fdtget "$dtb" "$node" "$property" >/dev/null 2>&1; then
    printf yes
  else
    printf no
  fi
}

dt_status() {
  local node=$1 status
  status=$(dt_string "$node" status)
  case "$status" in
    okay|disabled) printf '%s' "$status" ;;
    *) printf implicit-okay ;;
  esac
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

source_hash() {
  local path=$1
  if [[ -r "$linux_tree/$path" ]]; then
    sha256 "$linux_tree/$path"
  else
    printf missing
  fi
}

anchor() {
  local path=$1 pattern=$2
  printf '\n[%s]\n' "$path"
  rg -n "$pattern" "$linux_tree/$path" | tail -n 30 || true
}

printf 'validation=first-boot-probe-dependency-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'config_sha256=%s\n' "$(sha256 "$config")"
printf 'dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"

printf '\n[configuration_and_image]\n'
for mapping in \
  'CONFIG_ARM_PSCI_FW|psci_probe' \
  'CONFIG_ARM_PSCI_CPUIDLE|psci_cpuidle_probe' \
  'CONFIG_ARM_ARCH_TIMER|arch_timer_of_init' \
  'CONFIG_ARM_GIC_V3|gic_of_init' \
  'CONFIG_CPU_IDLE|cpuidle_init' \
  'CONFIG_SERIAL_8250_MT6577|mtk8250_probe' \
  'CONFIG_PINCTRL_MT6797|mt6797_pinctrl_init' \
  'CONFIG_MEDIATEK_WATCHDOG|mtk_wdt_probe' \
  'CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED|watchdog_dev_register' \
  'CONFIG_MTK_PMIC_WRAP|pwrap_probe' \
  'CONFIG_MFD_MT6397|mt6397_probe' \
  'CONFIG_REGULATOR_MT6351|mt6351_regulator_probe' \
  'CONFIG_MMC_MTK|msdc_drv_probe'; do
  IFS='|' read -r symbol probe <<< "$mapping"
  printf '%s=%s|probe=%s|image=%s\n' "$symbol" "$(config_state "$symbol")" \
    "$probe" "$(symbol_state "$probe")"
done
printf '\n[device_tree_status]\n'
for node in \
  /psci \
  /timer \
  /cpus \
  /pwrap@1000d000 \
  /pwrap@1000d000/pmic \
  /pwrap@1000d000/pmic/regulators \
  /pwrap@1000d000/pmic/regulators/ldo-vemc \
  /pwrap@1000d000/pmic/regulators/ldo-vio18 \
  /serial@11002000 \
  /mmc@11230000 \
  /mmc@11240000 \
  /watchdog@10007000; do
  printf '%s|status=%s|compatible=%s\n' "$node" "$(dt_status "$node")" \
    "$(dt_string "$node" compatible)"
done
printf '/cpus|cpu_nodes=%s|psci_enable_methods=%s|per_cpu_clock_frequency=%s|idle_state_refs=%s\n' \
  "$(count_matches '^[[:space:]]*cpu@[0-9a-f]+ \{' "$dt_source")" \
  "$(count_matches 'enable-method = \"psci\"' "$dt_source")" \
  "$(cpu_property_count 'clock-frequency')" \
  "$(count_matches 'cpu-idle-states|idle-states' "$dt_source")"
printf '/timer|arch_timer_compatible=%s|interrupt_property=%s\n' \
  "$(count_matches 'compatible = \"arm,armv8-timer\"' "$dt_source")" \
  "$(dt_has /timer interrupts)"
printf '/mmc@11230000|vmmc_supply_phandle=%s|vqmmc_supply_phandle=%s|bus_width=%s|max_frequency=%s\n' \
  "$(fdtget -t x "$dtb" /mmc@11230000 vmmc-supply 2>/dev/null || printf absent)" \
  "$(fdtget -t x "$dtb" /mmc@11230000 vqmmc-supply 2>/dev/null || printf absent)" \
  "$(fdtget -t x "$dtb" /mmc@11230000 bus-width 2>/dev/null || printf absent)" \
  "$(fdtget -t x "$dtb" /mmc@11230000 max-frequency 2>/dev/null || printf absent)"
printf '/ldo-vemc|name=%s|min=%s|max=%s|boot_on=%s\n' \
  "$(dt_string /pwrap@1000d000/pmic/regulators/ldo-vemc regulator-name)" \
  "$(fdtget -t x "$dtb" /pwrap@1000d000/pmic/regulators/ldo-vemc regulator-min-microvolt 2>/dev/null || printf absent)" \
  "$(fdtget -t x "$dtb" /pwrap@1000d000/pmic/regulators/ldo-vemc regulator-max-microvolt 2>/dev/null || printf absent)" \
  "$(dt_has /pwrap@1000d000/pmic/regulators/ldo-vemc regulator-boot-on)"
printf '/ldo-vio18|name=%s|min=%s|max=%s|always_on=%s\n' \
  "$(dt_string /pwrap@1000d000/pmic/regulators/ldo-vio18 regulator-name)" \
  "$(fdtget -t x "$dtb" /pwrap@1000d000/pmic/regulators/ldo-vio18 regulator-min-microvolt 2>/dev/null || printf absent)" \
  "$(fdtget -t x "$dtb" /pwrap@1000d000/pmic/regulators/ldo-vio18 regulator-max-microvolt 2>/dev/null || printf absent)" \
  "$(dt_has /pwrap@1000d000/pmic/regulators/ldo-vio18 regulator-always-on)"

printf '\n[probe_source_anchors]\n'
anchor drivers/soc/mediatek/mtk-pmic-wrap.c \
  '\bstatic int pwrap_probe|devm_clk_bulk_get_all_enabled|PWRAP_INIT_DONE2|PWRAP_WDT_SRC_EN|PWRAP_TIMER_EN|PWRAP_INT_EN|of_platform_populate'
anchor drivers/tty/serial/8250/8250_mtk.c \
  '\bstatic int mtk8250_probe|devm_clk_get_enabled|serial8250_register_8250_port'
anchor drivers/watchdog/mtk_wdt.c \
  '\bstatic int mtk_wdt_probe|mtk_wdt_init|mtk_wdt_set_timeout|mtk_wdt_ping|WDT_MODE_EN|devm_request_irq'
anchor drivers/watchdog/watchdog_dev.c \
  'handle_boot_enabled|watchdog_hw_running|hrtimer_start|__watchdog_ping'
anchor drivers/mfd/mt6397-core.c \
  '\bstatic int mt6397_probe|regmap_read\(pmic->regmap|mt6397_irq_init|devm_mfd_add_devices'
anchor drivers/mfd/mt6397-irq.c \
  'Mask all interrupt sources|regmap_write\(chip->regmap, chip->int_con|devm_request_threaded_irq'
anchor drivers/regulator/mt6351-regulator.c \
  '\bstatic int mt6351_regulator_probe|regmap_read\(mt6351->regmap|devm_regulator_register'
anchor drivers/mmc/host/mtk-sd.c \
  '\bstatic int msdc_drv_probe|mmc_regulator_get_supply|regulator_enable\(mmc->supply.vqmmc|mmc_regulator_set_ocr'

printf '\n[source_hashes]\n'
for path in \
  arch/arm64/boot/dts/mediatek/mt6797.dtsi \
  arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts \
  drivers/firmware/psci/psci.c \
  drivers/clocksource/arm_arch_timer.c \
  drivers/clocksource/timer-probe.c \
  drivers/of/cpu.c \
  drivers/tty/serial/8250/8250_mtk.c \
  drivers/watchdog/mtk_wdt.c \
  drivers/watchdog/watchdog_dev.c \
  drivers/soc/mediatek/mtk-pmic-wrap.c \
  drivers/mfd/mt6397-core.c \
  drivers/mfd/mt6397-irq.c \
  drivers/regulator/mt6351-regulator.c \
  drivers/mmc/host/mtk-sd.c; do
  printf '%s=%s\n' "$path" "$(source_hash "$path")"
done

printf '\n[decision]\n'
printf '%s\n' \
  'first_boot_chain=arm64_entry -> gic|psci|arch_timer -> uart0|pinctrl_and_clocks -> pwrap -> mt6351_mfd_and_regulator -> mmc0' \
  'generic_arm64_cpu_psci_timer_support_is_built_in_before_board_consumers' \
  'eMMC_supply_consumers_make_PMIC_part_of_storage_probe' \
  'uart_probe_enables_baud_and_bus_clocks_then_registers_8250_port' \
  'watchdog_probe_reads_MODE_and_if_firmware_enabled_rewrites_LENGTH_and_pings' \
  'WATCHDOG_HANDLE_BOOT_ENABLED_starts_kernel_ping_worker_for_boot_running_watchdog' \
  'pwrap_probe_is_stateful_even_when_INIT_DONE2_is_already_set' \
  'mt6397_irq_init_writes_all_four_MT6351_interrupt_mask_banks' \
  'mt6351_regulator_probe_reads_revision_and_vsel_control_without_selecting_a_rail' \
  'mmc_power_transition_may_enable_vemc_and_vio18_after_host_registration' \
  'first_runtime_test_requires_external_recovery_and_before_after_register_capture' \
  'runtime_mainline_boot=not_attempted' \
  'hardware_write=none'
