#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# One bounded WLAN DMA-path presence trace; no Wi-Fi control or added MMIO reads.
set -euo pipefail
export LC_ALL=C
umask 077

readonly release=3.18.41-gemini-wifi-ref2+
readonly trace_root=/sys/kernel/debug/tracing
readonly output=/var/tmp/gemini-wifi-reference-dma-presence-v2
readonly functions=(vfs_read kalDevPortRead kalDevPortWrite HifPdmaConfig HifPdmaStart)

fail() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 1 && $1 =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] ||
  fail 'pass the observed v2 boot ID'
readonly boot_id=$1
[[ "$(id -u)" == 0 && "$(uname -m)" == aarch64 &&
   "$(uname -r)" == "$release" &&
   "$(cat /proc/sys/kernel/random/boot_id)" == "$boot_id" ]] ||
  fail 'diagnostic boot identity changed'
[[ "$(cat /sys/class/net/wlan0/carrier)" == 1 ]] || fail 'Wi-Fi lacks carrier'
[[ "$(cat "$trace_root/current_tracer")" == nop &&
   "$(cat "$trace_root/tracing_on")" == 1 &&
   "$(head -n 1 "$trace_root/set_ftrace_filter")" == '#### all functions enabled ####' &&
   "$(cat "$trace_root/buffer_size_kb")" == 7 ]] ||
  fail 'tracer state is not the recorded v2 baseline'
grep -q '\[local\]' "$trace_root/trace_clock" || fail 'trace clock changed'
for function in "${functions[@]}"; do
  grep -Fxq "$function" "$trace_root/available_filter_functions" ||
    fail "required trace function missing: $function"
done
[[ ! -e "$output" && ! -L "$output" ]] || fail 'single-use output already exists'
mkdir -m 0700 "$output"
exec >"$output/control.log" 2>&1

trace_armed=no
cleanup() {
  local status=$?
  trap - EXIT
  set +e
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
  printf 'boot_id=%s\nrelease=%s\nexit_code=%s\ntracer=%s\ncarrier=%s\n' \
    "$(cat /proc/sys/kernel/random/boot_id)" "$(uname -r)" "$status" \
    "$(cat "$trace_root/current_tracer")" \
    "$(cat /sys/class/net/wlan0/carrier 2>/dev/null || echo unavailable)" \
    >"$output/result.txt"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 143' TERM

echo 0 >"$trace_root/tracing_on"
trace_armed=yes
echo mono >"$trace_root/trace_clock"
echo 128 >"$trace_root/buffer_size_kb"
printf '%s\n' "${functions[@]}" >"$trace_root/set_ftrace_filter"
echo function >"$trace_root/current_tracer"
: >"$trace_root/trace"
echo 1 >"$trace_root/tracing_on"
cat /proc/sys/kernel/random/boot_id >/dev/null
touch "$output/armed"
sleep 15
[[ "$(cat /proc/sys/kernel/random/boot_id)" == "$boot_id" ]] ||
  fail 'boot identity changed during trace'
echo 'window=complete'
