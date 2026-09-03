#!/usr/bin/env python3
"""Validate the profile-scoped physical-hotplug configuration identity repair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
PATCH = ROOT / "patches/v7.1.3/0503-arm64-bind-Gemini-physical-hotplug-configuration.patch"
SERIES = ROOT / "patches/series"
MANIFEST = ROOT / "kernel/manifest.json"
FRAGMENT = ROOT / "configs/gemini-a72-hotplug-physical-candidate.fragment"
PROFILE = "gemini-a72-hotplug-physical-candidate"
TARGET = "2e50cc09d2241006d819eeb0ed4151fbc6ed927e9e51b41e27c2dd7ce3cedd39"
PREDECESSOR = "c10a21881871dd9aad61f259d660a62fc24f989cb165bb61dc53af45438fe898"
WORDS = tuple(TARGET[index:index + 16] for index in range(0, 64, 16))
PREDECESSOR_WORDS = tuple(PREDECESSOR[index:index + 16] for index in range(0, 64, 16))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_patch_text(text: str) -> None:
    require(text.count("Subject: [PATCH] arm64: bind Gemini physical hotplug configuration") == 1,
            "patch subject changed")
    require(text.count("#if IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING)") == 1,
            "physical-profile condition changed")
    for word in WORDS:
        require(text.count(f"0x{word}") == 1, f"target identity word changed: {word}")
    for word in PREDECESSOR_WORDS:
        require(text.count(f"0x{word}") == 1,
                f"predecessor identity was not preserved: {word}")
    added = [
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    require(added == [
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING)",
        "static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {",
        f"\t0x{WORDS[0]}, 0x{WORDS[1]},",
        f"\t0x{WORDS[2]}, 0x{WORDS[3]},",
        "};",
        "#else",
        "#endif",
    ], "patch changes more than the profile-scoped identity branch")


def validate_repository(record_path: Path) -> None:
    record = json.loads(record_path.read_text(encoding="utf-8"))
    require(record.get("digests", {}).get("config-inputs-sha256") == TARGET,
            "package config-input identity changed")
    require(record.get("profile_id") == "mt6797-a53-a72-a41-v7",
            "package A41 profile changed")
    validate_patch_text(PATCH.read_text(encoding="utf-8"))

    series = [line for line in SERIES.read_text(encoding="utf-8").splitlines()
              if line and not line.startswith("#")]
    require(series[-2:] == [
        "v7.1.3/0503-arm64-bind-Gemini-physical-hotplug-configuration.patch",
        "v7.1.3/0504-soc-mediatek-record-CPU9-readback-mismatch-bitmap.patch",
    ], "identity repair and readback diagnostic are not the canonical series tip")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    profile = manifest["config"]["profiles"][PROFILE]
    require(profile["patch_series"] == "patches/series",
            "physical profile does not use canonical series")
    require(profile["fragments"][-2:] == [
        "configs/gemini-cpu9-progress-candidate.fragment",
        "configs/gemini-a72-hotplug-physical-candidate.fragment",
    ], "physical profile fragment tail changed")

    fragment = FRAGMENT.read_text(encoding="utf-8")
    require(fragment.count("CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING=y") == 1,
            "physical binding selection changed")
    require("CONFIG_LOCALVERSION=\"-gemini-a72-hotplug-physical\"" in fragment,
            "physical release identity changed")


def encoded_identity(identity: str) -> bytes:
    return b"".join(struct.pack("<Q", int(identity[index:index + 16], 16))
                    for index in range(0, 64, 16))


def validate_image(image_path: Path) -> None:
    image = image_path.read_bytes()
    require(image.count(encoded_identity(TARGET)) == 1,
            "built Image does not contain exactly one physical identity")
    require(image.count(encoded_identity(PREDECESSOR)) == 0,
            "built Image still contains the predecessor progress identity")
    controller = "cda6d936e61122d825a7fe7649f1b69b86455d6034f36a6cd562ff457bccd3d1"
    require(image.count(encoded_identity(controller)) == 0,
            "built Image contains the earlier controller identity")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a41-record", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    args = parser.parse_args()
    validate_repository(args.a41_record)
    validate_image(args.image)
    print("validation=physical-hotplug-config-identity-repair")
    print(f"config_inputs_sha256={TARGET}")
    print("scope=CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING-only")
    print("predecessor_production_identity=preserved")
    print("image_physical_identity_count=1")
    print("image_predecessor_identity_count=0")
    print("image_controller_identity_count=0")
    print(f"patch_sha256={hashlib.sha256(PATCH.read_bytes()).hexdigest()}")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
