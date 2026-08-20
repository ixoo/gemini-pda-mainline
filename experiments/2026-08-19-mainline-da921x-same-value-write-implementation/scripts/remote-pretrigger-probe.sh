#!/bin/sh

# Read-only USB/netcat pre-trigger capture for the exact Gate-6 candidate.
set -eu
export LC_ALL=C
BB=/bin/busybox

$BB printf '\n%s\n' __DA921X_SAME_VALUE_PRETRIGGER_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf 'cmdline='; $BB cat /proc/cmdline
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'udc_devices='; $BB find /sys/class/udc -mindepth 1 -maxdepth 1 2>/dev/null | $BB wc -l
$BB printf 'keyboard_matrix_inputs='; $BB grep -c 'Name="keyboard-matrix"' /proc/bus/input/devices || true
$BB printf 'da921x_i2c_clients='; $BB find /sys/bus/i2c/devices -maxdepth 1 -name '*-0068' 2>/dev/null | $BB wc -l
$BB printf 'block_mounts='; $BB grep -Ec '^/dev/(mmc|sd|nvme)' /proc/mounts || true
$BB printf 'pstore_files='; $BB find /sys/fs/pstore -maxdepth 1 -type f 2>/dev/null | $BB wc -l

set -- /sys/bus/i2c/devices/*-0068
if [ "$#" -ne 1 ] || [ ! -e "$1" ]; then
	[ -e "$1" ] || set --
	$BB printf 'da921x_i2c_client_count=%s\n' "$#"
	exit 1
fi
action=$1/same_value_write
[ -r "$action" ] || {
	$BB printf '%s\n' same_value_write_attribute_count=0
	exit 1
}
$BB printf '%s\n' __SAME_VALUE_STATE_BEGIN__
$BB cat "$action"
$BB printf '%s\n' __SAME_VALUE_STATE_END__

i2c6=/sys/bus/platform/devices/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || i2c6=/sys/devices/platform/soc/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || {
	$BB printf '%s\n' i2c6_status_absent
	exit 1
}
$BB printf '%s\n' __I2C6_STATUS_BEGIN__
$BB cat "$i2c6/handoff_status"
$BB printf '%s\n' __I2C6_STATUS_END__

$BB printf '%s\n' __DA921X_SAME_VALUE_DMESG_BASE64_BEGIN__
$BB dmesg | $BB base64
$BB printf '%s\n' __DA921X_SAME_VALUE_DMESG_BASE64_END__
$BB printf 'post_probe_boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf '%s\n' __DA921X_SAME_VALUE_PRETRIGGER_END__
