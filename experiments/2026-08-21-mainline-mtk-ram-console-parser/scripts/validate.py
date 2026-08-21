#!/usr/bin/env python3
"""Validate the repository-side retained ram-console parser design."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def main() -> None:
    contract = json.loads((HERE / "contract.json").read_text())
    require(contract["schema"] == 1, "contract schema")
    require(
        contract["repository_parent"] ==
        "97d9a02ab58dc967d0683380dbe3da481ccf8885",
        "repository parent",
    )
    decision = contract["decision"]
    require(decision["selected_boundary"] == "PURE_RETAINED_HEADER_PARSER",
            "selected boundary")
    for key in ("audit_readme", "audit_design", "audit_matrix"):
        require(
            sha256(ROOT / decision[key]) == decision[f"{key}_sha256"],
            f"decision {key} identity",
        )

    parent = contract["parent"]
    require(
        parent["source_state"] ==
        "2719c3b91f238e83b32f22e19bc94c15a4b4aeb6a886a6548e8952b28497da9e",
        "prepared source state",
    )
    require(
        sha256(ROOT / parent["last_patch"]) ==
        parent["last_patch_sha256"],
        "canonical parent patch",
    )

    source = contract["source"]
    for key in ("c", "header", "matrix"):
        require(sha256(ROOT / source[key]) == source[f"{key}_sha256"],
                f"source {key} identity")

    for script in (
        "source_edits.py", "validate_source.py", "validate_patches.py",
        "validate.py",
    ):
        ast.parse((HERE / "scripts" / script).read_text(), filename=script)

    source_edits = (HERE / "scripts/source_edits.py").read_text()
    for token in (
        "config MTK_RAM_CONSOLE_PARSER",
        "CONFIG_MTK_RAM_CONSOLE_PARSER) += mtk-ram-console.o",
        "source/mtk-ram-console.c",
        "source/mtk-ram-console.h",
    ):
        require(token in source_edits, f"source edit token: {token}")
    for forbidden in (
        "ioremap", "memremap", "readl(", "writel(", "psci_ops",
        "cpu_boot", "mt6797_a72_a34_evaluate",
    ):
        require(forbidden not in source_edits,
                f"forbidden source edit token: {forbidden}")

    c_source = (ROOT / source["c"]).read_text()
    header = (ROOT / source["header"]).read_text()
    require(c_source.count("KUNIT_CASE(mtk_ram_console_") == 8,
            "eight focused cases")
    require(c_source.count("get_unaligned_le32(bytes + off_pl)") == 1,
            "one raw status extraction")
    require("u32 preloader_status;" in header and "bool valid;" in header,
            "typed raw snapshot")
    for forbidden in (
        "ioremap", "memremap", "readl(", "writel(", "psci",
        "cpu_up", "cpu_boot", "reset_provenance", "safe_reset",
    ):
        require(forbidden not in c_source + header,
                f"forbidden source effect: {forbidden}")

    with (ROOT / source["matrix"]).open(newline="") as stream:
        rows = {row["id"]: row for row in csv.DictReader(stream,
                                                          delimiter="\t")}
    require(set(rows) == {
        "T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08",
        "D01", "D02", "D03", "D04",
    }, "test matrix inventory")

    generator = (HERE / "scripts/generate-on-buildbox").read_text()
    for token in (
        parent["source_state"], parent["mtk_soc_kconfig_sha256"],
        parent["mtk_soc_makefile_sha256"], "generated_patch_count=1",
        "status_extraction_count=1", "physical_mapping=none",
        "reset_classifier=none", "a34_caller=none",
        "hardware_action=none", "device_action=none",
        "boot_candidate=false",
    ):
        require(token in generator, f"generator token: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for token in (
        "generate-mtk-ram-console-parser-patch",
        "fetch-mtk-ram-console-parser-patch",
        "mainline-mtk-ram-console-parser-patch-generation",
        "status_extraction_count=1",
        "physical_mapping=none",
        "boot_candidate=false",
    ):
        require(token in buildbox, f"Buildbox lane token: {token}")

    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    require("three strict alignment rejections recorded" in readme and
            "checkpatch rejected one continuation-line" in readme and
            "third exact attempt" in readme and
            "rejected only that prototype" in readme and
            "No validated generated" in readme and
            "patch, compile result" in readme and
            "`inconclusive` pending exact Buildbox generation" in readme,
            "status is not overstated")
    for token in (
        "caller-owned byte buffer",
        "64-byte little-endian header",
        "Every bit pattern",
        "adds no reserved-memory lookup",
    ):
        require(token in design, f"design token: {token}")

    private_tokens = ("/" + "Users/", "/" + "home/", "mmc" + "blk")
    for path in HERE.rglob("*"):
        if path.is_file():
            text = path.read_text()
            for token in private_tokens:
                require(token not in text,
                        f"private token {token} in {path.name}")

    print("experiment=2026-08-21-mainline-mtk-ram-console-parser")
    print(f"parent_source_state={parent['source_state']}")
    print("selected_boundary=PURE_RETAINED_HEADER_PARSER")
    print("expected_patch=0304")
    print("status_extractions=1")
    print("kunit_cases=8")
    print("physical_mapping=none")
    print("reset_classifier=none")
    print("a34_caller=none")
    print("hardware_action=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("generation_lane=ready")
    print("result=pass")


if __name__ == "__main__":
    main()
