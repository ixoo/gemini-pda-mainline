#!/bin/sh

# Issue the exact same-value token once, restore sysfs read-only, and capture
# both the I2C6 ledger and supplier transaction-window counters.
set -eu
export LC_ALL=C
BB=/bin/busybox
TOKEN=run-same-value-write-20260819-a
sysfs_restore_required=0

restore_sysfs()
{
	[ "$sysfs_restore_required" = 1 ] || return 0
	$BB mount -o remount,ro /sys >/dev/null 2>&1 || true
}

handle_signal()
{
	restore_sysfs
	exit 1
}

sysfs_options()
{
	# shellcheck disable=SC2016 # The program is interpreted remotely by awk.
	$BB awk '$2 == "/sys" && $3 == "sysfs" {
		print $4; found++
	} END { if (found != 1) exit 1 }' /proc/mounts
}

require_mount_option()
{
	case ",$1," in
	*,"$2",*) ;;
	*) return 1 ;;
	esac
}

trap restore_sysfs EXIT
trap handle_signal HUP INT TERM

$BB printf '\n%s\n' __DA921X_SAME_VALUE_TRIGGER_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
set -- /sys/bus/i2c/devices/*-0068
if [ "$#" -ne 1 ] || [ ! -e "$1" ]; then
	[ -e "$1" ] || set --
	$BB printf 'da921x_i2c_client_count=%s\n' "$#"
	exit 1
fi
action=$1/same_value_write
[ -r "$action" ] || exit 1
$BB printf '%s\n' __SAME_VALUE_BEFORE_BEGIN__
$BB cat "$action"
$BB printf '%s\n' __SAME_VALUE_BEFORE_END__

mount_options="$(sysfs_options)" || exit 1
require_mount_option "$mount_options" ro || exit 1
$BB printf '%s\n' sysfs_mount_before=ro
set +e
$BB mount -o remount,rw /sys
remount_rw_status=$?
set -e
$BB printf 'sysfs_remount_rw_status=%s\n' "$remount_rw_status"
[ "$remount_rw_status" -eq 0 ] || exit 1
sysfs_restore_required=1
mount_options="$(sysfs_options)" || exit 1
require_mount_option "$mount_options" rw || exit 1
$BB printf '%s\n' sysfs_mount_during=rw
[ -w "$action" ] || {
	$BB printf '%s\n' same_value_write_writable=0
	exit 1
}
$BB printf '%s\n' same_value_write_writable=1

$BB printf 'trigger_command_started=yes\n'
set +e
$BB printf '%s\n' "$TOKEN" >"$action"
trigger_status=$?
set -e
$BB printf 'trigger_command_status=%s\n' "$trigger_status"

set +e
$BB mount -o remount,ro /sys
remount_ro_status=$?
set -e
$BB printf 'sysfs_remount_ro_status=%s\n' "$remount_ro_status"
[ "$remount_ro_status" -eq 0 ] || exit 1
mount_options="$(sysfs_options)" || exit 1
require_mount_option "$mount_options" ro || exit 1
sysfs_restore_required=0
$BB printf '%s\n' sysfs_mount_after=ro

$BB printf '%s\n' __SAME_VALUE_AFTER_BEGIN__
$BB cat "$action"
$BB printf '%s\n' __SAME_VALUE_AFTER_END__
i2c6=/sys/bus/platform/devices/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || i2c6=/sys/devices/platform/soc/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || exit 1
attestation=/sys/bus/platform/devices/11015000.dvfsp-handoff/firmware_writer_attestation
[ -r "$attestation" ] || exit 1
$BB printf '%s\n' __I2C6_POSTTRIGGER_STATUS_BEGIN__
$BB cat "$i2c6/handoff_status"
$BB cat "$attestation"
$BB printf '%s\n' __I2C6_POSTTRIGGER_STATUS_END__
$BB printf '%s\n' __DA921X_SAME_VALUE_POSTTRIGGER_DMESG_BASE64_BEGIN__
$BB dmesg | $BB base64
$BB printf '%s\n' __DA921X_SAME_VALUE_POSTTRIGGER_DMESG_BASE64_END__
$BB printf 'post_trigger_boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf '%s\n' __DA921X_SAME_VALUE_TRIGGER_END__
