#!/usr/bin/env python3
"""Classify the two hardware-free platform-movement KUnit suites."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess


PROFILE = "a72-platform-movement-kunit"
EXPECTED_RELEASE = "7.1.3-gemini-a72-movement-kunit"
SUITES = (
    ("mt6797-a72-platform-state-movement", (
        "mt6797_state_stable_test",
        "mt6797_state_read_errors_test",
        "mt6797_state_cci_busy_precedence_test",
        "mt6797_state_each_movement_test",
        "mt6797_state_masked_noise_test",
    )),
    ("mt6797-a72-platform-provider-clock", (
        "mt6797_a72_ppc_success_test",
        "mt6797_a72_ppc_not_ready_test",
        "mt6797_a72_ppc_platform_failure_test",
        "mt6797_a72_ppc_provider_failure_test",
        "mt6797_a72_ppc_before_failure_test",
        "mt6797_a72_ppc_clock_error_terminal_test",
        "mt6797_a72_ppc_after_failure_terminal_test",
        "mt6797_a72_ppc_clock_identity_terminal_test",
    )),
)
PANIC_PREFIX = "Kernel panic - not syncing: VFS: Unable to mount root fs"
PANIC_END_PREFIX = f"---[ end {PANIC_PREFIX}"


class ClassificationError(RuntimeError):
    """Raised when the log or package does not prove the exact contract."""


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
        path.read_text(encoding="utf-8"), re.MULTILINE,
    )
    require(len(matches) == 1, f"checksum entry absent or duplicated: {entry}")
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
    require(qemu_exit == 124, f"unexpected QEMU exit: {qemu_exit}")
    require("KTAP version 1" in lines, "top-level KTAP header absent")
    ktap = lines[lines.index("KTAP version 1"):]
    require(ktap.count("KTAP version 1") == 3,
            "expected one top-level and two suite KTAP headers")
    require(ktap.count("1..2") == 1, "top-level suite plan changed")
    require(ktap.count("1..5") == 1, "platform-state plan changed")
    require(ktap.count("1..8") == 1, "composed-observer plan changed")
    expected_subtests = {f"# Subtest: {suite}" for suite, _ in SUITES}
    observed_subtests = [line for line in ktap if line.startswith("# Subtest: ")]
    require(len(observed_subtests) == 2 and set(observed_subtests) == expected_subtests,
            f"focused suite inventory changed: {observed_subtests}")
    require(not any(line.startswith("not ok ") for line in ktap),
            "KTAP contains a failing result")

    for suite_index, (suite, cases) in enumerate(SUITES, start=1):
        for case_index, case in enumerate(cases, start=1):
            require(ktap.count(f"ok {case_index} {case}") == 1,
                    f"case absent or duplicated: {case}")
        summary = f"# {suite}: pass:{len(cases)} fail:0 skip:0 total:{len(cases)}"
        require(ktap.count(summary) == 1, f"suite summary changed: {suite}")
        require(ktap.count(f"ok {suite_index} {suite}") == 1,
                f"top-level suite result changed: {suite}")

    require(ktap.count("# Totals: pass:13 fail:0 skip:0 total:13") == 1,
            "global KUnit totals changed")
    last_result = ktap.index(f"ok 2 {SUITES[1][0]}")
    panics = [i for i, line in enumerate(ktap) if line.startswith(PANIC_PREFIX)]
    require(len(panics) == 1 and panics[0] > last_result,
            "expected post-test rootfs panic absent or reordered")
    panic_ends = [i for i, line in enumerate(ktap)
                  if line.startswith(PANIC_END_PREFIX)]
    require(len(panic_ends) == 1 and panic_ends[0] > panics[0],
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
    require(build["kernel_release"] == EXPECTED_RELEASE, "kernel release changed")
    require(build["target_architecture"] == "arm64", "architecture changed")
    require(build["modules_built"] is False, "unexpected module build")
    identities = {
        "image_sha256": sha256(image),
        "config_sha256": sha256(config),
        "system_map_sha256": sha256(system_map),
    }
    for key, entry in (("image_sha256", "./Image"),
                       ("config_sha256", "./kernel.config"),
                       ("system_map_sha256", "./System.map")):
        require(identities[key] == manifest_checksum(sums, entry),
                f"package checksum mismatch: {entry}")
    require(identities["config_sha256"] == build["config_sha256"],
            "configuration provenance mismatch")

    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    classify_runtime(raw, EXPECTED_RELEASE, args.qemu_exit)
    qemu_version = subprocess.run(
        ["qemu-system-aarch64", "--version"], check=True,
        capture_output=True, text=True).stdout.splitlines()[0]
    observed = datetime.now(timezone.utc).replace(
        microsecond=0).isoformat().replace("+00:00", "Z")

    print("experiment=2026-08-26-mainline-a72-platform-movement-attribution")
    print("phase=kunit-qemu")
    print(f"observed_utc={observed}")
    print(f"repository_commit={args.repository_commit}")
    print(f"profile={PROFILE}")
    print(f"kernel_release={EXPECTED_RELEASE}")
    for key, value in identities.items():
        print(f"{key}={value}")
    print(f"raw_log_sha256={sha256(raw_log)}")
    print(f"runner_version={qemu_version.removeprefix('QEMU emulator version ')}")
    print("machine=virt-cortex-a53-four-vcpu-no-network")
    print("suites=2")
    print("tests=13")
    print("failed=0")
    print("skipped=0")
    for _, cases in SUITES:
        for case in cases:
            print(f"{case}=pass")
    print("tap_summary=pass:13_fail:0_skip:0_total:13")
    print("post_test_state=expected_vm_rootfs_panic")
    print("qemu_exit=124")
    print("result=pass")
    print("physical_i2c=false")
    print("physical_clock_backend=false")
    print("mmio=false")
    print("retained_ram=false")
    print("smc=false")
    print("provider_transactions=0")
    print("publisher_calls=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("device_action=none")
    print("boot_candidate=false")


if __name__ == "__main__":
    main()
