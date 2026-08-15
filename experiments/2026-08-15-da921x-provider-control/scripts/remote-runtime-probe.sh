#!/bin/sh

# Stream one bounded, read-only matched-control record through the initramfs
# netcat shell. This performs no mount, storage, driver, CPU, or power action.
set -eu
export LC_ALL=C

readonly INSTALLED_FULL_SHA256=3188d474f5d6989a0eb0782cdfac781efaf43dd42a0bd11481277050e735f8a2

kernel_release="$(/bin/busybox uname -r)"
architecture="$(/bin/busybox uname -m)"
boot_id="$(/bin/busybox cat /proc/sys/kernel/random/boot_id 2>/dev/null || printf unavailable)"
cpu_possible="$(/bin/busybox cat /sys/devices/system/cpu/possible 2>/dev/null || printf unavailable)"
cpu_present="$(/bin/busybox cat /sys/devices/system/cpu/present 2>/dev/null || printf unavailable)"
cpu_online="$(/bin/busybox cat /sys/devices/system/cpu/online 2>/dev/null || printf unavailable)"
cpu_offline="$(/bin/busybox cat /sys/devices/system/cpu/offline 2>/dev/null || printf unavailable)"
cmdline="$(/bin/busybox cat /proc/cmdline 2>/dev/null || printf unavailable)"
provider_lines="$(/bin/busybox dmesg 2>/dev/null | /bin/busybox grep -E \
	'DA9214 legacy direct-address identity matched; provider is read-only|read-only identity transcript failed|failed to register read-only provider|da921x-observer-v1' || true)"
identity_count="$(printf '%s\n' "$provider_lines" | /bin/busybox grep -c \
	'DA9214 legacy direct-address identity matched; provider is read-only' || true)"
failure_count="$(printf '%s\n' "$provider_lines" | /bin/busybox grep -Ec \
	'read-only identity transcript failed|failed to register read-only provider' || true)"
observer_count="$(printf '%s\n' "$provider_lines" | /bin/busybox grep -c \
	'da921x-observer-v1' || true)"

bound_paths=
for path in /sys/bus/i2c/drivers/da9213-legacy-regulator/*-*; do
	[ -e "$path" ] || continue
	entry="${path##*/}"
	bound_paths="${bound_paths}${bound_paths:+ }${entry}"
done
regulator_names=
for path in /sys/class/regulator/regulator.*/name; do
	[ -f "$path" ] || continue
	name="$(/bin/busybox cat "$path" 2>/dev/null || true)"
	case "$name" in
	DA9213-legacy-BUCK0|DA9213-legacy-BUCK1)
		regulator_names="${regulator_names}${regulator_names:+ }${name}"
		;;
	esac
done

printf '%s\n' '__DA921X_PROVIDER_CONTROL_RUNTIME_BEGIN__'
printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
printf 'kernel_release=%s\narchitecture=%s\nboot_id=%s\n' \
	"$kernel_release" "$architecture" "$boot_id"
printf 'cpu_possible=%s\ncpu_present=%s\ncpu_online=%s\ncpu_offline=%s\n' \
	"$cpu_possible" "$cpu_present" "$cpu_online" "$cpu_offline"
printf 'cmdline=%s\n' "$cmdline"
printf 'provider_identity_count=%s\nprovider_failure_count=%s\nobserver_marker_count=%s\n' \
	"$identity_count" "$failure_count" "$observer_count"
printf 'bound_i2c_paths=%s\nregulator_names=%s\n' "$bound_paths" "$regulator_names"
printf '%s\n' '__DA921X_PROVIDER_CONTROL_DMESG_BEGIN__'
printf '%s\n' "$provider_lines"
printf '%s\n' '__DA921X_PROVIDER_CONTROL_DMESG_END__'
printf '%s\n' 'device_partition_reads=none'
printf '%s\n' 'device_storage_writes=none'
printf '%s\n' 'driver_binding_changes=none'
printf '%s\n' 'hardware_write_request=none'
printf '%s\n' 'cpu_admission_request=none'
printf '%s\n' 'reboot_request=none'
printf '%s\n' '__DA921X_PROVIDER_CONTROL_RUNTIME_END__'
