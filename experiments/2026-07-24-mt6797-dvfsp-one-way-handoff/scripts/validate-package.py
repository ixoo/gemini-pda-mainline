#!/usr/bin/env python3
"""Validate one unpinned Candidate AO kernel package against exact inputs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import pathlib
import re
import stat
import struct
import sys
import zlib
from types import ModuleType
from typing import Any


sys.dont_write_bytecode = True

PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner"
)
SERIES_REL = "patches/series-dvfsp-handoff-owner"
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
]

SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
SERIES_SHA256 = "00b79dc273943b52f7353b9e8252ab7a2963c0f45b5aea0077885af7f9fb28af"
PATCHSET_SHA256 = "98b2058c6c7127bcb441d734090025581dc1ebdfc50537123ea6ad3b1d9aec32"
CONFIG_INPUTS_SHA256 = (
    "0a6d7cedaf2b1b7bd4f6dd896d307ccd7696eecf88fafb30ee01e15ae92fdb54"
)
FDT_PARSER_SHA256 = (
    "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"
)
GATE_AUDITOR_SHA256 = (
    "90aa983f66261e18f192b14a535ccf9520b6e9079d45a8ce9234e30de8e90bde"
)
HANDOFF_AUDITOR_SHA256 = (
    "e008e4011c3a3cb1a6e3a4877e12955117cd7046ea2f1f37e87a8599b30808be"
)

PATCH_0092 = "v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
PATCH_0094 = (
    "v7.1.3/0094-dt-bindings-soc-mediatek-add-MT6797-DVFSP-"
    "handoff-observer.patch"
)
PATCH_0095 = "v7.1.3/0095-soc-mediatek-add-MT6797-DVFSP-handoff-observer.patch"
PATCH_0097 = (
    "v7.1.3/0097-dt-bindings-soc-mediatek-add-MT6797-DVFSP-"
    "handoff-owner.patch"
)
PATCH_0098 = "v7.1.3/0098-soc-mediatek-add-MT6797-DVFSP-one-way-handoff.patch"
PATCH_INPUT_SHA256 = {
    PATCH_0092: "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5",
    PATCH_0094: "2e20664ff4cb08a4f2296bdafb84148d4e4cf79b1eb17b3e92f6a7bb145abe59",
    PATCH_0095: "4ac79ec2653e829fef973e85176cc00c7be908983cb5261d940b3395332ae764",
    PATCH_0097: "11b5fb7c0cf8ef034fa3e1db706d05e3bab7f5aeade0d7592a2213ed7e3ac910",
    PATCH_0098: "260f84c885d9f25524162ab097f1377137b55b5461af2b429d4508f1cfe58748",
}

KERNEL_RELEASE = "7.1.3-gemini-observability-L"
COMPILER = "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
LINKER = "GNU ld (GNU Binutils for Ubuntu) 2.42"
GEMINI_DTB = "dtbs/mediatek/mt6797-gemini-pda.dtb"
PACKAGE_DIRECTORY_MODE = 0o775
PACKAGE_DEFAULT_FILE_MODE = 0o644
PACKAGE_GENERATED_FILE_MODE = 0o664
PACKAGE_MEMBER_COUNT = 236
PACKAGE_DTB_COUNT = 119

CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused "
    "initcall_blacklist=mt6797_a72_power_driver_init"
)
REQUIRED_CONFIG = {
    f'CONFIG_CMDLINE="{CMDLINE}"',
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
    b"mediatek,mt6797-dvfsp-handoff\0",
    b"mt6797-dvfsp-handoff\0",
    b"state=validating operation=one-way-handoff i2c6_policy=disabled\n\0",
    b"initial-gate-already-gated\0",
    b"late-revalidation-failed\0",
    b"state=provisional normalization=ungated-to-gated ",
    b"state=ready normalization=ungated-to-gated ",
    b"sample=%s timer=%08x/%08x con0=%08x con1=%08x ",
    b"i2c6_policy=disabled\n\0",
    CMDLINE.encode("ascii"),
)
FORBIDDEN_IMAGE_MARKERS = (
    b"mediatek,mt6797-dvfsp-handoff-observer\0",
    b"mt6797-dvfsp-handoff-observer\0",
    b"mediatek,mt6797-dvfsp\0",
    b"quiescent-stopped\0",
    b"active-v1\n\0",
    b"fixed-vproc-firmware-clock\n\0",
    b"CPU%u fixed-state A72 power sequence prepared\n\0",
)
REQUIRED_SYSTEM_MAP_SYMBOLS = {
    "mt6797_dvfsp_handoff_probe",
    "mt6797_dvfsp_late_work",
    "mt6797_dvfsp_handoff_driver",
    "mt6797_dvfsp_handoff_driver_init",
    "mt6797_a72_power_driver_init",
    "da9211_regulator_driver_init",
    "mt6797_psci_cpu_init",
    "mt6797_psci_cpu_prepare",
    "mt6797_psci_cpu_boot",
    "mt6797_psci_cpu_can_disable",
}
FORBIDDEN_SYSTEM_MAP_SYMBOLS = {
    "mt6797_dvfsp_observer_probe",
    "mt6797_dvfsp_observer_driver",
    "mt6797_dvfsp_observer_driver_init",
    "mt6797_dvfsp_handoff_remove",
    "mt6797_a72_power_cpu_boot_ready",
    "mt6797_a72_power_cpu_on_complete",
    "mt6797_a72_power_cpu_on_failed",
    "mt6797_a72_power_cpu_startup",
    "mt6797_a72_power_cpu_teardown",
    "mt6797_a72_power_preflight",
    "mt6797_a72_power_prepare_first",
}
REQUIRED_GATE_AUDIT_SEMANTICS = (
    b"compiled_cpu_ops_table=fail-closed\n",
    b"compiled_return_eagain=yes\n",
    b"resolved_calls=logging-only\n",
    b"psci_cpu_on_call=absent\n",
    b"compiled_can_disable_return=false\n",
    b"psci_cpu_off_callback=absent\n",
    b"hardware_transition_path=absent\n",
)
REQUIRED_HANDOFF_AUDIT_SEMANTICS = (
    b"probe_present=yes\n",
    b"clk_prepare_enable_calls=1\n",
    b"clk_disable_unprepare_calls=1\n",
    b"every_successful_enable_balanced=yes\n",
    b"late_worker_clock_mutation=absent\n",
    b"direct_mmio_write=absent\n",
    b"regmap_write_or_update=absent\n",
    b"i2c_regulator_cpu_control_calls=absent\n",
    b"restart_unpause_userspace_api=absent\n",
    b"remove_or_unbind_path=absent\n",
)

IKCONFIG_START = b"IKCFG_ST"
IKCONFIG_END = b"IKCFG_ED"
IKCONFIG_LIMIT = 16 * 1024 * 1024
LK_KERNEL_ADDR = 0x40200000
LK_MT6797_DECOMPRESS_LIMIT = 0x03200000
ARM64_PLACEMENT_ALIGNMENT = 0x00200000
LK_ARM64_IMAGE_FLAGS = 0x0A
ARM64_MAGIC = b"ARM\x64"
HEX256 = re.compile(r"[0-9a-f]{64}")
GENERATED_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

I2C6 = "/i2c@1100e000"
DA9214 = I2C6 + "/regulator@68"
A72_POWER = "/a72-power@10222000"
INFRACFG = "/syscon@10001000"
LEGACY_DVFSP = "/dvfsp@11015000"
OBSERVER = "/dvfsp-observer@11015000"
HANDOFF = "/dvfsp-handoff@11015000"


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    return digest_bytes(path.read_bytes())


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{label} is not a safe directory")
    return path.resolve(strict=True)


def decode_json_object(data: bytes, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate JSON member {key!r}")
            result[key] = value
        return result

    value = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=unique,
        parse_constant=lambda number: (_ for _ in ()).throw(
            ValueError(f"{label} contains invalid JSON number {number}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    return value


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    return decode_json_object(read_regular(path, label), label)


def inventory(root: pathlib.Path) -> dict[str, pathlib.Path]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe package tree: {root}")
    if stat.S_IMODE(info.st_mode) != PACKAGE_DIRECTORY_MODE:
        raise ValueError(f"package directory mode changed: {root}")

    files: dict[str, pathlib.Path] = {}
    directories: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        path_info = path.lstat()
        if path.is_symlink():
            raise ValueError(f"package contains symlink: {relative}")
        if stat.S_ISREG(path_info.st_mode):
            files[relative] = path
        elif stat.S_ISDIR(path_info.st_mode):
            if stat.S_IMODE(path_info.st_mode) != PACKAGE_DIRECTORY_MODE:
                raise ValueError(f"package directory mode changed: {relative}")
            directories.add(relative)
        else:
            raise ValueError(f"package contains special member: {relative}")

    expected_directories: set[str] = set()
    for relative in files:
        parent = pathlib.PurePosixPath(relative).parent
        while parent != pathlib.PurePosixPath("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    if directories != expected_directories:
        raise ValueError("package contains a missing or empty extra directory")
    return files


def expected_package_file_mode(relative: str) -> int:
    if (
        relative == "SHA256SUMS"
        or relative == "provenance/build.json"
        or relative.startswith("dtbs/")
    ):
        return PACKAGE_GENERATED_FILE_MODE
    return PACKAGE_DEFAULT_FILE_MODE


def validate_package_file_modes(members: dict[str, pathlib.Path]) -> None:
    for relative, path in members.items():
        actual = stat.S_IMODE(path.lstat().st_mode)
        expected = expected_package_file_mode(relative)
        if actual != expected:
            raise ValueError(
                f"package mode changed: {relative}: "
                f"expected {expected:04o}, found {actual:04o}"
            )


def manifest_map(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    lines = read_regular(path, "package SHA256SUMS").decode("ascii").splitlines()
    for number, line in enumerate(lines, 1):
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or HEX256.fullmatch(fields[0]) is None:
            raise ValueError(f"malformed package manifest line {number}")
        if not fields[1].startswith("./"):
            raise ValueError(f"non-canonical package manifest path at line {number}")
        relative = fields[1][2:]
        pure = pathlib.PurePosixPath(relative)
        if (
            not relative
            or pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != relative
            or relative == "SHA256SUMS"
            or relative in result
        ):
            raise ValueError(f"unsafe or duplicate package manifest path at line {number}")
        result[relative] = fields[0]
    return result


def validate_package_manifest(package: pathlib.Path) -> dict[str, pathlib.Path]:
    members = inventory(package)
    validate_package_file_modes(members)
    recorded = manifest_map(package / "SHA256SUMS")
    if set(recorded) != set(members) - {"SHA256SUMS"}:
        raise ValueError("package manifest is not an exact file inventory")
    for relative, expected in recorded.items():
        if digest_bytes(read_regular(members[relative], relative)) != expected:
            raise ValueError(f"package checksum mismatch: {relative}")
    return members


def series_entries(data: bytes) -> list[str]:
    result: list[str] = []
    for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
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
            raise ValueError(f"unsafe patch-series entry at line {number}")
        result.append(line)
    if len(result) != len(set(result)):
        raise ValueError("patch series contains a duplicate entry")
    return result


def expected_patch_prefixes() -> list[str]:
    return [
        *(f"{number:04d}" for number in range(1, 58)),
        "0057a",
        *(f"{number:04d}" for number in range(58, 93)),
        "0094",
        "0095",
        "0097",
        "0098",
    ]


def patchset_digest(series: bytes, patch_root: pathlib.Path) -> str:
    records = [f"{digest_bytes(series)}  {SERIES_REL}\n"]
    for entry in series_entries(series):
        data = read_regular(patch_root / entry, f"patch {entry}")
        records.append(f"{digest_bytes(data)}  {entry}\n")
    return digest_bytes("".join(records).encode("ascii"))


def validate_series(
    repository: pathlib.Path,
    package: pathlib.Path,
    members: dict[str, pathlib.Path],
) -> list[str]:
    repository_series = read_regular(
        repository / SERIES_REL, "repository Candidate AO series"
    )
    packaged_series = read_regular(
        package / "provenance/series", "packaged Candidate AO series"
    )
    if repository_series != packaged_series:
        raise ValueError("packaged Candidate AO series differs from repository")
    if digest_bytes(repository_series) != SERIES_SHA256:
        raise ValueError("Candidate AO selected-series identity changed")

    entries = series_entries(repository_series)
    prefixes = [
        pathlib.PurePosixPath(entry).name.split("-", 1)[0] for entry in entries
    ]
    if prefixes != expected_patch_prefixes() or len(entries) != 97:
        raise ValueError(
            "Candidate AO series is not exact 0001-0092 plus 0057a, "
            "0094, 0095, 0097, and 0098"
        )
    if entries[-5:] != [
        PATCH_0092,
        PATCH_0094,
        PATCH_0095,
        PATCH_0097,
        PATCH_0098,
    ]:
        raise ValueError("Candidate AO series ending changed")
    if any(
        pathlib.PurePosixPath(entry).name.startswith(("0093-", "0096-"))
        for entry in entries
    ):
        raise ValueError("Candidate AO selected forbidden patch 0093 or 0096")

    expected_patch_members = {
        f"provenance/patches/{entry}" for entry in entries
    }
    actual_patch_members = {
        relative
        for relative in members
        if relative.startswith("provenance/patches/")
    }
    if actual_patch_members != expected_patch_members:
        raise ValueError("packaged patch inventory differs from selected series")

    for entry in entries:
        repository_patch = read_regular(
            repository / "patches" / entry, f"repository patch {entry}"
        )
        packaged_patch = read_regular(
            package / "provenance/patches" / entry,
            f"packaged patch {entry}",
        )
        if packaged_patch != repository_patch:
            raise ValueError(f"packaged patch differs from repository: {entry}")
        expected_hash = PATCH_INPUT_SHA256.get(entry)
        if expected_hash is not None and digest_bytes(repository_patch) != expected_hash:
            raise ValueError(f"source-pinned Candidate AO patch changed: {entry}")

    patch_0092_text = read_regular(
        repository / "patches" / PATCH_0092, "corrected patch 0092"
    ).decode("utf-8")
    if (
        "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)"
        not in patch_0092_text
        or "+\treturn false;" not in patch_0092_text
        or "+\treturn true;" in patch_0092_text
    ):
        raise ValueError("patch 0092 no longer contains the corrected disable gate")

    repository_patchset = patchset_digest(
        repository_series, repository / "patches"
    )
    packaged_patchset = patchset_digest(
        packaged_series, package / "provenance/patches"
    )
    if repository_patchset != PATCHSET_SHA256 or packaged_patchset != PATCHSET_SHA256:
        raise ValueError("Candidate AO path-sensitive patchset identity changed")
    return entries


def validate_manifest_contract(data: bytes, label: str) -> dict[str, Any]:
    value = decode_json_object(data, label)
    expected_kernel = {
        "version": "7.1.3",
        "released": "2026-07-04",
        "source_url": "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.1.3.tar.xz",
        "sha256": SOURCE_SHA256,
    }
    if (
        set(value) != {"schema", "kernel", "architecture", "patch_series", "config"}
        or value.get("schema") != 1
        or value.get("kernel") != expected_kernel
        or value.get("architecture") != "arm64"
        or value.get("patch_series") != "patches/series"
    ):
        raise ValueError(f"{label} global kernel contract changed")
    config = value.get("config")
    if (
        not isinstance(config, dict)
        or set(config) != {"default_profile", "profiles"}
        or config.get("default_profile") != "full"
    ):
        raise ValueError(f"{label} configuration contract changed")
    profiles = config.get("profiles")
    expected_profile = {
        "base": "defconfig",
        "patch_series": SERIES_REL,
        "fragments": FRAGMENTS,
    }
    if not isinstance(profiles, dict) or profiles.get(PROFILE) != expected_profile:
        raise ValueError(f"{label} exact Candidate AO profile changed")
    return value


def config_inputs_digest(
    profile: str, fragments: dict[str, bytes]
) -> str:
    records = [f"profile={profile}\n", "base=defconfig\n"]
    for relative in FRAGMENTS:
        records.append(f"{digest_bytes(fragments[relative])}  {relative}\n")
    return digest_bytes("".join(records).encode("ascii"))


def validate_fragments(
    repository: pathlib.Path,
    package: pathlib.Path,
    members: dict[str, pathlib.Path],
) -> dict[str, bytes]:
    expected_members = {
        f"provenance/configs/{pathlib.PurePosixPath(relative).name}"
        for relative in FRAGMENTS
    }
    actual_members = {
        relative
        for relative in members
        if relative.startswith("provenance/configs/")
    }
    if actual_members != expected_members:
        raise ValueError("packaged configuration-fragment inventory changed")

    result: dict[str, bytes] = {}
    for relative in FRAGMENTS:
        name = pathlib.PurePosixPath(relative).name
        repository_data = read_regular(
            repository / relative, f"repository fragment {relative}"
        )
        packaged_data = read_regular(
            package / "provenance/configs" / name,
            f"packaged fragment {name}",
        )
        if packaged_data != repository_data:
            raise ValueError(f"packaged fragment differs from repository: {relative}")
        result[relative] = packaged_data
    if config_inputs_digest(PROFILE, result) != CONFIG_INPUTS_SHA256:
        raise ValueError("Candidate AO configuration-input identity changed")
    return result


def config_map(data: bytes) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        if line.startswith("CONFIG_"):
            key = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            key = line[2:-11]
        else:
            continue
        if key in result:
            raise ValueError(f"duplicate resolved-config symbol: {key}")
        result[key] = line
    return result


def fragment_requests(fragments: dict[str, bytes]) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in FRAGMENTS:
        for number, line in enumerate(
            fragments[relative].decode("utf-8").splitlines(), 1
        ):
            if not line or line == "#" or (
                line.startswith("# ") and not line.startswith("# CONFIG_")
            ):
                continue
            if line.startswith("CONFIG_") and "=" in line:
                symbol = line.split("=", 1)[0]
            elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
                symbol = line[2:-11]
            else:
                raise ValueError(
                    f"unsupported fragment line {relative}:{number}: {line}"
                )
            result[symbol] = line
    return result


def validate_resolved_config(
    config_data: bytes, fragments: dict[str, bytes]
) -> None:
    resolved = config_map(config_data)
    for symbol, expected in fragment_requests(fragments).items():
        actual = resolved.get(symbol)
        if expected.startswith("CONFIG_"):
            if actual != expected:
                raise ValueError(
                    f"resolved config lost fragment request {symbol}: {expected}"
                )
        elif actual is not None and actual != expected:
            raise ValueError(f"resolved config enabled disabled request {symbol}")

    lines = set(config_data.decode("utf-8").splitlines())
    missing = REQUIRED_CONFIG - lines
    if missing:
        raise ValueError(f"required config line is missing: {sorted(missing)[0]}")
    command_line = resolved.get("CONFIG_CMDLINE")
    if command_line != f'CONFIG_CMDLINE="{CMDLINE}"':
        raise ValueError("Candidate AO forced command line is not exact")
    if "CONFIG_MTK_MT6797_DVFSP_HANDOFF_OBSERVER" in resolved:
        raise ValueError("Candidate AO retained the predecessor observer config")
    tokens = CMDLINE.split()
    for token in (
        "maxcpus=8",
        "regulator_ignore_unused",
        "initcall_blacklist=mt6797_a72_power_driver_init",
    ):
        if tokens.count(token) != 1:
            raise ValueError(f"forced-command-line token is not exact: {token}")
    if (
        "maxcpus=1" in tokens
        or "maxcpus=9" in tokens
        or "maxcpus=10" in tokens
        or "nosmp" in tokens
        or any(token.startswith(("nr_cpus=", "isolcpus=", "irqaffinity=")) for token in tokens)
    ):
        raise ValueError("forced command line contains conflicting CPU policy")


def normalized_build_bytes(value: dict[str, Any], label: str) -> bytes:
    generated = value.get("generated_utc")
    if not isinstance(generated, str) or GENERATED_UTC.fullmatch(generated) is None:
        raise ValueError(f"{label} generated_utc is malformed")
    normalized = dict(value)
    del normalized["generated_utc"]
    return (json.dumps(normalized, indent=2, sort_keys=True) + "\n").encode()


def validate_build(
    value: dict[str, Any],
    config_data: bytes,
    package: pathlib.Path,
) -> bytes:
    expected = {
        "schema": 1,
        "kernel_release": KERNEL_RELEASE,
        "build_profile": PROFILE,
        "base_config": "defconfig",
        "config_fragments": FRAGMENTS,
        "config_inputs_sha256": CONFIG_INPUTS_SHA256,
        "source_sha256": SOURCE_SHA256,
        "patchset_sha256": PATCHSET_SHA256,
        "config_sha256": digest_bytes(config_data),
        "modules_built": False,
        "compiler": COMPILER,
        "linker": LINKER,
    }
    if set(value) != set(expected) | {"generated_utc"}:
        raise ValueError("Candidate AO build-provenance inventory changed")
    for key, wanted in expected.items():
        if type(value.get(key)) is not type(wanted) or value.get(key) != wanted:
            raise ValueError(f"Candidate AO build provenance changed: {key}")
    normalized = normalized_build_bytes(value, "Candidate AO build")

    expected_name = (
        f"linux-7.1.3-gemini-{PROFILE}-{PATCHSET_SHA256[:8]}-"
        f"{CONFIG_INPUTS_SHA256[:8]}"
    )
    if package.name != expected_name:
        raise ValueError("Candidate AO package basename disagrees with exact inputs")
    return normalized


def decompress_lk_image_gz(data: bytes, label: str) -> bytes:
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        image = decompressor.decompress(data, LK_MT6797_DECOMPRESS_LIMIT + 1)
        if len(image) > LK_MT6797_DECOMPRESS_LIMIT or decompressor.unconsumed_tail:
            raise ValueError(f"{label} exceeds the MT6797 LK decompression limit")
        image += decompressor.flush()
    except zlib.error as exc:
        raise ValueError(f"{label} gzip payload is invalid: {exc}") from exc
    if (
        not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
        or not image
        or len(image) > LK_MT6797_DECOMPRESS_LIMIT
    ):
        raise ValueError(f"{label} is not exactly one bounded gzip stream")
    if len(image) < 64 or image[56:60] != ARM64_MAGIC:
        raise ValueError(f"{label} does not contain an arm64 Image")
    text_offset, image_size, flags = struct.unpack_from("<3Q", image, 8)
    if not 0 < image_size <= LK_MT6797_DECOMPRESS_LIMIT:
        raise ValueError(f"{label} arm64 image_size is invalid")
    if flags != LK_ARM64_IMAGE_FLAGS:
        raise ValueError(f"{label} arm64 flags differ from the LK contract")
    if LK_KERNEL_ADDR < text_offset:
        raise ValueError(f"{label} arm64 text_offset exceeds the kernel address")
    if (LK_KERNEL_ADDR - text_offset) % ARM64_PLACEMENT_ALIGNMENT:
        raise ValueError(f"{label} arm64 placement is not 2 MiB aligned")
    return image


def extract_ikconfig(image: bytes) -> bytes:
    if image.count(IKCONFIG_START) != 1 or image.count(IKCONFIG_END) != 1:
        raise ValueError("Candidate AO Image lacks one exact IKCONFIG record")
    start = image.index(IKCONFIG_START) + len(IKCONFIG_START)
    end = image.index(IKCONFIG_END)
    if end <= start:
        raise ValueError("Candidate AO Image IKCONFIG record is malformed")
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        config = decompressor.decompress(image[start:end], IKCONFIG_LIMIT + 1)
        if len(config) > IKCONFIG_LIMIT or decompressor.unconsumed_tail:
            raise ValueError("Candidate AO embedded config exceeds extraction limit")
        config += decompressor.flush(IKCONFIG_LIMIT + 1 - len(config))
    except zlib.error as exc:
        raise ValueError(f"Candidate AO embedded config is invalid: {exc}") from exc
    if (
        len(config) > IKCONFIG_LIMIT
        or not decompressor.eof
        or decompressor.unused_data
        or decompressor.unconsumed_tail
        or not config
    ):
        raise ValueError("Candidate AO embedded config is incomplete or oversized")
    return config


def validate_image(image: bytes, config_data: bytes) -> None:
    if extract_ikconfig(image) != config_data:
        raise ValueError("Candidate AO embedded config is not exact kernel.config")
    for marker in REQUIRED_IMAGE_MARKERS:
        if marker not in image:
            raise ValueError(f"Candidate AO Image lacks handoff-owner marker: {marker!r}")
    for marker in FORBIDDEN_IMAGE_MARKERS:
        if marker in image:
            raise ValueError(f"Candidate AO Image contains forbidden active marker: {marker!r}")


def system_map_symbols(data: bytes) -> set[str]:
    symbols: set[str] = set()
    previous = -1
    for number, line in enumerate(data.decode("ascii").splitlines(), 1):
        fields = line.split()
        if len(fields) != 3 or re.fullmatch(r"[0-9a-fA-F]+", fields[0]) is None:
            raise ValueError(f"malformed System.map line {number}")
        address = int(fields[0], 16)
        if address < previous:
            raise ValueError("System.map is not address-sorted")
        previous = address
        symbols.add(fields[2])
    if not symbols:
        raise ValueError("System.map is empty")
    return symbols


def validate_system_map(data: bytes) -> None:
    symbols = system_map_symbols(data)
    missing = REQUIRED_SYSTEM_MAP_SYMBOLS - symbols
    if missing:
        raise ValueError(f"System.map lacks handoff-owner symbol: {sorted(missing)[0]}")
    forbidden = FORBIDDEN_SYSTEM_MAP_SYMBOLS & symbols
    if forbidden:
        raise ValueError(f"System.map contains active 0093 symbol: {sorted(forbidden)[0]}")


def load_gate_auditor() -> ModuleType:
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "2026-07-22-a72-reject-gate-kernel-split"
        / "scripts"
        / "audit-mt6797-psci-cpu-boot.py"
    )
    if digest_bytes(read_regular(source, "source-pinned gate auditor")) != GATE_AUDITOR_SHA256:
        raise ValueError("source-pinned compiled-gate auditor changed")
    spec = importlib.util.spec_from_file_location(
        "candidate_ao_compiled_gate_auditor", source
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned compiled-gate auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_compiled_gate(package: pathlib.Path) -> bytes:
    report = load_gate_auditor().audit_kernel(
        package / "Image", package / "System.map"
    )
    for required in REQUIRED_GATE_AUDIT_SEMANTICS:
        if required not in report:
            raise ValueError(
                f"compiled reject-gate audit lacks required result: {required!r}"
            )
    return report


def load_handoff_auditor() -> ModuleType:
    source = pathlib.Path(__file__).resolve().with_name("audit-compiled-handoff.py")
    if (
        digest_bytes(read_regular(source, "source-pinned handoff auditor"))
        != HANDOFF_AUDITOR_SHA256
    ):
        raise ValueError("source-pinned compiled-handoff auditor changed")
    spec = importlib.util.spec_from_file_location(
        "candidate_ao_compiled_handoff_auditor", source
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned compiled-handoff auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def validate_compiled_handoff(package: pathlib.Path) -> bytes:
    report = load_handoff_auditor().audit_kernel(
        package / "Image", package / "System.map"
    )
    for required in REQUIRED_HANDOFF_AUDIT_SEMANTICS:
        if required not in report:
            raise ValueError(
                f"compiled handoff audit lacks required result: {required!r}"
            )
    return report


def load_fdt_parser() -> ModuleType:
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    if digest_bytes(read_regular(source, "source-pinned FDT parser")) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("candidate_ao_package_fdt", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned FDT parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def phandle_map(tree: dict[str, dict[str, bytes]]) -> dict[int, str]:
    result: dict[int, str] = {}
    for path, properties in tree.items():
        aliases: list[int] = []
        for name in ("phandle", "linux,phandle"):
            raw = properties.get(name)
            if raw is None:
                continue
            if len(raw) != 4:
                raise ValueError(f"{path}:{name} is not one cell")
            aliases.append(struct.unpack(">I", raw)[0])
        if len(set(aliases)) > 1:
            raise ValueError(f"{path} has conflicting phandle aliases")
        if not aliases:
            continue
        value = aliases[0]
        if not value or (value in result and result[value] != path):
            raise ValueError(f"invalid or duplicate phandle at {path}")
        result[value] = path
    return result


def validate_package_dtb(path: pathlib.Path) -> None:
    fdt = load_fdt_parser()
    tree, _, _ = fdt.parse_fdt(path)
    fdt.require_prop(tree, I2C6, "status", fdt.string("disabled"))
    fdt.require_prop(tree, DA9214, "compatible", fdt.string("dlg,da9214"))
    fdt.require_prop(tree, DA9214, "reg", fdt.cells(0x68))
    fdt.require_prop(
        tree, A72_POWER, "compatible", fdt.string("mediatek,mt6797-a72-power")
    )
    fdt.require_prop(tree, A72_POWER, "status", fdt.string("okay"))
    fdt.require_prop(
        tree,
        HANDOFF,
        "compatible",
        fdt.string("mediatek,mt6797-dvfsp-handoff"),
    )
    fdt.require_prop(
        tree, HANDOFF, "reg", fdt.cells(0, 0x11015000, 0, 0x1000)
    )
    fdt.require_prop(tree, HANDOFF, "status", fdt.string("okay"))
    fdt.require_prop(tree, HANDOFF, "clock-names", fdt.string("i2c"))
    fdt.require_prop(
        tree,
        INFRACFG,
        "compatible",
        fdt.string("mediatek,mt6797-infracfg") + fdt.string("syscon"),
    )
    for forbidden_path in (OBSERVER, LEGACY_DVFSP):
        if forbidden_path in tree:
            raise ValueError(
                f"package DTB contains forbidden predecessor node {forbidden_path}"
            )
    forbidden_compatibles = (
        fdt.string("mediatek,mt6797-dvfsp"),
        fdt.string("mediatek,mt6797-dvfsp-handoff-observer"),
    )
    for node, properties in tree.items():
        compatible = properties.get("compatible")
        if compatible is not None and any(
            forbidden in compatible for forbidden in forbidden_compatibles
        ):
            raise ValueError(
                f"package DTB contains forbidden predecessor compatible at {node}"
            )
    for cpu in ("/cpus/cpu@200", "/cpus/cpu@201"):
        fdt.require_prop(
            tree,
            cpu,
            "enable-method",
            fdt.string("mediatek,mt6797-psci"),
        )

    references = phandle_map(tree)
    reference = tree[HANDOFF].get("mediatek,infracfg")
    if reference is None or len(reference) != 4:
        raise ValueError("package handoff infracfg reference is not one phandle")
    infracfg_handle = struct.unpack(">I", reference)[0]
    if references.get(infracfg_handle) != INFRACFG:
        raise ValueError("package handoff infracfg reference does not resolve exactly")

    clock = tree[HANDOFF].get("clocks")
    if clock is None or len(clock) != 8:
        raise ValueError("package handoff clock reference is not exactly two cells")
    clock_handle, clock_id = struct.unpack(">2I", clock)
    if (
        clock_handle != infracfg_handle
        or references.get(clock_handle) != INFRACFG
        or clock_id != 0x36
    ):
        raise ValueError("package handoff clock is not exact I2C_APPM clock 54")


def validate_package_shape(
    members: dict[str, pathlib.Path], entries: list[str]
) -> int:
    required = {
        "SHA256SUMS",
        "Image",
        "Image.gz",
        "kernel.config",
        "System.map",
        "provenance/build.json",
        "provenance/kernel-manifest.json",
        "provenance/series",
        GEMINI_DTB,
        *(
            f"provenance/configs/{pathlib.PurePosixPath(item).name}"
            for item in FRAGMENTS
        ),
        *(f"provenance/patches/{entry}" for entry in entries),
    }
    missing = required - set(members)
    if missing:
        raise ValueError(f"package lacks required member: {sorted(missing)[0]}")
    for relative in set(members) - required:
        path = pathlib.PurePosixPath(relative)
        if path.parent != pathlib.PurePosixPath("dtbs/mediatek") or path.suffix != ".dtb":
            raise ValueError(f"package contains unexpected member: {relative}")
    dtb_count = sum(
        relative.startswith("dtbs/mediatek/") and relative.endswith(".dtb")
        for relative in members
    )
    if len(members) != PACKAGE_MEMBER_COUNT or dtb_count != PACKAGE_DTB_COUNT:
        raise ValueError(
            "package inventory count changed: "
            f"members={len(members)}, dtbs={dtb_count}"
        )
    return dtb_count


def validate_package(
    repository: pathlib.Path, package: pathlib.Path
) -> dict[str, str | int]:
    members = validate_package_manifest(package)

    repository_manifest = read_regular(
        repository / "kernel/manifest.json", "repository kernel manifest"
    )
    packaged_manifest = read_regular(
        package / "provenance/kernel-manifest.json",
        "packaged kernel manifest",
    )
    if packaged_manifest != repository_manifest:
        raise ValueError("packaged kernel manifest differs from repository")
    validate_manifest_contract(repository_manifest, "Candidate AO manifest")

    entries = validate_series(repository, package, members)
    dtb_count = validate_package_shape(members, entries)
    fragments = validate_fragments(repository, package, members)

    config_data = read_regular(package / "kernel.config", "Candidate AO config")
    validate_resolved_config(config_data, fragments)
    build = load_json(package / "provenance/build.json", "Candidate AO build")
    normalized_build = validate_build(build, config_data, package)

    image = read_regular(package / "Image", "Candidate AO Image")
    image_gz = read_regular(package / "Image.gz", "Candidate AO Image.gz")
    if decompress_lk_image_gz(image_gz, "Candidate AO Image.gz") != image:
        raise ValueError("Candidate AO Image.gz does not expand to exact Image")
    validate_image(image, config_data)

    system_map = read_regular(package / "System.map", "Candidate AO System.map")
    validate_system_map(system_map)
    gate_audit = validate_compiled_gate(package)
    handoff_audit = validate_compiled_handoff(package)
    validate_package_dtb(package / GEMINI_DTB)

    return {
        "members": len(members),
        "dtbs": dtb_count,
        "package_manifest_sha256": digest_path(package / "SHA256SUMS"),
        "normalized_build_sha256": digest_bytes(normalized_build),
        "config_sha256": digest_bytes(config_data),
        "image_sha256": digest_bytes(image),
        "image_size": len(image),
        "image_gz_sha256": digest_bytes(image_gz),
        "image_gz_size": len(image_gz),
        "system_map_sha256": digest_bytes(system_map),
        "compiled_gate_audit_sha256": digest_bytes(gate_audit),
        "compiled_handoff_audit_sha256": digest_bytes(handoff_audit),
        "package_dtb_sha256": digest_path(package / GEMINI_DTB),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=pathlib.Path, required=True)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        repository = resolve_directory(args.repository, "repository")
        package = resolve_directory(args.package, "Candidate AO package")
        calibration = validate_package(repository, package)
        print("validation=candidate-ao-package-calibration")
        print(f"package={package.name}")
        print(f"profile={PROFILE}")
        print(f"series_path={SERIES_REL}")
        print("patch_count=97")
        print(f"series_sha256={SERIES_SHA256}")
        print(f"patchset_sha256={PATCHSET_SHA256}")
        print(
            "series_entries=0001-through-corrected-0092-with-0057a-"
            "plus-0094-0095-0097-0098"
        )
        print("patches_0093_0096=absent")
        print(f"config_inputs_sha256={CONFIG_INPUTS_SHA256}")
        print("forced_cmdline=exact-maxcpus8-a72-initcall-blacklist")
        print("handoff_owner_config=built-in")
        print("handoff_owner_image_markers=present")
        print("handoff_owner_system_map_symbols=present")
        print("predecessor_observer_markers_symbols=absent")
        print("active_0093_markers_symbols=absent")
        print("compiled_reject_gate=fail-closed-no-cpu-on")
        print("compiled_handoff=one-enable-one-balanced-disable-read-only-late")
        print("package_dtb_i2c6=disabled")
        print("package_dtb_handoff_owner=enabled")
        print("package_dtb_handoff_clock=infracfg-i2c-appm-54")
        print("package_dtb_role=nonfinal-build-output")
        for key, value in calibration.items():
            print(f"calibration_{key}={value}")
        print("output_hashes_pinned=no")
        print("artifact_build=none")
        print("device_access=none")
        print("storage_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        gzip.BadGzipFile,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
