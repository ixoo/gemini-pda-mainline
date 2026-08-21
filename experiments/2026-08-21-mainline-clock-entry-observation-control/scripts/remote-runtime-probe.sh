#!/bin/sh

# Read one exact serviceability and driver-registration control over the
# initramfs netcat shell. This performs no partition, driver, CPU, or power action.
set -eu
export LC_ALL=C

readonly INSTALLED_FULL_SHA256=fc2a9a1a53de1373cf75d14f163a5b9921219996882f58e0b5395595872230bf
readonly DRIVER_PATH=/sys/bus/platform/drivers/mt6797-dvfsp-clock-backend
readonly NODE_PATH=/sys/firmware/devicetree/base/dvfsp-clock-backend@1001a000

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
clock_node_status="$(/bin/busybox tr '\000' ' ' <"$NODE_PATH/status" 2>/dev/null || printf unavailable)"
if [ -d "$DRIVER_PATH" ]; then
	driver_registered=yes
else
	driver_registered=no
fi
if /bin/busybox find /sys/bus/platform/devices -maxdepth 1 -name '*dvfsp-clock-backend*' | /bin/busybox grep -q .; then
	clock_platform_device_present=yes
else
	clock_platform_device_present=no
fi
ioremap_ram_warning_count="$(/bin/busybox dmesg 2>/dev/null |
	/bin/busybox grep -c 'ioremap attempted on RAM pfn' || true)"

printf '%s\n' '__CLOCK_ENTRY_CONTROL_RUNTIME_BEGIN__'
printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
printf 'kernel_release=%s\narchitecture=%s\nboot_id=%s\nuptime_seconds=%s\n' \
	"$kernel_release" "$architecture" "$boot_id" "$uptime_seconds"
printf 'cpu_possible=%s\ncpu_present=%s\ncpu_online=%s\ncpu_offline=%s\n' \
	"$cpu_possible" "$cpu_present" "$cpu_online" "$cpu_offline"
printf 'cmdline=%s\nmodel=%s\nclock_node_status=%s\n' \
	"$cmdline" "$model" "$clock_node_status"
printf 'driver_registered=%s\nclock_platform_device_present=%s\n' \
	"$driver_registered" "$clock_platform_device_present"
printf 'ioremap_ram_warning_count=%s\n' "$ioremap_ram_warning_count"
printf '%s\n' 'device_partition_reads=none'
printf '%s\n' 'device_storage_writes=none'
printf '%s\n' 'driver_binding_changes=none'
printf '%s\n' 'protected_read_request=none'
printf '%s\n' 'secure_call_request=none'
printf '%s\n' 'owner_registration_request=none'
printf '%s\n' 'cpu_admission_request=none'
printf '%s\n' 'reboot_request=none'
printf '%s\n' '__CLOCK_ENTRY_CONTROL_RUNTIME_END__'
