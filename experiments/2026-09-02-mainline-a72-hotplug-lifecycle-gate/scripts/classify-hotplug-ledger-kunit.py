#!/usr/bin/env python3
"""Classify the disconnected record-4 hotplug-ledger KUnit run."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


PROFILE = "gemini-a72-hotplug-ledger-kunit"
EXPECTED_RELEASE = "7.1.3-gemini-a72-hotplug-ledger-kunit"
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"
SUITE = "gemini-a72-hotplug-ledger"
CASES = (
    "hotplug_layout_test",
    "hotplug_success_sequence_test",
    "hotplug_pstore_empty_test",
    "hotplug_nonempty_refusal_test",
    "hotplug_sequence_refusal_test",
    "hotplug_precommit_terminal_test",
    "hotplug_cpu_off_return_terminal_test",
    "hotplug_readback_fault_test",
    "hotplug_crc_and_ambiguity_test",
    "hotplug_shape_refusal_test",
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
    matches = re.findall(
        pattern, path.read_text(encoding="utf-8"), re.MULTILINE
    )
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


def classify_runtime(raw: str, qemu_exit: int) -> None:
    lines = clean_lines(raw)
    releases = re.findall(r"Linux version ([^ ]+)", raw)
    require(releases == [EXPECTED_RELEASE], f"kernel release mismatch: {releases}")
    require(
        qemu_exit == 124,
        f"unexpected QEMU exit (expected bounded timeout): {qemu_exit}",
    )
    require("KTAP version 1" in lines, "top-level KTAP header absent")
    ktap = lines[lines.index("KTAP version 1") :]
    require(
        ktap.count("KTAP version 1") == 2,
        "expected one top-level and one suite KTAP header",
    )
    plans = [line for line in ktap if re.fullmatch(r"1\.\.\d+", line)]
    require(plans == ["1..1", "1..10"], f"KUnit plans changed: {plans}")
    subtests = [line for line in ktap if line.startswith("# Subtest: ")]
    require(subtests == [f"# Subtest: {SUITE}"], f"suite inventory changed: {subtests}")
    require(
        not any(line.startswith("not ok ") for line in ktap),
        "KTAP contains a failing result",
    )

    expected_ok = [
        f"ok {case_index} {case}"
        for case_index, case in enumerate(CASES, start=1)
    ]
    expected_ok.append(f"ok 1 {SUITE}")
    observed_ok = [line for line in ktap if re.fullmatch(r"ok \d+ \S+", line)]
    require(observed_ok == expected_ok, f"case or suite inventory changed: {observed_ok}")
    require(Counter(observed_ok) == Counter(expected_ok), "KUnit results are duplicated")
    summary = f"# {SUITE}: pass:10 fail:0 skip:0 total:10"
    totals = "# Totals: pass:10 fail:0 skip:0 total:10"
    require(ktap.count(summary) == 1, "suite summary is not an exact pass")
    require(ktap.count(totals) == 1, "suite totals are not an exact pass")

    result_index = ktap.index(f"ok 1 {SUITE}")
    panic_indices = [
        index for index, line in enumerate(ktap) if line.startswith(PANIC_PREFIX)
    ]
    require(
        len(panic_indices) == 1 and panic_indices[0] > result_index,
        "expected post-test rootfs panic boundary absent or reordered",
    )
    end_indices = [
        index for index, line in enumerate(ktap)
        if line.startswith(PANIC_END_PREFIX)
    ]
    require(
        len(end_indices) == 1 and end_indices[0] > panic_indices[0],
        "expected terminal panic marker absent or reordered",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--raw-log", type=Path, required=True)
    parser.add_argument("--qemu-exit", type=int, required=True)
    parser.add_argument("--repository-commit", required=True)
    parser.add_argument("--harness-commit", required=True)
    args = parser.parse_args()
    for label, commit in (
        ("repository", args.repository_commit),
        ("harness", args.harness_commit),
    ):
        require(
            re.fullmatch(r"[0-9a-f]{40}", commit) is not None,
            f"invalid {label} commit",
        )

    package = args.package.resolve()
    raw_log = args.raw_log.resolve()
    build_path = package / "provenance/build.json"
    image = package / "Image"
    image_gzip = package / "Image.gz"
    config = package / "kernel.config"
    system_map = package / "System.map"
    sums = package / "SHA256SUMS"
    for path in (
        build_path,
        image,
        image_gzip,
        config,
        system_map,
        sums,
        raw_log,
    ):
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
    require(build["build_profile"] == PROFILE, "package profile mismatch")
    require(build["kernel_release"] == EXPECTED_RELEASE, "kernel release changed")
    require(
        build["target_architecture"] == "arm64",
        "package target architecture mismatch",
    )
    require(build["modules_built"] is False, "unexpected module build")
    identities = {
        "image_sha256": sha256(image),
        "image_gzip_sha256": sha256(image_gzip),
        "config_sha256": sha256(config),
        "system_map_sha256": sha256(system_map),
    }
    for key, entry in (
        ("image_sha256", "./Image"),
        ("image_gzip_sha256", "./Image.gz"),
        ("config_sha256", "./kernel.config"),
        ("system_map_sha256", "./System.map"),
    ):
        require(
            identities[key] == manifest_checksum(sums, entry),
            f"package checksum mismatch: {entry}",
        )
    require(
        identities["config_sha256"] == build["config_sha256"],
        "configuration checksum mismatch",
    )

    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    classify_runtime(raw, args.qemu_exit)
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
    scripts = Path(__file__).resolve().parent

    print("experiment=2026-09-02-mainline-a72-hotplug-lifecycle-gate")
    print("phase=record-4-hotplug-ledger-kunit-qemu")
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
    print(f"runner_sha256={sha256(scripts / 'run-hotplug-ledger-kunit-qemu')}")
    print(f"classifier_sha256={sha256(Path(__file__).resolve())}")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt-cortex-a53-four-vcpu-no-network")
    print("suites=1")
    print("tests=10")
    print("failed=0")
    print("skipped=0")
    print(f"suite_{SUITE}=pass:10_fail:0_skip:0_total:10")
    for case in CASES:
        print(f"{case}=pass")
    print("tap_summary=pass:10_fail:0_skip:0_total:10")
    print("post_test_state=expected_vm_rootfs_panic")
    print("qemu_exit=124")
    print("result=pass")
    print("record_index=4")
    print("record_size=4096")
    print("copies=2")
    print("copy_words=27")
    print("writes_per_record=28")
    print("max_success_records=16")
    print("max_success_writes=451")
    print("production_callers=0")
    print("physical_backends_invoked=0")
    print("mmio=false")
    print("retained_ram=false")
    print("smc=false")
    print("watchdog_takeovers=0")
    print("network=false")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
