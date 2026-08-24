#!/usr/bin/env python3
"""Validate the repository-side A72 direct-state compositor definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PARENT_PATCH = (
    ROOT / "patches/v7.1.3/"
    "0336-pstore-qualify-Gemini-protected-clock-call-in-first-dmesg.patch"
)
PARENT_PATCH_SHA256 = (
    "97394ab84b4f0fc68f69388a8456a6f82321f2597405b9f23c253949ecf7033f"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    readme = (EXPERIMENT / "README.md").read_text()
    source_edits = (EXPERIMENT / "scripts/source_edits.py").read_text()
    source_validator = (EXPERIMENT / "scripts/validate_source.py").read_text()
    generator = (EXPERIMENT / "scripts/generate-on-buildbox").read_text()
    stack_edits = (EXPERIMENT / "scripts/stack_source_edits.py").read_text()
    stack_validator = (
        EXPERIMENT / "scripts/validate_stack_source.py"
    ).read_text()
    stack_generator = (
        EXPERIMENT / "scripts/generate-stack-fix-on-buildbox"
    ).read_text()
    target_edits = (EXPERIMENT / "scripts/target_fix_edits.py").read_text()
    target_validator = (
        EXPERIMENT / "scripts/validate_target_fix_source.py"
    ).read_text()
    target_patch_validator = (
        EXPERIMENT / "scripts/validate_target_fix_patch.py"
    ).read_text()
    target_generator = (
        EXPERIMENT / "scripts/generate-target-fix-on-buildbox"
    ).read_text()
    buildbox = (ROOT / "scripts/buildbox").read_text()
    runner = (EXPERIMENT / "scripts/run-kunit-qemu").read_text()
    classifier = (EXPERIMENT / "scripts/classify-kunit.py").read_text()
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    series = (ROOT / "patches/series").read_text().splitlines()

    require(contract["experiment"] == EXPERIMENT.name, "experiment identity")
    require(contract["repository_parent"] ==
            "a8734f1dc03050a7192a5d6c8b1b9fe0cae6216b",
            "repository parent")
    require(contract["prepared_source_state"] ==
            "e321876084d9f2250fbb0a76e5deded87499e65d7c131daa5117023275d3e30b",
            "prepared source state")
    require(contract["prepared_source_integrity"] ==
            "56230cbfa53d3ba7de0d214ce74848baa2d8a05ba401c4a9b5fa9105f7938af4",
            "prepared source integrity")
    require(sha256(PARENT_PATCH) == PARENT_PATCH_SHA256,
            "canonical parent patch")
    require(contract["patches"] == [
        "0337-arm64-add-closed-A72-direct-state-compositor.patch",
        "0338-arm64-test-closed-A72-direct-state-compositor.patch",
    ], "patch order")
    generation = contract["patch_generation"]
    require(generation["repository_commit"] ==
            "24bc92a7ce25c08e69c7e22e03f39b698a91e120",
            "generation repository commit")
    require(generation["exact_replay"] is True,
            "generated patches were not exactly replayed")
    require(generation["checkpatch"] == "0 errors, 0 warnings, 0 checks",
            "strict checkpatch result")
    require(generation["boot_candidate"] is False,
            "generation promoted to boot candidate")
    for relative, expected in generation["patch_sha256"].items():
        require(sha256(ROOT / relative) == expected,
                f"admitted patch identity {relative}")
    require(series[-5:-3] == [
        "v7.1.3/0337-arm64-add-closed-A72-direct-state-compositor.patch",
        "v7.1.3/0338-arm64-test-closed-A72-direct-state-compositor.patch",
    ], "canonical initial patch order")
    attempts = contract["compile_attempts"]
    require(len(attempts) == 3, "compile attempt count")
    attempt = attempts[0]
    require(attempt["repository_commit"] ==
            "0dbe657dbec405253d06f8653da6a421f60e8f0b",
            "compile commit")
    require(attempt["build_exit"] == 0 and
            attempt["artifact_validation"] == "pass",
            "compile artifact result")
    require(attempt["classification"] == "rejected-stack-safety",
            "compile stack classification")
    require(attempt["introduced_frame_warning_count"] == 10 and
            attempt["production_frame_warning_count"] == 2 and
            attempt["kunit_frame_warning_count"] == 8,
            "compile stack warning counts")
    require(attempt["qemu_run"] is False and
            attempt["boot_candidate"] is False,
            "rejected compile execution closure")
    evidence = (EXPERIMENT / attempt["evidence"]).read_text()
    for token in (
        "classification=rejected-stack-safety",
        "production_frame_mt6797_a72_direct_owner_pristine_locked_bytes=33312",
        "production_frame_mt6797_a72_direct_state_snapshot_locked_bytes=66880",
        "kunit_frame_direct_snapshot_success_bytes=100944",
        "qemu_run=false", "device_action=none", "boot_candidate=false",
    ):
        require(token in evidence, f"compile evidence {token}")
    attempt = attempts[1]
    require(attempt["repository_commit"] ==
            "a0e5ff3a74f391812ee1998fa714db96f8c7093c",
            "stack-safe compile commit")
    require(attempt["build_exit"] == 0 and
            attempt["artifact_validation"] == "pass",
            "stack-safe compile artifact result")
    require(attempt["classification"] == "pass-stack-safety",
            "stack-safe compile classification")
    require(attempt["introduced_frame_warning_count"] == 0 and
            attempt["production_frame_warning_count"] == 0 and
            attempt["kunit_frame_warning_count"] == 0 and
            attempt["inherited_frame_warning_count"] == 2,
            "stack-safe compile warning counts")
    require(attempt["qemu_run"] is True and
            attempt["boot_candidate"] is False,
            "stack-safe compile execution scope")
    evidence = (EXPERIMENT / attempt["evidence"]).read_text()
    for token in (
        "classification=pass-stack-safety",
        "introduced_frame_warning_count=0",
        "inherited_frame_warning_count=2",
        "qemu_run=true", "device_action=none", "boot_candidate=false",
    ):
        require(token in evidence, f"stack-safe compile evidence {token}")
    attempt = attempts[2]
    require(attempt["repository_commit"] ==
            "9e8ed80cb9d50c53559de6c60ee7315d61997eaf",
            "target-fixed compile commit")
    require(attempt["patchset_sha256"] ==
            "c67e2c322a81715bba53a79d53587268ff4d81be2d49fefc050fb3499af6a95a",
            "target-fixed compile patchset")
    require(attempt["build_exit"] == 0 and
            attempt["artifact_validation"] == "pass" and
            attempt["classification"] == "pass-stack-safety",
            "target-fixed compile result")
    require(attempt["introduced_frame_warning_count"] == 0 and
            attempt["production_frame_warning_count"] == 0 and
            attempt["kunit_frame_warning_count"] == 0 and
            attempt["inherited_frame_warning_count"] == 2,
            "target-fixed compile warning counts")
    require(attempt["qemu_run"] is True and
            attempt["boot_candidate"] is False,
            "target-fixed compile execution scope")
    evidence = (EXPERIMENT / attempt["evidence"]).read_text()
    for token in (
        "repository_commit=9e8ed80cb9d50c53559de6c60ee7315d61997eaf",
        "patchset_sha256=c67e2c322a81715bba53a79d53587268ff4d81be2d49fefc050fb3499af6a95a",
        "classification=pass-stack-safety",
        "introduced_frame_warning_count=0",
        "inherited_frame_warning_count=2",
        "qemu_run=true", "device_action=none", "boot_candidate=false",
    ):
        require(token in evidence, f"target-fixed compile evidence {token}")
    stack_fix = contract["stack_fix_definition"]
    require(stack_fix["prepared_source_state"] ==
            "08ad5389a1cf831f13ad410da5d74b17a58d8c05c8ab05459f3568e47c4a41a1",
            "stack-fix prepared source")
    require(stack_fix["prepared_source_integrity"] ==
            "4f812300aa0171cfbb91a645de62e1daff8d73a0200357a281a2cae7b053191a",
            "stack-fix prepared integrity")
    require(stack_fix["patches"] == [
        "0339-arm64-move-A72-direct-state-workspace-off-stack.patch",
        "0340-arm64-move-A72-direct-state-KUnit-state-off-stack.patch",
    ], "stack-fix patch order")
    require(stack_fix["generated"] is True and
            stack_fix["boot_candidate"] is False,
            "stack-fix generation phase")
    stack_generation = stack_fix["generation"]
    require(stack_generation["repository_commit"] ==
            "6805c496112680caeb92b8e36bfd5aa34773f2a3",
            "stack generation commit")
    require(stack_generation["exact_replay"] is True,
            "stack exact replay")
    require(stack_generation["checkpatch"] ==
            "0 errors, 0 warnings, 0 checks",
            "stack strict checkpatch")
    for relative, expected in stack_generation["patch_sha256"].items():
        require(sha256(ROOT / relative) == expected,
                f"stack patch identity {relative}")
    require(series[-3:-1] == [
        "v7.1.3/0339-arm64-move-A72-direct-state-workspace-off-stack.patch",
        "v7.1.3/0340-arm64-move-A72-direct-state-KUnit-state-off-stack.patch",
    ], "canonical stack-fix tail")
    qemu_attempts = contract["qemu_attempts"]
    require(len(qemu_attempts) == 2, "QEMU attempt count")
    qemu = qemu_attempts[0]
    require(qemu["repository_commit"] ==
            "a0e5ff3a74f391812ee1998fa714db96f8c7093c",
            "QEMU attempt commit")
    require(qemu["network"] == "none" and qemu["tests"] == 7 and
            qemu["passed"] == 6 and qemu["failed"] == 1,
            "QEMU rejected test inventory")
    require(qemu["classification"] ==
            "rejected-test-target-contract" and
            qemu["failing_case"] == "direct_snapshot_success",
            "QEMU target-contract classification")
    require(qemu["expected_errno"] == "-EAGAIN" and
            qemu["observed_errno"] == "-EINVAL" and
            qemu["incorrect_target"] == "CPUHP_OFFLINE" and
            qemu["required_target"] == "CPUHP_ONLINE",
            "QEMU target mismatch")
    require(qemu["boot_candidate"] is False,
            "rejected QEMU promoted to boot candidate")
    qemu_evidence = (EXPERIMENT / qemu["evidence"]).read_text()
    for token in (
        "passed=6", "failed=1",
        "failing_assertion=preflight_before_expected_minus_EAGAIN_observed_minus_EINVAL",
        "preflight_target=CPUHP_OFFLINE",
        "admission_contract_target=CPUHP_ONLINE",
        "owner_preservation=pass", "lifecycle_preservation=pass",
        "classification=rejected-test-target-contract",
        "device_action=none", "boot_candidate=false",
    ):
        require(token in qemu_evidence, f"QEMU evidence {token}")
    qemu = qemu_attempts[1]
    require(qemu["repository_commit"] ==
            "9e8ed80cb9d50c53559de6c60ee7315d61997eaf",
            "passing QEMU commit")
    require(qemu["network"] == "none" and qemu["tests"] == 7 and
            qemu["passed"] == 7 and qemu["failed"] == 0 and
            qemu["skipped"] == 0,
            "passing QEMU test inventory")
    require(qemu["classification"] == "pass-hardware-free" and
            qemu["physical_reader_callers"] == 0 and
            qemu["hardware_effect"] is False and
            qemu["opens_owner"] is False and
            qemu["state_mutation"] is False and
            qemu["transaction_caller"] is False and
            qemu["cpu_on"] is False and qemu["cpu_off"] is False and
            qemu["boot_candidate"] is False,
            "passing QEMU scope closure")
    qemu_evidence = (EXPERIMENT / qemu["evidence"]).read_text()
    for token in (
        "tests=7", "passed=7", "failed=0", "skipped=0",
        "direct_snapshot_success=pass",
        "direct_unregister_closes_source=pass",
        "tap_summary=pass:7_fail:0_skip:0_total:7",
        "classification=pass-hardware-free",
        "physical_reader_callers=0", "hardware_effect=none",
        "device_action=none", "boot_candidate=false",
        "opens_owner=false", "state_mutation=false",
        "transaction_caller=false", "cpu_on=false", "cpu_off=false",
    ):
        require(token in qemu_evidence, f"passing QEMU evidence {token}")
    target_fix = contract["target_fix_definition"]
    require(target_fix["prepared_source_state"] ==
            "80ea4453047c0328efbb0361a1b2b26065b79011bbfbff82f1c9cc02d047ac46",
            "target-fix prepared source")
    require(target_fix["prepared_source_integrity"] ==
            "f4d816c74678b80e20ad920e81850e4f111cf50f1137271fdf265dc8bb12a0c8",
            "target-fix prepared integrity")
    require(target_fix["canonical_parent"] ==
            "patches/v7.1.3/0340-arm64-move-A72-direct-state-KUnit-state-off-stack.patch",
            "target-fix canonical parent")
    require(target_fix["canonical_parent_test_sha256"] ==
            "fb339b4e802a4775d2a598834c598f641a1e1089bd296ac98fa234bd2fdd11e6",
            "target-fix reconstructed parent")
    require(target_fix["canonical_parent_membership_sha256"] ==
            "38e3cc51c879ed1319d124aa9eb021ab8342d00d52499d4bf06228a9f290f8f4",
            "target-fix membership parent")
    require(target_fix["patch"] ==
            "0341-arm64-fix-A72-direct-state-preflight-target-test.patch",
            "target-fix patch name")
    require(target_fix["generated"] is True and
            target_fix["changed_file_count"] == 1 and
            target_fix["changed_test_call_count"] == 2 and
            target_fix["production_code_change"] is False and
            target_fix["boot_candidate"] is False,
            "target-fix definition scope")
    require(target_fix["incorrect_target"] == "CPUHP_OFFLINE" and
            target_fix["required_target"] == "CPUHP_ONLINE" and
            target_fix["expected_closed_result"] == "-EAGAIN",
            "target-fix semantic correction")
    target_generation = target_fix["generation"]
    require(target_generation["repository_commit"] ==
            "27a0d08b5306a206d86c5748705db2107c52f7eb",
            "target generation commit")
    require(target_generation["canonical_parent_commit"] ==
            "eeb1ce73b12d7376b6aa09d642632987154dd91d" and
            target_generation["result_commit"] ==
            "1ee2d4e8006d4ecddd66c7cc7df948d3c6eb0a8a",
            "target generation commits")
    require(target_generation["exact_replay"] is True and
            target_generation["checkpatch"] ==
            "0 errors, 0 warnings, 0 checks",
            "target generation validation")
    for relative, expected in target_generation["patch_sha256"].items():
        require(sha256(ROOT / relative) == expected,
                f"target patch identity {relative}")
    require(series[-1] ==
            "v7.1.3/0341-arm64-fix-A72-direct-state-preflight-target-test.patch",
            "canonical target-fix tail")
    require(contract["owner_order"] == [
        "cpu_hotplug_lock_read", "a72_transition_lock",
        "direct_state_source_registry_lock", "injected_source_callback",
    ], "owner order")
    for field in (
        "physical_reader_callers", "a34_abi_change", "lifecycle_publication",
        "dt_enablement", "hardware_operation", "cpu_on", "cpu_off",
        "device_action", "boot_candidate",
    ):
        required = 0 if field == "physical_reader_callers" else False
        require(contract["scope"][field] == required, f"scope {field}")

    source_files = {
        path.name: sha256(path)
        for path in sorted((EXPERIMENT / "source").iterdir()) if path.is_file()
    }
    require(contract["source_templates"] == source_files,
            "source template identities")
    combined = "\n".join(
        path.read_text() for path in sorted((EXPERIMENT / "source").iterdir())
        if path.is_file()
    )
    for token in (
        "cpus_read_lock();", "mutex_lock(&a72_transition_lock);",
        "mutex_lock(&a72_direct_source_registry_lock);",
        "memset(snapshot, 0, sizeof(*snapshot));",
        "source->platform.valid", "KUNIT_CASE(direct_snapshot_success)",
    ):
        require(token in combined, f"source invariant {token}")
    for forbidden in (
        "mt6797_a72_provider_snapshot(",
        "mt6797_a72_platform_state_snapshot(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(", "arm_smccc_smc(",
        "readl(", "writel(", "cpu_up(", "cpu_down(",
    ):
        require(forbidden not in combined, f"source effect {forbidden}")

    require("choices=(\"core\", \"tests\")" in source_edits,
            "two-phase deterministic editor")
    require("physical_reader_callers=0" in source_validator,
            "source validator closure")
    require("PARENT_SOURCE_STATE=" + contract["prepared_source_state"] in generator,
            "generator source pin")
    require("PARENT_SOURCE_INTEGRITY=" +
            contract["prepared_source_integrity"] in generator,
            "generator integrity pin")
    require("generated_patch_count=2" in generator,
            "generator patch count")
    require('choices=("core", "tests")' in stack_edits,
            "two-phase stack editor")
    require("production_large_stack_records=0" in stack_validator,
            "stack validator production closure")
    require("kunit_large_stack_records=0" in stack_validator,
            "stack validator KUnit closure")
    require("PARENT_SOURCE_STATE=" +
            stack_fix["prepared_source_state"] in stack_generator,
            "stack generator source pin")
    require("PARENT_SOURCE_INTEGRITY=" +
            stack_fix["prepared_source_integrity"] in stack_generator,
            "stack generator integrity pin")
    for relative, expected in stack_fix["parent_files"].items():
        variable = "MEMBERSHIP_SHA256" if relative.endswith(
            "mt6797_a72_membership.c") else "TEST_SHA256"
        require(f"{variable}={expected}" in stack_generator,
                f"stack generator parent {relative}")
    require("generated_patch_count=2" in stack_generator,
            "stack generator patch count")
    require("text.count(old) == 2" in target_edits and
            "text.replace(old, new)" in target_edits,
            "target deterministic editor")
    require("production_code_changes=0" in target_validator and
            "preflight_target=CPUHP_ONLINE" in target_validator,
            "target source validator closure")
    require("generated_patch_count=1" in target_patch_validator and
            "two-line substitution" in target_patch_validator,
            "target patch validator closure")
    require("PARENT_SOURCE_STATE=" +
            target_fix["prepared_source_state"] in target_generator,
            "target generator source pin")
    require("PARENT_SOURCE_INTEGRITY=" +
            target_fix["prepared_source_integrity"] in target_generator,
            "target generator integrity pin")
    require("TEST_SHA256=" +
            target_fix["canonical_parent_test_sha256"] in target_generator,
            "target generator test parent pin")
    require("MEMBERSHIP_SHA256=" +
            target_fix["canonical_parent_membership_sha256"] in
            target_generator, "target generator membership parent pin")
    require("generated_patch_count=1" in target_generator,
            "target generator patch count")
    for command in (
        "generate-a72-direct-state-compositor",
        "fetch-a72-direct-state-compositor",
        "generate-a72-direct-state-stack-fix",
        "fetch-a72-direct-state-stack-fix",
        "generate-a72-direct-state-target-fix",
        "fetch-a72-direct-state-target-fix",
    ):
        require(command in buildbox, f"Buildbox command {command}")
    offline = contract["offline_definition"]
    require(offline["profile"] == "a72-direct-state-kunit",
            "offline profile")
    profile = manifest["config"]["profiles"][offline["profile"]]
    require(profile["patch_series"] == "patches/series",
            "profile canonical series")
    require(profile["fragments"][-1] == offline["fragment"],
            "profile isolated fragment")
    fragment = (ROOT / offline["fragment"]).read_text().splitlines()
    for line in (
        "CONFIG_KUNIT=y",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST=y",
        "# CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR is not set",
        'CONFIG_LOCALVERSION="-gemini-direct-state-kunit"',
    ):
        require(line in fragment, f"offline fragment {line}")
    for token in (
        "EXPECTED_PROFILE=a72-direct-state-kunit",
        "-nic none", "timeout --signal=TERM 45 qemu-system-aarch64",
        "focused_test_count", "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST=y",
    ):
        require(token in runner, f"QEMU runner {token}")
    for token in (
        'SUITE = "mt6797-a72-direct-state"',
        'require(ktap.count("1..7") == 1',
        'print("physical_reader_callers=0")',
        'print("opens_owner=false")',
    ):
        require(token in classifier, f"QEMU classifier {token}")
    require("`pass-hardware-free`" in readme,
            "current phase statement")

    print("validation=a72-direct-state-definition")
    print(f"source_templates={len(source_files)}")
    print("generated_patch_count=2")
    print("compile_attempt_1=rejected-stack-safety")
    print("compile_attempt_2=pass-stack-safety")
    print("compile_attempt_3=pass-stack-safety")
    print("stack_fix_generated=true")
    print("qemu_attempt_1=rejected-test-target-contract")
    print("qemu_attempt_2=pass-hardware-free")
    print("target_fix_generated=true")
    print(f"manifest_profiles={len(manifest['config']['profiles'])}")
    print(f"canonical_patch_count={len(series)}")
    print("physical_reader_callers=0")
    print("hardware_operations=0")
    print("cpu_requests=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
