#!/usr/bin/env python3
"""Audit the P32R owner-ledger handoff as source evidence only."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0189-arm64-hand-P32R-into-owner-ledger.patch"

REQUIRED = (
    "MT6797_A72_P32R_HANDOFF_ABI",
    "MT6797_A72_P32R_EFFECT_MASK",
    "MT6797_A72_P32R_FAULT_ROLLBACK_RECORDED",
    "MT6797_A72_P32R_FAULT_ROLLBACK_LOST",
    "struct mt6797_a72_p32r_ledger_handoff",
    "p32r_valid",
    "p32r_side_effects",
    "callback_complete",
    "effect_complete",
    "mt6797_a72_p32r_capture_locked",
    "mt6797_a72_p32r_lose_locked",
    "mt6797_a72_p32r_retire_locked",
    "MT6797_A72_PROVIDER_FAULT_UNKNOWN",
    "a72_owner.retired_mask",
)

FORBIDDEN_ADDED = (
    "cpu_down(",
    "cpu_up(",
    "CPU_OFF",
    "CPU_ON",
    "AFFINITY_INFO(",
    "set_cpus_allowed",
    "mt6797_a72_provider_release(",
    "mt6797_a72_provider_acquire(",
    "i2c_",
    "regmap_",
    "writel(",
    "readl(",
)


def added_lines(text: str) -> list[str]:
    return [
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def main() -> int:
    text = PATCH.read_text(encoding="utf-8")
    added = added_lines(text)
    missing = [token for token in REQUIRED if token not in text]
    forbidden = [
        token for token in FORBIDDEN_ADDED if any(token in line for line in added)
    ]
    if missing:
        raise SystemExit(f"missing P32R markers: {', '.join(missing)}")
    if forbidden:
        raise SystemExit(f"forbidden operation in added source: {', '.join(forbidden)}")
    if text.index("mt6797_a72_p32r_capture_locked") > text.index(
        "mt6797_a72_membership_consume_p32"
    ):
        raise SystemExit("owner handoff helpers appear after their consumer")
    if text.index("MT6797_A72_P32R_FAULT_ROLLBACK_RECORDED") > text.index(
        "MT6797_A72_PROVIDER_FAULT_UNKNOWN"
    ):
        raise SystemExit("provider fault disposition precedes recorded handoff")
    if text.index("mt6797_a72_p32r_capture_locked(&a72_owner.active, trace") > text.index(
        "mt6797_a72_p32r_retire_locked(&a72_owner.active)"
    ):
        raise SystemExit("generation retirement precedes ledger capture")

    apply = subprocess.run(
        ["git", "apply", "--numstat", str(PATCH)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    digest = hashlib.sha256(PATCH.read_bytes()).hexdigest()
    print("claim=P32R_OWNER_LEDGER_SOURCE_AUDIT")
    print(f"patch_sha256={digest}")
    print("format_patch_parse=PASS")
    print("owner_only_handoff=PASS")
    print("snapshot_and_provider_fault_boundary=PASS")
    print("retire_after_capture=PASS")
    print("forbidden_operation_scan=PASS")
    print("status=PASS")
    print("numstat=" + "\n".join(apply.stdout.strip().splitlines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
