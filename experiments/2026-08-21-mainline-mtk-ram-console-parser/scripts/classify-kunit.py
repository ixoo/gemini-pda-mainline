#!/usr/bin/env python3
"""Classify the focused MediaTek retained-header parser KUnit/QEMU proof."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROFILE = "mtk-ram-console-parser-kunit"
SUITE = "mtk-ram-console-parser"
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"
EXPECTED_CASES = (
    "mtk_ram_console_invalid_arguments_test",
    "mtk_ram_console_truncated_test",
    "mtk_ram_console_signature_test",
    "mtk_ram_console_buffer_size_test",
    "mtk_ram_console_preloader_layout_test",
    "mtk_ram_console_lk_layout_test",
    "mtk_ram_console_exact_test",
    "mtk_ram_console_every_bit_test",
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
    require(ktap.count("KTAP version 1") == 2,
            "expected one top-level and one suite KTAP header")
    require(ktap.count("1..1") == 1, "top-level suite plan changed")
    require(ktap.count("1..8") == 1, "focused test plan changed")
    require(ktap.count(f"# Subtest: {SUITE}") == 1,
            "focused suite absent or duplicated")
    require(not any(line.startswith("# Subtest: ") and
                    line != f"# Subtest: {SUITE}" for line in ktap),
            "unexpected KUnit suite executed")
    require(not any(line.startswith("not ok ") for line in ktap),
            "KTAP contains a failing result")

    observed = []
    for line in ktap:
        match = re.fullmatch(r"ok (\d+) ([A-Za-z0-9_]+)", line)
        if match:
            observed.append((int(match.group(1)), match.group(2)))
    require(observed == list(enumerate(EXPECTED_CASES, start=1)),
            f"focused case inventory changed: {observed}")

    summary = f"# {SUITE}: pass:8 fail:0 skip:0 total:8"
    totals = "# Totals: pass:8 fail:0 skip:0 total:8"
    suite_result = f"ok 1 {SUITE}"
    require(ktap.count(summary) == 1, "suite summary is not exact pass")
    require(ktap.count(totals) == 1, "global KUnit totals are not exact pass")
    require(ktap.count(suite_result) == 1, "top-level suite result absent")
    result_index = ktap.index(suite_result)
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

    print("experiment=2026-08-21-mainline-mtk-ram-console-parser")
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
    print("physical_mapping=not-executed-parser-only")
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
    print("reset_classifier=none")
    print("a34_caller=none")
    print("hardware_write=none")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
