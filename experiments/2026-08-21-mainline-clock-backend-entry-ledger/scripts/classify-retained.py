#!/usr/bin/env python3
"""Classify the exact two-record clock-backend entry ledger."""

from __future__ import annotations

import argparse
from pathlib import Path


PREFIX = b"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1 token=GCBE-20260821-A "
DRIVER_INIT = PREFIX + b"checkpoint=driver-init slot=173 crc32=cda5d04d\n"
PROBE_ENTER = PREFIX + b"checkpoint=probe-enter slot=174 crc32=a3662888\n"
MAX_TOTAL_BYTES = 4_194_304


def classify_payload(payload: bytes) -> tuple[str, str, int, int]:
    driver_init = payload.count(DRIVER_INIT)
    probe_enter = payload.count(PROBE_ENTER)
    tagged = payload.count(PREFIX)
    if (
        tagged != driver_init + probe_enter
        or driver_init > 1
        or probe_enter > 1
        or probe_enter > driver_init
    ):
        return (
            "rejected-attribution",
            "malformed-duplicate-or-foreign-record",
            driver_init,
            probe_enter,
        )
    if driver_init == 0:
        return (
            "neither",
            "clock-driver-init-not-reached-or-shared-checkpoint-refused",
            driver_init,
            probe_enter,
        )
    if probe_enter == 0:
        return (
            "driver-init-only",
            "registration-matching-or-probe-entry-not-established",
            driver_init,
            probe_enter,
        )
    return (
        "driver-init-and-probe-enter",
        "clock-probe-entered-failure-at-or-after-first-operation",
        driver_init,
        probe_enter,
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
        result, reason, driver_init, probe_enter = classify_payload(payload)
    except ValueError as error:
        result, reason, driver_init, probe_enter, files = (
            "rejected-attribution",
            str(error).replace(" ", "-"),
            0,
            0,
            0,
        )
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"driver_init_record_count={driver_init}")
    print(f"probe_enter_record_count={probe_enter}")
    print(f"pstore_file_count={files}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=two-checkpoint-clock-backend-entry-retained-ledger-only")
    return 3 if result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
