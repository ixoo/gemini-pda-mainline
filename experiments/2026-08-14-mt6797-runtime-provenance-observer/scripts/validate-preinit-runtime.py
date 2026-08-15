#!/usr/bin/env python3
"""Classify a direct-USB sample from the exact pre-init recovery candidate."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
PARENT = SCRIPT_DIR / "validate-runtime.py"
PARENT_SHA256 = "ab754807135d3c9ab05d63cacbd35870c0ca18d0235b7b6ad20431c8d9b402fe"
EXPECTED_KERNEL = "3.18.79-gemini-provenance-preinit+"
EXPECTED_CANDIDATE = "99414cdecc4e031b12b93114b355fb3d44366d6e7b5092cb4f5f9132755d61c7"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(PARENT) != PARENT_SHA256:
    raise SystemExit("error: pinned runtime classifier changed")
spec = importlib.util.spec_from_file_location("preinit_runtime_parent", PARENT)
if spec is None or spec.loader is None:
    raise SystemExit("error: cannot load pinned runtime classifier")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
runtime.EXPECTED_KERNEL = EXPECTED_KERNEL
runtime.EXPECTED_CANDIDATE = EXPECTED_CANDIDATE

BEGIN = runtime.BEGIN
END = runtime.END
Classification = runtime.Classification
classify = runtime.classify


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, reason = classify(args.capture)
        code = 0
    except Classification as outcome:
        result, reason, code = outcome.result, outcome.reason, outcome.code
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=vendor-ppm-eem-lifecycle-publication-only")
    return code


if __name__ == "__main__":
    sys.exit(main())
