#!/usr/bin/env python3
"""Cross-check the live NVT trim bytes against the pinned source metadata."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


def read_kv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metadata_entry(path: Path) -> dict[str, str]:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("entry=8;"):
            return dict(field.split("=", 1) for field in line.split(";"))
    raise ValueError("metadata entry 8 is missing")


def main() -> int:
    result = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        "experiments/2026-07-12-input-backlight-recovery/results/"
        "nvt-live-trim-identity-20260714.txt"
    )
    metadata = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        "experiments/2026-07-12-input-backlight-recovery/results/"
        "nt36xxx-trim-map-metadata-20260714.txt"
    )

    live = read_kv(result)
    source = metadata_entry(metadata)
    live_bytes = tuple(int(part, 16) for part in live["trim_bytes"].split("_"))
    source_id = tuple(int(part, 16) for part in source["id"].split("_"))
    source_mask = tuple(int(part) for part in source["mask"].split("_"))
    matches = all(not mask or actual == expected for actual, expected, mask in zip(
        live_bytes, source_id, source_mask
    ))
    event_map = next(
        line.split("event=", 1)[1].split(";", 1)[0]
        for line in metadata.read_text(encoding="utf-8").splitlines()
        if line.startswith("map=NT36772;")
    )

    print("validation=gemini-live-nvt-trim-consistency")
    print(f"live_result={result}")
    print(f"live_result_sha256={sha256(result)}")
    print(f"source_metadata={metadata}")
    print(f"source_metadata_sha256={sha256(metadata)}")
    print(f"live_trim_bytes={live['trim_bytes']}")
    print(f"source_entry=8")
    print(f"source_map={source['map']}")
    print(f"source_event_map={event_map}")
    print(f"masked_bytes_match={'yes' if matches else 'no'}")
    print(f"identity_match={'yes' if live.get('selected_map') == source['map'] else 'no'}")
    print("hardware_write=none")
    print(f"status={'pass' if matches and live.get('selected_map') == source['map'] else 'fail'}")
    return 0 if matches and live.get("selected_map") == source["map"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
