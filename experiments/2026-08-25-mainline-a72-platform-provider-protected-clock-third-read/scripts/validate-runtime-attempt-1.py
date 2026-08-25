#!/usr/bin/env python3
"""Classify the exact attempt-1 pre-clock failure and its bounded dmesg excerpt."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_PATH = SCRIPT_DIR / "validate-runtime.py"
SOURCE_SHA256 = "0ca1a9146b35c3c4a30300205b59513c7ac1a2c3fbf5433f6a687ee2260d682f"
ERROR_RECEIPT = SCRIPT_DIR.parent / "results/runtime-attempt-1-dmesg-20260825.txt"
CANDIDATE = "1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2"
RELEASE = "7.1.3-gemini-a72-clock-third"
BOOT_ID = "574bb2c4-c372-48ec-9ebb-240f04bdd68a"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(SOURCE_PATH) != SOURCE_SHA256:
    raise SystemExit("preboot runtime validator changed")
SPEC = importlib.util.spec_from_file_location("third_reader_preboot_runtime", SOURCE_PATH)
assert SPEC is not None and SPEC.loader is not None
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)
BASE = SOURCE.BASE


def classify(text: str, error_text: str) -> tuple[str, str, str, dict[str, int], str]:
    clock_action = "clock_action_request=one-balanced-gate-pair-and-bounded-cspm-snapshot"
    if text.count(clock_action) != 1:
        raise BASE.Classification("rejected-pre-clock-failure", "clock-action-request-mismatch")
    inherited_text = text.replace(clock_action, "clock_action_request=none", 1)
    result, _, ledger, counts = BASE.classify_text(inherited_text)
    if result != "serviceable-stage27-control-pass":
        raise AssertionError("base serviceability classification changed")

    values = SOURCE.scalar_values(text)
    expected = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "boot_id": BOOT_ID,
        "model": "MT6797X",
        "compatible": "planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "maxcpus8_tokens": "1",
        "udc_devices": "1",
        "block_mounts": "0",
        "pstore_files": "0",
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
        "snapshot_log_b64": "Cg==",
        "snapshot_log_lines": "0",
        "snapshot_failure_lines": "1",
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
            raise BASE.Classification("rejected-pre-clock-failure", f"{key}-mismatch")
    if base64.b64decode(values["snapshot_log_b64"], validate=True) != b"\n":
        raise BASE.Classification("rejected-pre-clock-failure", "nonempty-snapshot-log")

    required_error_tokens = (
        f"candidate_sha256={CANDIDATE}",
        f"kernel_release={RELEASE}",
        f"boot_id={BOOT_ID}",
        "platform/provider/clock capture failed: -11",
        "probe with driver mt6797-a72-platform-provider-clock-observer failed with error -11",
        "probe of a72-platform-provider-clock-observer returned 11 after 7948 usecs",
        "failure_stage=ambiguous-platform-or-provider-snapshot",
        "retained_write_attempts=0",
        "protected_clock_calls=0",
        "native_reboot_requested=no",
        "result=decision-bearing-pre-clock-failure",
    )
    for token in required_error_tokens:
        if error_text.count(token) != 1:
            raise BASE.Classification("rejected-pre-clock-failure", "error-evidence-mismatch")
    if error_text.count("capture failed:") != 1:
        raise BASE.Classification("rejected-pre-clock-failure", "non-unique-capture-error")
    return (
        "serviceable-platform-provider-clock-pre-clock-failure",
        "exact-eagain-before-clock-stage-ambiguous",
        ledger,
        counts,
        hashlib.sha256(error_text.encode()).hexdigest(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    parser.add_argument("--error-evidence", type=Path, default=ERROR_RECEIPT)
    args = parser.parse_args()
    try:
        result, reason, ledger, counts, error_sha256 = classify(
            args.capture.read_text(encoding="utf-8", errors="replace"),
            args.error_evidence.read_text(encoding="utf-8", errors="strict"),
        )
    except BASE.Classification as error:
        result, reason, ledger, counts, error_sha256 = (
            error.result, error.reason, "not-classified", {}, "not-classified"
        )
    accepted = result == "serviceable-platform-provider-clock-pre-clock-failure"
    print("runtime_gate=decision-bearing-pre-clock-failure" if accepted else "runtime_gate=rejected")
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"error_evidence_sha256={error_sha256}")
    print(f"live_ledger_classification={ledger}")
    print(f"pure_marker_matches={counts.get('pure', 0)}")
    print(f"core_marker_matches={counts.get('core', 0)}")
    print(f"refusal_marker_matches={counts.get('refusal', 0)}")
    print("stage27_serviceability=pass" if accepted else "stage27_serviceability=unknown")
    print("observer_devices=1" if accepted else "observer_devices=unknown")
    print("observer_bound=0" if accepted else "observer_bound=unknown")
    print("failure_errno=-11" if accepted else "failure_errno=unknown")
    print("failure_name=EAGAIN" if accepted else "failure_name=unknown")
    print("failure_stage=ambiguous-platform-or-provider-snapshot" if accepted else "failure_stage=unknown")
    print("retained_write_attempts=0" if accepted else "retained_write_attempts=unknown")
    print("protected_clock_calls=0" if accepted else "protected_clock_calls=unknown")
    print("clock_gate_pairs=0" if accepted else "clock_gate_pairs=unknown")
    print("cpu_requests=0")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
