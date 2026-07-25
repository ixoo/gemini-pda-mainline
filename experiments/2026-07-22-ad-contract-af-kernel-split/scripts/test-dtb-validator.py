#!/usr/bin/env python3
"""Exercise Candidate AH's two-property whole-FDT allowlist."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile


def run(command: list[str], expect_success: bool = True) -> None:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if (result.returncode == 0) != expect_success:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError(f"unexpected command result ({result.returncode}): {detail}")
    if not expect_success and "error:" not in result.stderr:
        raise ValueError("mutation rejection did not provide a fail-closed diagnostic")


def mutate(path: pathlib.Path, arguments: list[str]) -> None:
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
    parser.add_argument("--ad-dtb", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        script_dir = pathlib.Path(__file__).resolve().parent
        builder = script_dir / "build-ah-dtb.sh"
        validator = script_dir / "validate-dtb-delta.py"
        for command in ("bash", "fdtput", "python3"):
            if shutil.which(command) is None:
                raise ValueError(f"required command missing: {command}")
        with tempfile.TemporaryDirectory(prefix="candidate-ah-dtb-mutations-") as raw:
            work = pathlib.Path(raw)
            good = work / "good.dtb"
            run(
                [
                    "bash",
                    str(builder),
                    "--ad-dtb",
                    str(args.ad_dtb),
                    "--output",
                    str(good),
                ]
            )
            validator_command = [
                sys.executable,
                str(validator),
                "--ad",
                str(args.ad_dtb),
                "--candidate",
            ]
            run([*validator_command, str(good)])

            mutations = {
                "cpu8-psci": ["-t", "s", "/cpus/cpu@200", "enable-method", "psci"],
                "cpu9-psci": ["-t", "s", "/cpus/cpu@201", "enable-method", "psci"],
                "cpu0-method": [
                    "-t",
                    "s",
                    "/cpus/cpu@0",
                    "enable-method",
                    "mediatek,mt6797-psci",
                ],
                "cpu8-compatible": [
                    "-t",
                    "s",
                    "/cpus/cpu@200",
                    "compatible",
                    "arm,cortex-a53",
                ],
                "cpu8-reg": ["-t", "x", "/cpus/cpu@200", "reg", "201"],
                "cpu8-status": ["-t", "s", "/cpus/cpu@200", "status", "disabled"],
                "cpu8-extra": ["-t", "s", "/cpus/cpu@200", "gemini,test", "bad"],
                "remove-cpu9": ["-r", "/cpus/cpu@201"],
                "simplefb-width": [
                    "-t",
                    "x",
                    "/chosen/framebuffer@7dfb0000",
                    "width",
                    "439",
                ],
                "usb-status": ["-t", "s", "/usb@11271000", "status", "disabled"],
                "xhci-status": [
                    "-t",
                    "s",
                    "/usb@11271000/usb@11270000",
                    "status",
                    "okay",
                ],
                "aw9523-status": [
                    "-t",
                    "s",
                    "/i2c@1101c000/gpio-expander@5b",
                    "status",
                    "disabled",
                ],
                "keyboard-status": [
                    "-t",
                    "s",
                    "/keyboard-matrix",
                    "status",
                    "disabled",
                ],
                "scp-status": ["-t", "s", "/scp@10020000", "status", "okay"],
                "i2c6-enabled": [
                    "-t",
                    "s",
                    "/i2c@1100e000",
                    "status",
                    "okay",
                ],
                "a72-power-node": [
                    "-p",
                    "-t",
                    "s",
                    "/a72-power@10222000",
                    "compatible",
                    "mediatek,mt6797-a72-power",
                ],
                "da9214-node": [
                    "-p",
                    "-t",
                    "s",
                    "/i2c@1100e000/regulator@68",
                    "compatible",
                    "dlg,da9214",
                ],
                "static-lk-framebuffer": [
                    "-p",
                    "-t",
                    "s",
                    "/reserved-memory/mblock-3-framebuffer",
                    "compatible",
                    "mediatek,framebuffer",
                ],
                "scp-reservation-size": [
                    "-t",
                    "x",
                    "/reserved-memory/reserve-memory-scp_share",
                    "size",
                    "0",
                    "2000000",
                ],
                "ramoops-size": [
                    "-t",
                    "x",
                    "/reserved-memory/ramoops@44410000",
                    "reg",
                    "0",
                    "44410000",
                    "0",
                    "d0000",
                ],
                "provider-phandle": [
                    "-t",
                    "x",
                    "/topckgen@10000000",
                    "phandle",
                    "77",
                ],
                "root-extra": ["-t", "s", "/", "gemini,unexpected", "yes"],
            }
            rejected = 0
            for name, command in mutations.items():
                bad = work / f"bad-{name}.dtb"
                shutil.copyfile(good, bad)
                mutate(bad, command)
                run([*validator_command, str(bad)], expect_success=False)
                rejected += 1

        print("validation=candidate-ah-dtb-mutations")
        print("positive_fixture=accepted")
        print(f"mutations_rejected={rejected}-of-{len(mutations)}")
        print("simplefb_usb_keyboard_scp_reservation_mutations=rejected")
        print("active_a72_operation=none")
        print("device_access=none")
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
