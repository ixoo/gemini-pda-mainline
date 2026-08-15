#!/bin/sh

# Read the exact runtime provenance ABI twice. This script is streamed to the
# boot2 initramfs shell and performs no writes, mounts, or power-state changes.
set -eu
export LC_ALL=C

readonly STATE=/sys/kernel/debug/gemini_dvfsp_provenance/state
readonly INSTALLED_FULL_SHA256=ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02

printf '%s\n' '__GEMINI_PROVENANCE_RUNTIME_BEGIN__'
printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
printf 'kernel_release=%s\n' "$(/bin/busybox uname -r)"
printf 'architecture=%s\n' "$(/bin/busybox uname -m)"
printf 'boot_id=%s\n' "$(/bin/busybox cat /proc/sys/kernel/random/boot_id 2>/dev/null || printf unavailable)"
printf 'cpu_possible=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/possible 2>/dev/null || printf unavailable)"
printf 'cpu_present=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/present 2>/dev/null || printf unavailable)"
printf 'cpu_online=%s\n' "$(/bin/busybox cat /sys/devices/system/cpu/online 2>/dev/null || printf unavailable)"
printf 'state_path=%s\n' "$STATE"

if [ ! -f "$STATE" ] || [ ! -r "$STATE" ]; then
	printf '%s\n' 'state_access=absent-or-unreadable'
	printf '%s\n' 'device_partition_reads=none'
	printf '%s\n' 'device_storage_writes=none'
	printf '%s\n' 'hardware_write=none'
	printf '%s\n' 'reboot_request=none'
	printf '%s\n' '__GEMINI_PROVENANCE_RUNTIME_END__'
	exit 0
fi

mode="$(/bin/busybox stat -c '%a' "$STATE" 2>/dev/null || printf unavailable)"
printf '%s\n' 'state_access=readable'
printf 'state_mode=%s\n' "$mode"
printf '%s\n' '__GEMINI_PROVENANCE_SNAPSHOT_1_BEGIN__'
/bin/busybox cat "$STATE"
printf '%s\n' '__GEMINI_PROVENANCE_SNAPSHOT_1_END__'
/bin/busybox sleep 2
printf '%s\n' '__GEMINI_PROVENANCE_SNAPSHOT_2_BEGIN__'
/bin/busybox cat "$STATE"
printf '%s\n' '__GEMINI_PROVENANCE_SNAPSHOT_2_END__'
printf '%s\n' 'device_partition_reads=none'
printf '%s\n' 'device_storage_writes=none'
printf '%s\n' 'hardware_write=none'
printf '%s\n' 'reboot_request=none'
printf '%s\n' '__GEMINI_PROVENANCE_RUNTIME_END__'
