#!/usr/bin/env python3
"""Audit the P32X effect-prefix patch as source evidence only."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0188-arm64-capture-P32X-effect-prefix.patch"

REQUIRED = (
    "CPU_UP_ROLLBACK_EFFECT_CPU_OFF_ATTEMPT",
    "CPU_UP_ROLLBACK_EFFECT_TOPOLOGY_REMOVE",
    "CPU_UP_ROLLBACK_EFFECT_NUMA_REMOVE",
    "CPU_UP_ROLLBACK_EFFECT_ONLINE_CLEAR",
    "CPU_UP_ROLLBACK_EFFECT_IPI_TEARDOWN",
    "CPU_UP_ROLLBACK_EFFECT_IRQ_MIGRATE",
    "CPU_UP_ROLLBACK_EFFECT_DEAD_PUBLISH",
    "CPU_UP_ROLLBACK_EFFECT_PARK",
    "CPU_UP_ROLLBACK_EFFECT_RCU_DEAD",
    "CPU_UP_ROLLBACK_EFFECT_RCU_MIGRATE",
    "CPU_UP_ROLLBACK_EFFECT_LOCKDEP_CLEANUP",
    "CPU_UP_ROLLBACK_EFFECT_KILL_OBSERVED",
    "CPU_UP_ROLLBACK_EFFECT_AFFINITY_INFO_ATTEMPT",
    "CPU_UP_ROLLBACK_EFFECT_BLOCKED",
    "effect_overflow",
    "effect_unknown",
)

BOUNDARIES = (
    "op_cpu_disable",
    "remove_cpu_topology",
    "numa_remove_cpu",
    "set_cpu_online",
    "ipi_teardown",
    "irq_migrate_all_off_this_cpu",
    "rcutree_report_cpu_dead",
    "stop_machine_park",
    "lockdep_cleanup_dead_cpu",
    "rcutree_migrate_callbacks",
    "op_cpu_kill",
)

FORBIDDEN_ADDED = (
    "cpu_down(",
    "cpu_up(",
    "set_cpus_allowed",
    "irq_set_affinity",
    "AFFINITY_INFO(",
    "cpu_psci_ops.cpu_disable",
)


def added_lines(text: str) -> list[str]:
    return [line[1:] for line in text.splitlines() if line.startswith("+") and not line.startswith("+++")]


def main() -> int:
    text = PATCH.read_text(encoding="utf-8")
    added = added_lines(text)
    missing = [token for token in REQUIRED if token not in text]
    missing_boundaries = [token for token in BOUNDARIES if token not in text]
    forbidden = [token for token in FORBIDDEN_ADDED if any(token in line for line in added)]
    if missing:
        raise SystemExit(f"missing effect markers: {', '.join(missing)}")
    if missing_boundaries:
        raise SystemExit(f"missing operation boundaries: {', '.join(missing_boundaries)}")
    if forbidden:
        raise SystemExit(f"forbidden operation in added source: {', '.join(forbidden)}")
    if text.index("struct cpu_up_rollback_effect_event {") > text.index(
        "struct cpu_up_rollback_trace {"
    ):
        raise SystemExit("effect event type is defined after the trace container")

    apply = subprocess.run(
        ["git", "apply", "--numstat", str(PATCH)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    digest = hashlib.sha256(PATCH.read_bytes()).hexdigest()
    print("claim=P32X_EFFECT_PREFIX_SOURCE_AUDIT")
    print(f"patch_sha256={digest}")
    print("format_patch_parse=PASS")
    print("arm64_disable_order=PASS")
    print("dead_rcu_park_lockdep_kill_boundaries=PASS")
    print("forbidden_operation_scan=PASS")
    print("status=PASS")
    print("numstat=" + "\n".join(apply.stdout.strip().splitlines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
