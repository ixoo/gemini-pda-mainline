#!/usr/bin/env python3
"""Validate Candidate Q's corrected source DTB and status-only final DTB."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile


P_DTB_SHA256 = "c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379"
Q_PACKAGE_DTB_SHA256 = "823598e906ac64b34782eb8b6a7203b1c72e6df4fe24c4ab649a67ea956dc0ce"
Q_FINAL_DTB_SHA256 = "9bb2f6e4feaa0b66e3d11bb35d175487d37b73891165df95f6c81498ac19078b"
NODES = (
    "/i2c@1101c000",
    "/i2c@1101c000/gpio-expander@5b",
    "/keyboard-matrix",
)
AW = NODES[1]


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fdtget(path: pathlib.Path, node: str, prop: str, kind: str = "x") -> list[str]:
    result = subprocess.run(
        ["fdtget", "-t", kind, str(path), node, prop],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.strip().split()


def require_hash(path: pathlib.Path, expected: str, label: str) -> None:
    actual = digest(path)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: {actual}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline = args.baseline.resolve(strict=True)
        package = args.package.resolve(strict=True)
        candidate = args.candidate.resolve(strict=True)
        for tool in ("fdtget", "fdtput"):
            if shutil.which(tool) is None:
                raise ValueError(f"required tool missing: {tool}")
        require_hash(baseline, P_DTB_SHA256, "Candidate P DTB")
        require_hash(package, Q_PACKAGE_DTB_SHA256, "Q package DTB")
        require_hash(candidate, Q_FINAL_DTB_SHA256, "Q final DTB")
        for node in NODES:
            if fdtget(baseline, node, "status", "s") != ["disabled"]:
                raise ValueError(f"P node was not disabled: {node}")
            if fdtget(package, node, "status", "s") != ["disabled"]:
                raise ValueError(f"Q source node was not disabled: {node}")
            if fdtget(candidate, node, "status", "s") != ["okay"]:
                raise ValueError(f"Q final node was not enabled: {node}")
        if fdtget(candidate, AW, "compatible", "s") != ["awinic,aw9523-pinctrl"]:
            raise ValueError("AW9523 compatible mismatch")
        phandle = fdtget(candidate, AW, "phandle")
        ranges = fdtget(candidate, AW, "gpio-ranges")
        if len(phandle) != 1 or ranges != [phandle[0], "0", "0", "10"]:
            raise ValueError("gpio-ranges is not the AW9523 self mapping")
        reset = fdtget(candidate, AW, "reset-gpios")
        parent = fdtget(candidate, AW, "interrupt-parent")
        interrupts = fdtget(candidate, AW, "interrupts")
        if len(reset) != 3 or reset[1:] != ["3a", "0"]:
            raise ValueError("reset-gpios is not GPIO58 active-high")
        if parent != [reset[0]]:
            raise ValueError("reset and interrupt parents differ")
        if interrupts != ["57", "8"]:
            raise ValueError("interrupt is not GPIO87 level-low")
        if not fdtget(candidate, NODES[0], "pinctrl-0"):
            raise ValueError("I2C5 pinctrl-0 is absent")
        if not fdtget(candidate, AW, "pinctrl-0"):
            raise ValueError("AW9523 SoC pinctrl-0 is absent")
        with tempfile.TemporaryDirectory() as directory:
            transformed = pathlib.Path(directory) / "expected.dtb"
            shutil.copyfile(package, transformed)
            for node in NODES:
                subprocess.run(
                    ["fdtput", "-t", "s", str(transformed), node, "status", "okay"],
                    check=True,
                )
            if transformed.read_bytes() != candidate.read_bytes():
                raise ValueError("final DTB contains changes beyond three status properties")
        print("validation=candidate-q-dtb-delta")
        print(f"baseline_dtb_sha256={P_DTB_SHA256}")
        print(f"package_dtb_sha256={Q_PACKAGE_DTB_SHA256}")
        print(f"candidate_dtb_sha256={Q_FINAL_DTB_SHA256}")
        print("gpio_ranges=aw9523-self-0-0-16")
        print("reset_gpio=58-active-high")
        print("interrupt_gpio=87-level-low")
        print("final_delta=three-status-properties-only")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
