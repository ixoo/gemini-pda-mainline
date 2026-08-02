#!/usr/bin/env python3
"""Validate one bounded two-worker observer capture and classify its result."""

from __future__ import annotations

import argparse
import pathlib
import re
import stat
import sys


HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEADER = re.compile(
    r"^abi=mt6797-a72-transition-observer-v1 count=([0-9]+) overwritten=([0-9]+)$"
)
RECORD = re.compile(
    r"^seq=([0-9]+) ns=([0-9]+) tx=([0-9]+) "
    r"event=(lifecycle|da9214|spm|secure|clock|toprgu|dcm|mutation) "
    r"phase=([0-9]+) target=([0-9]+) actor=([0-9]+) "
    r"online=0x([0-9a-f]{8})(?: .+)?$"
)
EXPECTED_SCALARS = {
    "experiment": "gemian-a72-bounded-observer-two-worker-pulse",
    "kernel": "3.18.41+",
    "architecture": "aarch64",
    "root_findmnt": "/dev/mmcblk0p29",
    "root_proc_mounts": "rootfs",
    "possible": "0-9",
    "present": "0-9",
    "load_command": "yes-to-dev-null",
    "stage_workers": "0,2",
    "pulse_repetitions": "1",
    "build_identity": "#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026",
    "observer_abi": "mt6797-a72-transition-observer-v1",
    "worker_active_deadline_seconds": "3-plus-1-kill-grace",
    "sample_interval_seconds": "0.2",
    "cpu_temp_abort_millic": "50000",
    "ap_temp_abort_millic": "50000",
    "pmic_temp_abort_millic": "60000",
    "da9214_temp_abort_millic": "80000",
    "state_changing_device_writes": "none",
    "cpu_online_writes": "none",
    "policy_writes": "none",
    "partition_access": "none",
    "boot_id_stable": "yes",
    "workers_cleaned": "yes",
    "status": "completed",
}


class ValidationError(Exception):
    pass


def read_regular(path: pathlib.Path) -> str:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValidationError("capture is missing, empty, or unsafe")
    return path.read_text()


def one(values: dict[str, list[str]], key: str) -> str:
    found = values.get(key, [])
    if len(found) != 1:
        raise ValidationError(f"{key} count is {len(found)}, expected one")
    return found[0]


def observer_section(lines: list[str], label: str) -> tuple[int, int, list[dict[str, int | str]]]:
    begin_marker = f"__OBSERVER_{label}_BEGIN__"
    end_marker = f"__OBSERVER_{label}_END__"
    if lines.count(begin_marker) != 1 or lines.count(end_marker) != 1:
        raise ValidationError(f"{label} observer delimiters are absent or duplicated")
    begin = lines.index(begin_marker)
    end = lines.index(end_marker)
    if end <= begin + 1:
        raise ValidationError(f"{label} observer section is empty or reversed")
    section = lines[begin + 1 : end]
    header = HEADER.fullmatch(section[0])
    if not header:
        raise ValidationError(f"{label} observer ABI header changed")
    count, overwritten = map(int, header.groups())
    if count > 256 or len(section[1:]) != count:
        raise ValidationError(f"{label} observer count exceeds the ring or line count")
    records: list[dict[str, int | str]] = []
    previous_sequence = -1
    for line in section[1:]:
        match = RECORD.fullmatch(line)
        if not match:
            raise ValidationError(f"malformed {label} observer record: {line}")
        sequence, ns, transaction, event, phase, target, actor, online = match.groups()
        sequence_value = int(sequence)
        if sequence_value <= previous_sequence:
            raise ValidationError(f"{label} observer sequence is not strictly increasing")
        previous_sequence = sequence_value
        if int(phase) > 26 or int(target) not in (8, 9) or int(actor) > 9:
            raise ValidationError(f"{label} observer identity is out of range")
        required_payload = {
            "lifecycle": (" result=", " arg0=0x", " arg1=0x"),
            "da9214": (" status=", " valid=0x"),
            "secure": (" stable=", " sentinel_after=0x"),
            "clock": (" status=", " semaphore=0x"),
            "mutation": (" requested=0x", " after=0x", " status="),
        }.get(event, ())
        if any(token not in line for token in required_payload):
            raise ValidationError(f"{label} {event} payload is incomplete")
        records.append(
            {
                "sequence": sequence_value,
                "ns": int(ns),
                "transaction": int(transaction),
                "event": event,
                "phase": int(phase),
                "target": int(target),
                "actor": int(actor),
                "online": online,
            }
        )
    return count, overwritten, records


def text_section(lines: list[str], label: str) -> list[str]:
    begin_marker = f"__KERNEL_ALERTS_{label}_BEGIN__"
    end_marker = f"__KERNEL_ALERTS_{label}_END__"
    if lines.count(begin_marker) != 1 or lines.count(end_marker) != 1:
        raise ValidationError(f"{label} kernel-alert delimiters are absent or duplicated")
    begin = lines.index(begin_marker)
    end = lines.index(end_marker)
    if end <= begin:
        raise ValidationError(f"{label} kernel-alert section is reversed")
    alerts = lines[begin + 1 : end]
    if len(alerts) > 100 or any(not line for line in alerts):
        raise ValidationError(f"{label} kernel-alert section is malformed")
    return alerts


def parse_samples(lines: list[str]) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    required = {
        "sample",
        "uptime",
        "stage",
        "workers_requested",
        "workers_alive_before",
        "workers_alive_after",
        "online_before",
        "online_after",
        "cpu8_before",
        "cpu8_after",
        "cpu9_before",
        "cpu9_after",
        "a72_bracket",
        "cpu_temp",
        "ap_temp",
        "pmic_temp",
        "da9214_temp",
        "usb_online",
        "battery_status",
        "battery_capacity",
        "battery_health",
    }
    for line in lines:
        if not line.startswith("sample="):
            continue
        fields: dict[str, str] = {}
        for token in line.split():
            if "=" not in token:
                raise ValidationError("sample contains an unkeyed token")
            key, value = token.split("=", 1)
            if key in fields:
                raise ValidationError(f"sample duplicates {key}")
            fields[key] = value
        if set(fields) != required:
            raise ValidationError("sample field set changed")
        if int(fields["sample"]) != len(samples) + 1:
            raise ValidationError("sample indices are not contiguous")
        if fields["stage"] not in ("baseline", "preload-2", "load-2", "cooldown"):
            raise ValidationError("sample stage is outside the one-pulse contract")
        for key in ("workers_requested", "workers_alive_before", "workers_alive_after"):
            if fields[key] not in ("0", "1", "2"):
                raise ValidationError("worker count exceeds two")
        if fields["workers_requested"] not in ("0", "2"):
            raise ValidationError("requested worker count is not zero or two")
        for key in ("cpu8_before", "cpu8_after", "cpu9_before", "cpu9_after"):
            if fields[key] not in ("0", "1"):
                raise ValidationError("CPU state is malformed")
        if fields["a72_bracket"] not in ("stable-off", "stable-on", "changed"):
            raise ValidationError("A72 bracket is malformed")
        if (
            fields["usb_online"] != "1"
            or fields["battery_status"] != "Full"
            or fields["battery_capacity"] != "100"
            or fields["battery_health"] != "Good"
        ):
            raise ValidationError("sample violates the power gate")
        for key, limit in (
            ("cpu_temp", 50000),
            ("ap_temp", 50000),
            ("pmic_temp", 60000),
            ("da9214_temp", 80000),
        ):
            if not re.fullmatch(r"[0-9]+", fields[key]) or int(fields[key]) >= limit:
                raise ValidationError(f"sample violates the {key} gate")
        samples.append(fields)
    if len(samples) < 5:
        raise ValidationError("fewer than five samples were retained")
    return samples


def validate(text: str) -> dict[str, str | int]:
    lines = text.splitlines()
    pre_count, pre_overwritten, pre_records = observer_section(lines, "PRE")
    post_count, post_overwritten, post_records = observer_section(lines, "POST")
    pre_alerts = text_section(lines, "PRE")
    post_alerts = text_section(lines, "POST")
    values: dict[str, list[str]] = {}
    in_section = False
    for line in lines:
        if line in (
            "__OBSERVER_PRE_BEGIN__",
            "__OBSERVER_POST_BEGIN__",
            "__KERNEL_ALERTS_PRE_BEGIN__",
            "__KERNEL_ALERTS_POST_BEGIN__",
        ):
            in_section = True
            continue
        if line in (
            "__OBSERVER_PRE_END__",
            "__OBSERVER_POST_END__",
            "__KERNEL_ALERTS_PRE_END__",
            "__KERNEL_ALERTS_POST_END__",
        ):
            in_section = False
            continue
        if not in_section and "=" in line:
            key, value = line.split("=", 1)
            values.setdefault(key, []).append(value)
    for key, expected in EXPECTED_SCALARS.items():
        if one(values, key) != expected:
            raise ValidationError(f"{key} changed")

    boot_id = one(values, "boot_id_sha256")
    if not HEX64.fullmatch(boot_id):
        raise ValidationError("boot ID hash is malformed")
    for key in ("run_uptime_begin", "run_uptime_end"):
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", one(values, key)):
            raise ValidationError(f"{key} is malformed")
    pre_alert_count = one(values, "kernel_alert_count_PRE")
    post_alert_count = one(values, "kernel_alert_count_POST")
    if not pre_alert_count.isdigit() or not post_alert_count.isdigit():
        raise ValidationError("reported kernel-alert count is malformed")
    if int(pre_alert_count) != len(pre_alerts) or int(post_alert_count) != len(post_alerts):
        raise ValidationError("reported kernel-alert counts disagree with the sections")
    if not post_overwritten and len(post_records) >= len(pre_records):
        if post_records[: len(pre_records)] != pre_records:
            raise ValidationError("post observer does not retain the pre observer prefix")
    elif pre_records and not post_overwritten:
        raise ValidationError("post observer lost pre-existing records without overwrite")

    samples = parse_samples(lines)
    direct_cpu8 = any(
        sample[side] == "1" for sample in samples for side in ("cpu8_before", "cpu8_after")
    )
    direct_cpu9 = any(
        sample[side] == "1" for sample in samples for side in ("cpu9_before", "cpu9_after")
    )
    observed_a72 = one(values, "observed_a72")
    if observed_a72 != ("yes" if direct_cpu8 or direct_cpu9 else "no"):
        raise ValidationError("observed_a72 disagrees with direct samples")

    pulse_executed = one(values, "pulse_executed")
    pulse_gate = one(values, "pulse_gate")
    stage_begins = [line for line in lines if line.startswith("stage_begin=")]
    stage_ends = [line for line in lines if line.startswith("stage_end=")]
    load_samples = [sample for sample in samples if sample["stage"] == "load-2"]
    if pulse_executed == "yes":
        if (
            pulse_gate != "passed-empty-offline"
            or (pre_count, pre_overwritten) != (0, 0)
            or pre_alerts
        ):
            raise ValidationError("executed pulse did not pass the empty observer gate")
        if len(stage_begins) != 1 or len(stage_ends) != 1:
            raise ValidationError("executed pulse does not have one stage boundary")
        if not stage_begins[0].startswith("stage_begin=2 uptime=") or not stage_ends[0].startswith(
            "stage_end=2 uptime="
        ):
            raise ValidationError("executed pulse used a non-two-worker stage")
        if not load_samples or any(sample["workers_requested"] != "2" for sample in load_samples):
            raise ValidationError("executed pulse lacks attributable two-worker samples")
    elif pulse_executed == "no":
        if pulse_gate not in (
            "blocked-preexisting-a72",
            "blocked-observer-not-empty",
            "blocked-kernel-alert",
        ):
            raise ValidationError("skipped pulse has an invalid gate disposition")
        if stage_begins or stage_ends or load_samples:
            raise ValidationError("skipped pulse retained a load stage")
    else:
        raise ValidationError("pulse_executed is malformed")

    final_cpu8 = one(values, "final_cpu8")
    final_cpu9 = one(values, "final_cpu9")
    if final_cpu8 not in ("0", "1") or final_cpu9 not in ("0", "1"):
        raise ValidationError("final CPU state is malformed")
    final_online = one(values, "final_online")
    if final_cpu8 == final_cpu9 == "0" and final_online != "0-7":
        raise ValidationError("final online mask disagrees with offline A72 state")
    first_stage = one(values, "first_a72_stage")
    first_uptime = one(values, "first_a72_uptime")
    first_before = one(values, "first_a72_workers_alive_before")
    first_after = one(values, "first_a72_workers_alive_after")
    trigger_attribution = one(values, "trigger_attribution")
    if observed_a72 == "no":
        if (first_stage, first_uptime, first_before, first_after) != ("none", "none", "0", "0"):
            raise ValidationError("no-A72 result has a first-observation attribution")
        if trigger_attribution != "none":
            raise ValidationError("no-A72 result has a trigger attribution")
    else:
        if first_stage not in ("baseline", "preload-2", "load-2", "cooldown"):
            raise ValidationError("first A72 stage is malformed")
        if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", first_uptime):
            raise ValidationError("first A72 uptime is malformed")
        if first_before not in ("0", "1", "2") or first_after not in ("0", "1", "2"):
            raise ValidationError("first A72 worker attribution exceeds two")
        if trigger_attribution not in (
            "not-run-preexisting-a72",
            "delayed-before-load-2",
            "active-full-load-2",
            "active-partial-load-2",
            "delayed-during-cooldown",
        ):
            raise ValidationError("trigger attribution is malformed")
    pre_load_samples = [sample for sample in samples if sample["stage"] != "load-2"]
    if pulse_executed == "yes" and any(
        sample[key] != "0"
        for sample in pre_load_samples
        if sample["stage"] != "cooldown"
        for key in ("cpu8_before", "cpu8_after", "cpu9_before", "cpu9_after")
    ):
        raise ValidationError("pulse executed after a pre-load A72 observation")
    cpu9_record = any(record["target"] == 9 for record in post_records)
    disposition = "inconclusive-no-transition"
    if direct_cpu9 or cpu9_record:
        disposition = "rejected-cpu9-activity"
    elif post_alerts:
        disposition = "rejected-kernel-alert"
    elif final_cpu8 != "0" or final_cpu9 != "0":
        disposition = "rejected-final-a72-online"
    elif post_overwritten:
        disposition = "inconclusive-observer-overwritten"
    elif pulse_executed == "no":
        disposition = "no-pulse-precondition-blocked"
    elif direct_cpu8 and post_count == 0:
        disposition = "rejected-observer-empty-during-cpu8"
    elif direct_cpu8 and trigger_attribution != "active-full-load-2":
        disposition = "inconclusive-trigger-attribution"
    elif direct_cpu8:
        disposition = "cpu8-cycle-captured-review-required"
    elif post_count:
        disposition = "observer-records-without-direct-online-review-required"

    if pre_records and pulse_executed == "yes":
        raise ValidationError("pulse executed after pre-existing observer records")
    return {
        "pulse_executed": pulse_executed,
        "direct_cpu8_observed": "yes" if direct_cpu8 else "no",
        "direct_cpu9_observed": "yes" if direct_cpu9 else "no",
        "pre_observer_count": pre_count,
        "post_observer_count": post_count,
        "post_observer_overwritten": post_overwritten,
        "runtime_disposition": disposition,
        "next_action": "return-to-known-good-gemian-and-review",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = validate(read_regular(args.capture))
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=gemian-a72-bounded-observer-two-worker-pulse")
    for key, value in result.items():
        print(f"{key}={value}")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
