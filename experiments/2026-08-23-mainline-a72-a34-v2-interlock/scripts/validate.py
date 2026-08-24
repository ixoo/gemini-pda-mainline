#!/usr/bin/env python3
"""Validate the repository-side A34-v2 interlock definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PARENT_PATCH = (
    ROOT / "patches/v7.1.3/"
    "0341-arm64-fix-A72-direct-state-preflight-target-test.patch"
)
PARENT_PATCH_SHA256 = (
    "03da9d3a0a42e637309ea8efda236a163b5380a5e0fd4139a0731a8b27bb92cb"
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
    source_validator = (
        EXPERIMENT / "scripts/validate_source.py"
    ).read_text()
    patch_validator = (EXPERIMENT / "scripts/validate_patch.py").read_text()
    generator = (EXPERIMENT / "scripts/generate-on-buildbox").read_text()
    test = (
        EXPERIMENT / "source/mt6797_a72_a34_evaluator_test.c"
    ).read_text()
    buildbox = (ROOT / "scripts/buildbox").read_text()
    docs = (ROOT / "docs/BUILDBOX.md").read_text()
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    series = (ROOT / "patches/series").read_text().splitlines()
    fragment = (ROOT / "configs/gemini-a72-a34-v2-kunit.fragment").read_text()

    require(contract["experiment"] == EXPERIMENT.name, "experiment identity")
    require(contract["repository_parent"] ==
            "83f9ef6c1a7a54f615f5e0d752ecc455c9a79566",
            "repository parent")
    require(contract["prepared_source_state"] ==
            "c020a36a674ca8ac6516f022649f143cd1d1d8834f17e5de758bc3fe0268c72e",
            "prepared source state")
    require(contract["prepared_source_integrity"] ==
            "54165d2bf54ca5b795d85314061fdfe0930e0b78e50927269b0746d1646625c3",
            "prepared source integrity")
    require(sha256(PARENT_PATCH) == PARENT_PATCH_SHA256,
            "canonical parent patch")
    require(series[-4:] == [
        "v7.1.3/0341-arm64-fix-A72-direct-state-preflight-target-test.patch",
        "v7.1.3/0342-arm64-add-P30-pristine-bootstrap-claim.patch",
        "v7.1.3/0343-arm64-bind-A72-direct-state-to-target-identity.patch",
        "v7.1.3/0344-arm64-revise-A34-for-direct-state-v2.patch",
    ], "canonical admission order")
    require(contract["patches"] == [
        "0342-arm64-add-P30-pristine-bootstrap-claim.patch",
        "0343-arm64-bind-A72-direct-state-to-target-identity.patch",
        "0344-arm64-revise-A34-for-direct-state-v2.patch",
    ], "planned patch order")
    attempts = contract["generation_attempts"]
    require(len(attempts) == 5, "generation attempt count")
    require([attempt["classification"] for attempt in attempts] == [
        "rejected-validator-snapshot-boundary",
        "rejected-source-anchor-direct-test",
        "rejected-validator-direct-header-boundary",
        "rejected-strict-style",
        "pass",
    ], "generation chronology")
    generation = contract["generation"]
    require(generation["repository_commit"] ==
            "91b6993a4ffcc4fa511f29fe2c3d7f7c7ceefa33",
            "generation repository commit")
    require(generation["result_commit"] ==
            "2473e240ec5dd9d2adae7bc503538b687a8547a0",
            "generated source result")
    require(generation["semantic_validation"] == "pass" and
            generation["exact_replay"] is True,
            "generation replay result")
    require(generation["checkpatch"] == "0 errors, 0 warnings, 0 checks",
            "strict checkpatch result")
    for relative, expected in generation["patch_sha256"].items():
        require(sha256(ROOT / relative) == expected,
                f"admitted patch identity {relative}")
    require(generation["production_callers"] == 0 and
            generation["owner_publication"] is False and
            generation["physical_reader_binding"] is False and
            generation["device_action"] is False and
            generation["boot_candidate"] is False,
            "generation scope closure")
    require(contract["scope"]["production_callers"] == 0,
            "production caller scope")
    require(all(contract["scope"][key] is False for key in (
        "owner_publication", "physical_reader_binding", "cpu_veto_change",
        "cpu_on", "cpu_off", "device_action", "boot_candidate",
    )), "scope is not closed")
    require(contract["scope"]["default_off"] is True and
            contract["scope"]["hardware_free"] is True,
            "default-off hardware-free scope")

    require('choices=("interlock", "direct", "a34")' in source_edits,
            "source phase selector")
    for token in (
        "arm64_late_cpu_startup_claim_pristine",
        "late_startup_pristine_locked",
        "get_cpu_ops(8) == &mt6797_psci_ops",
        "MT6797_A72_DIRECT_STATE_ABI 2",
        "MT6797_A72_A34_ELIGIBILITY_ABI 2",
        "MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR",
        "memcmp(observation, &a34_expected, sizeof(*observation))",
    ):
        require(token in source_edits, f"source editor contract {token}")
    for token in (
        "production_callers=0", "owner_lifecycle=closed",
        "physical_reader_binding=false", "hardware_operations=0",
        "cpu_requests=0",
    ):
        require(token in source_validator, f"source validator marker {token}")
    for token in (
        "generated_patch_count=3", "owner_publication=false",
        "physical_reader_binding=false", "hardware_operations=0",
        "cpu_requests=0",
    ):
        require(token in patch_validator, f"patch validator marker {token}")
    for token in (
        "PARENT_SOURCE_STATE=c020a36a", "PARENT_SOURCE_INTEGRITY=54165d2b",
        "PARENT_PATCH=0341-", "--phase interlock", "--phase direct",
        "--phase a34", "git -C \"$work/verify\" am",
        "checkpatch.pl", "boot_candidate=false",
    ):
        require(token in generator, f"generator invariant {token}")
    require("kunit_kzalloc(" in test, "A34 KUnit state is not off-stack")
    require(test.count("KUNIT_CASE(") == 5, "A34-v2 test case count")

    profile = manifest["config"]["profiles"]["a72-a34-v2-kunit"]
    require(profile["patch_series"] == "patches/series",
            "profile does not use canonical series")
    require(profile["fragments"][-1] ==
            "configs/gemini-a72-a34-v2-kunit.fragment",
            "profile fragment order")
    for token in (
        "CONFIG_ARM64_LATE_CPU_STARTUP_KUNIT_TEST=y",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_KUNIT_TEST=y",
        "CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_KUNIT_TEST=y",
        'CONFIG_LOCALVERSION="-gemini-a34-v2-kunit"',
    ):
        require(token in fragment, f"profile selector {token}")
    for token in (
        "generate-a34-v2-interlock", "fetch-a34-v2-interlock",
        str(Path("experiments") / EXPERIMENT.name /
            "scripts/generate-on-buildbox"),
    ):
        require(token in buildbox, f"Buildbox command {token}")
    require("./scripts/buildbox generate-a34-v2-interlock" in docs,
            "Buildbox documentation")
    for token in (
        "Buildbox compile pending", "no production caller",
        "not physical evidence", "No boot candidate",
    ):
        require(token in readme, f"README closure {token}")

    for relative in (
        "scripts/source_edits.py", "scripts/validate_source.py",
        "scripts/validate_patch.py", "scripts/generate-on-buildbox",
    ):
        path = EXPERIMENT / relative
        require(path.exists() and not path.is_symlink(),
                f"missing or unsafe definition file {relative}")

    print("validation=a34-v2-interlock-definition")
    print("admitted_patch_count=3")
    print("generation=pass")
    print("build_backend=buildbox")
    print("production_callers=0")
    print("owner_publication=false")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
