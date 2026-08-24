#!/usr/bin/env python3
"""Validate the checked-in A72 observer init/probe experiment definition."""

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
        == "2026-08-24-mainline-a72-physical-source-init-probe-ledger",
        "experiment identity",
    )
    require(
        contract["prepared_source_state"]
        == "1c2210e46275423d9db88b0841b3a6dd9e478ef95c498efdae83218c5690020d",
        "parent source state",
    )
    require(
        contract["prepared_source_integrity"]
        == "48d65aa58cb0b75ecf73359f4b0a912b8f439b99bae6d2bd6c9286e9cbd5f72f",
        "parent source integrity",
    )
    parent = ROOT / contract["canonical_parent"]
    require(parent.is_file() and not parent.is_symlink(), "canonical parent")
    require(
        sha256(parent)
        == "db53a84c440067862610733670637675e63b9f25fe345eaf141b1b53572ec75e",
        "canonical parent identity",
    )
    require(
        contract["retained"]
        == {
            "token": "GAIP-20260824-A",
            "slots": [1, 2],
            "checkpoints": ["driver-init", "probe-enter"],
            "maximum_writes": 2,
            "overwrite": False,
            "clear": False,
            "retry": False,
        },
        "retained contract",
    )
    require(all(value == 0 for value in contract["runtime_effects"].values()),
            "zero runtime effects")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profile = manifest["config"]["profiles"][
        "a72-physical-source-init-probe-ledger"
    ]
    require(profile["base"] == "defconfig", "profile base")
    require(profile["patch_series"] == "patches/series", "profile series")
    require(
        profile["fragments"][-1]
        == "configs/gemini-a72-physical-source-init-probe-ledger.fragment",
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
        'CONFIG_LOCALVERSION="-gemini-a72-init-probe"',
    ):
        require(token in fragment, f"fragment token: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-a72-physical-source-init-probe-ledger",
        "fetch-a72-physical-source-init-probe-ledger",
    ):
        require(buildbox.count(command) == 2, f"Buildbox command: {command}")
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    require(
        "2026-08-24-mainline-a72-physical-source-init-probe-ledger/README.md"
        in roadmap,
        "roadmap link",
    )
    predecessor = ROOT / contract["predecessor_result"]
    require(predecessor.is_file(), "predecessor runtime result")
    require(
        "runtime_classification=rejected-before-probe-enter-checkpoint"
        in predecessor.read_text(),
        "predecessor classification",
    )
    runtime = ROOT / (
        "experiments/2026-08-24-mainline-a72-physical-source-init-probe-ledger/"
        "results/runtime-attempt-1-before-driver-init-20260824.txt"
    )
    require(runtime.is_file(), "runtime result")
    runtime_text = runtime.read_text()
    require(
        "runtime_classification=before-driver-init-or-writer-refused" in runtime_text,
        "runtime classification",
    )
    require("retained_records_1_2=exact-empty" in runtime_text, "empty records")
    require(contract["decision"]["boot_candidate"] is False, "candidate retired")

    print("validation=a72-physical-source-init-probe-definition")
    print("profile=a72-physical-source-init-probe-ledger")
    print("retained_checkpoints=driver-init,probe-enter")
    print("allocations=0")
    print("source_lookups=0")
    print(f"boot_candidate={str(contract['candidate']['boot_candidate']).lower()}")
    print("result=pass")


if __name__ == "__main__":
    main()
