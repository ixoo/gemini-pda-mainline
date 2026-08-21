#!/bin/sh

# Read one exact current-tree serviceability control over the initramfs netcat
# shell. This performs no partition, driver, CPU, regulator, or power action.
set -eu
export LC_ALL=C
BB=/bin/busybox

readonly INSTALLED_FULL_SHA256=7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3

$BB printf '%s\n' __CURRENT_SERVICE_CONTROL_RUNTIME_BEGIN__
$BB printf 'installed_full_sha256=%s\n' "$INSTALLED_FULL_SHA256"
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'uptime_seconds='; $BB cut -d ' ' -f 1 /proc/uptime
$BB printf 'cmdline='; $BB cat /proc/cmdline
$BB printf 'model='; $BB tr '\000' ' ' </sys/firmware/devicetree/base/model; $BB printf '\n'
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'udc_devices='; $BB find /sys/class/udc -mindepth 1 -maxdepth 1 2>/dev/null | $BB wc -l
$BB printf 'keyboard_matrix_inputs='; $BB grep -c 'Name="keyboard-matrix"' /proc/bus/input/devices || true
$BB printf 'da921x_i2c_clients='; $BB find /sys/bus/i2c/devices -maxdepth 1 -name '*-0068' 2>/dev/null | $BB wc -l
$BB printf 'same_value_write_attributes='; $BB find /sys/bus/i2c/devices -name same_value_write 2>/dev/null | $BB wc -l
$BB printf 'clock_backend_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*dvfsp-clock-backend*' 2>/dev/null | $BB wc -l
$BB printf 'bigidvfs_backend_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*dvfsp-bigidvfs-backend*' 2>/dev/null | $BB wc -l
$BB printf 'protected_readback_devices='; $BB find /sys/bus/platform/devices -maxdepth 1 -name '*protected-readback*' 2>/dev/null | $BB wc -l
$BB printf 'block_mounts='; $BB grep -Ec '^/dev/(mmc|sd|nvme)' /proc/mounts || true
$BB printf 'pstore_files='; $BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | $BB wc -l
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' driver_binding_changes=none
$BB printf '%s\n' same_value_action_request=none
$BB printf '%s\n' protected_read_request=none
$BB printf '%s\n' secure_call_request=none
$BB printf '%s\n' owner_registration_request=none
$BB printf '%s\n' cpu_admission_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __CURRENT_SERVICE_CONTROL_RUNTIME_END__
