#!/usr/bin/env python3
"""Compare only the manifest fields that define a usbdiag package input."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


FIELD_PATHS = (
    ("schema",),
    ("kernel",),
    ("architecture",),
    ("patch_series",),
    ("config", "profiles", "usbdiag"),
)


def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream, object_pairs_hook=no_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"cannot parse {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} top level is not an object")
    return value


def select(value: dict[str, Any], path: tuple[str, ...], label: str) -> Any:
    current: Any = value
    for component in path:
        if not isinstance(current, dict) or component not in current:
            raise ValueError(f"{label} is missing {'.'.join(path)}")
        current = current[component]
    return current


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current", type=pathlib.Path, required=True)
    parser.add_argument("--packaged", type=pathlib.Path, required=True)
    args = parser.parse_args()

    try:
        current = load(args.current, "current manifest")
        packaged = load(args.packaged, "packaged manifest")
        for path in FIELD_PATHS:
            current_value = select(current, path, "current manifest")
            packaged_value = select(packaged, path, "packaged manifest")
            if packaged_value != current_value:
                raise ValueError(f"packaged manifest differs at {'.'.join(path)}")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=usbdiag-manifest-input-boundary")
    print("matched_fields=schema,kernel,architecture,patch_series,config.profiles.usbdiag")
    print("unrelated_profile_additions=ignored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
