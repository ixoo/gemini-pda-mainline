#!/usr/bin/env python3
"""Classify the exact B2 KUnit suite from an isolated arm64 QEMU log."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROFILE = "i2c6-write-transport-kunit"
SUITE = "mtk-i2c-idvfs-write-contract"
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"
EXPECTED_CASES = (
    "mtk_i2c_idvfs_exact_two_byte_fifo_plan",
    "mtk_i2c_idvfs_malformed_message_refusals",
    "mtk_i2c_idvfs_exact_completion_success",
    "mtk_i2c_idvfs_timeout_classification",
    "mtk_i2c_idvfs_nack_classification",
    "mtk_i2c_idvfs_arbitration_loss_classification",
    "mtk_i2c_idvfs_unexpected_irq_refusal",
    "mtk_i2c_idvfs_no_retry_eagain",
    "mtk_i2c_idvfs_retry_restoration_success",
    "mtk_i2c_idvfs_retry_restoration_failure",
    "mtk_i2c_idvfs_lease_failure_overrides_success",
    "mtk_i2c_idvfs_transport_failure_retains_precedence",
)


class ClassificationError(RuntimeError):
    """Raised when the runtime does not prove the exact B2 contract."""


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
    require(ktap.count("1..12") == 1, "focused test plan changed")
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

    suite_summary = f"# {SUITE}: pass:12 fail:0 skip:0 total:12"
    totals = "# Totals: pass:12 fail:0 skip:0 total:12"
    suite_result = f"ok 1 {SUITE}"
    require(ktap.count(suite_summary) == 1, "suite summary is not exact pass")
    require(ktap.count(totals) == 1, "global KUnit totals are not exact pass")
    require(ktap.count(suite_result) == 1, "top-level suite result absent")
    result_index = ktap.index(suite_result)
    panic_indices = [index for index, line in enumerate(ktap)
                     if line.startswith(PANIC_PREFIX)]
    require(len(panic_indices) == 1 and panic_indices[0] > result_index,
            "expected post-test rootfs panic boundary absent or reordered")
    end_panic_indices = [index for index, line in enumerate(ktap)
                         if line.startswith(PANIC_END_PREFIX)]
    require(len(end_panic_indices) == 1 and
            end_panic_indices[0] > panic_indices[0],
            "expected terminal panic marker absent or reordered")
    require(not any("System halted" in line for line in ktap),
            "runtime termination model changed")


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
    sums = package / "SHA256SUMS"
    for path in (build_path, image, config, sums, raw_log):
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
    require(image_sha256 == manifest_checksum(sums, "./Image"),
            "Image checksum mismatch")
    require(config_sha256 == manifest_checksum(sums, "./kernel.config"),
            "configuration manifest checksum mismatch")
    require(config_sha256 == build["config_sha256"],
            "configuration checksum mismatch")

    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    classify_runtime(raw, build["kernel_release"], args.qemu_exit)
    qemu_version = subprocess.run(
        ["qemu-system-aarch64", "--version"], check=True,
        capture_output=True, text=True).stdout.splitlines()[0]
    observed_utc = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")

    print("experiment=2026-08-19-mainline-i2c6-write-transport-kunit")
    print("phase=kunit-qemu")
    print(f"observed_utc={observed_utc}")
    print(f"repository_commit={args.repository_commit}")
    print(f"profile={PROFILE}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"image_sha256={image_sha256}")
    print(f"config_sha256={config_sha256}")
    print("runner=qemu-system-aarch64")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt")
    print("cpu=cortex-a53")
    print("vcpus=4")
    print("network=none")
    print("suites=1")
    print("tests=12")
    print("failed=0")
    print("skipped=0")
    for case in EXPECTED_CASES:
        print(f"{case}=pass")
    print("tap_summary=pass:12_fail:0_skip:0_total:12")
    print("post_test_state=expected_vm_rootfs_panic")
    print("qemu_exit=124")
    print("exit_interpretation=bounded_timeout_after_complete_KTAP_pass")
    print("result=pass")
    print("hardware_write=none")
    print("device_action=none")
    print("boot_candidate=false")
    print("gate6_B2=closed")
    print("gate6_write=not-authorized")
    print("cpu8_cpu9_admission=closed")


if __name__ == "__main__":
    main()
