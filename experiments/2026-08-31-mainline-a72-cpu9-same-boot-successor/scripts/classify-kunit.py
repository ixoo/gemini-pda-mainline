#!/usr/bin/env python3
"""Classify the exact hardware-free Gemini CPU9 executor KUnit proof."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROFILE = "gemini-cpu9-executor-kunit"
EXPECTED_RELEASE = "7.1.3-gemini-cpu9-executor-kunit"
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"
SUITES = (
    (
        "mt6797-a72-p24-owner",
        (
            "mt6797_a72_owner_initial_closed",
            "mt6797_a72_owner_cpu8_denied",
            "mt6797_a72_owner_cpu9_denied",
            "mt6797_a72_owner_public_hook_denied",
            "mt6797_a72_owner_internal_hook_denied",
            "mt6797_a72_owner_non_target_invalid",
            "mt6797_a72_owner_intermediate_target_invalid",
            "mt6797_a72_owner_repeat_is_diagnostic",
            "mt6797_a72_owner_entry_snapshot_gate",
            "mt6797_a72_owner_p31_consumes_once",
            "mt6797_a72_owner_a36_rejects_without_rearm",
            "mt6797_a72_owner_a36_prestate_mutations_rejected",
            "mt6797_a72_owner_cpu9_mints_distinct_token",
            "mt6797_a72_owner_p17_cpu8_publishes_once",
            "mt6797_a72_owner_p18_cpu9_preserves_provider",
            "mt6797_a72_owner_p18_without_provider_rejected",
            "mt6797_a72_owner_p27_cpu8_preparation_once",
            "mt6797_a72_owner_p27_rejects_bad_or_cpu9_proof",
            "mt6797_a72_owner_r01_r02_provider_once",
            "mt6797_a72_owner_r02_rejects_bad_proof_or_cpu9",
            "mt6797_a72_owner_p28_cpu8_preparation_once",
            "mt6797_a72_owner_p28_rejects_bad_proof_or_cpu9",
            "mt6797_a72_owner_r03_p29_rejects_and_retires",
            "mt6797_a72_owner_r03_p29_mutations_rejected",
            "mt6797_a72_owner_binder_success_handoff",
            "mt6797_a72_owner_binder_p32_from_verifying",
            "mt6797_a72_owner_binder_clean_rejection",
            "mt6797_a72_owner_binder_p29_without_provider",
            "mt6797_a72_owner_cpu9_parent_gate",
            "mt6797_a72_owner_cpu9_parent_mutations",
            "mt6797_a72_owner_cpu9_success_lifecycle",
            "mt6797_a72_owner_cpu9_rejection_one_shot",
            "mt6797_a72_owner_forged_token_rejected",
            "mt6797_a72_owner_no_live_token",
        ),
    ),
    (
        "mt6797-a72-transition-executor",
        (
            "mt6797_transition_split_success_test",
            "mt6797_transition_composed_run_test",
            "mt6797_transition_entry_rejections_test",
            "mt6797_transition_missing_op_test",
            "mt6797_transition_one_shot_test",
            "mt6797_transition_stage_failures_test",
            "mt6797_transition_checkpoint_failures_test",
            "mt6797_transition_terminal_failures_test",
            "mt6797_transition_lifecycle_failure_test",
            "mt6797_transition_handoff_guards_test",
            "mt6797_transition_malformed_ownership_test",
            "mt6797_transition_rollback_faults_test",
        ),
    ),
    (
        "mt6797-a72-default-off-binder",
        (
            "mt6797_binder_success_test",
            "mt6797_binder_terminal_failure_test",
            "mt6797_binder_preiso_checkpoint_test",
            "mt6797_binder_malformed_owners_test",
            "mt6797_binder_p27_diagnostic_test",
            "mt6797_binder_sram_diagnostic_test",
            "mt6797_binder_sram_selector_mask_test",
            "mt6797_binder_p30e_readback_test",
            "mt6797_binder_one_shot_test",
        ),
    ),
    (
        "mt6797-a72-cpu9-executor",
        (
            "mt6797_cpu9_executor_success_test",
            "mt6797_cpu9_executor_split_success_test",
            "mt6797_cpu9_executor_entry_rejections_test",
            "mt6797_cpu9_executor_missing_op_test",
            "mt6797_cpu9_executor_one_shot_test",
            "mt6797_cpu9_executor_stage_failures_test",
            "mt6797_cpu9_executor_checkpoint_failures_test",
            "mt6797_cpu9_executor_lifecycle_guards_test",
            "mt6797_cpu9_executor_failure_dispatch_test",
            "mt6797_cpu9_executor_terminal_failures_test",
        ),
    ),
)


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
    require(len(matches) == 1,
            f"checksum manifest entry absent or duplicated: {entry}")
    return matches[0]


def clean_lines(raw: str) -> list[str]:
    lines = []
    for line in raw.replace("\r", "").splitlines():
        line = re.sub(r"^\[\s*\d+\.\d+\]\s*", "", line)
        lines.append(line.strip())
    return lines


def classify_runtime(raw: str, expected_release: str, qemu_exit: int) -> None:
    lines = clean_lines(raw)
    release_matches = re.findall(r"Linux version ([^ ]+)", raw)
    require(release_matches == [expected_release],
            f"kernel release mismatch: {release_matches}")
    require(qemu_exit == 124,
            f"unexpected QEMU exit (expected bounded timeout): {qemu_exit}")
    require("KTAP version 1" in lines, "top-level KTAP header absent")
    start = lines.index("KTAP version 1")
    ktap = lines[start:]
    require(ktap.count("KTAP version 1") == len(SUITES) + 1,
            "expected one top-level and four suite KTAP headers")
    plans = [line for line in ktap if re.fullmatch(r"1\.\.\d+", line)]
    require(plans == ["1..4", "1..34", "1..12", "1..9", "1..10"],
            f"KUnit plans changed: {plans}")
    subtests = [line for line in ktap if line.startswith("# Subtest: ")]
    require(subtests == [f"# Subtest: {suite}" for suite, _ in SUITES],
            f"suite inventory changed: {subtests}")
    require(not any(line.startswith("not ok ") for line in ktap),
            "KTAP contains a failing result")

    expected_ok = []
    for suite_index, (suite, cases) in enumerate(SUITES, start=1):
        expected_ok.extend(
            f"ok {case_index} {case}"
            for case_index, case in enumerate(cases, start=1)
        )
        expected_ok.append(f"ok {suite_index} {suite}")
        summary = f"# {suite}: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        totals = f"# Totals: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        require(ktap.count(summary) == 1,
                f"suite summary is not an exact pass: {suite}")
        require(ktap.count(totals) == 1,
                f"suite totals are not an exact pass: {suite}")
    observed_ok = [line for line in ktap if re.fullmatch(r"ok \d+ \S+", line)]
    require(observed_ok == expected_ok,
            f"case or suite inventory changed: {observed_ok}")
    require(Counter(observed_ok) == Counter(expected_ok),
            "KUnit results are duplicated")

    final_result = f"ok {len(SUITES)} {SUITES[-1][0]}"
    result_index = ktap.index(final_result)
    panic_indices = [index for index, line in enumerate(ktap)
                     if line.startswith(PANIC_PREFIX)]
    require(len(panic_indices) == 1 and panic_indices[0] > result_index,
            "expected post-test rootfs panic boundary absent or reordered")
    end_indices = [index for index, line in enumerate(ktap)
                   if line.startswith(PANIC_END_PREFIX)]
    require(len(end_indices) == 1 and end_indices[0] > panic_indices[0],
            "expected terminal panic marker absent or reordered")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--raw-log", type=Path, required=True)
    parser.add_argument("--qemu-exit", type=int, required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--harness-commit", required=True)
    args = parser.parse_args()
    for label, commit in (("repository", args.repository_commit),
                          ("harness", args.harness_commit)):
        require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
                f"invalid {label} commit")

    package = args.package.resolve()
    raw_log = args.raw_log.resolve()
    build_path = package / "provenance/build.json"
    image = package / "Image"
    image_gzip = package / "Image.gz"
    config = package / "kernel.config"
    system_map = package / "System.map"
    sums = package / "SHA256SUMS"
    for path in (build_path, image, image_gzip, config, system_map, sums,
                 raw_log):
        require(path.is_file() and not path.is_symlink(),
                f"required regular file absent or unsafe: {path.name}")
    build = json.loads(build_path.read_text(encoding="utf-8"))
    require(build["repository_commit"] == args.repository_commit,
            "package repository commit mismatch")
    require(build["repository_dirty"] is False, "package source was dirty")
    require(build["build_profile"] == PROFILE, "package profile mismatch")
    require(build["kernel_release"] == EXPECTED_RELEASE,
            "kernel release changed")
    require(build["target_architecture"] == "arm64",
            "package target architecture mismatch")
    require(build["modules_built"] is False, "unexpected module build")
    identities = {
        "image_sha256": sha256(image),
        "image_gzip_sha256": sha256(image_gzip),
        "config_sha256": sha256(config),
        "system_map_sha256": sha256(system_map),
    }
    for key, entry in (("image_sha256", "./Image"),
                       ("image_gzip_sha256", "./Image.gz"),
                       ("config_sha256", "./kernel.config"),
                       ("system_map_sha256", "./System.map")):
        require(identities[key] == manifest_checksum(sums, entry),
                f"package checksum mismatch: {entry}")
    require(identities["config_sha256"] == build["config_sha256"],
            "configuration checksum mismatch")

    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    classify_runtime(raw, EXPECTED_RELEASE, args.qemu_exit)
    qemu_version = subprocess.run(
        ["qemu-system-aarch64", "--version"], check=True,
        capture_output=True, text=True).stdout.splitlines()[0]
    observed_utc = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")
    scripts = Path(__file__).resolve().parent
    total_tests = sum(len(cases) for _, cases in SUITES)

    print("experiment=2026-08-31-mainline-a72-cpu9-same-boot-successor")
    print("phase=kunit-qemu")
    print(f"observed_utc={observed_utc}")
    print(f"repository_commit={args.repository_commit}")
    print(f"harness_commit={args.harness_commit}")
    print(f"profile={PROFILE}")
    print(f"kernel_release={EXPECTED_RELEASE}")
    print(f"source_sha256={build['source_sha256']}")
    print(f"patchset_sha256={build['patchset_sha256']}")
    for key, value in identities.items():
        print(f"{key}={value}")
    print(f"raw_log_sha256={sha256(raw_log)}")
    print(f"runner_sha256={sha256(scripts / 'run-kunit-qemu')}")
    print(f"classifier_sha256={sha256(Path(__file__).resolve())}")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt-cortex-a53-four-vcpu-no-network")
    print(f"suites={len(SUITES)}")
    print(f"tests={total_tests}")
    print("cpu9_membership_tests=4")
    print("cpu9_executor_tests=10")
    print("regression_tests=55")
    print("failed=0")
    print("skipped=0")
    for suite, cases in SUITES:
        print(f"suite_{suite}=pass:{len(cases)}_fail:0_skip:0_total:{len(cases)}")
        for case in cases:
            print(f"{case}=pass")
    print(f"tap_summary=pass:{total_tests}_fail:0_skip:0_total:{total_tests}")
    print("post_test_state=expected_vm_rootfs_panic")
    print("qemu_exit=124")
    print("result=pass")
    print("cpu8_parent=retired-slot0-exact-success")
    print("cpu9_attempt=fresh-one-shot")
    print("cpu9_cluster_budgets=all-none")
    print("cpu9_cpu_on_budget=one")
    print("cpu9_success_members=bits0-1")
    print("cpu9_rejection=retains-cpu8-provider")
    print("physical_backends=0")
    print("mmio=false")
    print("retained_ram=false")
    print("watchdog=false")
    print("smc=false")
    print("production_callers=0")
    print("physical_cpu_requests=0")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
