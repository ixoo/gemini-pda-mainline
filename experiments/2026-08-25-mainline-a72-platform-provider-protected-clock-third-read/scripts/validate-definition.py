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
    candidate_build_receipt = read(
        exp / "results/buildbox-candidate-compile-20260825.txt"
    )
    dtb_receipt = read(exp / "results/offline-dtb-validation-20260825.txt")
    candidate_receipt = read(
        exp / "results/offline-candidate-validation-20260825.txt"
    )
    deployment_receipt = read(exp / "results/deployment-boot2-20260825.txt")
    runtime_tooling_receipt = read(
        exp / "results/preboot-runtime-tooling-20260825.txt"
    )

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
        contract["generator_parent_source_state"],
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

    candidate_build = contract["candidate_build"]
    require(candidate_build == {
        "backend": "buildbox",
        "repository_commit": "5e4b0d584f76d4bf5a5e7e924b886d6b65ed4bd5",
        "job": "5e4b0d584f76d4bf5a5e7e924b886d6b65ed4bd5-a72-platform-provider-clock-candidate-m0",
        "artifact": "linux-7.1.3-gemini-a72-platform-provider-clock-candidate-30a9d055-622e6240",
        "kernel_release": "7.1.3-gemini-a72-clock-third",
        "patchset_sha256": "30a9d0551a20c76f5abd756a3611ddee4c03e0105fd429d9f3a3a2136520f4ba",
        "config_sha256": "2facfaaec397287267701d3cc74a3362418f34b793a96dbcd88920e730f63755",
        "image_sha256": "845fbcaf68e847d18f5f4e4dce2981f93b5d1106cf396308515e5372d0ba9c62",
        "image_gzip_sha256": "c3a7a0f583c925c93537463d84c7fb0a04bb715c232a2595e920f8504d79c4ad",
        "system_map_sha256": "1ae62d5eaf09ac4d990cb4e81cce6101721ea332aa182821b266667729701d02",
        "package_manifest_sha256": "fc28c627cacc5c234937d85d8d3e5a342c66a2f35a3903a618a2ec1d741fedf0",
        "modules_built": False,
        "native_vm_build": False,
        "result": "pass",
    }, "exact device Buildbox build")
    candidate_dtb = contract["candidate_dtb"]
    require(candidate_dtb == {
        "source_sha256": "923575e4e25498f2749bb440af78372e36bb318bf5717d05ced18be600ebd6c8",
        "derived_sha256": "90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d",
        "derived_size": 27636,
        "removed_nodes": 1,
        "added_nodes": 1,
        "added_reference_properties": 3,
        "semantic_reverse_proof": "byte-identical-sorted-dts",
        "sha256sums_sha256": "f930082aed85d5bab73ac07f8385c1fc7710a0ffb59483e567655bfc4ac890b6",
        "offline_hardware_effects": 0,
    }, "exact candidate DT")
    candidate = contract["candidate"]
    require(candidate == {
        "repository_commit": "5e4b0d584f76d4bf5a5e7e924b886d6b65ed4bd5",
        "profile": "a72-platform-provider-clock-candidate",
        "kernel_release": "7.1.3-gemini-a72-clock-third",
        "raw_sha256": "d2f4d2bdecbac924eaf4b6d2a4732b6e6be2847391b974da3b4bc6d2beeb3139",
        "raw_size": 6912000,
        "padded_sha256": "1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2",
        "padded_size": 16777216,
        "candidate_manifest_sha256": "2a600e48125d45b6281bb8c056ebbc1f107e2b3039791184b5e334f4414606d0",
        "lk_gates_passed": 32,
        "container_mutations_rejected": 6,
        "predecessor_sha256_required": "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e",
        "predecessor_retained_record_1_sha256": "047e5c5c6f3bfa3b8f86ba174c3e1ceb65926a190dbec7099f915ee5b7e371b2",
        "predecessor_retained_record_2_sha256": "2f0ad139001347459344b031abd8376f63ff455f1742d24569823f33d23918e0",
        "boot_candidate": True,
        "deployment_status": "write-synced-flushed-full-readback-verified-and-shut-down",
        "device_action": True,
    }, "exact boot candidate")
    require(contract["deployment"] == {
        "repository_commit": "2fb031e14b09deaa9753f9d88907f0a7f19896a1",
        "boot_id": "258b3f63-71ff-4351-9db5-6fa839fd3d89",
        "target_logical_name": "boot2",
        "target": "/dev/mmcblk0p30",
        "root": "/dev/mmcblk0p29",
        "predecessor_sha256": "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e",
        "readback_sha256": "1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2",
        "retained_predecessor": "exact-completed-provider-pair",
        "retained_record_1_sha256": "047e5c5c6f3bfa3b8f86ba174c3e1ceb65926a190dbec7099f915ee5b7e371b2",
        "retained_record_2_sha256": "2f0ad139001347459344b031abd8376f63ff455f1742d24569823f33d23918e0",
        "retained_ram_write": False,
        "fresh_predecessor_backup": False,
        "full_readback_verified": True,
        "shutdown_confirmed": True,
        "reboot": False,
    }, "exact boot2 deployment")
    require(contract["runtime_tooling"] == {
        "source_collector": "experiments/2026-08-25-mainline-a72-platform-provider-deferred-bind-repair/scripts/collect-runtime.sh",
        "source_collector_sha256": "20f795c6d389b2d37216dbaa363386145fc6be5e29e2b63dee287afb6b6342a2",
        "source_validator": "experiments/2026-08-25-mainline-a72-platform-provider-deferred-bind-repair/scripts/validate-runtime.py",
        "source_validator_sha256": "8b88d26718faf70e98960e784d781e66041c37bbe45cd177bd4648fb5677db91",
        "remote_probe_sha256": "cd5f30e02a2d93b5794deac72ddda57f10680c6b91d137a3d3d2fd439d7a7c4c",
        "validator_sha256": "0ca1a9146b35c3c4a30300205b59513c7ac1a2c3fbf5433f6a687ee2260d682f",
        "collector_sha256": "3ae4fca56691f5f9f07e0e2b122aaf0e8cdbdef80c2c12442e9a6495931d1f01",
        "accepted_decision_branches": 4,
        "rejected_mutations": 19,
        "expected_output": "artifacts/runtime-captures/a72-platform-provider-clock-attempt-1",
        "collector_reboot": False,
        "offline_device_action": False,
        "result": "pass-preboot",
    }, "exact preboot runtime tooling")
    for relative, expected in (
        ("scripts/remote-live-probe.sh", contract["runtime_tooling"]["remote_probe_sha256"]),
        ("scripts/validate-runtime.py", contract["runtime_tooling"]["validator_sha256"]),
        ("scripts/collect-runtime.sh", contract["runtime_tooling"]["collector_sha256"]),
    ):
        require(
            hashlib.sha256((exp / relative).read_bytes()).hexdigest() == expected,
            f"runtime tool hash: {relative}",
        )
    for receipt, tokens in (
        (candidate_build_receipt, (
            "build_backend=buildbox",
            "kernel_release=7.1.3-gemini-a72-clock-third",
            "new_observer_warning=none",
            "native_vm_build=none",
            "result=pass",
        )),
        (dtb_receipt, (
            "derived_dtb_sha256=90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d",
            "semantic_baseline_after_reverse_replacement=byte-identical-sorted-dts",
            "hardware_write=none",
            "result=pass",
        )),
        (candidate_receipt, (
            "raw_candidate_sha256=d2f4d2bdecbac924eaf4b6d2a4732b6e6be2847391b974da3b4bc6d2beeb3139",
            "boot2_padded_sha256=1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2",
            "lk_gates=32-of-32",
            "hardware_write=none",
            "result=pass",
        )),
        (deployment_receipt, (
            "target_logical_name=boot2",
            "predecessor_sha256=f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e",
            "readback_sha256=1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2",
            "retained_predecessor=exact-completed-provider-pair",
            "fresh_predecessor_backup=no",
            "shutdown=confirmed-unreachable",
            "reboot=no",
            "result=pass",
        )),
        (runtime_tooling_receipt, (
            "remote_probe_sha256=cd5f30e02a2d93b5794deac72ddda57f10680c6b91d137a3d3d2fd439d7a7c4c",
            "validator_sha256=0ca1a9146b35c3c4a30300205b59513c7ac1a2c3fbf5433f6a687ee2260d682f",
            "collector_sha256=3ae4fca56691f5f9f07e0e2b122aaf0e8cdbdef80c2c12442e9a6495931d1f01",
            "runtime_accepted_branches=4",
            "runtime_rejected_mutations=19",
            "collector_reboot=no",
            "device_action=none",
            "result=pass",
        )),
    ):
        for token in tokens:
            require(token in receipt, f"candidate receipt token: {token}")

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
        "generation_tooling": "pass-attempt-7",
        "patch_generation": "pass-corrected-generated-fetched-and-admitted-byte-for-byte",
        "kernel_build": "kunit-and-candidate-buildbox-pass",
        "offline_candidate_validation": "pass",
        "boot_candidate": True,
        "deployment": "write-verified-and-shut-down",
        "runtime_tooling": "validated-and-pending-publication",
        "device_action": "guarded-boot2-write",
    }, "current status")
    require("/Users/" not in "\n".join((readme, design, audit)), "no host path")

    print("definition_validation=pass")
    print("retained_records=2")
    print("protected_clock_calls=1")
    print("protected_clock_caller_retries=0")
    print("explicit_mmio_writes_maximum=401")
    print("explicit_mmio_reads_maximum=419")
    print("boot_candidate=true")
    print("runtime_tooling=validated-preboot")
    print("device_action=guarded-boot2-write")


if __name__ == "__main__":
    main()
