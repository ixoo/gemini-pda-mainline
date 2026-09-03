#!/usr/bin/env python3
"""Validate the post-0496 one-task down/restore binder contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "physical-binder-implementation-contract.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate(document: dict) -> None:
    require(document.get("schema") == 1, "schema changed")
    require(
        document.get("experiment") ==
        "2026-09-02-mainline-a72-hotplug-lifecycle-gate",
        "experiment changed",
    )
    require(
        document.get("phase") ==
        "cpu9-one-task-down-restore-binder-implementation-contract",
        "phase changed",
    )
    require(
        document.get("repository_parent") ==
        "827880793d373f3dd5dd6316ed3469f43fd430ce",
        "repository parent changed",
    )
    require(document.get("canonical_series_entries") == 485,
            "series count changed")
    require(
        document.get("canonical_series_sha256") ==
        "bc9d4eba342411811239dc90746d9bb05cffb5d23a244586b9ffe3abd6624c1f",
        "series identity changed",
    )
    require(
        document.get("manifest_sha256") ==
        "4f785abd677ec7b03a730de2cd650ca08f4611337ee7ad4c088e57e156eb7c83",
        "manifest identity changed",
    )
    require(
        document.get("parent_contract_sha256") ==
        "c4ffca0b72c545fd4c418b4210304b14f4cfa33d4aeaddbfe78cc62f4e437abe",
        "parent contract changed",
    )
    require(
        document.get("parent_contract_evidence_sha256") ==
        "15f3509d09898ad4456f73953e121b37d65f308f89473bfa069a97f1607c50b2",
        "parent evidence changed",
    )
    require(
        document.get("restore_runtime_evidence_sha256") ==
        "6400f48e77b17e2a88ded40a4419ca15d3c9c11ab734d22a1edf923fde9b4a4b",
        "restore evidence changed",
    )

    prepared_source = document.get("prepared_source", {})
    require(len(prepared_source) == 26, "prepared source set changed")
    require(
        document.get("prepared_source_manifest_sha256") ==
        "bf45ae3aa2b632554c6b4768d60f7d21f1173e173e3679ad7ba9e2c9cb4419f6",
        "prepared source manifest identity changed",
    )
    require(
        object_sha256(prepared_source) ==
        document.get("prepared_source_manifest_sha256"),
        "prepared source identities changed",
    )

    predecessors = document.get("predecessors", {})
    require(set(predecessors) == {
        "down_executor_patch", "watchdog_validator_patch",
        "membership_parent_patch", "binder_parent_patch",
        "record4_ledger_patch", "snapshot_patch", "cpu8_observer_patch",
        "restore_executor_patch", "restore_test_patch",
    }, "predecessor set changed")
    require(all(
        isinstance(value, str) and len(value) == 64
        for value in predecessors.values()
    ), "predecessor identity invalid")
    require(
        document.get("predecessor_manifest_sha256") ==
        "12a4ae610f12b934891dd744dacead6000f3309e41ad9f41ad7977a8758dac61",
        "predecessor manifest identity changed",
    )
    require(
        object_sha256(predecessors) ==
        document.get("predecessor_manifest_sha256"),
        "predecessor identities changed",
    )

    orchestration = document.get("orchestration", {})
    require(
        orchestration.get("owner") ==
        "existing-one-shot-admission-trigger-task",
        "orchestration owner changed",
    )
    require(
        orchestration.get("ordered_cpu_calls") == [
            "add-cpu8", "add-cpu9", "remove-cpu9", "add-cpu9-restore"
        ],
        "CPU operation order changed",
    )
    require(orchestration.get("target_cpu") == 9,
            "target CPU changed")
    require(orchestration.get("same_task_required") is True,
            "same-task ownership removed")
    require(orchestration.get("remove_cpu_calls") == 1 and
            orchestration.get("restore_add_cpu_calls") == 1 and
            orchestration.get("retries") == 0,
            "CPU request budget changed")
    for gate in (
        "userspace_gap", "second_trigger", "sysfs_hotplug",
        "automatic_probe_action",
    ):
        require(orchestration.get(gate) is False, f"{gate} enabled")

    composition = document.get("composition", {})
    require(composition.get("ordered_primitives") == [
        "exact-parent-proof", "record4-begin",
        "down-executor-preflight", "watchdog-readonly-validation",
        "baseline-snapshot", "down-executor-validate",
        "cpu9-target-disable", "cpu-off-commit-ledger",
        "one-direct-cpu-off", "one-direct-affinity-info",
        "post-state-snapshot", "bounded-cpu8-observer",
        "down-owner-proof-and-complete",
        "restore-executor-preflight-and-validate",
        "cpu-on-commit-ledger", "one-cpu-boot",
        "restore-secondary-complete", "restore-full-complete",
        "terminal-record4-success",
    ], "primitive order changed")
    exact_counts = {
        "parent_proof_calls": 1,
        "watchdog_validation_calls": 1,
        "record4_begin_calls": 1,
        "record4_records_max": 16,
        "record4_word_writes_max": 451,
        "snapshot_calls": 2,
        "cpu8_observer_calls": 1,
        "cpu8_wait_ms_max": 250,
        "cpu_off_calls": 1,
        "affinity_info_calls": 1,
        "cpu_on_calls": 1,
        "last_a72_off_calls": 0,
        "cpu0_7_off_calls": 0,
    }
    for key, expected in exact_counts.items():
        require(composition.get(key) == expected, f"{key} changed")

    callbacks = document.get("callback_binding", {})
    require(callbacks.get("down_callbacks") == [
        "preflight", "validate", "disable", "die", "kill", "complete",
        "failed",
    ], "down callback set changed")
    require(callbacks.get("restore_callbacks") == [
        "preflight", "validate", "boot", "secondary-complete", "complete",
        "rollback",
    ], "restore callback set changed")
    require(
        callbacks.get("cpu_can_disable") ==
        "cpu9-only-exact-validated-active-transaction",
        "CPU disable gate changed",
    )
    require(
        callbacks.get("cpu_off") ==
        "direct-psci-ops-cpu-off-standard-power-down",
        "CPU_OFF boundary changed",
    )
    require(
        callbacks.get("affinity_info") ==
        "direct-psci-ops-affinity-info-level0-once",
        "affinity boundary changed",
    )
    require(callbacks.get("generic_cpu_kill_calls") == 0,
            "generic polling kill enabled")
    require(callbacks.get("initial_p32_on_restore_rollback") is False,
            "initial rollback publication enabled")
    require(callbacks.get("tasks_frozen_allowed") is False,
            "frozen-task hotplug enabled")

    failure = document.get("failure_policy", {})
    require(
        failure.get("precommit") ==
        "close-trigger-and-release-attempt-software-only",
        "precommit policy changed",
    )
    require(
        failure.get("postcommit") ==
        "durable-terminal-fault-then-reset-only",
        "postcommit policy changed",
    )
    require(failure.get("postcommit_retries") == 0,
            "postcommit retry enabled")
    for gate in (
        "postcommit_inverse", "screen_or_reboot_is_evidence",
        "expected_watchdog_reset_is_success",
    ):
        require(failure.get(gate) is False, f"unsafe {gate} enabled")

    implementation = document.get("implementation", {})
    require(implementation.get("default_enabled") is False,
            "implementation default enabled")
    require(implementation.get("isolated_kunit_profile_only") is True,
            "isolated profile requirement removed")
    require(
        implementation.get("candidate_selection_separate_commit") is True,
        "candidate separation removed",
    )
    for gate in (
        "production_profile_selected", "device_tree_nodes",
        "production_trigger_open", "sysfs_cpu_online_exposed",
        "boot_candidate", "device_action", "native_vm_build",
    ):
        expected = 0 if gate == "device_tree_nodes" else False
        require(implementation.get(gate) == expected, f"{gate} enabled")


def validate_source(document: dict, source_root: Path) -> None:
    require(source_root.is_dir() and not source_root.is_symlink(),
            "unsafe source root")
    state = (source_root / ".gemini-source-state").read_text().strip()
    integrity = (source_root / ".gemini-source-integrity").read_text().strip()
    require(state == document["prepared_source_state"],
            "prepared source state changed")
    require(integrity == document["prepared_source_integrity"],
            "prepared source integrity changed")
    for relative, expected in document.get("prepared_source", {}).items():
        path = source_root / relative
        require(path.is_file() and not path.is_symlink(),
                f"missing or unsafe source: {relative}")
        require(sha256(path) == expected,
                f"prepared source identity changed: {relative}")

    psci = (source_root / "arch/arm64/kernel/mt6797_psci.c").read_text()
    require("static bool mt6797_psci_cpu_can_disable" in psci and
            "return false;" in psci,
            "A72 disable veto changed")
    for callback in (
        ".cpu_down_preflight", ".cpu_down_validate", ".cpu_down_complete",
        ".cpu_down_failed",
    ):
        require(callback not in psci,
                f"production callback already bound: {callback}")
    require("mt6797_a72_restore_executor" not in psci,
            "restore executor already bound")

    admission = (
        source_root /
        "drivers/soc/mediatek/mt6797-a72-cpu9-admission-controller.c"
    ).read_text()
    require("ops->add_cpu(context, MT6797_A72_CPU9_EXECUTOR_CPU9)" in admission,
            "initial CPU9 request changed")
    require("remove_cpu(" not in admission and "run_hotplug" not in admission,
            "lifecycle orchestration already bound")
    require("state->cpu_off_requests" not in admission,
            "CPU_OFF request accounting unexpectedly active")

    restore = (
        source_root /
        "drivers/soc/mediatek/mt6797-a72-restore-executor.c"
    ).read_text()
    require("ops->cpu_boot(context, cpu)" in restore,
            "restore CPU boot seam changed")
    require("psci_ops." not in restore and "cpu_psci_ops." not in restore,
            "restore executor gained a physical caller")

    down = (
        source_root /
        "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c"
    ).read_text()
    require("ops->affinity_info(context, cpu," in down,
            "down affinity seam changed")
    require("psci_ops." not in down and "cpu_psci_ops." not in down,
            "down executor gained a physical caller")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    parser.add_argument("--source-root", type=Path)
    args = parser.parse_args()
    document = json.loads(args.contract.read_text(encoding="utf-8"))
    validate(document)
    print("binder_implementation_contract=pass")
    print("target_cpu=9")
    print("ordered_cpu_calls=add8,add9,remove9,add9-restore")
    print("unsafe_physical_retries=0")
    print("production_profile_selected=false")
    print("boot_candidate=false")
    print("device_action=none")
    if args.source_root:
        validate_source(document, args.source_root.resolve())
        print("prepared_source=pass")


if __name__ == "__main__":
    main()
