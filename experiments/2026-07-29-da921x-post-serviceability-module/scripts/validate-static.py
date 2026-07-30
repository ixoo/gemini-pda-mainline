#!/usr/bin/env python3
"""Validate the post-serviceability DA921x module profile."""

from __future__ import annotations

import json
import pathlib
import sys


PROFILE = "da921x-post-serviceability-module"
FRAGMENT = "configs/gemini-da921x-post-serviceability-module.fragment"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> int:
    repository = pathlib.Path(__file__).resolve().parents[3]
    try:
        manifest = json.loads(
            (repository / "kernel/manifest.json").read_text(encoding="utf-8")
        )
        profile = manifest["config"]["profiles"][PROFILE]
        fragment = (repository / FRAGMENT).read_text(encoding="utf-8")
        expected_tail = [
            "configs/gemini-da921x-legacy-bind.fragment",
            "configs/gemini-da921x-legacy-lifecycle.fragment",
            FRAGMENT,
        ]
        require(
            profile["fragments"][-3:] == expected_tail,
            "module profile does not extend the exact Gate 3 fragment stack",
        )
        require("patch_series" not in profile, "profile bypasses canonical series")
        for token in (
            "CONFIG_MODULES=y",
            "CONFIG_REGULATOR_DA9213_LEGACY=m",
            'CONFIG_LOCALVERSION="-gemini-da921x-mod"',
            "Gemini-L-DA921x-Module",
            "maxcpus=8",
            "initcall_blacklist=mt6797_a72_power_driver_init",
        ):
            require(token in fragment, f"module fragment missing {token}")
        for token in (
            "CONFIG_REGULATOR_DA9213_LEGACY=y",
            "CONFIG_MTK_MT6797_A72_POWER=y",
            "modprobe",
            "insmod",
        ):
            require(token not in fragment, f"module fragment gained {token}")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=da921x-post-serviceability-module-static")
    print(f"profile={PROFILE}")
    print("driver_linkage=module")
    print("automatic_module_load=absent")
    print("provider=absent")
    print("a72_request=absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
