#!/usr/bin/env python3
"""Validate the exact Pioneer kernel package before boot assembly."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import stat
import sys

sys.dont_write_bytecode = True
import candidate_pioneer as cg


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate(repository: pathlib.Path, package: pathlib.Path) -> None:
    manifest = json.loads(regular(repository / "kernel/manifest.json", "manifest"))
    profile = manifest["config"]["profiles"].get(cg.PROFILE)
    if profile is None or profile["base"] != "defconfig":
        raise ValueError("Pioneer profile is missing from the repository manifest")
    if profile["patch_series"] != cg.SERIES:
        raise ValueError("Pioneer patch-series identity differs")
    build = json.loads(regular(package / "provenance/build.json", "build provenance"))
    if build.get("build_profile") != cg.PROFILE:
        raise ValueError("package build profile is not Pioneer")
    repository_series = regular(repository / cg.SERIES, "repository patch series")
    if repository_series != regular(package / "provenance/series", "packaged patch series"):
        raise ValueError("packaged patch series differs from the repository")
    entries = [
        line.strip()
        for line in repository_series.decode().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if (
        len(entries) != 113
        or not entries[-1].endswith(
            "0113-regulator-da9211-preserve-legacy-page-revert-selector.patch"
        )
    ):
        raise ValueError("Pioneer series does not end in the active CPU8 retry patch")
    config = regular(package / "kernel.config", "kernel config").decode("ascii")
    required = (
        'CONFIG_LOCALVERSION="-gemini-pioneer"',
        'CONFIG_CMDLINE="console=ttyS0,921600n8 earlycon maxcpus=9 nokaslr '
        'ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug rdinit=/init '
        'panic=0 g_ether.dev_addr=42:00:15:19:82:01 '
        'g_ether.host_addr=42:00:15:19:82:00 '
        'g_ether.iManufacturer=gemini-pda-mainline '
        'g_ether.iProduct=Gemini-L-Pioneer '
        'g_ether.iSerialNumber=GEMINI_PIONEER_20260726 '
        'clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 '
        'regulator_ignore_unused fw_devlink=rpm"',
        "CONFIG_CMDLINE_FORCE=y",
        "CONFIG_SMP=y",
        "CONFIG_HOTPLUG_CPU=y",
        "CONFIG_ARM_PSCI_FW=y",
        "CONFIG_MTK_MT6797_A72_POWER=y",
        "CONFIG_USB_GADGET=y",
        "CONFIG_USB_ETH=y",
        "CONFIG_USB_ETH_RNDIS=y",
        "CONFIG_MEDIATEK_WATCHDOG=y",
        "# CONFIG_SUSPEND is not set",
        "# CONFIG_CPU_IDLE is not set",
        "# CONFIG_MODULES is not set",
    )
    missing = [line for line in required if line not in config.splitlines()]
    if missing:
        raise ValueError(f"required Pioneer config is missing: {missing[0]}")
    image = regular(package / "Image", "kernel Image")
    if gzip.decompress(regular(package / "Image.gz", "kernel Image.gz")) != image:
        raise ValueError("Image.gz does not expand to Image")
    system_map = regular(package / "System.map", "System.map").decode("ascii")
    for symbol in (
        "mt6797_a72_power_cpu_boot_ready",
        "mt6797_a72_power_cpu_on_complete",
        "mt6797_a72_power_cpu_on_failed",
        "mt6797_a72_power_retry_cpu8",
    ):
        if symbol not in system_map:
            raise ValueError(f"System.map lacks Pioneer symbol: {symbol}")
    print("validation=candidate-pioneer-package")
    print(f"profile={cg.PROFILE}")
    print(f"patch_count={len(entries)}")
    print(f"config_sha256={digest(config.encode())}")
    print(f"image_sha256={digest(image)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate(args.repository.resolve(strict=True), args.package.resolve(strict=True))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
