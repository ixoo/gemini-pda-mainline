#!/usr/bin/env python3
"""Classify isolated, hardware-free CPU8 admission KUnit profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DERIVED_SUITE = "mt6797-a72-derived-admission"
CONTROLLER_SUITE = "mt6797-a72-admission-controller"
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"
EXPECTED_PROFILES = {
    "a72-derived-admission-kunit": {
        DERIVED_SUITE: (
            "mt6797_a72_derived_success_test",
            "mt6797_a72_derived_source_rejections_test",
            "mt6797_a72_derived_ready_rejection_test",
            "mt6797_a72_legacy_assertions_rejected_test",
            "mt6797_a72_derived_repeat_rejected_test",
        ),
    },
    "a72-admission-controller-kunit": {
        DERIVED_SUITE: (
            "mt6797_a72_derived_success_test",
            "mt6797_a72_derived_source_rejections_test",
            "mt6797_a72_derived_ready_rejection_test",
            "mt6797_a72_legacy_assertions_rejected_test",
            "mt6797_a72_derived_repeat_rejected_test",
        ),
        CONTROLLER_SUITE: (
            "mt6797_a72_admission_success_test",
            "mt6797_a72_admission_preconsume_gates_test",
            "mt6797_a72_admission_terminal_failures_test",
            "mt6797_a72_admission_request_failure_test",
            "mt6797_a72_admission_repeat_closed_test",
        ),
    },
}


class ClassificationError(RuntimeError):
    """Raised when runtime evidence does not prove the exact suite."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ClassificationError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_checksum(path: Path, entry: str) -> str:
    pattern = rf"^([0-9a-f]{{64}})  {re.escape(entry)}$"
    matches = re.findall(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    require(
        len(matches) == 1,
        f"checksum manifest entry absent or duplicated: {entry}",
    )
    return matches[0]


def clean_lines(raw: str) -> list[str]:
    lines = []
    for line in raw.replace("\r", "").splitlines():
        line = re.sub(r"^\[\s*\d+\.\d+\]\s*", "", line)
        lines.append(line.strip())
    return lines


def validate_config(config: Path, profile: str) -> None:
    text = config.read_text(encoding="utf-8")
    lines = text.splitlines()
    required = (
        "CONFIG_KUNIT=y",
        "CONFIG_KUNIT_DEFAULT_ENABLED=y",
        "CONFIG_KUNIT_AUTORUN_ENABLED=y",
        "CONFIG_CMDLINE_FORCE=y",
        "CONFIG_ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL=y",
        "CONFIG_ARM64_MT6797_A72_P24_OWNER_TEST_SEED=y",
        "CONFIG_ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR=y",
        "CONFIG_ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR=y",
        "CONFIG_ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER=y",
        "CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION=y",
        "CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST=y",
    )
    for token in required:
        require(token in lines, f"configuration missing: {token}")
    if profile == "a72-admission-controller-kunit":
        for token in (
            "CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER=y",
            "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_OBSERVER=y",
            "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y",
            "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER_KUNIT_TEST=y",
        ):
            require(token in lines, f"controller configuration missing: {token}")
    excluded = (
        "CONFIG_ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST=y",
        "CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER_KUNIT_TEST=y",
        "CONFIG_MTK_MT6797_A72_TRANSITION_EXECUTOR_KUNIT_TEST=y",
        "CONFIG_MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST=y",
    )
    if profile == "a72-derived-admission-kunit":
        excluded += (
            "CONFIG_MTK_MT6797_A72_DEFAULT_OFF_BINDER=y",
            "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER=y",
            "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER_KUNIT_TEST=y",
        )
    for token in excluded:
        require(token not in lines, f"excluded path enabled: {token}")
    focused = re.findall(r"^CONFIG_.*_KUNIT_TEST=y$", text, re.MULTILINE)
    expected_focused = [
        "CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST=y"
    ]
    if profile == "a72-admission-controller-kunit":
        expected_focused.append(
            "CONFIG_MTK_MT6797_A72_ADMISSION_CONTROLLER_KUNIT_TEST=y"
        )
    require(
        focused == expected_focused,
        f"focused KUnit inventory changed: {focused}",
    )


def classify_runtime(
    raw: str,
    expected_release: str,
    expected_suites: dict[str, tuple[str, ...]],
) -> None:
    lines = clean_lines(raw)
    releases = re.findall(r"Linux version ([^ ]+)", raw)
    require(releases == [expected_release], f"kernel release mismatch: {releases}")
    require("KTAP version 1" in lines, "top-level KTAP header absent")
    start = lines.index("KTAP version 1")
    ktap = lines[start:]
    suite_count = len(expected_suites)
    test_count = sum(len(cases) for cases in expected_suites.values())
    require(
        ktap.count("KTAP version 1") == suite_count + 1,
        "unexpected KTAP header count",
    )
    require(
        ktap.count(f"1..{suite_count}") == 1,
        "top-level suite plan changed",
    )
    require(ktap.count("1..5") == suite_count, "focused test plans changed")
    for suite in expected_suites:
        require(
            ktap.count(f"# Subtest: {suite}") == 1,
            f"focused suite absent or duplicated: {suite}",
        )
    require(
        not any(
            line.startswith("# Subtest: ")
            and line.removeprefix("# Subtest: ") not in expected_suites
            for line in ktap
        ),
        "an unexpected KUnit suite executed",
    )
    require(
        not any(line.startswith("not ok ") for line in ktap),
        "KTAP contains a failing result",
    )
    observed: list[tuple[int, str]] = []
    for line in ktap:
        match = re.fullmatch(r"ok (\d+) ([A-Za-z0-9_]+)", line)
        if match:
            observed.append((int(match.group(1)), match.group(2)))
    observed_cases = [case for _, case in observed]
    expected_cases = [case for cases in expected_suites.values() for case in cases]
    require(
        sorted(observed_cases) == sorted(expected_cases),
        f"focused case inventory changed: {observed}",
    )
    for suite, cases in expected_suites.items():
        summary = f"# {suite}: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        require(ktap.count(summary) == 1, f"suite summary is not exact pass: {suite}")
    expected_totals: dict[str, int] = {}
    for cases in expected_suites.values():
        totals = (
            f"# Totals: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        )
        expected_totals[totals] = expected_totals.get(totals, 0) + 1
    for totals, count in expected_totals.items():
        require(
            ktap.count(totals) == count,
            f"per-suite KUnit totals are not exact pass: {totals}",
        )
    suite_results: list[tuple[int, str, int]] = []
    for index, line in enumerate(ktap):
        match = re.fullmatch(r"ok (\d+) ([a-z0-9-]+)", line)
        if match and match.group(2) in expected_suites:
            suite_results.append((int(match.group(1)), match.group(2), index))
    require(
        len(suite_results) == suite_count
        and sorted(number for number, _, _ in suite_results)
        == list(range(1, suite_count + 1))
        and sorted(suite for _, suite, _ in suite_results)
        == sorted(expected_suites),
        f"top-level suite results changed: {suite_results}",
    )
    result_index = max(index for _, _, index in suite_results)
    panics = [
        index for index, line in enumerate(ktap) if line.startswith(PANIC_PREFIX)
    ]
    require(
        len(panics) == 1 and panics[0] > result_index,
        "expected post-test rootfs panic boundary absent or reordered",
    )
    panic_ends = [
        index for index, line in enumerate(ktap) if line.startswith(PANIC_END_PREFIX)
    ]
    require(
        len(panic_ends) == 1 and panic_ends[0] > panics[0],
        "expected terminal panic marker absent or reordered",
    )
    for forbidden in (
        "BUG:",
        "Unable to handle kernel",
        "SError Interrupt",
        "stack overflow",
        "stack-protector",
    ):
        require(forbidden not in raw, f"unexpected kernel fault: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--raw-log", type=Path, required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument(
        "--termination",
        choices=("harness-after-terminal-marker",),
        required=True,
    )
    args = parser.parse_args()
    require(
        re.fullmatch(r"[0-9a-f]{40}", args.repository_commit) is not None,
        "invalid repository commit",
    )

    package = args.package.resolve()
    raw_log = args.raw_log.resolve()
    build_path = package / "provenance/build.json"
    image = package / "Image"
    config = package / "kernel.config"
    system_map = package / "System.map"
    sums = package / "SHA256SUMS"
    for path in (build_path, image, config, system_map, sums, raw_log):
        require(
            path.is_file() and not path.is_symlink(),
            f"required regular file absent or unsafe: {path.name}",
        )
    build = json.loads(build_path.read_text(encoding="utf-8"))
    require(
        build["repository_commit"] == args.repository_commit,
        "package repository commit mismatch",
    )
    require(build["repository_dirty"] is False, "package source was dirty")
    profile = build["build_profile"]
    require(profile in EXPECTED_PROFILES, "package profile mismatch")
    require(build["target_architecture"] == "arm64", "target is not arm64")
    require(build["modules_built"] is False, "unexpected module build")

    image_sha256 = sha256(image)
    config_sha256 = sha256(config)
    system_map_sha256 = sha256(system_map)
    require(
        image_sha256 == manifest_checksum(sums, "./Image"),
        "Image checksum mismatch",
    )
    require(
        config_sha256 == manifest_checksum(sums, "./kernel.config"),
        "configuration checksum mismatch",
    )
    require(
        system_map_sha256 == manifest_checksum(sums, "./System.map"),
        "System.map checksum mismatch",
    )
    require(config_sha256 == build["config_sha256"], "build config mismatch")
    validate_config(config, profile)

    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    expected_suites = EXPECTED_PROFILES[profile]
    classify_runtime(raw, build["kernel_release"], expected_suites)
    qemu_version = subprocess.run(
        ["qemu-system-aarch64", "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]
    observed_utc = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    print(f"experiment={Path(__file__).resolve().parents[1].name}")
    print("phase=kunit-qemu")
    print(f"observed_utc={observed_utc}")
    print(f"repository_commit={args.repository_commit}")
    print(f"profile={profile}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"image_sha256={image_sha256}")
    print(f"config_sha256={config_sha256}")
    print(f"system_map_sha256={system_map_sha256}")
    print(f"raw_log_sha256={sha256(raw_log)}")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt-cortex-a53-four-vcpu-no-network")
    test_count = sum(len(cases) for cases in expected_suites.values())
    print(f"suites={len(expected_suites)}")
    print(f"tests={test_count}")
    print("failed=0")
    print("skipped=0")
    for cases in expected_suites.values():
        for case in cases:
            print(f"{case}=pass")
    print(f"aggregate_result=pass:{test_count}_fail:0_skip:0_total:{test_count}")
    print(f"suite_summary_count={len(expected_suites)}")
    print("post_test_state=expected_vm_rootfs_panic")
    print(f"termination={args.termination}")
    print("result=pass")
    print("owner_kunit_suite=false")
    print("stack_fault=false")
    print("network=false")
    print("mmio=false")
    print("retained_ram=false")
    print("watchdog=false")
    print("smc=false")
    print("production_cpu_requests=0")
    print("physical_operations=0")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
