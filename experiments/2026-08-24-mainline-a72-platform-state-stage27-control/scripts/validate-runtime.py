#!/usr/bin/env python3
"""Classify the exact Stage-27 minimum platform-state live capture."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BASE_PATH = REPO_ROOT / "experiments/2026-08-24-mainline-a72-platform-state-only/scripts/validate-runtime.py"
BASE_SHA256 = "73e43ae3e4ec1df35f59b88caabaf17ab4b2f54ba1b5cfc51a7cff982a4d060d"
CANDIDATE = "662e86846e783cf29b13c388f9e88217fe7bd32933eef4f32df86e44def0b16b"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(BASE_PATH) != BASE_SHA256:
    raise SystemExit("base runtime validator changed")
SPEC = importlib.util.spec_from_file_location("platform_runtime_validator", BASE_PATH)
assert SPEC is not None and SPEC.loader is not None
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
BASE.CANDIDATE = CANDIDATE
BASE.BASE.CANDIDATE = CANDIDATE


def scalar_values(text: str) -> dict[str, str]:
    return BASE.scalar_values(text)


def classify(text: str) -> tuple[str, str, str, dict[str, int], str]:
    result, reason, ledger, counts, bound = BASE.classify(text)
    values = scalar_values(text)
    expected = {
        "usb_controller_status": "okay",
        "tphy_status": "okay",
        "i2c5_status": "okay",
        "keyboard_status": "okay",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise BASE.BASE.Classification("rejected-stage27-serviceability-state", f"{key}-mismatch")
    return result, reason, ledger, counts, bound


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, reason, ledger, counts, bound = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
    except BASE.BASE.Classification as error:
        result, reason, ledger, counts, bound = error.result, error.reason, "not-classified", {}, "unknown"
    print("runtime_gate=serviceable-platform-state-stage27-pass" if result.startswith("serviceable-platform-state-") else "runtime_gate=rejected")
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"platform_state_bound={bound}")
    print(f"live_ledger_classification={ledger}")
    print(f"pure_marker_matches={counts.get('pure', 0)}")
    print(f"core_marker_matches={counts.get('core', 0)}")
    print(f"refusal_marker_matches={counts.get('refusal', 0)}")
    print("stage27_serviceability_dt_state=exact")
    print("platform_snapshot_requested=no")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if result.startswith("serviceable-platform-state-") else 3


if __name__ == "__main__":
    raise SystemExit(main())
