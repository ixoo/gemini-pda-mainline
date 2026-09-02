#!/usr/bin/env python3
"""Require unsafe CPU9 hotplug contract mutations to fail closed."""

from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract.json"
VALIDATOR = ROOT / "scripts/validate_contract.py"


def set_path(document: dict, path: tuple[str, ...], value: object) -> None:
    target = document
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value


def run(document: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="gemini-hotplug-contract-") as temp:
        candidate = pathlib.Path(temp) / "contract.json"
        candidate.write_text(json.dumps(document, indent=2) + "\n")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), "--contract", str(candidate),
             "--contract-only"],
            check=False, capture_output=True, text=True,
        )


def main() -> int:
    base = json.loads(CONTRACT.read_text())
    positive = run(base)
    if positive.returncode:
        sys.stderr.write(positive.stderr)
        return 1

    mutations: list[tuple[str, tuple[str, ...], object]] = [
        ("source-identity", ("prepared_source", "files", "kernel/cpu.c"), "0" * 64),
        ("disable-veto", ("current_boundary", "cpu_can_disable"), True),
        ("p32-scope", ("current_boundary", "p32_scope"), "normal-down"),
        ("target-cpu", ("selected_transition", "target_cpu"), 8),
        ("retained-peer", ("selected_transition", "retained_peer_cpu"), 9),
        ("offline-members", ("selected_transition", "offline_members"), "0x0"),
        ("physical-off", ("selected_transition", "physical_cpu_off_required"), False),
        ("park-success", ("selected_transition", "park_only_is_success"), True),
        ("last-a72-off", ("selected_transition", "last_a72_off_allowed"), True),
        ("missing-preflight", ("required_generic_handoffs",),
         base["required_generic_handoffs"][1:]),
        ("missing-failure-publication", ("required_generic_handoffs",),
         base["required_generic_handoffs"][:-1]),
        ("cpu-off-budget", ("budgets", "cpu9_cpu_off"), 2),
        ("affinity-budget", ("budgets", "cpu9_affinity_info_level0"), 2),
        ("restore-budget", ("budgets", "cpu9_restore_cpu_on"), 0),
        ("affinity-falsely-bounded",
         ("timing", "secure_affinity_call_is_intrinsically_bounded"), True),
        ("watchdog-refresh", ("timing", "watchdog_refresh_after_cpu_off_commit"), True),
        ("retry-policy", ("failure_policy", "restore_failure"),
         "retry-cpu-on"),
        ("missing-restored-topology", ("physical_pass_predicate",),
         [item for item in base["physical_pass_predicate"]
          if item != "exact-4+4+2-topology-after-restore"]),
        ("allow-second-affinity", ("forbidden_actions",),
         [item for item in base["forbidden_actions"]
          if item != "second-affinity-query"]),
        ("boot-candidate", ("boot_candidate",), True),
        ("native-vm-build", ("native_vm_build",), True),
    ]

    for name, path, value in mutations:
        mutated = copy.deepcopy(base)
        set_path(mutated, path, value)
        result = run(mutated)
        if result.returncode == 0:
            print(f"mutation={name} result=unexpected-pass", file=sys.stderr)
            return 1

    print("experiment=2026-09-02-mainline-a72-hotplug-lifecycle-gate")
    print(f"mutation_rejections={len(mutations)}")
    print("hotplug_lifecycle_contract_mutations=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
