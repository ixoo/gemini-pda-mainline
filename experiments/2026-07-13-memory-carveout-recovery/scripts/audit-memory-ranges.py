#!/usr/bin/env python3
"""Check fixed Gemini reserved-memory ranges against the live capture.

This is a source/evidence audit only.  It never reads or writes device memory.
The live ranges below are copied from the sanitized 2026-07-13 capture in
artifacts/device-inventory/20260713-live/memory-map.txt; dynamic reservations
are intentionally reported as unresolved rather than assigned an address.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
BASE_PATCH = ROOT / "patches/v7.1.3/0020-arm64-dts-mediatek-add-Planet-Gemini-PDA.patch"

# (label, start, size), fixed nodes from the sanitized live FDT capture.
LIVE_FIXED = (
    ("spm-dummy-1", 0x40000000, 0x1000),
    ("ram-console", 0x44400000, 0x10000),
    ("pstore", 0x44410000, 0xE0000),
    ("minirdump", 0x444F0000, 0x10000),
    ("atf", 0x44600000, 0x10000),
    ("atf-ramdump", 0x44610000, 0x30000),
    ("cache-dump", 0x44640000, 0x30000),
    ("preloader", 0x44800000, 0x100000),
    ("lk", 0x46000000, 0x400000),
)

# These are runtime mblock allocations appended by LK after its conflict
# check. They are reported as observed evidence, not required static DT nodes.
POST_LK_OBSERVED = (
    ("framebuffer", 0x7DFB0000, 0x1F90000),
    ("atf-log", 0x7FF40000, 0x40000),
    ("log-store", 0x7FF80000, 0x80000),
    ("ccci-1", 0x88000000, 0x6000000),
    ("ccci-2", 0xB4000000, 0xA000000),
    ("ccci-3", 0xBE000000, 0xC00000),
    ("scp", 0xBFDF0000, 0x200000),
)


def parse_local_ranges(text: str) -> list[tuple[str, int, int]]:
    pattern = re.compile(
        r"^\+\s*memory@([0-9a-f]+)\s*\{.*?^\+\s*reg\s*=\s*<0\s+"
        r"0x([0-9a-f]+)\s+0\s+0x([0-9a-f]+)>;",
        re.MULTILINE | re.DOTALL,
    )
    return [
        (f"memory@{start.lower()}", int(start, 16), int(size, 16))
        for start, start_again, size in pattern.findall(text)
        if start.lower() == start_again.lower()
    ]


def overlaps(ranges: list[tuple[str, int, int]]) -> list[str]:
    findings: list[str] = []
    for index, (left_name, left_start, left_size) in enumerate(ranges):
        left_end = left_start + left_size
        for right_name, right_start, right_size in ranges[index + 1 :]:
            right_end = right_start + right_size
            if left_start < right_end and right_start < left_end:
                findings.append(
                    f"{left_name} [{left_start:#x},{left_end:#x}) overlaps "
                    f"{right_name} [{right_start:#x},{right_end:#x})"
                )
    return findings


def containing_range(
    ranges: list[tuple[str, int, int]], start: int, size: int
) -> str | None:
    end = start + size
    for name, range_start, range_size in ranges:
        if range_start <= start and end <= range_start + range_size:
            return name
    return None


def main() -> int:
    patch_path = Path(os.environ.get("GEMINI_DTS_PATCH", BASE_PATCH))
    if not patch_path.is_file():
        print(f"missing local DTS patch: {patch_path}", file=sys.stderr)
        return 2
    local = parse_local_ranges(patch_path.read_text(encoding="utf-8"))
    if not local:
        print("no local reserved-memory ranges parsed", file=sys.stderr)
        return 2

    print("Gemini fixed reserved-memory range audit")
    print(f"patch={patch_path}")
    print(f"local_fixed_range_count={len(local)}")
    local_overlaps = overlaps(local)
    print(f"local_overlaps={len(local_overlaps)}")
    for finding in local_overlaps:
        print(f"  {finding}")

    missing = []
    for label, start, size in LIVE_FIXED:
        owner = containing_range(local, start, size)
        status = f"covered_by={owner}" if owner else "MISSING"
        print(f"live_fixed {label} start={start:#x} size={size:#x} {status}")
        if owner is None:
            missing.append(label)

    print(f"live_fixed_missing={len(missing)}")
    if missing:
        print("missing_live_fixed=" + ",".join(missing))
    print("post_lk_observed_regions=" + ",".join(label for label, _, _ in POST_LK_OBSERVED))
    print("post_lk_static_policy=omit_until_lk_handoff_is_proven")
    print(
        "dynamic_live_regions=consys-reserve-memory,"
        "reserve-memory-scp_share,spm-reserve-memory,"
        "reserve-memory-dram_r0_dummy_read,reserve-memory-dram_r1_dummy_read"
    )
    print("dynamic_policy=do_not_assign_fixed_addresses_without_bootloader_contract")
    print("memory_model=local_4GiB_window_requires_runtime_handoff_validation")
    return 1 if local_overlaps or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
