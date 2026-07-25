#!/usr/bin/env python3
"""Validate Candidate U's inactive source DTB and exact polling transform."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import shutil
import subprocess
import sys
import tempfile


P_DTB_SHA256 = "c574762aa178cb5a7238400b499d2edcdd3acb3538d2255e916b041f2074c379"
U_PACKAGE_DTB_SHA256 = "f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5"
U_FINAL_DTB_SHA256 = "e541c9dffac15de859a876e80409eec4591d36319646845cb25c6eecb8ddf5b1"
I2C5 = "/i2c@1101c000"
AW = "/i2c@1101c000/gpio-expander@5b"
MATRIX = "/keyboard-matrix"
PINS_IRQ = "/pinctrl@10005000/keyboard-soc-pins/pins-irq"
NODES = (I2C5, AW, MATRIX)
REMOVED_AW_PROPERTIES = (
    "interrupt-parent",
    "interrupts",
    "interrupt-controller",
    "#interrupt-cells",
)


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


def absent(path: pathlib.Path, node: str, prop: str) -> bool:
    result = subprocess.run(
        ["fdtget", str(path), node, prop], text=True, capture_output=True
    )
    return result.returncode != 0


def require_hash(path: pathlib.Path, expected: str, label: str) -> None:
    actual = digest(path)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: {actual}")


def put(path: pathlib.Path, node: str, prop: str, *values: str, kind: str) -> None:
    subprocess.run(
        ["fdtput", "-t", kind, str(path), node, prop, *values], check=True
    )


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
        require_hash(package, U_PACKAGE_DTB_SHA256, "U package DTB")
        require_hash(candidate, U_FINAL_DTB_SHA256, "U final DTB")
        for node in NODES:
            if fdtget(baseline, node, "status", "s") != ["disabled"]:
                raise ValueError(f"P node was not disabled: {node}")
            if fdtget(package, node, "status", "s") != ["disabled"]:
                raise ValueError(f"U source node was not disabled: {node}")
            if fdtget(candidate, node, "status", "s") != ["okay"]:
                raise ValueError(f"U final node was not enabled: {node}")
        if fdtget(package, AW, "interrupts") != ["a", "8"]:
            raise ValueError("inactive source is not raw EINT10 level-low")
        for prop in REMOVED_AW_PROPERTIES:
            fdtget(package, AW, prop)
            if not absent(candidate, AW, prop):
                raise ValueError(f"polling DTB retained AW IRQ property: {prop}")
        if fdtget(candidate, AW, "compatible", "s") != ["awinic,aw9523-pinctrl"]:
            raise ValueError("AW9523 compatible mismatch")
        phandle = fdtget(candidate, AW, "phandle")
        ranges = fdtget(candidate, AW, "gpio-ranges")
        if len(phandle) != 1 or ranges != [phandle[0], "0", "0", "10"]:
            raise ValueError("gpio-ranges is not the AW9523 self mapping")
        reset = fdtget(candidate, AW, "reset-gpios")
        if len(reset) != 3 or reset[1:] != ["3a", "0"]:
            raise ValueError("reset-gpios is not GPIO58 active-high")
        if fdtget(candidate, I2C5, "clock-frequency", "u") != ["400000"]:
            raise ValueError("I2C5 clock is not 400 kHz")
        timings = {
            "poll-interval": "20",
            "col-scan-delay-us": "2",
        }
        for prop, expected in timings.items():
            if fdtget(candidate, MATRIX, prop, "u") != [expected]:
                raise ValueError(f"matrix timing mismatch: {prop}")
        if not absent(candidate, MATRIX, "debounce-delay-ms"):
            raise ValueError("polling DTB retained inert debounce-delay-ms")
        for prop in ("gpio-activelow", "drive-inactive-cols"):
            fdtget(candidate, MATRIX, prop)
        if fdtget(package, PINS_IRQ, "pinmux") != fdtget(candidate, PINS_IRQ, "pinmux"):
            raise ValueError("GPIO87/EINT10 pinmux did not remain unchanged")
        with tempfile.TemporaryDirectory() as directory:
            transformed = pathlib.Path(directory) / "expected.dtb"
            shutil.copyfile(package, transformed)
            for node in NODES:
                put(transformed, node, "status", "okay", kind="s")
            for prop in REMOVED_AW_PROPERTIES:
                subprocess.run(
                    ["fdtput", "-d", str(transformed), AW, prop], check=True
                )
            put(transformed, I2C5, "clock-frequency", "400000", kind="i")
            for prop, value in timings.items():
                put(transformed, MATRIX, prop, value, kind="i")
            if transformed.read_bytes() != candidate.read_bytes():
                raise ValueError("final DTB contains changes beyond the exact U transform")
        print("validation=candidate-u-dtb-delta")
        print(f"baseline_dtb_sha256={P_DTB_SHA256}")
        print(f"package_dtb_sha256={U_PACKAGE_DTB_SHA256}")
        print(f"candidate_dtb_sha256={U_FINAL_DTB_SHA256}")
        print("inactive_irq=raw-eint10-level-low")
        print("active_irq_contract=absent")
        print("gpio87_pinmux=retained")
        print("poll_interval_ms=20")
        print("polling_debounce=none")
        print("col_scan_delay_us=2")
        print("i2c5_hz=400000")
        print("final_delta=exact-polling-transform")
        print("hardware_write=none")
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
