#!/usr/bin/env python3
"""Classify the exact one-shot platform-snapshot live capture."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
BASE_PATH = REPO_ROOT / "experiments/2026-08-24-mainline-a72-early-live-control/scripts/validate-runtime.py"
BASE_SHA256 = "6fb2c2f7773c49d44d1cc9aa20402823d7f30c9bfd240bb204eb93f909f353fb"
CANDIDATE = "39f801f713a76c616ed8d9282fc0a662fb34c5a766d6839e4c47c757638bae43"
RELEASE = "7.1.3-gemini-a72-platform-read"
TAG = "GEMINI_A72_PLATFORM_SNAPSHOT_V1"
COMPLETE = (
    f"{TAG} state=complete platform_calls=1 stable_samples=2 "
    "register_observations=26 retained_writes=2 retries=0 "
    "provider_snapshots=0 protected_clock_reads=0 bigidvfs_reads=0 "
    "secure_calls=0 publisher_calls=0 owner_mutations=0 cpu_requests=0"
)
VALUES = re.compile(
    rf"{TAG} valid=1 spm=(?:[0-9a-f]{{8}}/){{3}}[0-9a-f]{{8}} "
    r"mp2=(?:[0-9a-f]{8}/){2}[0-9a-f]{8} iso=[0-9a-f]{8} "
    r"dcm=[0-9a-f]{8} cci=(?:[0-9a-f]{8}/){2}[0-9a-f]{8} pwrap=[01]"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(BASE_PATH) != BASE_SHA256:
    raise SystemExit("base runtime validator changed")
SPEC = importlib.util.spec_from_file_location("platform_snapshot_runtime_base", BASE_PATH)
assert SPEC is not None and SPEC.loader is not None
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)
BASE.CANDIDATE = CANDIDATE
BASE.RELEASE = RELEASE


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
        "bigidvfs_backend_bound": "1",
        "snapshot_observer_devices": "1",
        "snapshot_observer_bound": "1",
        "physical_observer_devices": "0",
        "usb_controller_status": "okay",
        "tphy_status": "okay",
        "i2c5_status": "okay",
        "keyboard_status": "okay",
        "snapshot_log_lines": "2",
        "snapshot_failure_lines": "0",
        "platform_snapshot_request": "boot-observer-one-shot",
        "platform_snapshot_calls_expected": "1",
        "stable_samples_expected": "2",
        "register_observations_expected": "26",
        "clock_backend_read_request": "none",
        "bigidvfs_backend_read_request": "none",
        "observer_registration_request": "dt-probe-only",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise BASE.Classification("rejected-platform-snapshot", f"{key}-mismatch")
    try:
        raw_log = base64.b64decode(values.get("snapshot_log_b64", ""), validate=True)
        log = raw_log.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise BASE.Classification("rejected-platform-snapshot", "snapshot-log-malformed") from error
    tagged = [line[line.index(TAG):].strip() for line in log.splitlines() if TAG in line]
    if len(tagged) != 2 or not VALUES.fullmatch(tagged[0]) or tagged[1] != COMPLETE:
        raise BASE.Classification("rejected-platform-snapshot", "snapshot-log-contract-mismatch")
    return (
        "serviceable-platform-snapshot-complete",
        "exact-live-identity-and-one-stable-platform-snapshot",
        ledger,
        counts,
        hashlib.sha256(raw_log).hexdigest(),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, reason, ledger, counts, log_sha256 = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
    except BASE.Classification as error:
        result, reason, ledger, counts, log_sha256 = (
            error.result, error.reason, "not-classified", {}, "not-classified"
        )
    accepted = result == "serviceable-platform-snapshot-complete"
    print("runtime_gate=serviceable-platform-snapshot-pass" if accepted else "runtime_gate=rejected")
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"snapshot_log_sha256={log_sha256}")
    print(f"live_ledger_classification={ledger}")
    print(f"pure_marker_matches={counts.get('pure', 0)}")
    print(f"core_marker_matches={counts.get('core', 0)}")
    print(f"refusal_marker_matches={counts.get('refusal', 0)}")
    print("platform_snapshot_calls=1" if accepted else "platform_snapshot_calls=unknown")
    print("stable_samples=2" if accepted else "stable_samples=unknown")
    print("register_observations=26" if accepted else "register_observations=unknown")
    print("provider_snapshots=0")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("secure_calls=0")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
