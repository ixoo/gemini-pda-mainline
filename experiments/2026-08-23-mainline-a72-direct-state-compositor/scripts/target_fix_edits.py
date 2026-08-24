#!/usr/bin/env python3
"""Correct the focused admission-preservation probe target."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()

    root = args.source_root.resolve()
    path = root / "arch/arm64/kernel/mt6797_a72_direct_state_test.c"
    require(path.is_file() and not path.is_symlink(),
            "focused test source absent or unsafe")
    text = path.read_text(encoding="utf-8")
    old = "mt6797_a72_membership_preflight_up(8, CPUHP_OFFLINE)"
    new = "mt6797_a72_membership_preflight_up(8, CPUHP_ONLINE)"
    require(text.count(old) == 2, "expected two incorrect preflight targets")
    require(text.count(new) == 0, "target correction already applied")
    path.write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
