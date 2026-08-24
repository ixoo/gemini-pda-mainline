#!/usr/bin/env python3
"""Validate the checked-in A72 early-initcall experiment definition."""

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
        == "2026-08-24-mainline-a72-early-initcall-ledger",
        "experiment identity",
    )
    require(
        contract["prepared_source_state"]
        == "0d4eeb1812cce7e956325b0fdf4465b9824d811a344b98e683e4616b0322b4c4",
        "parent source state",
    )
    require(
        contract["prepared_source_integrity"]
        == "56b5611456de5817cf719e38b6fe9d94500c6089cfa03aaf8a767cf6108d06e3",
        "parent source integrity",
    )
    require(
        contract["prepared_files"]
        == {
            "fs/pstore/Kconfig":
                "4d89e2d592ca2e5813d422f000faa2d4ecfd02b5ee1faa7de23f25807f0c7c4b",
            "fs/pstore/gemini_protected_readback_ledger.c":
                "dc02a7b5250f43ec590c37d9583ee94e46fcfa3701ecf55c0804881ae6e9bda7",
            "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c":
                "365c1f342cd95a4efa40f8d06f4841e6690b5aae0806ab2c00f8c4062f49ffce",
        },
        "prepared touched-file identities",
    )
    parent = ROOT / contract["canonical_parent"]
    require(parent.is_file() and not parent.is_symlink(), "canonical parent")
    require(sha256(parent) == contract["canonical_parent_sha256"],
            "canonical parent identity")
    predecessor = ROOT / contract["predecessor_result"]
    require(predecessor.is_file() and not predecessor.is_symlink(),
            "predecessor runtime result")
    require(sha256(predecessor) == contract["predecessor_result_sha256"],
            "predecessor runtime identity")
    predecessor_text = predecessor.read_text()
    require("retained_records_1_2=exact-empty" in predecessor_text,
            "predecessor exact empty records")
    require("automatic_reset_retention=not-independently-proven"
            in predecessor_text, "predecessor inference limit")
    generator_parent = ROOT / contract["generator_parent"]
    require(generator_parent.is_file() and not generator_parent.is_symlink(),
            "generator parent")
    require(sha256(generator_parent) == contract["generator_parent_sha256"],
            "generator parent identity")

    require(
        contract["retained"]
        == {
            "token": "GAEI-20260824-A",
            "slots": [1, 2],
            "checkpoints": ["pure-init", "core-init"],
            "fallback": "pure-init-primary-refused",
            "maximum_write_attempts": 2,
            "overwrite": False,
            "clear": False,
            "retry": False,
        },
        "retained contract",
    )
    require(all(value == 0 for value in contract["runtime_effects"].values()),
            "zero hardware/source runtime effects")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profile = manifest["config"]["profiles"]["a72-early-initcall-ledger"]
    require(profile["base"] == "defconfig", "profile base")
    require(profile["patch_series"] == "patches/series", "profile series")
    require(profile["fragments"][-1]
            == "configs/gemini-a72-early-initcall-ledger.fragment",
            "profile fragment")
    fragment_path = ROOT / profile["fragments"][-1]
    require(sha256(fragment_path)
            == "11b564c36f196e2245fa561776ee6b8593378aea3c03e61e83b69bc0e5dcf49c",
            "profile fragment identity")
    fragment = fragment_path.read_text()
    for token in (
        "CONFIG_MODULES=y",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "CONFIG_PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER=y",
        "# CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER is not set",
        "# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set",
        "# CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set",
        "# CONFIG_KUNIT is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-early"',
    ):
        require(token in fragment, f"fragment token: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-a72-early-initcall-ledger",
        "fetch-a72-early-initcall-ledger",
    ):
        require(buildbox.count(command) == 2, f"Buildbox command: {command}")
    docs = (ROOT / "docs/BUILDBOX.md").read_text()
    require("generate-a72-early-initcall-ledger" in docs,
            "Buildbox documentation")
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    require("2026-08-24-mainline-a72-early-initcall-ledger/README.md"
            in roadmap, "roadmap link")

    for name, expected in {
        "source_edits.py":
            "db3cdf8f2dce7065524c19fbf2175edbdbc7fe3358456a8c57b1f99c1bbd3715",
        "validate_source.py":
            "8c74b3ee4d3d849e66cdc47baf05decf21eaa55267c0d8b115d1f8f50ad1faf5",
        "validate_patch.py":
            "815aa775ba3c15f2014ec8fb0055233f8b85c2f925ccddd389e35021117b991e",
        "generate-on-buildbox":
            "cbc182bdadefb8265c77c385df1070e0c40b2fb05586664e157e300a375bb887",
    }.items():
        path = EXPERIMENT / "scripts" / name
        require(path.is_file() and not path.is_symlink() and
                sha256(path) == expected, f"definition tool identity: {name}")

    generation = contract["generation"]
    require(generation["status"] == "validated-admitted",
            "generation admitted")
    require(generation["patch"]
            == "0362-pstore-add-Gemini-A72-early-initcall-ledger.patch",
            "generated patch name")
    require(generation["patch_count"] == 1 and
            generation["changed_files"]
            == [
                "fs/pstore/Kconfig",
                "fs/pstore/gemini_protected_readback_ledger.c",
                "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c",
            ], "generation scope")
    generated_patch = ROOT / "patches/v7.1.3" / generation["patch"]
    require(generated_patch.is_file() and not generated_patch.is_symlink(),
            "canonical generated patch")
    require(sha256(generated_patch) == generation["patch_sha256"]
            == "65771c690b9c19833160d8547898b2f97b8b0149518092700eab3ef8b861a5a9",
            "canonical generated patch identity")
    require(generation["canonical_admission"] is True,
            "canonical admission")
    series = (ROOT / "patches/series").read_text().splitlines()
    require(series[-1] == f"v7.1.3/{generation['patch']}",
            "canonical series tail")
    require([attempt["attempt"] for attempt in generation["attempts"]]
            == [1, 2, 3], "generation attempt chronology")
    require(generation["attempts"][0]["result"]
            == "validator-split-string-rejected",
            "attempt-1 result")
    require(generation["attempts"][1]["result"]
            == "checkpatch-blank-line-rejected",
            "attempt-2 result")
    success = generation["attempts"][2]
    require(success["repository_commit"]
            == "e9b9d2fcff2e7e5be1871840606f05531529d34c" and
            success["result_commit"]
            == "2371b752dc86e084f28ddcfff5bd2f85689df813",
            "attempt-3 source identities")
    require(success["source_validation"] is True and
            success["patch_shape_validation"] is True and
            success["byte_identical_replay"] is True and
            success["checkpatch"]
            == {"errors": 0, "warnings": 0, "checks": 0},
            "attempt-3 validation")
    for attempt in generation["attempts"]:
        attempt_receipt = ROOT / attempt["receipt"]
        require(attempt_receipt.is_file() and not attempt_receipt.is_symlink(),
                f"attempt-{attempt['attempt']} receipt")
        require(sha256(attempt_receipt) == attempt["receipt_sha256"],
                f"attempt-{attempt['attempt']} receipt identity")
    require(
        contract["decision"]
        == {
            "result": "canonical-patch-admitted",
            "selected_next": "build-isolated-profile-on-buildbox",
            "device_action": False,
            "boot_candidate": False,
        },
        "current decision",
    )

    print("validation=a72-early-initcall-ledger-definition")
    print("retained_checkpoints=pure-init,core-init")
    print("fallback=pure-init-primary-refused")
    print("retained_write_attempts_maximum=2")
    print("observer_registrations=0")
    print("allocations=0")
    print("source_lookups=0")
    print("cpu_requests=0")
    print("device_action=false")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
