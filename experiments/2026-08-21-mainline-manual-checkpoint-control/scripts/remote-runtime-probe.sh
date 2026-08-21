#!/bin/sh

# Read one exact serviceability and live-checkpoint result over the initramfs
# netcat shell. This performs no partition, driver, CPU, regulator, or power
# action.
set -eu
export LC_ALL=C
BB=/bin/busybox

readonly INSTALLED_FULL_SHA256=53e03cb7100cbb355b7513320428cea8bf39c8c81da9b89a52c91cadd24e8e5c
readonly LIVE_PREFIX=GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1
readonly LIVE_EXACT='GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1 first=1 second=1 retained_writes=2 protected_calls=0 cpu_requests=0'

live_prefix_count="$($BB dmesg | $BB grep -Fc "$LIVE_PREFIX" || true)"
live_exact_count="$($BB dmesg | $BB grep -Fc "$LIVE_EXACT" || true)"

$BB printf '%s\n' __MANUAL_CHECKPOINT_CONTROL_RUNTIME_BEGIN__
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
$BB printf 'manual_live_prefix_count=%s\n' "$live_prefix_count"
$BB printf 'manual_live_exact_count=%s\n' "$live_exact_count"
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
$BB printf '%s\n' __MANUAL_CHECKPOINT_CONTROL_RUNTIME_END__
