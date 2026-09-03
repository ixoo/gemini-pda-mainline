#!/bin/sh

# One-shot lifecycle trigger plus read-only topology capture. Materialize the
# expected fresh boot ID before use; never run this template directly.
set -u
export LC_ALL=C

BB=/bin/busybox
EXPECTED_BOOT_ID=__EXPECTED_BOOT_ID__
GROUP=/sys/bus/platform/devices/a72-admission-controller/gemini_admission
STATUS="$GROUP/status"
TRIGGER="$GROUP/trigger"
RECORD=/sys/firmware/devicetree/base/chosen/gemini-late-cpu-provenance/record-identity
READY_LINE='arm64-late-cpu-profile: mt6797-a53-a72-a41-v7 ready'

$BB printf '%s\n' __A72_TOPOLOGY_REPEAT_TRIGGER_BEGIN__
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'boot_id='; $BB cat /proc/sys/kernel/random/boot_id
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
pre_status="$($BB cat "$STATUS" 2>/dev/null)"
$BB printf 'pre_status=%s\n' "$pre_status"

reject_preflight()
{
	$BB printf 'trigger_commit=no reason=%s\n' "$1"
	$BB printf '%s\n' __A72_TOPOLOGY_REPEAT_TRIGGER_END__
	exit 3
}

[ "$($BB uname -r)" = 7.1.3-gemini-a72-hotplug-physical ] || reject_preflight kernel-identity
[ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$EXPECTED_BOOT_ID" ] || reject_preflight boot-identity
[ "$($BB cat /sys/devices/system/cpu/online)" = 0-7 ] || reject_preflight cpu-online-set
[ "$($BB cat /sys/devices/system/cpu/offline)" = 8-9 ] || reject_preflight cpu-offline-set
[ -d /sys/bus/platform/devices/a72-binder ] || reject_preflight binder
[ -d /sys/bus/platform/devices/10222000.a72-platform-state ] || reject_preflight platform-state

record_identity="$($BB od -An -tx1 -v "$RECORD" 2>/dev/null | $BB tr -d '[:space:]')"
[ "$record_identity" = d4940602e7ad9cbc947376bfb9dc4222ef5a671faa15eb42a821df1852af9ba4 ] || reject_preflight record-identity
sysfs_options="$($BB awk "\$2 == \"/sys\" { print \$4 }" /proc/mounts)"
case ",$sysfs_options," in *,ro,*) ;; *) reject_preflight sysfs-not-readonly ;; esac
late_profile="$($BB dmesg 2>/dev/null | $BB grep 'arm64-late-cpu-profile:' || true)"
[ "$($BB printf '%s\n' "$late_profile" | $BB grep -Fc "$READY_LINE")" = 1 ] || reject_preflight late-profile-ready
if $BB printf '%s\n' "$late_profile" | $BB grep -Eiq 'blocked|proof[ _]mask'; then
	reject_preflight late-profile-veto
fi

for required in \
	'state=armed trigger_consumed=0 trigger_executions=0 operation_ret=-115 core_consumed=0' \
	'cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0' \
	'binder_snapshot_ret=0 binder_abi=5 lifecycle=0 terminal=0 last_stage=0' \
	'attempted=0 watchdog_armed=0' \
	'cpu9_controller_consumed=0 cpu9_operation_ret=-115' \
	'cpu9_attempted=0 cpu9_membership_published=0 cpu9_cpu_requests=0 cpu9_cpu_off_requests=0 cpu9_retries=0'; do
	case "$pre_status" in
		*"$required"*) ;;
		*) reject_preflight controller-state ;;
	esac
done

if ! $BB mount -o remount,rw /sys; then
	reject_preflight sysfs-remount-rw
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
$BB printf '%s\n' __A72_TOPOLOGY_REPEAT_SYSFS_BEGIN__
for cpu in 0 1 2 3 4 5 6 7 8 9; do
	topology="/sys/devices/system/cpu/cpu$cpu/topology"
	$BB printf 'cpu%s_physical_package_id=' "$cpu"; $BB cat "$topology/physical_package_id"
	$BB printf 'cpu%s_core_id=' "$cpu"; $BB cat "$topology/core_id"
	$BB printf 'cpu%s_core_siblings=' "$cpu"; $BB cat "$topology/core_siblings_list"
	$BB printf 'cpu%s_cluster_cpus=' "$cpu"; $BB cat "$topology/cluster_cpus_list"
	$BB printf 'cpu%s_thread_siblings=' "$cpu"; $BB cat "$topology/thread_siblings_list"
done
$BB printf '%s\n' __A72_TOPOLOGY_REPEAT_SYSFS_END__
$BB printf '%s\n' __A72_TOPOLOGY_REPEAT_TRIGGER_DMESG_BEGIN__
$BB dmesg 2>/dev/null | $BB grep -E 'GEMINI_A72|CPU8|CPU9|hotplug|watchdog' | $BB tail -n 320 || true
$BB printf '%s\n' __A72_TOPOLOGY_REPEAT_TRIGGER_DMESG_END__
$BB printf '%s\n' device_storage_reads=none device_storage_writes=none
$BB printf '%s\n' load_probe=none retry_request=none reboot_request=none
$BB printf '%s\n' __A72_TOPOLOGY_REPEAT_TRIGGER_END__
exit "$trigger_write_status"
