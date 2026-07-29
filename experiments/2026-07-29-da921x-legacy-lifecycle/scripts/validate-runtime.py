#!/usr/bin/env python3
"""Validate the exact one-shot Gate 3 lifecycle record."""

from __future__ import annotations

import argparse
import pathlib


EXPECTED = {
    "experiment": "2026-07-29-da921x-legacy-lifecycle",
    "kernel_release": "7.1.3-gemini-da921x-life",
    "cpu_online": "0-7",
    "cpu_offline": "8-9",
    "identity_log_count": "2",
    "initial_oracle_combined_pointer_reads": "14",
    "initial_oracle_primary_pointer_reads": "8",
    "initial_oracle_page2_pointer_reads": "6",
    "post_unbind_oracle_combined_pointer_reads": "14",
    "post_unbind_oracle_primary_pointer_reads": "8",
    "post_unbind_oracle_page2_pointer_reads": "6",
    "post_rebind_oracle_combined_pointer_reads": "28",
    "post_rebind_oracle_primary_pointer_reads": "16",
    "post_rebind_oracle_page2_pointer_reads": "12",
    "provider": "absent",
    "consumer": "absent",
    "automatic_reboot": "no",
    "gate3_result": "PASS",
}
ZERO_SUFFIXES = (
    "oracle_write_only_messages",
    "oracle_register_data_write_messages",
    "oracle_other_transfers",
    "oracle_other_address_transfers",
)


def parse_record(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw or raw.startswith("#"):
            continue
        if "=" not in raw:
            raise ValueError(f"{path}:{number}: malformed record")
        key, value = raw.split("=", 1)
        if not key or key in values:
            raise ValueError(f"{path}:{number}: empty or duplicate key")
        values[key] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=pathlib.Path)
    args = parser.parse_args()
    values = parse_record(args.record)

    for key, expected in EXPECTED.items():
        actual = values.get(key)
        if actual != expected:
            raise SystemExit(f"{key}: expected {expected!r}, got {actual!r}")
    if not values.get("i2c_device", "").endswith("-0068"):
        raise SystemExit("i2c_device: expected the bound primary 0x68 client")
    for phase in ("initial", "post_unbind", "post_rebind"):
        for suffix in ZERO_SUFFIXES:
            key = f"{phase}_{suffix}"
            if values.get(key) != "0":
                raise SystemExit(f"{key}: expected '0', got {values.get(key)!r}")

    print("validation=da921x-legacy-lifecycle-runtime")
    print("gate3_result=PASS")
    print("next_action=close-gate-3")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
