#!/usr/bin/env python3
"""Validate the exact current-mainline module-policy control profile."""

from __future__ import annotations

import json
from pathlib import Path


PROFILE = "da921x-resource-only-provider-modules-control"
PARENT = "da921x-resource-only-provider"
FRAGMENT = "configs/gemini-da921x-provider-modules-control.fragment"
EXPECTED_SETTINGS = [
    "CONFIG_MODULES=y",
    'CONFIG_LOCALVERSION="-gemini-da921x-modctl"',
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def settings(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def validate_profile(manifest: dict, fragment_text: str) -> None:
    profiles = manifest["config"]["profiles"]
    require(PARENT in profiles and PROFILE in profiles, "required profile missing")
    parent = profiles[PARENT]
    control = profiles[PROFILE]
    require(control["base"] == parent["base"] == "defconfig", "base config drift")
    require("patch_series" not in control, "control must inherit the canonical series")
    require(
        control["fragments"] == parent["fragments"] + [FRAGMENT],
        "control must extend the exact parent with one final fragment",
    )
    require(len(control["fragments"]) == len(set(control["fragments"])), "duplicate fragment")
    require(settings(fragment_text) == EXPECTED_SETTINGS, "control settings changed")
    require(
        "configs/gemini-da921x-readonly-observer.fragment" not in control["fragments"],
        "observer leaked into control",
    )
    require(
        "configs/gemini-da921x-post-serviceability-module.fragment"
        not in control["fragments"],
        "historical command line/module fragment leaked into matched control",
    )


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    manifest = json.loads((repo / "kernel/manifest.json").read_text(encoding="utf-8"))
    fragment = (repo / FRAGMENT).read_text(encoding="utf-8")
    validate_profile(manifest, fragment)
    for path in manifest["config"]["profiles"][PROFILE]["fragments"]:
        require((repo / path).is_file(), f"missing fragment: {path}")
    provider = (repo / "configs/gemini-da921x-resource-only-provider.fragment").read_text(
        encoding="utf-8"
    )
    require("CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y" in provider, "provider missing")
    require("CONFIG_MODULES" not in provider, "provider fragment changes module policy")
    print("validation=mainline-module-policy-control-static")
    print("parent_profile=da921x-resource-only-provider")
    print("profile_delta=one-final-fragment")
    print("module_policy=CONFIG_MODULES-y")
    print("provider=read-only")
    print("observer=disabled")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
