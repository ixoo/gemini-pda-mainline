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
    require(series[-2:] == [
        "v7.1.3/0337-arm64-add-closed-A72-direct-state-compositor.patch",
        "v7.1.3/0338-arm64-test-closed-A72-direct-state-compositor.patch",
    ], "canonical tail")
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
    for command in (
        "generate-a72-direct-state-compositor",
        "fetch-a72-direct-state-compositor",
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
    require("No compile or KUnit runtime result exists yet" in readme,
            "current phase statement")

    print("validation=a72-direct-state-definition")
    print(f"source_templates={len(source_files)}")
    print("generated_patch_count=2")
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
