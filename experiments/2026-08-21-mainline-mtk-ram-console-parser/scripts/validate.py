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

    expected_patch = contract["expected_patch"]
    patch_path = ROOT / expected_patch["path"]
    require(patch_path.name == expected_patch["filename"],
            "canonical patch filename")
    require(sha256(patch_path) == expected_patch["sha256"],
            "canonical patch identity")
    series = (ROOT / "patches/series").read_text().splitlines()
    require(series[-1] == "v7.1.3/" + expected_patch["filename"],
            "canonical patch is series tail")

    generation = contract["validated_generation"]
    receipt_path = ROOT / generation["receipt"]
    require(sha256(receipt_path) == generation["receipt_sha256"],
            "validated generation receipt identity")
    receipt = receipt_path.read_text()
    for key in (
        "repository_commit", "baseline_commit", "result_commit",
        "package_sha256s_sha256", "generation_sha256",
        "checkpatch_sha256",
    ):
        require(f"{key}={generation[key]}" in receipt,
                f"validated generation {key}")
    for token in (
        f"generated_patch_sha256={expected_patch['sha256']}",
        f"canonical_patch={expected_patch['path']}",
        f"canonical_patch_sha256={expected_patch['sha256']}",
        "generated_patch_count=1", "status_extraction_count=1",
        "kunit_case_count=8", "replay=pass", "checkpatch_errors=0",
        "checkpatch_warnings=0", "checkpatch_checks=0",
        "physical_mapping=none", "reset_classifier=none",
        "a34_caller=none", "hardware_action=none", "device_action=none",
        "boot_candidate=false", "compile=not-run", "qemu=not-run",
        "result=pass",
    ):
        require(token in receipt, f"validated generation token: {token}")
    require(generation["replay"] == "pass" and
            generation["checkpatch_errors"] == 0 and
            generation["checkpatch_warnings"] == 0 and
            generation["checkpatch_checks"] == 0 and
            generation["compile"] == "not-run" and
            generation["qemu"] == "not-run",
            "generation result contract")

    build = contract["validated_build"]
    build_receipt_path = ROOT / build["receipt"]
    require(sha256(build_receipt_path) == build["receipt_sha256"],
            "validated build receipt identity")
    build_receipt = build_receipt_path.read_text()
    for key in (
        "repository_commit", "profile", "kernel_release", "package",
        "package_sha256s_sha256", "build_provenance_sha256",
        "source_sha256", "patchset_sha256", "config_sha256",
        "image_sha256", "image_gzip_sha256",
    ):
        require(f"{key}={build[key]}" in build_receipt,
                f"validated build {key}")
    for token in (
        "repository_dirty=false", "patch_count=293", "fragment_count=11",
        "target_architecture=arm64", "modules_built=false",
        "config_parser=y", "config_parser_kunit_test=y", "config_kunit=y",
        "parser_symbol_count=1", "kunit_test_symbol_count=8",
        "package_checksums=pass", "compile=pass", "link=pass",
        "hardware_write=none", "device_action=none", "boot_candidate=false",
        "result=pass",
    ):
        require(token in build_receipt, f"validated build token: {token}")
    require(build["result"] == "pass", "validated build result")

    qemu = contract["validated_qemu"]
    qemu_receipt_path = ROOT / qemu["receipt"]
    require(sha256(qemu_receipt_path) == qemu["receipt_sha256"],
            "validated QEMU receipt identity")
    qemu_receipt = qemu_receipt_path.read_text()
    for key in ("observed_utc", "runner_version", "raw_log_sha256"):
        require(f"{key}={qemu[key]}" in qemu_receipt,
                f"validated QEMU {key}")
    for key in ("suites", "tests", "failed", "skipped"):
        require(f"{key}={qemu[key]}" in qemu_receipt,
                f"validated QEMU {key}")
    for token in (
        f"repository_commit={build['repository_commit']}",
        f"profile={build['profile']}",
        f"kernel_release={build['kernel_release']}",
        f"image_sha256={build['image_sha256']}",
        f"config_sha256={build['config_sha256']}",
        "runner=qemu-system-aarch64", "machine=virt", "cpu=cortex-a53",
        "vcpus=4", "network=none",
        "physical_mapping=not-executed-parser-only",
        "tap_summary=pass:8_fail:0_skip:0_total:8",
        "post_test_state=expected_vm_rootfs_panic", "qemu_exit=124",
        "reset_classifier=none", "a34_caller=none", "hardware_write=none",
        "device_action=none", "boot_candidate=false", "result=pass",
    ):
        require(token in qemu_receipt, f"validated QEMU token: {token}")
    for case in (
        "invalid_arguments", "truncated", "signature", "buffer_size",
        "preloader_layout", "lk_layout", "exact", "every_bit",
    ):
        require(f"mtk_ram_console_{case}_test=pass" in qemu_receipt,
                f"validated QEMU case: {case}")
    require(qemu["suites"] == 1 and qemu["tests"] == 8 and
            qemu["failed"] == 0 and qemu["skipped"] == 0 and
            qemu["result"] == "pass", "validated QEMU result")

    for script in (
        "source_edits.py", "validate_source.py", "validate_patches.py",
        "validate.py", "classify-kunit.py", "test-kunit-classifier.py",
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

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    require(profiles["mtk-ram-console-parser"]["fragments"][-1:] == [
        "configs/gemini-mtk-ram-console-parser.fragment",
    ], "source profile fragment")
    require(profiles["mtk-ram-console-parser-kunit"]["fragments"][-2:] == [
        "configs/gemini-mtk-ram-console-parser.fragment",
        "configs/gemini-mtk-ram-console-parser-kunit.fragment",
    ], "KUnit profile fragments")
    require((ROOT / "configs/gemini-mtk-ram-console-parser.fragment").read_text().count(
        "CONFIG_MTK_RAM_CONSOLE_PARSER=y") == 1,
        "source configuration")
    kunit_fragment = (
        ROOT / "configs/gemini-mtk-ram-console-parser-kunit.fragment"
    ).read_text()
    require("CONFIG_KUNIT=y" in kunit_fragment and
            "CONFIG_MTK_RAM_CONSOLE_PARSER_KUNIT_TEST=y" in kunit_fragment,
            "KUnit configuration")

    classifier = (HERE / "scripts/classify-kunit.py").read_text()
    runner = (HERE / "scripts/run-kunit-qemu").read_text()
    classifier_test = (HERE / "scripts/test-kunit-classifier.py").read_text()
    for token in (
        'PROFILE = "mtk-ram-console-parser-kunit"',
        'SUITE = "mtk-ram-console-parser"', "1..8", "pass:8",
        "physical_mapping=not-executed-parser-only",
        "reset_classifier=none", "a34_caller=none",
        "boot_candidate=false",
    ):
        require(token in classifier, f"classifier token: {token}")
    for case in (
        "invalid_arguments", "truncated", "signature", "buffer_size",
        "preloader_layout", "lk_layout", "exact", "every_bit",
    ):
        require(classifier.count(f"mtk_ram_console_{case}_test") == 1,
                f"classifier exact case: {case}")
    for token in (
        "EXPECTED_PROFILE=mtk-ram-console-parser-kunit",
        "CONFIG_MTK_RAM_CONSOLE_PARSER=y",
        "CONFIG_MTK_RAM_CONSOLE_PARSER_KUNIT_TEST=y",
        "-nic none", "--qemu-exit",
    ):
        require(token in runner, f"QEMU runner token: {token}")
    require("pass:8 fail:0 skip:0 total:8" in classifier_test,
            "classifier self-test exact summary")

    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    require(
            "canonical patch `0304` proven by Buildbox compile and focused QEMU KUnit"
            in readme and
            "checkpatch rejected one continuation-line" in readme and
            "third exact attempt" in readme and
            "rejected only that prototype" in readme and
            "fourth exact Buildbox generation" in readme and
            "zero errors, warnings, or checks across 397 lines" in readme and
            "all passed with zero failures or skips" in readme and
            "`pass` for the pure retained-header parser boundary" in readme and
            "This does not prove a physical mapping owner" in readme,
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
        if path.is_file() and "__pycache__" not in path.parts and \
                path.suffix != ".pyc":
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
    print(f"canonical_patch_sha256={expected_patch['sha256']}")
    print("generation=pass")
    print("compile=pass")
    print("qemu_suites=1")
    print("qemu_tests=8")
    print("qemu_failed=0")
    print("qemu_skipped=0")
    print("qemu=pass")
    print("result=pass")


if __name__ == "__main__":
    main()
