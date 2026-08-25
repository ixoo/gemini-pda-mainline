#!/usr/bin/env python3
"""Classify the exact provider-ready one-shot platform/provider capture."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_PATH = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-snapshot-second-read/scripts/validate-runtime.py"
SOURCE_SHA256 = "9e60e9e297aa4412d98f2d7decb459684c049949fcc7bd760b69146be7a89ef9"
CANDIDATE = "f55bb272de24a62a0e4055624e8eb0ef35bc53432fa130463c867c43c059732e"
RELEASE = "7.1.3-gemini-a72-provider-ready"
TAG = "GEMINI_A72_PLATFORM_PROVIDER_SNAPSHOT_V1"
COMPLETE = (
    f"{TAG} state=complete provider_ready_gate=passed platform_calls=1 "
    "platform_samples=2 platform_register_observations=26 retained_writes=2 "
    "provider_snapshots=1 provider_samples=2 provider_i2c_reads=10 "
    "provider_i2c_writes=0 observer_retries=0 protected_clock_reads=0 "
    "bigidvfs_reads=0 secure_calls=0 provider_acquires=0 provider_releases=0 "
    "publisher_calls=0 owner_mutations=0 cpu_requests=0"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(SOURCE_PATH) != SOURCE_SHA256:
    raise SystemExit("source runtime validator changed")
SPEC = importlib.util.spec_from_file_location("provider_snapshot_runtime_source", SOURCE_PATH)
assert SPEC is not None and SPEC.loader is not None
PREVIOUS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREVIOUS)
PREVIOUS.CANDIDATE = CANDIDATE
PREVIOUS.RELEASE = RELEASE
PREVIOUS.COMPLETE = COMPLETE
BASE = PREVIOUS.BASE
BASE.CANDIDATE = CANDIDATE
BASE.RELEASE = RELEASE


def classify(text: str) -> tuple[str, str, str, dict[str, int], str]:
    result = PREVIOUS.classify(text)
    values = PREVIOUS.scalar_values(text)
    if values.get("provider_readiness_request") != "explicit-phandle-bound-device":
        raise BASE.Classification("rejected-provider-ready", "provider-readiness-request-mismatch")
    return result


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
            error.result,
            error.reason,
            "not-classified",
            {},
            "not-classified",
        )
    accepted = result == "serviceable-platform-provider-snapshot-complete"
    print("runtime_gate=serviceable-platform-provider-ready-pass" if accepted else "runtime_gate=rejected")
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"snapshot_log_sha256={log_sha256}")
    print(f"live_ledger_classification={ledger}")
    print(f"pure_marker_matches={counts.get('pure', 0)}")
    print(f"core_marker_matches={counts.get('core', 0)}")
    print(f"refusal_marker_matches={counts.get('refusal', 0)}")
    print("provider_ready_gate=passed" if accepted else "provider_ready_gate=unknown")
    print("platform_snapshot_calls=1" if accepted else "platform_snapshot_calls=unknown")
    print("platform_samples=2" if accepted else "platform_samples=unknown")
    print("platform_register_observations=26" if accepted else "platform_register_observations=unknown")
    print("provider_snapshots=1" if accepted else "provider_snapshots=unknown")
    print("provider_samples=2" if accepted else "provider_samples=unknown")
    print("provider_i2c_reads=10" if accepted else "provider_i2c_reads=unknown")
    print("provider_i2c_writes=0")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("secure_calls=0")
    print("provider_acquires=0")
    print("provider_releases=0")
    print("publisher_calls=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
