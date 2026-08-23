#!/bin/sh

# Read exact serviceability and the first-dmesg write result over the initramfs
# netcat shell. This performs no memory, storage, CPU, or power action.
set -eu
export LC_ALL=C
BB=/bin/busybox

readonly INSTALLED_FULL_SHA256=b96ec109b3f020fdaf0cdc6ca1733d012051e6607b5520a11d32a6441f569e96
readonly CONTROL_PREFIX=GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1
readonly STAGE_PREFIX=GEMINI_MANUAL_CHECKPOINT_STAGE_V1
readonly FIRST_PREFIX=GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1
readonly CONTROL_EXACT='GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1 first=1 second=0 retained_writes=1 protected_calls=0 cpu_requests=0'
readonly STAGE_EXACT='GEMINI_MANUAL_CHECKPOINT_STAGE_V1 first=1 second=0 stage=success writes=1 protected=0 cpu=0'
readonly FIRST_EXACT='GEMINI_FIRST_DMESG_RAW_WRITE_QUALIFICATION_LIVE_V1 commit=1 stage=success writes=1 record=1 address=44410000 protected=0 clock=0 bigidvfs=0 cpu=0'

control_prefix_count="$($BB dmesg | $BB grep -Fc "$CONTROL_PREFIX" || true)"
stage_prefix_count="$($BB dmesg | $BB grep -Fc "$STAGE_PREFIX" || true)"
first_prefix_count="$($BB dmesg | $BB grep -Fc "$FIRST_PREFIX" || true)"
control_exact_count="$($BB dmesg | $BB grep -Fc "$CONTROL_EXACT" || true)"
stage_exact_count="$($BB dmesg | $BB grep -Fc "$STAGE_EXACT" || true)"
first_exact_count="$($BB dmesg | $BB grep -Fc "$FIRST_EXACT" || true)"

$BB printf '%s\n' __FIRST_DMESG_RAW_WRITE_RUNTIME_BEGIN__
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
$BB printf 'manual_control_prefix_count=%s\n' "$control_prefix_count"
$BB printf 'manual_stage_prefix_count=%s\n' "$stage_prefix_count"
$BB printf 'first_dmesg_prefix_count=%s\n' "$first_prefix_count"
$BB printf 'manual_control_exact_count=%s\n' "$control_exact_count"
$BB printf 'manual_stage_exact_count=%s\n' "$stage_exact_count"
$BB printf 'first_dmesg_exact_count=%s\n' "$first_exact_count"
$BB printf 'block_mounts='; $BB grep -Ec '^/dev/(mmc|sd|nvme)' /proc/mounts || true
$BB printf 'pstore_files='; $BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | $BB wc -l
$BB printf '%s\n' device_partition_reads=none device_storage_writes=none
$BB printf '%s\n' driver_binding_changes=none same_value_action_request=none
$BB printf '%s\n' protected_read_request=none secure_call_request=none
$BB printf '%s\n' owner_registration_request=none cpu_admission_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __FIRST_DMESG_RAW_WRITE_RUNTIME_END__
