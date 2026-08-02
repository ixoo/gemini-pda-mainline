#!/usr/bin/env python3
"""Exercise two-worker derivation, classification, and fail-closed invariants."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
SOURCE = ROOT.parent / "2026-07-23-gemian-a72-load-assisted-observation" / "scripts" / "remote-load-probe.sh"


def load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


deriver = load("pulse_deriver", SCRIPTS / "derive-two-worker-pulse.py")
validator = load("pulse_validator", SCRIPTS / "validate-pulse.py")


def record(sequence: int = 1, target: int = 8, phase: int = 1) -> str:
    return (
        f"seq={sequence} ns={100 + sequence} tx=1 event=lifecycle phase={phase} "
        f"target={target} actor=0 online=0x000000ff result=0 arg0=0x0 arg1=0x0"
    )


def sample(index: int, stage: str, workers: int, cpu8: int = 0, cpu9: int = 0) -> str:
    bracket = "stable-on" if cpu8 or cpu9 else "stable-off"
    return (
        f"sample={index} uptime={100 + index / 10:.1f} stage={stage} "
        f"workers_requested={workers} workers_alive_before={workers} "
        f"workers_alive_after={workers} online_before=0-7 online_after=0-7 "
        f"cpu8_before={cpu8} cpu8_after={cpu8} cpu9_before={cpu9} "
        f"cpu9_after={cpu9} a72_bracket={bracket} cpu_temp=35000 ap_temp=28000 "
        "pmic_temp=27000 da9214_temp=60000 usb_online=1 battery_status=Full "
        "battery_capacity=100 battery_health=Good"
    )


def capture(
    *,
    post_records: list[str],
    pre_records: list[str] | None = None,
    overwritten: int = 0,
    executed: bool = True,
    cpu8: bool = False,
    cpu9: bool = False,
    final_cpu8: int = 0,
    final_cpu9: int = 0,
    post_alerts: list[str] | None = None,
) -> str:
    pre_records = pre_records or []
    post_alerts = post_alerts or []
    lines = [
        "experiment=gemian-a72-bounded-observer-two-worker-pulse",
        "kernel=3.18.41+",
        "architecture=aarch64",
        "root_findmnt=/dev/mmcblk0p29",
        "root_proc_mounts=rootfs",
        "possible=0-9",
        "present=0-9",
        "boot_id_sha256=" + "a" * 64,
        "load_command=yes-to-dev-null",
        "stage_workers=0,2",
        "pulse_repetitions=1",
        "build_identity=#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026",
        "observer_abi=mt6797-a72-transition-observer-v1",
        "worker_active_deadline_seconds=3-plus-1-kill-grace",
        "sample_interval_seconds=0.2",
        "cpu_temp_abort_millic=50000",
        "ap_temp_abort_millic=50000",
        "pmic_temp_abort_millic=60000",
        "da9214_temp_abort_millic=80000",
        "state_changing_device_writes=none",
        "cpu_online_writes=none",
        "policy_writes=none",
        "partition_access=none",
        "run_uptime_begin=100.0",
    ]
    for index in range(1, 6):
        lines.append(sample(index, "baseline", 0))
    lines.extend(
        [
            "__OBSERVER_PRE_BEGIN__",
            f"abi=mt6797-a72-transition-observer-v1 count={len(pre_records)} overwritten=0",
            *pre_records,
            "__OBSERVER_PRE_END__",
            "__KERNEL_ALERTS_PRE_BEGIN__",
            "__KERNEL_ALERTS_PRE_END__",
            "kernel_alert_count_PRE=0",
        ]
    )
    if executed:
        lines.append("stage_begin=2 uptime=101.0")
        lines.append(sample(6, "load-2", 2, int(cpu8), int(cpu9)))
        lines.append("stage_end=2 uptime=102.0 status=10" if cpu8 or cpu9 else "stage_end=2 uptime=104.0 status=0")
    lines.append(sample(7 if executed else 6, "cooldown", 0))
    lines.extend(
        [
            "__OBSERVER_POST_BEGIN__",
            f"abi=mt6797-a72-transition-observer-v1 count={len(post_records)} overwritten={overwritten}",
            *post_records,
            "__OBSERVER_POST_END__",
            "__KERNEL_ALERTS_POST_BEGIN__",
            *post_alerts,
            "__KERNEL_ALERTS_POST_END__",
            f"kernel_alert_count_POST={len(post_alerts)}",
            "pulse_gate=passed-empty-offline" if executed else "pulse_gate=blocked-observer-not-empty",
            "pulse_executed=yes" if executed else "pulse_executed=no",
            "observed_a72=yes" if cpu8 or cpu9 else "observed_a72=no",
            "first_a72_stage=load-2" if cpu8 or cpu9 else "first_a72_stage=none",
            "first_a72_uptime=101.1" if cpu8 or cpu9 else "first_a72_uptime=none",
            "first_a72_workers_alive_before=2" if cpu8 or cpu9 else "first_a72_workers_alive_before=0",
            "first_a72_workers_alive_after=2" if cpu8 or cpu9 else "first_a72_workers_alive_after=0",
            "trigger_attribution=active-full-load-2" if cpu8 or cpu9 else "trigger_attribution=none",
            "run_uptime_end=117.0",
            "final_online=0-7",
            f"final_cpu8={final_cpu8}",
            f"final_cpu9={final_cpu9}",
            "boot_id_stable=yes",
            "workers_cleaned=yes",
            "status=completed",
        ]
    )
    return "\n".join(lines) + "\n"


def reject(label: str, text: str) -> None:
    try:
        validator.validate(text)
    except validator.ValidationError:
        return
    raise AssertionError(f"{label} mutation was accepted")


def replace_once(text: str, old: str, new: str) -> str:
    assert text.count(old) == 1, old
    return text.replace(old, new, 1)


def main() -> int:
    derived = deriver.derive(SOURCE.read_bytes()).decode()
    assert derived.count("start_load 2\n") == 1
    for forbidden in (
        "for stage in 1 2 4 8 10",
        "start_load 1",
        "start_load 4",
        "start_load 8",
        "start_load 10",
        "/sys/devices/system/cpu/cpu8/online >",
        "/sys/devices/system/cpu/cpu9/online >",
        "i2cset",
        "devmem",
        "reboot",
        "poweroff",
    ):
        assert forbidden not in derived
    for required in (
        "GEMINI_EXPECTED_BOOT_ID_SHA256",
        "pulse_gate=passed-empty-offline",
        "__OBSERVER_%s_BEGIN__",
        "snapshot_observer PRE",
        "snapshot_observer POST",
        "#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026",
    ):
        assert required in derived

    cpu8_capture = capture(post_records=[record()], cpu8=True)
    assert validator.validate(cpu8_capture)["runtime_disposition"] == (
        "cpu8-cycle-captured-review-required"
    )
    assert validator.validate(capture(post_records=[]))["runtime_disposition"] == (
        "inconclusive-no-transition"
    )
    assert validator.validate(capture(post_records=[record(target=9)]))["runtime_disposition"] == (
        "rejected-cpu9-activity"
    )
    assert validator.validate(capture(post_records=[record()], overwritten=1))[
        "runtime_disposition"
    ] == "inconclusive-observer-overwritten"
    assert validator.validate(capture(post_records=[], final_cpu8=1))[
        "runtime_disposition"
    ] == "rejected-final-a72-online"
    assert validator.validate(
        capture(post_records=[], post_alerts=["[  101.2] WARNING: observer test"])
    )["runtime_disposition"] == "rejected-kernel-alert"
    skipped = capture(post_records=[record()], pre_records=[record()], executed=False)
    assert validator.validate(skipped)["runtime_disposition"] == "no-pulse-precondition-blocked"

    reject("four-worker request", replace_once(cpu8_capture, "workers_requested=2", "workers_requested=4"))
    reject("build identity", replace_once(cpu8_capture, "Sun Aug 2", "Sat Aug 1"))
    reject("missing pre delimiter", replace_once(cpu8_capture, "__OBSERVER_PRE_BEGIN__\n", ""))
    reject("power drift", cpu8_capture.replace("usb_online=1", "usb_online=0", 1))
    reject(
        "temperature limit",
        cpu8_capture.replace("cpu_temp=35000", "cpu_temp=50000", 1),
    )
    reject("incomplete status", replace_once(cpu8_capture, "status=completed", "status=aborted"))
    reject(
        "kernel alert count",
        replace_once(cpu8_capture, "kernel_alert_count_POST=0", "kernel_alert_count_POST=1"),
    )
    reject("pulse with pre-record", capture(post_records=[record()], pre_records=[record()], cpu8=True))
    no_load_sample = "\n".join(
        line for line in cpu8_capture.splitlines() if " stage=load-2 " not in line
    ) + "\n"
    reject("pulse without load sample", no_load_sample)
    unordered = capture(post_records=[record(2), record(1, phase=2)], cpu8=True)
    reject("observer sequence order", unordered)

    collector = (SCRIPTS / "collect-pulse.sh").read_text()
    for required in (
        "initial_disposition=empty-offline",
        "eligible-for-separate-second-prepulse-gate",
        "GEMINI_EXPECTED_BOOT_ID_SHA256=$boot_id_sha256",
        deriver.SOURCE_SHA256,
        "derived two-worker probe identity changed",
    ):
        assert required in collector
    pins = dict(re.findall(r"^readonly ([A-Z_]+_SHA256)=([0-9a-f]{64})$", collector, re.M))
    assert pins["SOURCE_SHA256"] == deriver.SOURCE_SHA256
    assert pins["DERIVER_SHA256"] == hashlib.sha256(
        (SCRIPTS / "derive-two-worker-pulse.py").read_bytes()
    ).hexdigest()
    assert pins["DERIVED_SHA256"] == hashlib.sha256(derived.encode()).hexdigest()
    assert pins["PULSE_VALIDATOR_SHA256"] == hashlib.sha256(
        (SCRIPTS / "validate-pulse.py").read_bytes()
    ).hexdigest()

    print("PASS: two-worker derivation, 7 classifications, and 10 fail-closed checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
