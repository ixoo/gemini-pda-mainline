#!/bin/sh

# Read-only confirmation after the runtime token has already completed.
set -eu
export LC_ALL=C
BB=/bin/busybox

$BB printf '\n%s\n' __DA921X_RUNTIME_POSTTRIGGER_CONFIRM_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'block_mounts='; $BB grep -Ec '^/dev/(mmc|sd|nvme)' /proc/mounts || true

# shellcheck disable=SC2016 # The single-quoted program is interpreted by awk.
mount_options="$($BB awk '$2 == "/sys" && $3 == "sysfs" {
	print $4; found++
} END { if (found != 1) exit 1 }' /proc/mounts)"
case ",$mount_options," in
*,ro,*) $BB printf '%s\n' sysfs_mount=ro ;;
*) $BB printf '%s\n' sysfs_mount=unexpected; exit 1 ;;
esac

set -- /sys/bus/i2c/devices/*-0068
if [ "$#" -ne 1 ] || [ ! -e "$1" ]; then
	[ -e "$1" ] || set --
	$BB printf 'da921x_i2c_client_count=%s\n' "$#"
	exit 1
fi
preflight=$1/readonly_preflight
[ -r "$preflight" ] || exit 1
$BB printf '%s\n' __RUNTIME_PREFLIGHT_CONFIRM_STATE_BEGIN__
$BB cat "$preflight"
$BB printf '%s\n' __RUNTIME_PREFLIGHT_CONFIRM_STATE_END__

i2c6=/sys/bus/platform/devices/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || i2c6=/sys/devices/platform/soc/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || exit 1
$BB printf '%s\n' __I2C6_CONFIRM_STATUS_BEGIN__
$BB cat "$i2c6/handoff_status"
$BB printf '%s\n' __I2C6_CONFIRM_STATUS_END__
$BB printf 'post_confirm_boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf '%s\n' __DA921X_RUNTIME_POSTTRIGGER_CONFIRM_END__
