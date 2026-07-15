#!/usr/bin/env bash
set -euo pipefail

# Read-only provider inventory for the owner-authorized Gemini device.
# Do not add writes here: clock debugfs contains control files on some vendor
# kernels, and power/reset operations can make the device unbootable.

printf '%s\n' 'MT6797 clock/power/reset live capture'
printf 'kernel='; uname -a

printf '%s\n' '=== debugfs and provider paths ==='
grep -E 'debugfs|sysfs' /proc/mounts || true
find /sys/kernel/debug -maxdepth 2 \( -type f -o -type l \) 2>/dev/null \
  | grep -Ei 'clk|power|spm|scpsys|pwr|reset|mfg|mm|infra|regulator' \
  | sort | head -n 320 || true

printf '%s\n' '=== platform provider links ==='
for pattern in '10006000*' '10001000*' '13000000*' '14000000*' \
               '11230000*' '11240000*' '13040000*'; do
  find /sys/bus/platform/devices -maxdepth 1 -type l -name "$pattern" \
    -print 2>/dev/null || true
done

printf '%s\n' '=== clock summary ==='
if [ -r /sys/kernel/debug/clk/clk_summary ]; then
  timeout 5 cat /sys/kernel/debug/clk/clk_summary || true
fi

printf '%s\n' '=== clock orphan summary ==='
if [ -r /sys/kernel/debug/clk/clk_orphan_summary ]; then
  timeout 3 cat /sys/kernel/debug/clk/clk_orphan_summary || true
fi

printf '%s\n' '=== SPM read-only diagnostics ==='
for f in /sys/kernel/debug/spm/scp_debug /sys/kernel/debug/spm/firmware; do
  [ -r "$f" ] || continue
  printf '%s\n' "--- $f"
  timeout 3 cat "$f" 2>&1 | head -n 220 || true
done

printf '%s\n' '=== regulator supply map ==='
if [ -r /sys/kernel/debug/regulator/supply_map ]; then
  timeout 3 cat /sys/kernel/debug/regulator/supply_map || true
fi

printf '%s\n' '=== selected device-tree provider metadata ==='
for node in /proc/device-tree/soc/scpsys \
            /proc/device-tree/soc/mali@13040000 \
            /proc/device-tree/soc/g3d_config@13000000 \
            /proc/device-tree/soc/mm@14000000; do
  [ -d "$node" ] || continue
  printf 'node=%s\n' "$node"
  for f in compatible reg reg-names clock-names power-domains status; do
    [ -f "$node/$f" ] || continue
    printf '%s=' "$f"
    tr '\000' ' ' <"$node/$f" 2>/dev/null | head -c 800 || true
    printf '\n'
  done
done

printf '%s\n' '=== selected runtime PM metadata ==='
for d in /sys/bus/platform/devices/13040000.mali \
         /sys/bus/platform/devices/14000000.mmsys_config \
         /sys/bus/platform/devices/11230000.mmc \
         /sys/bus/platform/devices/11240000.mmc; do
  [ -d "$d/power" ] || continue
  printf 'device=%s\n' "$d"
  for f in "$d/power"/runtime_status "$d/power"/runtime_active_time \
           "$d/power"/runtime_suspended_time "$d/power"/control; do
    [ -r "$f" ] || continue
    printf '%s=' "${f##*/}"
    timeout 1 cat "$f" 2>/dev/null || true
  done
done
