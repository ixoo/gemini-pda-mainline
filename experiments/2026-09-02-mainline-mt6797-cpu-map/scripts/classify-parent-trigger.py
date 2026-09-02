#!/usr/bin/env python3
"""Retarget the proven dual-A72 trigger classifier to the CPU-map candidate."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "b10dcf6a1f7d495b012e856d45ae04047a2ad70be5d8280724336adf9c82f536"
OLD_CANDIDATE = "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e"
NEW_CANDIDATE = "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
SOURCE = ROOT / (
    "experiments/2026-08-31-mainline-a72-cpu9-same-boot-successor/"
    "scripts/classify-completion-lock-repair-attempt.py"
)


def reject(reason: str) -> int:
    print("runtime_classification=rejected")
    print(f"runtime_reason={reason}")
    print("trigger_attempts=unknown")
    print("cpu8_request_maximum=1")
    print("cpu9_request_maximum=1")
    print("cpu_off_requests=0")
    print("retries=0")
    print("native_reboot_requested=no")
    return 3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrigger", required=True, type=Path)
    parser.add_argument("--trigger", required=True, type=Path)
    args = parser.parse_args()

    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        return reject("source-trigger-classifier-changed")
    text = args.pretrigger.read_text(encoding="utf-8")
    if text.count(NEW_CANDIDATE) != 1 or OLD_CANDIDATE in text:
        return reject("installed-full-candidate-mismatch")
    normalized = text.replace(NEW_CANDIDATE, OLD_CANDIDATE, 1)

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix="gemini-mt6797-pretrigger-"
    ) as temporary:
        temporary.write(normalized)
        temporary.flush()
        result = subprocess.run(
            [
                sys.executable,
                str(SOURCE),
                "--pretrigger",
                temporary.name,
                "--trigger",
                str(args.trigger),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
