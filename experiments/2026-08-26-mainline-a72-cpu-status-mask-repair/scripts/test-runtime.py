#!/usr/bin/env python3
"""Test the retargeted CPU-status-mask runtime classifier."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_TEST = REPO_ROOT / (
    "experiments/2026-08-26-mainline-a72-platform-movement-attribution/"
    "scripts/test-runtime.py"
)
SOURCE_TEST_SHA256 = "a618f51cee510f5311c1b8b089c398466ec7a06bd949e9fef1586aa3a6bc48a8"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if hashlib.sha256(SOURCE_TEST.read_bytes()).hexdigest() != SOURCE_TEST_SHA256:
    raise SystemExit("source runtime tests changed")
SOURCE = load("cpu_status_mask_source_runtime_tests", SOURCE_TEST)
MODULE = load("cpu_status_mask_runtime", SCRIPT_DIR / "validate-runtime.py")


def retarget(text: str) -> str:
    return text.replace(SOURCE.MODULE.CANDIDATE, MODULE.CANDIDATE).replace(
        SOURCE.MODULE.RELEASE, MODULE.RELEASE
    )


branches = (
    SOURCE.capture(),
    SOURCE.capture(valid=0, after=1, ret=-5, abi=0, generation=0),
    SOURCE.capture(valid=0, after=0),
    SOURCE.capture(valid=0, after=1, generation=2),
    SOURCE.capture(stage="platform-movement"),
    SOURCE.capture(stage="provider"),
    SOURCE.capture(stage="before-clock"),
)
for candidate in branches:
    decision = MODULE.classify(retarget(candidate))
    assert decision.classification.startswith("serviceable-")

for candidate in (
    retarget(SOURCE.capture()).replace(MODULE.CANDIDATE, "0" * 64),
    retarget(SOURCE.capture()).replace(MODULE.RELEASE, "wrong-release"),
):
    try:
        MODULE.classify(candidate)
    except MODULE.BASE.Classification:
        pass
    else:
        raise AssertionError("unsafe retargeted identity mutation accepted")

print("source_runtime_suite=pass")
print(f"retargeted_serviceable_branches={len(branches)}")
print("retargeted_identity_mutations_rejected=2")
print("result=pass")
