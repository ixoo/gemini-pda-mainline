#!/usr/bin/env python3
"""Validate the repository-side pure A34 evaluator design."""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
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
    decision = contract["decision_contract"]
    decision_path = ROOT / decision["path"]
    require(sha256(decision_path) == decision["sha256"],
            "decision contract identity")
    require(decision["selected_boundary"] == "A34_ELIGIBILITY_EVALUATOR",
            "selected audit boundary")
    parent = contract["parent"]
    require(sha256(ROOT / parent["last_patch"]) == parent["last_patch_sha256"],
            "canonical parent patch")
    expected_patch = ROOT / contract["expected_patch"]
    require(expected_patch.is_file(), "canonical evaluator patch")
    require(sha256(expected_patch) == contract["expected_patch_sha256"],
            "canonical evaluator patch identity")
    generation = contract["validated_generation"]
    require(generation["repository_commit"] ==
            "6d1aea564cea147256ef6a6c5f56681b07f3343b" and
            generation["package"] ==
            "a72-a34-eligibility-patch-6d1aea564cea" and
            generation["result_commit"] ==
            "369ba0f889cba4161e2905b38f051b41e7eb4b7a",
            "validated Buildbox generation identity")
    build = contract["validated_build"]
    require(build["repository_commit"] ==
            "cd44cada028f24289fe0565ffc16ce7853eaff25" and
            build["profile"] == "a72-a34-eligibility-kunit" and
            build["kernel_release"] ==
            "7.1.3-gemini-a34-eligibility-kunit" and
            build["config_sha256"] ==
            "b4d9dbe348aa6df91982e3d49bda6804424b6a2dd58d05f1e3a7294a4e5cfc15" and
            build["image_sha256"] ==
            "031fd8f4b4c0162aeb729ecfbad34cc024117a191c97aabd55e6f6a04d2f0e92",
            "validated Buildbox build identity")
    qemu = contract["validated_qemu"]
    require(qemu["runner_version"] == "11.0.2" and
            qemu["suites"] == 1 and qemu["tests"] == 5 and
            qemu["failed"] == 0 and qemu["skipped"] == 0 and
            qemu["result"] == "pass",
            "validated focused QEMU result")

    scope = contract["scope"]
    require(scope["default_off"] and scope["hardware_free"],
            "positive scope")
    require(all(scope[name] is False for name in (
        "production_init_caller", "opens_owner", "state_mutation",
        "transaction_caller", "provider_call", "p27_p28_effect",
        "p30_mutation", "cpu_on", "cpu_off", "boot_veto_change",
        "build_before_signed_audit_push", "device_action", "boot_candidate",
    )), "negative scope")
    provenance = contract["provenance_sources"]
    require(provenance == {
        "existing_watchdog_class_reason": "nondiscriminating-not-accepted",
        "production_reset_owner": "unresolved",
        "private_replay_owner": "unresolved",
    }, "unresolved provenance owners")
    reset_audit = contract["reset_source_audit"]
    require(reset_audit["candidate"] ==
            "read-WDT_STATUS-offset-0x0c-after-ioremap-before-mtk_wdt_init" and
            reset_audit["status"].startswith("inconclusive-until-LK"),
            "reset-source candidate remains inconclusive")

    generator = (HERE / "scripts/generate-on-buildbox").read_text()
    require(f"PARENT_SOURCE_STATE={parent['source_state']}" in generator,
            "generator source-state pin")
    constants = {
        "arch/arm64/Kconfig": "ARM64_KCONFIG_SHA256",
        "arch/arm64/Kconfig.platforms": "ARM64_PLATFORM_KCONFIG_SHA256",
        "arch/arm64/kernel/Makefile": "ARM64_MAKEFILE_SHA256",
        "arch/arm64/kernel/smp.c": "ARM64_SMP_SHA256",
        "arch/arm64/include/asm/mt6797_a72_membership.h": "MEMBERSHIP_HEADER_SHA256",
        "arch/arm64/kernel/mt6797_a72_membership.c": "MEMBERSHIP_SOURCE_SHA256",
        "arch/arm64/kernel/mt6797_psci.c": "MT6797_PSCI_SHA256",
        "drivers/watchdog/mtk_wdt.c": "MTK_WDT_SOURCE_SHA256",
    }
    for path, name in constants.items():
        expected = contract["parent_source_files"][path]
        require(f"{name}={expected}" in generator,
                f"generator source pin: {path}")
    require("./scripts/build-kernel" not in generator,
            "generator is not a build backend")
    for marker in ("source-tree-integrity", "format-patch -1",
                   "git -C \"$work/verify\" am", "checkpatch.pl",
                   "production_hook=none", "opens_owner=false",
                   "hardware_action=none", "cpu_on=false"):
        require(marker in generator, f"generator marker: {marker}")
    buildbox = (ROOT / "scripts/buildbox").read_text()
    for marker in (
        "generate-a72-a34-eligibility-patch",
        "fetch-a72-a34-eligibility-patch",
        "mainline-a72-a34-eligibility-patch-generation",
        "a72-a34-eligibility-artifacts",
        "generated_patch_count=1",
        "production_hook=none",
        "opens_owner=false",
        "hardware_action=none",
        "device_action=none",
        "boot_candidate=false",
    ):
        require(marker in buildbox, f"Buildbox lane marker: {marker}")

    for relative in ("scripts/source_edits.py", "scripts/validate_source.py",
                     "scripts/validate_patches.py", "scripts/classify-kunit.py",
                     "scripts/test-kunit-classifier.py"):
        ast.parse((HERE / relative).read_text())
    for relative in (
        "scripts/generate-on-buildbox", "scripts/run-kunit-qemu",
        "scripts/source_edits.py", "scripts/validate_source.py",
        "scripts/validate_patches.py", "scripts/classify-kunit.py",
        "scripts/test-kunit-classifier.py", "scripts/validate.py",
    ):
        require((HERE / relative).stat().st_mode & 0o111,
                f"script executable: {relative}")
    test = (HERE / "source/mt6797-a72-a34-evaluator-test.c").read_text()
    require(test.count("KUNIT_CASE(mt6797_a34_") ==
            contract["tests"]["kunit_cases"], "KUnit case count")
    require("sizeof(*state->observation)" in test and
            "bytes[offset] ^= 1" in test, "every-byte observation mutation")
    require("MT6797_A72_A34_RESET_PLATFORM" in test and
            "MT6797_A72_A34_RESET_EXTERNAL" in test,
            "two accepted provenance cases")
    require("kunit_kzalloc" in test and
            "struct mt6797_a72_owner_snapshot before;" not in test,
            "large test state remains heap-backed")
    production_fragment = (
        ROOT / "configs/gemini-a72-a34-eligibility.fragment").read_text()
    test_fragment = (
        ROOT / "configs/gemini-a72-a34-eligibility-kunit.fragment").read_text()
    require("CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y" in
            production_fragment, "evaluator fragment")
    require("CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST=y" in
            test_fragment and "CONFIG_KUNIT=y" in test_fragment,
            "focused KUnit fragment")
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    require(profiles["a72-a34-eligibility"]["fragments"][-1] ==
            "configs/gemini-a72-a34-eligibility.fragment",
            "evaluator build profile")
    require(profiles["a72-a34-eligibility-kunit"]["fragments"][-2:] == [
        "configs/gemini-a72-a34-eligibility.fragment",
        "configs/gemini-a72-a34-eligibility-kunit.fragment",
    ], "focused KUnit build profile")
    series = (ROOT / "patches/series").read_text().splitlines()
    require(series[-1] ==
            "v7.1.3/0302-arm64-add-A72-A34-eligibility-evaluator.patch",
            "canonical patch ordering")
    runner = (HERE / "scripts/run-kunit-qemu").read_text()
    classifier = (HERE / "scripts/classify-kunit.py").read_text()
    for marker in ("-machine virt -cpu cortex-a53 -smp 4", "-nic none",
                   "CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST=y"):
        require(marker in runner, f"QEMU runner marker: {marker}")
    for marker in ("production_hook=none", "EXPECTED_CASES", "tests=5",
                   "opens_owner=false", "hardware_effect=none"):
        require(marker in classifier, f"classifier marker: {marker}")

    with (HERE / "results/test-matrix.tsv").open(newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    require([row["id"] for row in rows] ==
            [f"A34-{number:02d}" for number in range(1, 13)],
            "test matrix identity")
    expected_evidence = {
        "A34-01": "buildbox-pass",
        "A34-12": "source-validated",
    }
    require(all(row["evidence_state"] ==
                expected_evidence.get(row["id"], "qemu-pass")
                for row in rows), "final evidence status")

    build_receipt = (HERE / "results/buildbox-build-validated-20260821.txt").read_text()
    qemu_receipt = (HERE / "results/qemu-kunit-validated-20260821.txt").read_text()
    for marker in (
        "repository_commit=cd44cada028f24289fe0565ffc16ce7853eaff25",
        "profile=a72-a34-eligibility-kunit",
        "a34_evaluator_object=compiled",
        "a34_kunit_object=compiled",
        "package_checksums=pass",
        "boot_candidate=false",
        "result=pass",
    ):
        require(marker in build_receipt, f"build receipt marker: {marker}")
    for marker in (
        "suites=1", "tests=5", "failed=0", "skipped=0",
        "mt6797_a34_every_byte_mutation_test=pass",
        "mt6797_a34_admission_remains_closed_test=pass",
        "tap_summary=pass:5_fail:0_skip:0_total:5",
        "hardware_effect=none", "device_action=none",
        "boot_candidate=false", "result=pass",
    ):
        require(marker in qemu_receipt, f"QEMU receipt marker: {marker}")

    design = (HERE / "DESIGN.md").read_text()
    readme = (HERE / "README.md").read_text()
    for marker in ("ordinary-Linux-reboot provenance reject",
                   "explicitly owner-safe zero",
                   "writes no state", "no production A34 hook",
                   "Future reset-provenance candidate",
                   "cannot make the evaluator input true"):
        require(marker in design, f"design marker: {marker}")
    require("pure evaluator proven by Buildbox compile and focused QEMU KUnit"
            in readme and
            "No production reset or private-replay" in readme and
            "no device work was attempted" in readme,
            "current status is not overstated")
    require(not re.search(r"/Users/|BEGIN (?:RSA|OPENSSH|EC) PRIVATE KEY|IMEI",
                          design + readme), "no private material")

    print("experiment=2026-08-20-mainline-a72-a34-reset-bootstrap")
    print("parent_source_state=1db1fb912bc7a0f35e4511f314d4300e52d0ab4f687b4b06a1556d8b687b5f3b")
    print("expected_patch=0302")
    print("kunit_cases=5")
    print("classifier_mutations=8")
    print("production_hook=none")
    print("opens_owner=no")
    print("reset_provenance_owner=unresolved")
    print("private_replay_owner=unresolved")
    print("reset_provenance_candidate=toprgu-wdt-status-preinit-read")
    print("reset_provenance_candidate_state=inconclusive")
    print("signed_audit_prerequisite=satisfied")
    print("canonical_patch=validated")
    print("buildbox_compile=pass")
    print("qemu_suites=1")
    print("qemu_tests=5")
    print("qemu_failed=0")
    print("qemu_skipped=0")
    print("hardware_effect=no")
    print("device_action=no")
    print("result=pass")


if __name__ == "__main__":
    main()
