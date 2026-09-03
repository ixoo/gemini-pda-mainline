#!/usr/bin/env python3
"""Require unsafe CPU9 physical-binder contract mutations to fail."""

from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "physical-binder-contract.json"
VALIDATOR = ROOT / "scripts/validate_physical_binder_contract.py"


def set_path(document: dict, path: tuple[str, ...], value: object) -> None:
    target = document
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value


def run(document: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="gemini-physical-binder-") as temp:
        candidate = pathlib.Path(temp) / "contract.json"
        candidate.write_text(json.dumps(document, indent=2) + "\n")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--contract", str(candidate)],
            check=False, capture_output=True, text=True,
        )


def main() -> int:
    base = json.loads(CONTRACT.read_text())
    positive = run(base)
    if positive.returncode:
        sys.stderr.write(positive.stderr)
        return 1

    mutations: list[tuple[str, tuple[str, ...], object]] = [
        ("target-cpu8", ("entry_gate", "target_cpu"), 8),
        ("entry-members", ("entry_gate", "a72_members"), "0x1"),
        ("different-task", ("entry_gate", "same_task_required"), False),
        ("frozen-hotplug", ("entry_gate", "frozen_tasks_allowed"), True),
        ("mutable-parent-proof", ("entry_gate", "parent_proof_read_only"), False),
        ("late-entry", ("entry_gate", "watchdog_age_max_ms"), 10000),
        ("watchdog-owner", ("watchdog", "owner"), "new-hotplug-owner"),
        ("watchdog-deadline", ("watchdog", "deadline_ms"), 30000),
        ("watchdog-no-register-check", ("watchdog", "mode_and_length_exact"), False),
        ("watchdog-write", ("watchdog", "register_writes"), 1),
        ("watchdog-takeover", ("watchdog", "takeover_calls"), 1),
        ("watchdog-refresh", ("watchdog", "refresh_calls"), 1),
        ("record3", ("retained_ledger", "record_index"), 3),
        ("record3-base", ("retained_ledger", "record_base"), "0x44413000"),
        ("reuse-nonempty", ("retained_ledger", "requires_logical_empty"), False),
        ("record-clear", ("retained_ledger", "clear_calls"), 1),
        ("one-copy", ("retained_ledger", "format", "copies"), 1),
        ("short-copy", ("retained_ledger", "format", "copy_words"), 18),
        ("crc-not-last", ("retained_ledger", "format", "integrity_committed_last"), False),
        ("no-full-readback", ("retained_ledger", "format", "full_copy_readback"), False),
        ("signature-first", ("retained_ledger", "format", "signature_committed_last"), False),
        ("missing-mismatch-field",
         ("retained_ledger", "format", "fields"),
         [item for item in base["retained_ledger"]["format"]["fields"]
          if item != "readback-mismatch"]),
        ("missing-off-commit-stage", ("retained_ledger", "stages", "7"), "cpu-off-called"),
        ("missing-restore-stage", ("retained_ledger", "stages", "15"), "cpu-on-returned"),
        ("extra-writes", ("retained_ledger", "total_word_writes_max"), 999),
        ("no-recovery-reader", ("retained_ledger", "recovery_reader_required_before_candidate"), False),
        ("remove-remote-record", ("retained_ledger", "remote_record_removal"), True),
        ("snapshot-retry", ("snapshot", "binding_retries"), 1),
        ("reuse-direct-state", ("snapshot", "direct_state_compositor_calls"), 1),
        ("reuse-protected-ledger", ("snapshot", "protected_readback_ledger_checkpoints"), 1),
        ("clock-unbounded", ("snapshot", "dvfsp_clock_transport_per_call", "semaphore_acquire_request_writes_max"), 400),
        ("clock-opp-write", ("snapshot", "dvfsp_clock_transport_per_call", "pll_divider_opp_voltage_writes"), 1),
        ("bigidvfs-set", ("snapshot", "bigidvfs_per_call", "sram_set_calls"), 1),
        ("callback-sync", ("cpu8_callback", "dispatch"), "smp_call_function_single-wait-1"),
        ("callback-retry", ("cpu8_callback", "retry_calls"), 1),
        ("callback-unbounded", ("cpu8_callback", "controller_wait_timeout_ms"), 0),
        ("generic-kill", ("psci", "generic_cpu_psci_cpu_kill_calls"), 1),
        ("affinity-twice", ("psci", "affinity_calls"), 2),
        ("cpu-off-return-success", ("psci", "cpu_off_return_success"), True),
        ("cpu-on-twice", ("psci", "cpu_on_calls"), 2),
        ("open-disable", ("callback_binding", "cpu_can_disable"), "cpu9-whenever-present"),
        ("p32-restore", ("callback_binding", "up_rollback"), "publish-initial-p32"),
        ("userspace-gap", ("orchestration", "userspace_gap_after_cpu9_online"), True),
        ("restore-before-down", ("orchestration", "ordered_cpu_calls"), ["add-cpu8", "add-cpu9", "add-cpu9-restore", "remove-cpu9"]),
        ("second-trigger", ("orchestration", "second_trigger"), True),
        ("reuse-initial-binder", ("restore", "initial_cpu9_binder_reused"), True),
        ("restore-with-cpu9-online", ("restore", "entry_cpu9_online"), True),
        ("no-full-cpuhp", ("restore", "full_cpuhp_completion_required"), False),
        ("reboot-as-proof", ("failure_policy", "screen_or_reboot_is_result_evidence"), True),
        ("guessed-inverse", ("failure_policy", "guessed_inverse"), True),
        ("bind-production", ("production_callbacks_bound",), True),
        ("boot-candidate", ("boot_candidate",), True),
        ("device-action", ("device_action",), True),
        ("native-build", ("native_vm_build",), True),
    ]

    for name, path, value in mutations:
        candidate = copy.deepcopy(base)
        set_path(candidate, path, value)
        result = run(candidate)
        if result.returncode == 0:
            print(f"mutation={name} result=unexpected-pass", file=sys.stderr)
            return 1

    print("experiment=2026-09-02-mainline-a72-hotplug-lifecycle-gate")
    print(f"mutation_rejections={len(mutations)}")
    print("physical_binder_contract_mutations=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
