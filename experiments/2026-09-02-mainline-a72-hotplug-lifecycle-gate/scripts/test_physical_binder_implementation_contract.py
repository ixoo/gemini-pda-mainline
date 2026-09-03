#!/usr/bin/env python3
"""Reject unsafe mutations of the one-task binder implementation contract."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "physical-binder-implementation-contract.json"
VALIDATOR = Path(__file__).with_name(
    "validate_physical_binder_implementation_contract.py"
)


def load_validator():
    spec = importlib.util.spec_from_file_location("binder_contract", VALIDATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("validator import failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def set_path(document: dict, path: tuple[str, ...], value: object) -> None:
    current = document
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value


def main() -> None:
    validator = load_validator()
    document = json.loads(CONTRACT.read_text(encoding="utf-8"))
    validator.validate(document)
    mutations = (
        (("repository_parent",), "0" * 40),
        (("canonical_series_entries",), 484),
        (("restore_runtime_evidence_sha256",), "0" * 64),
        (("prepared_source", "drivers/soc/mediatek/Kconfig"), "0" * 64),
        (("predecessors", "restore_executor_patch"), "0" * 64),
        (("orchestration", "owner"), "userspace"),
        (("orchestration", "ordered_cpu_calls"),
         ["add-cpu8", "add-cpu9", "add-cpu9-restore", "remove-cpu9"]),
        (("orchestration", "target_cpu"), 8),
        (("orchestration", "same_task_required"), False),
        (("orchestration", "userspace_gap"), True),
        (("orchestration", "remove_cpu_calls"), 2),
        (("orchestration", "restore_add_cpu_calls"), 2),
        (("orchestration", "retries"), 1),
        (("orchestration", "second_trigger"), True),
        (("orchestration", "sysfs_hotplug"), True),
        (("composition", "record4_records_max"), 17),
        (("composition", "record4_word_writes_max"), 452),
        (("composition", "snapshot_calls"), 3),
        (("composition", "cpu8_observer_calls"), 2),
        (("composition", "cpu8_wait_ms_max"), 251),
        (("composition", "cpu_off_calls"), 2),
        (("composition", "affinity_info_calls"), 2),
        (("composition", "cpu_on_calls"), 2),
        (("composition", "last_a72_off_calls"), 1),
        (("callback_binding", "cpu_can_disable"), "all-a72"),
        (("callback_binding", "generic_cpu_kill_calls"), 1),
        (("callback_binding", "initial_p32_on_restore_rollback"), True),
        (("callback_binding", "tasks_frozen_allowed"), True),
        (("failure_policy", "postcommit"), "return-error"),
        (("failure_policy", "postcommit_retries"), 1),
        (("failure_policy", "postcommit_inverse"), True),
        (("failure_policy", "screen_or_reboot_is_evidence"), True),
        (("failure_policy", "expected_watchdog_reset_is_success"), True),
        (("implementation", "default_enabled"), True),
        (("implementation", "isolated_kunit_profile_only"), False),
        (("implementation", "production_profile_selected"), True),
        (("implementation", "device_tree_nodes"), 1),
        (("implementation", "production_trigger_open"), True),
        (("implementation", "sysfs_cpu_online_exposed"), True),
        (("implementation", "boot_candidate"), True),
        (("implementation", "device_action"), True),
        (("implementation", "native_vm_build"), True),
        (("implementation", "candidate_selection_separate_commit"), False),
    )
    rejected = 0
    for path, value in mutations:
        mutated = deepcopy(document)
        set_path(mutated, path, value)
        try:
            validator.validate(mutated)
        except ValueError:
            rejected += 1
        else:
            raise AssertionError(f"unsafe mutation accepted: {'.'.join(path)}")
    print("binder_implementation_contract_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")


if __name__ == "__main__":
    main()
