#!/usr/bin/env python3
"""Classify the exact read-free BigiDVFS-backend live capture."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BASE_PATH = REPO_ROOT / "experiments/2026-08-24-mainline-a72-early-live-control/scripts/validate-runtime.py"
BASE_SHA256 = "6fb2c2f7773c49d44d1cc9aa20402823d7f30c9bfd240bb204eb93f909f353fb"
CANDIDATE = "0b17da983293f68f227931c964021b43efb1cdd57b4d0cf4db3bd70312f6092a"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(BASE_PATH) != BASE_SHA256:
    raise SystemExit("base runtime validator changed")
SPEC = importlib.util.spec_from_file_location("bigidvfs_runtime_base", BASE_PATH)
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
    result, _, ledger, counts = BASE.classify_text(text)
    if result != "serviceable-stage27-control-pass":
        raise AssertionError("base serviceability classification changed")
    values = scalar_values(text)
    expected = {
        "platform_state_devices": "1",
        "platform_state_bound": "1",
        "clock_backend_devices": "1",
        "clock_backend_bound": "1",
        "bigidvfs_backend_devices": "1",
        "physical_observer_devices": "0",
        "usb_controller_status": "okay",
        "tphy_status": "okay",
        "i2c5_status": "okay",
        "keyboard_status": "okay",
        "platform_snapshot_request": "none",
        "clock_backend_read_request": "none",
        "bigidvfs_backend_read_request": "none",
        "observer_registration_request": "none",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise BASE.Classification("rejected-bigidvfs-backend-isolation", f"{key}-mismatch")
    bound = values.get("bigidvfs_backend_bound")
    if bound not in {"0", "1"}:
        raise BASE.Classification("rejected-bigidvfs-backend-isolation", "bigidvfs-backend-bound-malformed")
    outcome = "serviceable-bigidvfs-backend-bound" if bound == "1" else "serviceable-bigidvfs-backend-unbound"
    return outcome, "exact-live-identity-and-bigidvfs-backend-isolation", ledger, counts, bound


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
    accepted = result.startswith("serviceable-bigidvfs-backend-")
    print("runtime_gate=serviceable-bigidvfs-backend-stage27-pass" if accepted else "runtime_gate=rejected")
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print("platform_state_bound=1" if accepted else "platform_state_bound=unknown")
    print("clock_backend_bound=1" if accepted else "clock_backend_bound=unknown")
    print(f"bigidvfs_backend_bound={bound}")
    print(f"live_ledger_classification={ledger}")
    print(f"pure_marker_matches={counts.get('pure', 0)}")
    print(f"core_marker_matches={counts.get('core', 0)}")
    print(f"refusal_marker_matches={counts.get('refusal', 0)}")
    print("stage27_serviceability_dt_state=exact")
    print("platform_snapshot_requested=no")
    print("clock_backend_read_requested=no")
    print("bigidvfs_backend_read_requested=no")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
