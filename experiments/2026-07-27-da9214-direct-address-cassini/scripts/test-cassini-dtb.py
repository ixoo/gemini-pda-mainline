#!/usr/bin/env python3
"""Reject focused mutations of Cassini's exact childless-I2C6 DT."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

I2C6 = "/i2c@1100e000"
HANDOFF = "/dvfsp-handoff@11015000"


def run(command: list[str], success: bool = True) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if (result.returncode == 0) != success:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"unexpected command result: {detail}")
    if not success and "error:" not in result.stderr:
        raise ValueError("rejection lacked a fail-closed diagnostic")


def fdtput(path: pathlib.Path, arguments: list[str]) -> None:
    if arguments[:1] == ["-t"]:
        command = ["fdtput", "-t", arguments[1], str(path), *arguments[2:]]
    elif arguments[:2] == ["-p", "-t"]:
        command = ["fdtput", "-p", "-t", arguments[2], str(path), *arguments[3:]]
    elif arguments[:1] == ["-d"]:
        command = ["fdtput", "-d", str(path), *arguments[1:]]
    else:
        raise ValueError(f"unsupported mutation {arguments!r}")
    run(command)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ao-dtb", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        scripts = pathlib.Path(__file__).resolve().parent
        builder = scripts / "build-cassini-dtb.sh"
        validator = scripts / "validate-cassini-dtb.py"
        with tempfile.TemporaryDirectory(prefix="cassini-dtb-mutations-") as raw:
            work = pathlib.Path(raw)
            good = work / "good.dtb"
            run([
                "bash", str(builder), "--ao-dtb", str(args.ao_dtb),
                "--output", str(good),
            ])
            base_command = [
                sys.executable, str(validator), "--ao", str(args.ao_dtb),
                "--candidate",
            ]
            run([*base_command, str(good)])
            mutations = {
                "i2c6-disabled": ["-t", "s", I2C6, "status", "disabled"],
                "dependency-wrong": [
                    "-t", "x", I2C6, "access-controllers", "2b"
                ],
                "dependency-missing": ["-d", I2C6, "access-controllers"],
                "handoff-cells-one": [
                    "-t", "x", HANDOFF, "#access-controller-cells", "1"
                ],
                "da9214-68": [
                    "-p", "-t", "s", I2C6 + "/regulator@68",
                    "compatible", "dlg,da9214"
                ],
                "da9214-69": [
                    "-p", "-t", "s", I2C6 + "/regulator@69",
                    "compatible", "dlg,da9214"
                ],
                "a72-provider": [
                    "-p", "-t", "s", "/a72-power@10222000",
                    "compatible", "mediatek,mt6797-a72-power"
                ],
                "cpu8-psci": [
                    "-t", "s", "/cpus/cpu@200", "enable-method", "psci"
                ],
                "cpu9-psci": [
                    "-t", "s", "/cpus/cpu@201", "enable-method", "psci"
                ],
                "unrelated": ["-t", "s", "/", "gemini,unexpected", "yes"],
            }
            rejected = 0
            for name, mutation in mutations.items():
                bad = work / f"bad-{name}.dtb"
                shutil.copyfile(good, bad)
                fdtput(bad, mutation)
                if bad.read_bytes() == good.read_bytes():
                    raise ValueError(f"mutation {name} made no byte change")
                run([*base_command, str(bad)], success=False)
                rejected += 1
        print("validation=cassini-dtb-mutations")
        print("positive_fixture=accepted")
        print(f"mutations_rejected={rejected}-of-{len(mutations)}")
        print("i2c6_children=forbidden")
        print("cpu8_cpu9_fail_closed=required")
        print("a72_provider=forbidden")
        print("device_access=none")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
