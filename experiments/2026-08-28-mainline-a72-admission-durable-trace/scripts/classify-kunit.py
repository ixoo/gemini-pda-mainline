#!/usr/bin/env python3
"""Classify the exact hardware-free durable admission-trace KUnit proof."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


PROFILE = "a72-admission-trace-kunit"
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"
SUITES = (
    (
        "gemini-admission-trace",
        (
            "gemini_admission_trace_entry_commit_test",
            "gemini_admission_trace_entry_reentry_test",
            "gemini_admission_trace_foreign_refusal_test",
            "gemini_admission_trace_terminal_records_test",
            "gemini_admission_trace_terminal_gates_test",
            "gemini_admission_trace_torn_write_test",
        ),
    ),
    (
        "mt6797-a72-admission-controller",
        (
            "mt6797_a72_admission_success_test",
            "mt6797_a72_admission_preconsume_gates_test",
            "mt6797_a72_admission_terminal_failures_test",
            "mt6797_a72_admission_request_failure_test",
            "mt6797_a72_admission_trace_failures_test",
            "mt6797_a72_admission_repeat_closed_test",
        ),
    ),
)


class ClassificationError(RuntimeError):
    """Raised when the runtime evidence does not prove the exact contract."""


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
        path.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    require(len(matches) == 1,
            f"checksum entry absent or duplicated: {entry}")
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
    require(releases == [expected_release],
            f"kernel release mismatch: {releases}")
    require(qemu_exit == 124,
            f"unexpected QEMU exit (expected bounded timeout): {qemu_exit}")
    require("KTAP version 1" in lines, "top-level KTAP header absent")
    ktap = lines[lines.index("KTAP version 1"):]
    require(ktap.count("KTAP version 1") == len(SUITES) + 1,
            "expected one top-level and two suite KTAP headers")
    plans = [line for line in ktap if re.fullmatch(r"1\.\.\d+", line)]
    require(plans == ["1..2", "1..6", "1..6"],
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
    config = package / "kernel.config"
    system_map = package / "System.map"
    sums = package / "SHA256SUMS"
    for path in (build_path, image, config, system_map, sums, raw_log):
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
    config_sha256 = sha256(config)
    system_map_sha256 = sha256(system_map)
    require(image_sha256 == manifest_checksum(sums, "./Image"),
            "Image checksum mismatch")
    require(config_sha256 == manifest_checksum(sums, "./kernel.config"),
            "configuration manifest checksum mismatch")
    require(system_map_sha256 == manifest_checksum(sums, "./System.map"),
            "System.map checksum mismatch")
    require(config_sha256 == build["config_sha256"],
            "configuration checksum mismatch")

    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    classify_runtime(raw, build["kernel_release"], args.qemu_exit)
    qemu_version = subprocess.run(
        ["qemu-system-aarch64", "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]
    observed_utc = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")

    print("experiment=2026-08-28-mainline-a72-admission-durable-trace")
    print("phase=kunit-qemu")
    print(f"observed_utc={observed_utc}")
    print(f"repository_commit={args.repository_commit}")
    print(f"harness_commit={args.harness_commit}")
    print(f"profile={PROFILE}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"image_sha256={image_sha256}")
    print(f"config_sha256={config_sha256}")
    print(f"system_map_sha256={system_map_sha256}")
    print(f"raw_log_sha256={sha256(raw_log)}")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt-cortex-a53-four-vcpu-single-thread-no-network")
    print("suites=2")
    print("tests=12")
    print("failed=0")
    print("skipped=0")
    for suite, cases in SUITES:
        print(f"suite_{suite}=pass-{len(cases)}-of-{len(cases)}")
        for case in cases:
            print(f"{case}=pass")
    print("tap_summary=pass:12_fail:0_skip:0_total:12")
    print("post_test_state=expected_vm_rootfs_panic")
    print("qemu_exit=124")
    print("result=pass")
    print("physical_dt_match=false")
    print("physical_cpu_requests=0")
    print("cpu_off_requests=0")
    print("retries=0")
    print("network=false")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
