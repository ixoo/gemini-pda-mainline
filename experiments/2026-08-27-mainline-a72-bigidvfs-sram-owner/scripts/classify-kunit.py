#!/usr/bin/env python3
"""Classify the hardware-free MT6797 A72 BigiDVFS SRAM-owner suite."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROFILE = "mt6797-a72-bigidvfs-sram-kunit"
SUITE = "mt6797-bigidvfs-sram-owner"
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"
EXPECTED_CASES = (
    "mt6797_bigidvfs_sram_success_test",
    "mt6797_bigidvfs_sram_guards_test",
    "mt6797_bigidvfs_sram_one_shot_test",
    "mt6797_bigidvfs_sram_service_failure_test",
    "mt6797_bigidvfs_sram_read_failures_test",
    "mt6797_bigidvfs_sram_instability_test",
    "mt6797_bigidvfs_sram_selector_test",
    "mt6797_bigidvfs_sram_calibration_test",
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
    require(ktap.count("KTAP version 1") == 2,
            "expected exactly one top-level and one suite KTAP header")
    require(ktap.count("1..1") == 1, "top-level suite plan changed")
    require(ktap.count("1..8") == 1, "focused test plan changed")
    require(ktap.count(f"# Subtest: {SUITE}") == 1,
            "focused suite absent or duplicated")
    require(not any(line.startswith("# Subtest: ") and
                    line != f"# Subtest: {SUITE}" for line in ktap),
            "an unexpected KUnit suite executed")
    require(not any(line.startswith("not ok ") for line in ktap),
            "KTAP contains a failing result")

    observed_cases: list[tuple[int, str]] = []
    for line in ktap:
        match = re.fullmatch(r"ok (\d+) ([A-Za-z0-9_]+)", line)
        if match:
            observed_cases.append((int(match.group(1)), match.group(2)))
    require(observed_cases == list(enumerate(EXPECTED_CASES, start=1)),
            f"focused case inventory changed: {observed_cases}")

    summary = f"# {SUITE}: pass:8 fail:0 skip:0 total:8"
    totals = "# Totals: pass:8 fail:0 skip:0 total:8"
    suite_result = f"ok 1 {SUITE}"
    require(ktap.count(summary) == 1, "suite summary is not exact pass")
    require(ktap.count(totals) == 1, "global KUnit totals are not exact pass")
    require(ktap.count(suite_result) == 1, "top-level suite result absent")
    result_index = ktap.index(suite_result)
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
    args = parser.parse_args()
    require(re.fullmatch(r"[0-9a-f]{40}", args.repository_commit) is not None,
            "invalid repository commit")

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
        ["qemu-system-aarch64", "--version"], check=True,
        capture_output=True, text=True).stdout.splitlines()[0]
    observed_utc = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")

    print("experiment=2026-08-27-mainline-a72-bigidvfs-sram-owner")
    print("phase=kunit-qemu")
    print(f"observed_utc={observed_utc}")
    print(f"repository_commit={args.repository_commit}")
    print(f"profile={PROFILE}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"image_sha256={image_sha256}")
    print(f"config_sha256={config_sha256}")
    print(f"system_map_sha256={system_map_sha256}")
    print(f"raw_log_sha256={sha256(raw_log)}")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt-cortex-a53-four-vcpu-no-network")
    print("suites=1")
    print("tests=8")
    print("failed=0")
    print("skipped=0")
    for case in EXPECTED_CASES:
        print(f"{case}=pass")
    print("tap_summary=pass:8_fail:0_skip:0_total:8")
    print("post_test_state=expected_vm_rootfs_panic")
    print("qemu_exit=124")
    print("result=pass")
    print("serialized_resource_owner=bigidvfs-backend")
    print("physical_effect_calls=0")
    print("secure_calls=0")
    print("delay=false")
    print("mmio=false")
    print("watchdog=false")
    print("retained_ram=false")
    print("regulator=false")
    print("production_callers=0")
    print("physical_cpu_requests=0")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
