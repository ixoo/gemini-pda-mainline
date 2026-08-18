#!/bin/sh

# Issue the exact one-shot read-only token once, then capture the surviving state.
set -eu
export LC_ALL=C
BB=/bin/busybox
TOKEN=run-readonly-preflight-20260818-a

$BB printf '%s\n' __DA921X_RUNTIME_TRIGGER_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
# shellcheck disable=SC2046 # Exact path inventory is intentionally split into arguments.
set -- $($BB find /sys/bus/i2c/devices -maxdepth 2 -name readonly_preflight 2>/dev/null)
[ "$#" -eq 1 ] || {
	$BB printf 'readonly_preflight_attribute_count=%s\n' "$#"
	exit 1
}
preflight=$1
$BB printf '%s\n' __RUNTIME_PREFLIGHT_BEFORE_BEGIN__
$BB cat "$preflight"
$BB printf '%s\n' __RUNTIME_PREFLIGHT_BEFORE_END__
$BB printf 'trigger_command_started=yes\n'
set +e
$BB printf '%s\n' "$TOKEN" >"$preflight"
trigger_status=$?
set -e
$BB printf 'trigger_command_status=%s\n' "$trigger_status"
$BB printf '%s\n' __RUNTIME_PREFLIGHT_AFTER_BEGIN__
$BB cat "$preflight"
$BB printf '%s\n' __RUNTIME_PREFLIGHT_AFTER_END__

i2c6=/sys/bus/platform/devices/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || i2c6=/sys/devices/platform/soc/1100e000.i2c
[ -r "$i2c6/handoff_status" ] || {
	$BB printf '%s\n' i2c6_status_absent
	exit 1
}
$BB printf '%s\n' __I2C6_POSTTRIGGER_STATUS_BEGIN__
$BB cat "$i2c6/handoff_status"
$BB printf '%s\n' __I2C6_POSTTRIGGER_STATUS_END__
$BB printf '%s\n' __DA921X_RUNTIME_POSTTRIGGER_DMESG_BASE64_BEGIN__
$BB dmesg | $BB base64
$BB printf '%s\n' __DA921X_RUNTIME_POSTTRIGGER_DMESG_BASE64_END__
$BB printf 'post_trigger_boot_id_sha256='; $BB sha256sum /proc/sys/kernel/random/boot_id | $BB cut -d ' ' -f 1
$BB printf '%s\n' __DA921X_RUNTIME_TRIGGER_END__
