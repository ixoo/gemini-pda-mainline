#!/usr/bin/env python3
"""Validate the checked-in A72 global-initcall experiment definition."""

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
        == "2026-08-24-mainline-a72-global-initcall-ledger",
        "experiment identity",
    )
    require(
        contract["prepared_source_state"]
        == "5afac462264e8fd73d509f585f1aa1107ecead2be962fcfb12bf95f93402cef6",
        "parent source state",
    )
    require(
        contract["prepared_source_integrity"]
        == "390a291f4e2c2c2bbf2e64fda0371bf00c79e85ebc00717a642bac38ccaf6e43",
        "parent source integrity",
    )
    require(
        contract["prepared_files"]
        == {
            "fs/pstore/Kconfig":
                "506ad6311e55e8c7f4fbdeee4232043bb45e0516ef9f1cea2f1356a7c4071535",
            "fs/pstore/gemini_protected_readback_ledger.c":
                "889a5d2199f0498b2517c161e0026251213e13de90c09672a4a7cc965a1eaaa0",
            "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c":
                "5a4d297e29e6abb7910998cd360032b3b0b587b0b93b7e13f21f8aca9dfbcf95",
        },
        "prepared touched-file identities",
    )
    parent = ROOT / contract["canonical_parent"]
    require(parent.is_file() and not parent.is_symlink(), "canonical parent")
    require(sha256(parent) == contract["canonical_parent_sha256"],
            "canonical parent identity")
    require(
        contract["retained"]
        == {
            "token": "GAIC-20260824-A",
            "slots": [1, 2],
            "checkpoints": ["subsys-init", "fs-init"],
            "maximum_writes": 2,
            "overwrite": False,
            "clear": False,
            "retry": False,
        },
        "retained contract",
    )
    require(all(value == 0 for value in contract["runtime_effects"].values()),
            "zero hardware/source runtime effects")

    predecessor = ROOT / contract["predecessor_result"]
    require(predecessor.is_file() and not predecessor.is_symlink(),
            "predecessor runtime receipt")
    require(sha256(predecessor) == contract["predecessor_result_sha256"],
            "predecessor runtime identity")
    predecessor_text = predecessor.read_text()
    require(
        "runtime_classification=before-driver-init-or-writer-refused"
        in predecessor_text,
        "predecessor classification",
    )
    require("retained_records_1_2=exact-empty" in predecessor_text,
            "predecessor empty records")

    generator_parent = ROOT / contract["generator_parent"]
    require(generator_parent.is_file() and not generator_parent.is_symlink(),
            "generator parent")
    require(sha256(generator_parent) == contract["generator_parent_sha256"],
            "generator parent identity")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profile = manifest["config"]["profiles"]["a72-global-initcall-ledger"]
    require(profile["base"] == "defconfig", "profile base")
    require(profile["patch_series"] == "patches/series", "profile series")
    require(
        profile["fragments"][-1]
        == "configs/gemini-a72-global-initcall-ledger.fragment",
        "profile fragment",
    )
    fragment = (ROOT / profile["fragments"][-1]).read_text()
    for token in (
        "CONFIG_MODULES=y",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
        "CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER=y",
        "CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER=y",
        "# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER is not set",
        "# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set",
        "# CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set",
        "# CONFIG_KUNIT is not set",
        'CONFIG_LOCALVERSION="-gemini-a72-initcalls"',
    ):
        require(token in fragment, f"fragment token: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-a72-global-initcall-ledger",
        "fetch-a72-global-initcall-ledger",
    ):
        require(buildbox.count(command) == 2, f"Buildbox command: {command}")
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    require(
        "2026-08-24-mainline-a72-global-initcall-ledger/README.md" in roadmap,
        "roadmap link",
    )
    generation = contract["generation"]
    generated_patch = ROOT / "patches/v7.1.3" / generation["patch"]
    require(generation["status"] == "validated-admitted",
            "generation admitted")
    require(generated_patch.is_file() and not generated_patch.is_symlink(),
            "canonical generated patch")
    require(sha256(generated_patch) == generation["patch_sha256"],
            "canonical generated patch identity")
    require(generation["canonical_admission"] is True,
            "canonical admission")
    require(generation["checkpatch"] == {"errors": 0, "warnings": 0, "checks": 0},
            "strict checkpatch result")
    series = (ROOT / "patches/series").read_text().splitlines()
    require(series[-1] == f"v7.1.3/{generation['patch']}",
            "canonical series tail")
    candidate = contract["candidate"]
    require(candidate["status"] == "validated", "candidate validated")
    require(candidate["repository_commit"]
            == "16567a0bf48286e00579ecc9838cef399e7c5919",
            "candidate repository commit")
    require(candidate["kernel_release"] == "7.1.3-gemini-a72-initcalls",
            "candidate release")
    require(candidate["raw_sha256"]
            == "41a181f631456be55ae28b75ee525226dd7b41da844c5c4ed5a0acd3f13c5156",
            "raw candidate identity")
    require(candidate["raw_size"] == 6_909_952, "raw candidate size")
    require(candidate["padded_sha256"]
            == "e9d565021de9ed1164aa78a78795d6a3dabd7af656aaa3df791e23424e66125a",
            "padded candidate identity")
    require(candidate["padded_size"] == 16_777_216,
            "padded candidate size")
    require(candidate["lk_gates"] == "32-of-32",
            "LK validation gates")
    require(candidate["independent_validation"] is True,
            "independent candidate validation")
    require(candidate["boot_candidate"] is True, "candidate accepted")
    for name, expected in {
        "build-candidate.sh":
            "c8ed57de3c3ad87691cc43d5d84fb75b87ac3a95b375a6020ecf892ef6b0b053",
        "validate-candidate.sh":
            "5a52e1211054493e264076c0178cc251912f5d728db92694bc87b6f7b3c1bcfe",
        "install-boot2.sh":
            "c1c3a364d945fb869c994bfada673cc71a89eb94c6db6be518a16fe88f3447a0",
    }.items():
        path = EXPERIMENT / "scripts" / name
        require(path.is_file() and not path.is_symlink() and sha256(path) == expected,
                f"candidate tool identity: {name}")

    print("validation=a72-global-initcall-ledger-definition")
    print("profile=a72-global-initcall-ledger")
    print("retained_checkpoints=subsys-init,fs-init")
    print("observer_registrations=0")
    print("allocations=0")
    print("source_lookups=0")
    print("cpu_requests=0")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
