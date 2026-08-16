#!/bin/sh

# Stream one bounded, read-only checkpoint record through the initramfs netcat
# shell. This performs no mount, storage, driver, CPU, or power action.
set -eu
export LC_ALL=C

readonly INSTALLED_FULL_SHA256=ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348
readonly MARKER=GEMINI_MAINLINE_POST_RAMOOPS_20260815_A

kernel_release="$(/bin/busybox uname -r)"
architecture="$(/bin/busybox uname -m)"
boot_id="$(/bin/busybox cat /proc/sys/kernel/random/boot_id 2>/dev/null || printf unavailable)"
cpu_possible="$(/bin/busybox cat /sys/devices/system/cpu/possible 2>/dev/null || printf unavailable)"
cpu_present="$(/bin/busybox cat /sys/devices/system/cpu/present 2>/dev/null || printf unavailable)"
cpu_online="$(/bin/busybox cat /sys/devices/system/cpu/online 2>/dev/null || printf unavailable)"
cpu_offline="$(/bin/busybox cat /sys/devices/system/cpu/offline 2>/dev/null || printf unavailable)"
cmdline="$(/bin/busybox cat /proc/cmdline 2>/dev/null || printf unavailable)"
checkpoint_lines="$(/bin/busybox dmesg 2>/dev/null | /bin/busybox grep -F "$MARKER" || true)"
checkpoint_count="$(printf '%s\n' "$checkpoint_lines" | /bin/busybox grep -c -F "$MARKER" || true)"
provider_lines="$(/bin/busybox dmesg 2>/dev/null | /bin/busybox grep -E \
	'DA9214 legacy direct-address identity matched; provider is read-only|read-only identity transcript failed|failed to register read-only provider|da921x-observer-v1' || true)"

printf '%s\n' '__POST_RAMOOPS_CHECKPOINT_RUNTIME_BEGIN__'
printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
printf 'kernel_release=%s\narchitecture=%s\nboot_id=%s\n' \
	"$kernel_release" "$architecture" "$boot_id"
printf 'cpu_possible=%s\ncpu_present=%s\ncpu_online=%s\ncpu_offline=%s\n' \
	"$cpu_possible" "$cpu_present" "$cpu_online" "$cpu_offline"
printf 'cmdline=%s\ncheckpoint_marker_count=%s\n' "$cmdline" "$checkpoint_count"
printf '%s\n' '__POST_RAMOOPS_CHECKPOINT_DMESG_BEGIN__'
printf '%s\n%s\n' "$checkpoint_lines" "$provider_lines"
printf '%s\n' '__POST_RAMOOPS_CHECKPOINT_DMESG_END__'
printf '%s\n' 'device_partition_reads=none'
printf '%s\n' 'device_storage_writes=none'
printf '%s\n' 'driver_binding_changes=none'
printf '%s\n' 'hardware_write_request=none'
printf '%s\n' 'cpu_admission_request=none'
printf '%s\n' 'reboot_request=none'
printf '%s\n' '__POST_RAMOOPS_CHECKPOINT_RUNTIME_END__'
