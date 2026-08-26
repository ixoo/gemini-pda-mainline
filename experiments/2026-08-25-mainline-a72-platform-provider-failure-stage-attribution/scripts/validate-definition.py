#!/usr/bin/env python3
"""Validate the frozen failure-stage attribution definition."""

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


require(contract["schema"] == 1, "schema")
require(contract["experiment"] == EXP.name, "experiment")
parent = ROOT / contract["canonical_parent"]
require(hashlib.sha256(parent.read_bytes()).hexdigest() == contract["canonical_parent_sha256"],
        "canonical parent")
parent_source = ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-protected-clock-third-read/source"
for name, expected in contract["parent_templates"].items():
    require(hashlib.sha256((parent_source / name).read_bytes()).hexdigest() == expected,
            f"parent template: {name}")
require(contract["failure_stages"] == {
    "none": 0, "dependency": 1, "platform": 2, "provider": 3,
    "before-clock": 4,
}, "exact stages")
require(contract["canonical_patch_sha256"] == {
    "0378-soc-mediatek-report-A72-platform-provider-failure-stage.patch": "5f1c3b0a3fad2fddad6adbca475cbd48f59d5c9993ca6706b266bf3bf75259c7",
    "0379-soc-mediatek-test-A72-platform-provider-failure-stage.patch": "62864ce96b8467dbc73097019b56e08757a7d23f1c32b2a48b6307d5200fffb7",
}, "canonical patch hashes")
for name, expected in contract["canonical_patch_sha256"].items():
    require(hashlib.sha256((ROOT / "patches/v7.1.3" / name).read_bytes()).hexdigest() == expected,
            f"canonical patch: {name}")
require(hashlib.sha256((ROOT / "patches/series").read_bytes()).hexdigest()
        == contract["canonical_series_sha256"], "canonical series")
require(contract["planned_profiles"] == {
    "kunit": "a72-platform-provider-clock-stage-kunit",
    "candidate": "a72-platform-provider-clock-stage-candidate",
}, "isolated profiles")
for name, expected in contract["profile_fragments_sha256"].items():
    require(hashlib.sha256((ROOT / "configs" / name).read_bytes()).hexdigest() == expected,
            f"profile fragment: {name}")
for name, expected in contract["tooling_sha256"].items():
    require(hashlib.sha256((EXP / "scripts" / name).read_bytes()).hexdigest() == expected,
            f"tooling hash: {name}")
require(contract["tooling_rejected_mutations"] == 6, "tooling mutations")
require(contract["profiles_checked"] == 138, "profile count")
require(contract["canonical_admission"] is True, "canonical admission")
require(contract["preserved_ceiling"] == {
    "platform_snapshot_calls": 1, "provider_snapshot_calls": 1,
    "retained_write_attempts_maximum": 2, "protected_clock_calls": 1,
    "protected_clock_caller_retries": 0, "clock_gate_pairs": 1,
    "explicit_mmio_writes_maximum": 401, "explicit_mmio_reads_maximum": 419,
    "bigidvfs_reads": 0, "secure_calls": 0, "owner_mutations": 0,
    "cpu_requests": 0,
}, "preserved hardware ceiling")
require(contract["snapshot_zero_on_pre_clock_failure"] is True, "zero snapshot")
require(contract["dt_change"] is False, "no DT change")
require(contract["native_vm_build"] is False, "no native build")
require(contract["device_action"] is False, "no device action")
receipt = (EXP / "results/prebuild-tooling-20260825.txt").read_text(encoding="utf-8")
for token in (
    "generated_patch_count=2", "tooling_rejected_mutations=6",
    "profiles_checked=138", "canonical_patch_bytes=byte-identical",
    "native_vm_build=none", "device_action=none", "result=pass",
):
    require(token in receipt, f"tooling receipt: {token}")
build_receipt = (EXP / "results/buildbox-kunit-20260826.txt").read_text(encoding="utf-8")
for token in (
    "repository_commit=2e507bcbf5391a765a42ae7d90b39c0914292b77",
    "profile=a72-platform-provider-clock-stage-kunit",
    "kernel_release=7.1.3-gemini-a72-clock-stage-kunit",
    "sha256sums=pass", "native_vm_build=none", "device_action=none",
    "result=pass",
):
    require(token in build_receipt, f"Buildbox receipt: {token}")
qemu_receipt = (EXP / "results/kunit-qemu-20260826.txt").read_text(encoding="utf-8")
for token in (
    "machine=virt-cortex-a53-four-vcpu-no-network", "tests=8",
    "failed=0", "skipped=0", "mt6797_a72_ppc_platform_failure_test=pass",
    "mt6797_a72_ppc_provider_failure_test=pass",
    "mt6797_a72_ppc_before_failure_test=pass", "mmio=false",
    "retained_ram=false", "cpu_requests=0", "boot_candidate=false",
    "result=pass",
):
    require(token in qemu_receipt, f"QEMU receipt: {token}")
candidate_receipt = (EXP / "results/offline-candidate-validation-20260826.txt").read_text(encoding="utf-8")
for token in (
    "repository_commit=53398b8a4689e6a4150ec450e5c1e8a5ce37c6bc",
    "profile=a72-platform-provider-clock-stage-candidate",
    "kernel_release=7.1.3-gemini-a72-clock-stage",
    "candidate_dtb_vs_retired_third_reader=byte-identical",
    "boot2_padded_sha256=8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb",
    "independent_candidate_assemblies=byte-identical",
    "lk_gates=32-of-32", "container_negative_mutations_rejected=6",
    "cpu_requests=0", "native_vm_build=none", "device_access=none",
    "hardware_write=none", "result=pass",
):
    require(token in candidate_receipt, f"candidate receipt: {token}")
for token in (
    "The exact prior image is retired", "out-of-band failure-stage result",
    "changes no supplier lookup", "same DT", "Buildbox compile",
):
    require(token in readme, f"README token: {token}")
for token in ("all-zero snapshot", "protected-clock call returns", "No new loop"):
    require(token in design, f"design token: {token}")
require("/Users/" not in readme + design, "no host paths")
print("definition_validation=pass")
print("failure_stages=5")
print("protected_clock_calls=1")
print("caller_retries=0")
print("canonical_patches=2")
print("profiles_checked=138")
print("buildbox_kunit=pass")
print("kunit_qemu=pass:8_fail:0_skip:0_total:8")
print("device_build=buildbox-pass")
print("offline_candidate=pass:32_lk_gates:6_mutations")
print("device_action=none")
