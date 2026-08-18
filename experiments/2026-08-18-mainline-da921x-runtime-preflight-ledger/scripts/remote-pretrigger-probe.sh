#!/bin/sh

# Read-only USB/netcat probe for the exact runtime-preflight candidate.
set -eu
export LC_ALL=C
BB=/bin/busybox

$BB printf '%s\n' __DA921X_RUNTIME_PRETRIGGER_BEGIN__
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
$BB printf 'reboot_sha256='; $BB sha256sum /bin/reboot | $BB cut -d ' ' -f 1

# The entries below /sys/bus/i2c/devices are symlinks. BusyBox find does not
# descend through them by default, so resolve the one exact DA921x client via
# the shell glob and then address its attribute directly.
set -- /sys/bus/i2c/devices/*-0068
if [ "$#" -ne 1 ] || [ ! -e "$1" ]; then
	[ -e "$1" ] || set --
	$BB printf 'da921x_i2c_client_count=%s\n' "$#"
	exit 1
fi
preflight=$1/readonly_preflight
[ -r "$preflight" ] || {
	$BB printf '%s\n' readonly_preflight_attribute_count=0
	exit 1
}
$BB printf '%s\n' __RUNTIME_PREFLIGHT_STATE_BEGIN__
$BB cat "$preflight"
$BB printf '%s\n' __RUNTIME_PREFLIGHT_STATE_END__

i2c6=/sys/bus/platform/devices/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || i2c6=/sys/devices/platform/soc/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || {
	$BB printf '%s\n' i2c6_status_absent
	exit 1
}
$BB printf '%s\n' __I2C6_STATUS_BEGIN__
$BB cat "$i2c6/handoff_status"
$BB printf '%s\n' __I2C6_STATUS_END__

$BB printf '%s\n' __DA921X_RUNTIME_DMESG_BASE64_BEGIN__
$BB dmesg | $BB base64
$BB printf '%s\n' __DA921X_RUNTIME_DMESG_BASE64_END__
$BB printf 'post_probe_boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf '%s\n' __DA921X_RUNTIME_PRETRIGGER_END__
