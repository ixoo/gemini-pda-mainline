#!/usr/bin/env python3
"""Validate Candidate V's complete corrected polling-package foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys


PROFILE = "observability-fbcon-rotation-keyboard-polling"
P_PROFILE = "observability-fbcon-rotation"
PACKAGE_BASENAME = (
    "linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-polling-"
    "5f9f1dcf-b727350a"
)
KEYBOARD_FRAGMENT = "configs/gemini-keyboard.fragment"
CONFIG_SHA256 = "63c1012cc87d517dbd072fae59b0e20064649a4572501a42e63d8311ae10aeaa"
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
PATCHSET_SHA256 = "5f9f1dcf746de55a6a258803f4a9c214fc287c0a9d39e738e9f15b8a503544c5"
CONFIG_INPUTS_SHA256 = "b727350adffb6fc20c825608d391b10c1fafd85b4591cf48f8a1d372ed69368a"
PACKAGE_DTB_SHA256 = "f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5"
PACKAGE_SUMS_SHA256 = "22193d6149579be5c9e34d20db88853e55e46f1490c5f85314504bbe0e6ce257"
IMAGE_SHA256 = "202aef6bcec0458cfad077fb08bcdbb4fe3ef3a836538a21faf2f9f6b4d9eda2"
IMAGE_GZ_SHA256 = "69095483a984eb05a94e5ae212aeeb87cc3ffbded2d753f09f89661972ed89a3"
SYSTEM_MAP_SHA256 = "f63ac8143fe840119407030513838d8be6b1bb478f55d191498073cf57097d25"
BUILD_JSON_SHA256 = "3b35cfc1d3bb3d5556aefde404b433ce66aad292c65707a48af1c1e8cde4660a"
MATRIX_PATCH = "v7.1.3/0084-Input-matrix-keypad-add-optional-polling-mode.patch"
MATRIX_PATCH_SHA256 = "4a183e91b07fb5d62e005d94bf1b416c798555945b93047b5619ceca4a0d09de"
PATCH_COUNT = 86
KERNEL_RELEASE = "7.1.3-gemini-observability-L"
COMPILER = "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
LINKER = "GNU ld (GNU Binutils for Ubuntu) 2.42"
MANIFEST_SHA256 = "e058053f9b706f5cfd668688bf4baee8cc5be584f1a6c6c0c23039c11740e137"
SERIES_SHA256 = "592289c83de2598c34935223c5784f4a85d9df91154ee40af22fb5ba28adc8ab"
HEX256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_CONFIG = {
    "CONFIG_I2C=y",
    "CONFIG_I2C_MT65XX=y",
    "CONFIG_PINCTRL_AW9523=y",
    "CONFIG_KEYBOARD_MATRIX=y",
    "CONFIG_INPUT=y",
    "CONFIG_INPUT_EVDEV=y",
    "CONFIG_INPUT_KEYBOARD=y",
    "CONFIG_INPUT_MATRIXKMAP=y",
    "CONFIG_GPIOLIB=y",
    "CONFIG_GPIOLIB_IRQCHIP=y",
    "CONFIG_EINT_MTK=y",
    "CONFIG_PINCTRL_MT6797=y",
    "CONFIG_REGMAP_I2C=y",
    "CONFIG_TTY=y",
    "CONFIG_VT=y",
    "CONFIG_VT_CONSOLE=y",
    "CONFIG_FB_SIMPLE=y",
    "CONFIG_FRAMEBUFFER_CONSOLE=y",
    "CONFIG_FRAMEBUFFER_CONSOLE_ROTATION=y",
    "CONFIG_FONT_8x16=y",
    "CONFIG_CMDLINE_FORCE=y",
    "CONFIG_PSTORE=y",
    "CONFIG_PSTORE_RAM=y",
    "CONFIG_PSTORE_CONSOLE=y",
    "# CONFIG_PSTORE_PMSG is not set",
    "# CONFIG_PSTORE_COMPRESS is not set",
    "CONFIG_WATCHDOG=y",
    "CONFIG_WATCHDOG_SYSFS=y",
    "CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y",
    "CONFIG_WATCHDOG_OPEN_TIMEOUT=0",
    "CONFIG_MEDIATEK_WATCHDOG=y",
    "# CONFIG_WATCHDOG_HRTIMER_PRETIMEOUT is not set",
    "# CONFIG_MODULES is not set",
    "# CONFIG_I2C_CHARDEV is not set",
    "# CONFIG_DEVMEM is not set",
    "# CONFIG_MMC is not set",
}


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_hex(value: str, label: str) -> None:
    if HEX256.fullmatch(value) is None:
        raise ValueError(f"{label} is not a lowercase SHA-256")


def validate_package_manifest(package: pathlib.Path) -> None:
    manifest_path = package / "SHA256SUMS"
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    listed: dict[str, str] = {}
    for line in lines:
        try:
            expected, relative = line.split("  ", 1)
        except ValueError as exc:
            raise ValueError("malformed package SHA256SUMS line") from exc
        require_hex(expected, "package manifest digest")
        if relative.startswith("./"):
            relative = relative[2:]
        candidate = pathlib.PurePosixPath(relative)
        if (
            not relative
            or candidate.is_absolute()
            or ".." in candidate.parts
            or relative in listed
            or relative == "SHA256SUMS"
        ):
            raise ValueError(f"unsafe or duplicate package manifest path: {relative}")
        listed[relative] = expected

    actual = {
        path.relative_to(package).as_posix()
        for path in package.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if set(listed) != actual:
        missing = sorted(actual - set(listed))
        extra = sorted(set(listed) - actual)
        raise ValueError(
            f"package manifest inventory mismatch: missing={missing[:1]} extra={extra[:1]}"
        )
    for relative, expected in listed.items():
        if digest(package / relative) != expected:
            raise ValueError(f"package checksum mismatch: {relative}")


def series_entries(series: pathlib.Path) -> list[str]:
    entries: list[str] = []
    for number, line in enumerate(
        series.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line or line.startswith("#"):
            continue
        candidate = pathlib.PurePosixPath(line)
        if (
            any(character.isspace() for character in line)
            or candidate.is_absolute()
            or ".." in candidate.parts
            or len(candidate.parts) < 2
        ):
            raise ValueError(f"unsafe patch series entry at line {number}")
        entries.append(line)
    if len(entries) != len(set(entries)):
        raise ValueError("duplicate patch series entry")
    return entries


def validate_packaged_patches(package: pathlib.Path, repo_root: pathlib.Path) -> None:
    packaged_series = package / "provenance/series"
    repo_series = repo_root / "patches/series"
    if packaged_series.read_bytes() != repo_series.read_bytes():
        raise ValueError("packaged patch series differs from repository input")
    entries = series_entries(packaged_series)
    if len(entries) != PATCH_COUNT:
        raise ValueError(f"patch series count is not exactly {PATCH_COUNT}")
    expected_paths = {pathlib.PurePosixPath(entry).as_posix() for entry in entries}
    packaged_root = package / "provenance/patches"
    actual_paths = {
        path.relative_to(packaged_root).as_posix()
        for path in packaged_root.rglob("*")
        if path.is_file()
    }
    if actual_paths != expected_paths:
        raise ValueError("packaged patch inventory differs from exact series")

    records = [f"{digest(packaged_series)}  patches/series\n"]
    for entry in entries:
        packaged_patch = packaged_root / entry
        repo_patch = repo_root / "patches" / entry
        if packaged_patch.read_bytes() != repo_patch.read_bytes():
            raise ValueError(f"packaged patch differs from repository: {entry}")
        records.append(f"{digest(packaged_patch)}  {entry}\n")
    calculated = hashlib.sha256("".join(records).encode("ascii")).hexdigest()
    if calculated != PATCHSET_SHA256:
        raise ValueError(f"recomputed packaged patchset hash mismatch: {calculated}")
    if digest(packaged_root / MATRIX_PATCH) != MATRIX_PATCH_SHA256:
        raise ValueError("packaged corrected polling patch hash mismatch")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        package = args.package.resolve(strict=True)
        if package.name != PACKAGE_BASENAME:
            raise ValueError("package basename is not the selected corrected build")
        manifest_path = args.manifest.resolve(strict=True)
        repo_root = manifest_path.parent.parent
        if digest(manifest_path) != MANIFEST_SHA256:
            raise ValueError("repository kernel manifest hash changed")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        build_json_path = package / "provenance/build.json"
        build = json.loads(build_json_path.read_text(encoding="utf-8"))
        required_files = (
            package / "Image",
            package / "Image.gz",
            package / "System.map",
            package / "kernel.config",
            package / "dtbs/mediatek/mt6797-gemini-pda.dtb",
            build_json_path,
            package / "provenance/kernel-manifest.json",
            package / "provenance/series",
            package / "SHA256SUMS",
        )
        for path in required_files:
            if not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f"required package file is missing: {path.name}")
        validate_package_manifest(package)

        pinned_files = (
            (package / "SHA256SUMS", PACKAGE_SUMS_SHA256, "package SHA256SUMS"),
            (package / "Image", IMAGE_SHA256, "Image"),
            (package / "Image.gz", IMAGE_GZ_SHA256, "Image.gz"),
            (package / "System.map", SYSTEM_MAP_SHA256, "System.map"),
            (build_json_path, BUILD_JSON_SHA256, "build.json"),
        )
        for path, expected, label in pinned_files:
            if digest(path) != expected:
                raise ValueError(f"{label} is not the selected corrected build")

        package_dtb = package / "dtbs/mediatek/mt6797-gemini-pda.dtb"
        config = package / "kernel.config"
        if digest(package_dtb) != PACKAGE_DTB_SHA256:
            raise ValueError("package DTB hash mismatch")
        if digest(config) != CONFIG_SHA256:
            raise ValueError("resolved config is not the exact polling profile")
        if build.get("kernel_release") != KERNEL_RELEASE:
            raise ValueError("kernel release is not exact")
        if build.get("build_profile") != PROFILE:
            raise ValueError("package profile is not the polling profile")
        if build.get("base_config") != "defconfig":
            raise ValueError("package base config is not exact")
        if build.get("modules_built") is not False:
            raise ValueError("package unexpectedly built modules")
        if build.get("source_sha256") != SOURCE_SHA256:
            raise ValueError("kernel source hash disagrees with pinned manifest")
        if manifest["kernel"]["sha256"] != SOURCE_SHA256:
            raise ValueError("repository kernel source pin changed")
        if build.get("patchset_sha256") != PATCHSET_SHA256:
            raise ValueError("package patchset is not the explicitly selected correction")
        if build.get("config_sha256") != CONFIG_SHA256:
            raise ValueError("package provenance config hash mismatch")
        if build.get("config_inputs_sha256") != CONFIG_INPUTS_SHA256:
            raise ValueError("package config-input hash mismatch")
        if build.get("compiler") != COMPILER or build.get("linker") != LINKER:
            raise ValueError("package toolchain identity changed")

        package_manifest = package / "provenance/kernel-manifest.json"
        if package_manifest.read_bytes() != manifest_path.read_bytes():
            raise ValueError("packaged kernel manifest differs from repository input")
        if digest(package_manifest) != MANIFEST_SHA256:
            raise ValueError("packaged kernel manifest hash changed")
        validate_packaged_patches(package, repo_root)
        if digest(package / "provenance/series") != SERIES_SHA256:
            raise ValueError("packaged series hash changed")

        profile = manifest["config"]["profiles"][PROFILE]
        parent = manifest["config"]["profiles"][P_PROFILE]
        if (
            profile["base"] != parent["base"]
            or profile["fragments"] != parent["fragments"] + [KEYBOARD_FRAGMENT]
        ):
            raise ValueError("polling profile is not exact P plus keyboard fragment")
        if build.get("config_fragments") != profile["fragments"]:
            raise ValueError("package config fragment order changed")
        config_records = [f"profile={PROFILE}\n", f"base={profile['base']}\n"]
        for fragment in profile["fragments"]:
            repo_fragment = repo_root / fragment
            packaged_fragment = package / "provenance" / fragment
            if packaged_fragment.read_bytes() != repo_fragment.read_bytes():
                raise ValueError(f"packaged config fragment differs: {fragment}")
            config_records.append(f"{digest(packaged_fragment)}  {fragment}\n")
        calculated_config_inputs = hashlib.sha256(
            "".join(config_records).encode("ascii")
        ).hexdigest()
        if calculated_config_inputs != CONFIG_INPUTS_SHA256:
            raise ValueError(
                f"recomputed package config-input hash mismatch: {calculated_config_inputs}"
            )

        config_lines = set(config.read_text(encoding="utf-8").splitlines())
        missing = sorted(REQUIRED_CONFIG - config_lines)
        if missing:
            raise ValueError(f"required resolved config line missing: {missing[0]}")
        cmdline = next(
            line for line in config_lines if line.startswith("CONFIG_CMDLINE=")
        )
        for token in (
            "maxcpus=1",
            "panic=0",
            "clk_ignore_unused",
            "fbcon=rotate:3",
            "consoleblank=0",
            "rdinit=/init",
        ):
            if f" {token}" not in cmdline:
                raise ValueError(f"forced command line missing: {token}")

        print("validation=candidate-v-corrected-package-foundation")
        print(f"package={PACKAGE_BASENAME}")
        print(f"build_profile={PROFILE}")
        print(f"package_sums_sha256={PACKAGE_SUMS_SHA256}")
        print(f"image_sha256={IMAGE_SHA256}")
        print(f"image_gz_sha256={IMAGE_GZ_SHA256}")
        print(f"system_map_sha256={SYSTEM_MAP_SHA256}")
        print(f"build_json_sha256={BUILD_JSON_SHA256}")
        print(f"package_dtb_sha256={PACKAGE_DTB_SHA256}")
        print(f"patchset_sha256={PATCHSET_SHA256}")
        print(f"matrix_patch_sha256={MATRIX_PATCH_SHA256}")
        print(f"patch_count={PATCH_COUNT}")
        print(f"config_inputs_sha256={CONFIG_INPUTS_SHA256}")
        print(f"manifest_sha256={MANIFEST_SHA256}")
        print(f"series_sha256={SERIES_SHA256}")
        print(f"config_sha256={CONFIG_SHA256}")
        print("package_manifest=complete-and-valid")
        print("profile_boundary=exact-p-plus-keyboard-fragment")
        print("cpu_policy=maxcpus-1")
        print("hardware_write=none")
        return 0
    except (OSError, KeyError, StopIteration, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
