#!/usr/bin/env python3
"""Exercise Candidate AG's whole-FDT allowlist with focused mutations."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile


def run(command: list[str], expect_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if (result.returncode == 0) != expect_success:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"unexpected command result ({result.returncode}): {detail}")
    return result


def mutate(path: pathlib.Path, commands: list[list[str]]) -> None:
    for arguments in commands:
        if arguments[:1] == ["-t"] and len(arguments) >= 4:
            command = ["fdtput", "-t", arguments[1], str(path), *arguments[2:]]
        elif arguments[:2] == ["-p", "-t"] and len(arguments) >= 5:
            command = ["fdtput", "-p", "-t", arguments[2], str(path), *arguments[3:]]
        elif arguments[:1] == ["-r"] and len(arguments) == 2:
            command = ["fdtput", "-r", str(path), arguments[1]]
        else:
            raise ValueError(f"unsupported mutation command: {arguments!r}")
        run(command)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--af-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--ad-dtb", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        script_dir = pathlib.Path(__file__).resolve().parent
        builder = script_dir / "build-simplefb-dtb.sh"
        validator = script_dir / "validate-dtb-delta.py"
        for command in ("bash", "fdtput", "python3"):
            if shutil.which(command) is None:
                raise ValueError(f"required command missing: {command}")
        with tempfile.TemporaryDirectory(prefix="candidate-ag-dtb-mutations-") as raw:
            work = pathlib.Path(raw)
            good = work / "good.dtb"
            run(
                [
                    "bash",
                    str(builder),
                    "--af-dtb",
                    str(args.af_dtb),
                    "--ad-dtb",
                    str(args.ad_dtb),
                    "--output",
                    str(good),
                ]
            )
            validator_command = [
                "python3",
                str(validator),
                "--af",
                str(args.af_dtb),
                "--ad",
                str(args.ad_dtb),
                "--candidate",
            ]
            run([*validator_command, str(good)])

            framebuffer = "/chosen/framebuffer@7dfb0000"
            mutations: dict[str, list[list[str]]] = {
                "width": [["-t", "x", framebuffer, "width", "439"]],
                "height": [["-t", "x", framebuffer, "height", "871"]],
                "stride": [["-t", "x", framebuffer, "stride", "1104"]],
                "format": [["-t", "s", framebuffer, "format", "x8r8g8b8"]],
                "compatible": [["-t", "s", framebuffer, "compatible", "simple-bus"]],
                "base": [["-t", "x", framebuffer, "reg", "0", "7dfa0000", "0", "1f90000"]],
                "size": [["-t", "x", framebuffer, "reg", "0", "7dfb0000", "0", "8f7000"]],
                "clock-order": [["-t", "x", framebuffer, "clocks", "6", "6", "3", "2d"]],
                "infra-clock-id": [["-t", "x", framebuffer, "clocks", "3", "2e", "6", "6"]],
                "top-clock-id": [["-t", "x", framebuffer, "clocks", "3", "2d", "6", "7"]],
                "memory-region": [["-t", "x", framebuffer, "memory-region", "3"]],
                "extra-property": [["-t", "s", framebuffer, "status", "okay"]],
                "address-cells": [["-t", "x", "/chosen", "#address-cells", "1"]],
                "size-cells": [["-t", "x", "/chosen", "#size-cells", "1"]],
                "nonempty-ranges": [["-t", "x", "/chosen", "ranges", "0"]],
                "stdout-path": [["-t", "s", "/chosen", "stdout-path", "serial0:115200"]],
                "root-extra": [["-t", "s", "/", "gemini,unexpected", "yes"]],
                "provider-compatible": [["-t", "s", "/syscon@10001000", "compatible", "syscon"]],
                "provider-phandle": [["-t", "x", "/topckgen@10000000", "phandle", "77"]],
                "duplicate-phandle": [["-t", "x", "/topckgen@10000000", "phandle", "3"]],
                "remove-framebuffer": [["-r", framebuffer]],
                "framebuffer-child": [["-p", "-t", "s", f"{framebuffer}/bad", "compatible", "simple-bus"]],
                "static-overlap": [
                    ["-p", "-t", "s", "/reserved-memory/ag-bad@7dfb0000", "compatible", "reserved-memory"],
                    ["-t", "x", "/reserved-memory/ag-bad@7dfb0000", "reg", "0", "7dfb0000", "0", "1000"],
                ],
                "static-mtk-framebuffer": [
                    ["-p", "-t", "s", "/reserved-memory/mblock-3-framebuffer", "compatible", "mediatek,framebuffer"],
                    ["-t", "x", "/reserved-memory/mblock-3-framebuffer", "reg", "0", "7dfb0000", "0", "1f90000"],
                ],
            }
            rejected = 0
            for name, commands in mutations.items():
                bad = work / f"bad-{name}.dtb"
                shutil.copyfile(good, bad)
                mutate(bad, commands)
                run([*validator_command, str(bad)], expect_success=False)
                rejected += 1

        print("validation=candidate-ag-simplefb-dtb-mutations")
        print("positive_fixture=accepted")
        print(f"mutations_rejected={rejected}-of-{len(mutations)}")
        print("device_access=none")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
