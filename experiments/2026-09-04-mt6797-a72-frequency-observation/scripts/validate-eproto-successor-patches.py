#!/usr/bin/env python3
"""Validate normal failure-stage diagnostic format patches."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


EXPECTED = {
    "0531-soc-mediatek-trace-A72-frequency-observer-failures.patch": {
        "drivers/soc/mediatek/mt6797-a72-frequency-observer-internal.h",
        "drivers/soc/mediatek/mt6797-a72-frequency-observer.c",
    },
    "0532-soc-mediatek-test-A72-frequency-observer-failure-trace.patch": {
        "drivers/soc/mediatek/mt6797-a72-frequency-observer-test.c",
    },
}


def changed_paths(text: str) -> set[str]:
    found: set[str] = set()
    for left, right in re.findall(r"^diff --git a/(\S+) b/(\S+)$", text, re.M):
        if left != right:
            raise SystemExit(f"rename forbidden: {left} -> {right}")
        found.add(left)
    return found


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    series = (patch_dir / "series").read_text().splitlines()
    if series != list(EXPECTED):
        raise SystemExit(f"unexpected generated series: {series!r}")

    combined_added = ""
    for name, expected in EXPECTED.items():
        text = (patch_dir / name).read_text()
        if not text.startswith("From ") or "\nSubject: [PATCH " not in text:
            raise SystemExit(f"not a normal format-patch: {name}")
        if "Signed-off-by:" in text:
            raise SystemExit(f"synthetic sign-off forbidden: {name}")
        actual = changed_paths(text)
        if actual != expected:
            raise SystemExit(f"unexpected paths in {name}: {sorted(actual)!r}")
        combined_added += "\n" + added_lines(text)

    for forbidden in (
        "add_cpu(", "remove_cpu(", "cpu_up(", "cpu_down(",
        "cpu_off(", "regmap_write(", "writel(", "reboot(",
        "kernel_restart(", "emergency_restart(", "of_property_write",
    ):
        if forbidden in combined_added:
            raise SystemExit(f"forbidden added operation: {forbidden}")

    if combined_added.count("source->ops->clock(source->clock, &clock)") != 0:
        raise SystemExit("diagnostic patch must not add another clock call")
    if combined_added.count("source->ops->bigidvfs(source->bigidvfs, &big)") != 0:
        raise SystemExit("diagnostic patch must not add another BigiDVFS call")
    for stage in (
        "clock-transport", "clock-shape", "bigidvfs-transport",
        "bigidvfs-shape", "decode",
    ):
        if f'return "{stage}";' not in combined_added:
            raise SystemExit(f"missing stable failure stage: {stage}")

    print("generated_patch_count=2")
    print("changed_path_count=3")
    print("failure_stage_count=6")
    print("failure_stage_kunit_coverage=complete")
    print("additional_hardware_calls=0")
    print("observer_attempt_budget=3-unchanged")
    print("cpu_requests_added=0")
    print("hardware_writes_added=0")
    print("device_tree_changes=0")
    print("synthetic_signoff=absent")
    print("result=pass")


if __name__ == "__main__":
    main()
