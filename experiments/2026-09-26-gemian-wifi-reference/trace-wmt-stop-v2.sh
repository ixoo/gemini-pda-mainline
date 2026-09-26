#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# One v2 stop-decision trace with a disconnected WLAN interface.
set -euo pipefail
export LC_ALL=C
umask 077

readonly expected_release=3.18.41-gemini-wifi-ref2+
readonly trace_root=/sys/kernel/debug/tracing
readonly output=/var/tmp/gemini-wifi-reference-wmt-stop-v2
readonly wifi_device=/dev/wmtWifi
readonly functions=(
  WIFI_write wmt_func_wifi_off wmt_func_wifi_on
  wlanRemove wlanStop wlanAdapterStop wlanSendNicPowerCtrlCmd wlanPowerOffInt
  wlanProbe kalFirmwareOpen kalFirmwareLoad kalFirmwareClose
  mtk_wcn_consys_hw_pwr_off mtk_wcn_consys_hw_pwr_on
  mtk_wcn_consys_hw_reg_ctrl wmt_plat_pwr_ctrl
  emi_mpu_set_region_protection mt_emi_mpu_set_region_protection
)

fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 1 && $1 =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] ||
  fail 'pass the observed v2 boot ID'
readonly expected_boot=$1
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 &&
   "$(uname -r)" == "$expected_release" &&
   "$(cat /proc/sys/kernel/random/boot_id)" == "$expected_boot" ]] ||
  fail 'diagnostic boot identity changed'
[[ "$(cat /sys/class/net/wlan0/carrier)" == 1 ]] || fail 'Wi-Fi lacks starting carrier'
[[ -c "$wifi_device" && "$(stat -c '%t:%T' "$wifi_device")" == 99:0 ]] ||
  fail 'WMT Wi-Fi control node changed'
[[ "$(cat /sys/class/power_supply/battery/present)" == 1 &&
   "$(cat /sys/class/power_supply/battery/health)" == Good ]] ||
  fail 'battery gate failed'
capacity=$(cat /sys/class/power_supply/battery/capacity)
[[ "$capacity" =~ ^[0-9]+$ ]] || fail 'battery capacity malformed'
(( capacity >= 40 )) || fail 'battery capacity too low'
[[ "$(cat "$trace_root/current_tracer")" == nop &&
   "$(cat "$trace_root/tracing_on")" == 1 ]] || fail 'another trace is active'
[[ "$(head -n 1 "$trace_root/set_ftrace_filter")" == '#### all functions enabled ####' ]] ||
  fail 'function filter is in use'
for function in "${functions[@]}"; do
  grep -Fxq "$function" "$trace_root/available_filter_functions" ||
    fail "required trace function missing: $function"
done
grep -Fxq vfs_read "$trace_root/available_filter_functions" ||
  fail 'function tracer control target missing'
for command in timeout connmanctl iw; do
  command -v "$command" >/dev/null || fail "required command missing: $command"
done
[[ ! -e "$output" && ! -L "$output" ]] || fail 'single-use output already exists'
mkdir -m 0700 "$output"
exec >"$output/control.log" 2>&1

trace_armed=no
connman_disabled=no
connman_enable_calls=0
wmt_off_attempted=no
wmt_on_attempts=0
disconnected_before_wmt=no
cleanup() {
  local status=$?
  trap - EXIT
  set +e
  if [[ "$wmt_off_attempted" == yes && "$wmt_on_attempts" == 0 ]]; then
    wmt_on_attempts=1
    timeout 15 bash -c 'printf 1 > /dev/wmtWifi'
  fi
  if [[ "$connman_disabled" == yes && "$connman_enable_calls" == 0 ]]; then
    connman_enable_calls=1
    timeout 15 connmanctl enable wifi
  fi
  if [[ "$trace_armed" == yes ]]; then
    echo 0 >"$trace_root/tracing_on"
    cat "$trace_root/trace" >"$output/trace.log"
    for file in "$trace_root"/per_cpu/cpu*/stats; do
      [[ ! -r "$file" ]] || { printf '%s\n' "$file"; cat "$file"; }
    done >"$output/trace-stats.txt"
    echo nop >"$trace_root/current_tracer"
    : >"$trace_root/set_ftrace_filter"
    echo local >"$trace_root/trace_clock"
    echo 7 >"$trace_root/buffer_size_kb"
    echo 1 >"$trace_root/tracing_on"
  fi
  dmesg >"$output/dmesg-after.log"
  connmanctl technologies >"$output/technologies-after.txt"
  {
    printf 'boot_id=%s\nrelease=%s\nexit_code=%s\n' \
      "$(cat /proc/sys/kernel/random/boot_id)" "$(uname -r)" "$status"
    printf 'disconnected_before_wmt=%s\nwmt_off_attempted=%s\nwmt_on_attempts=%s\n' \
      "$disconnected_before_wmt" "$wmt_off_attempted" "$wmt_on_attempts"
    printf 'connman_disabled=%s\nconnman_enable_calls=%s\n' \
      "$connman_disabled" "$connman_enable_calls"
    printf 'carrier=%s\n' "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unavailable)"
    printf 'current_tracer=%s\n' "$(cat "$trace_root/current_tracer")"
  } >"$output/result.txt"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM

dmesg >"$output/dmesg-before.log"
connmanctl technologies >"$output/technologies-before.txt"
echo 0 >"$trace_root/tracing_on"
trace_armed=yes
echo mono >"$trace_root/trace_clock"
echo 128 >"$trace_root/buffer_size_kb"
echo vfs_read >"$trace_root/set_ftrace_filter"
echo function >"$trace_root/current_tracer"
: >"$trace_root/trace"
echo 1 >"$trace_root/tracing_on"
cat /proc/sys/kernel/random/boot_id >/dev/null
echo 0 >"$trace_root/tracing_on"
cat "$trace_root/trace" >"$output/positive-control.log"
grep -q vfs_read "$output/positive-control.log" ||
  fail 'function tracer did not record positive control'
printf '%s\n' "${functions[@]}" >"$trace_root/set_ftrace_filter"
: >"$trace_root/trace"
echo 1 >"$trace_root/tracing_on"

connman_disabled=yes
timeout 15 connmanctl disable wifi
disconnected_samples=0
for _ in {1..25}; do
  if [[ "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0)" == 0 ]] &&
     iw dev wlan0 link | grep -Fxq 'Not connected.'; then
    (( disconnected_samples += 1 ))
  else
    disconnected_samples=0
  fi
  (( disconnected_samples >= 3 )) && break
  sleep 1
done
(( disconnected_samples >= 3 )) || fail 'association did not clear before WMT removal'
disconnected_before_wmt=yes

wmt_off_attempted=yes
timeout 15 bash -c 'printf 0 > /dev/wmtWifi'
for _ in {1..20}; do
  [[ ! -e /sys/class/net/wlan0 ]] && break
  sleep 1
done
[[ ! -e /sys/class/net/wlan0 ]] || fail 'WLAN netdev remained after WMT off'

wmt_on_attempts=1
timeout 15 bash -c 'printf 1 > /dev/wmtWifi'
for _ in {1..30}; do
  [[ -e /sys/class/net/wlan0 ]] && break
  sleep 1
done
[[ -e /sys/class/net/wlan0 ]] || fail 'WLAN netdev did not return after WMT on'

connman_enable_calls=1
timeout 15 connmanctl enable wifi
for _ in {1..90}; do
  [[ "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0)" == 1 ]] && break
  sleep 1
done
[[ "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo 0)" == 1 ]] ||
  fail 'Wi-Fi carrier did not return after ConnMan enable'
echo 'cycle=carrier-restored'
