#!/usr/bin/env python3
"""Validate Cassini's exact childless-I2C6 kernel package."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import stat
import sys

sys.dont_write_bytecode = True
import candidate_cassini as cc

FRAGMENTS = (
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
    cc.CONFIG_FRAGMENT,
)

KERNEL_CMDLINE = (
    'CONFIG_CMDLINE="console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr '
    "ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug rdinit=/init "
    "panic=0 g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Cassini "
    "g_ether.iSerialNumber=GEMINI_CASSINI_20260727 "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused initcall_blacklist=mt6797_a72_power_driver_init "
    'fw_devlink=rpm"'
)

REQUIRED_CONFIG = {
    'CONFIG_LOCALVERSION="-gemini-cassini"',
    "# CONFIG_LOCALVERSION_AUTO is not set",
    "CONFIG_CMDLINE_FORCE=y",
    KERNEL_CMDLINE,
    "CONFIG_IKCONFIG=y",
    "CONFIG_IKCONFIG_PROC=y",
    "CONFIG_SMP=y",
    "CONFIG_HOTPLUG_CPU=y",
    "CONFIG_ARM_PSCI_FW=y",
    "CONFIG_ARCH_MEDIATEK=y",
    "CONFIG_OF=y",
    "CONFIG_I2C=y",
    "CONFIG_I2C_CHARDEV=y",
    "CONFIG_I2C_MT65XX=y",
    "CONFIG_PINCTRL_AW9523=y",
    "CONFIG_KEYBOARD_MATRIX=y",
    "CONFIG_REGMAP_I2C=y",
    "CONFIG_REGULATOR=y",
    "# CONFIG_REGULATOR_DA9211 is not set",
    "CONFIG_MFD_SYSCON=y",
    "CONFIG_RESET_CONTROLLER=y",
    "# CONFIG_MTK_MT6797_A72_POWER is not set",
    "CONFIG_MTK_MT6797_DVFSP_HANDOFF=y",
    "CONFIG_KALLSYMS=y",
    "CONFIG_WATCHDOG=y",
    "CONFIG_MEDIATEK_WATCHDOG=y",
    "CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED=y",
    "CONFIG_WATCHDOG_OPEN_TIMEOUT=0",
    "CONFIG_WATCHDOG_SYSFS=y",
    "CONFIG_FB_SIMPLE=y",
    "CONFIG_FRAMEBUFFER_CONSOLE=y",
    "CONFIG_FONT_TER16x32=y",
    "CONFIG_USB_GADGET=y",
    "CONFIG_USB_ETH=y",
    "CONFIG_USB_ETH_RNDIS=y",
    "CONFIG_PSTORE=y",
    "CONFIG_PSTORE_RAM=y",
    "CONFIG_PSTORE_CONSOLE=y",
    "# CONFIG_PSTORE_PMSG is not set",
    "# CONFIG_SUSPEND is not set",
    "# CONFIG_CPU_FREQ is not set",
    "# CONFIG_CPU_IDLE is not set",
    "# CONFIG_THERMAL is not set",
    "# CONFIG_MODULES is not set",
    "# CONFIG_MMC is not set",
    "# CONFIG_MTD is not set",
    "# CONFIG_SCSI is not set",
    "# CONFIG_ATA is not set",
    "# CONFIG_USB_MASS_STORAGE is not set",
}

REQUIRED_IMAGE_MARKERS = (
    b"shared-ap-dma=preserved",
    b"dma_unchanged=%u",
    b"i2c6_policy=requires-ready",
    b"mt6797-dvfsp-handoff",
)

REQUIRED_SYMBOLS = {
    "i2c_dev_init",
    "mt6797_psci_cpu_boot",
    "mt6797_psci_ops",
    "mt6797_dvfsp_handoff_driver_init",
    "mt6797_dvfsp_handoff_require_ready",
    "mtk_i2c_transfer",
}

FORBIDDEN_SYMBOLS = {
    "mt6797_a72_power_cpu_boot_ready",
    "mt6797_a72_power_cpu_on_complete",
    "mt6797_a72_power_cpu_on_failed",
    "mt6797_a72_power_prepare_first",
    "mt6797_a72_power_cpu_startup",
    "mt6797_a72_power_retry_cpu8",
    "da9214_detect_legacy_interface",
    "da9214_read_legacy_page2_reg",
    "da9214_read_signature",
    "mt6797_a72_power_driver_init",
    "da9211_i2c_probe",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def tree_inventory(
    root: pathlib.Path, label: str
) -> dict[str, pathlib.Path]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{label} is missing or unsafe")

    files: dict[str, pathlib.Path] = {}
    directories: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        member_info = path.lstat()
        if path.is_symlink():
            raise ValueError(f"{label} contains symlink: {relative}")
        if stat.S_ISREG(member_info.st_mode):
            if not member_info.st_size:
                raise ValueError(f"{label} contains empty file: {relative}")
            files[relative] = path
        elif stat.S_ISDIR(member_info.st_mode):
            directories.add(relative)
        else:
            raise ValueError(f"{label} contains special member: {relative}")

    expected_directories: set[str] = set()
    for relative in files:
        parent = pathlib.PurePosixPath(relative).parent
        while parent != pathlib.PurePosixPath("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    if directories != expected_directories:
        raise ValueError(f"{label} contains a missing or empty extra directory")
    return files


def series_entries(data: bytes) -> list[str]:
    try:
        lines = data.decode("utf-8").splitlines()
    except UnicodeError as exc:
        raise ValueError("patch series is not UTF-8") from exc
    entries = [line for line in lines if line and not line.startswith("#")]
    if len(entries) != len(set(entries)):
        raise ValueError("patch series contains duplicate entries")
    for entry in entries:
        path = pathlib.PurePosixPath(entry)
        if (
            path.is_absolute()
            or ".." in path.parts
            or len(path.parts) != 2
            or path.parts[0] != "v7.1.3"
            or path.as_posix() != entry
            or any(character.isspace() for character in entry)
            or path.suffix != ".patch"
        ):
            raise ValueError(f"patch series contains unsafe entry: {entry}")
    return entries


def validate_fragment_provenance(
    repository: pathlib.Path, package: pathlib.Path
) -> None:
    by_name = {
        pathlib.PurePosixPath(relative).name: relative
        for relative in FRAGMENTS
    }
    if len(by_name) != len(FRAGMENTS):
        raise ValueError("Cassini fragment basenames collide")
    packaged = tree_inventory(
        package / "provenance/configs", "packaged fragment provenance"
    )
    if set(packaged) != set(by_name):
        raise ValueError("packaged configuration-fragment inventory changed")
    for name, relative in by_name.items():
        repository_data = regular(
            repository / relative, f"repository fragment {relative}"
        )
        packaged_data = regular(
            packaged[name], f"packaged fragment {name}"
        )
        if packaged_data != repository_data:
            raise ValueError(
                f"packaged fragment differs from repository: {relative}"
            )


def validate_patch_provenance(
    repository: pathlib.Path,
    package: pathlib.Path,
    entries: list[str],
) -> None:
    packaged = tree_inventory(
        package / "provenance/patches", "packaged patch provenance"
    )
    if set(packaged) != set(entries):
        raise ValueError("packaged patch inventory differs from selected series")
    for entry in entries:
        repository_data = regular(
            repository / "patches" / entry, f"repository patch {entry}"
        )
        packaged_data = regular(
            packaged[entry], f"packaged patch {entry}"
        )
        if packaged_data != repository_data:
            raise ValueError(
                f"packaged patch differs from repository: {entry}"
            )


def parse_symbols(config: str) -> dict[str, str]:
    symbols: dict[str, str] = {}
    for line in config.splitlines():
        if line.startswith("CONFIG_") and "=" in line:
            symbol = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            symbol = line[2:-11]
        else:
            continue
        if symbol in symbols:
            raise ValueError(f"kernel config duplicates {symbol}")
        symbols[symbol] = line
    return symbols


def validate_config(data: bytes) -> None:
    try:
        config = data.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("kernel configuration is not ASCII") from exc
    lines = set(config.splitlines())
    parse_symbols(config)
    missing = sorted(REQUIRED_CONFIG - lines)
    if missing:
        raise ValueError("Cassini kernel configuration lacks " + missing[0])
    forbidden = {
        "CONFIG_I2C_CHARDEV=m",
        "CONFIG_SUSPEND=y",
        "CONFIG_CPU_IDLE=y",
        "CONFIG_MODULES=y",
    }
    present = sorted(forbidden & lines)
    if present:
        raise ValueError("Cassini kernel configuration enables " + present[0])
    if config.count("maxcpus=8") != 1 or "maxcpus=9" in config:
        raise ValueError("Cassini CPU request boundary changed")
    if config.count("GEMINI_CASSINI_20260727") != 1:
        raise ValueError("Cassini USB attribution marker changed")


def parse_system_map(data: bytes) -> set[str]:
    try:
        return {
            parts[2]
            for line in data.decode("ascii").splitlines()
            if len(parts := line.split(maxsplit=2)) == 3
        }
    except UnicodeError as exc:
        raise ValueError("System.map is not ASCII") from exc


def validate_system_map(data: bytes) -> None:
    symbols = parse_system_map(data)
    missing = sorted(REQUIRED_SYMBOLS - symbols)
    if missing:
        raise ValueError("Cassini System.map lacks " + missing[0])
    present = sorted(FORBIDDEN_SYMBOLS & symbols)
    if present:
        raise ValueError("Cassini contains forbidden active symbol " + present[0])


def validate_image(image: bytes) -> None:
    cmdline_value = KERNEL_CMDLINE.removeprefix(
        'CONFIG_CMDLINE="'
    ).removesuffix('"').encode("ascii")
    if image.count(cmdline_value) != 2:
        raise ValueError(
            "Cassini Image does not contain exactly two full forced-cmdline copies"
        )
    for marker in (
        (
            b"g_ether.iProduct=Gemini-L-Cassini "
            b"g_ether.iSerialNumber=GEMINI_CASSINI_20260727 "
        ),
        b"CPU%u boot rejected: A72 power sequence inactive",
        *REQUIRED_IMAGE_MARKERS,
    ):
        if marker not in image:
            raise ValueError(f"Cassini Image lacks marker {marker!r}")


def validate_package_manifest(package: pathlib.Path) -> None:
    text = regular(package / "SHA256SUMS", "package checksum manifest")
    seen: set[str] = set()
    for line in text.decode("ascii").splitlines():
        if len(line) < 67 or line[64:66] != "  ":
            raise ValueError("malformed package checksum line")
        wanted = line[:64]
        relative = line[66:]
        path = pathlib.PurePosixPath(relative)
        if (
            len(wanted) != 64
            or any(character not in "0123456789abcdef" for character in wanted)
            or path.is_absolute()
            or ".." in path.parts
            or relative in seen
        ):
            raise ValueError("unsafe package checksum entry")
        seen.add(relative)
        if digest(regular(package / relative, f"package member {relative}")) != wanted:
            raise ValueError(f"package checksum failed: {relative}")


def validate(repository: pathlib.Path, package: pathlib.Path) -> None:
    validate_package_manifest(package)
    repository_manifest = regular(
        repository / "kernel/manifest.json", "repository kernel manifest"
    )
    packaged_manifest = regular(
        package / "provenance/kernel-manifest.json",
        "packaged kernel manifest",
    )
    if packaged_manifest != repository_manifest:
        raise ValueError("packaged kernel manifest differs from repository")
    manifest = json.loads(repository_manifest)
    profile = manifest["config"]["profiles"].get(cc.PROFILE)
    if profile != {
        "base": "defconfig",
        "patch_series": cc.SERIES,
        "fragments": list(FRAGMENTS),
    }:
        raise ValueError("Cassini manifest profile changed")
    fragment = regular(repository / cc.CONFIG_FRAGMENT, "Cassini config fragment")
    if digest(fragment) != cc.CONFIG_FRAGMENT_SHA256:
        raise ValueError("source-pinned Cassini config fragment changed")
    repository_series = regular(repository / cc.SERIES, "Cassini patch series")
    if digest(repository_series) != cc.SERIES_SHA256:
        raise ValueError("source-pinned Cassini patch series changed")
    if repository_series != regular(
        package / "provenance/series", "packaged patch series"
    ):
        raise ValueError("packaged patch series differs from repository")
    entries = series_entries(repository_series)
    if (
        len(entries) != 102
        or not entries[-1].endswith(
            "0103-soc-mediatek-preserve-shared-MT6797-AP-DMA-owner.patch"
        )
    ):
        raise ValueError("Cassini is not the exact childless-I2C6 series")
    forbidden_prefixes = ("0093-", "0096-", "0104-", "0105-", "0106-",
                          "0107-", "0108-", "0109-", "0110-", "0111-",
                          "0112-", "0113-")
    if any(pathlib.PurePosixPath(entry).name.startswith(forbidden_prefixes)
           for entry in entries):
        raise ValueError("Cassini series includes DA9214 or active-A72 code")
    validate_patch_provenance(repository, package, entries)
    validate_fragment_provenance(repository, package)

    build = json.loads(
        regular(package / "provenance/build.json", "build provenance")
    )
    if (
        build.get("build_profile") != cc.PROFILE
        or build.get("base_config") != "defconfig"
        or build.get("config_fragments") != list(FRAGMENTS)
    ):
        raise ValueError("package provenance is not exact Cassini")

    config = regular(package / "kernel.config", "kernel config")
    validate_config(config)
    system_map = regular(package / "System.map", "System.map")
    validate_system_map(system_map)
    image = regular(package / "Image", "kernel Image")
    if gzip.decompress(regular(package / "Image.gz", "kernel Image.gz")) != image:
        raise ValueError("Image.gz does not expand to Image")
    validate_image(image)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--package", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        repository = args.repository.resolve(strict=True)
        package = args.package.resolve(strict=True)
        validate(repository, package)
        config = regular(package / "kernel.config", "kernel config")
        image = regular(package / "Image", "kernel Image")
        entries = series_entries(regular(repository / cc.SERIES, "series"))
    except (
        OSError, UnicodeError, ValueError, json.JSONDecodeError, gzip.BadGzipFile
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=cassini-childless-i2c6-package")
    print(f"profile={cc.PROFILE}")
    print(f"patch_series={cc.SERIES}")
    print(f"patch_count={len(entries)}")
    print(f"config_sha256={digest(config)}")
    print(f"image_sha256={digest(image)}")
    print("i2c_chardev=built-in")
    print("i2c6_kernel_clients=none-by-final-dtb-contract")
    print("da9214_legacy_kernel_probe=absent")
    print("active_a72_symbols=absent")
    print("cpu8_cpu9=fail-closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
