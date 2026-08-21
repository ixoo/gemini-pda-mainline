#!/bin/sh

# Stream one bounded call-ledger protected-readback observation through the
# initramfs netcat shell. This performs no storage, driver, CPU, or power action.
set -eu
export LC_ALL=C

readonly INSTALLED_FULL_SHA256=3ce494c971c24c9edab73aac592d0ba8dd0bbd25f06051245f7846f95d0c715a

kernel_release="$(/bin/busybox uname -r)"
architecture="$(/bin/busybox uname -m)"
boot_id="$(/bin/busybox cat /proc/sys/kernel/random/boot_id 2>/dev/null || printf unavailable)"
uptime_seconds="$(/bin/busybox cut -d ' ' -f 1 /proc/uptime 2>/dev/null || printf unavailable)"
cpu_possible="$(/bin/busybox cat /sys/devices/system/cpu/possible 2>/dev/null || printf unavailable)"
cpu_present="$(/bin/busybox cat /sys/devices/system/cpu/present 2>/dev/null || printf unavailable)"
cpu_online="$(/bin/busybox cat /sys/devices/system/cpu/online 2>/dev/null || printf unavailable)"
cpu_offline="$(/bin/busybox cat /sys/devices/system/cpu/offline 2>/dev/null || printf unavailable)"
cmdline="$(/bin/busybox cat /proc/cmdline 2>/dev/null || printf unavailable)"
model="$(/bin/busybox tr '\000' ' ' </sys/firmware/devicetree/base/model 2>/dev/null || printf unavailable)"
observer_lines="$(/bin/busybox dmesg 2>/dev/null | /bin/busybox grep \
	'GEMINI_PROTECTED_READBACK_V1' || true)"
clock_count="$(printf '%s\n' "$observer_lines" | /bin/busybox grep -c \
	'GEMINI_PROTECTED_READBACK_V1 clock ' || true)"
bigidvfs_count="$(printf '%s\n' "$observer_lines" | /bin/busybox grep -c \
	'GEMINI_PROTECTED_READBACK_V1 bigidvfs ' || true)"
complete_count="$(printf '%s\n' "$observer_lines" | /bin/busybox grep -c \
	'GEMINI_PROTECTED_READBACK_V1 state=complete ' || true)"

printf '%s\n' '__PROTECTED_READBACK_RUNTIME_BEGIN__'
printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
printf 'kernel_release=%s\narchitecture=%s\nboot_id=%s\nuptime_seconds=%s\n' \
	"$kernel_release" "$architecture" "$boot_id" "$uptime_seconds"
printf 'cpu_possible=%s\ncpu_present=%s\ncpu_online=%s\ncpu_offline=%s\n' \
	"$cpu_possible" "$cpu_present" "$cpu_online" "$cpu_offline"
printf 'cmdline=%s\nmodel=%s\n' "$cmdline" "$model"
printf 'clock_record_count=%s\nbigidvfs_record_count=%s\ncompletion_record_count=%s\n' \
	"$clock_count" "$bigidvfs_count" "$complete_count"
printf '%s\n' '__PROTECTED_READBACK_DMESG_BEGIN__'
printf '%s\n' "$observer_lines"
printf '%s\n' '__PROTECTED_READBACK_DMESG_END__'
printf '%s\n' 'device_partition_reads=none'
printf '%s\n' 'device_storage_writes=none'
printf '%s\n' 'driver_binding_changes=none'
printf '%s\n' 'secure_write_request=none'
printf '%s\n' 'owner_registration_request=none'
printf '%s\n' 'cpu_admission_request=none'
printf '%s\n' 'reboot_request=none'
printf '%s\n' '__PROTECTED_READBACK_RUNTIME_END__'
