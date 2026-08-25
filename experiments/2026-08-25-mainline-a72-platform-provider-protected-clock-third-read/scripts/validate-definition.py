#!/usr/bin/env python3
"""Validate the frozen platform/provider/protected-clock definition."""

from __future__ import annotations

import argparse
import hashlib
import json
import zlib
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-protected-clock-third-read"
PATCHES = (
    "0374-pstore-add-Gemini-A72-platform-provider-clock-ledger.patch",
    "0375-dt-bindings-soc-mediatek-add-A72-platform-provider-clock-observer.patch",
    "0376-soc-mediatek-add-A72-platform-provider-clock-observer.patch",
    "0377-soc-mediatek-test-A72-platform-provider-clock-observer.patch",
)
HASHES = set("0123456789abcdef")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"safe regular file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path)
    args = parser.parse_args()
    root = (
        args.repository_root.resolve()
        if args.repository_root
        else Path(__file__).resolve().parents[3]
    )
    exp = root / "experiments" / EXPERIMENT
    contract = json.loads(read(exp / "contract.json"))
    readme = read(exp / "README.md")
    design = read(exp / "DESIGN.md")
    audit = read(exp / "results/prebuild-source-audit-20260825.txt")

    require(contract["schema"] == 1, "contract schema")
    require(contract["experiment"] == EXPERIMENT, "experiment identity")
    require(tuple(contract["planned_patches"]) == PATCHES, "planned patch order")
    require(contract["planned_profiles"] == {
        "kunit": "a72-platform-provider-clock-kunit",
        "candidate": "a72-platform-provider-clock-candidate",
    }, "isolated profiles")

    parent = root / contract["canonical_parent"]
    require(parent.is_file() and not parent.is_symlink(), "safe canonical parent")
    require(
        hashlib.sha256(parent.read_bytes()).hexdigest()
        == contract["canonical_parent_sha256"],
        "canonical parent hash",
    )
    for value in (
        contract["canonical_parent_sha256"],
        contract["prepared_source_state"],
        contract["prepared_source_integrity"],
        *contract["edited_parent_files"].values(),
        *contract["audited_dependencies"].values(),
    ):
        require(len(value) == 64 and set(value) <= HASHES, "lowercase SHA-256")

    require(contract["call_order"] == [
        "platform-snapshot",
        "provider-snapshot",
        "retained-before-clock",
        "protected-clock-call",
        "retained-after-clock",
    ], "exact call order")
    require(contract["dependency_gate"] == {
        "all_sources_resolved_before_capture": True,
        "platform_lookup": "of_find_device_by_node-and-device_is_bound",
        "provider_lookup": "of_find_i2c_device_by_node-and-device_is_bound",
        "provider_compatible": "dlg,da9214-legacy",
        "clock_lookup": "of_find_device_by_node-and-device_is_bound",
        "clock_compatible": "mediatek,mt6797-dvfsp-clock-backend",
        "not_ready_result": "-EPROBE_DEFER",
        "not_ready_hardware_calls": 0,
        "not_ready_retained_writes": 0,
    }, "exact dependency gate")

    records = contract["retained_records"]
    expected_records = (
        (1, "before-clock", "7a63713c"),
        (2, "after-clock", "5773d4f6"),
    )
    require(len(records) == 2, "two retained records")
    for record, (slot, checkpoint, checksum) in zip(records, expected_records):
        require(record == {
            "slot": slot,
            "checkpoint": checkpoint,
            "token": "GAPC-20260825-A",
            "crc32": checksum,
        }, f"exact retained record {slot}")
        line = (
            "GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1 "
            f"token=GAPC-20260825-A checkpoint={checkpoint} slot={slot}"
        )
        require(f"{zlib.crc32(line.encode()):08x}" == checksum,
                f"retained CRC {slot}")

    require(contract["clock_transport_ceiling"] == {
        "backend_abi": 2,
        "backend_calls": 1,
        "caller_retries": 0,
        "balanced_i2c_clock_enable_disable_pairs": 1,
        "cspm_poweron_writes": 1,
        "semaphore_request_writes_maximum": 400,
        "explicit_mmio_writes_maximum": 401,
        "fixed_payload_register_reads": 18,
        "poweron_readbacks": 1,
        "semaphore_reads_maximum": 400,
        "explicit_mmio_reads_maximum": 419,
        "acquire_poll_retries_maximum": 200,
        "release_poll_retries_maximum": 200,
        "settle_nanoseconds_after_acquire": 200,
        "secure_calls": 0,
        "fault_latches_maximum": 1,
    }, "exact protected-clock ceiling")
    require(contract["runtime_ceiling"] == {
        "platform_snapshot_calls": 1,
        "platform_samples": 2,
        "platform_register_observations": 26,
        "provider_snapshots": 1,
        "provider_samples": 2,
        "provider_i2c_reads": 10,
        "provider_i2c_writes": 0,
        "retained_write_attempts_maximum": 2,
        "protected_clock_calls": 1,
        "bigidvfs_reads": 0,
        "provider_acquires": 0,
        "provider_releases": 0,
        "publisher_calls": 0,
        "owner_mutations": 0,
        "cpu_requests": 0,
    }, "exact runtime ceiling")
    require(contract["post_call_rule"] == {
        "clock_error_is_terminal_observation": True,
        "after_checkpoint_failure_is_terminal_observation": True,
        "probe_returns_success_after_clock_call_returns": True,
        "automatic_retry_after_clock_attempt": False,
        "clock_result_logged": True,
        "all_raw_fields_logged": True,
    }, "terminal no-retry rule")
    require(contract["configuration"]["maxcpus"] == 8, "CPU8/CPU9 closed")
    for key, value in contract["configuration"].items():
        if key != "maxcpus":
            require(value is False, f"closed configuration: {key}")
    require(contract["decision_map"] == {
        "exact-live-success-and-both-records": "qualify-three-reader-composition",
        "before-clock-only": "clock-call-entered-and-did-not-return",
        "both-records-and-clock-error": "clock-call-returned-error-no-retry",
        "no-clock-record": "failure-before-clock-call",
        "serviceability-or-closure-violation": "reject-candidate",
    }, "exact decision map")

    for token in (
        "deliberately not hardware-read-only",
        "at most 401 explicit MMIO writes",
        "at most 419 explicit MMIO reads",
        "no caller retry",
        "Buildbox only",
        "A later console attachment reported the\n  same boot ID and is not counted as another attempt",
    ):
        require(token in readme, f"README boundary: {token}")
    for token in (
        "Maximum retained write attempts are two",
        "checkpoint(before-clock)",
        "probe succeeds so the platform core cannot repeat the hardware call",
        "No secure call",
        "four logical patches after canonical `0373`",
    ):
        require(token in design, f"design boundary: {token}")
    for token in (
        f"prepared_source_state={contract['prepared_source_state']}",
        f"prepared_source_integrity={contract['prepared_source_integrity']}",
        "explicit_mmio_writes_maximum=401",
        "explicit_mmio_reads_maximum=419",
        "planned_retained_write_attempts_maximum=2",
        "planned_clock_caller_retries=0",
        "planned_bigidvfs_calls=0",
        "device_action=none",
    ):
        require(token in audit, f"source audit pin: {token}")

    status = contract["current_status"]
    require(status == {
        "definition": "frozen",
        "source_audit": "pass-read-only-buildbox",
        "generation_tooling": "attempt-3-single-style-fix-pending",
        "patch_generation": "attempt-3-semantic-pass-style-rejected",
        "kernel_build": "pending",
        "boot_candidate": False,
        "device_action": "none",
    }, "current status")
    require("/Users/" not in "\n".join((readme, design, audit)), "no host path")

    print("definition_validation=pass")
    print("retained_records=2")
    print("protected_clock_calls=1")
    print("protected_clock_caller_retries=0")
    print("explicit_mmio_writes_maximum=401")
    print("explicit_mmio_reads_maximum=419")
    print("boot_candidate=false")
    print("device_action=none")


if __name__ == "__main__":
    main()
