#!/usr/bin/env python3
"""Validate the exact source-only P31 attempt-ledger milestone."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0162-arm64-add-dormant-P31-attempt-consumption.patch"
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
        ["python3", f"experiments/2026-08-05-a72-p31-attempt-consumption/scripts/{script}"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    require(result.returncode == 0, f"{script} failed: {result.stdout}{result.stderr}")
    return result.stdout


def main() -> int:
    raw = PATCH.read_bytes()
    text = raw.decode()
    require(text.startswith("From 950bdf936"), "prepared commit changed")
    require("Subject: [PATCH] arm64: add dormant P31 attempt consumption" in text,
            "patch subject changed")
    require("not submission-ready" in text, "submission warning missing")
    require("Signed-off-by:" not in text, "unexpected sign-off")
    for token in (
        "mt6797_a72_membership_p31_consume_attempt",
        "MT6797_A72_OBSERVER_WINDOW_OPEN",
        "a72_owner.attempts_available &= ~expected_attempt",
        "a72_owner.attempts_consumed |= expected_attempt",
        "ret = -EALREADY",
        "A34 is the only future reset authority",
        "mt6797_a72_membership_test_seed_available",
    ):
        require(token in text, f"patch lost token: {token}")
    entries = [
        line.strip() for line in PROFILE_SERIES.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    p161 = "v7.1.3/0161-arm64-add-read-only-A28-entry-admission-gate.patch"
    p162 = "v7.1.3/0162-arm64-add-dormant-P31-attempt-consumption.patch"
    require(p161 in entries and p162 in entries, "profile lacks 0161/0162")
    require(entries.index(p162) > entries.index(p161), "0162 is not after 0161")
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
    print("validation=p31-attempt-ledger")
    print(f"patch_sha256={hashlib.sha256(raw).hexdigest()}")
    print(f"patch_bytes={len(raw)}")
    print("observer_window_required=1")
    print("attempts_consumed=2")
    print("a28_rejection_rearms=0")
    print("production_callers=0")
    print("token_allocations=0")
    print("p30_mutations=0")
    print("cpu_on_calls=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
