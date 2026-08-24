#!/usr/bin/env python3
"""Validate the checked-in pre-capture experiment definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    require(contract["schema"] == 1, "schema")
    require(
        contract["experiment"]
        == "2026-08-24-mainline-a72-physical-source-precapture-ledger",
        "experiment identity",
    )
    require(
        contract["prepared_source_state"]
        == "268ebef69a7575d23004b137a3334989b82b444cbf3a773850626566275b8fb8",
        "parent source state",
    )
    require(
        contract["prepared_source_integrity"]
        == "9f18bf45f6d001892044d8b1f1303b5e26c49e2fcd19dab637a994355fc6c65f",
        "parent source integrity",
    )
    parent = ROOT / contract["canonical_parent"]
    require(parent.is_file() and not parent.is_symlink(), "canonical parent")
    require(
        sha256(parent)
        == "94076d20cf542941016e72996d5bdc1a8c03cedbd6e284763e424d8841dde4c9",
        "canonical parent identity",
    )
    require(contract["retained"] == {
        "token": "GAPC-20260824-A",
        "slots": [1, 2],
        "checkpoints": ["probe-enter", "sources-held"],
        "maximum_writes": 2,
        "overwrite": False,
        "clear": False,
        "retry": False,
    }, "retained contract")
    require(all(value == 0 for value in contract["runtime"].values()),
            "zero-capture runtime contract")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profile = manifest["config"]["profiles"][
        "a72-physical-source-precapture-ledger"
    ]
    require(profile["base"] == "defconfig", "profile base")
    require(profile["patch_series"] == "patches/series", "profile series")
    require(
        profile["fragments"][-1]
        == "configs/gemini-a72-physical-source-precapture-ledger.fragment",
        "profile fragment",
    )
    fragment = (ROOT / profile["fragments"][-1]).read_text()
    for token in (
        "CONFIG_MODULES=y",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER=y",
        "# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set",
        "# CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set",
        "# CONFIG_KUNIT is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-precapture"',
    ):
        require(token in fragment, f"fragment token: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-a72-physical-source-precapture-ledger",
        "fetch-a72-physical-source-precapture-ledger",
    ):
        require(buildbox.count(command) == 2, f"Buildbox command: {command}")
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    require(
        "2026-08-24-mainline-a72-physical-source-precapture-ledger/README.md"
        in roadmap,
        "roadmap link",
    )
    predecessor = ROOT / contract["predecessor_result"]
    require(predecessor.is_file(), "predecessor runtime result")
    require(
        "runtime_classification=rejected-before-first-physical-source-checkpoint"
        in predecessor.read_text(),
        "predecessor classification",
    )

    print("validation=a72-physical-source-precapture-definition")
    print("profile=a72-physical-source-precapture-ledger")
    print("retained_checkpoints=probe-enter,sources-held")
    print("capture_calls=0")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
