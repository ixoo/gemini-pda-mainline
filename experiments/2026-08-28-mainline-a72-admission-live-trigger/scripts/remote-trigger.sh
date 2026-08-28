#!/bin/sh

# Execute the exact live trigger once after the host has durably accepted the
# pre-trigger frame. Any loss after the commit marker is attributable.
set -u
export LC_ALL=C
BB=/bin/busybox
GROUP=/sys/bus/platform/devices/a72-admission-controller/gemini_admission
STATUS="$GROUP/status"
TRIGGER="$GROUP/trigger"
ARMED='GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 trigger_executions=0 operation_ret=-115 core_consumed=0 cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0'

$BB printf '%s\n' __GEMINI_A72_LIVE_TRIGGER_BEGIN__
$BB printf 'pre_status='; $BB cat "$STATUS" 2>/dev/null || $BB printf 'unreadable\n'
if [ "$($BB cat "$STATUS" 2>/dev/null)" != "$ARMED" ]; then
	$BB printf '%s\n' trigger_commit=no reason=pre-status-not-armed
	$BB printf '%s\n' __GEMINI_A72_LIVE_TRIGGER_END__
	exit 3
fi
if ! $BB mount -o remount,rw /sys; then
	$BB printf '%s\n' trigger_commit=no reason=sysfs-remount-rw-failed
	$BB printf '%s\n' __GEMINI_A72_LIVE_TRIGGER_END__
	exit 3
fi
$BB printf '%s\n' trigger_commit=yes token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f
$BB printf 'run-a72-admission-20260828-a\n' >"$TRIGGER"
trigger_write_status=$?
$BB mount -o remount,ro /sys
remount_ro_status=$?
$BB printf 'trigger_write_status=%s\n' "$trigger_write_status"
$BB printf 'remount_ro_status=%s\n' "$remount_ro_status"
$BB printf 'post_status='; $BB cat "$STATUS" 2>/dev/null || $BB printf 'unreadable\n'
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf '%s\n' cpu9_request=none
$BB printf '%s\n' cpu_off_request=none
$BB printf '%s\n' retry_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' __GEMINI_A72_LIVE_TRIGGER_END__
exit "$trigger_write_status"
