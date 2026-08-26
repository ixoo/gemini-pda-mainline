#!/usr/bin/env python3
"""Validate the frozen prebuild platform-movement experiment definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXP = Path(__file__).resolve().parent.parent
ROOT = EXP.parents[1]
contract = json.loads((EXP / "contract.json").read_text(encoding="utf-8"))
readme = (EXP / "README.md").read_text(encoding="utf-8")
design = (EXP / "DESIGN.md").read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


require(contract["schema"] == 1, "schema")
require(contract["experiment"] == EXP.name, "experiment")
require(sha256(ROOT / contract["canonical_parent"]) ==
        contract["canonical_parent_sha256"], "canonical parent")
require(contract["parent_series_sha256"] ==
        "69c04deafdb551f64bfae00134c117094b99064ff0dbb98c51f5f25737189020",
        "post-0379 parent series")
require(contract["planned_patches"] == [
    "0380-soc-mediatek-report-A72-platform-state-movement.patch",
    "0381-soc-mediatek-test-A72-platform-state-movement.patch",
], "planned patch inventory")
for name, expected in contract["canonical_patch_sha256"].items():
    require(sha256(ROOT / "patches/v7.1.3" / name) == expected,
            f"canonical patch: {name}")
require(sha256(ROOT / "patches/series") == contract["canonical_series_sha256"],
        "canonical series")
require(contract["planned_profiles"] == {
    "kunit": "a72-platform-movement-kunit",
    "candidate": "a72-platform-movement-candidate",
}, "isolated profiles")
for name, expected in contract["profile_fragments_sha256"].items():
    require(sha256(ROOT / "configs" / name) == expected,
            f"profile fragment: {name}")
require(sha256(ROOT / "kernel/manifest.json") == contract["manifest_sha256"],
        "manifest")
for name, expected in contract["tooling_sha256"].items():
    require(expected != "pending", f"pending tooling hash: {name}")
    require(sha256(EXP / "scripts" / name) == expected, f"tooling hash: {name}")
require(contract["tooling_rejected_mutations"] == 8, "tooling mutations")
require(contract["kunit_classifier_mutations_rejected"] == 6,
        "classifier mutations")
require(contract["profiles_checked"] == 140, "profile count")
require(contract["canonical_admission"] is True, "canonical admission")
require(contract["movement_bits"] == {
    "spm_cpu_pwr_status": 0,
    "spm_cpu_pwr_status_2nd": 1,
    "spm_mp2_cpusys_pwr_con": 2,
    "spm_mp2_cpu0_pwr_con": 3,
    "spm_mp2_cpu1_pwr_con": 4,
    "spm_cpu_ext_buck_iso": 5,
    "mp2_sync_dcm_masked": 6,
    "cci_mp2_port_request_masked": 7,
    "pwrap_reset_asserted": 8,
}, "movement bit map")
require(contract["transaction_contract"] == {
    "stable_pair_reads": 2,
    "first_read_error_reads": 1,
    "second_read_error_reads": 2,
    "third_read": False,
    "read_retry": False,
    "cci_busy_errno": -16,
    "movement_errno": -11,
    "cci_busy_precedence": True,
    "stable_snapshot_zero_on_failure": True,
    "failure_detail_zero_on_read_error": True,
    "failure_detail_complete_pair_on_busy_or_movement": True,
    "stable_success_publishes_second_sample": True,
}, "transaction contract")
require(contract["preserved_ceiling"] == {
    "platform_snapshot_calls": 1,
    "platform_samples": 2,
    "platform_register_observations": 26,
    "provider_snapshot_calls": 1,
    "retained_write_attempts_maximum": 2,
    "protected_clock_calls": 1,
    "protected_clock_caller_retries": 0,
    "clock_gate_pairs": 1,
    "explicit_mmio_writes_maximum": 401,
    "explicit_mmio_reads_maximum": 419,
    "bigidvfs_reads": 0,
    "secure_calls": 0,
    "owner_mutations": 0,
    "cpu_requests": 0,
}, "preserved hardware ceiling")
runtime_receipt = ROOT / (
    "experiments/2026-08-25-mainline-a72-platform-provider-failure-stage-attribution/"
    "results/runtime-attempt-1-platform-eagain-20260826.txt"
)
require(sha256(runtime_receipt) ==
        contract["predecessor_runtime"]["runtime_receipt_sha256"],
        "predecessor runtime receipt")
require(contract["planned_kunit"] == {
    "profile": "a72-platform-movement-kunit",
    "kernel_release": "7.1.3-gemini-a72-movement-kunit",
    "suites": 2,
    "tests": 13,
    "physical_hardware": False,
    "boot_candidate": False,
}, "planned KUnit")
buildbox_receipt = EXP / "results/buildbox-kunit-20260826.txt"
require(sha256(buildbox_receipt) ==
        contract["buildbox_kunit"]["receipt_sha256"],
        "Buildbox KUnit receipt")
require(contract["buildbox_kunit"] == {
    "repository_commit": "d2caf9df3962845a85cfb6983c957ec044f135c4",
    "profile": "a72-platform-movement-kunit",
    "kernel_release": "7.1.3-gemini-a72-movement-kunit",
    "patchset_sha256":
        "7a0467b79748619c3dff6011a17ea7040a5a50b63211f6e5d157503d1f47d81e",
    "config_sha256":
        "2b9ba71e0aaa9bebbea60c1f942a19fb78ed6848412a29241bc6f5e55a29662c",
    "image_sha256":
        "cf87036183923096e324f080f13b130ebc5473446668026b386d6315a08c3044",
    "receipt_sha256":
        "a27f6cee90836475eaaece09092703cbe926fbe0f99718d13699e5c0f0d5d5ec",
    "result": "pass",
}, "Buildbox KUnit result")
qemu_receipt = EXP / "results/kunit-qemu-20260826.txt"
require(sha256(qemu_receipt) == contract["kunit_qemu"]["receipt_sha256"],
        "QEMU KUnit receipt")
require(contract["kunit_qemu"] == {
    "runner": "QEMU emulator version 11.0.2",
    "machine": "virt-cortex-a53-four-vcpu-no-network",
    "suites": 2,
    "tests": 13,
    "failed": 0,
    "skipped": 0,
    "emitted_suite_totals": [5, 8],
    "initial_classifier_rejection":
        "tool-expected-nonexistent-combined-total",
    "kernel_test_failure": False,
    "classifier_mutations_rejected": 6,
    "raw_log_sha256":
        "ad1de15b8e5dd8fdcca177f913b2cca21a947719649f7ce2d9e80286698607e2",
    "receipt_sha256":
        "1dba8019382cf87188cc759d4fe044dd40cc0c0a7ab58f34baa533aa28a2d8d0",
    "result": "pass",
}, "QEMU KUnit result")
require(contract["candidate"] == {
    "profile": "a72-platform-movement-candidate",
    "kernel_release": "7.1.3-gemini-a72-movement",
    "same_dt_required": True,
    "maxcpus": 8,
    "boot_candidate": False,
    "device_action": False,
}, "planned candidate")
require(contract["dt_change"] is False, "no DT change")
require(contract["native_vm_build"] is False, "no native build")
require(contract["device_action"] is False, "no device action")
require(contract["current_status"] ==
        "buildbox-kunit-and-qemu-pass-device-build-pending", "current status")
receipt = (EXP / "results/prebuild-tooling-20260826.txt").read_text(encoding="utf-8")
for token in (
    "generated_patch_count=2", "movement_bits=9", "third_read=none",
    "read_retry=none", "cci_busy_precedence=preserved",
    "tooling_rejected_mutations=8", "kunit_classifier_mutations_rejected=6",
    "profiles_checked=140", "canonical_patch_bytes=byte-identical",
    "checkpatch_0380=0_errors:0_warnings:0_checks",
    "checkpatch_0381=0_errors:0_warnings:0_checks",
    "planned_kunit_tests=13", "native_vm_build=none", "device_action=none",
    "result=pass",
):
    require(token in receipt, f"prebuild receipt: {token}")
for token in (
    "Which existing platform-state comparison moved", "nine-bit mask",
    "adds no register read or write", "Buildbox",
):
    require(token in readme, f"README token: {token}")
for token in (
    "Preserve `mt6797_a72_platform_state_snapshot()`",
    "CCI change-pending in either completed sample returns `-EBUSY`",
    "stable pair returns zero", "does not stabilize the sample",
):
    require(token in design, f"design token: {token}")
require("/Users/" not in readme + design + receipt, "no host paths")
print("definition_validation=pass")
print("movement_bits=9")
print("stable_pair_reads=2")
print("first_read_error_reads=1")
print("third_read=none")
print("caller_retries=0")
print("canonical_patches=2")
print("profiles_checked=140")
print("planned_kunit=2_suites:13_tests")
print("buildbox_kunit=pass")
print("kunit_qemu=2_suites:13_tests:pass")
print("classifier_correction=per-suite-totals")
print("native_vm_build=none")
print("device_action=none")
