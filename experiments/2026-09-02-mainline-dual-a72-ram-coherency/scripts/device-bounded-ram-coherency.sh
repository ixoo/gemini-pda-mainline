#!/bin/sh

# Run one finite, bidirectional RAM-backed integrity observation on CPUs 8/9.
# shellcheck disable=SC2016 # Device-side awk programs are intentionally literal.
set -u
export LC_ALL=C
BB=/bin/busybox
EXPECTED_BOOT_ID=__EXPECTED_BOOT_ID__
EXPECTED_PAYLOAD_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
EXPECTED_PAYLOAD_SIZE=1914704
FILE8=/run/.gemini-a72-cpu8-payload
FILE9=/run/.gemini-a72-cpu9-payload

cleanup()
{
	$BB rm -f -- "$FILE8" "$FILE9"
}

file_state()
{
	if [ -e "$1" ]; then
		$BB printf present
	else
		$BB printf absent
	fi
}

finish_failure()
{
	$BB printf 'probe_result=fail\nprobe_failure=%s\n' "$1"
	cleanup
	$BB printf 'cleanup_file8=%s\n' "$(file_state "$FILE8")"
	$BB printf 'cleanup_file9=%s\n' "$(file_state "$FILE9")"
	$BB printf '%s\n' __GEMINI_A72_RAM_COHERENCY_END__
	exit 3
}

trap cleanup EXIT HUP INT TERM
$BB printf '%s\n' __GEMINI_A72_RAM_COHERENCY_BEGIN__
boot_id=$($BB cat /proc/sys/kernel/random/boot_id 2>/dev/null)
$BB printf 'boot_id=%s\n' "$boot_id"
[ "$boot_id" = "$EXPECTED_BOOT_ID" ] || finish_failure boot-id-changed
$BB printf 'kernel_release='; $BB uname -r
$BB printf 'cpu_online='; $BB cat /sys/devices/system/cpu/online
$BB printf 'cpu_offline='; $BB cat /sys/devices/system/cpu/offline
[ "$($BB cat /sys/devices/system/cpu/online)" = 0-9 ] || finish_failure cpu-set-not-online
[ -z "$($BB cat /sys/devices/system/cpu/offline)" ] || finish_failure cpu-set-still-offline

root_entries=$($BB awk '$2 == "/" { count++ } END { print count + 0 }' /proc/mounts)
root_source=$($BB awk '$2 == "/" { print $1 }' /proc/mounts)
root_fstype=$($BB awk '$2 == "/" { print $3 }' /proc/mounts)
run_mount_entries=$($BB awk '$2 == "/run" { count++ } END { print count + 0 }' /proc/mounts)
block_mounts=$($BB awk '$1 ~ /^\/dev\// { count++ } END { print count + 0 }' /proc/mounts)
$BB printf 'root_entries=%s\nroot_source=%s\nroot_fstype=%s\n' \
	"$root_entries" "$root_source" "$root_fstype"
$BB printf 'run_mount_entries=%s\nblock_mounts=%s\n' "$run_mount_entries" "$block_mounts"
[ "$root_entries" = 1 ] || finish_failure root-mount-ambiguous
[ "$root_source" = rootfs ] || finish_failure root-not-ram-backed
[ "$root_fstype" = rootfs ] || finish_failure root-fstype-not-rootfs
[ "$run_mount_entries" = 0 ] || finish_failure run-has-separate-mount
[ "$block_mounts" = 0 ] || finish_failure block-device-mounted
[ -d /run ] && [ -w /run ] || finish_failure run-not-writable
[ ! -e "$FILE8" ] && [ ! -e "$FILE9" ] || finish_failure stale-probe-file

for cpu in 8 9; do
	topology=/sys/devices/system/cpu/cpu${cpu}/topology
	[ -d "$topology" ] || finish_failure topology-missing
	$BB printf 'cpu%s_core_id=' "$cpu"; $BB cat "$topology/core_id"
	$BB printf 'cpu%s_package_id=' "$cpu"; $BB cat "$topology/physical_package_id"
	$BB printf 'cpu%s_core_siblings=' "$cpu"; $BB cat "$topology/core_siblings_list"
	$BB printf 'cpu%s_thread_siblings=' "$cpu"; $BB cat "$topology/thread_siblings_list"
done

cpu8_affinity=$($BB taskset 100 $BB awk '$1 == "Cpus_allowed_list:" { print $2 }' /proc/self/status)
cpu9_affinity=$($BB taskset 200 $BB awk '$1 == "Cpus_allowed_list:" { print $2 }' /proc/self/status)
cpu8_processor=$($BB taskset 100 $BB awk '{ print $39 }' /proc/self/stat)
cpu9_processor=$($BB taskset 200 $BB awk '{ print $39 }' /proc/self/stat)
$BB printf 'cpu8_affinity=%s\ncpu9_affinity=%s\n' "$cpu8_affinity" "$cpu9_affinity"
$BB printf 'cpu8_processor=%s\ncpu9_processor=%s\n' "$cpu8_processor" "$cpu9_processor"
[ "$cpu8_affinity" = 8 ] && [ "$cpu8_processor" = 8 ] || finish_failure cpu8-affinity-failed
[ "$cpu9_affinity" = 9 ] && [ "$cpu9_processor" = 9 ] || finish_failure cpu9-affinity-failed

$BB printf 'cpu8_stat_before='; $BB grep '^cpu8 ' /proc/stat
$BB printf 'cpu9_stat_before='; $BB grep '^cpu9 ' /proc/stat
source8=$($BB taskset 100 $BB sha256sum /bin/busybox | $BB awk '{ print $1 }')
source9=$($BB taskset 200 $BB sha256sum /bin/busybox | $BB awk '{ print $1 }')
$BB printf 'source_cpu8_sha256=%s\nsource_cpu9_sha256=%s\n' "$source8" "$source9"
[ "$source8" = "$EXPECTED_PAYLOAD_SHA256" ] || finish_failure cpu8-source-checksum-mismatch
[ "$source9" = "$EXPECTED_PAYLOAD_SHA256" ] || finish_failure cpu9-source-checksum-mismatch

$BB taskset 100 $BB dd if=/bin/busybox of="$FILE8" bs=65536 2>/dev/null || finish_failure cpu8-copy-failed
size8=$($BB wc -c <"$FILE8" | $BB tr -d ' ')
writer8=$($BB taskset 100 $BB sha256sum "$FILE8" | $BB awk '{ print $1 }')
reader9=$($BB taskset 200 $BB sha256sum "$FILE8" | $BB awk '{ print $1 }')
$BB printf 'file8_size=%s\nfile8_writer_cpu8_sha256=%s\nfile8_reader_cpu9_sha256=%s\n' \
	"$size8" "$writer8" "$reader9"
[ "$size8" = "$EXPECTED_PAYLOAD_SIZE" ] || finish_failure file8-size-mismatch
[ "$writer8" = "$EXPECTED_PAYLOAD_SHA256" ] || finish_failure file8-writer-mismatch
[ "$reader9" = "$EXPECTED_PAYLOAD_SHA256" ] || finish_failure file8-reader-mismatch

$BB taskset 200 $BB dd if=/bin/busybox of="$FILE9" bs=65536 2>/dev/null || finish_failure cpu9-copy-failed
size9=$($BB wc -c <"$FILE9" | $BB tr -d ' ')
writer9=$($BB taskset 200 $BB sha256sum "$FILE9" | $BB awk '{ print $1 }')
reader8=$($BB taskset 100 $BB sha256sum "$FILE9" | $BB awk '{ print $1 }')
$BB printf 'file9_size=%s\nfile9_writer_cpu9_sha256=%s\nfile9_reader_cpu8_sha256=%s\n' \
	"$size9" "$writer9" "$reader8"
[ "$size9" = "$EXPECTED_PAYLOAD_SIZE" ] || finish_failure file9-size-mismatch
[ "$writer9" = "$EXPECTED_PAYLOAD_SHA256" ] || finish_failure file9-writer-mismatch
[ "$reader8" = "$EXPECTED_PAYLOAD_SHA256" ] || finish_failure file9-reader-mismatch

$BB taskset 100 $BB sleep 1 || finish_failure cpu8-bounded-wait-failed
$BB taskset 200 $BB sleep 1 || finish_failure cpu9-bounded-wait-failed
$BB printf 'cpu8_stat_after='; $BB grep '^cpu8 ' /proc/stat
$BB printf 'cpu9_stat_after='; $BB grep '^cpu9 ' /proc/stat
cleanup
$BB printf 'cleanup_file8=%s\n' "$(file_state "$FILE8")"
$BB printf 'cleanup_file9=%s\n' "$(file_state "$FILE9")"
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' cpu_off_request=none
$BB printf '%s\n' retry_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' probe_result=pass
$BB printf '%s\n' __GEMINI_A72_RAM_COHERENCY_END__
trap - EXIT HUP INT TERM
exit 0
