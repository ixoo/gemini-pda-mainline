#!/usr/bin/env python3
"""Validate the repository-side boot-status capture design."""

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
    require(contract["repository_parent"] ==
            "6be86b582a1fcb40d79126a6c83ad24f0e7ad65c",
            "repository parent")
    decision = contract["decision"]
    for key in ("readme", "design", "matrix"):
        require(sha256(ROOT / decision[key]) == decision[f"{key}_sha256"],
                f"decision {key} identity")
    require(decision["selected_boundary"] == "TOPRGU_CAPTURE_ONLY",
            "selected boundary")
    parent = contract["parent"]
    require(sha256(ROOT / parent["last_patch"]) ==
            parent["last_patch_sha256"], "canonical parent patch")
    require(parent["source_state"] ==
            "efc26dede64ec019c074d29f5cd625767f11fb5a16db376b1549f72a4614a735",
            "prepared source state")

    for script in ("source_edits.py", "validate_source.py",
                   "validate_patches.py", "validate.py"):
        ast.parse((HERE / "scripts" / script).read_text(), filename=script)

    source_edits = (HERE / "scripts/source_edits.py").read_text()
    for token in (
        "CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE",
        ".has_boot_status = true",
        "readl(mtk_wdt->wdt_base + WDT_STATUS)",
        "smp_store_release(&status->valid, true)",
        "EXPORT_SYMBOL_GPL(mtk_wdt_boot_status_snapshot)",
    ):
        require(token in source_edits, f"source edit token: {token}")
    for forbidden in ("writel(", "iowrite", "psci_ops", "cpu_boot",
                      "mt6797_a72_a34_evaluate"):
        require(forbidden not in source_edits,
                f"forbidden source edit token: {forbidden}")

    with (HERE / "results/test-matrix.tsv").open(newline="") as stream:
        rows = {row["id"]: row for row in csv.DictReader(stream, delimiter="\t")}
    require(set(rows) == {"T01", "T02", "T03", "T04",
                          "S01", "S02", "S03", "S04"},
            "test matrix inventory")

    header = (HERE / "source/mtk_wdt.h").read_text()
    require("u32 raw;" in header and "bool valid;" in header,
            "typed raw snapshot")
    require("reset_provenance" not in header and "safe_reset" not in header,
            "header contains no classifier")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for token in (
        "generate-mtk-wdt-boot-status-patch",
        "fetch-mtk-wdt-boot-status-patch",
        "mainline-mtk-wdt-boot-status-patch-generation",
        "status_read_count=1",
        "reset_classifier=none",
        "boot_candidate=false",
    ):
        require(token in buildbox, f"Buildbox lane token: {token}")

    design = (HERE / "DESIGN.md").read_text()
    readme = (HERE / "README.md").read_text()
    for token in (
        "exactly one `readl()`",
        "first-write-wins",
        "does not interpret the word as reset authority",
        "A valid raw snapshot cannot make the A34 evaluator input",
    ):
        require(token in design, f"design token: {token}")
    require("authorizes no device work" in readme and
            "No patch-generation," in readme and
            "compile, QEMU, boot, or device result" in readme,
            "current status is not overstated")

    generator = (HERE / "scripts/generate-on-buildbox").read_text()
    for token in (
        parent["source_state"], parent["watchdog_kconfig_sha256"],
        parent["mtk_wdt_source_sha256"],
        "generated_patch_count=1", "hardware_write=none",
        "device_action=none", "boot_candidate=false",
    ):
        require(token in generator, f"generator token: {token}")

    private_tokens = ("/" + "Users/", "/" + "home/", "mmc" + "blk")
    for path in HERE.rglob("*"):
        if path.is_file():
            text = path.read_text()
            for token in private_tokens:
                require(token not in text,
                        f"private token {token} in {path.name}")

    print("experiment=2026-08-21-mainline-mtk-wdt-boot-status-capture")
    print(f"parent_source_state={parent['source_state']}")
    print("selected_boundary=TOPRGU_CAPTURE_ONLY")
    print("expected_patch=0303")
    print("status_read_count=1")
    print("kunit_cases=4")
    print("reset_classifier=none")
    print("a34_caller=none")
    print("hardware_write=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("buildbox_generation_lane=ready")
    print("result=pass")


if __name__ == "__main__":
    main()
