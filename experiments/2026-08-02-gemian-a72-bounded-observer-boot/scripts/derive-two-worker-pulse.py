#!/usr/bin/env python3
"""Derive the single two-worker observer probe from the calibrated probe."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat
import sys


SOURCE_SHA256 = "c04bdfda47676645ef55dc5d99c5d067076b59e6246ae29baa20d848bcd0992d"
TAIL_MARKER = "run_uptime_begin=$(awk '{ print $1 }' /proc/uptime) || fail uptime-begin\n"


class DerivationError(Exception):
    pass


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise DerivationError(f"source contract changed for {old!r}")
    return text.replace(old, new, 1)


def derive(source: bytes) -> bytes:
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise DerivationError("calibrated source SHA-256 changed")
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DerivationError("calibrated source is not UTF-8") from exc

    text = replace_once(text, "export LC_ALL=C\n", "export LC_ALL=C\numask 077\n")
    text = replace_once(text, "interstage_samples=5\n", "")
    text = replace_once(
        text,
        "[ \"$kernel_release\" = 3.18.41+ ] || fail wrong-kernel\n",
        "[ \"$kernel_release\" = 3.18.41+ ] || fail wrong-kernel\n"
        "grep -Fq '#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026' /proc/version ||\n"
        "\tfail wrong-build-identity\n",
    )
    text = replace_once(
        text,
        "boot_id_sha256=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)\n"
        "case \"$boot_id_sha256\" in\n"
        "????????????????????????????????????????????????????????????????) ;;\n"
        "*) fail boot-id-hash ;;\n"
        "esac\n",
        "boot_id_sha256=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)\n"
        "case \"$boot_id_sha256\" in\n"
        "????????????????????????????????????????????????????????????????) ;;\n"
        "*) fail boot-id-hash ;;\n"
        "esac\n"
        "case \"${GEMINI_EXPECTED_BOOT_ID_SHA256:-}\" in\n"
        "????????????????????????????????????????????????????????????????) ;;\n"
        "*) fail expected-boot-id-hash ;;\n"
        "esac\n"
        "[ \"$boot_id_sha256\" = \"$GEMINI_EXPECTED_BOOT_ID_SHA256\" ] ||\n"
        "\tfail wrong-boot-id\n",
    )
    text = replace_once(
        text,
        "printf 'experiment=gemian-a72-load-assisted-observation\\n'\n",
        "printf 'experiment=gemian-a72-bounded-observer-two-worker-pulse\\n'\n",
    )
    text = replace_once(
        text,
        "printf 'stage_workers=0,1,2,4,8,10\\n'\n",
        "printf 'stage_workers=0,2\\n'\n"
        "printf 'pulse_repetitions=1\\n'\n"
        "printf 'build_identity=#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026\\n'\n"
        "printf 'observer_abi=mt6797-a72-transition-observer-v1\\n'\n",
    )

    if text.count(TAIL_MARKER) != 1:
        raise DerivationError("calibrated execution tail changed")
    prefix = text.split(TAIL_MARKER, 1)[0]
    derived_tail = r'''observer=/proc/mt6797_a72_transition
[ -r "$observer" ] || fail observer-unreadable
[ "$(stat -c %a "$observer")" = 400 ] || fail observer-mode

snapshot_observer()
{
	snapshot_label=$1
	snapshot_data=$(cat "$observer") || fail "observer-read-$snapshot_label"
	snapshot_header=$(printf '%s\n' "$snapshot_data" | head -n 1)
	case "$snapshot_header" in
	abi=mt6797-a72-transition-observer-v1\ count=*\ overwritten=*) ;;
	*) fail "observer-header-$snapshot_label" ;;
	esac
	snapshot_count=$(printf '%s\n' "$snapshot_header" |
		awk '{sub(/^count=/, "", $2); print $2}')
	snapshot_overwritten=$(printf '%s\n' "$snapshot_header" |
		awk '{sub(/^overwritten=/, "", $3); print $3}')
	[ "$snapshot_header" = "abi=mt6797-a72-transition-observer-v1 count=$snapshot_count overwritten=$snapshot_overwritten" ] ||
		fail "observer-header-fields-$snapshot_label"
	case "$snapshot_count:$snapshot_overwritten" in
	*[!0-9:]*|:*|*:) fail "observer-count-$snapshot_label" ;;
	esac
	[ "$snapshot_count" -le 256 ] || fail "observer-count-limit-$snapshot_label"
	[ "$(printf '%s\n' "$snapshot_data" | wc -l | awk '{print $1}')" \
		-eq $((snapshot_count + 1)) ] || fail "observer-lines-$snapshot_label"
	printf '__OBSERVER_%s_BEGIN__\n' "$snapshot_label"
	printf '%s\n' "$snapshot_data"
	printf '__OBSERVER_%s_END__\n' "$snapshot_label"
}

snapshot_kernel_alerts()
{
	alert_label=$1
	dmesg >/dev/null 2>&1 || fail "dmesg-read-$alert_label"
	alert_data=$(dmesg 2>/dev/null |
		grep -Ei 'BUG:|WARNING:|Oops:|Kernel panic|watchdog: BUG|soft lockup|hard LOCKUP|Call trace:' |
		tail -n 100 || :)
	if [ -n "$alert_data" ]; then
		alert_count=$(printf '%s\n' "$alert_data" | wc -l | awk '{print $1}')
	else
		alert_count=0
	fi
	printf '__KERNEL_ALERTS_%s_BEGIN__\n' "$alert_label"
	[ -z "$alert_data" ] || printf '%s\n' "$alert_data"
	printf '__KERNEL_ALERTS_%s_END__\n' "$alert_label"
	printf 'kernel_alert_count_%s=%s\n' "$alert_label" "$alert_count"
}

run_uptime_begin=$(awk '{ print $1 }' /proc/uptime) || fail uptime-begin
printf 'run_uptime_begin=%s\n' "$run_uptime_begin"
current_stage=baseline
if sample_loop "$baseline_samples" yes; then
	baseline_status=0
else
	baseline_status=$?
fi
if [ "$baseline_status" -eq 1 ]; then
	printf 'status=aborted reason=%s\n' "$abort_reason"
	exit 3
fi
[ "$baseline_status" -eq 0 ] || [ "$baseline_status" -eq 10 ] ||
	fail unexpected-baseline-status

pulse_gate=pending
pulse_executed=no
stage_status=not-run
if [ "$baseline_status" -eq 10 ]; then
	trigger_attribution=not-run-preexisting-a72
	pulse_gate=blocked-preexisting-a72
	printf 'load_escalation=not-started-preexisting-a72\n'
	snapshot_observer PRE
	snapshot_kernel_alerts PRE
else
	current_stage=policy-preload-2
	print_and_require_hps_policy
	current_stage=preload-2
	preload_gate_sample=1
	while [ "$preload_gate_sample" -le 2 ]; do
		if ! sample_once; then
			printf 'status=aborted reason=%s\n' "$abort_reason"
			exit 3
		fi
		if [ "$observed_a72" = yes ]; then
			trigger_attribution=delayed-before-load-2
			pulse_gate=blocked-preexisting-a72
			break
		fi
		[ "$a72_bracket" = stable-off ] || fail preload-a72-bracket-not-stable-off-2
		preload_gate_sample=$((preload_gate_sample + 1))
	done
	snapshot_observer PRE
	snapshot_kernel_alerts PRE
	if [ "$pulse_gate" = pending ] &&
		[ "$snapshot_count" -eq 0 ] && [ "$snapshot_overwritten" -eq 0 ] &&
		[ "$alert_count" -eq 0 ]; then
		[ "$(flat_read /sys/devices/system/cpu/cpu8/online pulse-gate-cpu8)" = 0 ] ||
			fail pulse-gate-cpu8-online
		[ "$(flat_read /sys/devices/system/cpu/cpu9/online pulse-gate-cpu9)" = 0 ] ||
			fail pulse-gate-cpu9-online
		[ "$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)" = \
			"$boot_id_sha256" ] || fail pulse-gate-boot-id-changed
		pulse_gate=passed-empty-offline
		current_stage=load-2
		printf 'stage_begin=2 uptime=%s\n' "$(awk '{ print $1 }' /proc/uptime)"
		start_load 2
		pulse_executed=yes
		if sample_active_stage; then
			stage_status=0
		else
			stage_status=$?
		fi
		cleanup_load
		printf 'stage_end=2 uptime=%s status=%s\n' \
			"$(awk '{ print $1 }' /proc/uptime)" "$stage_status"
		if [ "$stage_status" -eq 1 ]; then
			printf 'status=aborted reason=%s\n' "$abort_reason"
			exit 3
		fi
		if [ "$stage_status" -eq 10 ]; then
			if [ "$first_a72_workers_alive_before" -eq 2 ] &&
				[ "$first_a72_workers_alive_after" -eq 2 ]; then
				trigger_attribution=active-full-load-2
			else
				trigger_attribution=active-partial-load-2
			fi
			printf 'load_escalation=stopped-after-a72-observation stage=2\n'
		else
			[ "$stage_status" -eq 0 ] || fail unexpected-stage-status
		fi
	else
		if [ "$pulse_gate" = pending ] && [ "$alert_count" -ne 0 ]; then
			pulse_gate=blocked-kernel-alert
		fi
		[ "$pulse_gate" != pending ] || pulse_gate=blocked-observer-not-empty
		printf 'load_escalation=not-started-observer-gate\n'
	fi
fi

run_cooldown
if [ "$observed_a72" = yes ] && [ "$trigger_attribution" = none ]; then
	trigger_attribution=delayed-during-cooldown
fi
snapshot_observer POST
snapshot_kernel_alerts POST
printf '__HPS_FIXED_SHOWS_FINAL_BEGIN__\n'
print_and_require_hps_policy
printf '__HPS_FIXED_SHOWS_FINAL_END__\n'
final_boot_id_sha256=$(sha256sum /proc/sys/kernel/random/boot_id | cut -c1-64)
[ "$final_boot_id_sha256" = "$boot_id_sha256" ] || fail boot-id-changed
run_uptime_end=$(awk '{ print $1 }' /proc/uptime) || fail uptime-end
final_online=$(flat_read /sys/devices/system/cpu/online final-online)
final_cpu8=$(flat_read /sys/devices/system/cpu/cpu8/online final-cpu8)
final_cpu9=$(flat_read /sys/devices/system/cpu/cpu9/online final-cpu9)
printf 'pulse_gate=%s\n' "$pulse_gate"
printf 'pulse_executed=%s\n' "$pulse_executed"
printf 'observed_a72=%s\n' "$observed_a72"
printf 'first_a72_stage=%s\n' "$first_a72_stage"
printf 'first_a72_uptime=%s\n' "$first_a72_uptime"
printf 'first_a72_workers_alive_before=%s\n' "$first_a72_workers_alive_before"
printf 'first_a72_workers_alive_after=%s\n' "$first_a72_workers_alive_after"
printf 'trigger_attribution=%s\n' "$trigger_attribution"
printf 'run_uptime_end=%s\n' "$run_uptime_end"
printf 'final_online=%s\n' "$final_online"
printf 'final_cpu8=%s\n' "$final_cpu8"
printf 'final_cpu9=%s\n' "$final_cpu9"
printf 'boot_id_stable=yes\n'
printf 'workers_cleaned=yes\n'
printf 'status=completed\n'
'''
    result = (prefix + derived_tail).encode("utf-8")
    forbidden = (
        "for stage in 1 2 4 8 10",
        "start_load 1",
        "start_load 4",
        "start_load 8",
        "start_load 10",
    )
    if any(token.encode() in result for token in forbidden):
        raise DerivationError("derived probe retains a forbidden load stage")
    if result.count(b"start_load 2\n") != 1:
        raise DerivationError("derived probe does not contain one exact pulse")
    return result


def read_source(path: pathlib.Path) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise DerivationError("source is missing, empty, or unsafe")
    return path.read_bytes()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise DerivationError("output already exists")
        payload = derive(read_source(args.source))
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
    except (OSError, DerivationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"source_sha256={SOURCE_SHA256}")
    print(f"derived_sha256={hashlib.sha256(payload).hexdigest()}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
