#!/usr/bin/env python3
"""Validate the hardware-free CPU9 physical binder contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "physical-binder-contract.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(document: dict) -> None:
    require(document.get("schema") == 1, "schema changed")
    require(document.get("experiment") ==
            "2026-09-02-mainline-a72-hotplug-lifecycle-gate",
            "experiment changed")
    require(document.get("phase") ==
            "cpu9-physical-binder-hardware-free-contract",
            "phase changed")
    require(document.get("repository_parent") ==
            "ae643f095bc89ad71b45b3cf682ff519a877e711",
            "repository parent changed")
    require(document.get("canonical_series_entries") == 477,
            "series count changed")
    require(document.get("canonical_series_sha256") ==
            "6912c6b0b01cd86de634fcae044e864c2a898fa2211b765e6b5e68b06ad28a98",
            "series identity changed")
    require(document.get("manifest_sha256") ==
            "4e26f0534854c282f4f3a86a34bce5b147899569053d1d40c811553186dabda3",
            "manifest identity changed")
    require(document.get("executor_runtime_evidence_sha256") ==
            "1f684f23bb8bce421d3118aa3cfeef9d052bfc9a539cb39ba74e041d5b6e9b47",
            "executor evidence changed")

    entry = document.get("entry_gate", {})
    require(entry.get("controller") ==
            "existing-one-shot-admission-trigger-task",
            "controller ownership changed")
    require(entry.get("target_cpu") == 9 and
            entry.get("target_mpidr") == "0x201",
            "target changed")
    require(entry.get("a72_members") == "0x3" and
            entry.get("a72_online_mask") == "0x3" and
            entry.get("system_online_cpus") == "0-9",
            "entry topology changed")
    require(entry.get("initial_cpu8_requests") == 1 and
            entry.get("initial_cpu9_requests") == 1 and
            entry.get("down_authorizations") == 1,
            "entry request budget changed")
    require(entry.get("same_task_required") is True and
            entry.get("frozen_tasks_allowed") is False and
            entry.get("parent_proof_read_only") is True,
            "entry ownership weakened")
    require(entry.get("watchdog_age_max_ms") == 5000,
            "watchdog entry age changed")
    require(set(entry.get("parent_exact", [])) == {
        "cpu8-retired-success", "cpu9-retired-success",
        "provider-held-same-identity", "membership-0x3",
        "cpu8-and-cpu9-online", "no-active-owner-or-policy-transition",
        "cpu8-binder-exact-terminal", "watchdog-identity-and-takeover-time",
    }, "parent proof changed")

    watchdog = document.get("watchdog", {})
    require(watchdog == {
        "owner": "established-cpu8-transition",
        "deadline_ms": 15000,
        "identity_nonzero": True,
        "takeover_time_required": True,
        "validation_lock": "recovery_lock",
        "validation_reads": ["software-owned", "software-identity",
                             "WDT_MODE", "WDT_LENGTH"],
        "mode_and_length_exact": True,
        "register_writes": 0,
        "takeover_calls": 0,
        "reload_calls": 0,
        "refresh_calls": 0,
        "cancel_calls": 0,
        "release_calls": 0,
        "terminal_disposition": "durable-result-then-expected-reset",
    }, "watchdog contract changed")

    ledger = document.get("retained_ledger", {})
    require(ledger.get("reservation_base") == "0x44410000" and
            ledger.get("reservation_size") == "0x000e0000" and
            ledger.get("record_index") == 4 and
            ledger.get("record_base") == "0x44414000" and
            ledger.get("record_size") == "0x1000",
            "retained record allocation changed")
    require(ledger.get("preserve_record_indices") == [0, 1, 2, 3],
            "predecessor records not preserved")
    for gate in ("requires_logical_empty",):
        require(ledger.get(gate) is True, f"{gate} removed")
    for count in ("clear_calls", "repair_calls", "reopen_calls",
                  "writer_retries"):
        require(ledger.get(count) == 0, f"{count} enabled")
    wire = ledger.get("format", {})
    require(wire.get("byte_order") == "little-endian" and
            wire.get("pstore_signature") == "0x43474244" and
            wire.get("magic") == "0x4c483947" and
            wire.get("version_word") == "0x00010001",
            "ledger wire identity changed")
    require(wire.get("header_words") == 3 and wire.get("copies") == 2 and
            wire.get("copy_words") == 27 and
            wire.get("integrity_word") == 26,
            "ledger dimensions changed")
    require(wire.get("integrity") ==
            "crc32-le-init-ffffffff-final-xor-ffffffff" and
            wire.get("integrity_committed_last") is True and
            wire.get("full_copy_readback") is True and
            wire.get("signature_committed_last") is True,
            "ledger commit protocol changed")
    require(wire.get("fields") == [
        "magic", "version", "generation", "stage", "terminal", "error",
        "session-id", "parent-generation", "parent-cookie",
        "watchdog-identity", "down-generation", "down-cookie",
        "restore-generation", "restore-cookie", "result-flags",
        "call-counts", "online-members", "readback-mismatch", "integrity",
    ], "ledger fields changed")
    require(ledger.get("stages") == {
        "1": "binding-entry-parent-exact",
        "2": "down-owner-prepared",
        "3": "watchdog-validated",
        "4": "baseline-valid",
        "5": "down-owner-validated",
        "6": "target-disable-valid",
        "7": "cpu-off-committed-before-smc",
        "8": "cpu-off-returned-fault",
        "9": "affinity-level0-off",
        "10": "post-state-valid",
        "11": "cpu8-responsive",
        "12": "off-proof-accepted",
        "13": "generic-down-complete-members-0x1",
        "14": "restore-prepared",
        "15": "cpu-on-committed-before-call",
        "16": "secondary-complete",
        "17": "generic-restore-complete-members-0x3",
    }, "ledger stage map changed")
    require(ledger.get("terminal_codes") == {
        "1": "rejected-precommit", "2": "cpu-off-returned",
        "3": "postcommit-down-fault", "4": "restore-fault",
        "5": "restored-success",
    }, "ledger terminal map changed")
    require(ledger.get("successful_checkpoint_records_max") == 16 and
            ledger.get("word_writes_per_record") == 28 and
            ledger.get("first_use_header_word_writes_max") == 3 and
            ledger.get("total_word_writes_max") == 451,
            "ledger write budget changed")
    require(ledger.get("recovery_requires_disconnect_reconnect_changed_boot_id")
            is True and
            ledger.get("recovery_reader_required_before_candidate") is True and
            ledger.get("remote_record_removal") is False,
            "recovery contract changed")

    snapshot = document.get("snapshot", {})
    require(snapshot.get("binder_snapshot_calls") == 2 and
            snapshot.get("binding_retries") == 0 and
            snapshot.get("direct_state_compositor_calls") == 0 and
            snapshot.get("physical_source_capture_calls") == 0 and
            snapshot.get("protected_readback_ledger_checkpoints") == 0,
            "snapshot call boundary changed")
    require(set(snapshot.get("long_lived_device_references", [])) == {
        "platform-state", "dvfsp-clock-backend", "bigidvfs-backend",
    }, "snapshot device ownership changed")
    require(snapshot.get("provider_snapshots") == 2 and
            snapshot.get("platform_stable_captures") == 2 and
            snapshot.get("dvfsp_clock_backend_calls") == 2 and
            snapshot.get("bigidvfs_backend_calls") == 2,
            "snapshot budget changed")
    require(snapshot.get("dvfsp_clock_transport_per_call") == {
        "fixed_poweron_writes": 1,
        "semaphore_acquire_request_writes_max": 200,
        "semaphore_release_request_writes_max": 200,
        "pll_divider_opp_voltage_writes": 0,
    }, "clock observation transport changed")
    require(snapshot.get("bigidvfs_per_call") == {
        "stable_samples": 2, "register_reads": 8, "sram_set_calls": 0,
    }, "BigiDVFS read boundary changed")
    require(set(snapshot.get("exclude_from_equality", [])) == {
        "clock.sample_generation", "bigidvfs.sample_generation",
    }, "snapshot equality exclusions changed")
    require(snapshot.get("readback_predicate") ==
            "physical-executor-contract-exact",
            "readback predicate changed")

    callback = document.get("cpu8_callback", {})
    require(callback == {
        "target_cpu": 8,
        "dispatch": "smp_call_function_single-wait-0",
        "dispatch_calls": 1,
        "controller_wait_timeout_ms": 250,
        "context_lifetime": "binder-owned-until-terminal-or-reset",
        "identity_checked": True,
        "retry_calls": 0,
        "synchronous_wait_1_calls": 0,
    }, "CPU8 callback boundary changed")

    psci = document.get("psci", {})
    require(psci == {
        "disable_guard": "cpu_psci_ops.cpu_disable",
        "cpu_off_call": "direct-psci_ops.cpu_off-standard-power-down",
        "cpu_off_calls": 1,
        "affinity_call":
            "direct-psci_ops.affinity_info-cpu_logical_map-9-level-0",
        "affinity_calls": 1,
        "generic_cpu_psci_cpu_kill_calls": 0,
        "cpu_on_call": "cpu_psci_ops.cpu_boot-9",
        "cpu_on_calls": 1,
        "cpu_off_return_success": False,
        "affinity_intrinsically_bounded": False,
        "retry_calls": 0,
    }, "PSCI boundary changed")

    binding = document.get("callback_binding", {})
    require(set(binding) == {
        "down_preflight", "down_validate", "cpu_can_disable",
        "cpu_disable", "cpu_die", "cpu_kill", "down_complete",
        "down_failed", "up_preflight", "up_validate", "cpu_boot",
        "up_secondary_complete", "up_complete", "up_rollback",
    }, "callback binding set changed")
    require(binding.get("cpu_can_disable") ==
            "cpu9-only-exact-validated-active-transaction",
            "disable gate weakened")
    require(binding.get("cpu_kill") ==
            "executor-kill-with-one-direct-affinity-call",
            "kill binding changed")
    require(binding.get("up_rollback") ==
            "fail-restore-and-suppress-initial-p32",
            "restore failure routing changed")

    orchestration = document.get("orchestration", {})
    require(orchestration.get("ordered_cpu_calls") ==
            ["add-cpu8", "add-cpu9", "remove-cpu9",
             "add-cpu9-restore"],
            "orchestration order changed")
    require(orchestration.get("remove_cpu_calls") == 1 and
            orchestration.get("restore_add_cpu_calls") == 1,
            "orchestration budget changed")
    for gate in ("userspace_gap_after_cpu9_online", "automatic_probe_action",
                 "second_trigger", "sysfs_cpu_online_control"):
        require(orchestration.get(gate) is False, f"{gate} enabled")

    restore = document.get("restore", {})
    require(restore.get("distinct_parent_linked_identity") is True and
            restore.get("initial_cpu9_binder_reused") is False and
            restore.get("entry_members") == "0x1" and
            restore.get("terminal_members") == "0x3" and
            restore.get("terminal_system_online_cpus") == "0-9",
            "restore identity or topology changed")
    for gate in ("entry_cpu8_online", "down_parent_completed_and_proven",
                 "same_provider_identity", "same_watchdog_identity",
                 "secondary_completion_required", "full_cpuhp_completion_required",
                 "cpu8_cpu9_progress_required"):
        require(restore.get(gate) is True, f"restore {gate} removed")
    require(restore.get("entry_cpu9_online") is False,
            "restore no longer requires CPU9 offline")

    failure = document.get("failure_policy", {})
    require(failure.get("precommit") ==
            "reject-close-trigger-release-attempt-software-only" and
            failure.get("postcommit") ==
            "durable-terminal-fault-no-retry-reset-only",
            "failure boundary changed")
    for gate in ("screen_or_reboot_is_result_evidence", "last_a72_off",
                 "cpu0_7_off", "guessed_inverse"):
        require(failure.get(gate) is False, f"unsafe {gate} enabled")

    require(document.get("implementation_order") == [
        "disconnected-parent-watchdog-ledger-snapshot-primitives",
        "disconnected-restore-executor-and-failure-routing",
        "one-task-down-restore-binder-and-orchestration",
        "separate-candidate-selection-after-buildbox-runtime-gates",
    ], "implementation order changed")
    for gate in ("production_callbacks_bound", "cpu_can_disable",
                 "candidate_dt_selected", "boot_candidate", "device_action",
                 "native_vm_build"):
        require(document.get(gate) is False, f"{gate} enabled")


def validate_source(document: dict, source_tree: pathlib.Path) -> None:
    state = (source_tree / ".gemini-source-state").read_text().strip()
    integrity = (source_tree / ".gemini-source-integrity").read_text().strip()
    require(state == document["prepared_source_state"],
            "prepared source state changed")
    require(integrity == document["prepared_source_integrity"],
            "prepared source integrity changed")
    for relative, expected in document.get("prepared_source", {}).items():
        path = source_tree / relative
        require(path.is_file(), f"missing prepared source: {relative}")
        require(sha256(path) == expected,
                f"prepared source identity changed: {relative}")

    psci = (source_tree / "arch/arm64/kernel/mt6797_psci.c").read_text()
    require("static bool mt6797_psci_cpu_can_disable" in psci and
            "return false;" in psci,
            "current A72 disable veto changed")
    require(".cpu_down_preflight" not in psci and
            ".cpu_down_validate" not in psci and
            ".cpu_down_complete" not in psci and
            ".cpu_down_failed" not in psci,
            "production down callback already bound")
    generic_psci = (source_tree / "arch/arm64/kernel/psci.c").read_text()
    require("do {" in generic_psci and
            "psci_ops.affinity_info(cpu_logical_map(cpu), 0)" in generic_psci,
            "generic polling CPU kill changed")

    watchdog = (source_tree / "include/linux/mtk_wdt.h").read_text()
    require("mtk_wdt_recovery_takeover" in watchdog and
            "recovery_validate" not in watchdog,
            "watchdog prerequisite changed")
    observer = (source_tree /
                "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
                ).read_text()
    require("gemini_protected_readback_ledger_checkpoint" in observer,
            "physical observer ledger side effect changed")
    clock = (source_tree /
             "drivers/soc/mediatek/mt6797-dvfsp-clock-backend.c").read_text()
    require("MT6797_DVFSP_SEMAPHORE_RETRIES\t\t200" in clock and
            "ops->write(context, cspm," in clock,
            "clock transport prerequisite changed")

    membership = (source_tree /
                  "arch/arm64/kernel/mt6797_a72_membership.c").read_text()
    for symbol in ("mt6797_a72_hotplug_prepare_down",
                   "mt6797_a72_hotplug_complete_down",
                   "mt6797_a72_hotplug_prepare_restore",
                   "mt6797_a72_hotplug_begin_restore",
                   "mt6797_a72_hotplug_complete_restore",
                   "mt6797_a72_hotplug_fail_restore"):
        require(symbol in membership, f"missing owner prerequisite: {symbol}")

    record4 = document["retained_ledger"]["record_base"][2:].lower()
    pstore_text = "\n".join(
        path.read_text(errors="ignore")
        for path in (source_tree / "fs/pstore").glob("*.[ch]"))
    require(record4 not in pstore_text.lower(),
            "record 4 is no longer unowned")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=pathlib.Path, default=CONTRACT)
    parser.add_argument("--source-tree", type=pathlib.Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.contract.read_text())
        validate(document)
        if args.source_tree:
            validate_source(document, args.source_tree)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physical_binder_contract=fail reason={exc}", file=sys.stderr)
        return 1
    print("experiment=2026-09-02-mainline-a72-hotplug-lifecycle-gate")
    print("phase=cpu9-physical-binder-hardware-free-contract")
    print("record4=0x44414000 stages=17 word_writes_max=451")
    print("watchdog=read-only-exact-inherited-identity age_max_ms=5000")
    print("sequence=add8-add9-remove9-add9-restore same_task=true")
    print("production_callbacks_bound=false")
    print("boot_candidate=false")
    print("device_action=false")
    print("physical_binder_contract=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
