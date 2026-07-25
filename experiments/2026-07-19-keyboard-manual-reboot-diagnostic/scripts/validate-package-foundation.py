#!/usr/bin/env python3
"""Validate Candidate X's repository-derived kernel-package foundation."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


PROFILE = "observability-fbcon-rotation-keyboard-wrrd-manual-reboot"
PATCH_COUNT = 87
LAST_PATCH = "v7.1.3/0086-i2c-mediatek-use-MT8173-data-for-MT6797.patch"
EXPECTED_FRAGMENTS = (
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
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
W_CMDLINE = "console=tty2 " + EXPECTED_CMDLINE
W_CONFIG_SHA256 = (
    "e143daa84127e2c04895c2576943dfb77ee10903c35f4d8cc9fe1dc90bf1bebb"
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
HEX256 = re.compile(r"^[0-9a-f]{64}$")
SYSTEM_MAP_MATCH = re.compile(
    r"^[0-9a-fA-F]+\s+[A-Za-z]\s+mtk_i2c_of_match$", re.MULTILINE
)
VIRTUAL_CONSOLE = re.compile(r"^console=tty[0-9]+$")
EXPECTED_PATCHSET_SHA256 = (
    "4cd417adb0d79aad2f021e1f07e47bed4825cb51b3a069e5258ea4eb49ca5ef4"
)


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_file(path: pathlib.Path, label: str) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"{label} is missing, empty, or a symlink: {path}")


def exact_tree_inventory(
    root: pathlib.Path, expected_files: set[str], expected_directories: set[str]
) -> None:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"required provenance directory is invalid: {root}")
    files: set[str] = set()
    directories: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"provenance tree contains a symlink: {relative}")
        if path.is_dir():
            directories.add(relative)
        elif path.is_file():
            files.add(relative)
        else:
            raise ValueError(f"provenance tree contains a non-regular entry: {relative}")
    if files != expected_files or directories != expected_directories:
        missing = sorted(expected_files - files)
        extra = sorted(files - expected_files)
        missing_directories = sorted(expected_directories - directories)
        extra_directories = sorted(directories - expected_directories)
        raise ValueError(
            "provenance tree inventory changed: "
            f"missing={missing[:1]} extra={extra[:1]} "
            f"missing_dirs={missing_directories[:1]} extra_dirs={extra_directories[:1]}"
        )


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    return value


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
    records = [f"{digest(series)}  patches/series\n"]
    for entry in series_entries(series):
        patch = patch_root / entry
        require_file(patch, f"series patch {entry}")
        records.append(f"{digest(patch)}  {entry}\n")
    return hashlib.sha256("".join(records).encode("ascii")).hexdigest()


def config_inputs_digest(repo_root: pathlib.Path) -> str:
    records = [f"profile={PROFILE}\n", "base=defconfig\n"]
    for relative in EXPECTED_FRAGMENTS:
        fragment = repo_root / relative
        require_file(fragment, f"configuration fragment {relative}")
        records.append(f"{digest(fragment)}  {relative}\n")
    return hashlib.sha256("".join(records).encode("ascii")).hexdigest()


def validate_patch_provenance(package: pathlib.Path, repo_root: pathlib.Path) -> str:
    repo_series = repo_root / "patches/series"
    packaged_series = package / "provenance/series"
    require_file(repo_series, "repository patch series")
    require_file(packaged_series, "packaged patch series")
    if packaged_series.read_bytes() != repo_series.read_bytes():
        raise ValueError("packaged patch series differs from repository")
    entries = series_entries(repo_series)
    if len(entries) != PATCH_COUNT or entries[-1] != LAST_PATCH:
        raise ValueError("Candidate X patch-series boundary changed")
    repo_patch_root = repo_root / "patches"
    packaged_patch_root = package / "provenance/patches"
    expected = set(entries)
    expected_directories = {
        pathlib.PurePosixPath(entry).parent.as_posix() for entry in entries
    }
    exact_tree_inventory(packaged_patch_root, expected, expected_directories)
    for entry in entries:
        repository_patch = repo_patch_root / entry
        packaged_patch = packaged_patch_root / entry
        require_file(repository_patch, f"repository patch {entry}")
        require_file(packaged_patch, f"packaged patch {entry}")
        if repository_patch.read_bytes() != packaged_patch.read_bytes():
            raise ValueError(f"packaged patch differs: {entry}")
    repository_hash = patchset_digest(repo_series, repo_patch_root)
    if patchset_digest(packaged_series, packaged_patch_root) != repository_hash:
        raise ValueError("packaged patchset identity changed")
    if repository_hash != EXPECTED_PATCHSET_SHA256:
        raise ValueError("Candidate X exact patchset identity changed")
    return repository_hash


def validate_config_provenance(
    package: pathlib.Path, repo_root: pathlib.Path, manifest: dict[str, Any]
) -> str:
    try:
        profile = manifest["config"]["profiles"][PROFILE]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"manifest lacks profile {PROFILE}") from exc
    if not isinstance(profile, dict) or profile.get("base") != "defconfig":
        raise ValueError("Candidate X profile base changed")
    if profile.get("fragments") != list(EXPECTED_FRAGMENTS):
        raise ValueError("Candidate X ordered fragment stack changed")

    packaged_root = package / "provenance/configs"
    expected_names = {
        pathlib.PurePosixPath(relative).name for relative in EXPECTED_FRAGMENTS
    }
    exact_tree_inventory(packaged_root, expected_names, set())
    for relative in EXPECTED_FRAGMENTS:
        repository = repo_root / relative
        packaged = packaged_root / pathlib.PurePosixPath(relative).name
        require_file(repository, f"repository fragment {relative}")
        require_file(packaged, f"packaged fragment {relative}")
        if repository.read_bytes() != packaged.read_bytes():
            raise ValueError(f"packaged configuration fragment differs: {relative}")
    return config_inputs_digest(repo_root)


def validate_resolved_config(path: pathlib.Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    missing = sorted(REQUIRED_CONFIG - set(lines))
    if missing:
        raise ValueError(f"required resolved configuration is missing: {missing[0]}")
    cmdlines = [line for line in lines if line.startswith("CONFIG_CMDLINE=")]
    if len(cmdlines) != 1:
        raise ValueError("resolved configuration must contain one CONFIG_CMDLINE")
    try:
        command_line = json.loads(cmdlines[0].split("=", 1)[1])
    except json.JSONDecodeError as exc:
        raise ValueError("CONFIG_CMDLINE is not valid quoted text") from exc
    if command_line != EXPECTED_CMDLINE:
        raise ValueError("Candidate X forced command line is not exact")
    tokens = command_line.split()
    if any(VIRTUAL_CONSOLE.fullmatch(token) for token in tokens):
        raise ValueError("Candidate X must not route printk to a virtual console")
    serial_consoles = [token for token in tokens if token.startswith("console=")]
    if serial_consoles != ["console=ttyS0,921600n8"]:
        raise ValueError("Candidate X must retain exactly the fixed serial console")
    x_line = "CONFIG_CMDLINE=" + json.dumps(EXPECTED_CMDLINE)
    w_line = "CONFIG_CMDLINE=" + json.dumps(W_CMDLINE)
    if text.count(x_line) != 1:
        raise ValueError("Candidate X CONFIG_CMDLINE source line is not unique")
    reconstructed_w = text.replace(x_line, w_line, 1).encode("utf-8")
    if hashlib.sha256(reconstructed_w).hexdigest() != W_CONFIG_SHA256:
        raise ValueError(
            "resolved config differs from exact Candidate W beyond CONFIG_CMDLINE"
        )
    return command_line, digest(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.package.is_symlink() or args.manifest.is_symlink():
            raise ValueError("selected package and manifest must not be symlinks")
        package = args.package.resolve(strict=True)
        manifest_path = args.manifest.resolve(strict=True)
        if not package.is_dir():
            raise ValueError("package is not a regular directory")
        repo_root = manifest_path.parent.parent
        required = (
            package / "Image",
            package / "Image.gz",
            package / "System.map",
            package / "kernel.config",
            package / "SHA256SUMS",
            package / "provenance/build.json",
            package / "provenance/kernel-manifest.json",
            package / "provenance/series",
        )
        for path in required:
            require_file(path, "required package input")
        manifest = load_json(manifest_path, "repository manifest")
        if (package / "provenance/kernel-manifest.json").read_bytes() != manifest_path.read_bytes():
            raise ValueError("packaged kernel manifest differs from repository")
        kernel = manifest.get("kernel")
        if (
            manifest.get("architecture") != "arm64"
            or manifest.get("patch_series") != "patches/series"
            or not isinstance(kernel, dict)
            or kernel.get("version") != "7.1.3"
        ):
            raise ValueError("kernel manifest foundation changed")
        source_sha256 = kernel.get("sha256")
        if not isinstance(source_sha256, str) or HEX256.fullmatch(source_sha256) is None:
            raise ValueError("kernel source SHA-256 pin is invalid")

        patchset_sha256 = validate_patch_provenance(package, repo_root)
        config_inputs_sha256 = validate_config_provenance(package, repo_root, manifest)
        command_line, config_sha256 = validate_resolved_config(package / "kernel.config")
        expected_package_name = (
            f"linux-7.1.3-gemini-{PROFILE}-"
            f"{patchset_sha256[:8]}-{config_inputs_sha256[:8]}"
        )
        if package.name != expected_package_name:
            raise ValueError("package basename does not match its selected identities")
        build = load_json(package / "provenance/build.json", "build provenance")
        expected_build = {
            "schema": 1,
            "source_sha256": source_sha256,
            "patchset_sha256": patchset_sha256,
            "config_inputs_sha256": config_inputs_sha256,
            "config_sha256": config_sha256,
            "build_profile": PROFILE,
            "base_config": "defconfig",
            "config_fragments": list(EXPECTED_FRAGMENTS),
            "modules_built": False,
        }
        for key, expected in expected_build.items():
            if build.get(key) != expected:
                raise ValueError(f"build provenance changed: {key}")
        if build.get("kernel_release") != "7.1.3-gemini-observability-L":
            raise ValueError("kernel release changed from the W foundation")
        for key in ("compiler", "linker"):
            if not isinstance(build.get(key), str) or not build[key]:
                raise ValueError(f"build provenance lacks {key} identity")
        image = package / "Image"
        if b"mediatek,mt6797-i2c\x00" not in image.read_bytes():
            raise ValueError("Image lacks built-in direct MT6797 I2C match")
        system_map = (package / "System.map").read_text(
            encoding="ascii", errors="strict"
        )
        if SYSTEM_MAP_MATCH.search(system_map) is None:
            raise ValueError("System.map lacks mtk_i2c_of_match")

        print("validation=candidate-x-package-foundation")
        print(f"package={expected_package_name}")
        print(f"profile={PROFILE}")
        print(f"source_sha256={source_sha256}")
        print(f"patchset_sha256={patchset_sha256}")
        print(f"config_inputs_sha256={config_inputs_sha256}")
        print(f"config_sha256={config_sha256}")
        print(f"command_line={command_line}")
        print("virtual_kernel_console=none")
        print(f"reconstructed_w_config_sha256={W_CONFIG_SHA256}")
        print("resolved_config_delta=CONFIG_CMDLINE-only-remove-console-tty2")
        print("serial_console=ttyS0,921600n8")
        print("font=TER16x32")
        print("watchdog_handle_boot_enabled=yes")
        print("watchdog_open_timeout=0")
        print("hardware_write=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
