#!/usr/bin/env python3
"""Self-test for validate-gpu-config.py using the minimal fixture."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
FIXTURE = HERE.parent / "fixtures" / "mt6797-gpu-minimal.dts"
VALIDATOR = HERE / "validate-gpu-config.py"
COMPOSER = HERE / "compose-gpu-dtb.py"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, text=True, capture_output=True, **kwargs)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gpu-validator-") as tmp:
        tmp_path = Path(tmp)
        dtb = tmp_path / "gpu.dtb"
        enabled_dtb = tmp_path / "gpu-enabled.dtb"
        result = run(["dtc", "-I", "dts", "-O", "dtb", "-o", str(dtb), str(FIXTURE)])
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            return 1

        config = tmp_path / "config"
        config.write_text(
            "\n".join(
                [
                    "CONFIG_DRM=y",
                    "CONFIG_DRM_PANFROST=m",
                    "CONFIG_PM_DEVFREQ=y",
                    "CONFIG_PM_OPP=y",
                    "CONFIG_MTK_SCPSYS=y",
                    "CONFIG_COMMON_CLK_MT6797_MFGSYS=y",
                    "CONFIG_REGULATOR_RT5735=y",
                    "CONFIG_I2C_MT65XX=y",
                ]
            )
            + "\n"
        )

        base = run(
            [
                sys.executable,
                str(VALIDATOR),
                "--config",
                str(config),
                "--dtb",
                str(dtb),
                "--gpu-path",
                "/gpu@13040000",
                "--expect",
                "disabled",
            ]
        )
        if base.returncode:
            print(base.stderr, file=sys.stderr)
            return 1

        # Create an enabled composition with the reviewed helper.
        result = run(
            [
                sys.executable,
                str(COMPOSER),
                "--input",
                str(dtb),
                "--output",
                str(enabled_dtb),
                "--gpu-path",
                "/gpu@13040000",
                "--mfgsys-path",
                "/syscon@13000000",
                "--infrasys-path",
                "/syscon@10001000",
                "--i2c7-path",
                "/i2c@11010000",
                "--regulator-path",
                "/i2c@11010000/regulator@1c",
            ]
        )
        if result.returncode:
            print(result.stderr, file=sys.stderr)
            return 1

        enabled = run(
            [
                sys.executable,
                str(VALIDATOR),
                "--config",
                str(config),
                "--dtb",
                str(enabled_dtb),
                "--gpu-path",
                "/gpu@13040000",
                "--expect",
                "enabled",
            ]
        )
        if enabled.returncode:
            print(enabled.stderr, file=sys.stderr)
            return 1

        # Negative: wrong interrupt order must fail.
        run(["fdtput", "-t", "x", str(enabled_dtb), "/gpu@13040000", "interrupts", "0", "263", "8", "0", "264", "8", "0", "262", "8"])
        broken = run(
            [
                sys.executable,
                str(VALIDATOR),
                "--config",
                str(config),
                "--dtb",
                str(enabled_dtb),
                "--gpu-path",
                "/gpu@13040000",
                "--expect",
                "enabled",
            ]
        )
        if broken.returncode == 0:
            print("FAIL: validator accepted wrong interrupt order", file=sys.stderr)
            return 1

    print("PASS: GPU validator positive and negative cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
