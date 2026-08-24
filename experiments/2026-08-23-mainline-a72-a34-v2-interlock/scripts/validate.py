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
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    series = (ROOT / "patches/series").read_text().splitlines()
    fragment = (ROOT / "configs/gemini-a72-a34-v2-kunit.fragment").read_text()
    runner = (EXPERIMENT / "scripts/run-kunit-qemu").read_text()
    classifier = (EXPERIMENT / "scripts/classify-kunit.py").read_text()
    build_result = (
        EXPERIMENT / "results/buildbox-compile-pass-20260824.txt"
    ).read_text()
    qemu_result = (
        EXPERIMENT / "results/kunit-qemu-pass-20260824.txt"
    ).read_text()

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
    build = contract["build"]
    require(build["repository_commit"] ==
            "b89e284f2ba7d663f3086f2b108e0ca1dcb0bca0",
            "build repository commit")
    require(build["buildbox_job"] ==
            "b89e284f2ba7d663f3086f2b108e0ca1dcb0bca0-"
            "a72-a34-v2-kunit-m0", "buildbox job")
    require(build["package"] ==
            "linux-7.1.3-gemini-a72-a34-v2-kunit-5bfb371e-0f62ecbf",
            "build package")
    require(build["kernel_release"] ==
            "7.1.3-gemini-a34-v2-kunit", "kernel release")
    require(build["source_sha256"] ==
            "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc",
            "build source identity")
    require(build["patchset_sha256"] ==
            "5bfb371e092a88374d91695151e51971fcf22f0c97a8066baada28a853a56d19",
            "build patchset identity")
    require(build["config_sha256"] ==
            "0779246848f2217146e1c1099265b55755a7c22598cdacedb44cece2c184d197",
            "build configuration identity")
    require(build["image_sha256"] ==
            "bbe3d78dfd1b23bb8128e2ab7dacc825ad06e8801af8b739ecc575edfe2393fb",
            "build Image identity")
    require(build["image_gzip_sha256"] ==
            "f85653844d56f6aa1852f52f357cdeebefb37ffcf9416f996543a058bad9c271",
            "build Image.gz identity")
    require(build["build_exit"] == 0 and
            build["artifact_validation"] == "pass" and
            build["classification"] == "pass-no-new-stack-warning" and
            build["introduced_frame_warning_count"] == 0 and
            build["inherited_frame_warning_count"] == 2 and
            build["qemu_run"] is True and
            build["boot_candidate"] is False,
            "Buildbox compile classification")
    require(build["evidence"] ==
            "results/buildbox-compile-pass-20260824.txt",
            "build evidence path")
    qemu = contract["qemu"]
    require(qemu["repository_commit"] == build["repository_commit"] and
            qemu["profile"] == "a72-a34-v2-kunit" and
            qemu["kernel_release"] == build["kernel_release"] and
            qemu["image_sha256"] == build["image_sha256"],
            "QEMU artifact identity")
    require(qemu["runner"] == "qemu-system-aarch64-11.0.2" and
            qemu["network"] == "none" and
            qemu["suites"] == 3 and qemu["tests"] == 32 and
            qemu["failed"] == 0 and qemu["skipped"] == 0 and
            qemu["result"] == "pass" and
            qemu["post_test_state"] == "expected-vm-rootfs-panic",
            "focused QEMU result")
    require(qemu["production_callers"] == 0 and
            qemu["owner_publication"] is False and
            qemu["physical_reader_binding"] is False and
            qemu["device_action"] is False and
            qemu["boot_candidate"] is False,
            "QEMU scope closure")
    require(qemu["evidence"] == "results/kunit-qemu-pass-20260824.txt",
            "QEMU evidence path")
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

    for token in (
        "EXPECTED_PROFILE=a72-a34-v2-kunit", "sha256sum --check --strict",
        "merge-base --is-ancestor", "-nic none", "timeout --signal=TERM 45",
        "focused KUnit inventory changed", "classify-kunit.py",
    ):
        require(token in runner, f"QEMU runner invariant {token}")
    for token in (
        'PROFILE = "a72-a34-v2-kunit"', '"arm64-late-cpu-startup"',
        '"mt6797-a72-a34-eligibility"', '"mt6797-a72-direct-state"',
        '"1..3", "1..20", "1..5", "1..7"',
        "expected post-test rootfs panic", "tests={total_tests}",
        'print("owner_publication=false")',
        'print("physical_reader_binding=false")',
        'print("boot_candidate=false")',
    ):
        require(token in classifier, f"QEMU classifier invariant {token}")
    for token in (
        "repository_commit=b89e284f2ba7d663f3086f2b108e0ca1dcb0bca0",
        "artifact_validation=pass",
        "classification=pass-no-new-stack-warning",
        "introduced_frame_warning_count=0",
        "inherited_frame_warning_count=2",
        "boot_candidate=false",
    ):
        require(token in build_result, f"build result invariant {token}")
    for token in (
        "repository_commit=b89e284f2ba7d663f3086f2b108e0ca1dcb0bca0",
        "network=none", "suites=3", "tests=32", "failed=0",
        "skipped=0", "tap_summary=pass:32_fail:0_skip:0_total:32",
        "owner_publication=false", "physical_reader_binding=false",
        "device_action=none", "boot_candidate=false",
    ):
        require(token in qemu_result, f"QEMU result invariant {token}")

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
        "completed hardware-free compile and focused runtime proof",
        "no production caller", "not physical evidence",
        "All 32 passed", "It does not publish",
    ):
        require(token in readme, f"README closure {token}")
    for token in (
        "all 32 cases under no-network arm64 QEMU",
        "separate hardware-free review of the atomic single membership",
        "retaining both CPU vetoes",
        "Production positive", "physical source binding remain separate",
    ):
        require(token in roadmap, f"Roadmap next-step invariant {token}")

    for relative in (
        "scripts/source_edits.py", "scripts/validate_source.py",
        "scripts/validate_patch.py", "scripts/generate-on-buildbox",
        "scripts/run-kunit-qemu", "scripts/classify-kunit.py",
        "results/buildbox-compile-pass-20260824.txt",
        "results/kunit-qemu-pass-20260824.txt",
    ):
        path = EXPERIMENT / relative
        require(path.exists() and not path.is_symlink(),
                f"missing or unsafe definition file {relative}")

    print("validation=a34-v2-interlock-definition")
    print("admitted_patch_count=3")
    print("generation=pass")
    print("build_backend=buildbox")
    print("compile=pass-no-new-stack-warning")
    print("inherited_frame_warning_count=2")
    print("qemu_suites=3")
    print("qemu_tests=32")
    print("qemu_failed=0")
    print("qemu_skipped=0")
    print("production_callers=0")
    print("owner_publication=false")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
