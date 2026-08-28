#!/usr/bin/env python3
"""Validate the repository-side CPU8 admission candidate definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
require(contract["prepared_source_state"] ==
        "9fd302b315e0da6860d00295b4865d732a72e60b58d0ec1fd3f80631b8c4ff10",
        "exact post-0412 source state")
require(contract["prepared_source_integrity"] ==
        "01f388011bf406bfc56c8a8c7b60ea5b2ee769c6f2d608a471f1cce797eb4897",
        "exact post-0412 source integrity")
require(contract["physical_boots_budget"] == 1, "one physical boot")
require(contract["target_cpu"] == 8 and contract["excluded_cpu"] == 9,
        "CPU8 only")
require(contract["device_action"] is False, "definition has no device action")
require(contract["boot_candidate"] is False, "definition is not a candidate")
series = ROOT / "patches/series"
require(sha256(series) == contract["parent_series_sha256"], "parent series hash")
require(series.read_text(encoding="utf-8").splitlines()[-1].endswith(
        "0412-soc-mediatek-test-one-shot-CPU8-admission-controller.patch"),
        "parent series tail")
for path in (
    EXPERIMENT / "kernel/mediatek,mt6797-a72-admission-controller.yaml",
    EXPERIMENT / "kernel/mt6797-gemini-pda-a72-admission.dts",
    EXPERIMENT / "scripts/source_edits.py",
    EXPERIMENT / "scripts/validate_source.py",
    EXPERIMENT / "scripts/generate-patches.py",
    EXPERIMENT / "scripts/generate-on-buildbox",
):
    require(path.is_file() and not path.is_symlink(), f"exact file {path.name}")
source_validator = (
    EXPERIMENT / "scripts/validate_source.py"
).read_text(encoding="utf-8")
require(
    '"mediatek,platform-state = <&a72_platform_state>;": 2' in source_validator,
    "binder and controller share the platform-state supplier",
)
patch_generator = (
    EXPERIMENT / "scripts/generate-patches.py"
).read_text(encoding="utf-8")
require(
    '"Enable the binder, controller, and their three owned sources in a\\n"'
    in patch_generator,
    "generated DT commit body is wrapped for strict checkpatch",
)
subprocess.run(
    ["python3", "-m", "py_compile",
     str(EXPERIMENT / "scripts/source_edits.py"),
     str(EXPERIMENT / "scripts/validate_source.py"),
     str(EXPERIMENT / "scripts/generate-patches.py")],
    check=True,
)
print("validation=a72-cpu8-admission-candidate-definition")
print("physical_boots_budget=1")
print("target_cpu=8")
print("excluded_cpu=9")
print("standalone_observer_nodes=0")
print("native_vm_build=none")
print("device_action=none")
print("boot_candidate=false")
print("result=pass")
