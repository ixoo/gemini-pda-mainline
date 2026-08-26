#!/usr/bin/env python3
"""Validate the CPU8 active-transition audit definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


EXP = Path(__file__).resolve().parent.parent
ROOT = EXP.parents[1]
contract = json.loads((EXP / "contract.json").read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


require(contract["schema"] == 1, "schema")
require(contract["experiment"] == EXP.name, "experiment")
require(sha256(ROOT / "patches/series") == contract["canonical_series_sha256"],
        "canonical series")
require(len((ROOT / "patches/series").read_text(encoding="utf-8").splitlines()) ==
        contract["canonical_series_entries"], "series entries")
require(sha256(ROOT / "kernel/manifest.json") == contract["manifest_sha256"],
        "manifest")
runtime = ROOT / (
    "experiments/2026-08-26-mainline-a72-cpu-status-mask-repair/results/"
    "runtime-attempt-1-platform-provider-clock-complete-20260826.txt"
)
require(sha256(runtime) == contract["qualified_runtime_receipt_sha256"],
        "qualified runtime")
require(all(value == 0 for value in contract["production_callers"].values()),
        "production callers remain absent")
require(contract["selected_contract"] == {
    "cpu": 8,
    "cpu9_offline": True,
    "attempts": 1,
    "cpu_requests": 1,
    "cpu_off_requests": 0,
    "retries": 0,
    "cpu_on_wait_ms": 10000,
    "recovery_timeout_ms": 15000,
    "preisolation_inverse": ["provider", "p27"],
    "postisolation_policy": "retain-power-and-reset",
    "production_membership_publication": False,
    "native_vm_build": False,
}, "selected contract")
require(contract["selected_contract"]["recovery_timeout_ms"] >
        contract["selected_contract"]["cpu_on_wait_ms"], "timeout ordering")
for name, expected in contract["tooling_sha256"].items():
    require(expected != "pending", f"pending tool hash: {name}")
    require(sha256(EXP / "scripts" / name) == expected, f"tool hash: {name}")
require(sha256(EXP / "results/source-audit-20260826.txt") ==
        contract["source_audit_receipt_sha256"], "source audit receipt")
require(sha256(EXP / "results/decision-matrix.tsv") ==
        contract["decision_matrix_sha256"], "decision matrix")
model = subprocess.run(
    [str(EXP / "scripts/test_transition_model.py")],
    check=True,
    capture_output=True,
    text=True,
).stdout
for token in (
    "success_checkpoints=18", "injected_stage_failures=9",
    "watchdog_arm_failures_rejected=1",
    "preisolation_failures_rolled_back=2",
    "postisolation_failures_retained=6", "cpu9_prefix_repeat_rejections=3",
    "cpu_requests_maximum=1", "cpu_off_requests=0", "retries=0",
    "device_action=none", "result=pass",
):
    require(token in model, f"model token: {token}")
readme = (EXP / "README.md").read_text(encoding="utf-8")
design = (EXP / "DESIGN.md").read_text(encoding="utf-8")
for token in (
    "zero production callers", "unconditionally returns `-EAGAIN`",
    "P27 and P28 validate typed records", "active transition executor",
):
    require(token in readme, f"README token: {token}")
for token in (
    "15-second hardware watchdog", "exactly one standard PSCI `CPU_ON`",
    "do not set isolation", "CPU9", "No remote file",
):
    require(token in design, f"DESIGN token: {token}")
require("/Users/" not in readme + design, "no host path")
require(contract["kernel_build"] is False, "no kernel build")
require(contract["device_action"] is False, "no device action")
print("definition_validation=pass")
print("configuration_only_candidate=not_reachable")
print("selected_next=default_off_injected_active_transition_executor")
print("cpu_requests_maximum=1")
print("cpu_off_requests=0")
print("native_vm_build=none")
print("device_action=none")
