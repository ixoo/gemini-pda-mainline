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
        "ea2d2250dcec3abb14f92c35968403198b0b2f1a022fbdf2c77e2e92976691d1",
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
    ], "generation attempt chronology")
    require(contract["generation"] == {
        "repository_commit":
            "40c623eeaa707b861a572d385a25967c502af49e",
        "package": "a72-atomic-publication-40c623eeaa70",
        "result_commit": "db4d388fabd2921ee1c8e25007d7b85371b85b17",
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
        "PARENT_PATCH=0344-", "--phase finalizer", "--phase publisher",
        "--phase tests", 'git -C "$work/verify" am', "checkpatch.pl",
        "PSCI_SOURCE_SHA256=7e332979", "generated_patch_count=3",
        "MEMBERSHIP_TEST_SHA256=1bf20757", "boot_candidate=false",
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
    profile = manifest["config"]["profiles"][PROFILE]
    require(profile["base"] == "defconfig" and
            profile["patch_series"] == "patches/series",
            "isolated profile base")
    require(profile["fragments"][-1] ==
            "configs/gemini-a72-atomic-publication-kunit.fragment",
            "isolated profile fragment")
    require("CONFIG_KUNIT=y" in fragment and
            "CONFIG_ARM64_MT6797_A72_ATOMIC_PUBLICATION_KUNIT_TEST=y" in
            fragment and
            'CONFIG_LOCALVERSION="-gemini-a72-atomic-kunit"' in fragment,
            "isolated profile contract")
    for token in (
        "generated, reviewed, and canonically admitted",
        "no production caller", "candidate is defined",
        "failed closed before any", "No kernel has yet been compiled",
    ):
        require(token in readme, f"README closure {token}")

    for relative in (
        "README.md", "contract.json",
        "source/mt6797_a72_atomic_publication_test.inc",
        "scripts/source_edits.py", "scripts/validate_source.py",
        "scripts/validate_patch.py", "scripts/generate-on-buildbox",
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
