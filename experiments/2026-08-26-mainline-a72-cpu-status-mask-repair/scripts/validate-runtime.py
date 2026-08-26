#!/usr/bin/env python3
"""Retarget the exact movement classifier to the CPU-status-mask candidate."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_PATH = REPO_ROOT / (
    "experiments/2026-08-26-mainline-a72-platform-movement-attribution/"
    "scripts/validate-runtime.py"
)
SOURCE_SHA256 = "518262924b0b50ad9a45af57eeb4c5a54ebd7f6b08972c69c14b66760f31ee6e"
CANDIDATE = "6219357a1c505a8c08ad33f97940aed4a9c73bf37a691a31c66ebc63559fe4f7"
RELEASE = "7.1.3-gemini-a72-cpumask"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(SOURCE_PATH) != SOURCE_SHA256:
    raise SystemExit("source runtime validator changed")
SPEC = importlib.util.spec_from_file_location("cpu_status_mask_runtime_source", SOURCE_PATH)
assert SPEC is not None and SPEC.loader is not None
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)

SOURCE.CANDIDATE = CANDIDATE
SOURCE.RELEASE = RELEASE
SOURCE.PARENT.CANDIDATE = CANDIDATE
SOURCE.PARENT.RELEASE = RELEASE
SOURCE.PARENT.SOURCE.CANDIDATE = CANDIDATE
SOURCE.PARENT.SOURCE.RELEASE = RELEASE
SOURCE.BASE.CANDIDATE = CANDIDATE
SOURCE.BASE.RELEASE = RELEASE

BASE = SOURCE.BASE
PARENT = SOURCE.PARENT
FAILURE_PREFIX = SOURCE.FAILURE_PREFIX
MOVEMENT_FIELDS = SOURCE.MOVEMENT_FIELDS
MOVEMENT = SOURCE.MOVEMENT
Decision = SOURCE.Decision
classify = SOURCE.classify


def main() -> int:
    # The inherited gate name deliberately remains stable so all predecessor
    # serviceable branches stay comparable; candidate and release are exact.
    return SOURCE.main()


if __name__ == "__main__":
    raise SystemExit(main())
