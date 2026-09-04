#!/usr/bin/env python3
"""Validate the exact canonical PWRAP-reset serviceability package."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import stat
import subprocess
from pathlib import Path, PurePosixPath


PROFILE = "mt6797-pwrap-reset-serviceability"
ORIGIN = "https://github.com/ixoo/gemini-pda-mainline.git"
BUILD_COMMIT = "ded915b81d56902d8800ff9fefc477480e4bcaa1"
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
    "configs/gemini-emmc-development.fragment",
    "configs/gemini-mt6797-pwrap-reset-serviceability.fragment",
]
REQUIRED_CONFIG = (
    'CONFIG_LOCALVERSION="-gemini-mt6797-pwrap-reset"',
    "# CONFIG_LOCALVERSION_AUTO is not set",
    "CONFIG_CMDLINE_FORCE=y",
    "CONFIG_SMP=y",
    "CONFIG_MTK_PMIC_WRAP=y",
    "CONFIG_MFD_MT6397=y",
    "CONFIG_REGULATOR_MT6351=y",
    "CONFIG_MMC=y",
    "CONFIG_MMC_BLOCK=y",
    "CONFIG_MMC_MTK=y",
    "CONFIG_USB_GADGET=y",
    "CONFIG_USB_ETH=y",
    "CONFIG_COMMON_CLK_MT6797=y",
    "CONFIG_RESET_CONTROLLER=y",
    "# CONFIG_KUNIT is not set",
    "# CONFIG_THERMAL is not set",
    "# CONFIG_CPU_FREQ is not set",
    "# CONFIG_CPU_IDLE is not set",
    "# CONFIG_SUSPEND is not set",
    "# CONFIG_MODULES is not set",
)
FORBIDDEN_CONFIG = (
    "CONFIG_COMMON_CLK_MT6797_RESET_KUNIT_TEST=y",
)
REQUIRED_SYMBOLS = (
    " pwrap_probe\n",
    " mt6351_regulator_probe\n",
    " msdc_drv_probe\n",
    " mtk_register_reset_controller_with_dev\n",
    " mtk_reset_assert_set_clr\n",
    " mtk_reset_deassert_set_clr\n",
)
RESET_PATCHES = {
    "v7.1.3/0514-dt-bindings-reset-mediatek-correct-MT6797-infracfg-resets.patch":
        "7b7e88138f47892b642c230c9ac9e9306f06a467e397a0cc9f3f96c0791351a7",
    "v7.1.3/0515-clk-mediatek-repair-MT6797-infracfg-resets.patch":
        "4b11d7021bc3c6f033ce2fdec34fef39df442fae2df9be759a5d591763cfb562",
}


class PackageError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise PackageError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def git(repository: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repository), *args], text=True
    ).strip()


def validate_sums(package: Path) -> None:
    lines = regular(package / "SHA256SUMS", "package checksums").decode().splitlines()
    seen: set[str] = set()
    for line in lines:
        expected, marker, relative = line.partition("  ")
        if marker != "  " or len(expected) != 64:
            raise PackageError("malformed package checksum line")
        path = PurePosixPath(relative)
        if path.is_absolute() or ".." in path.parts or relative in seen:
            raise PackageError("unsafe or duplicate package checksum path")
        seen.add(relative)
        if digest(regular(package / path, f"package member {relative}")) != expected:
            raise PackageError(f"package checksum mismatch: {relative}")


def validate(repository: Path, package: Path) -> dict[str, object]:
    if package.is_symlink() or not package.is_dir():
        raise PackageError("package directory is missing or unsafe")
    manifest = json.loads(regular(repository / "kernel/manifest.json", "manifest"))
    expected_profile = {
        "base": "defconfig",
        "patch_series": "patches/series",
        "fragments": FRAGMENTS,
    }
    if manifest["config"]["profiles"].get(PROFILE) != expected_profile:
        raise PackageError("manifest profile changed")
    commit = BUILD_COMMIT
    if git(repository, "cat-file", "-t", commit) != "commit":
        raise PackageError("pinned Buildbox commit is absent")
    published = subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor", commit,
         "origin/main"],
        check=False,
    )
    if published.returncode != 0:
        raise PackageError("pinned Buildbox commit is not published at origin/main")
    if git(repository, "remote", "get-url", "origin") != ORIGIN:
        raise PackageError("unexpected origin URL")
    expected_root = repository / "artifacts/buildbox" / commit
    if package.parent != expected_root:
        raise PackageError("package is outside the exact Buildbox commit root")

    validate_sums(package)
    build = json.loads(regular(package / "provenance/build.json", "build provenance"))
    for key, expected in (
        ("repository_commit", commit),
        ("repository_dirty", False),
        ("build_profile", PROFILE),
        ("target_architecture", "arm64"),
        ("modules_built", False),
    ):
        if build.get(key) != expected:
            raise PackageError(f"build provenance mismatch: {key}")
    config = regular(package / "kernel.config", "kernel config").decode()
    config_lines = set(config.splitlines())
    for line in REQUIRED_CONFIG:
        if line not in config_lines:
            raise PackageError(f"required configuration missing: {line}")
    for line in FORBIDDEN_CONFIG:
        if line in config_lines:
            raise PackageError(f"forbidden configuration enabled: {line}")
    image = regular(package / "Image", "Image")
    image_gz = regular(package / "Image.gz", "Image.gz")
    if gzip.decompress(image_gz) != image:
        raise PackageError("Image.gz does not reproduce Image")
    system_map = regular(package / "System.map", "System.map").decode()
    for symbol in REQUIRED_SYMBOLS:
        if symbol not in system_map:
            raise PackageError(f"required linked symbol absent: {symbol.strip()}")
    series = regular(package / "provenance/series", "packaged series").decode().splitlines()
    selected = [line for line in series if line and not line.startswith("#")]
    if len(selected) != 505:
        raise PackageError("canonical patch count changed")
    for relative, expected_hash in RESET_PATCHES.items():
        if selected.count(relative) != 1:
            raise PackageError(f"reset patch inventory changed: {relative}")
        packaged = regular(package / "provenance/patches" / relative, relative)
        repository_patch = regular(repository / "patches" / relative, relative)
        if packaged != repository_patch or digest(packaged) != expected_hash:
            raise PackageError(f"reset patch content changed: {relative}")
    return build


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    package = args.package.resolve(strict=True)
    build = validate(repository, package)
    print("validation=mt6797-pwrap-reset-serviceability-package")
    print(f"repository_commit={build['repository_commit']}")
    print(f"build_profile={build['build_profile']}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"patchset_sha256={build['patchset_sha256']}")
    print(f"config_sha256={build['config_sha256']}")
    print("patch_count=505")
    print("hardware_action=none")
    print("boot_candidate=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
