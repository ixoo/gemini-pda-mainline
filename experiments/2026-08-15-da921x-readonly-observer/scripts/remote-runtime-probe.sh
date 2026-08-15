#!/bin/sh

# Stream one bounded, read-only DA921x observer record through the initramfs
# netcat shell. This performs no mount, storage, driver, CPU, or power action.
set -eu
export LC_ALL=C

readonly INSTALLED_FULL_SHA256=7a3ce120de99d7c5ad26dce618f81d50bfeb1ca95b5f2a0bdb9fbf4acba1f564

kernel_release="$(/bin/busybox uname -r)"
architecture="$(/bin/busybox uname -m)"
boot_id="$(/bin/busybox cat /proc/sys/kernel/random/boot_id 2>/dev/null || printf unavailable)"
cpu_possible="$(/bin/busybox cat /sys/devices/system/cpu/possible 2>/dev/null || printf unavailable)"
cpu_present="$(/bin/busybox cat /sys/devices/system/cpu/present 2>/dev/null || printf unavailable)"
cpu_online="$(/bin/busybox cat /sys/devices/system/cpu/online 2>/dev/null || printf unavailable)"
cpu_offline="$(/bin/busybox cat /sys/devices/system/cpu/offline 2>/dev/null || printf unavailable)"
cmdline="$(/bin/busybox cat /proc/cmdline 2>/dev/null || printf unavailable)"
observer_lines="$(/bin/busybox dmesg 2>/dev/null | /bin/busybox grep -E \
	'da921x-observer-v1|DA9214 legacy direct-address identity|read-only observation failed' || true)"
bound_count="$(printf '%s\n' "$observer_lines" | /bin/busybox grep -c \
	'da921x-observer-v1 event=bound' || true)"
cleanup_count="$(printf '%s\n' "$observer_lines" | /bin/busybox grep -Ec \
	'da921x-observer-v1 event=(unbind|failed-probe)' || true)"
failure_count="$(printf '%s\n' "$observer_lines" | /bin/busybox grep -c \
	'read-only observation failed' || true)"

printf '%s\n' '__DA921X_OBSERVER_RUNTIME_BEGIN__'
printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
printf 'kernel_release=%s\narchitecture=%s\nboot_id=%s\n' \
	"$kernel_release" "$architecture" "$boot_id"
printf 'cpu_possible=%s\ncpu_present=%s\ncpu_online=%s\ncpu_offline=%s\n' \
	"$cpu_possible" "$cpu_present" "$cpu_online" "$cpu_offline"
printf 'cmdline=%s\n' "$cmdline"
printf 'bound_marker_count=%s\ncleanup_marker_count=%s\nfailure_marker_count=%s\n' \
	"$bound_count" "$cleanup_count" "$failure_count"
printf '%s\n' '__DA921X_OBSERVER_DMESG_BEGIN__'
printf '%s\n' "$observer_lines"
printf '%s\n' '__DA921X_OBSERVER_DMESG_END__'
printf '%s\n' 'device_partition_reads=none'
printf '%s\n' 'device_storage_writes=none'
printf '%s\n' 'driver_binding_changes=none'
printf '%s\n' 'hardware_write_request=none'
printf '%s\n' 'cpu_admission_request=none'
printf '%s\n' 'reboot_request=none'
printf '%s\n' '__DA921X_OBSERVER_RUNTIME_END__'
