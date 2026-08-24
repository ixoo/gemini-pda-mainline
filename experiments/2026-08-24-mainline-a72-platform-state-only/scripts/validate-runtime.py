#!/usr/bin/env python3
"""Classify the exact platform-state-only live capture."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BASE_PATH = REPO_ROOT / "experiments/2026-08-24-mainline-a72-early-live-control/scripts/validate-runtime.py"
BASE_SHA256 = "6fb2c2f7773c49d44d1cc9aa20402823d7f30c9bfd240bb204eb93f909f353fb"
CANDIDATE = "012f7eac6884e65baab075ef286929f610a63f2ea065eba45865bd046492a23f"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(BASE_PATH) != BASE_SHA256:
    raise SystemExit("base runtime validator changed")
SPEC = importlib.util.spec_from_file_location("base_runtime_validator", BASE_PATH)
assert SPEC is not None and SPEC.loader is not None
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
BASE.CANDIDATE = CANDIDATE


def scalar_values(text: str) -> dict[str, str]:
    start = text.index(BASE.BEGIN) + len(BASE.BEGIN)
    finish = text.index(BASE.END, start)
    section = text[start:finish].replace("\r", "")
    marker_start = section.index(BASE.MARKERS_BEGIN)
    marker_finish = section.index(BASE.MARKERS_END) + len(BASE.MARKERS_END)
    section = section[:marker_start] + section[marker_finish:]
    values: dict[str, str] = {}
    for raw in section.splitlines():
        line = raw.strip()
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def classify(text: str) -> tuple[str, str, str, dict[str, int], str]:
    result, reason, ledger, counts = BASE.classify_text(text)
    if result != "serviceable-stage27-control-pass":
        raise AssertionError("base serviceability classification changed")
    values = scalar_values(text)
    expected = {
        "platform_state_devices": "1",
        "clock_backend_devices": "0",
        "bigidvfs_backend_devices": "0",
        "physical_observer_devices": "0",
        "platform_snapshot_request": "none",
        "observer_registration_request": "none",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise BASE.Classification("rejected-provider-isolation", f"{key}-mismatch")
    bound = values.get("platform_state_bound")
    if bound not in {"0", "1"}:
        raise BASE.Classification("rejected-provider-isolation", "platform-state-bound-malformed")
    outcome = "serviceable-platform-state-bound" if bound == "1" else "serviceable-platform-state-unbound"
    return outcome, "exact-live-identity-and-provider-isolation", ledger, counts, bound


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, reason, ledger, counts, bound = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
    except BASE.Classification as error:
        result, reason, ledger, counts, bound = error.result, error.reason, "not-classified", {}, "unknown"
    print("runtime_gate=serviceable-platform-state-only-pass" if result.startswith("serviceable-platform-state-") else "runtime_gate=rejected")
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"platform_state_bound={bound}")
    print(f"live_ledger_classification={ledger}")
    print(f"pure_marker_matches={counts.get('pure', 0)}")
    print(f"core_marker_matches={counts.get('core', 0)}")
    print(f"refusal_marker_matches={counts.get('refusal', 0)}")
    print("platform_snapshot_requested=no")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if result.startswith("serviceable-platform-state-") else 3


if __name__ == "__main__":
    raise SystemExit(main())
