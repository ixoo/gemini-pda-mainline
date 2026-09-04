#!/usr/bin/env python3
"""Validate the exact live-model-repaired thermal production package."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import stat
import subprocess
from pathlib import Path, PurePosixPath


ORIGIN = "https://github.com/ixoo/gemini-pda-mainline.git"
BUILD_COMMIT = "08fd54667c620649938f2b500779e59f4d4b8762"
PROFILE = "mt6797-thermal-stage-ledger"
KERNEL_RELEASE = "7.1.3-gemini-mt6797-thermal-stage-ledger"
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
PATCHSET_SHA256 = "eb29842d5afde20cc6cf0f0f3cbfb7b4b3277d48c79f082803931675c0cc57c6"
CONFIG_SHA256 = "f0a135b24055229447d56ae6bda16e1ada683ebe4612af3ba0b96ec7febd375a"
IMAGE_SHA256 = "7a8b6fb281420d0d3c5c60df1c6072c50df6f3650b46b000ae6599e3d099c2f6"
IMAGE_GZ_SHA256 = "71104199d99e2be3ac6b42867763d5e74ba8474019f2f47d33c1fc8ac44f8b12"
SYSTEM_MAP_SHA256 = "041d6efae789aadf6a2dc1aaaa980e8ce76f465273dc7d160630d9a73d094a0d"
PARENT_VALIDATOR_SHA256 = "0bec8097f36e2831a19239810d4faf2d1f74fe480f80e9391ecad703ccdf9191"
PATCH = "v7.1.3/0524-pstore-match-Gemini-thermal-ledger-after-LK-model-rewrite.patch"
PATCH_SHA256 = "c99d16ced8952df6c8c6eefa27304e9bfe6e3685bef6f3e554f58fa79a022e03"
PATCH_COUNT = 513


class PackageError(ValueError):
    """Raised when the exact package contract is not met."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise PackageError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_parent(repository: Path):
    path = repository / "experiments/2026-09-04-mt6797-thermal-stage-ledger/scripts/validate_package.py"
    data = regular(path, "parent package validator")
    if digest(data) != PARENT_VALIDATOR_SHA256:
        raise PackageError("parent package validator identity changed")
    spec = importlib.util.spec_from_file_location("thermal_parent_validator", path)
    if spec is None or spec.loader is None:
        raise PackageError("could not load parent package validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_sums(package: Path) -> None:
    lines = regular(package / "SHA256SUMS", "package checksums").decode().splitlines()
    seen: set[str] = set()
    for line in lines:
        expected, marker, relative = line.partition("  ")
        path = PurePosixPath(relative)
        if (marker != "  " or len(expected) != 64 or path.is_absolute()
                or ".." in path.parts or relative in seen):
            raise PackageError("malformed package checksum line")
        seen.add(relative)
        if digest(regular(package / path, f"package member {relative}")) != expected:
            raise PackageError(f"package checksum mismatch: {relative}")


def validate(repository: Path, package: Path) -> dict[str, object]:
    if package.is_symlink() or not package.is_dir():
        raise PackageError("package directory is missing or unsafe")
    if subprocess.check_output(
        ["git", "-C", str(repository), "remote", "get-url", "origin"], text=True
    ).strip() != ORIGIN:
        raise PackageError("unexpected origin URL")
    if subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor",
         BUILD_COMMIT, "origin/main"], check=False,
    ).returncode != 0:
        raise PackageError("build commit is not published at origin/main")
    if package.parent != repository / "artifacts/buildbox" / BUILD_COMMIT:
        raise PackageError("package is outside the exact Buildbox commit root")

    parent = load_parent(repository)
    manifest = json.loads(regular(repository / "kernel/manifest.json", "manifest"))
    expected_profile = {
        "base": "defconfig",
        "patch_series": "patches/series",
        "fragments": parent.FRAGMENTS,
    }
    if manifest["config"]["profiles"].get(PROFILE) != expected_profile:
        raise PackageError("manifest profile changed")

    validate_sums(package)
    build = json.loads(regular(package / "provenance/build.json", "build provenance"))
    for key, expected in (
        ("repository_commit", BUILD_COMMIT),
        ("repository_dirty", False),
        ("build_profile", PROFILE),
        ("kernel_release", KERNEL_RELEASE),
        ("source_sha256", SOURCE_SHA256),
        ("patchset_sha256", PATCHSET_SHA256),
        ("config_sha256", CONFIG_SHA256),
        ("target_architecture", "arm64"),
        ("modules_built", False),
    ):
        if build.get(key) != expected:
            raise PackageError(f"build provenance mismatch: {key}")

    config = regular(package / "kernel.config", "kernel config")
    if digest(config) != CONFIG_SHA256:
        raise PackageError("kernel config identity changed")
    config_lines = set(config.decode().splitlines())
    for line in parent.REQUIRED_CONFIG:
        if line not in config_lines:
            raise PackageError(f"required configuration missing: {line}")
    for line in parent.FORBIDDEN_CONFIG:
        if line in config_lines:
            raise PackageError(f"forbidden configuration enabled: {line}")

    image = regular(package / "Image", "Image")
    image_gz = regular(package / "Image.gz", "Image.gz")
    system_map_data = regular(package / "System.map", "System.map")
    if digest(image) != IMAGE_SHA256 or digest(image_gz) != IMAGE_GZ_SHA256:
        raise PackageError("pinned kernel image identity changed")
    if digest(system_map_data) != SYSTEM_MAP_SHA256:
        raise PackageError("pinned System.map identity changed")
    if gzip.decompress(image_gz) != image:
        raise PackageError("Image.gz does not reproduce Image")
    system_map = system_map_data.decode()
    for symbol in parent.REQUIRED_SYMBOLS:
        if symbol not in system_map:
            raise PackageError(f"required linked symbol absent: {symbol.strip()}")

    series = regular(package / "provenance/series", "packaged series").decode().splitlines()
    selected = [line for line in series if line and not line.startswith("#")]
    if len(selected) != PATCH_COUNT or selected[-1] != PATCH:
        raise PackageError("canonical patch count or terminal patch changed")
    thermal_patches = dict(parent.THERMAL_PATCHES)
    thermal_patches[PATCH] = PATCH_SHA256
    for relative, expected_hash in thermal_patches.items():
        if selected.count(relative) != 1:
            raise PackageError(f"thermal patch inventory changed: {relative}")
        packaged = regular(package / "provenance/patches" / relative, relative)
        repository_patch = regular(repository / "patches" / relative, relative)
        if packaged != repository_patch or digest(packaged) != expected_hash:
            raise PackageError(f"thermal patch content changed: {relative}")
    parent.validate_dtbs(package)
    return build


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    build = validate(args.repository.resolve(strict=True), args.package.resolve(strict=True))
    print("validation=mt6797-thermal-ledger-live-model-repair-package")
    print(f"repository_commit={build['repository_commit']}")
    print(f"build_profile={build['build_profile']}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"source_sha256={build['source_sha256']}")
    print(f"patchset_sha256={build['patchset_sha256']}")
    print(f"config_sha256={build['config_sha256']}")
    print(f"image_sha256={IMAGE_SHA256}")
    print(f"image_gz_sha256={IMAGE_GZ_SHA256}")
    print(f"system_map_sha256={SYSTEM_MAP_SHA256}")
    print(f"patch_count={PATCH_COUNT}")
    print("hardware_action=none")
    print("boot_candidate=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
