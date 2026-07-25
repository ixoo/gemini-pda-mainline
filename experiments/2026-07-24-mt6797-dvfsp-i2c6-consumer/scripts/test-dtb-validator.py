#!/usr/bin/env python3
"""Exercise Candidate AP's exact-AO whole-FDT allowlist."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import struct
import subprocess
import sys
import tempfile
from collections.abc import Callable

sys.dont_write_bytecode = True

I2C6 = "/i2c@1100e000"
HANDOFF = "/dvfsp-handoff@11015000"


def run(
    command: list[str],
    expect_success: bool = True,
    *,
    label: str = "command",
) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if (result.returncode == 0) != expect_success:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(
            f"{label}: unexpected command result ({result.returncode}): {detail}"
        )
    if not expect_success and "error:" not in result.stderr:
        raise ValueError(
            f"{label}: rejection did not provide a fail-closed diagnostic"
        )


def fdtput(path: pathlib.Path, arguments: list[str]) -> None:
    if arguments[:1] == ["-t"] and len(arguments) >= 4:
        command = ["fdtput", "-t", arguments[1], str(path), *arguments[2:]]
    elif arguments[:2] == ["-p", "-t"] and len(arguments) >= 5:
        command = ["fdtput", "-p", "-t", arguments[2], str(path), *arguments[3:]]
    elif arguments[:1] == ["-r"] and len(arguments) == 2:
        command = ["fdtput", "-r", str(path), arguments[1]]
    elif arguments[:1] == ["-d"] and len(arguments) == 3:
        command = ["fdtput", "-d", str(path), arguments[1], arguments[2]]
    else:
        raise ValueError(f"unsupported mutation command: {arguments!r}")
    run(command)


def raw_u32(path: pathlib.Path, offset: int, value: int) -> None:
    data = bytearray(path.read_bytes())
    struct.pack_into(">I", data, offset, value)
    path.write_bytes(data)


def mutate_totalsize(path: pathlib.Path) -> None:
    data = bytearray(path.read_bytes())
    data.extend(b"\0\0\0\0")
    struct.pack_into(">I", data, 4, len(data))
    path.write_bytes(data)


def mutate_reservation_terminator(path: pathlib.Path) -> None:
    data = bytearray(path.read_bytes())
    header = struct.unpack_from(">10I", data)
    struct.pack_into(">QQ", data, header[4], 0x40000000, 0x1000)
    path.write_bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ao-dtb", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        script_dir = pathlib.Path(__file__).resolve().parent
        builder = script_dir / "build-ap-dtb.sh"
        validator = script_dir / "validate-dtb-delta.py"
        for command in ("bash", "fdtput", "python3"):
            if shutil.which(command) is None:
                raise ValueError(f"required command missing: {command}")

        with tempfile.TemporaryDirectory(
            prefix="candidate-ap-dtb-mutations-"
        ) as raw:
            work = pathlib.Path(raw)
            good = work / "good.dtb"
            run(
                [
                    "bash",
                    str(builder),
                    "--ao-dtb",
                    str(args.ao_dtb),
                    "--output",
                    str(good),
                ]
            )
            validator_command = [
                sys.executable,
                str(validator),
                "--ao",
                str(args.ao_dtb),
                "--candidate",
            ]
            run([*validator_command, str(good)])

            mutations: dict[str, Callable[[pathlib.Path], None]] = {
                "dependency-wrong": lambda path: fdtput(
                    path, ["-t", "x", I2C6, "access-controllers", "2b"]
                ),
                "dependency-extra-cell": lambda path: fdtput(
                    path, ["-t", "x", I2C6, "access-controllers", "2c", "0"]
                ),
                "dependency-missing": lambda path: fdtput(
                    path, ["-d", I2C6, "access-controllers"]
                ),
                "access-cells-one": lambda path: fdtput(
                    path, ["-t", "x", HANDOFF, "#access-controller-cells", "1"]
                ),
                "access-cells-missing": lambda path: fdtput(
                    path, ["-d", HANDOFF, "#access-controller-cells"]
                ),
                "handoff-phandle-wrong": lambda path: fdtput(
                    path, ["-t", "x", HANDOFF, "phandle", "2b"]
                ),
                "handoff-phandle-missing": lambda path: fdtput(
                    path, ["-d", HANDOFF, "phandle"]
                ),
                "i2c6-disabled": lambda path: fdtput(
                    path, ["-t", "s", I2C6, "status", "disabled"]
                ),
                "clock-frequency": lambda path: fdtput(
                    path, ["-t", "x", I2C6, "clock-frequency", "61a80"]
                ),
                "push-pull": lambda path: fdtput(
                    path, ["-t", "x", I2C6, "mediatek,use-push-pull", "1"]
                ),
                "pinctrl-names": lambda path: fdtput(
                    path, ["-t", "s", I2C6, "pinctrl-names", "default"]
                ),
                "pinctrl-0": lambda path: fdtput(
                    path, ["-t", "x", I2C6, "pinctrl-0", "1"]
                ),
                "i2c6-child": lambda path: fdtput(
                    path,
                    [
                        "-p",
                        "-t",
                        "s",
                        I2C6 + "/client@50",
                        "compatible",
                        "test,client",
                    ],
                ),
                "da9214-node": lambda path: fdtput(
                    path,
                    [
                        "-p",
                        "-t",
                        "s",
                        I2C6 + "/regulator@68",
                        "compatible",
                        "dlg,da9214",
                    ],
                ),
                "a72-power-node": lambda path: fdtput(
                    path,
                    [
                        "-p",
                        "-t",
                        "s",
                        "/a72-power@10222000",
                        "compatible",
                        "mediatek,mt6797-a72-power",
                    ],
                ),
                "unrelated-property": lambda path: fdtput(
                    path, ["-t", "s", "/", "gemini,unexpected", "yes"]
                ),
                "header-magic": lambda path: raw_u32(path, 0, 0),
                "header-structure-offset": lambda path: raw_u32(path, 8, 0x3C),
                "header-strings-offset": lambda path: raw_u32(path, 12, 0x61D8),
                "header-reservation-offset": lambda path: raw_u32(path, 16, 0x30),
                "header-version": lambda path: raw_u32(path, 20, 16),
                "header-last-compatible": lambda path: raw_u32(path, 24, 17),
                "header-boot-cpu": lambda path: raw_u32(path, 28, 1),
                "header-strings-size": lambda path: raw_u32(path, 32, 0x5E6),
                "header-structure-size": lambda path: raw_u32(path, 36, 0x6198),
                "header-total-size": mutate_totalsize,
                "reservation-map": mutate_reservation_terminator,
            }

            rejected = 0
            for name, mutation in mutations.items():
                bad = work / f"bad-{name}.dtb"
                shutil.copyfile(good, bad)
                try:
                    mutation(bad)
                except (OSError, ValueError, struct.error) as exc:
                    raise ValueError(
                        f"mutation {name}: setup failed: {exc}"
                    ) from exc
                if bad.read_bytes() == good.read_bytes():
                    raise ValueError(
                        f"mutation {name}: mutation produced no byte change"
                    )
                run(
                    [*validator_command, str(bad)],
                    expect_success=False,
                    label=f"mutation {name}",
                )
                rejected += 1

            mutated_ao = work / "mutated-ao.dtb"
            shutil.copyfile(args.ao_dtb, mutated_ao)
            fdtput(
                mutated_ao,
                ["-t", "s", I2C6, "clock-names", "dma", "main"],
            )
            run(
                [
                    "bash",
                    str(builder),
                    "--ao-dtb",
                    str(mutated_ao),
                    "--output",
                    str(work / "from-mutated-ao.dtb"),
                ],
                expect_success=False,
            )

        print("validation=candidate-ap-dtb-mutations")
        print("positive_fixture=accepted")
        print(f"mutations_rejected={rejected}-of-{len(mutations)}")
        print("mutated_ao_input=rejected")
        print("access_controller_dependency_mutations=rejected")
        print("i2c6_child_frequency_push_pull_pinctrl_mutations=rejected")
        print("forbidden_da9214_a72_operation=none")
        print("fdt_header_reservation_phandle_mutations=rejected")
        print("device_access=none")
        print("storage_access=none")
        return 0
    except (OSError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
