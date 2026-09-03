#!/usr/bin/env python3
"""Require unsafe CPU9 physical-executor contract mutations to fail."""

from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "physical-executor-contract.json"
VALIDATOR = ROOT / "scripts/validate_physical_executor_contract.py"


def set_path(document: dict, path: tuple[str, ...], value: object) -> None:
    target = document
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value


def run(document: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="gemini-physical-executor-") as temp:
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
        ("watchdog-owner", ("watchdog", "owner"), "new-hotplug-owner"),
        ("watchdog-deadline", ("watchdog", "deadline_ms"), 30000),
        ("watchdog-takeover", ("watchdog", "takeover_calls"), 1),
        ("watchdog-refresh", ("watchdog", "refresh_calls"), 1),
        ("watchdog-cancel", ("watchdog", "cancel_calls"), 1),
        ("watchdog-cancellable", ("watchdog", "cancellation_api_available"), True),
        ("target-owner", ("split_owners", "disable_and_cpu_off"), "controller"),
        ("missing-commit-checkpoint", ("ordered_stages",),
         [stage for stage in base["ordered_stages"]
          if stage != "target-durable-commit-checkpoint"]),
        ("affinity-before-cpu-off", ("ordered_stages",),
         ["controller-one-active-affinity-level0"] +
         [stage for stage in base["ordered_stages"]
          if stage != "controller-one-active-affinity-level0"]),
        ("cpu-off-retry", ("budgets", "cpu_off_retry"), 1),
        ("affinity-budget", ("budgets", "cpu9_affinity_info_level0"), 2),
        ("cpu8-last-off", ("budgets", "cpu8_last_off"), 1),
        ("cpu8-one-status", ("readback", "cpu8_required_in_both_status_words"), False),
        ("cpu9-one-status", ("readback", "cpu9_clear_in_both_status_words"), False),
        ("missing-cluster", ("readback", "unchanged_exact"),
         [item for item in base["readback"]["unchanged_exact"]
          if item != "spm_mp2_cpusys_pwr_con"]),
        ("missing-provider", ("readback", "unchanged_exact"),
         [item for item in base["readback"]["unchanged_exact"]
          if item != "provider-five-byte-tuple"]),
        ("cci-mask", ("readback", "unchanged_masked", "cci_mp2_port_control"),
         "0x00000000"),
        ("cpu9-control-guess", ("readback", "cpu9_core_control"), "exact-zero"),
        ("general-spm-predicate", ("readback", "general_spm_status"), "exact-equality"),
        ("bounded-affinity", ("secure_affinity_intrinsically_bounded",), True),
        ("park-success", ("park_only_success",), True),
        ("bind-production", ("production_callbacks_bound",), True),
        ("open-disable", ("cpu_can_disable",), True),
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
    print("physical_executor_contract_mutations=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
