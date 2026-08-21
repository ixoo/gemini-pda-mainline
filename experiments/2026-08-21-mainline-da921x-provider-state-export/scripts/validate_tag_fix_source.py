#!/usr/bin/env python3
"""Validate the provider snapshot tag-namespace compile fix."""

from __future__ import annotations

import argparse
from pathlib import Path


FILES = (
    "include/linux/mt6797-a72-provider.h",
    "arch/arm64/kernel/mt6797_a72_membership.c",
    "drivers/regulator/da9213-legacy-regulator.c",
    "drivers/regulator/da9213-legacy-membership-test.c",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    texts = {relative: (root / relative).read_text() for relative in FILES}
    joined = "\n".join(texts.values())

    require("struct mt6797_a72_provider_state" not in joined,
            "conflicting struct tag removed")
    require(joined.count("struct mt6797_a72_provider_snapshot") == 13,
            "all thirteen struct-tag uses renamed")
    require("enum mt6797_a72_provider_state" in
            texts["arch/arm64/kernel/mt6797_a72_membership.c"],
            "existing lifecycle enum uses preserved")
    for token in (
        "int mt6797_a72_provider_snapshot(",
        "MT6797_A72_PROVIDER_STATE_ABI",
        "da9213_provider_snapshot(void *context",
        "da9213_provider_snapshot_transport_faults",
    ):
        require(token in joined, f"snapshot behavior token: {token}")
    for forbidden in ("cpu_up(", "cpu_down(", "psci_ops"):
        require(forbidden not in "\n".join(
            line for line in joined.splitlines()
            if "provider_snapshot" in line
        ), f"forbidden renamed-path effect: {forbidden}")

    print("tag_fix_source_validation=pass")
    print("renamed_struct_uses=13")
    print("lifecycle_enum=unchanged")
    print("behavior_change=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
