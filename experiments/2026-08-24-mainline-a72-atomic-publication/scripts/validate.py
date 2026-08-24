#!/usr/bin/env python3
"""Validate the repository-side atomic-publication definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PARENT_PATCH = (
    ROOT / "patches/v7.1.3/"
    "0344-arm64-revise-A34-for-direct-state-v2.patch"
)
PARENT_PATCH_SHA256 = (
    "c7f39812d182f85a9b7db3f47cf8de4219efcdf36bfb4b99dae5026fac6bb192"
)
PATCH_SHA256 = {
    "patches/v7.1.3/0345-arm64-finalize-P30-pristine-bootstrap-claim.patch":
        "e84b1096911dd2e1375aac856702bf7d9508803e4984006ddca07a99fbd09aba",
    "patches/v7.1.3/0346-arm64-add-atomic-A72-bootstrap-publisher.patch":
        "7229672d0eb94614dd3bdfb2fb1661ab54f420f6dd6211a0b4e84223fbc0ade8",
    "patches/v7.1.3/0347-arm64-test-atomic-A72-bootstrap-publication.patch":
        "aa6ecee3bb4cbd9e5a449ac0adc22a85595c9ec3df0552b383ae4830710c1f14",
}
PROFILE = "a72-atomic-publication-kunit"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    readme = (EXPERIMENT / "README.md").read_text()
    edits = (EXPERIMENT / "scripts/source_edits.py").read_text()
    source_validator = (EXPERIMENT / "scripts/validate_source.py").read_text()
    patch_validator = (EXPERIMENT / "scripts/validate_patch.py").read_text()
    generator = (EXPERIMENT / "scripts/generate-on-buildbox").read_text()
    test = (EXPERIMENT / "source/"
            "mt6797_a72_atomic_publication_test.inc").read_text()
    buildbox = (ROOT / "scripts/buildbox").read_text()
    docs = (ROOT / "docs/BUILDBOX.md").read_text()
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    series = (ROOT / "patches/series").read_text().splitlines()
    fragment = (ROOT / "configs/"
                "gemini-a72-atomic-publication-kunit.fragment").read_text()
    runner = (EXPERIMENT / "scripts/run-kunit-qemu").read_text()
    classifier = (EXPERIMENT / "scripts/classify-kunit.py").read_text()
    build_evidence = (EXPERIMENT / "results/"
                      "buildbox-compile-e5de89b7-20260824.txt").read_text()
    mixed_evidence = (EXPERIMENT / "results/"
                      "kunit-qemu-mixed-e5de89b7-20260824.txt").read_text()

    require(contract["experiment"] == EXPERIMENT.name, "experiment identity")
    require(contract["repository_parent"] ==
            "fdfd588e434cf3dd145089da2c2fc410916fba83",
            "repository parent")
    require(contract["prepared_source_state"] ==
            "5f830ffd6050d3831b2a6a5d94b6f8a8125444215f93828de714c5f551dcf0ad",
            "prepared source state")
    require(contract["prepared_source_integrity"] ==
            "6e8edea4e04443353bcc5bc5c6da8eed3914bcca529e864f8af9af52a9ef502d",
            "prepared source integrity")
    require(sha256(PARENT_PATCH) == PARENT_PATCH_SHA256,
            "canonical parent patch")
    require(contract["patches"] == [
        "0345-arm64-finalize-P30-pristine-bootstrap-claim.patch",
        "0346-arm64-add-atomic-A72-bootstrap-publisher.patch",
        "0347-arm64-test-atomic-A72-bootstrap-publication.patch",
    ], "planned patch order")
    require(contract["parent_files"]["arch/arm64/kernel/mt6797_psci.c"] ==
            "7e3329797e0f2eebc4372aa47c84c09e3c2ed85e5121f9492898727db5e4f83d",
            "PSCI source identity")
    require(contract["parent_files"][
                "arch/arm64/kernel/mt6797_a72_membership_test.c"] ==
            "1bf20757aa9b76e01074bba8c33b76db25ea063f9d6406c64dc742764cb637ed",
            "membership test source identity")
    require(contract["generation_attempts"] == [
        {
            "repository_commit":
                "c697f934d18048b3b99cda45d698b0b6a9bf34f1",
            "classification": "rejected-validator-source-subset",
        },
        {
            "repository_commit":
                "8a8d88e9f0d99c25d4d872863280e01f5fcdc53f",
            "classification": "rejected-pinned-psci-file-identity",
        },
        {
            "repository_commit":
                "21953be69ce08bed84b7e629728cb857af9b93a5",
            "classification": "rejected-validator-kconfig-symbol-spelling",
        },
        {
            "repository_commit":
                "3204c1878b59fe3c22474638c8f7d3c683b68938",
            "classification": "rejected-strict-finalizer-style",
            "semantic_validation": "pass",
            "exact_replay": True,
            "checkpatch_0345": "0 errors, 0 warnings, 3 checks",
        },
        {
            "repository_commit":
                "b9cb931b00c817ec3d9c5b59d0a914ba3322f3dc",
            "classification": "rejected-strict-finalizer-alignment",
            "semantic_validation": "pass",
            "exact_replay": True,
            "checkpatch_0345": "0 errors, 0 warnings, 3 checks",
        },
        {
            "repository_commit":
                "d31031b00024e539b9da57a7a48fa96245abefc9",
            "classification": "rejected-strict-finalizer-indent",
            "semantic_validation": "pass",
            "exact_replay": True,
            "checkpatch_0345": "5 errors, 5 warnings, 0 checks",
        },
        {
            "repository_commit":
                "01a0de125656bce791382a5a1fc56e01dfac6ab1",
            "classification": "rejected-strict-publisher-alignment",
            "semantic_validation": "pass",
            "exact_replay": True,
            "checkpatch_0345": "0 errors, 0 warnings, 0 checks",
            "checkpatch_0346": "0 errors, 0 warnings, 6 checks",
        },
        {
            "repository_commit":
                "e6e2efdac7a56bddae08d281b632ad1c04c17055",
            "classification": "rejected-strict-test-style",
            "semantic_validation": "pass",
            "exact_replay": True,
            "checkpatch_0345": "0 errors, 0 warnings, 0 checks",
            "checkpatch_0346": "0 errors, 0 warnings, 0 checks",
            "checkpatch_0347": "0 errors, 1 warning, 17 checks",
        },
        {
            "repository_commit":
                "7e20180e65b9dac8e824a4e591284fae90f7f0f5",
            "classification": "rejected-strict-test-line-length",
            "semantic_validation": "pass",
            "exact_replay": True,
            "checkpatch_0345": "0 errors, 0 warnings, 0 checks",
            "checkpatch_0346": "0 errors, 0 warnings, 0 checks",
            "checkpatch_0347": "0 errors, 4 warnings, 0 checks",
        },
        {
            "repository_commit":
                "40c623eeaa707b861a572d385a25967c502af49e",
            "classification": "pass",
        },
        {
            "repository_commit":
                "d0b836d33d541b4ad1781577df6bc53dbe3d6154",
            "classification": "rejected-managed-source-state-advanced",
        },
        {
            "repository_commit":
                "b7677583d47a2416a15a29cdfb523a34ce64a28b",
            "classification": "pass",
        },
    ], "generation attempt chronology")
    require(contract["generation"] == {
        "repository_commit":
            "b7677583d47a2416a15a29cdfb523a34ce64a28b",
        "package": "a72-atomic-publication-b7677583d47a",
        "result_commit": "96406f5483e00c96375dde586bf83c5ab2e323d8",
        "source_input_mode": "current-series-reverse",
        "source_input_state":
            "c7652badc345119ce6d5f842b01cc48d79d502944390aa90a20d9e3d2bf7cda7",
        "source_input_integrity":
            "88aa62a3c1e8f412c421020f7ca4fa160a3dfa056a3c35567d240f9b9867a922",
        "semantic_validation": "pass",
        "exact_replay": True,
        "checkpatch": "0 errors, 0 warnings, 0 checks",
        "patch_sha256": PATCH_SHA256,
        "production_callers": 0,
        "injected_owner_publication": True,
        "physical_reader_binding": False,
        "production_replay_source": False,
        "hardware_operations": 0,
        "cpu_requests": 0,
        "device_action": False,
        "boot_candidate": False,
    }, "successful generation result")
    require(contract["build_attempts"] == [{
        "repository_commit":
            "84c94b0460db492ab89565cfe0f361491b770b96",
        "classification": "rejected-fragment-override-closure",
        "stage": "configuration-validation",
        "compile_started": False,
        "reason": ("inherited P30 fragment explicitly disabled the selected "
                   "late-startup KUnit suite"),
    }], "build attempt chronology")
    require(contract["build"] == {
        "repository_commit":
            "e5de89b7b5affc859a2f491d1b795fa3d41dd14a",
        "profile": PROFILE,
        "package": ("linux-7.1.3-gemini-a72-atomic-publication-kunit-"
                    "f371203d-fb1ade23"),
        "kernel_release": "7.1.3-gemini-a72-atomic-kunit",
        "source_sha256":
            "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc",
        "patchset_sha256":
            "f371203dcbaa77ea0a616d5f93bf60355878c74e021a94461114114365a0b820",
        "config_sha256":
            "5681d90b3bd01e5b0e25b99d6dc3421725e0eef8be0445c2767b2a7602a3591c",
        "image_sha256":
            "4c1fdf90a78fa3e05f2ad17029762657006dabad5e1ce7abf392534a5b1423bc",
        "build_log_sha256":
            "987cb23429a4c866c317d4b9c475db01995ab49575fc36f228caf1551ef56fc6",
        "frame_warning_total": 29,
        "inherited_production_frame_warnings": 2,
        "inherited_membership_test_frame_warnings": 27,
        "atomic_test_region_frame_warnings": 0,
        "classification":
            "pass-no-new-atomic-frame-warning-with-inherited-debt",
        "evidence": "results/buildbox-compile-e5de89b7-20260824.txt",
    }, "successful build evidence")
    require(contract["runtime_attempts"] == [{
        "repository_commit":
            "e5de89b7b5affc859a2f491d1b795fa3d41dd14a",
        "classification":
            "rejected-profile-registered-unrelated-owner-suite",
        "late_startup": "pass:20_fail:0_skip:0_total:20",
        "owner_suite": "pass:3_fail:23_skip:0_total:26",
        "atomic_publication": "pass:8_fail:0_skip:0_total:8",
        "raw_log_sha256":
            "6585d0bb91aed22a71153d94cfd99df14aa662e725e058efa275f3f505cbaed5",
        "evidence": "results/kunit-qemu-mixed-e5de89b7-20260824.txt",
    }], "runtime attempt chronology")
    for relative, expected in PATCH_SHA256.items():
        require(sha256(ROOT / relative) == expected,
                f"admitted patch identity {relative}")
    require([f"patches/{relative}" for relative in series[-3:]] ==
            list(PATCH_SHA256), "canonical patch order")
    require(contract["tests"] == {
        "suite": "mt6797-a72-atomic-publication",
        "cases": 8,
        "network": "none",
    }, "focused test contract")
    scope = contract["scope"]
    require(scope["default_off"] is True and
            scope["hardware_free"] is True and
            scope["production_callers"] == 0 and
            scope["hardware_operations"] == 0 and
            scope["cpu_requests"] == 0,
            "default-off scope")
    require(all(scope[key] is False for key in (
        "physical_reader_binding", "production_replay_source",
        "cpu_veto_change", "device_action", "boot_candidate",
    )), "scope closure")

    require('choices=("finalizer", "publisher", "tests")' in edits,
            "source phase selector")
    for token in (
        "arm64_late_cpu_startup_finalize_pristine",
        "late_startup_pristine_locked(claim->cookie)",
        "mt6797_a72_membership_publish_bootstrap_locked",
        "mt6797_a72_direct_state_snapshot_locked(",
        "a72_owner.health = MT6797_A72_OWNER_AVAILABLE",
        "CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST",
        "kunit_test_suite(atomic_publication_test_suite)",
    ):
        require(token in edits, f"source editor contract {token}")
    for token in (
        "p30_lock_spans_callback=true", "production_callers=0",
        "physical_reader_binding=false", "cpu_veto_change=false",
        "hardware_operations=0", "cpu_requests=0",
    ):
        require(token in source_validator, f"source validator marker {token}")
    for token in (
        "generated_patch_count=3", "focused_tests=8",
        "production_callers=0", "physical_reader_binding=false",
        "cpu_veto_change=false", "hardware_operations=0",
        "cpu_requests=0", "boot_candidate=false",
    ):
        require(token in patch_validator, f"patch validator marker {token}")
    for token in (
        "PARENT_SOURCE_STATE=5f830ffd", "PARENT_SOURCE_INTEGRITY=6e8edea4",
        "CURRENT_SOURCE_STATE=c7652bad", "CURRENT_SOURCE_INTEGRITY=88aa62a3",
        "PARENT_PATCH=0344-", "--phase finalizer", "--phase publisher",
        "--phase tests", 'git -C "$work/verify" am', "checkpatch.pl",
        "PSCI_SOURCE_SHA256=7e332979", "generated_patch_count=3",
        "MEMBERSHIP_TEST_SHA256=1bf20757",
        'git -C "$work/source" apply --reverse',
        "source_input_mode=$source_mode", "boot_candidate=false",
    ):
        require(token in generator, f"generator invariant {token}")
    require(test.count("KUNIT_CASE(") == 8, "focused fixture count")
    require(test.startswith("// SPDX-License-Identifier: GPL-2.0-only\n"),
            "focused fixture license")
    for token in (
        "atomic_finalizer_success_test",
        "atomic_publication_success_repeat_test",
        "atomic_publication_replay_rejections_test",
        "atomic_publication_p30_busy_test",
        "atomic_publication_final_owner_mismatch_test",
        'name = "mt6797-a72-atomic-publication"',
    ):
        require(token in test, f"fixture contract {token}")
    for token in (
        "generate-a72-atomic-publication",
        "fetch-a72-atomic-publication",
        str(Path("experiments") / EXPERIMENT.name /
            "scripts/generate-on-buildbox"),
    ):
        require(token in buildbox, f"Buildbox command {token}")
    require("./scripts/buildbox generate-a72-atomic-publication" in docs,
            "Buildbox documentation")
    for token in (
        "EXPECTED_PROFILE=a72-atomic-publication-kunit",
        "CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST=y",
        "focused KUnit inventory changed",
    ):
        require(token in runner, f"QEMU runner contract {token}")
    for token in (
        'PROFILE = "a72-atomic-publication-kunit"',
        '"arm64-late-cpu-startup"',
        '"mt6797-a72-atomic-publication"',
        '"1..2", "1..20", "1..8"',
        "production_owner_publication=false",
    ):
        require(token in classifier, f"QEMU classifier contract {token}")
    for token in (
        "frame_warning_total=29",
        "inherited_membership_test_frame_warnings=27",
        "atomic_test_region_frame_warnings=0",
        "result=pass-no-new-atomic-frame-warning-with-inherited-debt",
    ):
        require(token in build_evidence, f"build evidence {token}")
    for token in (
        "suite_arm64-late-cpu-startup=pass:20_fail:0_skip:0_total:20",
        "suite_mt6797-a72-p24-owner=pass:3_fail:23_skip:0_total:26",
        "suite_mt6797-a72-atomic-publication=pass:8_fail:0_skip:0_total:8",
        "result=rejected-profile-registered-unrelated-owner-suite",
    ):
        require(token in mixed_evidence, f"mixed QEMU evidence {token}")
    profile = manifest["config"]["profiles"][PROFILE]
    require(profile["base"] == "defconfig" and
            profile["patch_series"] == "patches/series",
            "isolated profile base")
    require(profile["fragments"][-1] ==
            "configs/gemini-a72-atomic-publication-kunit.fragment",
            "isolated profile fragment")
    require("CONFIG_KUNIT=y" in fragment and
            "CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST=y" in fragment and
            "CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST=y" in fragment and
            "CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST=y" in
            fragment and
            'CONFIG_LOCALVERSION="-gemini-a72-atomic-kunit"' in fragment,
            "isolated profile contract")
    for token in (
        "compiled; atomic KUnit passes",
        "no production caller", "candidate is defined",
        "failed closed before any", "atomic-publication suite passed 8/8",
        "failed closed before", "reverse-applies the exact three",
        "Patches `0345` and `0346` are byte-identical",
        "a72-atomic-publication-b7677583d47a",
        "Build the exact regenerated profile",
    ):
        require(token in readme, f"README closure {token}")

    for relative in (
        "README.md", "contract.json",
        "source/mt6797_a72_atomic_publication_test.inc",
        "scripts/source_edits.py", "scripts/validate_source.py",
        "scripts/validate_patch.py", "scripts/generate-on-buildbox",
        "scripts/run-kunit-qemu", "scripts/classify-kunit.py",
        "results/buildbox-compile-e5de89b7-20260824.txt",
        "results/kunit-qemu-mixed-e5de89b7-20260824.txt",
    ):
        path = EXPERIMENT / relative
        require(path.is_file() and not path.is_symlink(),
                f"missing or unsafe definition file {relative}")

    print("validation=a72-atomic-publication-definition")
    print("planned_patch_count=3")
    print("focused_tests=8")
    print("build_backend=buildbox")
    print("production_callers=0")
    print("physical_reader_binding=false")
    print("cpu_veto_change=false")
    print("hardware_operations=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
