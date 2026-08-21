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
    require(all(row["evidence_state"] == "design-frozen" for row in rows),
            "design evidence status")

    design = (HERE / "DESIGN.md").read_text()
    readme = (HERE / "README.md").read_text()
    for marker in ("ordinary-Linux-reboot provenance reject",
                   "explicitly owner-safe zero",
                   "writes no state", "no production A34 hook",
                   "Future reset-provenance candidate",
                   "cannot make the evaluator input true"):
        require(marker in design, f"design marker: {marker}")
    require("no kernel patch or build yet" in readme,
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
    print("build_prerequisite=signed-audit-push")
    print("hardware_effect=no")
    print("device_action=no")
    print("result=pass")


if __name__ == "__main__":
    main()
