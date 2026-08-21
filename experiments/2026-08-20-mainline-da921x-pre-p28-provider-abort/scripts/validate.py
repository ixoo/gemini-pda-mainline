#!/usr/bin/env python3
"""Validate the frozen pre-P28 provider-abort contract and tooling."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPO = ROOT.parents[1]
EXPECTED_PATCHES = {
    "0296-arm64-fail-stop-ambiguous-A72-provider-acquire.patch":
        "d388b62ff544e8efa93ccea91aaafba9927134cc77c355a647e8a11e8ef507f8",
    "0297-arm64-add-exact-pre-P28-A72-provider-abort.patch":
        "07dae4c535b80171243a48f7841567b15b485d7969493e54b99e9a9716252b46",
    "0298-regulator-make-DA921x-provider-endpoint-injectable.patch":
        "00975eeb0da3138d617f87c9448483d9165fe3e813b56ff5dd2e3009ce37968f",
    "0299-regulator-test-DA921x-pre-P28-membership-abort.patch":
        "d95024c58b3bbea892310e8712e88ccf86d6bb032a16150eef898a2df4dd0854",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = json.loads((ROOT / "contract.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPO / "kernel/manifest.json").read_text(encoding="utf-8"))
    edits = (ROOT / "scripts/source_edits.py").read_text(encoding="utf-8")
    generator = (ROOT / "scripts/generate-on-buildbox").read_text(encoding="utf-8")
    source_validator = (ROOT / "scripts/validate_source.py").read_text(
        encoding="utf-8"
    )
    patch_validator = (ROOT / "scripts/validate_patches.py").read_text(
        encoding="utf-8"
    )
    runner = (ROOT / "scripts/run-kunit-qemu").read_text(encoding="utf-8")
    classifier = (ROOT / "scripts/classify-kunit.py").read_text(
        encoding="utf-8"
    )
    classifier_test = (ROOT / "scripts/test-kunit-classifier.py").read_text(
        encoding="utf-8"
    )
    test = (ROOT / "source/da9213-legacy-membership-test.c").read_text(
        encoding="utf-8"
    )
    buildbox = (REPO / "scripts/buildbox").read_text(encoding="utf-8")

    require(
        contract["status"]
        == "qemu-stack-remediation-patch-generation-pending",
            "experiment status changed")
    safety = contract["safety"]
    require(safety["default_off"] and safety["hardware_free"],
            "slice gained default reachability or hardware")
    for field in (
        "device_access",
        "native_vm_build",
        "physical_provider_call",
        "p27_hardware_effect",
        "p28_effect",
        "cpu_on",
        "cpu_off",
        "boot_candidate",
    ):
        require(not safety[field], f"unsafe contract permission: {field}")
    require(contract["implementation"]["production_reachability"] is False,
            "production reachability changed")
    require(contract["implementation"]["logical_patches"] == 4,
            "logical patch count changed")
    require(contract["proof"]["cases"] == 6, "KUnit case count changed")
    require(contract["generated_patches"]["sha256"] == EXPECTED_PATCHES,
            "generated patch contract changed")

    canonical = [
        line.strip() for line in (REPO / "patches/series").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    expected_suffix = [f"v7.1.3/{name}" for name in EXPECTED_PATCHES]
    require(canonical[-len(expected_suffix):] == expected_suffix,
            "canonical patch suffix changed")
    for name, expected_sha256 in EXPECTED_PATCHES.items():
        patch = REPO / "patches/v7.1.3" / name
        require(patch.is_file(), f"canonical patch missing: {name}")
        actual_sha256 = hashlib.sha256(patch.read_bytes()).hexdigest()
        require(actual_sha256 == expected_sha256,
                f"canonical patch identity changed: {name}")

    profiles = manifest["config"]["profiles"]
    positive = profiles["da921x-positive-provider"]["fragments"]
    abort = profiles["da921x-pre-p28-provider-abort"]["fragments"]
    kunit = profiles["da921x-pre-p28-provider-abort-kunit"]["fragments"]
    require(abort[:-1] == positive, "abort profile parent changed")
    require(
        abort[-1] == "configs/gemini-a72-pre-p28-provider-abort.fragment",
        "abort profile fragment changed",
    )
    require(kunit[:-1] == abort, "KUnit profile parent changed")
    require(
        kunit[-1]
        == "configs/gemini-a72-pre-p28-provider-abort-kunit.fragment",
        "KUnit profile fragment changed",
    )
    for profile_name in (
        "da921x-pre-p28-provider-abort",
        "da921x-pre-p28-provider-abort-kunit",
    ):
        profile_series = profiles[profile_name].get(
            "patch_series", manifest["patch_series"]
        )
        require(profile_series == "patches/series",
                f"{profile_name} no longer selects canonical patches")
    abort_fragment = (
        REPO / "configs/gemini-a72-pre-p28-provider-abort.fragment"
    ).read_text()
    kunit_fragment = (
        REPO / "configs/gemini-a72-pre-p28-provider-abort-kunit.fragment"
    ).read_text()
    require("CONFIG_ARM64_MT6797_A72_PRE_P28_PROVIDER_ABORT=y"
            in abort_fragment, "abort config missing")
    require("CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST=y"
            not in kunit_fragment, "unrelated owner KUnit suite leaked in")
    require("CONFIG_REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST=y"
            in kunit_fragment, "integration KUnit config missing")

    for token in (
        "--phase failstop",
        "--phase abort",
        "--phase endpoint",
        "--phase kunit",
        "format-patch -4",
        "source-tree-integrity\" verify",
        "strict checkpatch rejected generated patches",
        "physical_da921x_write_authorized=false",
        "p28_effect=false",
        "cpu_on=false",
        "cpu_off=false",
    ):
        require(token in generator, f"generator token missing: {token}")
    for token in (
        "mt6797_a72_membership_latch_provider_fault",
        "mt6797_a72_membership_run_provider_abort",
        "MT6797_A72_PROVIDER_RELEASE_INFLIGHT",
        "provider_rejection_valid ==",
        "struct da9213_legacy_provider_endpoint",
        "REGULATOR_DA9213_LEGACY_MEMBERSHIP_KUNIT_TEST",
    ):
        require(token in edits, f"source edit token missing: {token}")
    require(test.count("KUNIT_CASE(") == 6, "KUnit inventory changed")
    require(".name = \"da9213-legacy-membership-provider\"" in test,
            "KUnit suite changed")
    require("struct da9213_membership_test_state" in test,
            "heap-backed KUnit state missing")
    require(test.count("kunit_kzalloc(test, sizeof(*state), GFP_KERNEL)") == 6,
            "KUnit heap-state allocation inventory changed")
    require("mt6797_a72_membership_snapshot(&synthetic->snapshot)" in test,
            "release callback retained a stack-local snapshot")
    for forbidden in (
        "i2c_add_adapter",
        "i2c_new_client",
        "ioremap",
        "writel(",
        "cpu_up(",
        "cpu_down(",
    ):
        require(forbidden not in test, f"hardware test token: {forbidden}")
    require("logical_patches=4" in source_validator,
            "source validator patch count changed")
    require("patches=4" in patch_validator,
            "patch validator patch count changed")
    require("KUnit heap-state allocation inventory changed"
            in source_validator, "source stack-safety validation missing")
    require("KUnit heap-state allocation inventory changed"
            in patch_validator, "patch stack-safety validation missing")
    for token in (
        "EXPECTED_PROFILE=da921x-pre-p28-provider-abort-kunit",
        "CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED=y",
        "focused KUnit test inventory changed",
        "timeout --signal=TERM 45 qemu-system-aarch64",
        "-nographic -no-reboot -nic none",
        "package commit differs from repository HEAD",
    ):
        require(token in runner, f"QEMU runner token missing: {token}")
    for token in (
        'SUITE = "da9213-legacy-membership-provider"',
        '"da9213_membership_positive_abort_success"',
        '"da9213_membership_abort_guards_and_p29"',
        "require(qemu_exit == 124,",
        'print("p28_effect=false")',
        'print("cpu8_cpu9_admission=closed")',
    ):
        require(token in classifier, f"KUnit classifier token missing: {token}")
    require("unsafe_runtime_mutations_rejected=" in classifier_test,
            "KUnit classifier self-test missing")
    for token in (
        "generate-da921x-pre-p28-provider-abort-patches",
        "fetch-da921x-pre-p28-provider-abort-patches",
        "mainline-da921x-pre-p28-provider-abort-patch-generation",
        "generated_patch_count=4",
    ):
        require(token in buildbox, f"Buildbox command token missing: {token}")

    print("validation=da921x-pre-p28-provider-abort-contract")
    print("status=qemu-stack-remediation-patch-generation-pending")
    print("canonical_patch_count=4")
    print("logical_patches=4")
    print("kunit_cases=6")
    print("hardware_action=none")
    print("device_action=none")
    print("cpu8_cpu9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
