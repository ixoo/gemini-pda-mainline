#!/usr/bin/env python3
"""Classify independent arm64 entry-ledger records recovered by Gemian."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import zlib


TOKEN = "GAEL-20260816-A"
PREFIX = "GEMINI_ARM64_ENTRY_LEDGER_V1"
STAGES = (
    ("primary-entry", "E0", 171),
    ("pre-primary-switch", "E1", 172),
    ("post-mmu", "E2", 173),
    ("post-reserved-scan", "E3", 174),
)
LINE = re.compile(
    rf"^{PREFIX} {TOKEN} (E[0-3]) ([0-9]+) ([0-9a-f]{{8}})$"
)


@dataclass(frozen=True)
class Classification:
    result: str
    reason: str
    present: tuple[int, ...]
    missing_before_highest: tuple[int, ...]


def integrity(stage: str, slot: int) -> str:
    source = f"token={TOKEN}|stage={stage}|slot={slot}".encode()
    return f"{zlib.crc32(source):08x}"


def files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise ValueError("capture path is neither a file nor a directory")
    return sorted(item for item in path.rglob("*") if item.is_file())


def classify(path: Path) -> Classification:
    expected = {slot: (stage, code) for stage, code, slot in STAGES}
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
            code = match.group(1)
            slot = int(match.group(2))
            crc = match.group(3)
            stage_and_code = expected.get(slot)
            if (stage_and_code is None or stage_and_code[1] != code or
                    integrity(stage_and_code[0], slot) != crc):
                suspicious.append(f"integrity-or-stage:{item.name}")
                continue
            if slot in found:
                suspicious.append(f"duplicate-slot:{slot}")
                continue
            found[slot] = (stage_and_code[0], item)

    present = tuple(sorted(found))
    if suspicious:
        return Classification(
            "rejected-attribution", ",".join(sorted(suspicious)), present, ()
        )
    if not present:
        return Classification(
            "no-stage",
            "image-entry-unestablished-or-entry-refused-before-post-mmu",
            (),
            (),
        )

    highest = present[-1]
    missing = tuple(slot for _, _, slot in STAGES if slot < highest and slot not in found)
    reasons = {
        171: "primary-entry-reached-with-mmu-and-dcache-off",
        172: "pre-primary-switch-reached-with-mmu-and-dcache-off",
        173: "post-mmu-early-setup-arch-reached",
        174: "post-arm64-memblock-init-reached",
    }
    stage = found[highest][0]
    return Classification(f"through-{stage}", reasons[highest], present, missing)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result = classify(args.capture)
    except (OSError, ValueError) as error:
        print("runtime_classification=rejected-attribution")
        print(f"runtime_reason={str(error).replace(' ', '-')}")
        return 3
    print(f"runtime_classification={result.result}")
    print(f"runtime_reason={result.reason}")
    print("valid_slots=" + (",".join(map(str, result.present)) if result.present else "none"))
    print(f"highest_valid_slot={result.present[-1] if result.present else 'none'}")
    print(
        "missing_earlier_slots="
        + (",".join(map(str, result.missing_before_highest)) if result.missing_before_highest else "none")
    )
    print("earlier_empty_slots=accepted-as-safe-writer-refusal")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=arm64-entry-localization-only")
    return 3 if result.result == "rejected-attribution" else 0


if __name__ == "__main__":
    raise SystemExit(main())
