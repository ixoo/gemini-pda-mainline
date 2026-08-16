#!/usr/bin/env python3
"""Classify retained Gemini pre-ramoops records recovered by Gemian."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import zlib


TOKEN = "GPRL-20260816-A"
PREFIX = "GEMINI_PRE_RAMOOPS_LEDGER_V1"
STAGES = (
    ("reserved-scan", 171),
    ("early-initcall", 172),
    ("core-initcall", 173),
    ("postcore-initcall", 174),
)
LINE = re.compile(
    rf"^{PREFIX} token={TOKEN} stage=([a-z-]+) slot=([0-9]+) crc32=([0-9a-f]{{8}})$"
)


def integrity(stage: str, slot: int) -> str:
    source = f"token={TOKEN}|stage={stage}|slot={slot}".encode()
    return f"{zlib.crc32(source):08x}"


def files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError("capture path is neither a file nor a directory")
    return sorted(item for item in path.rglob("*") if item.is_file())


def classify(path: Path) -> tuple[str, str, list[int]]:
    found: dict[int, tuple[str, Path]] = {}
    suspicious: list[str] = []
    for item in files(path):
        text = item.read_text(encoding="utf-8", errors="replace").replace("\r", "")
        for raw in text.splitlines():
            line = raw.strip()
            if PREFIX not in line and TOKEN not in line:
                continue
            match = LINE.fullmatch(line)
            if not match:
                suspicious.append(f"malformed:{item.name}")
                continue
            stage = match.group(1)
            slot = int(match.group(2))
            crc = match.group(3)
            expected = dict((number, name) for name, number in STAGES)
            if expected.get(slot) != stage or integrity(stage, slot) != crc:
                suspicious.append(f"integrity-or-stage:{item.name}")
                continue
            if slot in found:
                suspicious.append(f"duplicate-slot:{slot}")
                continue
            found[slot] = (stage, item)

    if suspicious:
        return "rejected-attribution", ",".join(sorted(suspicious)), sorted(found)

    present = sorted(found)
    expected_prefix = [slot for _, slot in STAGES[: len(present)]]
    if present != expected_prefix:
        return "rejected-attribution", "non-contiguous-stage-set", present
    if not present:
        return "no-stage", "before-reserved-scan-checkpoint-or-writer-refused", present

    stage = found[present[-1]][0]
    reasons = {
        171: "after-reserved-scan-before-early-initcall-checkpoint",
        172: "after-early-before-core-initcall-checkpoint",
        173: "after-core-before-postcore-initcall-checkpoint",
        174: "through-postcore-checkpoint",
    }
    return f"through-{stage}", reasons[present[-1]], present


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, reason, present = classify(args.capture)
    except (OSError, ValueError) as error:
        print("runtime_classification=rejected-attribution")
        print(f"runtime_reason={str(error).replace(' ', '-')}")
        return 3
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print("valid_slots=" + (",".join(map(str, present)) if present else "none"))
    print(f"highest_valid_slot={present[-1] if present else 'none'}")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=early-boot-localization-only")
    return 3 if result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
