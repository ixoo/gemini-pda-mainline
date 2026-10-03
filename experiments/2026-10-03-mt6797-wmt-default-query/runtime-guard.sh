#!/bin/sh
# SPDX-License-Identifier: MIT
# Embedded by capture-private.py after its exact boot/release checks.
BB=${BB:-/bin/busybox}
$BB grep -Eq '(^|[[:space:]])console=ttyS0,921600n8([[:space:]]|$)' /proc/cmdline || exit 20
$BB grep -Eq '^ttyS0[[:space:]].*\([^)]*E[^)]*\)' /proc/consoles || exit 21
[ "$($BB readlink -f /sys/bus/platform/devices/11002000.serial/driver)" = /sys/bus/platform/drivers/mt6577-uart ] || exit 22
[ "$($BB cat /sys/bus/platform/devices/11002000.serial/power/runtime_status)" = active ] || exit 23
clock=/sys/kernel/debug/clk/infra_ap_dma
if [ ! -r "$clock/clk_prepare_count" ] || [ ! -r "$clock/clk_enable_count" ]; then
    [ "${ALLOW_DEBUGFS_MOUNT:-0}" = 1 ] || exit 24
    [ -d /sys/kernel/debug ] || exit 25
    [ "$($BB grep -c ' /sys/kernel/debug ' /proc/mounts)" = 0 ] || exit 26
    $BB mount -t debugfs -o ro debugfs /sys/kernel/debug || exit 27
fi
[ "$($BB grep -c '^debugfs /sys/kernel/debug debugfs ro,' /proc/mounts)" = 1 ] || exit 28
for counter in clk_prepare_count clk_enable_count; do
    value=$($BB cat "$clock/$counter") || exit 29
    case "$value" in ''|*[!0-9]*) exit 29 ;; esac
    [ "$value" -gt 0 ] || exit 29
done
