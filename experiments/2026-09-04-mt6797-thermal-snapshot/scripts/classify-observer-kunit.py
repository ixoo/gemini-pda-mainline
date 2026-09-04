#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Classify the focused MT6797 thermal snapshot KUnit runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


PROFILE = "mt6797-thermal-observer-kunit"
SUITE = "mt6797-thermal-snapshot"
EXPECTED_CASES = (
    "mt6797_observer_budget_test",
    "mt6797_observer_failure_test",
    "mt6797_observer_invalid_test",
    "mt6797_snapshot_complete_test",
    "mt6797_snapshot_tie_test",
    "mt6797_snapshot_budget_test",
    "mt6797_snapshot_order_test",
    "mt6797_snapshot_invalid_test",
    "mt6797_snapshot_aggregate_time_test",
    "mt6797_snapshot_lifecycle_test",
)


class ClassificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ClassificationError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_lines(raw: str) -> list[str]:
    lines = []
    for line in raw.replace("\r", "").splitlines():
        lines.append(re.sub(r"^\[\s*\d+\.\d+\]\s*", "", line).strip())
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--raw-log", type=Path, required=True)
    parser.add_argument("--qemu-exit", type=int, required=True)
    parser.add_argument("--repository-commit", required=True)
    args = parser.parse_args()
    package = args.package.resolve()
    raw_log = args.raw_log.resolve()
    build = json.loads((package / "provenance/build.json").read_text())
    require(
        build["repository_commit"] == args.repository_commit,
        "package repository commit mismatch",
    )
    require(build["repository_dirty"] is False, "package source was dirty")
    require(build["build_profile"] == PROFILE, "package profile mismatch")
    require(build["target_architecture"] == "arm64", "architecture mismatch")
    require(args.qemu_exit == 124, "QEMU did not end at bounded timeout")
    raw = raw_log.read_text(encoding="utf-8", errors="replace")
    require(
        re.findall(r"Linux version ([^ ]+)", raw) == [build["kernel_release"]],
        "kernel release mismatch",
    )
    lines = clean_lines(raw)
    require(lines.count("KTAP version 1") == 2, "KTAP headers changed")
    require(lines.count(f"# Subtest: {SUITE}") == 1, "focused suite absent")
    require(
        not any(line.startswith("not ok ") for line in lines),
        "KTAP contains a failure",
    )
    observed = []
    for line in lines:
        match = re.fullmatch(r"ok (\d+) ([A-Za-z0-9_]+)", line)
        if match and match.group(2) != SUITE:
            observed.append((int(match.group(1)), match.group(2)))
    require(
        observed == list(enumerate(EXPECTED_CASES, start=1)),
        f"case inventory changed: {observed}",
    )
    require(
        lines.count(f"# {SUITE}: pass:7 fail:0 skip:0 total:7") == 1,
        "suite totals changed",
    )
    require(
        lines.count("# Totals: pass:7 fail:0 skip:0 total:7") == 1,
        "global totals changed",
    )
    require(lines.count(f"ok 1 {SUITE}") == 1, "suite result absent")
    require(
        any(
            line.startswith("Kernel panic - not syncing: VFS: Unable to mount root fs")
            for line in lines
        ),
        "post-test rootfs panic boundary absent",
    )
    result = {
        "classification": "exact_focused_kunit_pass",
        "repository_commit": args.repository_commit,
        "build_profile": PROFILE,
        "kernel_release": build["kernel_release"],
        "config_sha256": build["config_sha256"],
        "image_sha256": sha256(package / "Image"),
        "raw_log_sha256": sha256(raw_log),
        "suite": SUITE,
        "cases_passed": len(EXPECTED_CASES),
        "hardware_action": "none",
        "device_action": "none",
        "boot_candidate": False,
        "observed_utc": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
    }
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
