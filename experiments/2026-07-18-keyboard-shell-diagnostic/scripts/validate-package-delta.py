#!/usr/bin/env python3
"""Validate Candidate Q's package and its exact resolved-config delta from P."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


P_CONFIG_SHA256 = "0759fdb25abf25008ecf967736316a2d16d227c80c6835dad5875e8a612ef424"
PROFILE = "observability-fbcon-rotation-keyboard"
FRAGMENT = "configs/gemini-keyboard.fragment"
REQUIRED = {
    "CONFIG_I2C=y",
    "CONFIG_I2C_MT65XX=y",
    "CONFIG_PINCTRL_AW9523=y",
    "CONFIG_KEYBOARD_MATRIX=y",
    "CONFIG_INPUT_EVDEV=y",
    "CONFIG_REGMAP_I2C=y",
    "CONFIG_GPIOLIB_IRQCHIP=y",
    "CONFIG_EINT_MTK=y",
    "CONFIG_PINCTRL_MT6797=y",
    "CONFIG_TTY=y",
    "CONFIG_VT=y",
    "CONFIG_VT_CONSOLE=y",
    "# CONFIG_MODULES is not set",
    "# CONFIG_I2C_CHARDEV is not set",
    "# CONFIG_DEVMEM is not set",
    "# CONFIG_MMC is not set",
}
EXPECTED_NEW_ENABLED = {
    "CONFIG_I2C=y",
    "CONFIG_I2C_BOARDINFO=y",
    "CONFIG_I2C_HELPER_AUTO=y",
    "CONFIG_I2C_MUX=y",
    "CONFIG_I2C_DESIGNWARE_CORE=y",
    "CONFIG_I2C_MT65XX=y",
    "CONFIG_I3C_OR_I2C=y",
    "CONFIG_REGMAP_I2C=y",
    "CONFIG_PINCTRL_AW9523=y",
    "CONFIG_KEYBOARD_MATRIX=y",
    "CONFIG_MOUSE_PS2_SYNAPTICS_SMBUS=y",
    "CONFIG_MOUSE_PS2_SMBUS=y",
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def config_map(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("CONFIG_"):
            key = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line[2:-11]
        else:
            continue
        if key in result:
            raise ValueError(f"duplicate config symbol: {key}")
        result[key] = line
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-config", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-package", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--expected-profile", default=PROFILE)
    args = parser.parse_args()
    try:
        baseline = args.baseline_config.resolve(strict=True)
        package = args.candidate_package.resolve(strict=True)
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        candidate = package / "kernel.config"
        build_json = json.loads(
            (package / "provenance/build.json").read_text(encoding="utf-8")
        )
        if digest(baseline) != P_CONFIG_SHA256:
            raise ValueError("baseline config is not exact Candidate P")
        if build_json.get("build_profile") != args.expected_profile:
            raise ValueError("candidate build profile is not the expected profile")
        if build_json.get("modules_built") is not False:
            raise ValueError("candidate unexpectedly built modules")
        if build_json.get("config_sha256") != digest(candidate):
            raise ValueError("candidate config hash disagrees with provenance")
        profile = manifest["config"]["profiles"][args.expected_profile]
        fragments = profile["fragments"]
        parent = manifest["config"]["profiles"]["observability-fbcon-rotation"]
        if profile["base"] != parent["base"] or fragments != parent["fragments"] + [FRAGMENT]:
            raise ValueError("candidate profile is not exact P plus keyboard fragment")
        lines = set(candidate.read_text(encoding="utf-8").splitlines())
        missing = sorted(REQUIRED - lines)
        if missing:
            raise ValueError(f"required config line missing: {missing[0]}")
        cmdline = next(line for line in lines if line.startswith("CONFIG_CMDLINE="))
        p_cmdline = next(
            line for line in baseline.read_text(encoding="utf-8").splitlines()
            if line.startswith("CONFIG_CMDLINE=")
        )
        if cmdline != p_cmdline[:-1] + " consoleblank=0\"":
            raise ValueError("forced command line is not exact P plus consoleblank=0")
        before = config_map(baseline)
        after = config_map(candidate)
        enabled = {
            value for key, value in after.items()
            if value.endswith("=y") and before.get(key) != value
        }
        if enabled != EXPECTED_NEW_ENABLED:
            extra = sorted(enabled - EXPECTED_NEW_ENABLED)
            missing_enabled = sorted(EXPECTED_NEW_ENABLED - enabled)
            raise ValueError(
                f"unexpected enabled delta; extra={extra} missing={missing_enabled}"
            )
        print("validation=keyboard-candidate-package-delta")
        print(f"build_profile={args.expected_profile}")
        print(f"baseline_config_sha256={digest(baseline)}")
        print(f"candidate_config_sha256={digest(candidate)}")
        print("profile_boundary=exact-p-plus-keyboard-fragment")
        print("resolved_enabled_delta=" + ",".join(sorted(EXPECTED_NEW_ENABLED)))
        print("forced_cmdline_delta=consoleblank=0-only")
        print("modules_built=false")
        print("hardware_write=none")
        return 0
    except (OSError, KeyError, StopIteration, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
