#!/bin/sh
# SPDX-License-Identifier: MIT
# One admitted read; invoke through the baseline's pinned authenticated channel.
# This file has no device-write or mount action. /run state is RAM-only.
# shellcheck disable=SC2016 # awk and the child sh intentionally expand locally.
set -eu
export LC_ALL=C
BB=/bin/busybox
STATE=/run/gemini-emmc-readonly

refuse() { printf 'refused=%s\n' "$1" >&2; exit 2; }
[ "$#" = 4 ] || refuse require-boot-id-release-padded-sha256-busybox-sha256
BOOT=$1 RELEASE=$2 EXPECTED=$3 EXPECTED_BB=$4
printf '%s\n' "$BOOT" | $BB grep -Eq '^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$' || refuse boot-id-format
printf '%s\n' "$RELEASE" | $BB grep -Eq '^[A-Za-z0-9_.+-]+$' || refuse release-format
for digest in "$EXPECTED" "$EXPECTED_BB"; do
    printf '%s\n' "$digest" | $BB grep -Eq '^[0-9a-f]{64}$' || refuse digest-format
done
[ "$($BB sha256sum "$BB" | $BB cut -d ' ' -f 1)" = "$EXPECTED_BB" ] || refuse busybox-identity

runtime_guard() {
    [ "$($BB cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] || refuse boot-id
    [ "$($BB uname -r)" = "$RELEASE" ] || refuse kernel-release
    [ "$($BB uname -m)" = aarch64 ] || refuse architecture
    [ "$($BB cat /sys/devices/system/cpu/possible)" = 0-9 ] || refuse cpu-possible
    [ "$($BB cat /sys/devices/system/cpu/present)" = 0-9 ] || refuse cpu-present
    [ "$($BB cat /sys/devices/system/cpu/online)" = 0-7 ] || refuse cpu-online
    [ "$($BB cat /sys/devices/system/cpu/offline)" = 8-9 ] || refuse cpu-offline
    self=$($BB readlink /proc/self/ns/mnt) || refuse self-namespace
    init=$($BB readlink /proc/1/ns/mnt) || refuse init-namespace
    printf '%s\n' "$self" | $BB grep -Eq '^mnt:\[[0-9]+\]$' || refuse namespace-format
    [ "$self" = "$init" ] || refuse namespace
    # RAM root, explicit tmpfs /run, and no block-backed mount anywhere.
    # Reject malformed, duplicate, missing and ambiguous mount observations.
    $BB awk '
      function bad() { fail=1; exit 1 }
      {
        if (NF<10 || $1 !~ /^[1-9][0-9]*$/ || seen[$1]++ ||
            $2 !~ /^[0-9]+$/ || $3 !~ /^0:[0-9]+$/ ||
            $4 !~ /^\// || $5 !~ /^\//) bad()
        sep=0
        for (i=7;i<=NF;i++) if ($i=="-") { if(sep) bad(); sep=i }
        if (!sep || sep+3!=NF) bad()
        if ($5=="/") { roots++; if ($(sep+1)!="rootfs" && $(sep+1)!="tmpfs") bad() }
        if ($5=="/run") { runs++; if ($(sep+1)!="tmpfs") bad() }
        # No nested mount may redirect this packet state to another filesystem.
        if ($5 ~ /^\/run\/gemini-emmc-readonly(\/|$)/) bad()
        rows++
      }
      END { if(fail || !rows || roots!=1 || runs!=1) exit 1 }
    ' /proc/self/mountinfo || refuse ram-mount-contract
    [ "$($BB readlink -f /run)" = /run ] || refuse run-alias
    $BB awk 'NR==1 {if(NF!=5 || $1!="Filename" || $2!="Type" || $3!="Size" || $4!="Used" || $5!="Priority") exit 1; next} {exit 1} END {if(NR!=1) exit 1}' /proc/swaps || refuse swap
}

resolve_target() {
    count=0 target=
    for entry in /sys/class/block/*; do
        [ -f "$entry/partition" ] || continue
        partname=$($BB awk -F= '$1=="PARTNAME" {n++; v=$2} END {if(n>1) exit 1; if(n==1) print v}' "$entry/uevent") || refuse duplicate-partname
        [ "$partname" = boot2 ] || continue
        count=$((count+1))
        name=${entry##*/}
        printf '%s\n' "$name" | $BB grep -Eq '^mmcblk0p[1-9][0-9]*$' || refuse boot2-parent-name
        target=/dev/$name
        sys=$($BB readlink -f "$entry") || refuse target-sysfs
    done
    [ "$count" = 1 ] || refuse boot2-count
    case "$sys" in /sys/devices/*/mmc_host/mmc0/mmc0:0001/block/mmcblk0/mmcblk0p*) ;; *) refuse target-sysfs-path;; esac
    [ "$($BB cat "$sys/size")" = 32768 ] || refuse boot2-size
    partition=$($BB cat "$sys/partition") || refuse partition-number
    printf '%s\n' "$partition" | $BB grep -Eq '^[1-9][0-9]*$' || refuse partition-format
    [ "$name" = "mmcblk0p$partition" ] || refuse partition-name
    parent=${sys%/*}
    [ "$($BB readlink -f /sys/class/block/mmcblk0)" = "$parent" ] || refuse parent-class
    [ "$($BB cat "$parent/size")" = 122142720 ] || refuse parent-size
    [ "$($BB cat "$parent/device/type")" = MMC ] || refuse card-type
    [ "$($BB readlink -f /sys/bus/platform/devices/11230000.mmc/driver)" = /sys/bus/platform/drivers/mtk-msdc ] || refuse host-driver
    for path in "$sys" "$parent"; do
        number=$($BB cat "$path/dev") || refuse missing-device-number
        printf '%s\n' "$number" | $BB grep -Eq '^179:(0|[1-9][0-9]*)$' || refuse device-number-format
        [ "$($BB readlink -f "/sys/dev/block/$number")" = "$path" ] || refuse device-number-sysfs
        node=/dev/${path##*/}
        major=${number%:*} minor=${number#*:}
        [ "$minor" -le 1048575 ] || refuse minor-range
        actual=$($BB stat -L -c '%F|%t:%T' "$node") || refuse device-stat
        expected_stat=$(printf 'block special file|%x:%x' "$major" "$minor")
        [ "$actual" = "$expected_stat" ] || refuse device-number-node
        holders=$($BB find "$path/holders" -mindepth 1 -maxdepth 1 -print) || refuse holder-inspection
        [ -z "$holders" ] || refuse holders
    done
    target_number=$($BB cat "$sys/dev") || refuse target-number
    start=$($BB cat "$sys/start") || refuse target-start
    printf '%s\n' "$start" | $BB grep -Eq '^[1-9][0-9]*$' || refuse target-start-format
    [ "$start" -le 122109952 ] || refuse target-range
}

runtime_guard
resolve_target
initial_target=$target initial_number=$target_number initial_start=$start
# mkdir is the atomic per-boot admission lock. Never remove the tombstone, even
# on pre-read refusal, interruption, or failure; a custodian reviews every run.
$BB mkdir -m 700 "$STATE" || refuse prior-attempt-or-unsafe-state
cleanup() { $BB rm -f "$STATE/dd.status" "$STATE/dd.stderr" "$STATE/read.sha" "$STATE/log.before" "$STATE/log.after"; }
trap cleanup EXIT
trap 'exit 130' HUP INT TERM
printf 'attempt-consumed\n' > "$STATE/consumed"
$BB dmesg > "$STATE/log.before" || refuse kernel-log-before
ERROR_PATTERN='(mmc|msdc|pwrap).*(error|fail|timeout|timed out|crc|defer|returned -)|I/O error|Buffer I/O|blk_update_request|blk_print_req_error'
grep_status=0
prior_errors=$($BB grep -Eic "$ERROR_PATTERN" "$STATE/log.before") || grep_status=$?
[ "$grep_status" -le 1 ] || refuse kernel-log-before-parser
[ "$prior_errors" = 0 ] || refuse prior-controller-error
runtime_guard
resolve_target
[ "$target|$target_number|$start" = "$initial_target|$initial_number|$initial_start" ] || refuse changed-target
before=$($BB date +%s) || refuse clock
printf '%s\n' __GEMINI_EMMC_READONLY_BEGIN__
printf 'boot_id=%s\nkernel_release=%s\nexpected_sha256=%s\nbusybox_sha256=%s\n' "$BOOT" "$RELEASE" "$EXPECTED" "$EXPECTED_BB"
printf 'target=%s\ntarget_major_minor=%s\ntarget_start_sector=%s\n' "$target" "$target_number" "$start"
printf 'read_attempts=1\nrequested_bytes=16777216\nread_timeout_seconds=20\n'
# Only dd opens the partition, and only as input. Its status travels separately
# from the data pipe; sha256sum never receives diagnostic text. No raw capture.
# timeout may not kill an uninterruptible kernel task: lost completion consumes
# the attempt and requires recovery; it never permits another read.
$BB timeout -s KILL 20 "$BB" sh -c '
  "$1" dd if="$2" bs=4096 count=4096 2>"$3/dd.stderr"
  result=$?
  printf "%s\n" "$result" > "$3/dd.status"
  exit "$result"
' read "$BB" "$target" "$STATE" | $BB sha256sum > "$STATE/read.sha"
after=$($BB date +%s) || refuse clock
status=$($BB cat "$STATE/dd.status" 2>/dev/null) || refuse missing-dd-completion
read_sha=$($BB cut -d ' ' -f 1 "$STATE/read.sha") || refuse missing-sha256
runtime_guard
resolve_target
[ "$target|$target_number|$start" = "$initial_target|$initial_number|$initial_start" ] || refuse changed-target-after-read
$BB dmesg > "$STATE/log.after" || refuse kernel-log-after
grep_status=0
errors=$($BB grep -Eic "$ERROR_PATTERN" "$STATE/log.after") || grep_status=$?
[ "$grep_status" -le 1 ] || refuse kernel-log-after-parser
printf 'dd_status=%s\nread_sha256=%s\nelapsed_seconds=%s\ncontroller_error_count=%s\n' "$status" "$read_sha" "$((after-before))" "$errors"
printf 'kernel_log_before_sha256=%s\n' "$($BB sha256sum "$STATE/log.before" | $BB cut -d ' ' -f 1)"
printf 'kernel_log_after_sha256=%s\n' "$($BB sha256sum "$STATE/log.after" | $BB cut -d ' ' -f 1)"
printf 'guards_after=pass\ndevice_storage_writes=none\nmount_requests=none\nsysfs_writes=none\n'
printf '%s\n' __GEMINI_EMMC_READONLY_END__
