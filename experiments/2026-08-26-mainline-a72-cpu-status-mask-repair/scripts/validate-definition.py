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
require(contract["kunit_classifier_mutations_rejected"] == 6,
        "KUnit classifier mutations")
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
buildbox_receipt = EXP / "results/buildbox-kunit-20260826.txt"
require(sha256(buildbox_receipt) ==
        contract["buildbox_kunit"]["receipt_sha256"],
        "Buildbox KUnit receipt")
require(contract["buildbox_kunit"] == {
    "repository_commit": "7fb8f50d910185483028ebe4af254aa343c5b5ef",
    "profile": "a72-cpu-status-mask-kunit",
    "kernel_release": "7.1.3-gemini-a72-cpumask-kunit",
    "patchset_sha256":
        "fe4544a19ab1bf034ffe3b52c254c03c36ddd1449506329c39a33efee17cf69e",
    "config_sha256":
        "21baac2000c3f93d9bde5973ac457360bbb23f0d514518b5e9682d142ec0e861",
    "image_sha256":
        "cfb0b078dc24e3d6a98beb2c82be256d486189e97d8e418646dd19479a2c413a",
    "receipt_sha256":
        "3f722ee0a40f31c12fbd692a63d18454690054e10440cfc2fcb9d840e56ce660",
    "result": "pass",
}, "Buildbox KUnit result")
buildbox_text = buildbox_receipt.read_text(encoding="utf-8")
for token in (
    "repository_dirty=false", "patch_count=372", "focused_kunit_configs=2",
    "sha256sums=pass", "native_vm_build=none", "device_action=none",
    "result=pass",
):
    require(token in buildbox_text, f"Buildbox KUnit receipt: {token}")
qemu_receipt = EXP / "results/kunit-qemu-20260826.txt"
require(sha256(qemu_receipt) == contract["kunit_qemu"]["receipt_sha256"],
        "QEMU KUnit receipt")
require(contract["kunit_qemu"] == {
    "runner": "QEMU emulator version 11.0.2",
    "machine": "virt-cortex-a53-four-vcpu-no-network",
    "suites": 2,
    "tests": 14,
    "failed": 0,
    "skipped": 0,
    "emitted_suite_totals": [6, 8],
    "classifier_mutations_rejected": 6,
    "raw_log_sha256":
        "7e9ad681b72ecedcdcfef913053cc46f5525bbaa86022830e9baaec6fa6a28dd",
    "receipt_sha256":
        "24d30e2ca8cbee97a2847d9da1918e58bf675fd8c12f03bc846450a3a5cf8e94",
    "result": "pass",
}, "QEMU KUnit result")
qemu_text = qemu_receipt.read_text(encoding="utf-8")
for token in (
    "tests=14", "failed=0", "skipped=0",
    "mt6797_state_each_a72_identity_bit_test=pass",
    "emitted_suite_totals=pass:6_fail:0_skip:0_total:6,"
        "pass:8_fail:0_skip:0_total:8",
    "tap_summary=pass:14_fail:0_skip:0_total:14",
    "qemu_exit=124", "cpu_requests=0", "device_action=none",
    "boot_candidate=false",
):
    require(token in qemu_text, f"QEMU KUnit receipt: {token}")
candidate_build_receipt = EXP / "results/buildbox-candidate-20260826.txt"
require(sha256(candidate_build_receipt) ==
        contract["buildbox_candidate"]["receipt_sha256"],
        "Buildbox candidate receipt")
require(contract["buildbox_candidate"] == {
    "repository_commit": "8b087b98fcc4e2a03d82d89bee26c99818a81836",
    "profile": "a72-cpu-status-mask-candidate",
    "kernel_release": "7.1.3-gemini-a72-cpumask",
    "patchset_sha256":
        "fe4544a19ab1bf034ffe3b52c254c03c36ddd1449506329c39a33efee17cf69e",
    "config_sha256":
        "e2deb1f5495f71dbb8afd2e7ad5bee1f2af7c2a17a517aff19a9547305e6dc77",
    "image_sha256":
        "84096d9dc21e3393ee427c7550ecd19d104000fc6ba982bd4ab23bdd97a8bfd5",
    "receipt_sha256":
        "b8a807a83a2f6a69b8b8e52531bf07a291c1a64f0db668cbb7ebd88b16009201",
    "result": "pass",
}, "Buildbox candidate result")
candidate_build_text = candidate_build_receipt.read_text(encoding="utf-8")
for token in (
    "repository_dirty=false", "patch_count=372", "sha256sums=pass",
    "native_vm_build=none", "device_action=none", "result=pass",
):
    require(token in candidate_build_text, f"Buildbox candidate receipt: {token}")
candidate_receipt = EXP / "results/candidate-validation-20260826.txt"
require(sha256(candidate_receipt) == contract["candidate"]["receipt_sha256"],
        "candidate receipt")
require(contract["candidate"] == {
    "raw_sha256":
        "ebaddc69660a824de4ff0f2f59eafb9073a7b100ae3f737caf0f9b50f59cf98a",
    "raw_size": 6912000,
    "padded_sha256":
        "6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7",
    "padded_size": 16777216,
    "predecessor_sha256":
        "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78",
    "dtb_sha256":
        "90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d",
    "candidate_manifest_sha256":
        "fa59a909220097851bed92d6514b2bf3a5c3e1c336a5f7d920fe87737bbc1d08",
    "lk_gates": 32,
    "container_mutations_rejected": 6,
    "receipt_sha256":
        "10faf1da78688703c43887aebf40c44a96a95797ac1711b98865a664ed5671a7",
    "result": "pass",
}, "candidate result")
candidate_text = candidate_receipt.read_text(encoding="utf-8")
for token in (
    "dtb_vs_movement_attribution=byte-identical",
    "independent_raw_assemblies=2-byte-identical",
    "independent_padding_paths=2-byte-identical", "lk_gates=32-of-32",
    "container_mutations_rejected=6", "cpu_requests=0",
    "boot_candidate=true", "result=pass",
):
    require(token in candidate_text, f"candidate receipt: {token}")
runtime_tooling_receipt = EXP / "results/deployment-runtime-tooling-20260826.txt"
require(sha256(runtime_tooling_receipt) ==
        contract["runtime_tooling"]["receipt_sha256"],
        "runtime tooling receipt")
require(contract["runtime_tooling"] == {
    "serviceable_branches": 7,
    "source_mutations_rejected": 23,
    "identity_mutations_rejected": 2,
    "bounded_chunks": 40,
    "observed_maximum_command_line": 812,
    "required_consecutive_tcp_closures": 3,
    "remote_temporary_file": False,
    "device_storage_write": False,
    "reboot_request": False,
    "receipt_sha256":
        "96c383237d102df40f32dbc018ec014214f8616cad41f44ae89686d2f716ec20",
    "result": "pass",
}, "runtime tooling result")
runtime_tooling_text = runtime_tooling_receipt.read_text(encoding="utf-8")
for token in (
    "retargeted_serviceable_branches=7",
    "retargeted_identity_mutations_rejected=2", "bounded_chunks=40",
    "maximum_command_line=812", "remote_temporary_file=false",
    "installer_fresh_backup=none",
    "installer_success_action=shutdown-without-reboot",
    "installer_shutdown_confirmation=ssh-failure-plus-three-tcp-closures",
    "shutdown_required_consecutive_closures=3",
    "device_action=none", "result=pass",
):
    require(token in runtime_tooling_text, f"runtime tooling receipt: {token}")
deployment_receipt = EXP / "results/deployment-boot2-20260826.txt"
require(sha256(deployment_receipt) == contract["deployment"]["receipt_sha256"],
        "deployment receipt")
require(contract["deployment"] == {
    "published_tooling_commit": "6a38dc25",
    "gemian_boot_id": "6ad7a635-13b4-4aae-9e3c-1a1ceddc7bd4",
    "target": "/dev/mmcblk0p30",
    "predecessor_sha256":
        "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78",
    "candidate_sha256":
        "6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7",
    "readback_sha256":
        "6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7",
    "fresh_predecessor_backup": False,
    "retained_ram_write": False,
    "reboot_request": False,
    "shutdown_confirmed": False,
    "tcp22_open": True,
    "receipt_sha256":
        "9f490c11d78e6c818f7e89af90cb20b48301e2072b330954b5e113fbb640b559",
    "result": "write-readback-pass-shutdown-unconfirmed",
}, "deployment result")
deployment_text = deployment_receipt.read_text(encoding="utf-8")
for token in (
    "fresh_predecessor_backup=no", "retained_ram_write=none",
    "write=sync-flush-complete",
    "independent_readback_sha256=6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7",
    "reboot_request=none", "shutdown_confirmed=no",
    "shutdown_state=half-responsive", "installer_false_confirmation=proven",
    "next_action=confirm-physical-poweroff-before-boot2-selection",
    "result=write-readback-pass-shutdown-unconfirmed",
):
    require(token in deployment_text, f"deployment receipt: {token}")
require(contract["canonical_admission"] is True, "canonical admission")
require(contract["dt_change"] is False, "no DT change")
require(contract["native_vm_build"] is False, "no native build")
require(contract["device_action"] is True, "device action recorded")
require(contract["current_status"] ==
        "boot2-write-readback-pass-shutdown-unconfirmed",
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
    "all 32 LK gates pass", "makes no fresh backup",
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
print("buildbox_kunit=pass")
print("kunit_qemu=2_suites:14_tests:pass")
print("classifier_mutations_rejected=6")
print("buildbox_candidate=pass")
print("candidate=32_lk_gates:6_mutations:pass")
print("transport=bounded-memory-only")
print("deployment_runtime_tooling=pass")
print("deployment=write_readback_pass:shutdown_unconfirmed")
print("native_vm_build=none")
print("device_action=boot2-write-recorded")
