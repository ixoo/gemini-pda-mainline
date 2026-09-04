#!/bin/sh

# Read-only pre-trigger frame for the production thermal/frequency candidate.
set -u
export LC_ALL=C

BB=/bin/busybox
GROUP=/sys/bus/platform/devices/a72-admission-controller/gemini_admission
STATUS="$GROUP/status"
TRIGGER="$GROUP/trigger"
RECORD=/sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/record-identity

$BB printf '%s\n' __A72_FREQUENCY_THERMAL_PRETRIGGER_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'architecture='; $BB uname -m
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'cpu_possible='; $BB cat /sys/devices/system/cpu/possible
$BB printf 'cpu_present='; $BB cat /sys/devices/system/cpu/present
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
$BB printf 'controller_bound='
if [ -r "$STATUS" ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'binder_bound='
if [ -d /sys/bus/platform/devices/a72-binder ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'platform_state_bound='
if [ -d /sys/bus/platform/devices/10222000.a72-platform-state ]; then $BB printf '1\n'; else $BB printf '0\n'; fi
$BB printf 'status_mode='; $BB stat -c '%a' "$STATUS" 2>/dev/null || $BB printf 'missing\n'
$BB printf 'trigger_mode='; $BB stat -c '%a' "$TRIGGER" 2>/dev/null || $BB printf 'missing\n'
$BB printf 'sysfs_options='; $BB awk "\$2 == \"/sys\" { print \$4 }" /proc/mounts
$BB printf 'record_identity='
if [ -r "$RECORD" ]; then
	$BB od -An -tx1 -v "$RECORD" | $BB tr -d '[:space:]'
	$BB printf '\n'
else
	$BB printf 'missing\n'
fi
$BB printf 'live_status='; $BB cat "$STATUS" 2>/dev/null || $BB printf 'unreadable\n'

frequency_observer_count=0
frequency_observer_mode=missing
for item in /sys/bus/platform/devices/*/a72_frequency_observation; do
	[ -r "$item" ] || continue
	frequency_observer_count=$((frequency_observer_count + 1))
	frequency_observer_mode=$($BB stat -c '%a' "$item" 2>/dev/null || $BB printf 'missing')
done
$BB printf 'frequency_observer_count=%s\n' "$frequency_observer_count"
$BB printf 'frequency_observer_mode=%s\n' "$frequency_observer_mode"
$BB printf 'frequency_log_count='; $BB dmesg 2>/dev/null | $BB grep -Fc 'GEMINI_A72_FREQUENCY_OBSERVATION_V1'

thermal_zone_count=0
thermal_zone_type=missing
thermal_temperature=missing
for item in /sys/class/thermal/thermal_zone[0-9]*; do
	[ -r "$item/type" ] && [ -r "$item/temp" ] || continue
	thermal_zone_count=$((thermal_zone_count + 1))
	thermal_zone_type=$($BB cat "$item/type")
	thermal_temperature=$($BB cat "$item/temp")
done
$BB printf 'thermal_zone_count=%s\n' "$thermal_zone_count"
$BB printf 'thermal_zone_type=%s\n' "$thermal_zone_type"
$BB printf 'thermal_temperature_millicelsius=%s\n' "$thermal_temperature"

$BB printf '%s\n' __A72_FREQUENCY_THERMAL_LATE_PROFILE_BEGIN__
$BB dmesg 2>/dev/null | $BB grep 'arm64-late-cpu-profile:' || true
$BB printf '%s\n' __A72_FREQUENCY_THERMAL_LATE_PROFILE_END__
$BB printf '%s\n' device_storage_reads=none device_storage_writes=none
$BB printf '%s\n' frequency_observation_request=none sysfs_write_request=none
$BB printf '%s\n' cpu_admission_request=none cpu_off_request=none
$BB printf '%s\n' retry_request=none reboot_request=none
$BB printf '%s\n' __A72_FREQUENCY_THERMAL_PRETRIGGER_END__
