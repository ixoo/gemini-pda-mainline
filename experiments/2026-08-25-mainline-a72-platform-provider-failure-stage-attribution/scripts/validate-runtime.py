#!/usr/bin/env python3
"""Classify the exact failure-stage platform/provider/clock live capture."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
from pathlib import Path
import re
from typing import NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_PATH = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-protected-clock-third-read/scripts/validate-runtime.py"
SOURCE_SHA256 = "0ca1a9146b35c3c4a30300205b59513c7ac1a2c3fbf5433f6a687ee2260d682f"
CANDIDATE = "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb"
RELEASE = "7.1.3-gemini-a72-clock-stage"
FAILURE_PREFIX = "platform/provider/clock capture failed:"
FAILURE = re.compile(
    r"platform/provider/clock capture failed: "
    r"stage=(platform|provider|before-clock) ret=(-?[0-9]+)"
)


class Decision(NamedTuple):
    classification: str
    reason: str
    ledger: str
    counts: dict[str, int]
    snapshot_sha256: str
    clock_state: tuple[int, int, int, int, int, int]
    failure_stage: str
    failure_errno: int
    retained_write_attempts: int
    failure_sha256: str


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(SOURCE_PATH) != SOURCE_SHA256:
    raise SystemExit("source runtime validator changed")
SPEC = importlib.util.spec_from_file_location("clock_stage_runtime_source", SOURCE_PATH)
assert SPEC is not None and SPEC.loader is not None
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)
BASE = SOURCE.BASE
SOURCE.CANDIDATE = CANDIDATE
SOURCE.RELEASE = RELEASE
BASE.CANDIDATE = CANDIDATE
BASE.RELEASE = RELEASE


def decode_log(values: dict[str, str], key: str, reason: str) -> bytes:
    try:
        raw = base64.b64decode(values.get(key, ""), validate=True)
        raw.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise BASE.Classification("rejected-clock-stage", reason) from error
    return raw


def classify(text: str) -> Decision:
    clock_action = "clock_action_request=one-balanced-gate-pair-and-bounded-cspm-snapshot"
    if text.count(clock_action) != 1:
        raise BASE.Classification("rejected-clock-stage", "clock-action-request-mismatch")
    values = SOURCE.scalar_values(text)
    raw_failure = decode_log(values, "failure_log_b64", "failure-log-malformed")
    failure_lines = values.get("failure_log_lines")
    snapshot_failure_lines = values.get("snapshot_failure_lines")

    if snapshot_failure_lines == "0":
        if failure_lines != "0" or raw_failure != b"\n":
            raise BASE.Classification("rejected-clock-stage", "unexpected-failure-log")
        result, reason, ledger, counts, snapshot_sha256, state = SOURCE.classify(text)
        return Decision(
            result, reason, ledger, counts, snapshot_sha256, state,
            "none", 0, 2, hashlib.sha256(raw_failure).hexdigest(),
        )

    if snapshot_failure_lines != "1" or failure_lines != "1":
        raise BASE.Classification("rejected-clock-stage", "failure-count-mismatch")
    inherited_text = text.replace(clock_action, "clock_action_request=none", 1)
    result, _, ledger, counts = BASE.classify_text(inherited_text)
    if result != "serviceable-stage27-control-pass":
        raise AssertionError("base serviceability classification changed")
    expected = {
        "platform_state_devices": "1",
        "platform_state_bound": "1",
        "clock_backend_devices": "1",
        "clock_backend_bound": "1",
        "bigidvfs_backend_devices": "1",
        "bigidvfs_backend_bound": "1",
        "composed_observer_devices": "1",
        "composed_observer_bound": "0",
        "provider_only_observer_devices": "0",
        "platform_only_observer_devices": "0",
        "physical_observer_devices": "0",
        "provider_i2c_devices": "1",
        "provider_i2c_bound": "1",
        "usb_controller_status": "okay",
        "tphy_status": "okay",
        "i2c5_status": "okay",
        "keyboard_status": "okay",
        "snapshot_log_lines": "0",
        "platform_snapshot_request": "boot-observer-one-shot",
        "platform_snapshot_calls_expected": "1",
        "platform_samples_expected": "2",
        "platform_register_observations_expected": "26",
        "provider_readiness_request": "explicit-phandle-bound-device",
        "provider_snapshot_request": "one-stable-read-only",
        "provider_snapshots_expected": "1",
        "provider_samples_expected": "2",
        "provider_i2c_reads_expected": "10",
        "provider_i2c_writes_expected": "0",
        "clock_backend_read_request": "one-handoff-owned-snapshot",
        "protected_clock_calls_expected": "1",
        "protected_clock_abi_expected": "2",
        "protected_clock_generation_expected": "1",
        "clock_gate_pairs_expected": "1",
        "explicit_mmio_writes_maximum": "401",
        "explicit_mmio_reads_maximum": "419",
        "bigidvfs_backend_read_request": "none",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "regulator_action_request": "none",
        "clock_action_request": "one-balanced-gate-pair-and-bounded-cspm-snapshot",
        "secure_call_request": "none",
        "provider_acquire_release_request": "none",
        "observer_registration_request": "dt-probe-only",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise BASE.Classification("rejected-clock-stage", f"{key}-mismatch")
    raw_snapshot = decode_log(values, "snapshot_log_b64", "snapshot-log-malformed")
    if raw_snapshot != b"\n":
        raise BASE.Classification("rejected-clock-stage", "nonzero-pre-clock-snapshot")
    failure_text = raw_failure.decode("utf-8")
    lines = failure_text.splitlines()
    if len(lines) != 1 or FAILURE_PREFIX not in lines[0]:
        raise BASE.Classification("rejected-clock-stage", "failure-log-contract-mismatch")
    attributed = lines[0][lines[0].index(FAILURE_PREFIX):].strip()
    match = FAILURE.fullmatch(attributed)
    if not match:
        raise BASE.Classification("rejected-clock-stage", "failure-stage-contract-mismatch")
    stage, errno_text = match.groups()
    failure_errno = int(errno_text)
    if failure_errno != -11:
        raise BASE.Classification("rejected-clock-stage", "failure-errno-mismatch")
    retained_write_attempts = 1 if stage == "before-clock" else 0
    return Decision(
        f"serviceable-platform-provider-clock-stage-{stage}-eagain",
        f"exact-pre-clock-{stage}-eagain",
        ledger,
        counts,
        hashlib.sha256(raw_snapshot).hexdigest(),
        (0, 0, 0, 0, 0, 0),
        stage,
        failure_errno,
        retained_write_attempts,
        hashlib.sha256(raw_failure).hexdigest(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        decision = classify(args.capture.read_text(encoding="utf-8", errors="replace"))
    except BASE.Classification as error:
        decision = Decision(
            error.result, error.reason, "not-classified", {}, "not-classified",
            (0, 0, 0, 0, 0, 0), "unknown", 0, 0, "not-classified",
        )
    accepted = decision.classification.startswith("serviceable-platform-provider-clock-")
    valid, returned, after, clock_ret, clock_abi, clock_generation = decision.clock_state
    failure = decision.failure_stage != "none"
    print("runtime_gate=serviceable-platform-provider-clock-stage-decision" if accepted else "runtime_gate=rejected")
    print(f"runtime_classification={decision.classification}")
    print(f"runtime_reason={decision.reason}")
    print(f"snapshot_log_sha256={decision.snapshot_sha256}")
    print(f"failure_log_sha256={decision.failure_sha256}")
    print(f"failure_stage={decision.failure_stage}")
    print(f"failure_errno={decision.failure_errno}")
    print(f"live_ledger_classification={decision.ledger}")
    print(f"pure_marker_matches={decision.counts.get('pure', 0)}")
    print(f"core_marker_matches={decision.counts.get('core', 0)}")
    print(f"refusal_marker_matches={decision.counts.get('refusal', 0)}")
    print("provider_ready_gate=passed" if accepted else "provider_ready_gate=unknown")
    print("clock_ready_gate=not-reached" if failure else ("clock_ready_gate=passed" if accepted else "clock_ready_gate=unknown"))
    print(f"snapshot_valid={valid}")
    print(f"clock_returned={returned}")
    print(f"after_checkpoint={after}")
    print("platform_snapshot_calls=1" if accepted else "platform_snapshot_calls=unknown")
    print("platform_samples=unknown" if failure else ("platform_samples=2" if accepted else "platform_samples=unknown"))
    print("platform_register_observations=unknown" if failure else ("platform_register_observations=26" if accepted else "platform_register_observations=unknown"))
    if failure:
        provider_calls = 0 if decision.failure_stage == "platform" else 1
        print(f"provider_snapshots={provider_calls}")
        print("provider_samples=unknown")
        print("provider_i2c_reads=unknown")
    else:
        print("provider_snapshots=1" if accepted else "provider_snapshots=unknown")
        print("provider_samples=2" if accepted else "provider_samples=unknown")
        print("provider_i2c_reads=10" if accepted else "provider_i2c_reads=unknown")
    print("provider_i2c_writes=0")
    print(f"retained_write_attempts={decision.retained_write_attempts if accepted else 'unknown'}")
    print("protected_clock_calls=0" if failure else ("protected_clock_calls=1" if accepted else "protected_clock_calls=unknown"))
    print(f"protected_clock_ret={'not-called' if failure else clock_ret}")
    print(f"protected_clock_abi={'not-called' if failure else clock_abi}")
    print(f"protected_clock_generation={'not-called' if failure else clock_generation}")
    print("clock_gate_pairs=0" if failure else ("clock_gate_pairs=1" if accepted else "clock_gate_pairs=unknown"))
    print("explicit_mmio_writes_maximum=401")
    print("explicit_mmio_reads_maximum=419")
    print("bigidvfs_reads=0")
    print("secure_calls=0")
    print("provider_acquires=0")
    print("provider_releases=0")
    print("publisher_calls=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
