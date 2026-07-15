#!/usr/bin/env bash
set -euo pipefail

# Read-only GPU inventory for the owner-authorized Gemini device.
# This deliberately does not write any procfs/sysfs control, change clocks,
# bind/unbind a driver, or open a GPU job.

printf '%s\n' 'MT6797 GPU live capture'
printf 'kernel='; uname -a

printf '%s\n' '=== platform GPU links ==='
find /sys/bus/platform/devices -maxdepth 1 -type l 2>/dev/null \
  | grep -Ei '13040000|mali|gpu|mfg' | sort || true

printf '%s\n' '=== GPU devices and interrupts ==='
ls -l /dev/mali* /dev/gpu* 2>/dev/null || true
grep -Ei 'mali|gpu|mfg|262|263|264' /proc/interrupts 2>/dev/null || true

printf '%s\n' '=== device-tree GPU metadata ==='
for f in /proc/device-tree/soc/mali@13040000/compatible \
         /proc/device-tree/soc/mali@13040000/reg \
         /proc/device-tree/soc/mali@13040000/interrupt-names \
         /proc/device-tree/soc/mali@13040000/clock-frequency \
         /proc/device-tree/soc/mali@13040000/clock-names \
         /proc/device-tree/soc/gpufreq/compatible \
         /proc/device-tree/soc/gpufreq/clock-names; do
  [ -f "$f" ] || continue
  printf '%s=' "$f"
  tr '\000' ' ' <"$f" 2>/dev/null | head -c 500 || true
  printf '\n'
done

printf '%s\n' '=== vendor GPU frequency diagnostics ==='
for f in /proc/gpufreq/gpufreq_state \
         /proc/gpufreq/gpufreq_opp_dump \
         /proc/gpufreq/gpufreq_power_dump \
         /proc/gpufreq/gpufreq_var_dump \
         /proc/gpufreq/gpufreq_limited_power \
         /proc/gpufreq/gpufreq_limited_by_pbm \
         /proc/gpufreq/gpufreq_volt_enable; do
  [ -f "$f" ] || continue
  printf '%s\n' "--- $f"
  timeout 2 cat "$f" 2>&1 | head -n 120 || true
done

printf '%s\n' '=== Mali status ==='
for f in /proc/mali/dvfs_enable /proc/mali/frequency \
         /proc/mali/memory_usage /proc/mali/utilization \
         /sys/bus/platform/devices/13040000.mali/gpuinfo \
         /sys/bus/platform/devices/13040000.mali/core_mask \
         /sys/bus/platform/devices/13040000.mali/power_policy \
         /sys/bus/platform/devices/13040000.mali/dvfs_period; do
  [ -f "$f" ] || continue
  printf '%s\n' "--- $f"
  timeout 2 cat "$f" 2>&1 | head -n 80 || true
done

printf '%s\n' '=== GPU driver messages ==='
dmesg 2>/dev/null | grep -Ei 'mali|gpu|mfg|ged|gpufreq' | tail -n 120 || true
