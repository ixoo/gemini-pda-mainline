#!/usr/bin/env python3
"""Audit the P32A callback-prefix patch without claiming a kernel build."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0187-arm64-capture-P32A-rollback-prefix.patch"

REQUIRED = (
    "CPU_UP_ROLLBACK_MAX_EVENTS",
    "struct cpu_up_rollback_event",
    "struct cpu_up_rollback_trace",
    "cpuhp_record_rollback_event",
    "nested_valid",
    "rollback_trace = &st->rollback_trace",
    "outer_reset = 1",
    "reverse_complete = !rollback_ret",
    "arch_cpu_up_rollback_complete(cpu, ret,",
)

FORBIDDEN_ADDED = (
    "cpu_down(",
    "set_cpus_allowed",
    "irq_set_affinity",
    "set_cpu_online",
    "set_cpu_present",
    "topology_remove",
    "numa_remove",
    "smp_call_function",
)


def added_lines(text: str) -> list[str]:
    return [line[1:] for line in text.splitlines() if line.startswith("+") and not line.startswith("+++")]


def main() -> int:
    text = PATCH.read_text(encoding="utf-8")
    added = added_lines(text)
    missing = [token for token in REQUIRED if token not in text]
    forbidden = [token for token in FORBIDDEN_ADDED if any(token in line for line in added)]
    if missing:
        raise SystemExit(f"missing required source markers: {', '.join(missing)}")
    if forbidden:
        raise SystemExit(f"forbidden source effect markers: {', '.join(forbidden)}")

    record_calls = sum(line.count("cpuhp_record_rollback_event(") for line in added)
    if record_calls < 5:  # helper definition plus four callback paths
        raise SystemExit(f"callback record coverage too small: {record_calls}")
    if "rollback_trace = NULL" not in text:
        raise SystemExit("configuration-off nullable trace path is missing")
    if "&st->rollback_trace))" in text:
        raise SystemExit("generic rollback call still dereferences conditional state")

    apply = subprocess.run(
        ["git", "apply", "--numstat", str(PATCH)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    digest = hashlib.sha256(PATCH.read_bytes()).hexdigest()
    print("claim=P32A_CALLBACK_PREFIX_SOURCE_AUDIT")
    print(f"patch_sha256={digest}")
    print("format_patch_parse=PASS")
    print(f"callback_record_sites={record_calls - 1}")
    print("nested_outer_reverse_markers=PASS")
    print("config_off_nullable_trace=PASS")
    print("forbidden_effect_scan=PASS")
    print("status=PASS")
    print("numstat=" + "\n".join(apply.stdout.strip().splitlines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
