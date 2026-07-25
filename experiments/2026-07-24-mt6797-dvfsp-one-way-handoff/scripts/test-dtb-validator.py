#!/usr/bin/env python3
"""Exercise Candidate AO's exact-AH whole-FDT allowlist."""

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


def run(command: list[str], expect_success: bool = True) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if (result.returncode == 0) != expect_success:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"unexpected command result ({result.returncode}): {detail}")
    if not expect_success and "error:" not in result.stderr:
        raise ValueError("mutation rejection did not provide a fail-closed diagnostic")


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
    parser.add_argument("--ah-dtb", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        script_dir = pathlib.Path(__file__).resolve().parent
        builder = script_dir / "build-ao-dtb.sh"
        validator = script_dir / "validate-dtb-delta.py"
        for command in ("bash", "fdtput", "python3"):
            if shutil.which(command) is None:
                raise ValueError(f"required command missing: {command}")

        with tempfile.TemporaryDirectory(
            prefix="candidate-ao-dtb-mutations-"
        ) as raw:
            work = pathlib.Path(raw)
            good = work / "good.dtb"
            run(
                [
                    "bash",
                    str(builder),
                    "--ah-dtb",
                    str(args.ah_dtb),
                    "--output",
                    str(good),
                ]
            )
            validator_command = [
                sys.executable,
                str(validator),
                "--ah",
                str(args.ah_dtb),
                "--candidate",
            ]
            run([*validator_command, str(good)])

            handoff = "/dvfsp-handoff@11015000"
            mutations: dict[str, Callable[[pathlib.Path], None]] = {
                "compatible": lambda path: fdtput(
                    path,
                    [
                        "-t",
                        "s",
                        handoff,
                        "compatible",
                        "mediatek,mt6797-dvfsp-handoff-observer",
                    ],
                ),
                "reg-base": lambda path: fdtput(
                    path,
                    ["-t", "x", handoff, "reg", "0", "11014000", "0", "1000"],
                ),
                "reg-size": lambda path: fdtput(
                    path,
                    ["-t", "x", handoff, "reg", "0", "11015000", "0", "2000"],
                ),
                "clock-provider": lambda path: fdtput(
                    path, ["-t", "x", handoff, "clocks", "2", "36"]
                ),
                "clock-id": lambda path: fdtput(
                    path, ["-t", "x", handoff, "clocks", "3", "35"]
                ),
                "clock-extra": lambda path: fdtput(
                    path, ["-t", "x", handoff, "clocks", "3", "36", "3", "2e"]
                ),
                "clock-name": lambda path: fdtput(
                    path, ["-t", "s", handoff, "clock-names", "main"]
                ),
                "infracfg-reference": lambda path: fdtput(
                    path, ["-t", "x", handoff, "mediatek,infracfg", "2"]
                ),
                "status": lambda path: fdtput(
                    path, ["-t", "s", handoff, "status", "disabled"]
                ),
                "extra-property": lambda path: fdtput(
                    path, ["-t", "s", handoff, "gemini,unexpected", "yes"]
                ),
                "remove-node": lambda path: fdtput(path, ["-r", handoff]),
                "i2c6-status": lambda path: fdtput(
                    path, ["-t", "s", "/i2c@1100e000", "status", "okay"]
                ),
                "i2c6-property": lambda path: fdtput(
                    path,
                    ["-t", "x", "/i2c@1100e000", "clock-frequency", "61a80"],
                ),
                "i2c6-child": lambda path: fdtput(
                    path,
                    [
                        "-p",
                        "-t",
                        "s",
                        "/i2c@1100e000/client@50",
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
                        "/i2c@1100e000/regulator@68",
                        "compatible",
                        "dlg,da9214",
                    ],
                ),
                "observer-node": lambda path: fdtput(
                    path,
                    [
                        "-p",
                        "-t",
                        "s",
                        "/dvfsp-observer@11015000",
                        "compatible",
                        "mediatek,mt6797-dvfsp-handoff-observer",
                    ],
                ),
                "legacy-dvfsp-node": lambda path: fdtput(
                    path,
                    [
                        "-p",
                        "-t",
                        "s",
                        "/dvfsp@11015000",
                        "compatible",
                        "mediatek,dvfsp",
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
                "cpu8-method": lambda path: fdtput(
                    path, ["-t", "s", "/cpus/cpu@200", "enable-method", "psci"]
                ),
                "simplefb-width": lambda path: fdtput(
                    path,
                    [
                        "-t",
                        "x",
                        "/chosen/framebuffer@7dfb0000",
                        "width",
                        "439",
                    ],
                ),
                "usb-status": lambda path: fdtput(
                    path, ["-t", "s", "/usb@11271000", "status", "disabled"]
                ),
                "keyboard-status": lambda path: fdtput(
                    path, ["-t", "s", "/keyboard-matrix", "status", "disabled"]
                ),
                "provider-phandle": lambda path: fdtput(
                    path, ["-t", "x", "/syscon@10001000", "phandle", "4"]
                ),
                "root-extra": lambda path: fdtput(
                    path, ["-t", "s", "/", "gemini,unexpected", "yes"]
                ),
                "header-magic": lambda path: raw_u32(path, 0, 0),
                "header-structure-offset": lambda path: raw_u32(path, 8, 0x3C),
                "header-strings-offset": lambda path: raw_u32(path, 12, 0x61AC),
                "header-reservation-offset": lambda path: raw_u32(path, 16, 0x30),
                "header-version": lambda path: raw_u32(path, 20, 16),
                "header-last-compatible": lambda path: raw_u32(path, 24, 17),
                "header-boot-cpu": lambda path: raw_u32(path, 28, 1),
                "header-strings-size": lambda path: raw_u32(path, 32, 0x5BA),
                "header-structure-size": lambda path: raw_u32(path, 36, 0x616C),
                "header-total-size": mutate_totalsize,
                "reservation-map": mutate_reservation_terminator,
            }
            for prop in (
                "compatible",
                "reg",
                "clocks",
                "clock-names",
                "mediatek,infracfg",
                "status",
            ):
                mutations[f"missing-{prop}"] = (
                    lambda path, property_name=prop: fdtput(
                        path, ["-d", handoff, property_name]
                    )
                )

            rejected = 0
            for name, mutation in mutations.items():
                bad = work / f"bad-{name}.dtb"
                shutil.copyfile(good, bad)
                mutation(bad)
                run([*validator_command, str(bad)], expect_success=False)
                rejected += 1

            mutated_ah = work / "mutated-ah.dtb"
            shutil.copyfile(args.ah_dtb, mutated_ah)
            fdtput(
                mutated_ah,
                ["-t", "s", "/i2c@1100e000", "clock-names", "dma", "main"],
            )
            run(
                [
                    "bash",
                    str(builder),
                    "--ah-dtb",
                    str(mutated_ah),
                    "--output",
                    str(work / "from-mutated-ah.dtb"),
                ],
                expect_success=False,
            )

        print("validation=candidate-ao-dtb-mutations")
        print("positive_fixture=accepted")
        print(f"mutations_rejected={rejected}-of-{len(mutations)}")
        print("mutated_ah_input=rejected")
        print("six_property_contract_mutations=rejected")
        print("i2c6_disabled_childless_mutations=rejected")
        print("forbidden_dvfsp_da9214_a72_power_nodes=rejected")
        print("fdt_header_reservation_phandle_mutations=rejected")
        print("active_i2c6_da9214_a72_operation=none")
        print("device_access=none")
        print("storage_access=none")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
