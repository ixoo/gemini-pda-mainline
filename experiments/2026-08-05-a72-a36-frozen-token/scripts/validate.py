#!/usr/bin/env python3
"""Validate the exact source-only A36 frozen-token milestone."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0163-arm64-mint-frozen-A72-transaction-tokens.patch"
PROFILE_SERIES = ROOT / (
    "patches/series-a72-reject-gate-a41-kernel-identity-p30-protocol-"
    "p24-closed-owner-hooks"
)
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-kernel-identity-p30-protocol-p24-closed-owner-hooks"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(script: str) -> str:
    result = subprocess.run(
        ["python3", f"experiments/2026-08-05-a72-a36-frozen-token/scripts/{script}"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    require(result.returncode == 0, f"{script} failed: {result.stdout}{result.stderr}")
    return result.stdout


def main() -> int:
    raw = PATCH.read_bytes()
    text = raw.decode()
    require(text.startswith("From 70b98c307"), "prepared commit changed")
    require("Subject: [PATCH] arm64: mint frozen A72 transaction tokens" in text,
            "patch subject changed")
    require("not submission-ready" in text, "submission warning missing")
    require("Signed-off-by:" not in text, "unexpected sign-off")
    for token in (
        "mt6797_a72_ready_token_validate",
        "mt6797-a53-a72-a41-v7",
        "a72_transition_lock",
        "mt6797_a72_membership_p31_consume_attempt",
        "mt6797_a72_membership_validate_entry",
        "mt6797_a72_membership_mint_up_token",
        "MT6797_A72_PHASE_FROZEN",
        "ARM64_LATE_CPU_STARTUP_OP_CPU8_UP",
        "ARM64_LATE_CPU_STARTUP_OP_CPU9_UP",
        "ARM64_LATE_CPU_STARTUP_ABI",
        "p30_token.plan_identity",
        "MT6797_A72_BUDGET_AVAILABLE",
    ):
        require(token in text, f"patch lost token: {token}")
    require("arm64_late_cpu_startup_prepare" not in text,
            "A36 slice armed P30 unexpectedly")
    require("cpu_on(" not in text and "psci_ops.cpu_on" not in text,
            "A36 slice issued CPU_ON unexpectedly")
    entries = [
        line.strip() for line in PROFILE_SERIES.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    required = [
        "v7.1.3/0161-arm64-add-read-only-A28-entry-admission-gate.patch",
        "v7.1.3/0162-arm64-add-dormant-P31-attempt-consumption.patch",
        "v7.1.3/0163-arm64-mint-frozen-A72-transaction-tokens.patch",
    ]
    for entry in required:
        require(entry in entries, f"profile lacks {entry}")
    require(entries.index(required[2]) > entries.index(required[1]) > entries.index(required[0]),
            "A36 patch order changed")
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    require(PROFILE in profiles, "profile missing from manifest")
    require(profiles[PROFILE]["patch_series"] == str(PROFILE_SERIES.relative_to(ROOT)),
            "manifest profile series changed")
    oracle = run("oracle.py")
    mutations = run("test_mutations.py")
    require("status=PASS" in oracle and "status=PASS" in mutations,
            "bounded evidence did not pass")
    canonical = subprocess.run(
        ["./scripts/validate-manifest-series"], cwd=ROOT,
        text=True, capture_output=True, check=False,
    )
    require(canonical.returncode == 0, canonical.stdout + canonical.stderr)
    print("validation=a36-frozen-token")
    print(f"patch_sha256={hashlib.sha256(raw).hexdigest()}")
    print(f"patch_bytes={len(raw)}")
    print("ready_identity=exact")
    print("transition_lock_scope=p31-through-mint")
    print("frozen_tokens=2")
    print("a36_hardware_prestate=not-run")
    print("p30_armed=0")
    print("cpu_on_calls=0")
    print("production_callers=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
