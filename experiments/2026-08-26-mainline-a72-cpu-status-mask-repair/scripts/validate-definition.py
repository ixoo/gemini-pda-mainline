#!/usr/bin/env python3
"""Validate the frozen prebuild CPU-status-mask repair definition."""

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
runtime_receipt = ROOT / (
    "experiments/2026-08-26-mainline-a72-platform-movement-attribution/"
    "results/runtime-attempt-1-cpu-status-unrelated-movement-20260826.txt"
)
require(sha256(runtime_receipt) ==
        contract["predecessor_runtime"]["receipt_sha256"],
        "predecessor runtime receipt")
require(contract["predecessor_runtime"]["movement_mask"] == "0x003",
        "predecessor movement mask")
require(contract["predecessor_runtime"]["a72_identity_movement"] is False,
        "no A72 identity movement")
require(contract["planned_patches"] == [
    "0382-soc-mediatek-mask-A72-CPU-status-stability.patch",
    "0383-soc-mediatek-test-A72-CPU-status-stability-mask.patch",
], "planned patches")
for name, expected in contract["canonical_patch_sha256"].items():
    require(sha256(ROOT / "patches/v7.1.3" / name) == expected,
            f"canonical patch: {name}")
require(sha256(ROOT / "patches/series") == contract["canonical_series_sha256"],
        "canonical series")
require(contract["planned_profiles"] == {
    "kunit": "a72-cpu-status-mask-kunit",
    "candidate": "a72-cpu-status-mask-candidate",
}, "planned profiles")
for name, expected in contract["profile_fragments_sha256"].items():
    require(sha256(ROOT / "configs" / name) == expected,
            f"profile fragment: {name}")
require(sha256(ROOT / "kernel/manifest.json") == contract["manifest_sha256"],
        "manifest")
manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
profiles = manifest["config"]["profiles"]
require(len(profiles) == 142, "profile count")
for kind, profile in contract["planned_profiles"].items():
    require(profile in profiles, f"manifest profile: {kind}")
for name, expected in contract["tooling_sha256"].items():
    require(expected != "pending", f"pending tooling hash: {name}")
    require(sha256(EXP / "scripts" / name) == expected, f"tooling hash: {name}")
require(contract["source_contract"] == {
    "cpu_status_mask": "GENMASK(7,6)",
    "cpu_status_words_masked": 2,
    "full_raw_words_preserved": True,
    "stable_pair_reads": 2,
    "first_read_error_reads": 1,
    "second_read_error_reads": 2,
    "third_read": False,
    "read_retry": False,
    "cci_busy_errno": -16,
    "movement_errno": -11,
    "cci_busy_precedence": True,
    "success_publishes_complete_second_sample": True,
}, "source contract")
require(contract["preserved_ceiling"] == {
    "platform_snapshot_calls": 1,
    "platform_samples": 2,
    "platform_register_observations": 26,
    "provider_calls_added": 0,
    "retained_writes_added": 0,
    "protected_clock_calls_added": 0,
    "bigidvfs_reads_added": 0,
    "secure_calls_added": 0,
    "owner_mutations": 0,
    "cpu_requests": 0,
}, "preserved ceiling")
require(contract["transport_contract"] == {
    "chunk_size": 768,
    "maximum_command_line": 820,
    "exact_payload_round_trip": True,
    "remote_temporary_file": False,
    "device_storage_write": False,
    "reboot_request": False,
}, "transport contract")
require(contract["tooling_rejected_mutations"] == 8, "tooling mutations")
require(contract["deterministic_generations"] == 2, "deterministic generations")
require(contract["profiles_checked"] == 142, "profiles checked")
require(contract["planned_kunit"] == {
    "profile": "a72-cpu-status-mask-kunit",
    "kernel_release": "7.1.3-gemini-a72-cpumask-kunit",
    "suites": 2,
    "platform_cases": 6,
    "preserved_observer_cases": 8,
    "tests": 14,
    "physical_hardware": False,
    "boot_candidate": False,
}, "planned KUnit")
require(contract["canonical_admission"] is True, "canonical admission")
require(contract["dt_change"] is False, "no DT change")
require(contract["native_vm_build"] is False, "no native build")
require(contract["device_action"] is False, "no device action")
require(contract["current_status"] ==
        "prebuild-gates-pass-ready-for-signed-buildbox-kunit-submission",
        "current status")
receipt_path = EXP / "results/prebuild-tooling-20260826.txt"
require(sha256(receipt_path) == contract["prebuild_receipt_sha256"],
        "prebuild receipt")
receipt = receipt_path.read_text(encoding="utf-8")
for token in (
    "cpu_status_mask=GENMASK(7,6)", "full_raw_words_preserved=yes",
    "third_read=none", "read_retry=none", "cci_busy_precedence=preserved",
    "tooling_rejected_mutations=8", "deterministic_generations=2",
    "transport_chunk_size=768", "transport_remote_temporary_file=none",
    "profiles_checked=142", "canonical_patch_bytes=byte-identical",
    "checkpatch_0382=0_errors:0_warnings:0_checks",
    "checkpatch_0383=0_errors:0_warnings:0_checks",
    "planned_kunit_tests=14", "native_vm_build=none", "device_action=none",
    "result=pass",
):
    require(token in receipt, f"prebuild receipt: {token}")
for token in (
    "bits 7:6", "full raw CPU-status words", "exactly two completed reads",
    "No device build or action",
):
    require(token in readme, f"README token: {token}")
for token in (
    "GENMASK(7, 6)", "No remote temporary file", "No DT change",
):
    require(token in design, f"design token: {token}")
require("/Users/" not in readme + design + receipt, "no host paths")
print("definition_validation=pass")
print("cpu_status_mask=GENMASK(7,6)")
print("complete_samples=2")
print("third_read=none")
print("canonical_patches=2")
print("profiles_checked=142")
print("planned_kunit=2_suites:14_tests")
print("transport=bounded-memory-only")
print("native_vm_build=none")
print("device_action=none")
