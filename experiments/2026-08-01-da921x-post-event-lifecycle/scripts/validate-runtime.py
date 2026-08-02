#!/usr/bin/env python3
"""Classify the exact Stage 27 post-event lifecycle record."""

from __future__ import annotations

import argparse
from pathlib import Path


NATURAL_STATE = (
    "attempts=1 register_entries=1 register_returns=1 register_retval=0 "
    "callsite_entries=1 callsite_returns=1 public_returns=1 wrapper_entries=2 "
    "wrapper_returns=2 namespace_checks=2 untagged_routes=2 tagged_routes=0 "
    "sockets=1 listeners=0 allocations=0 broadcasts=0 uevent_retval=0"
)
EXPECTED = {
    "kernel": "7.1.3-gemini-da921x-life27",
    "validation_stage": "20",
    "natural_device_add_state": NATURAL_STATE,
    "i2c_device": "1-0068",
    "identity_log_count": "2",
    "provider": "absent",
    "consumer": "absent",
    "cpu_online": "0-7",
    "cpu_offline": "8-9",
    "sysfs": "restored-read-only",
    "usb": "serviceable",
    "tty1": "present",
    "keyboard": "present",
    "device_storage_access": "none",
    "automatic_reboot": "no",
    "post_event_lifecycle_result": "PASS",
}
PHASE_COUNTS = {
    "initial": (14, 8, 6),
    "post_unbind": (14, 8, 6),
    "post_rebind": (28, 16, 12),
}
ZERO_COUNTERS = (
    "oracle_write_only_messages",
    "oracle_register_data_write_messages",
    "oracle_other_transfers",
    "oracle_other_address_transfers",
)


def parse(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text().splitlines(), 1):
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            raise ValueError(f"{path}:{number}: malformed record")
        key, value = raw.split("=", 1)
        if not key or key in values:
            raise ValueError(f"{path}:{number}: empty or duplicate key")
        values[key] = value
    return values


def validate(values: dict[str, str]) -> None:
    expected_keys = set(EXPECTED)
    for phase in PHASE_COUNTS:
        expected_keys.update(
            f"{phase}_{key}"
            for key in (
                "transfer_attempts",
                "dma_starts",
                "nonzero_starts",
                "irq_count",
                "oracle_combined_pointer_reads",
                "oracle_primary_pointer_reads",
                "oracle_page2_pointer_reads",
                *ZERO_COUNTERS,
            )
        )
    if set(values) != expected_keys:
        missing = sorted(expected_keys - set(values))
        extra = sorted(set(values) - expected_keys)
        raise ValueError(f"runtime inventory changed: missing={missing}, extra={extra}")
    for key, expected in EXPECTED.items():
        if values[key] != expected:
            raise ValueError(f"{key}: expected {expected!r}, got {values[key]!r}")
    for phase, (combined, primary, page2) in PHASE_COUNTS.items():
        for key in (
            "transfer_attempts",
            "nonzero_starts",
            "irq_count",
            "oracle_combined_pointer_reads",
        ):
            if values[f"{phase}_{key}"] != str(combined):
                raise ValueError(f"{phase}_{key}: expected {combined}")
        if values[f"{phase}_dma_starts"] != "0":
            raise ValueError(f"{phase}_dma_starts: expected zero")
        if values[f"{phase}_oracle_primary_pointer_reads"] != str(primary):
            raise ValueError(f"{phase}_oracle_primary_pointer_reads: expected {primary}")
        if values[f"{phase}_oracle_page2_pointer_reads"] != str(page2):
            raise ValueError(f"{phase}_oracle_page2_pointer_reads: expected {page2}")
        for key in ZERO_COUNTERS:
            if values[f"{phase}_{key}"] != "0":
                raise ValueError(f"{phase}_{key}: expected zero")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        validate(parse(args.record))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"error: {exc}")
    print("validation=da921x-post-event-lifecycle-runtime")
    print("post_event_lifecycle_result=PASS")
    print("next_action=close-identification-lifecycle")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
