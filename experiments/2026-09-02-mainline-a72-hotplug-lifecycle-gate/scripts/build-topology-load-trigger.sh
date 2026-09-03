#!/usr/bin/env bash

# Materialize one boot-bound device transaction that completes the exact
# lifecycle/topology gate before running the proven bounded RAM observation.
set -euo pipefail
export LC_ALL=C
umask 077

readonly TRIGGER_BUILDER_SHA256=dfec77a10d504a6027b1c58825f3723b366133c4f2e05c0630b1d45402e01624
readonly PROBE_BUILDER_SHA256=daf71fbd3badf5a646afb042730205889624ff03751afe845f69c572a93fea46
die() { printf 'error: %s\n' "$*" >&2; exit 2; }
[[ $# == 2 && $1 == --boot-id ]] || die "usage: $0 --boot-id UUID"
boot_id=$2
[[ "$boot_id" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]] ||
	die 'boot ID is malformed'
for command in mktemp python3 rm sha256sum; do
	command -v "$command" >/dev/null 2>&1 || die "required command missing: $command"
done
script_dir=$(cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(cd -- "$script_dir/../../.." && pwd -P)
trigger_builder="$script_dir/build-topology-repeat-trigger.sh"
probe_builder="$repo_root/experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/remote-bounded-topology-ram.sh"
[[ -f "$trigger_builder" && ! -L "$trigger_builder" ]] ||
	die 'topology-repeat trigger builder is absent or unsafe'
[[ -f "$probe_builder" && ! -L "$probe_builder" ]] ||
	die 'topology/RAM probe builder is absent or unsafe'
[[ "$(sha256sum "$trigger_builder" | awk '{print $1}')" == "$TRIGGER_BUILDER_SHA256" ]] ||
	die 'topology-repeat trigger builder changed'
[[ "$(sha256sum "$probe_builder" | awk '{print $1}')" == "$PROBE_BUILDER_SHA256" ]] ||
	die 'topology/RAM probe builder changed'

trigger=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-topology-load-trigger.XXXXXXXX")
probe=$(mktemp "${TMPDIR:-/tmp}/.gemini-a72-topology-load-probe.XXXXXXXX")
cleanup() { rm -f -- "${trigger:-}" "${probe:-}"; }
trap cleanup EXIT HUP INT TERM
"$trigger_builder" --boot-id "$boot_id" >"$trigger"
"$probe_builder" --boot-id "$boot_id" >"$probe"
python3 - "$trigger" "$probe" <<'PY'
from pathlib import Path
import sys

trigger = Path(sys.argv[1]).read_text(encoding="utf-8")
probe = Path(sys.argv[2]).read_text(encoding="utf-8")
shebang = "#!/bin/sh\n"
if trigger.count(shebang) != 1 or not trigger.startswith(shebang):
    raise SystemExit("topology-repeat trigger shebang changed")
trigger = trigger.replace(shebang, shebang + "# shellcheck disable=SC2016\n", 1)
old = 'exit "$trigger_write_status"\n'
gate = r'''integrated_reject()
{
	$BB printf '__A72_TOPOLOGY_LOAD_GATE_REJECTED__ reason=%s\n' "$1"
	exit 3
}

[ "$trigger_write_status" -eq 0 ] || integrated_reject trigger-write
[ "$remount_ro_status" -eq 0 ] || integrated_reject sysfs-remount-ro
[ "$($BB cat /sys/devices/system/cpu/online)" = 0-9 ] || integrated_reject cpu-online-set
[ -z "$($BB cat /sys/devices/system/cpu/offline)" ] || integrated_reject cpu-offline-set
post_status="$($BB cat "$STATUS" 2>/dev/null)" || integrated_reject status-unreadable
for required in \
	'state=terminal trigger_consumed=1 trigger_executions=1 operation_ret=0 core_consumed=1' \
	'cpu_requests=1 cpu9_requests=1 cpu_off_requests=0 retries=0'; do
	case "$post_status" in
		*"$required"*) ;;
		*) integrated_reject controller-terminal ;;
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
		*) integrated_reject binder-terminal ;;
	esac
done
[ "$($BB dmesg 2>/dev/null | $BB grep -Fc 'CPU8: Booted secondary processor 0x0000000200 [0x410fd081]')" = 1 ] ||
	integrated_reject cpu8-entry-count
[ "$($BB dmesg 2>/dev/null | $BB grep -Fc 'CPU9: Booted secondary processor 0x0000000201 [0x410fd081]')" = 2 ] ||
	integrated_reject cpu9-entry-count
for mapping in 0,0,0-3 1,1,0-3 2,2,0-3 3,3,0-3 4,0,4-7 5,1,4-7 6,2,4-7 7,3,4-7 8,0,8-9 9,1,8-9; do
	cpu=${mapping%%,*}
	remainder=${mapping#*,}
	core=${remainder%%,*}
	cluster=${remainder#*,}
	topology=/sys/devices/system/cpu/cpu${cpu}/topology
	[ "$($BB cat "$topology/physical_package_id")" = 0 ] || integrated_reject topology-package
	[ "$($BB cat "$topology/core_id")" = "$core" ] || integrated_reject topology-core
	[ "$($BB cat "$topology/core_siblings_list")" = 0-9 ] || integrated_reject topology-package-siblings
	[ "$($BB cat "$topology/cluster_cpus_list")" = "$cluster" ] || integrated_reject topology-cluster
	[ "$($BB cat "$topology/thread_siblings_list")" = "$cpu" ] || integrated_reject topology-thread
done
$BB printf '%s\n' __A72_TOPOLOGY_LOAD_GATE_PASSED__
'''
if trigger.count(old) != 1:
    raise SystemExit("unsafe topology/load trigger continuation")
if trigger.count("__A72_TOPOLOGY_REPEAT_TRIGGER_BEGIN__") != 1:
    raise SystemExit("topology-repeat trigger begin boundary changed")
if trigger.count("__A72_TOPOLOGY_REPEAT_TRIGGER_END__") != 2:
    raise SystemExit("topology-repeat trigger end boundary changed")
if probe.count("__GEMINI_A72_RAM_COHERENCY_BEGIN__") != 1:
    raise SystemExit("RAM probe begin boundary changed")
if probe.count("__GEMINI_A72_RAM_COHERENCY_END__") != 2:
    raise SystemExit("RAM probe end boundary changed")
sys.stdout.write(trigger.replace(old, gate, 1))
sys.stdout.write("\n")
sys.stdout.write(probe)
PY
