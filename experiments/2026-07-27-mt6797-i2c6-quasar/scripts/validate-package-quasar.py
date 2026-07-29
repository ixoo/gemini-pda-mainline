#!/usr/bin/env python3
"""Validate Candidate Quasar's exact kernel package and fail-closed DT."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True
import candidate_quasar as co


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
    co.CONFIG_FRAGMENT,
)
GEMINI_DTB = "dtbs/mediatek/mt6797-gemini-pda.dtb"
FDT_PARSER_SHA256 = (
    "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"
)
KERNEL_CMDLINE = (
    'CONFIG_CMDLINE="console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr '
    "ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug rdinit=/init "
    "panic=0 g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Quasar "
    "g_ether.iSerialNumber=GEMINI_QUASAR_20260727 "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused initcall_blacklist=mt6797_a72_power_driver_init "
    'fw_devlink=rpm"'
)
REQUIRED_CONFIG = {
    'CONFIG_LOCALVERSION="-gemini-quasar"',
    "# CONFIG_LOCALVERSION_AUTO is not set",
    "CONFIG_CMDLINE_FORCE=y",
    KERNEL_CMDLINE,
    "CONFIG_DEBUG_FS=y",
    "CONFIG_I2C=y",
    "CONFIG_I2C_MT65XX=y",
    "# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set",
    "CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC=y",
    "# CONFIG_I2C_CHARDEV is not set",
    "# CONFIG_REGULATOR_DA9211 is not set",
    "# CONFIG_MTK_MT6797_A72_POWER is not set",
    "CONFIG_MTK_MT6797_DVFSP_HANDOFF=y",
    "CONFIG_SMP=y",
    "CONFIG_HOTPLUG_CPU=y",
    "CONFIG_ARM_PSCI_FW=y",
    "CONFIG_USB_GADGET=y",
    "CONFIG_USB_ETH=y",
    "CONFIG_USB_ETH_RNDIS=y",
    "CONFIG_MEDIATEK_WATCHDOG=y",
    "CONFIG_FB_SIMPLE=y",
    "CONFIG_FRAMEBUFFER_CONSOLE=y",
    "CONFIG_FONT_TER16x32=y",
    "CONFIG_PSTORE=y",
    "CONFIG_PSTORE_RAM=y",
    "# CONFIG_SUSPEND is not set",
    "# CONFIG_CPU_FREQ is not set",
    "# CONFIG_CPU_IDLE is not set",
    "# CONFIG_MODULES is not set",
    "# CONFIG_MMC is not set",
    "# CONFIG_MTD is not set",
}
REQUIRED_SYMBOLS = {
    "__i2c_transfer",
    "mt6797_dvfsp_handoff_driver_init",
    "mt6797_dvfsp_handoff_require_ready",
    "mt6797_psci_cpu_boot",
    "mtk_i2c_quasar_fops",
    "mtk_i2c_quasar_read",
    "mtk_i2c_quasar_write",
    "mtk_i2c_transfer",
}
FORBIDDEN_SYMBOLS = {
    "da9211_i2c_probe",
    "i2c_dev_init",
    "mt6797_a72_power_cpu_boot_ready",
    "mt6797_a72_power_cpu_on_complete",
    "mt6797_a72_power_driver_init",
    "mt6797_a72_power_prepare_first",
    "mtk_i2c_orion_run",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def tree_inventory(root: pathlib.Path, label: str) -> dict[str, pathlib.Path]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{label} is missing or unsafe")
    files: dict[str, pathlib.Path] = {}
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        member = path.lstat()
        if path.is_symlink():
            raise ValueError(f"{label} contains symlink: {relative}")
        if stat.S_ISREG(member.st_mode):
            if not member.st_size:
                raise ValueError(f"{label} contains empty file: {relative}")
            files[relative] = path
        elif not stat.S_ISDIR(member.st_mode):
            raise ValueError(f"{label} contains special member: {relative}")
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
            or path.suffix != ".patch"
        ):
            raise ValueError(f"patch series contains unsafe entry: {entry}")
    return entries


def validate_patch_pins(repository: pathlib.Path) -> None:
    if len(co.QUASAR_PATCHES) != len(co.QUASAR_PATCH_SHA256S):
        raise ValueError("Quasar patch-pin inventory is inconsistent")
    for relative, wanted in zip(
        co.QUASAR_PATCHES,
        co.QUASAR_PATCH_SHA256S,
        strict=True,
    ):
        source = regular(
            repository / "patches" / relative,
            f"source-pinned Quasar patch {relative}",
        )
        if digest(source) != wanted:
            raise ValueError(f"source-pinned Quasar patch changed: {relative}")


def validate_package_manifest(package: pathlib.Path) -> None:
    manifest = regular(package / "SHA256SUMS", "package checksum manifest")
    seen: set[str] = set()
    for line in manifest.decode("ascii").splitlines():
        if len(line) < 67 or line[64:66] != "  ":
            raise ValueError("malformed package checksum line")
        wanted = line[:64]
        name = line[66:]
        if not name.startswith("./"):
            raise ValueError("package checksum entry lacks canonical ./ prefix")
        relative = name[2:]
        path = pathlib.PurePosixPath(relative)
        if (
            len(wanted) != 64
            or any(character not in "0123456789abcdef" for character in wanted)
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != relative
            or relative in seen
        ):
            raise ValueError("unsafe package checksum entry")
        seen.add(relative)
        if digest(regular(package / relative, f"package member {relative}")) != wanted:
            raise ValueError(f"package checksum failed: {relative}")


def validate_provenance(
    repository: pathlib.Path,
    package: pathlib.Path,
    entries: list[str],
) -> None:
    packaged_patches = tree_inventory(
        package / "provenance/patches", "packaged patch provenance"
    )
    if set(packaged_patches) != set(entries):
        raise ValueError("packaged patch inventory differs from selected series")
    for entry in entries:
        if regular(
            repository / "patches" / entry, f"repository patch {entry}"
        ) != regular(packaged_patches[entry], f"packaged patch {entry}"):
            raise ValueError(f"packaged patch differs from repository: {entry}")

    names = {pathlib.PurePosixPath(relative).name: relative for relative in FRAGMENTS}
    if len(names) != len(FRAGMENTS):
        raise ValueError("Quasar fragment basenames collide")
    packaged_fragments = tree_inventory(
        package / "provenance/configs", "packaged fragment provenance"
    )
    if set(packaged_fragments) != set(names):
        raise ValueError("packaged configuration-fragment inventory changed")
    for name, relative in names.items():
        if regular(
            repository / relative, f"repository fragment {relative}"
        ) != regular(packaged_fragments[name], f"packaged fragment {name}"):
            raise ValueError(f"packaged fragment differs from repository: {relative}")


def validate_config(data: bytes) -> None:
    try:
        config = data.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("kernel configuration is not ASCII") from exc
    missing = sorted(REQUIRED_CONFIG - set(config.splitlines()))
    if missing:
        raise ValueError("Quasar kernel configuration lacks " + missing[0])
    if config.count("maxcpus=8") != 1 or "maxcpus=9" in config:
        raise ValueError("Quasar CPU request boundary changed")
    if config.count("GEMINI_QUASAR_20260727") != 1:
        raise ValueError("Quasar USB attribution marker changed")
    if "CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC=y" in config:
        raise ValueError("Quasar unexpectedly compiles the Orion diagnostic")


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
        raise ValueError("Quasar System.map lacks " + missing[0])
    present = sorted(FORBIDDEN_SYMBOLS & symbols)
    if present:
        raise ValueError("Quasar contains forbidden active symbol " + present[0])


def validate_image(image: bytes) -> None:
    cmdline = KERNEL_CMDLINE.removeprefix(
        'CONFIG_CMDLINE="'
    ).removesuffix('"').encode("ascii")
    if image.count(cmdline) != 2:
        raise ValueError(
            "Quasar Image does not contain exactly two forced-cmdline copies"
        )
    required = (
        b"GEMINI_QUASAR_NATIVE_DIAGNOSTIC state=ready",
        b"GEMINI_QUASAR_DIAGNOSTIC_GATE missing DVFSP handoff",
        b"GEMINI_QUASAR_DIAGNOSTIC_GATE target node unavailable",
        b"GEMINI_QUASAR_DIAGNOSTIC_GATE node identity mismatch",
        b"GEMINI_QUASAR_DIAGNOSTIC_GATE adapter debugfs unavailable",
        b"GEMINI_QUASAR_DIAGNOSTIC_GATE debugfs creation failed",
        b"quasar-run-native",
        b"candidate=Quasar state=%s one_shot=%s",
        b"forced_length_mode=none forced_engine=none reset_pending=0",
        b"CPU%u boot rejected: A72 power sequence inactive",
    )
    for marker in required:
        if marker not in image:
            raise ValueError(f"Quasar Image lacks marker {marker!r}")
    forbidden = (
        b"orion-run-all",
        b"GEMINI_ORION_DIAGNOSTIC state=ready",
        b"modes=packed-fifo,packed-dma,aux-dma",
    )
    for marker in forbidden:
        if marker in image:
            raise ValueError(f"Quasar Image contains forbidden marker {marker!r}")


def load_fdt_parser(repository: pathlib.Path) -> ModuleType:
    source = (
        repository
        / "experiments/2026-07-16-lk-handoff-alignment/scripts/"
        "validate-lk-compatible-dtb.py"
    )
    data = regular(source, "source-pinned FDT parser")
    if digest(data) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("quasar_fdt", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned FDT parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_dtb(repository: pathlib.Path, path: pathlib.Path) -> None:
    fdt = load_fdt_parser(repository)
    tree, _reservations, _boot_cpu = fdt.parse_fdt(path)
    i2c6 = co.I2C6_PATH
    compatible = b"".join(fdt.string(value) for value in co.I2C6_COMPATIBLE)
    fdt.require_prop(tree, i2c6, "compatible", compatible)
    fdt.require_prop(tree, i2c6, "status", fdt.string("okay"))
    if "access-controllers" not in tree[i2c6]:
        raise ValueError("Quasar I2C6 lacks its fail-closed handoff dependency")
    if any(node.startswith(i2c6 + "/") for node in tree):
        raise ValueError("Quasar I2C6 is not childless")
    for forbidden in (
        i2c6 + "/regulator@68",
        i2c6 + "/regulator@69",
        i2c6 + "/da9214@68",
        i2c6 + "/da9214@69",
        "/a72-power@10222000",
    ):
        if forbidden in tree:
            raise ValueError(f"Quasar DT contains forbidden node {forbidden}")
    for cpu in ("/cpus/cpu@200", "/cpus/cpu@201"):
        fdt.require_prop(
            tree, cpu, "enable-method", fdt.string("mediatek,mt6797-psci")
        )


def validate(repository: pathlib.Path, package: pathlib.Path) -> None:
    co.require_input_pins()
    validate_patch_pins(repository)
    validate_package_manifest(package)
    repository_manifest = regular(
        repository / "kernel/manifest.json", "repository kernel manifest"
    )
    if repository_manifest != regular(
        package / "provenance/kernel-manifest.json",
        "packaged kernel manifest",
    ):
        raise ValueError("packaged kernel manifest differs from repository")
    manifest = json.loads(repository_manifest)
    if manifest["config"]["profiles"].get(co.PROFILE) != {
        "base": "defconfig",
        "patch_series": co.SERIES,
        "fragments": list(FRAGMENTS),
    }:
        raise ValueError("Quasar manifest profile changed")

    fragment = regular(repository / co.CONFIG_FRAGMENT, "Quasar config fragment")
    if digest(fragment) != co.CONFIG_FRAGMENT_SHA256:
        raise ValueError("source-pinned Quasar config fragment changed")
    series = regular(repository / co.SERIES, "Quasar patch series")
    if digest(series) != co.SERIES_SHA256:
        raise ValueError("source-pinned Quasar patch series changed")
    if series != regular(package / "provenance/series", "packaged patch series"):
        raise ValueError("packaged patch series differs from repository")
    entries = series_entries(series)
    if len(entries) != 108 or tuple(entries[-6:]) != co.QUASAR_PATCHES:
        raise ValueError("Quasar series ending changed")
    validate_provenance(repository, package, entries)

    build = json.loads(regular(package / "provenance/build.json", "build provenance"))
    if (
        build.get("build_profile") != co.PROFILE
        or build.get("base_config") != "defconfig"
        or build.get("config_fragments") != list(FRAGMENTS)
    ):
        raise ValueError("package provenance is not exact Quasar")

    config = regular(package / "kernel.config", "kernel config")
    validate_config(config)
    validate_system_map(regular(package / "System.map", "System.map"))
    image = regular(package / "Image", "kernel Image")
    if gzip.decompress(regular(package / "Image.gz", "kernel Image.gz")) != image:
        raise ValueError("Image.gz does not expand to Image")
    validate_image(image)
    dtb_path = package / GEMINI_DTB
    if digest(regular(dtb_path, "compiled Quasar Gemini DT")) != (
        co.ORION_COMPILED_DTB_SHA256
    ):
        raise ValueError("Quasar compiled DT differs from exact Orion/Vega")
    validate_dtb(repository, dtb_path)


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
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        gzip.BadGzipFile,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=quasar-native-i2c6-kernel-package")
    print(f"profile={co.PROFILE}")
    print(f"patch_series={co.SERIES}")
    print("patch_count=108")
    print(f"quasar_patch_sha256={co.QUASAR_PATCH_SHA256}")
    print(f"config_sha256={digest(config)}")
    print(f"image_sha256={digest(image)}")
    print("i2c6=mt6797-idvfs-childless")
    print("orion_diagnostic=absent")
    print("quasar_diagnostic=fixed-native-root-only-one-shot")
    print("native_policy=unforced-packed-fifo")
    print("i2c_chardev=absent")
    print("da9214_provider=absent")
    print("cpu8_cpu9=fail-closed-unrequested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
