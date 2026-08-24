#!/usr/bin/env python3
"""Classify the exact hardware-free atomic-publication KUnit proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


PROFILE = "a72-atomic-publication-kunit"
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"
SUITES = (
    (
        "arm64-late-cpu-startup",
        (
            "late_cpu_startup_bootstrap_claim_excludes_prepare_test",
            "late_cpu_startup_bootstrap_claim_identity_test",
            "late_cpu_startup_bootstrap_claim_rejects_nonpristine_test",
            "late_cpu_startup_invalid_token_test",
            "late_cpu_startup_abort_is_one_shot_test",
            "late_cpu_startup_unproven_cpu_on_test",
            "late_cpu_startup_cpu_on_fault_test",
            "late_cpu_startup_cancel_wins_test",
            "late_cpu_startup_cpu8_then_cpu9_test",
            "late_cpu_startup_armed_quarantine_test",
            "late_cpu_startup_publishing_quarantine_test",
            "late_cpu_startup_publishing_wrong_target_test",
            "late_cpu_startup_online_mismatch_test",
            "late_cpu_startup_premature_retire_test",
            "late_cpu_startup_terminal_branches_test",
            "late_cpu_startup_k_to_c_immutability_test",
            "late_cpu_startup_panic_order_test",
            "late_cpu_startup_target_tuple_test",
            "late_cpu_startup_invalid_failure_branch_test",
            "late_cpu_startup_prearmed_target_claim_test",
        ),
    ),
    (
        "mt6797-a72-atomic-publication",
        (
            "atomic_finalizer_success_test",
            "atomic_finalizer_failure_identity_test",
            "atomic_publication_success_repeat_test",
            "atomic_publication_replay_rejections_test",
            "atomic_publication_source_rejections_test",
            "atomic_publication_topology_rejection_test",
            "atomic_publication_p30_busy_test",
            "atomic_publication_final_owner_mismatch_test",
        ),
    ),
)


class ClassificationError(RuntimeError):
    """Raised when runtime evidence does not prove the exact suites."""


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
    matches = re.findall(
        rf"^([0-9a-f]{{64}})  {re.escape(entry)}$",
        path.read_text(encoding="utf-8"), re.MULTILINE)
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
    releases = re.findall(r"Linux version ([^ ]+)", raw)
    require(releases == [expected_release], f"kernel release mismatch: {releases}")
    require(qemu_exit == 124,
            f"unexpected QEMU exit (expected bounded timeout): {qemu_exit}")
    require("KTAP version 1" in lines, "top-level KTAP header absent")
    ktap = lines[lines.index("KTAP version 1"):]
    require(ktap.count("KTAP version 1") == 3,
            "expected one top-level and two suite KTAP headers")
    require([line for line in ktap if re.fullmatch(r"1\.\.\d+", line)] ==
            ["1..2", "1..20", "1..8"],
            "KUnit plans changed")
    require([line for line in ktap if line.startswith("# Subtest: ")] ==
            [f"# Subtest: {suite}" for suite, _ in SUITES],
            "focused suite inventory changed")
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
                f"suite summary is not exact pass: {suite}")
        require(ktap.count(totals) == 1,
                f"suite totals are not exact pass: {suite}")
    observed_ok = [line for line in ktap if re.fullmatch(r"ok \d+ \S+", line)]
    require(observed_ok == expected_ok,
            f"focused case or suite inventory changed: {observed_ok}")
    require(Counter(observed_ok) == Counter(expected_ok),
            "focused results are duplicated")

    final_result = f"ok {len(SUITES)} {SUITES[-1][0]}"
    result_index = ktap.index(final_result)
    panics = [index for index, line in enumerate(ktap)
              if line.startswith(PANIC_PREFIX)]
    require(len(panics) == 1 and panics[0] > result_index,
            "expected post-test rootfs panic absent or reordered")
    panic_ends = [index for index, line in enumerate(ktap)
                  if line.startswith(PANIC_END_PREFIX)]
    require(len(panic_ends) == 1 and panic_ends[0] > panics[0],
            "terminal panic marker absent or reordered")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--raw-log", type=Path, required=True)
    parser.add_argument("--qemu-exit", type=int, required=True)
    parser.add_argument("--repository-commit", required=True)
    args = parser.parse_args()

    require(re.fullmatch(r"[0-9a-f]{40}", args.repository_commit) is not None,
            "invalid repository commit")
    package = args.package.resolve()
    raw_log = args.raw_log.resolve()
    build_path = package / "provenance/build.json"
    image = package / "Image"
    image_gzip = package / "Image.gz"
    config = package / "kernel.config"
    sums = package / "SHA256SUMS"
    for path in (build_path, image, image_gzip, config, sums, raw_log):
        require(path.is_file() and not path.is_symlink(),
                f"required regular file absent or unsafe: {path.name}")
    build = json.loads(build_path.read_text(encoding="utf-8"))
    require(build["repository_commit"] == args.repository_commit,
            "package repository commit mismatch")
    require(build["repository_dirty"] is False, "package source was dirty")
    require(build["build_profile"] == PROFILE, "package profile mismatch")
    require(build["target_architecture"] == "arm64",
            "package target architecture mismatch")
    require(build["modules_built"] is False, "unexpected module build")
    image_sha256 = sha256(image)
    image_gzip_sha256 = sha256(image_gzip)
    config_sha256 = sha256(config)
    require(image_sha256 == manifest_checksum(sums, "./Image"),
            "Image checksum mismatch")
    require(image_gzip_sha256 == manifest_checksum(sums, "./Image.gz"),
            "Image.gz checksum mismatch")
    require(config_sha256 == manifest_checksum(sums, "./kernel.config"),
            "configuration checksum mismatch")
    require(config_sha256 == build["config_sha256"],
            "configuration provenance mismatch")

    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    classify_runtime(raw, build["kernel_release"], args.qemu_exit)
    qemu_version = subprocess.run(
        ["qemu-system-aarch64", "--version"], check=True,
        capture_output=True, text=True).stdout.splitlines()[0]
    observed_utc = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")
    total_tests = sum(len(cases) for _, cases in SUITES)

    print("experiment=2026-08-24-mainline-a72-atomic-publication")
    print("phase=kunit-qemu")
    print(f"observed_utc={observed_utc}")
    print(f"repository_commit={args.repository_commit}")
    print(f"profile={PROFILE}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"source_sha256={build['source_sha256']}")
    print(f"patchset_sha256={build['patchset_sha256']}")
    print(f"image_sha256={image_sha256}")
    print(f"image_gzip_sha256={image_gzip_sha256}")
    print(f"config_sha256={config_sha256}")
    print("runner=qemu-system-aarch64")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt")
    print("cpu=cortex-a53")
    print("vcpus=4")
    print("network=none")
    print(f"suites={len(SUITES)}")
    print(f"tests={total_tests}")
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
    print("production_callers=0")
    print("injected_owner_publication=true")
    print("production_owner_publication=false")
    print("physical_reader_binding=false")
    print("hardware_effect=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("cpu_on=false")
    print("cpu_off=false")


if __name__ == "__main__":
    main()
