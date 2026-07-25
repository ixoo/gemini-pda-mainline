#!/usr/bin/env python3
"""Validate the exact Candidate AB kernel package and repository provenance."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

from ab_contract import (
    COMPILER,
    CONFIG_INPUTS_SHA256,
    CONFIG_SHA256,
    EXPECTED_FRAGMENTS,
    HEX256,
    IMAGE_GZ_SHA256,
    IMAGE_SHA256,
    KERNEL_BUILD_SCRIPT_SHA256,
    KERNEL_MANIFEST_SHA256,
    KERNEL_RELEASE,
    LAST_PATCH,
    LINKER,
    PACKAGE_DTB_SHA256,
    PACKAGE_FILE_PAIRS,
    PACKAGE_NAME,
    PATCHSET_SHA256,
    PATCH_0087_SHA256,
    PATCH_COUNT,
    PROFILE,
    SERIES_SHA256,
    SOURCE_SHA256,
    SYSTEM_MAP_SHA256,
    digest_bytes,
    digest_path,
    read_regular,
    require_package_calibration,
)


EXPECTED_CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=1 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32"
)
REQUIRED_CONFIG = frozenset(
    {
        "CONFIG_I2C=y",
        "CONFIG_I2C_MT65XX=y",
        "CONFIG_REGMAP_I2C=y",
        "CONFIG_PINCTRL_AW9523=y",
        "CONFIG_KEYBOARD_MATRIX=y",
        "CONFIG_VT=y",
        "CONFIG_VT_CONSOLE=y",
        "CONFIG_DUMMY_CONSOLE=y",
        "CONFIG_FRAMEBUFFER_CONSOLE=y",
        "CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y",
        "CONFIG_FONT_TER16x32=y",
        "CONFIG_PSTORE=y",
        "CONFIG_PSTORE_RAM=y",
        "CONFIG_PSTORE_CONSOLE=y",
        "CONFIG_WATCHDOG=y",
        "CONFIG_MEDIATEK_WATCHDOG=y",
        "CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y",
        "CONFIG_WATCHDOG_OPEN_TIMEOUT=0",
        "CONFIG_CMDLINE_FORCE=y",
        "# CONFIG_MODULES is not set",
        "# CONFIG_I2C_CHARDEV is not set",
        "# CONFIG_MMC is not set",
        "# CONFIG_MTD is not set",
        "# CONFIG_SCSI is not set",
        "# CONFIG_ATA is not set",
        "# CONFIG_USB_MASS_STORAGE is not set",
    }
)


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    data = read_regular(path, label)
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    return value


def require_file(path: pathlib.Path, label: str) -> None:
    if path.is_symlink() or not path.is_file() or not path.stat().st_size:
        raise ValueError(f"{label} is missing, empty, or a symlink")


def exact_tree_inventory(
    root: pathlib.Path, expected_files: set[str], expected_directories: set[str]
) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"invalid provenance directory: {root}")
    files: set[str] = set()
    directories: set[str] = set()
    for item in root.rglob("*"):
        relative = item.relative_to(root).as_posix()
        if item.is_symlink():
            raise ValueError(f"provenance tree contains symlink: {relative}")
        if item.is_dir():
            directories.add(relative)
        elif item.is_file():
            files.add(relative)
        else:
            raise ValueError(f"provenance tree contains special entry: {relative}")
    if files != expected_files or directories != expected_directories:
        raise ValueError("provenance tree inventory changed")


def series_entries(path: pathlib.Path) -> list[str]:
    entries: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#"):
            continue
        candidate = pathlib.PurePosixPath(line)
        if (
            any(character.isspace() for character in line)
            or candidate.is_absolute()
            or ".." in candidate.parts
            or len(candidate.parts) < 2
        ):
            raise ValueError(f"unsafe patch-series entry at line {number}")
        entries.append(line)
    if len(entries) != len(set(entries)):
        raise ValueError("duplicate patch-series entry")
    return entries


def patchset_digest(series: pathlib.Path, patch_root: pathlib.Path) -> str:
    records = [f"{digest_path(series)}  patches/series\n"]
    for entry in series_entries(series):
        patch = patch_root / entry
        require_file(patch, f"series patch {entry}")
        records.append(f"{digest_path(patch)}  {entry}\n")
    return hashlib.sha256("".join(records).encode("ascii")).hexdigest()


def config_inputs_digest(repo_root: pathlib.Path) -> str:
    records = [f"profile={PROFILE}\n", "base=defconfig\n"]
    for relative in EXPECTED_FRAGMENTS:
        path = repo_root / relative
        require_file(path, f"configuration fragment {relative}")
        records.append(f"{digest_path(path)}  {relative}\n")
    return hashlib.sha256("".join(records).encode("ascii")).hexdigest()


def validate_package_manifest(package: pathlib.Path) -> None:
    manifest = read_regular(package / "SHA256SUMS", "package SHA256SUMS")
    seen: set[str] = set()
    for line in manifest.decode("ascii").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or HEX256.fullmatch(fields[0]) is None:
            raise ValueError("malformed package checksum manifest")
        relative = fields[1].removeprefix("*").removeprefix("./")
        pure = pathlib.PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or relative in seen:
            raise ValueError("unsafe or duplicate package checksum path")
        seen.add(relative)
        path = package / relative
        require_file(path, f"manifest member {relative}")
        if digest_path(path) != fields[0]:
            raise ValueError(f"package checksum mismatch: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        require_package_calibration()
        if args.package.is_symlink() or not args.package.is_dir():
            raise ValueError("selected package is not a regular directory")
        package = args.package.resolve(strict=True)
        manifest_path = args.manifest.resolve(strict=True)
        if package.name != PACKAGE_NAME:
            raise ValueError("package basename is not exact Candidate AB")
        repo_root = manifest_path.parent.parent

        required = (
            package / "Image",
            package / "Image.gz",
            package / "System.map",
            package / "kernel.config",
            package / "SHA256SUMS",
            package / "dtbs/mediatek/mt6797-gemini-pda.dtb",
            package / "provenance/build.json",
            package / "provenance/kernel-manifest.json",
            package / "provenance/series",
        )
        for path in required:
            require_file(path, "required package input")
        validate_package_manifest(package)

        raw_pair = (
            digest_path(package / "provenance/build.json"),
            digest_path(package / "SHA256SUMS"),
        )
        if raw_pair not in PACKAGE_FILE_PAIRS:
            raise ValueError("package build.json/SHA256SUMS pair is not calibrated")

        exact_files = (
            (package / "Image", IMAGE_SHA256),
            (package / "Image.gz", IMAGE_GZ_SHA256),
            (package / "System.map", SYSTEM_MAP_SHA256),
            (package / "kernel.config", CONFIG_SHA256),
            (package / "dtbs/mediatek/mt6797-gemini-pda.dtb", PACKAGE_DTB_SHA256),
        )
        for path, expected in exact_files:
            if digest_path(path) != expected:
                raise ValueError(f"exact Candidate AB package payload changed: {path.name}")
        if gzip.decompress((package / "Image.gz").read_bytes()) != (
            package / "Image"
        ).read_bytes():
            raise ValueError("Image.gz does not expand to exact packaged Image")

        repository_manifest = load_json(manifest_path, "repository kernel manifest")
        if digest_path(manifest_path) != KERNEL_MANIFEST_SHA256:
            raise ValueError("repository kernel manifest identity changed")
        kernel_build_script = repo_root / "scripts/kernel"
        if digest_path(kernel_build_script) != KERNEL_BUILD_SCRIPT_SHA256:
            raise ValueError("reproducible kernel build script identity changed")
        if kernel_build_script.read_text(encoding="utf-8").count(
            "export KBUILD_BUILD_VERSION=1"
        ) != 1:
            raise ValueError("kernel build-number reproducibility pin changed")
        if (package / "provenance/kernel-manifest.json").read_bytes() != manifest_path.read_bytes():
            raise ValueError("packaged kernel manifest differs from repository")
        kernel = repository_manifest.get("kernel")
        if (
            repository_manifest.get("architecture") != "arm64"
            or repository_manifest.get("patch_series") != "patches/series"
            or not isinstance(kernel, dict)
            or kernel.get("version") != "7.1.3"
            or kernel.get("sha256") != SOURCE_SHA256
        ):
            raise ValueError("kernel manifest foundation changed")

        repo_series = repo_root / "patches/series"
        packaged_series = package / "provenance/series"
        if digest_path(repo_series) != SERIES_SHA256 or packaged_series.read_bytes() != repo_series.read_bytes():
            raise ValueError("repository or packaged patch series changed")
        entries = series_entries(repo_series)
        if len(entries) != PATCH_COUNT or entries[-1] != LAST_PATCH:
            raise ValueError("Candidate AB patch-series boundary changed")
        repo_patches = repo_root / "patches"
        packaged_patches = package / "provenance/patches"
        expected_patch_files = set(entries)
        expected_patch_dirs = {
            pathlib.PurePosixPath(entry).parent.as_posix() for entry in entries
        }
        exact_tree_inventory(packaged_patches, expected_patch_files, expected_patch_dirs)
        for entry in entries:
            if (packaged_patches / entry).read_bytes() != (repo_patches / entry).read_bytes():
                raise ValueError(f"packaged patch differs from repository: {entry}")
        if digest_path(repo_patches / LAST_PATCH) != PATCH_0087_SHA256:
            raise ValueError("patch 0087 identity changed")
        if patchset_digest(repo_series, repo_patches) != PATCHSET_SHA256:
            raise ValueError("Candidate AB patchset identity changed")

        try:
            profile = repository_manifest["config"]["profiles"][PROFILE]
        except (KeyError, TypeError) as exc:
            raise ValueError("kernel manifest lacks Candidate AB profile") from exc
        if profile != {"base": "defconfig", "fragments": list(EXPECTED_FRAGMENTS)}:
            raise ValueError("Candidate AB profile definition changed")
        packaged_configs = package / "provenance/configs"
        expected_config_files = {
            pathlib.PurePosixPath(relative).name for relative in EXPECTED_FRAGMENTS
        }
        exact_tree_inventory(packaged_configs, expected_config_files, set())
        for relative in EXPECTED_FRAGMENTS:
            repository = repo_root / relative
            packaged = packaged_configs / pathlib.PurePosixPath(relative).name
            if packaged.read_bytes() != repository.read_bytes():
                raise ValueError(f"packaged config fragment differs: {relative}")
        if config_inputs_digest(repo_root) != CONFIG_INPUTS_SHA256:
            raise ValueError("Candidate AB configuration input identity changed")

        config_text = (package / "kernel.config").read_text(encoding="utf-8")
        missing = sorted(REQUIRED_CONFIG - set(config_text.splitlines()))
        if missing:
            raise ValueError(f"required resolved configuration is missing: {missing[0]}")
        cmdline_rows = [
            line for line in config_text.splitlines() if line.startswith("CONFIG_CMDLINE=")
        ]
        if len(cmdline_rows) != 1 or json.loads(cmdline_rows[0].split("=", 1)[1]) != EXPECTED_CMDLINE:
            raise ValueError("Candidate AB forced command line changed")
        if re.search(r"(?:^| )console=tty[0-9]+(?: |$)", EXPECTED_CMDLINE):
            raise ValueError("Candidate AB unexpectedly routes printk to a virtual console")

        build = load_json(package / "provenance/build.json", "package build provenance")
        expected_build = {
            "schema": 1,
            "kernel_release": KERNEL_RELEASE,
            "build_profile": PROFILE,
            "base_config": "defconfig",
            "config_fragments": list(EXPECTED_FRAGMENTS),
            "config_inputs_sha256": CONFIG_INPUTS_SHA256,
            "source_sha256": SOURCE_SHA256,
            "patchset_sha256": PATCHSET_SHA256,
            "config_sha256": CONFIG_SHA256,
            "modules_built": False,
            "compiler": COMPILER,
            "linker": LINKER,
        }
        for key, expected in expected_build.items():
            if build.get(key) != expected:
                raise ValueError(f"package build provenance changed: {key}")
        generated = build.get("generated_utc")
        if not isinstance(generated, str) or re.fullmatch(
            r"20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", generated
        ) is None:
            raise ValueError("package build provenance has invalid generated_utc")

        print("validation=exact-candidate-ab-kernel-package")
        print(f"package={PACKAGE_NAME}")
        print(f"source_sha256={SOURCE_SHA256}")
        print(f"patchset_sha256={PATCHSET_SHA256}")
        print(f"series_sha256={SERIES_SHA256}")
        print(f"patch_0087_sha256={PATCH_0087_SHA256}")
        print(f"config_inputs_sha256={CONFIG_INPUTS_SHA256}")
        print(f"config_sha256={CONFIG_SHA256}")
        print(f"image_sha256={IMAGE_SHA256}")
        print(f"image_gz_sha256={IMAGE_GZ_SHA256}")
        print(f"system_map_sha256={SYSTEM_MAP_SHA256}")
        print(f"package_dtb_sha256={PACKAGE_DTB_SHA256}")
        print(f"build_json_sha256={raw_pair[0]}")
        print(f"package_sums_sha256={raw_pair[1]}")
        print("restart_priority=MT6797-255,other-MediaTek-128")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError, gzip.BadGzipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
