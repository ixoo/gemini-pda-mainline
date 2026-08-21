#!/usr/bin/env python3
"""Validate the admitted retained ram-console copy-owner design."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((HERE / "contract.json").read_text())
    require(contract["schema"] == 1, "contract schema")
    require(contract["repository_parent"] ==
            "851648127fc19d79c117c68ca5c9e97e047c92a4",
            "repository parent")

    decision = contract["decision"]
    require(decision["selected_boundary"] ==
            "ONE_SHOT_RETAINED_RAM_COPY_OWNER", "selected boundary")
    for key in ("audit_readme", "audit_design", "audit_matrix"):
        require(sha256(ROOT / decision[key]) == decision[f"{key}_sha256"],
                f"decision input: {key}")

    parent = contract["parent"]
    require(parent["source_state"] ==
            "6a904f3dbbaf8c7946d6a11c13fe768e16e63db6dd5650f2ad3aa57c8b830209",
            "prepared parent state")
    require(sha256(ROOT / parent["last_patch"]) ==
            parent["last_patch_sha256"], "parser parent patch")

    source = contract["source"]
    for key in ("binding", "reader", "header", "matrix"):
        require(sha256(ROOT / source[key]) == source[f"{key}_sha256"],
                f"source input: {key}")

    expected_paths = [entry["path"] for entry in contract["expected_patches"]]
    require(expected_paths == [
        "patches/v7.1.3/0305-dt-bindings-soc-mediatek-document-retained-ram-console.patch",
        "patches/v7.1.3/0306-soc-mediatek-add-retained-ram-console-copy-owner.patch",
        "patches/v7.1.3/0307-arm64-dts-mediatek-add-Gemini-ram-console-reader.patch",
    ], "expected patch inventory")
    for entry in contract["expected_patches"]:
        require(sha256(ROOT / entry["path"]) == entry["sha256"],
                f"canonical patch: {entry['path']}")
    series = (ROOT / "patches/series").read_text().splitlines()
    require(series[-3:] == [path.removeprefix("patches/")
                            for path in expected_paths],
            "canonical series tail")

    generation = contract["validated_generation"]
    receipt = ROOT / generation["receipt"]
    require(sha256(receipt) == generation["receipt_sha256"],
            "generation receipt identity")
    receipt_text = receipt.read_text()
    for key in (
        "repository_commit", "baseline_commit", "result_commit",
        "package_sha256s_sha256", "generation_sha256",
        "checkpatch_sha256",
    ):
        require(f"{key}={generation[key]}" in receipt_text,
                f"generation receipt: {key}")
    for token in (
        "generated_patch_count=3", "binding_patch_count=1",
        "driver_patch_count=1", "dt_patch_count=1", "kunit_case_count=7",
        "physical_map_call_count=1", "physical_unmap_call_count=1",
        "copy_attempt_limit=1", "dt_default=disabled", "raw_export=none",
        "reset_classifier=none", "secure_epoch_authority=none",
        "a34_caller=none", "hardware_write=none", "device_action=none",
        "boot_candidate=false", "source_validation=pass",
        "patch_validation=pass", "replay=pass", "checkpatch_errors=0",
        "checkpatch_warnings=0", "checkpatch_checks=0",
        "compile=not-run", "qemu=not-run", "result=pass",
    ):
        require(token in receipt_text, f"generation token: {token}")

    build = contract["validated_build"]
    build_receipt = ROOT / build["receipt"]
    require(sha256(build_receipt) == build["receipt_sha256"],
            "build receipt identity")
    build_text = build_receipt.read_text()
    for key in (
        "repository_commit", "profile", "kernel_release", "package",
        "package_sha256s_sha256", "build_provenance_sha256",
        "source_sha256", "patchset_sha256", "config_sha256", "image_sha256",
    ):
        require(f"{key}={build[key]}" in build_text, f"build receipt: {key}")
    for token in (
        "patch_count=296", "fragment_count=11", "dtb_count=119",
        "target_architecture=arm64", "modules_built=false",
        "config_parser=y", "config_reader=y", "config_reader_kunit_test=y",
        "snapshot_getter_symbol_count=1", "kunit_test_symbol_count=7",
        "gemini_dtb_compile=pass", "package_checksums=pass",
        "compile=pass", "link=pass", "dt_binding_check=not-run",
        "dt_binding_check_reason=dtschema-absent-on-buildbox",
        "hardware_write=none", "device_action=none", "boot_candidate=false",
        "result=pass",
    ):
        require(token in build_text, f"build token: {token}")

    qemu = contract["validated_qemu"]
    qemu_receipt = ROOT / qemu["receipt"]
    require(sha256(qemu_receipt) == qemu["receipt_sha256"],
            "QEMU receipt identity")
    qemu_text = qemu_receipt.read_text()
    for key in (
        "repository_commit", "profile", "image_sha256", "config_sha256",
        "raw_log_sha256",
    ):
        require(f"{key}={qemu[key]}" in qemu_text, f"QEMU receipt: {key}")
    for token in (
        "network=none", "physical_mapping=not-executed-dt-consumer-disabled",
        "suites=1", "tests=7", "failed=0", "skipped=0",
        "tap_summary=pass:7_fail:0_skip:0_total:7",
        "post_test_state=expected_vm_rootfs_panic", "qemu_exit=124",
        "classifier_self_test=pass",
        "dt_binding_check=not-run-dtschema-absent-on-buildbox",
        "reset_classifier=none", "secure_epoch_authority=none",
        "a34_caller=none", "hardware_write=none", "device_action=none",
        "boot_candidate=false", "result=pass",
    ):
        require(token in qemu_text, f"QEMU token: {token}")
    for case in (
        "invalid_arguments", "exact_copy", "copy_failure", "parser_failure",
        "second_capture", "source_independence", "every_bit",
    ):
        require(f"mtk_ram_console_reader_{case}_test=pass" in qemu_text,
                f"QEMU case: {case}")
    require(qemu["tests"] == 7 and qemu["failed"] == 0 and
            qemu["skipped"] == 0 and qemu["result"] == "pass",
            "QEMU result contract")

    with (ROOT / source["matrix"]).open(newline="") as stream:
        rows = {row["id"]: row for row in csv.DictReader(stream, delimiter="\t")}
    require(set(rows) == {
        *(f"T0{index}" for index in range(1, 8)),
        *(f"D0{index}" for index in range(1, 6)),
    }, "test matrix inventory")

    reader = (ROOT / source["reader"]).read_text()
    header = (ROOT / source["header"]).read_text()
    require(reader.count("memremap(") == 1, "one physical map call")
    require(reader.count("memunmap(") == 1, "one physical unmap call")
    require(reader.count("KUNIT_CASE(mtk_ram_console_reader_") == 7,
            "seven KUnit cases")
    require("kfree_sensitive(buffer);" in reader, "private copy clearing")
    require("return -EALREADY;" in reader, "one-attempt latch")
    require("mtk_ram_console_snapshot_get" in reader + header,
            "typed snapshot getter")
    for token in (
        "ioremap(", "devm_memremap(", "readl(", "writel(", "debugfs",
        "proc_create", "nvmem", "0x44400000", "cpu_up", "cpu_boot",
        "psci_ops", "reset_provenance", "safe_reset",
    ):
        require(token not in reader + header,
                f"forbidden source token: {token}")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    require(profiles["mtk-ram-console-reader"]["fragments"][-1:] == [
        "configs/gemini-mtk-ram-console-reader.fragment",
    ], "reader profile")
    require(profiles["mtk-ram-console-reader-kunit"]["fragments"][-2:] == [
        "configs/gemini-mtk-ram-console-reader.fragment",
        "configs/gemini-mtk-ram-console-reader-kunit.fragment",
    ], "reader KUnit profile")

    for script in ("source_edits.py", "validate_source.py",
                   "validate_patches.py", "validate.py", "classify-kunit.py",
                   "test-kunit-classifier.py"):
        ast.parse((HERE / "scripts" / script).read_text(), filename=script)
    generator = (HERE / "scripts/generate-on-buildbox").read_text()
    for token in (
        parent["source_state"], "generated_patch_count=3",
        "physical_map_call_count=1", "physical_unmap_call_count=1",
        "dt_default=disabled", "secure_epoch_authority=none",
        "a34_caller=none", "hardware_write=none", "device_action=none",
        "boot_candidate=false",
    ):
        require(token in generator, f"generator token: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for token in (
        "generate-mtk-ram-console-copy-owner-patches",
        "fetch-mtk-ram-console-copy-owner-patches",
        "mainline-mtk-ram-console-copy-owner-patch-generation",
    ):
        require(token in buildbox, f"Buildbox wrapper token: {token}")

    runner = (HERE / "scripts/run-kunit-qemu").read_text()
    for token in (
        "mtk-ram-console-reader-kunit", "CONFIG_MTK_RAM_CONSOLE_READER=y",
        "CONFIG_MTK_RAM_CONSOLE_READER_KUNIT_TEST=y", "-nic none",
        "timeout --signal=TERM 45", "refusing to overwrite a raw log",
    ):
        require(token in runner, f"QEMU runner token: {token}")

    require(contract["expected_kunit_cases"] == 7, "KUnit case contract")
    require(contract["physical_map_calls"] == 1, "map-call contract")
    require(contract["physical_unmap_calls"] == 1, "unmap-call contract")
    require(contract["copy_attempt_limit"] == 1, "copy-attempt contract")
    for key in (
        "dt_default_enabled", "raw_export", "reset_classifier",
        "secure_epoch_authority", "a34_caller", "hardware_write",
        "device_action", "boot_candidate",
    ):
        require(contract[key] is False, f"effect boundary: {key}")

    forbidden = ("/" + "Users/", "/" + "home/", "mmc" + "blk")
    for path in HERE.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text()
        for token in forbidden:
            require(token not in text, f"private token {token} in {path.name}")

    print("experiment=2026-08-21-mainline-mtk-ram-console-copy-owner")
    print("validation=pass")
    print("canonical_patch_count=3")
    print("manifest_profiles=99")
    print("kunit_case_count=7")
    print("physical_map_call_count=1")
    print("physical_unmap_call_count=1")
    print("copy_attempt_limit=1")
    print("dt_default=disabled")
    print("secure_epoch_authority=none")
    print("a34_caller=none")
    print("hardware_write=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("compile=pass")
    print("gemini_dtb_compile=pass")
    print("dt_binding_check=not-run-dtschema-absent-on-buildbox")
    print("qemu=pass")


if __name__ == "__main__":
    main()
