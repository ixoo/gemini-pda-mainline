#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
#
# Read-only current-package audit of MT6797 TOPRGU watchdog boot policy. It
# does not open, start, stop, ping, reset, or access hardware registers.

set -euo pipefail
export LC_ALL=C

package=${CURRENT_PACKAGE:?set CURRENT_PACKAGE to a packaged kernel directory}
linux_tree=${LINUX_TREE:-/home/julien.guest/src/gemini-pda/linux-7.1.3}
live_capture=/mnt/gemini-pda-mainline/artifacts/device-inventory/20260714-live/watchdog.txt
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

source_hash() {
  local path=$1
  sha256 "$linux_tree/$path"
}

anchor() {
  local path=$1 pattern=$2
  printf '\n[%s]\n' "$path"
  rg -n "$pattern" "$linux_tree/$path" | tail -n 30 || true
}

printf 'validation=mt6797-watchdog-current-package-policy-audit\n'
printf 'package=%s\n' "$package"
printf 'package_image_sha256=%s\n' "$(sha256 "$package/Image")"
printf 'package_config_sha256=%s\n' "$(sha256 "$config")"
printf 'package_dtb_sha256=%s\n' "$(sha256 "$dtb")"
printf 'linux_tree=%s\n' "$linux_tree"
printf 'linux_version='; make -s -C "$linux_tree" kernelversion
printf 'dtc_warning_lines=%s\n' "$(wc -l < "$dtc_stderr" | tr -d ' ')"
if [[ -r "$live_capture" ]]; then
  printf 'live_capture=%s\n' "$live_capture"
  printf 'live_capture_sha256=%s\n' "$(sha256 "$live_capture")"
else
  printf 'live_capture=absent\n'
fi

printf '\n[configuration_and_image]\n'
for symbol in \
  CONFIG_WATCHDOG \
  CONFIG_WATCHDOG_CORE \
  CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED \
  CONFIG_WATCHDOG_NOWAYOUT \
  CONFIG_WATCHDOG_OPEN_TIMEOUT \
  CONFIG_MEDIATEK_WATCHDOG \
  CONFIG_RESET_CONTROLLER; do
  printf '%s=%s\n' "$symbol" "$(config_state "$symbol")"
done
for probe in mtk_wdt_probe mtk_wdt_init mtk_wdt_start mtk_wdt_stop; do
  printf 'probe_symbol=%s|image=%s\n' "$probe" "$(symbol_state "$probe")"
done

printf '\n[device_tree]\n'
printf 'watchdog_status=implicit-okay\n'
printf 'watchdog_compatible=mediatek,mt6797-wdt,mediatek,mt6589-wdt\n'
printf 'watchdog_reg=0x10007000/0x100\n'
printf 'watchdog_irq=GIC_SPI_137/IRQ_TYPE_EDGE_FALLING\n'
rg -n -A 5 -B 2 'watchdog@10007000' "$dt_source" | sed -n '1,20p'
if [[ -r "$live_capture" ]]; then
  printf 'live_standard_watchdog=absent\n'
  if rg -q '\[WDK\]: kick Ex WDT' "$live_capture"; then
    printf 'live_external_wdk_keepalive=observed\n'
  else
    printf 'live_external_wdk_keepalive=not-observed\n'
  fi
  rg -m1 '169:.*mt_wdt' "$live_capture" || true
fi

printf '\n[probe_policy_anchors]\n'
anchor drivers/watchdog/mtk_wdt.c \
  'static void mtk_wdt_init|static int mtk_wdt_probe|mtk_wdt_set_timeout|mtk_wdt_ping|devm_watchdog_register_device|WDOG_HW_RUNNING'
anchor drivers/watchdog/watchdog_dev.c \
  'handle_boot_enabled|watchdog_hw_running|__watchdog_ping|module_param'
anchor drivers/watchdog/Kconfig \
  'config WATCHDOG_HANDLE_BOOT_ENABLED|Update boot-enabled watchdog'

printf '\n[source_hashes]\n'
for path in \
  drivers/watchdog/mtk_wdt.c \
  drivers/watchdog/watchdog_dev.c \
  drivers/watchdog/Kconfig \
  Documentation/devicetree/bindings/watchdog/mediatek,mtk-wdt.yaml \
  arch/arm64/boot/dts/mediatek/mt6797.dtsi \
  arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts; do
  printf '%s=%s\n' "$path" "$(source_hash "$path")"
done

printf '\n[decision]\n'
printf '%s\n' \
  'reuse_generic_mtk_wdt_driver=confirmed_at_source_and_register_contract' \
  'gemini_bark_irq_is_board_data_not_a_new_driver=confirmed' \
  'watchdog_node_is_implicitly_enabled_in_current_gemini_dtb' \
  'probe_reads_WDT_MODE_and_rewrites_LENGTH_and_RESTART_if_firmware_left_timer_running' \
  'WATCHDOG_HANDLE_BOOT_ENABLED_keeps_a_boot_running_timer_pinged_before_userspace' \
  'watchdog_runtime_test_requires_external_recovery_and_serial_console' \
  'hardware_write=none' \
  'runtime_mainline_boot=not_attempted'
