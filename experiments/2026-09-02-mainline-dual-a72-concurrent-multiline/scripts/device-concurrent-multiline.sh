#!/bin/sh

# Run one finite concurrent disjoint-write and peer-read workload on CPU8/9.
# shellcheck disable=SC2016 # Worker bodies are intentionally passed literally.
set -u
export LC_ALL=C
BB=/bin/busybox
EXPECTED_BOOT_ID=__EXPECTED_BOOT_ID__
EXPECTED_PAYLOAD_SHA256=52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933
EXPECTED_PAYLOAD_SIZE=1914704
ROUNDS=4
SPIN_LIMIT=1000000
FILE8=/run/.gemini-a72-concurrent-file8
FILE9=/run/.gemini-a72-concurrent-file9
OUT8=/run/.gemini-a72-concurrent-out8
OUT9=/run/.gemini-a72-concurrent-out9
READ8=/run/.gemini-a72-concurrent-read8
READ9=/run/.gemini-a72-concurrent-read9
START_WRITE=/run/.gemini-a72-concurrent-start-write
START_READ=/run/.gemini-a72-concurrent-start-read

cleanup()
{
	$BB rm -f -- "$FILE8" "$FILE9" "$OUT8" "$OUT9" "$READ8" "$READ9" \
		"$START_WRITE" "$START_READ"
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
	$BB printf 'concurrent_result=fail\nconcurrent_failure=%s\n' "$1"
	for output in "$OUT8" "$OUT9" "$READ8" "$READ9"; do
		[ ! -f "$output" ] || $BB cat "$output"
	done
	cleanup
	$BB printf 'cleanup_file8=%s\n' "$(file_state "$FILE8")"
	$BB printf 'cleanup_file9=%s\n' "$(file_state "$FILE9")"
	$BB printf 'cleanup_auxiliary=absent\n'
	$BB printf '%s\n' __GEMINI_A72_CONCURRENT_MULTILINE_END__
	exit 3
}

trap cleanup EXIT HUP INT TERM
$BB printf '%s\n' __GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__
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
for item in "$FILE8" "$FILE9" "$OUT8" "$OUT9" "$READ8" "$READ9" \
	"$START_WRITE" "$START_READ"; do
	[ ! -e "$item" ] || finish_failure stale-workload-file
done

$BB printf 'rounds=%s\npayload_size=%s\npayload_sha256=%s\n' \
	"$ROUNDS" "$EXPECTED_PAYLOAD_SIZE" "$EXPECTED_PAYLOAD_SHA256"
$BB printf 'writer_start_barrier=bounded-file-publication\n'
$BB printf 'reader_start_barrier=bounded-file-publication\n'
$BB printf 'spin_limit=%s\n' "$SPIN_LIMIT"
$BB printf 'cpu8_stat_before='; $BB grep '^cpu8 ' /proc/stat
$BB printf 'cpu9_stat_before='; $BB grep '^cpu9 ' /proc/stat

$BB taskset 100 $BB sh -c '
set -u
BB=/bin/busybox
prefix=$1
payload=$2
target=$3
start=$4
rounds=$5
expected=$6
spin_limit=$7
spin=0
while [ ! -e "$start" ]; do
	spin=$((spin + 1))
	[ "$spin" -lt "$spin_limit" ] || exit 10
done
affinity=$($BB awk '\''$1 == "Cpus_allowed_list:" { print $2 }'\'' /proc/self/status)
processor=$($BB awk '\''{ print $39 }'\'' /proc/self/stat)
done_rounds=0
checksum=none
while [ "$done_rounds" -lt "$rounds" ]; do
	$BB dd if="$payload" of="$target" bs=65536 2>/dev/null || exit 11
	checksum=$($BB sha256sum "$target" | $BB awk '\''{ print $1 }'\'')
	[ "$checksum" = "$expected" ] || exit 12
	done_rounds=$((done_rounds + 1))
done
size=$($BB wc -c <"$target" | $BB tr -d " ")
$BB printf "%s_affinity=%s\n%s_processor=%s\n" "$prefix" "$affinity" "$prefix" "$processor"
$BB printf "%s_rounds_completed=%s\n%s_size=%s\n%s_sha256=%s\n" \
	"$prefix" "$done_rounds" "$prefix" "$size" "$prefix" "$checksum"
' sh writer8 /bin/busybox "$FILE8" "$START_WRITE" "$ROUNDS" \
	"$EXPECTED_PAYLOAD_SHA256" "$SPIN_LIMIT" >"$OUT8" 2>&1 &
pid8=$!
$BB taskset 200 $BB sh -c '
set -u
BB=/bin/busybox
prefix=$1
payload=$2
target=$3
start=$4
rounds=$5
expected=$6
spin_limit=$7
spin=0
while [ ! -e "$start" ]; do
	spin=$((spin + 1))
	[ "$spin" -lt "$spin_limit" ] || exit 10
done
affinity=$($BB awk '\''$1 == "Cpus_allowed_list:" { print $2 }'\'' /proc/self/status)
processor=$($BB awk '\''{ print $39 }'\'' /proc/self/stat)
done_rounds=0
checksum=none
while [ "$done_rounds" -lt "$rounds" ]; do
	$BB dd if="$payload" of="$target" bs=65536 2>/dev/null || exit 11
	checksum=$($BB sha256sum "$target" | $BB awk '\''{ print $1 }'\'')
	[ "$checksum" = "$expected" ] || exit 12
	done_rounds=$((done_rounds + 1))
done
size=$($BB wc -c <"$target" | $BB tr -d " ")
$BB printf "%s_affinity=%s\n%s_processor=%s\n" "$prefix" "$affinity" "$prefix" "$processor"
$BB printf "%s_rounds_completed=%s\n%s_size=%s\n%s_sha256=%s\n" \
	"$prefix" "$done_rounds" "$prefix" "$size" "$prefix" "$checksum"
' sh writer9 /bin/busybox "$FILE9" "$START_WRITE" "$ROUNDS" \
	"$EXPECTED_PAYLOAD_SHA256" "$SPIN_LIMIT" >"$OUT9" 2>&1 &
pid9=$!
$BB touch "$START_WRITE" || finish_failure writer-start-publication-failed
wait "$pid8"; writer8_status=$?
wait "$pid9"; writer9_status=$?
$BB cat "$OUT8"
$BB cat "$OUT9"
$BB printf 'writer8_status=%s\nwriter9_status=%s\n' "$writer8_status" "$writer9_status"
[ "$writer8_status" = 0 ] && [ "$writer9_status" = 0 ] || finish_failure writer-child-failed

$BB taskset 100 $BB sh -c '
set -u
BB=/bin/busybox
prefix=$1
peer=$2
start=$3
rounds=$4
expected=$5
spin_limit=$6
spin=0
while [ ! -e "$start" ]; do
	spin=$((spin + 1))
	[ "$spin" -lt "$spin_limit" ] || exit 20
done
affinity=$($BB awk '\''$1 == "Cpus_allowed_list:" { print $2 }'\'' /proc/self/status)
processor=$($BB awk '\''{ print $39 }'\'' /proc/self/stat)
done_rounds=0
checksum=none
while [ "$done_rounds" -lt "$rounds" ]; do
	checksum=$($BB sha256sum "$peer" | $BB awk '\''{ print $1 }'\'')
	[ "$checksum" = "$expected" ] || exit 21
	done_rounds=$((done_rounds + 1))
done
$BB printf "%s_affinity=%s\n%s_processor=%s\n" "$prefix" "$affinity" "$prefix" "$processor"
$BB printf "%s_rounds_completed=%s\n%s_peer_sha256=%s\n" \
	"$prefix" "$done_rounds" "$prefix" "$checksum"
' sh reader8 "$FILE9" "$START_READ" "$ROUNDS" \
	"$EXPECTED_PAYLOAD_SHA256" "$SPIN_LIMIT" >"$READ8" 2>&1 &
reader_pid8=$!
$BB taskset 200 $BB sh -c '
set -u
BB=/bin/busybox
prefix=$1
peer=$2
start=$3
rounds=$4
expected=$5
spin_limit=$6
spin=0
while [ ! -e "$start" ]; do
	spin=$((spin + 1))
	[ "$spin" -lt "$spin_limit" ] || exit 20
done
affinity=$($BB awk '\''$1 == "Cpus_allowed_list:" { print $2 }'\'' /proc/self/status)
processor=$($BB awk '\''{ print $39 }'\'' /proc/self/stat)
done_rounds=0
checksum=none
while [ "$done_rounds" -lt "$rounds" ]; do
	checksum=$($BB sha256sum "$peer" | $BB awk '\''{ print $1 }'\'')
	[ "$checksum" = "$expected" ] || exit 21
	done_rounds=$((done_rounds + 1))
done
$BB printf "%s_affinity=%s\n%s_processor=%s\n" "$prefix" "$affinity" "$prefix" "$processor"
$BB printf "%s_rounds_completed=%s\n%s_peer_sha256=%s\n" \
	"$prefix" "$done_rounds" "$prefix" "$checksum"
' sh reader9 "$FILE8" "$START_READ" "$ROUNDS" \
	"$EXPECTED_PAYLOAD_SHA256" "$SPIN_LIMIT" >"$READ9" 2>&1 &
reader_pid9=$!
$BB touch "$START_READ" || finish_failure reader-start-publication-failed
wait "$reader_pid8"; reader8_status=$?
wait "$reader_pid9"; reader9_status=$?
$BB cat "$READ8"
$BB cat "$READ9"
$BB printf 'reader8_status=%s\nreader9_status=%s\n' "$reader8_status" "$reader9_status"
[ "$reader8_status" = 0 ] && [ "$reader9_status" = 0 ] || finish_failure reader-child-failed

$BB printf 'cpu8_stat_after='; $BB grep '^cpu8 ' /proc/stat
$BB printf 'cpu9_stat_after='; $BB grep '^cpu9 ' /proc/stat
cleanup
$BB printf 'cleanup_file8=%s\n' "$(file_state "$FILE8")"
$BB printf 'cleanup_file9=%s\n' "$(file_state "$FILE9")"
$BB printf 'cleanup_auxiliary=absent\n'
$BB printf '%s\n' device_partition_reads=none
$BB printf '%s\n' device_storage_writes=none
$BB printf '%s\n' cpu_off_request=none
$BB printf '%s\n' retry_request=none
$BB printf '%s\n' reboot_request=none
$BB printf '%s\n' concurrent_result=pass
$BB printf '%s\n' __GEMINI_A72_CONCURRENT_MULTILINE_END__
trap - EXIT HUP INT TERM
exit 0
