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
    "dtb_sha256":
        "90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d",
    "raw_sha256":
        "fd070a56d1f247108935298ab1be61938987cab912b84fd64624e8a26a7a6d99",
    "raw_size": 6912000,
    "padded_sha256":
        "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78",
    "padded_size": 16777216,
    "manifest_sha256":
        "ace809cb0da37d977f36f9db5c0618b153103767a89cd796e1ed02d783831b48",
    "independent_assemblies": 2,
    "independent_padding_paths": 2,
    "lk_gates_passed": 32,
    "container_mutations_rejected": 6,
    "predecessor_sha256_required":
        "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb",
    "receipt_sha256":
        "0c5f3a9c26b76f617aef05d2414446ee58223d1039801fbe77cace97631ee00d",
    "boot_candidate": True,
    "device_action": False,
}, "validated candidate")
candidate_receipt = EXP / "results/candidate-validation-20260826.txt"
require(sha256(candidate_receipt) == contract["candidate"]["receipt_sha256"],
        "candidate receipt")
build_receipt = EXP / "results/buildbox-candidate-20260826.txt"
require(sha256(build_receipt) == contract["device_build"]["receipt_sha256"],
        "device build receipt")
require(contract["device_build"] == {
    "backend": "buildbox",
    "repository_commit": "1ad025c40cb6716cb5a110319b715cc03f812551",
    "profile": "a72-platform-movement-candidate",
    "kernel_release": "7.1.3-gemini-a72-movement",
    "patchset_sha256":
        "7a0467b79748619c3dff6011a17ea7040a5a50b63211f6e5d157503d1f47d81e",
    "config_sha256":
        "f0c86eeea98b478930745c5957cdff81cab05deec9710262b677936ec452736c",
    "image_sha256":
        "d1e244b4b3d757b6ee20d3ef0c2719a8f6cfc8f627b6381993ed7b702b26fb27",
    "image_gzip_sha256":
        "5413eace14655c31ef3355a769ec36986e7e458309d4fe5d374c4923b66b6814",
    "receipt_sha256":
        "d1c0a0e7dd221f5c4cbfc6ce8da900e8cf93d6e2888cd31fe777b422c88d5cc6",
    "result": "pass",
}, "device build result")
tooling_receipt = EXP / "results/deployment-runtime-tooling-20260826.txt"
require(sha256(tooling_receipt) ==
        contract["deployment_runtime_tooling"]["receipt_sha256"],
        "deployment/runtime tooling receipt")
require(contract["deployment_runtime_tooling"] == {
    "predecessor_sha256_required":
        "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb",
    "runtime_gate": "serviceable-platform-movement-decision",
    "accepted_success_branches": 4,
    "accepted_failure_branches": 3,
    "movement_mask": "nonzero-exact-nine-bit",
    "rejected_mutations": 23,
    "fresh_partition_backup": False,
    "collector_reboot": False,
    "installer_shutdown": True,
    "receipt_sha256":
        "49f5c7473f9fe7942c62ef459d9cd831826ced8c19a2039aab75d306ad331ec2",
    "result": "pass",
}, "deployment/runtime tooling")
deployment_receipt = EXP / "results/deployment-boot2-20260826.txt"
require(sha256(deployment_receipt) == contract["deployment"]["receipt_sha256"],
        "deployment receipt")
require(contract["deployment"] == {
    "deployment_tooling_commit":
        "93f31189307a7fd76c1af9e98f73133c592ad658",
    "kernel_source_commit":
        "1ad025c40cb6716cb5a110319b715cc03f812551",
    "boot_id": "5047f3a3-096e-41d1-b282-2e04f02c41de",
    "target": "/dev/mmcblk0p30",
    "active_root": "/dev/mmcblk0p29",
    "predecessor_sha256":
        "8b6bedfd7187369104250af5524a36dd2339493df95588e372d54e360d6aeabb",
    "candidate_sha256":
        "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78",
    "readback_sha256":
        "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78",
    "fresh_predecessor_backup": False,
    "retained_ram_write": False,
    "shutdown": "confirmed-unreachable",
    "independent_shutdown_check": "ssh-timeout",
    "reboot": False,
    "receipt_sha256": contract["deployment"]["receipt_sha256"],
    "result": "pass",
}, "deployment")
require(contract["dt_change"] is False, "no DT change")
require(contract["native_vm_build"] is False, "no native build")
require(contract["device_action"] is True, "device action")
require(contract["current_status"] ==
        "movement-candidate-installed-shut-down-runtime-boot-pending",
        "current status")
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
print("device_build=buildbox:pass")
print("candidate=validated:boot_candidate")
print("runtime_classifier=23_mutations_rejected")
print("native_vm_build=none")
print("deployment=write-verified-and-shut-down")
print("device_action=guarded-boot2-write")
