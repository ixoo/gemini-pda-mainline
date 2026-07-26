#!/usr/bin/env python3
"""Validate one Candidate AS kernel package against the pinned AS profile."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import stat
import sys


PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-da9214-legacy-readonly"
)
SERIES_REL = "patches/series-dvfsp-handoff-owner-i2c6-consumer-ap-dma-preserve-da9214-legacy-readonly"
FRAGMENTS = [
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
    "configs/gemini-smp8.fragment",
    "configs/gemini-a72-observer.fragment",
    "configs/gemini-a72-observer-initcall-blacklist.fragment",
    "configs/gemini-dvfsp-handoff-owner.fragment",
    "configs/gemini-dvfsp-i2c6-consumer.fragment",
    "configs/gemini-dvfsp-da9214-legacy-readonly.fragment",
]
REQUIRED_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused "
    "initcall_blacklist=mt6797_a72_power_driver_init fw_devlink=rpm"
)
REQUIRED_CONFIG = (
    f'CONFIG_CMDLINE="{REQUIRED_CMDLINE}"',
    "CONFIG_CMDLINE_FORCE=y",
    "CONFIG_IKCONFIG=y",
    "CONFIG_IKCONFIG_PROC=y",
    "CONFIG_SMP=y",
    "CONFIG_HOTPLUG_CPU=y",
    "CONFIG_ARM_PSCI_FW=y",
    "CONFIG_ARCH_MEDIATEK=y",
    "CONFIG_OF=y",
    "CONFIG_I2C=y",
    "CONFIG_I2C_MT65XX=y",
    "CONFIG_PINCTRL_AW9523=y",
    "CONFIG_KEYBOARD_MATRIX=y",
    "CONFIG_REGMAP_I2C=y",
    "CONFIG_REGULATOR=y",
    "CONFIG_REGULATOR_DA9211=y",
    "CONFIG_MFD_SYSCON=y",
    "CONFIG_RESET_CONTROLLER=y",
    "CONFIG_MTK_MT6797_A72_POWER=y",
    "CONFIG_MTK_MT6797_DVFSP_HANDOFF=y",
    "CONFIG_WATCHDOG=y",
    "CONFIG_MEDIATEK_WATCHDOG=y",
    "CONFIG_USB_GADGET=y",
    "CONFIG_USB_ETH=y",
    "CONFIG_PSTORE=y",
    "CONFIG_PSTORE_RAM=y",
    "# CONFIG_SUSPEND is not set",
    "# CONFIG_CPU_FREQ is not set",
    "# CONFIG_CPU_IDLE is not set",
    "# CONFIG_MODULES is not set",
    "# CONFIG_MMC is not set",
    "# CONFIG_MTD is not set",
    "# CONFIG_SCSI is not set",
    "# CONFIG_ATA is not set",
    "# CONFIG_USB_MASS_STORAGE is not set",
)
REQUIRED_IMAGE_MARKERS = (
    b"shared-ap-dma=preserved",
    b"dma_unchanged=%u",
    b"i2c6_policy=requires-ready",
    b"mt6797-dvfsp-handoff",
    b"legacy DA9214",
)


def fail(message: str) -> None:
    raise ValueError(message)


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        fail(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def series_entries(data: bytes) -> list[str]:
    entries = []
    for number, raw in enumerate(data.decode("utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        path = pathlib.PurePosixPath(line)
        if (
            path.is_absolute()
            or ".." in path.parts
            or len(path.parts) != 2
            or path.parts[0] != "v7.1.3"
            or path.suffix != ".patch"
            or path.as_posix() != line
            or any(character.isspace() for character in line)
        ):
            fail(f"unsafe patch-series entry at line {number}")
        entries.append(line)
    if len(entries) != len(set(entries)):
        fail("patch series contains a duplicate entry")
    return entries


def validate(repository: pathlib.Path, package: pathlib.Path) -> None:
    if package.is_symlink() or not package.is_dir():
        fail("package is missing or unsafe")
    manifest = json.loads(regular(repository / "kernel/manifest.json", "manifest"))
    profile = manifest["config"]["profiles"].get(PROFILE)
    expected_profile = {"base": "defconfig", "patch_series": SERIES_REL, "fragments": FRAGMENTS}
    if profile != expected_profile:
        fail("AS profile differs from the repository manifest")

    build = json.loads(regular(package / "provenance/build.json", "build provenance"))
    if build.get("build_profile") != PROFILE:
        fail("package build profile is not Candidate AS")
    repository_series = regular(repository / SERIES_REL, "repository AS series")
    packaged_series = regular(package / "provenance/series", "packaged AS series")
    if repository_series != packaged_series:
        fail("packaged AS series differs from repository")
    entries = series_entries(repository_series)
    if len(entries) != 108 or not entries[-1].endswith("0108-regulator-da9211-reproduce-legacy-page-selector-rmw.patch"):
        fail("AS series does not end in patch 0108")
    if any(pathlib.PurePosixPath(entry).name.startswith("0093-") for entry in entries):
        fail("AS series selects the forbidden active-power patch")
    required_entries = {
        "v7.1.3/0096-regulator-da9211-support-legacy-DA9214-interface.patch",
        "v7.1.3/0104-regulator-da9211-require-exact-legacy-DA9214-signature.patch",
        "v7.1.3/0105-arm64-dts-mediatek-enable-legacy-Gemini-DA9214-after-handoff.patch",
        "v7.1.3/0106-regulator-da9211-use-legacy-DA9214-page-selector.patch",
        "v7.1.3/0107-regulator-da9211-use-write-only-legacy-page-selector.patch",
        "v7.1.3/0108-regulator-da9211-reproduce-legacy-page-selector-rmw.patch",
    }
    if not required_entries.issubset(entries):
        fail("AS series omits a required legacy DA9214 patch")

    for entry in entries:
        repository_patch = regular(repository / "patches" / entry, f"repository patch {entry}")
        packaged_patch = regular(package / "provenance/patches" / entry, f"packaged patch {entry}")
        if repository_patch != packaged_patch:
            fail(f"packaged patch differs from repository: {entry}")

    for relative in FRAGMENTS:
        name = pathlib.PurePosixPath(relative).name
        repository_fragment = regular(repository / relative, f"repository fragment {relative}")
        packaged_fragment = regular(package / "provenance/configs" / name, f"packaged fragment {name}")
        if repository_fragment != packaged_fragment:
            fail(f"packaged fragment differs from repository: {relative}")

    config = regular(package / "kernel.config", "kernel config").decode("utf-8")
    for line in REQUIRED_CONFIG:
        if line not in config.splitlines():
            fail(f"required config line is missing: {line}")
    image = regular(package / "Image", "kernel Image")
    image_gz = regular(package / "Image.gz", "kernel Image.gz")
    if gzip.decompress(image_gz) != image:
        fail("Image.gz does not expand to exact Image")
    for marker in REQUIRED_IMAGE_MARKERS:
        if marker not in image:
            fail(f"kernel Image lacks required AS marker: {marker!r}")
    system_map = regular(package / "System.map", "System.map")
    for marker in (
        b"mt6797_dvfsp_handoff_validate_clock",
        b"mt6797_dvfsp_sample_consumer_post",
        b"da9211_i2c_probe",
        b"da9214_read_signature",
        b"da9214_read_legacy_page2_reg",
    ):
        if marker not in system_map:
            fail(f"System.map lacks required AS symbol: {marker!r}")

    print("validation=candidate-as-package")
    print(f"profile={PROFILE}")
    print(f"series_path={SERIES_REL}")
    print(f"series_sha256={digest(repository_series)}")
    print(f"patch_count={len(entries)}")
    print(f"config_sha256={digest(config.encode())}")
    print(f"image_sha256={digest(image)}")
    print("runtime_result=not-tested")


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
