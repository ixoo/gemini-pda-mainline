#!/usr/bin/env python3
"""Validate the exact post-ramoops checkpoint profile and patch."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_NAME = "v7.1.3/0279-pstore-add-Gemini-post-ramoops-checkpoint.patch"
PATCH_PATH = ROOT / "patches" / PATCH_NAME
FRAGMENT_PATH = ROOT / "configs/gemini-post-ramoops-checkpoint.fragment"
MANIFEST_PATH = ROOT / "kernel/manifest.json"
SERIES_PATH = ROOT / "patches/series"
PARENT = "da921x-resource-only-provider-modules-control"
PROFILE = "da921x-modules-post-ramoops-checkpoint"
FRAGMENT = "configs/gemini-post-ramoops-checkpoint.fragment"
MARKER = "GEMINI_MAINLINE_POST_RAMOOPS_20260815_A"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_inputs(
    manifest: dict[str, object], series: str, patch: str, fragment: str
) -> None:
    profiles = manifest["config"]["profiles"]  # type: ignore[index]
    parent = profiles[PARENT]  # type: ignore[index]
    profile = profiles[PROFILE]  # type: ignore[index]
    require(profile["base"] == parent["base"] == "defconfig", "base drift")
    require(
        profile["fragments"] == [*parent["fragments"], FRAGMENT],
        "profile is not the exact parent plus one final fragment",
    )

    lines = [line for line in series.splitlines() if line and not line.startswith("#")]
    require(lines[-1] == PATCH_NAME, "checkpoint patch is not final in canonical series")
    require(lines.count(PATCH_NAME) == 1, "checkpoint patch series identity is not unique")

    semantic = [
        line for line in fragment.splitlines()
        if line and not line.startswith("#")
    ]
    require(
        semantic
        == [
            "CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT=y",
            'CONFIG_LOCALVERSION="-gemini-postram-a"',
        ],
        "fragment gained unrelated policy",
    )

    require(patch.count(MARKER) == 1, "marker is not unique")
    require(patch.count("config PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT") == 1, "Kconfig gate drift")
    require("depends on PSTORE_RAM=y" in patch, "built-in ramoops dependency missing")
    require("depends on PSTORE_CONSOLE && ARM64 && ARCH_MEDIATEK" in patch, "platform dependency drift")
    require("default n" in patch, "checkpoint is not default-off")
    require(patch.count("#ifdef CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT") == 1, "source gate drift")
    require(patch.count("PSTORE_FLAGS_CONSOLE") == 1, "console runtime guard drift")
    require(
        patch.index("err = pstore_register(&cxt->pstore);") < patch.index(MARKER),
        "marker moved before pstore registration",
    )
    for field in (
        "checkpoint=ramoops-registered",
        "pstore_console=active",
        "storage_access=none",
        "regulator_reads=none",
        "regulator_writes=none",
        "cpu8_cpu9_admission=closed",
    ):
        require(patch.count(field) == 1, f"marker field drift: {field}")
    for forbidden in (
        "i2c_transfer(",
        "regulator_set_",
        "regmap_write(",
        "emergency_restart(",
        "kernel_restart(",
        "schedule_delayed_work(",
        "cpu_up(",
        "cpu_down(",
        "Signed-off-by:",
    ):
        require(forbidden not in patch, f"forbidden operation present: {forbidden}")
    require("non-certifying author identity" in patch, "synthetic author status missing")
    require("submission-ready." in patch, "experiment-only status missing")


def main() -> None:
    validate_inputs(
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
        SERIES_PATH.read_text(encoding="utf-8"),
        PATCH_PATH.read_text(encoding="utf-8"),
        FRAGMENT_PATH.read_text(encoding="utf-8"),
    )
    print("validation=mainline-post-ramoops-checkpoint-static")
    print(f"parent_profile={PARENT}")
    print("profile_delta=one-final-fragment")
    print("ramoops_checkpoint=after-successful-pstore-registration")
    print("da921x_device_initcall=later")
    print("hardware_write=none")
    print("cpu8_cpu9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
