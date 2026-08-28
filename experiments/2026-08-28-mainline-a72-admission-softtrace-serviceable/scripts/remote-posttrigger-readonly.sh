#!/bin/sh

# Read back the terminal one-shot state and the bounded arm64 late-CPU boot
# diagnostics. This script is storage-inert and never retries the trigger.
set -eu
export LC_ALL=C
BB=/bin/busybox
STATUS=/sys/bus/platform/devices/a72-admission-controller/gemini_admission/status

$BB printf '%s\n' __GEMINI_A72_LIVE_POSTTRIGGER_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'live_status='; $BB cat "$STATUS" 2>/dev/null || $BB printf 'unreadable\n'
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf '%s\n' late_cpu_dmesg_begin
$BB dmesg | $BB grep -Ei 'late.?cpu|mt6797-psci' | $BB tail -n 80 || true
$BB printf '%s\n' late_cpu_dmesg_end
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' sysfs_write_request=none
$BB printf '%s\n' cpu_admission_request=none
$BB printf '%s\n' cpu_off_request=none
$BB printf '%s\n' retry_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __GEMINI_A72_LIVE_POSTTRIGGER_END__
