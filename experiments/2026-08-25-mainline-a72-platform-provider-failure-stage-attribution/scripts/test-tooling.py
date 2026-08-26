#!/usr/bin/env python3
"""Exercise generation and reject stage-attribution mutations."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
PARENT = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-protected-clock-third-read/source"
FILES = (
    "mt6797-a72-platform-provider-clock-observer.c",
    "mt6797-a72-platform-provider-clock-observer-internal.h",
    "mt6797-a72-platform-provider-clock-observer-test.c",
)


def run_validator(root: Path, phase: str) -> int:
    return subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_source.py"),
         "--source-root", str(root), "--phase", phase],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    ).returncode


with tempfile.TemporaryDirectory(prefix="a72-failure-stage-test-") as temp:
    root = Path(temp)
    soc = root / "drivers/soc/mediatek"
    soc.mkdir(parents=True)
    for name in FILES:
        shutil.copyfile(PARENT / name, soc / name)
    subprocess.run(
        ["python3", str(SCRIPT_DIR / "source_edits.py"),
         "--source-root", str(root), "--phase", "production"], check=True,
    )
    if run_validator(root, "production") != 0:
        raise SystemExit("FAIL: valid production source rejected")
    subprocess.run(
        ["python3", str(SCRIPT_DIR / "source_edits.py"),
         "--source-root", str(root), "--phase", "tests"], check=True,
    )
    if run_validator(root, "tests") != 0:
        raise SystemExit("FAIL: valid test source rejected")

    mutations = (
        (FILES[0], "MT6797_A72_PPC_FAILURE_PLATFORM;", "MT6797_A72_PPC_FAILURE_PROVIDER;"),
        (FILES[0], "MT6797_A72_PPC_FAILURE_BEFORE_CLOCK;", "MT6797_A72_PPC_FAILURE_NONE;"),
        (FILES[0], "stage=%s ret=%d", "ret=%d stage=%s"),
        (FILES[0], "ops->clock(context, clock, &snapshot->clock)", "ops->clock(context, clock, &snapshot->clock) + ops->clock(context, clock, &snapshot->clock)"),
        (FILES[1], "MT6797_A72_PPC_FAILURE_DEPENDENCY", "MT6797_A72_PPC_FAILURE_PLATFORM"),
        (FILES[2], "failure_stage, MT6797_A72_PPC_FAILURE_PROVIDER", "failure_stage, MT6797_A72_PPC_FAILURE_PLATFORM"),
    )
    rejected = 0
    for name, old, new in mutations:
        path = soc / name
        original = path.read_text(encoding="utf-8")
        if original.count(old) < 1:
            raise SystemExit(f"fixture anchor changed: {old}")
        path.write_text(original.replace(old, new, 1), encoding="utf-8")
        if run_validator(root, "tests") == 0:
            raise SystemExit(f"FAIL: accepted tooling mutation: {old}")
        rejected += 1
        path.write_text(original, encoding="utf-8")

with tempfile.TemporaryDirectory(prefix="a72-failure-stage-package-") as temp:
    package = Path(temp) / "package"
    subprocess.run(
        ["python3", str(SCRIPT_DIR / "generate-patches.py"),
         "--output", str(package)], check=True, stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate_patch.py"),
         "--patch-dir", str(package)], check=True, stdout=subprocess.DEVNULL,
    )

print("tooling_validation=pass")
print("generated_patch_count=2")
print(f"tooling_rejected_mutations={rejected}")
print("native_vm_build=false")
print("device_action=none")
