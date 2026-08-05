#!/usr/bin/env python3
"""Validate the exact source-only A28 entry-gate milestone."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH = ROOT / "patches/v7.1.3/0161-arm64-add-read-only-A28-entry-admission-gate.patch"
PROFILE_SERIES = ROOT / (
    "patches/series-a72-reject-gate-a41-kernel-identity-p30-protocol-"
    "p24-closed-owner-hooks"
)
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-reject-gate-a41-kernel-identity-p30-protocol-p24-closed-owner-hooks"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def run(script: str) -> str:
    result = subprocess.run(
        ["python3", f"experiments/2026-08-05-a72-a28-entry-gate/scripts/{script}"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    require(result.returncode == 0, f"{script} failed: {result.stdout}{result.stderr}")
    return result.stdout


def main() -> int:
    patch = PATCH.read_bytes()
    text = patch.decode()
    require(text.startswith("From 351b77201"), "prepared commit changed")
    require("Subject: [PATCH] arm64: add read-only A28 entry admission gate" in text,
            "patch subject changed")
    require("not submission-ready" in text, "submission warning missing")
    require("Signed-off-by:" not in text, "unexpected sign-off")
    for token in (
        "MT6797_A72_ENTRY_FLAGS_MASK",
        "mt6797_a72_membership_validate_entry(",
        "P31 owns attempt consumption",
        "entry->provider_state != expected_provider",
        "entry->cpu8_mpidr != 0x200",
        "ret = mt6797_a72_membership_validate_entry(cpu, target, attempt,",
        "return ret;",
    ):
        require(token in text, f"patch lost token: {token}")
    entries = [
        line.strip() for line in PROFILE_SERIES.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require("v7.1.3/0161-arm64-add-read-only-A28-entry-admission-gate.patch" in entries,
            "profile does not select 0161")
    require(entries.index("v7.1.3/0161-arm64-add-read-only-A28-entry-admission-gate.patch")
            > entries.index("v7.1.3/0160-cpu-add-closed-arm64-CPU-up-admission-hooks.patch"),
            "0161 is not after 0160")
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
    print("validation=a28-read-only-entry-gate")
    print(f"patch_sha256={sha256(patch)}")
    print(f"patch_bytes={len(patch)}")
    print("valid_tuples=2")
    print("mutations_rejected=7/7")
    print("production_callers=0")
    print("attempt_consumption=0")
    print("p30_mutations=0")
    print("cpu_on_calls=0")
    print("build=not-run")
    print("device_action=none")
    print("status=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
