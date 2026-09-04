#!/usr/bin/env bash

# Materialize one boot-bound stage-18, thermal, and frequency observation run.
set -euo pipefail
export LC_ALL=C
umask 077

readonly LIFECYCLE_BUILDER_SHA256=dfec77a10d504a6027b1c58825f3723b366133c4f2e05c0630b1d45402e01624
readonly CONCURRENT_SOURCE_SHA256=c6bc8a26f2f79487d1bbfd9c8a294e589afd02ba17acf31647736dff7f100316
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --boot-id ]] || die "usage: $0 --boot-id UUID"
boot_id=$2
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] ||
	die 'boot ID is malformed'
for command in mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repository=$(cd -- "$script_dir/../../.." && pwd -P)
lifecycle_builder=$repository/experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/build-topology-repeat-trigger.sh
concurrent_source=$repository/experiments/2026-09-02-mainline-dual-a72-concurrent-multiline/scripts/device-concurrent-multiline.sh
for path in "$lifecycle_builder" "$concurrent_source"; do
	[[ -f "$path" && ! -L "$path" ]] || die "required source is absent or unsafe: $path"
done
[[ "$(sha256sum "$lifecycle_builder" | awk '{print $1}')" == "$LIFECYCLE_BUILDER_SHA256" ]] ||
	die 'lifecycle builder changed'
[[ "$(sha256sum "$concurrent_source" | awk '{print $1}')" == "$CONCURRENT_SOURCE_SHA256" ]] ||
	die 'concurrent source changed'

lifecycle=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-frequency-lifecycle.XXXXXXXX")
concurrent=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-frequency-concurrent.XXXXXXXX")
cleanup() { rm -f -- "${lifecycle:-}" "${concurrent:-}"; }
trap cleanup EXIT HUP INT TERM
"$lifecycle_builder" --boot-id "$boot_id" >"$lifecycle"
python3 - "$concurrent_source" "$concurrent" "$boot_id" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
marker = "EXPECTED_BOOT_ID=__EXPECTED_BOOT_ID__"
if source.count(marker) != 1:
    raise SystemExit("concurrent boot-ID marker changed")
Path(sys.argv[2]).write_text(
    source.replace(marker, f"EXPECTED_BOOT_ID={sys.argv[3]}", 1),
    encoding="utf-8",
)
PY
python3 - "$lifecycle" "$concurrent" <<'PY'
from pathlib import Path
import sys

lifecycle = Path(sys.argv[1]).read_text(encoding="utf-8")
concurrent = Path(sys.argv[2]).read_text(encoding="utf-8")
shebang = "#!/bin/sh\n"
if lifecycle.count(shebang) != 1 or not lifecycle.startswith(shebang):
    raise SystemExit("lifecycle shebang changed")
lifecycle = lifecycle.replace(
    shebang, shebang + "# shellcheck disable=SC2016\n", 1,
)
identity_replacements = (
    ("[ \"$($BB uname -r)\" = 7.1.3-gemini-a72-hotplug-physical ] || "
     "reject_preflight kernel-identity",
     "[ \"$($BB uname -r)\" = 7.1.3-gemini-a72-frequency-thermal ] || "
     "reject_preflight kernel-identity"),
    ("d4940602e7ad9cbc947376bfb9dc4222ef5a671faa15eb42a821df1852af9ba4",
     "018de9150ffcf0b7b30fe7c45f3863555909c87e92ec4e868f30ef74a0e8cd2e"),
)
for old, new in identity_replacements:
    if lifecycle.count(old) != 1 or lifecycle.count(new) != 0:
        raise SystemExit("unsafe lifecycle production identity substitution")
    lifecycle = lifecycle.replace(old, new, 1)
old_exit = 'exit "$trigger_write_status"\n'
gate = r'''frequency_reject()
{
	$BB printf '__A72_FREQUENCY_THERMAL_REJECTED__ reason=%s\n' "$1"
	$BB printf 'failure_cpu_online='; $BB cat /sys/devices/system/cpu/online
	$BB printf 'failure_cpu_offline='; $BB cat /sys/devices/system/cpu/offline
	$BB printf 'failure_status='; $BB cat "$STATUS" 2>/dev/null || $BB printf 'unreadable\n'
	$BB printf 'failure_frequency_log_count='; $BB dmesg 2>/dev/null |
		$BB grep -Fc 'GEMINI_A72_FREQUENCY_OBSERVATION_V1'
	$BB dmesg 2>/dev/null |
		$BB grep -F 'GEMINI_A72_FREQUENCY_OBSERVATION_V1' |
		$BB tail -n 3 || true
	$BB printf '%s\n' failure_additional_frequency_observation_request=none
	exit 3
}

[ "$trigger_write_status" -eq 0 ] || frequency_reject trigger-write
[ "$remount_ro_status" -eq 0 ] || frequency_reject sysfs-remount-ro
[ "$($BB cat /sys/devices/system/cpu/online)" = 0-9 ] || frequency_reject cpu-online-set
[ -z "$($BB cat /sys/devices/system/cpu/offline)" ] || frequency_reject cpu-offline-set
post_status="$($BB cat "$STATUS" 2>/dev/null)" || frequency_reject status-unreadable
for required in \
	'state=terminal trigger_consumed=1 trigger_executions=1 operation_ret=0 core_consumed=1' \
	'cpu_requests=1 cpu9_requests=1 cpu_off_requests=0 retries=0'; do
	case "$post_status" in
		*"$required"*) ;;
		*) frequency_reject controller-terminal ;;
	esac
done
binder_line="$($BB dmesg 2>/dev/null | $BB grep -F 'GEMINI_A72_HOTPLUG_BINDING_V1' | $BB tail -n 1)"
for required in \
	'GEMINI_A72_HOTPLUG_BINDING_V1 ret=0 terminal=5 last_stage=18 stage_errno=0 publication_errno=0 add_cpu_ret=0' \
	'restore_validation_attempted=1 restore_transaction_valid=1 down_completed=1 restore_completed=1 completed=1' \
	'restore_lifecycle=14 restore_terminal=2 restore_last_stage=18 restore_stage_errno=0 restore_publication_errno=0 p30e_rearmed=1' \
	'cpu8_online=1 cpu9_online=1'; do
	case "$binder_line" in
		*"$required"*) ;;
		*) frequency_reject binder-terminal ;;
	esac
done
[ "$($BB dmesg 2>/dev/null | $BB grep -Fc 'CPU8: Booted secondary processor 0x0000000200 [0x410fd081]')" = 1 ] ||
	frequency_reject cpu8-entry-count
[ "$($BB dmesg 2>/dev/null | $BB grep -Fc 'CPU9: Booted secondary processor 0x0000000201 [0x410fd081]')" = 2 ] ||
	frequency_reject cpu9-entry-count
for mapping in 0,0,0-3 1,1,0-3 2,2,0-3 3,3,0-3 4,0,4-7 5,1,4-7 6,2,4-7 7,3,4-7 8,0,8-9 9,1,8-9; do
	cpu=${mapping%%,*}
	remainder=${mapping#*,}
	core=${remainder%%,*}
	cluster=${remainder#*,}
	topology=/sys/devices/system/cpu/cpu${cpu}/topology
	[ "$($BB cat "$topology/physical_package_id")" = 0 ] || frequency_reject topology-package
	[ "$($BB cat "$topology/core_id")" = "$core" ] || frequency_reject topology-core
	[ "$($BB cat "$topology/core_siblings_list")" = 0-9 ] || frequency_reject topology-package-siblings
	[ "$($BB cat "$topology/cluster_cpus_list")" = "$cluster" ] || frequency_reject topology-cluster
	[ "$($BB cat "$topology/thread_siblings_list")" = "$cpu" ] || frequency_reject topology-thread
done

frequency_observer_count=0
FREQUENCY_OBSERVER=none
for item in /sys/bus/platform/devices/*/a72_frequency_observation; do
	[ -r "$item" ] || continue
	frequency_observer_count=$((frequency_observer_count + 1))
	FREQUENCY_OBSERVER=$item
done
[ "$frequency_observer_count" = 1 ] || frequency_reject frequency-observer-count
[ "$($BB stat -c %a "$FREQUENCY_OBSERVER")" = 444 ] || frequency_reject frequency-observer-mode
frequency_log_count_before=$($BB dmesg 2>/dev/null | $BB grep -Fc 'GEMINI_A72_FREQUENCY_OBSERVATION_V1')
[ "$frequency_log_count_before" = 0 ] || frequency_reject frequency-observer-not-pristine
thermal_zone_count=0
THERMAL_ZONE=none
thermal_zone_type=none
for item in /sys/class/thermal/thermal_zone[0-9]*; do
	[ -r "$item/type" ] && [ -r "$item/temp" ] || continue
	thermal_zone_count=$((thermal_zone_count + 1))
	THERMAL_ZONE=$item
	thermal_zone_type=$($BB cat "$item/type")
done
[ "$thermal_zone_count" = 1 ] || frequency_reject thermal-zone-count
[ "$thermal_zone_type" = soc-thermal ] || frequency_reject thermal-zone-type

frequency_observe()
{
	label=$1
	observation=$($BB cat "$FREQUENCY_OBSERVER" 2>/dev/null) ||
		frequency_reject "frequency-${label}"
	temperature=$($BB cat "$THERMAL_ZONE/temp" 2>/dev/null) ||
		frequency_reject "thermal-${label}"
	$BB printf 'frequency_%s=%s\n' "$label" "$observation"
	$BB printf 'thermal_%s_millicelsius=%s\n' "$label" "$temperature"
}

$BB printf '%s\n' __A72_FREQUENCY_THERMAL_BEGIN__
$BB printf 'frequency_observer_count=%s\n' "$frequency_observer_count"
$BB printf 'frequency_observer_mode=%s\n' "$($BB stat -c %a "$FREQUENCY_OBSERVER")"
$BB printf 'frequency_log_count_before=%s\n' "$frequency_log_count_before"
$BB printf 'thermal_zone_count=%s\nthermal_zone_type=%s\n' "$thermal_zone_count" "$thermal_zone_type"
frequency_observe before
'''
if lifecycle.count(old_exit) != 1:
    raise SystemExit("unsafe lifecycle continuation")
if lifecycle.count("__A72_TOPOLOGY_REPEAT_TRIGGER_BEGIN__") != 1:
    raise SystemExit("lifecycle begin boundary changed")
if lifecycle.count("__A72_TOPOLOGY_REPEAT_TRIGGER_END__") != 2:
    raise SystemExit("lifecycle end boundary changed")
lifecycle = lifecycle.replace(old_exit, gate, 1)

touch = '''$BB touch "$START_WRITE" || finish_failure writer-start-publication-failed
wait "$pid8"; writer8_status=$?'''
during = r'''writer8_alive_before_observation=0
writer9_alive_before_observation=0
$BB kill -0 "$pid8" 2>/dev/null && writer8_alive_before_observation=1
$BB kill -0 "$pid9" 2>/dev/null && writer9_alive_before_observation=1
[ "$writer8_alive_before_observation" = 1 ] && [ "$writer9_alive_before_observation" = 1 ] ||
	finish_failure writer-not-alive-before-observation
$BB printf 'writer8_alive_before_observation=%s\nwriter9_alive_before_observation=%s\n' \
	"$writer8_alive_before_observation" "$writer9_alive_before_observation"
frequency_observe during
writer8_alive_after_observation=0
writer9_alive_after_observation=0
$BB kill -0 "$pid8" 2>/dev/null && writer8_alive_after_observation=1
$BB kill -0 "$pid9" 2>/dev/null && writer9_alive_after_observation=1
[ "$writer8_alive_after_observation" = 1 ] && [ "$writer9_alive_after_observation" = 1 ] ||
	finish_failure writer-not-alive-after-observation
$BB printf 'writer8_alive_after_observation=%s\nwriter9_alive_after_observation=%s\n' \
	"$writer8_alive_after_observation" "$writer9_alive_after_observation"
$BB touch "$START_WRITE" || finish_failure writer-start-publication-failed
$BB printf 'writer_start_released=1\n'
wait "$pid8"; writer8_status=$?'''
if concurrent.count(touch) != 1:
    raise SystemExit("writer release boundary changed")
concurrent = concurrent.replace(touch, during, 1)

after_anchor = '''[ "$reader8_status" = 0 ] && [ "$reader9_status" = 0 ] || finish_failure reader-child-failed

$BB printf 'cpu8_stat_after='; $BB grep '^cpu8 ' /proc/stat'''
after = '''[ "$reader8_status" = 0 ] && [ "$reader9_status" = 0 ] || finish_failure reader-child-failed

frequency_observe after
$BB printf 'cpu8_stat_after='; $BB grep '^cpu8 ' /proc/stat'''
if concurrent.count(after_anchor) != 1:
    raise SystemExit("post-worker observation boundary changed")
concurrent = concurrent.replace(after_anchor, after, 1)

end_anchor = r'''$BB printf '%s\n' concurrent_result=pass
$BB printf '%s\n' __GEMINI_A72_CONCURRENT_MULTILINE_END__'''
end = r'''frequency_log_count=$($BB dmesg 2>/dev/null | $BB grep -Fc 'GEMINI_A72_FREQUENCY_OBSERVATION_V1')
$BB printf 'frequency_log_count=%s\n' "$frequency_log_count"
$BB dmesg 2>/dev/null | $BB grep -F 'GEMINI_A72_FREQUENCY_OBSERVATION_V1' | $BB tail -n 3
$BB printf '%s\n' concurrent_result=pass
$BB printf '%s\n' __GEMINI_A72_CONCURRENT_MULTILINE_END__
$BB printf '%s\n' __A72_FREQUENCY_THERMAL_END__'''
if concurrent.count(end_anchor) != 1:
    raise SystemExit("concurrent completion boundary changed")
concurrent = concurrent.replace(end_anchor, end, 1)
if concurrent.count("__GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__") != 1:
    raise SystemExit("concurrent begin boundary changed")
if concurrent.count("__GEMINI_A72_CONCURRENT_MULTILINE_END__") != 2:
    raise SystemExit("concurrent end boundary changed")
sys.stdout.write(lifecycle)
sys.stdout.write("\n")
sys.stdout.write(concurrent)
PY
