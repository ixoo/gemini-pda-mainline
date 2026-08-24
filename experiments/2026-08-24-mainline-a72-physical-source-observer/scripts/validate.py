#!/usr/bin/env python3
"""Validate the A72 physical-source observer generation input."""

from __future__ import annotations

import hashlib
import json
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    require(contract["schema"] == 1, "contract schema")
    require(
        contract["experiment"]
        == "2026-08-24-mainline-a72-physical-source-observer",
        "experiment identity",
    )
    require(
        contract["canonical_parent"].startswith("patches/v7.1.3/0349-"),
        "canonical parent",
    )
    require(
        contract["prepared_source_state"]
        == "6e3b726cd84b346409bb14b6fb66652b7a52aae60a4636b39229e949275d961f",
        "prepared source state",
    )
    require(
        contract["prepared_source_integrity"]
        == "75be833a675873a374e1b4ef1c77ba0557307b4d054eab793e31930d097785dd",
        "prepared source integrity",
    )
    require(contract["production"] == {
        "source_registrations": 1,
        "public_direct_snapshots": 1,
        "source_unregistrations": 1,
        "component_order": [
            "platform", "provider", "clock", "before-bigidvfs",
            "bigidvfs", "after-bigidvfs",
        ],
        "retained_token": "GPSQ-20260824-A",
        "retained_slots": [1, 2],
        "maximum_retained_writes": 2,
        "clock_calls": 1,
        "bigidvfs_calls": 1,
        "bigidvfs_smc_reads": 8,
        "compositor_retries": 0,
    }, "production contract")
    require(contract["test"]["focused_cases"] == 4, "focused case count")
    require(all(value is False for key, value in contract["test"].items()
                if key != "focused_cases"), "hardware-free test effects")
    require(all(value is False for value in contract["exclusions"].values()),
            "excluded effects remain false")
    require(contract["generation"] == {
        "patch_count": 5,
        "logical_boundaries": ["ledger", "observer", "binding", "dts", "tests"],
        "intentional_checkpatch_ignore":
            "SPLIT_STRING-for-two-atomic-retained-records",
        "stopped_attempts": 5,
        "status": "validated",
        "repository_commit":
            "8d0d49042331f54eeef475f9601bc9de2a5722ea",
        "buildbox_job":
            "8d0d49042331f54eeef475f9601bc9de2a5722ea-a72-physical-source-patchgen",
        "package": "a72-physical-source-8d0d49042331",
        "parent_commit": "a796fdef26e26c896db6147de3f4166a87bebb99",
        "result_commit": "31d96ca391708d74228e6b8621bf7931ed2a8e7e",
        "sha256sums_sha256":
            "36a69869b23a34e66b4285235b7562a1e104b576e96cb1bc70cba3c34a173547",
        "patch_sha256": [
            "b13b8e2451e6807b6fcdf0863c774e9219616f09d7cb58d1575ebcd10c84badd",
            "d6f173fe53251644e671f49961b11e15b39f337923bfe9501a7efde6c19bf5c7",
            "209c9304567976287e385e48d46797d837876a7b38bbf880a3a554659ca42c9c",
            "bba2c1ba68ac231d9360e428c39d8fda2e40698e2f14c821de69383f23ed0756",
            "c9d35ee189e081099520a18becc3f839c04085aaa7fc1863c9c62270944a8aca",
        ],
        "canonical_admission": "0350-0354",
    }, "generation contract")
    require(contract["build"] == {
        "profile": "a72-physical-source-kunit",
        "backend": "buildbox",
        "status": "passed",
        "repository_commit":
            "98cf0ff383944420601a19c8a73f4e9d3c3b6beb",
        "package":
            "linux-7.1.3-gemini-a72-physical-source-kunit-d3da89b6-186d9a17",
        "patchset_sha256":
            "d3da89b6189839b3bc0419d28d3c04b8195f6d65d6fd15911b0feb5b4192cb9c",
        "config_sha256":
            "4a5cc00123c7456c7d7028f8f3ddfa3798b352d510d389bb0424918835dd2e50",
        "qemu": "failed-test-stack-fixture",
        "qemu_passed": 2,
        "qemu_failed": 2,
        "qemu_log_sha256":
            "8787bda750c85e7df35828172d43a19c137c9b4c2434f95c493852f48aa3bcfd",
    }, "build contract")
    require(contract["stack_fix"] == {
        "status": "validated",
        "stopped_attempts": 1,
        "canonical_parent":
            "patches/v7.1.3/0354-soc-mediatek-test-A72-physical-source-observer.patch",
        "prepared_source_state":
            "419101daee0a40c89b12669b94bcec87674fafaa18624a75d2a5c5473766ba72",
        "prepared_source_integrity":
            "c0380951cceda5a3a034cd7119ddf7f4b96f1d28c94655ad36f48aac7f4f6db9",
        "parent_test_sha256":
            "068748f876c2720ade9b96d17db90ef61ed78145a757e212322f57728bf7ee05",
        "generated_patch_count": 1,
        "repository_commit":
            "b3752361529188aa0481b18c590c51dde8d752f0",
        "buildbox_job":
            "b3752361529188aa0481b18c590c51dde8d752f0-a72-physical-source-stack-fix-patchgen",
        "package": "a72-physical-source-stack-fix-b37523615291",
        "parent_commit": "083f52fbb0412942c57aefcbeae6f19b349fe25f",
        "result_commit": "11af8683e0bcdc20acad6e4a2e56a749a774ae5e",
        "sha256sums_sha256":
            "826cf5f5d06d7583d303aa6bd1b0d9295cc7b869e2c124ef1137c146e96ece19",
        "patch":
            "0355-soc-mediatek-move-A72-physical-source-KUnit-snapshots-off-stack.patch",
        "patch_sha256":
            "70e316293c0b825b619572e759bba20c18403d43b3e6413cfd54763cb3242ae8",
        "canonical_admission": "0355",
        "compile": "passed",
        "qemu": "passed-4-of-4",
        "verification_repository_commit":
            "ef0da357a74de3962286df331728a04d8fd7e5c1",
        "verification_buildbox_job":
            "ef0da357a74de3962286df331728a04d8fd7e5c1-a72-physical-source-kunit-m0",
        "verification_package":
            "linux-7.1.3-gemini-a72-physical-source-kunit-8c983929-186d9a17",
        "verification_patchset_sha256":
            "8c9839297f8c8c2550fac345982c70391e9bd2cc7194a7580d05c18f5a3a27e6",
        "verification_config_sha256":
            "4a5cc00123c7456c7d7028f8f3ddfa3798b352d510d389bb0424918835dd2e50",
        "verification_image_sha256":
            "7670a5489bcac43fa16857c59154306440c5413ac7c592d15041231b06b2cdfb",
        "verification_system_map_sha256":
            "f050748efeb74b35e32617de25c8b243575e6ecc0e23a4a60f02dbff1dc96411",
        "verification_qemu_log_sha256":
            "2defcec28678b9d03feec1d9871ec549033fdad3e688541289557f382eb97797",
        "verification_failed": 0,
        "verification_skipped": 0,
        "changed_files": [
            "drivers/soc/mediatek/mt6797-a72-physical-source-observer-test.c",
        ],
        "direct_state_stack_objects": 0,
        "kunit_heap_snapshots": 2,
        "production_changed": False,
        "hardware_operations": False,
    }, "stack-fix contract")

    canonical = [ROOT / "patches/v7.1.3" / patch
                 for patch in contract["patches"]]
    require(all(path.is_file() and not path.is_symlink() for path in canonical),
            "canonical patch inventory")
    require([sha256(path) for path in canonical]
            == contract["generation"]["patch_sha256"],
            "canonical patch identities")
    series = (ROOT / "patches/series").read_text().splitlines()
    expected_tail = [f"v7.1.3/{patch}" for patch in contract["patches"]]
    expected_tail.append(f"v7.1.3/{contract['stack_fix']['patch']}")
    require(series[-6:] == expected_tail,
            "canonical series tail")
    stack_patch = ROOT / "patches/v7.1.3" / contract["stack_fix"]["patch"]
    require(stack_patch.is_file() and not stack_patch.is_symlink(),
            "canonical stack-fix patch")
    require(sha256(stack_patch) == contract["stack_fix"]["patch_sha256"],
            "canonical stack-fix identity")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profile = manifest["config"]["profiles"]["a72-physical-source-kunit"]
    require(profile["base"] == "defconfig", "profile base")
    require(profile["patch_series"] == "patches/series", "profile series")
    require(profile["fragments"][-1]
            == "configs/gemini-a72-physical-source-kunit.fragment",
            "profile final fragment")
    fragment = (
        ROOT / "configs/gemini-a72-physical-source-kunit.fragment"
    ).read_text()
    for token in (
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST=y",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR=y",
        "# CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER is not set",
        "# CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION is not set",
        "# CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW is not set",
    ):
        require(token in fragment, f"profile token: {token}")

    source_dir = EXPERIMENT / "source"
    observer = (source_dir / "mt6797-a72-physical-source-observer.c").read_text()
    tests = (source_dir / "mt6797-a72-physical-source-observer-test.c").read_text()
    binding = (
        source_dir / "mediatek,mt6797-a72-physical-source-observer.yaml"
    ).read_text()
    dts = (source_dir / "mt6797-gemini-pda-a72-physical-source.dts").read_text()
    order = (
        "readers->platform(",
        "readers->provider(",
        "readers->clock(",
        "readers->checkpoint(0)",
        "readers->bigidvfs(",
        "readers->checkpoint(1)",
    )
    positions = [observer.index(token) for token in order]
    require(positions == sorted(positions), "template capture order")
    for token in (
        "mt6797_a72_direct_source_register",
        "mt6797_a72_direct_state_snapshot",
        "mt6797_a72_direct_source_unregister",
        "put_device(context.bigidvfs)",
        "put_device(context.clock)",
        "put_device(context.platform)",
    ):
        require(token in observer, f"observer token: {token}")
    require(tests.count("KUNIT_CASE(") == 4, "four template KUnit cases")
    require('name = "mt6797-a72-physical-source"' in tests,
            "focused suite name")
    require("mediatek,platform-state:" in binding, "platform binding")
    require("mediatek,bigidvfs-backend:" in binding, "BigiDVFS binding")
    require("model =" not in dts, "candidate preserves model")
    require(dts.count('status = "okay";') == 4, "candidate enablement count")

    for checkpoint, slot, checksum in (
        ("before-bigidvfs", 1, "47eaad49"),
        ("after-bigidvfs", 2, "d03ca6dc"),
    ):
        line = (
            "GEMINI_A72_PHYSICAL_SOURCE_V1 token=GPSQ-20260824-A "
            f"checkpoint={checkpoint} slot={slot}"
        )
        require(f"{zlib.crc32(line.encode()):08x}" == checksum,
                f"retained CRC: {checkpoint}")

    generator = (EXPERIMENT / "scripts/generate-on-buildbox").read_text()
    for token in (
        "PARENT_SOURCE_STATE=6e3b726cd84b346409bb14b6fb66652b7a52aae60a4636b39229e949275d961f",
        "PARENT_SOURCE_INTEGRITY=75be833a675873a374e1b4ef1c77ba0557307b4d054eab793e31930d097785dd",
        "generated_patch_count=5",
        "retained_token=GPSQ-20260824-A",
        "provider_transactions=0",
        "publisher_calls=0",
        "owner_mutations=0",
        "cpu_requests=0",
        "checkpatch_intentional_ignore=SPLIT_STRING-for-two-atomic-retained-records",
        "boot_candidate=false",
    ):
        require(token in generator, f"generator token: {token}")
    source_edits = (EXPERIMENT / "scripts/source_edits.py").read_text()
    validator = (EXPERIMENT / "scripts/validate_source.py").read_text()
    for phase in ("ledger", "observer", "binding", "dts", "tests"):
        require(f'"{phase}"' in source_edits, f"source edit phase: {phase}")
    for token in (
        "exact component/checkpoint order",
        "reverse device release order",
        "raw all-ones and signature-last conditionals",
        "test physical operation",
    ):
        require(token in validator, f"source validator token: {token}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-a72-physical-source-patches",
        "fetch-a72-physical-source-patches",
    ):
        require(buildbox.count(command) >= 2, f"Buildbox command: {command}")
    require(
        "readonly source_root=\"${workspace_root}/src/linux-7.1.3-series-source\""
        in buildbox[buildbox.index("generate_a72_physical_source_patches"):],
        "exact managed source root",
    )
    require(
        "2026-08-24-mainline-a72-physical-source-observer"
        in (ROOT / "experiments/README.md").read_text(),
        "experiment index",
    )
    require(
        "generate-a72-physical-source-patches"
        in (ROOT / "docs/BUILDBOX.md").read_text(),
        "Buildbox documentation",
    )
    require(
        "Phase B physical-source observer"
        in (ROOT / "docs/ROADMAP.md").read_text(),
        "roadmap selection",
    )
    runner = (EXPERIMENT / "scripts/run-kunit-qemu").read_text()
    classifier = (EXPERIMENT / "scripts/classify-kunit.py").read_text()
    for token in (
        "EXPECTED_PROFILE=a72-physical-source-kunit",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST=y",
        "PSTORE_GEMINI_A72_PHYSICAL_SOURCE_LEDGER=y",
        "-nic none",
    ):
        require(token in runner, f"QEMU runner token: {token}")
    for token in (
        'SUITE = "mt6797-a72-physical-source"',
        '"mt6797_source_capture_failures_test"',
        'print("tests=4")',
        'print("boot_candidate=false")',
    ):
        require(token in classifier, f"classifier token: {token}")
    stack_generator = (EXPERIMENT / "scripts/generate-stack-fix-on-buildbox").read_text()
    stack_editor = (EXPERIMENT / "scripts/stack_fix_edits.py").read_text()
    stack_source_validator = (
        EXPERIMENT / "scripts/validate_stack_fix_source.py"
    ).read_text()
    stack_patch_validator = (
        EXPERIMENT / "scripts/validate_stack_fix_patch.py"
    ).read_text()
    for token in (
        "PARENT_SOURCE_STATE=419101daee0a40c89b12669b94bcec87674fafaa18624a75d2a5c5473766ba72",
        "TEST_SHA256=068748f876c2720ade9b96d17db90ef61ed78145a757e212322f57728bf7ee05",
        "kunit_direct_state_stack_objects=0",
        "production_changed=false",
        "boot_candidate=false",
    ):
        require(token in stack_generator, f"stack generator token: {token}")
    require(stack_editor.count("kunit_kzalloc(test, sizeof(*snapshot), GFP_KERNEL)")
            == 2, "two KUnit-managed stack-fix allocations")
    require("no direct-state snapshot remains on stack" in stack_source_validator,
            "stack source boundary")
    require("test-only path boundary" in stack_patch_validator,
            "stack patch boundary")
    require("exact numbered and folded patch subject" in stack_patch_validator,
            "stack patch subject boundary")
    for command in (
        "generate-a72-physical-source-stack-fix",
        "fetch-a72-physical-source-stack-fix",
    ):
        require(buildbox.count(command) >= 2,
                f"Buildbox stack-fix command: {command}")
    production_stack_generator = (
        EXPERIMENT / "scripts/generate-production-stack-fix-on-buildbox"
    ).read_text()
    production_stack_editor = (
        EXPERIMENT / "scripts/production_stack_fix_edits.py"
    ).read_text()
    production_stack_source_validator = (
        EXPERIMENT / "scripts/validate_production_stack_fix_source.py"
    ).read_text()
    production_stack_patch_validator = (
        EXPERIMENT / "scripts/validate_production_stack_fix_patch.py"
    ).read_text()
    for token in (
        "PARENT_SOURCE_STATE=3f1b291eaa793e8f5275bc3091fc2146312e1aeb65a81a5721f33805609cdc2c",
        "OBSERVER_SHA256=10e030caabfc420e676f46882e4ce24bdd21d77febcba1c8bc6e829331d9334d",
        "production_direct_state_stack_objects=0",
        "transaction_changed=false",
        "physical_operations_added=0",
        "boot_candidate=false",
    ):
        require(token in production_stack_generator,
                f"production stack generator token: {token}")
    require("snapshot = kvzalloc(sizeof(*snapshot), GFP_KERNEL)"
            in production_stack_editor, "production result allocation edit")
    require("kvfree(snapshot);" in production_stack_editor,
            "production result free edit")
    require("production direct-state result is not on the kernel stack"
            in production_stack_source_validator,
            "production stack source boundary")
    require("one production observer path" in production_stack_patch_validator,
            "production stack patch boundary")
    require("exact numbered patch subject" in production_stack_patch_validator,
            "production stack exact subject boundary")
    for command in (
        "generate-a72-physical-source-production-stack-fix",
        "fetch-a72-physical-source-production-stack-fix",
    ):
        require(buildbox.count(command) >= 2,
                f"Buildbox production stack-fix command: {command}")
    receipt = (
        EXPERIMENT / "results/buildbox-generation-8d0d4904.txt"
    ).read_text()
    for token in (
        "source_validation=pass-all-five-phases",
        "patch_replay=byte-exact-pass",
        "strict_checkpatch=0-errors-0-warnings-0-checks",
        "canonical_admission=0350-0354",
        "compile=pending",
        "boot_candidate=false",
    ):
        require(token in receipt, f"generation receipt token: {token}")
    qemu_failure = (
        EXPERIMENT / "results/qemu-98cf0ff3-stack-fixture-failure.txt"
    ).read_text()
    for token in (
        "build=pass",
        "passed_cases=2",
        "failed_cases=2",
        "failure_class=KUnit-worker-kernel-stack-boundary",
        "production_changed=false",
        "boot_candidate=false",
    ):
        require(token in qemu_failure, f"QEMU failure receipt token: {token}")
    stack_attempt = (
        EXPERIMENT / "results/stack-fix-generation-attempt-1-subject-validator.txt"
    ).read_text()
    for token in (
        "source_validation=pass",
        "stop=patch-subject-validator",
        "generated_artifact=none",
        "boot_candidate=false",
    ):
        require(token in stack_attempt, f"stack attempt receipt token: {token}")
    stack_receipt = (
        EXPERIMENT / "results/buildbox-stack-fix-generation-b3752361.txt"
    ).read_text()
    for token in (
        "source_validation=pass",
        "patch_boundary=test-only-one-file-pass",
        "patch_replay=byte-exact-pass",
        "strict_checkpatch=0-errors-0-warnings-0-checks",
        "canonical_admission=0355",
        "boot_candidate=false",
    ):
        require(token in stack_receipt, f"stack generation receipt token: {token}")
    qemu_pass = (
        EXPERIMENT / "results/qemu-ef0da357-pass.txt"
    ).read_text()
    for token in (
        "build=pass",
        "focused_cases=4",
        "failed=0",
        "skipped=0",
        "tap_summary=pass:4_fail:0_skip:0_total:4",
        "writer_symbols=absent",
        "device_action=none",
        "boot_candidate=false",
    ):
        require(token in qemu_pass, f"QEMU pass receipt token: {token}")
    production_stack_attempt = (
        EXPERIMENT
        / "results/production-stack-fix-generation-attempt-1-subject-validator.txt"
    ).read_text()
    for token in (
        "source_validation=pass",
        "stop=patch-subject-validator",
        "source_change=unchanged-for-retry",
        "generated_artifact=none",
        "boot_candidate=false",
    ):
        require(token in production_stack_attempt,
                f"production stack attempt token: {token}")
    readme = (EXPERIMENT / "README.md").read_text()
    require("candidate admission paused for production stack repair" in readme,
            "candidate pause status")
    require("roughly 32 KiB direct-state" in readme,
            "production stack discovery")
    print("validation=a72-physical-source-admission")
    print("prepared_source=exact-through-0349")
    print("generated_patch_count=5")
    print("focused_tests=4")
    print("canonical_admission=0350-0355")
    print("compile=pass")
    print("qemu=2-pass-2-test-stack-fault")
    print("stack_fix=generated-admitted-compile-pass")
    print("qemu_after_fix=pass-4-of-4")
    print("phase_b=hardware-free-complete")
    print("hardware_operations=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
