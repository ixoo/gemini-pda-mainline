#!/usr/bin/env python3
"""Validate the generated provider-readiness format-patch set."""

from __future__ import annotations

import argparse
from pathlib import Path


PATCHES = (
    "0371-soc-mediatek-defer-A72-platform-provider-until-provider-ready.patch",
    "0372-dt-bindings-soc-mediatek-require-A72-snapshot-provider.patch",
    "0373-soc-mediatek-test-A72-platform-provider-readiness.patch",
)

EXPECTED_PATHS = {
    PATCHES[0]: {
        "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer.c",
        "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer-internal.h",
    },
    PATCHES[1]: {
        "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-platform-provider-snapshot-observer.yaml",
    },
    PATCHES[2]: {
        "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer-test.c",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def changed_paths(text: str) -> set[str]:
    paths: set[str] = set()
    for line in text.splitlines():
        if not line.startswith("diff --git a/"):
            continue
        left, right = line[len("diff --git ") :].split(" b/", 1)
        require(left.startswith("a/"), "malformed diff left path")
        require(left[2:] == right, "rename or path mismatch is prohibited")
        paths.add(right)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    series = (patch_dir / "series").read_text(encoding="utf-8").splitlines()
    require(tuple(series) == PATCHES, "exact three-patch order")
    require(tuple(sorted(path.name for path in patch_dir.glob("*.patch"))) == PATCHES,
            "exact patch inventory")

    for patch in PATCHES:
        text = (patch_dir / patch).read_text(encoding="utf-8")
        require(text.startswith("From "), f"format-patch header: {patch}")
        require(
            "From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
            in text,
            f"synthetic experiment author: {patch}",
        )
        require("Signed-off-by:" not in text, f"synthetic sign-off absent: {patch}")
        require(changed_paths(text) == EXPECTED_PATHS[patch],
                f"exact changed-file boundary: {patch}")
        for forbidden in (
            "cpu_up(",
            "cpu_down(",
            "arm_smccc_smc(",
            "regmap_write(",
            "mt6797_dvfsp_clock_backend_read(",
            "mt6797_bigidvfs_backend_read(",
            "mt6797_a72_provider_acquire(",
            "mt6797_a72_provider_release(",
        ):
            require(forbidden not in text, f"forbidden token {forbidden}: {patch}")

    dependency = (patch_dir / PATCHES[0]).read_text(encoding="utf-8")
    added = "\n".join(
        line[1:]
        for line in dependency.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    require(dependency.count("of_find_i2c_device_by_node(") == 1,
            "one provider lookup")
    require("mt6797_a72_provider_snapshot(" not in added,
            "no new provider read call")
    require("provider_ready_gate=passed" in dependency, "terminal readiness token")
    tests = (patch_dir / PATCHES[2]).read_text(encoding="utf-8")
    require("KUNIT_CASE(mt6797_platform_provider_not_ready_test)" in tests,
            "not-ready KUnit case")
    print("patch_validation=pass")


if __name__ == "__main__":
    main()
