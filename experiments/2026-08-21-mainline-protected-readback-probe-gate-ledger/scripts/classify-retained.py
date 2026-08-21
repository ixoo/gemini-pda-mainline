#!/usr/bin/env python3
"""Classify the exact two-record probe/gate ledger from a private pstore capture."""

from __future__ import annotations

import argparse
from pathlib import Path


PREFIX = b"GEMINI_PROTECTED_READBACK_LEDGER_V2 token=GPRB-20260821-B "
PROBE = PREFIX + b"checkpoint=probe-enter slot=173 crc32=06a9b43b\n"
GATE = PREFIX + b"checkpoint=gate-passed slot=174 crc32=41e86ca4\n"
MAX_TOTAL_BYTES = 4_194_304


def classify_payload(payload: bytes) -> tuple[str, str, int, int]:
    probe = payload.count(PROBE)
    gate = payload.count(GATE)
    tagged = payload.count(PREFIX)
    if tagged != probe + gate or probe > 1 or gate > 1 or gate > probe:
        return "rejected-attribution", "malformed-duplicate-or-foreign-record", probe, gate
    if probe == 0:
        return "neither", "probe-not-entered-or-minimal-gate-refused", probe, gate
    if gate == 0:
        return (
            "probe-enter-only",
            "backend-acquisition-or-complete-gate-not-crossed",
            probe,
            gate,
        )
    return (
        "probe-and-gate-passed",
        "first-protected-call-reached-failure-at-or-after-call",
        probe,
        gate,
    )


def read_capture(capture: Path) -> tuple[bytes, int]:
    pstore = capture / "pstore"
    if not pstore.is_dir() or pstore.is_symlink():
        raise ValueError("capture pstore directory missing or unsafe")
    files = sorted(pstore.iterdir())
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise ValueError("capture contains unsafe pstore entry")
    total = sum(path.stat().st_size for path in files)
    if total > MAX_TOTAL_BYTES:
        raise ValueError("capture exceeds bounded pstore size")
    return b"".join(path.read_bytes() for path in files), len(files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload, files = read_capture(args.capture)
        result, reason, probe, gate = classify_payload(payload)
    except ValueError as error:
        result, reason, probe, gate, files = (
            "rejected-attribution",
            str(error).replace(" ", "-"),
            0,
            0,
            0,
        )
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"probe_enter_record_count={probe}")
    print(f"gate_passed_record_count={gate}")
    print(f"pstore_file_count={files}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=two-checkpoint-probe-gate-retained-ledger-only")
    return 3 if result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
