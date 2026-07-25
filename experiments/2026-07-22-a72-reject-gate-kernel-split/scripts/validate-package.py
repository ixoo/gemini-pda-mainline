#!/usr/bin/env python3
"""Validate Candidate AI's exact AD + corrected-0092 package boundary."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import pathlib
import re
import stat
import struct
import sys
import zlib
from typing import Any

sys.dont_write_bytecode = True


AD_PROFILE = "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-"
    "smp8-a72-reject-gate"
)
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
]
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
AD_PATCHSET_SHA256 = "efb79d0ced5ebee485e337f224075faaa4abf7eb7d5e6a38326383274cd75f93"
AD_SERIES_SHA256 = "124db1a0c4d3d4f5ee43d75bbced9d4b5f28a649ef92c04acdb8ccb67be4117a"
AD_SERIES_REL = "patches/series"
AI_SERIES_REL = "patches/series-a72-reject-gate"
AI_PATCHSET_SHA256 = "ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd"
AI_SERIES_SHA256 = "b172d419cc1e331932e734dda57be076872a442719dd6d406b217d81547dfd00"
PATCH_0092 = "v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch"
PATCH_0092_SHA256 = "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5"
AD_CONFIG_INPUTS_SHA256 = "37223bd4a7e2e3ed0852b9dfe3ea4f5e4268b4e7db69d9cf40eafabf75441a67"
AI_CONFIG_INPUTS_SHA256 = "ad93d6669bd261cf1171237328dd9209fd45b2c3ed2154e441a1951908da4ba1"
AD_CONFIG_SHA256 = "32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46"
AD_IMAGE_GZ_SHA256 = "1ab084bd427f9fade4adb43a83cca879c3289929485ad1469c6dffa539d3548b"
AD_SYSTEM_MAP_SHA256 = "63dc89816c1cee5b62e3f514e12512b199415e81be37f5577168465787a42890"
AD_PACKAGE_DTB_SHA256 = "f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5"
AD_NORMALIZED_BUILD_SHA256 = "41e930eb6743b3d145c7f4e10155b3d8e1e807931bd858736de9b27fda3dd0d5"
AD_PACKAGE_MANIFEST_SHA256S = {
    "1fbdb9aa20737e081cdcba2086f3ae435e702d44090e94e9cb47d0e3224816ab",
    "c601cdc3b6317d98d6781fe8b64add043505c935da503f42233e2dd2a8a546f9",
}
AF_IMAGE_GZ_SHA256 = "b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912"
AF_SYSTEM_MAP_SHA256 = "a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d"
FDT_PARSER_SHA256 = "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"
KERNEL_RELEASE = "7.1.3-gemini-observability-L"
COMPILER = "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
LINKER = "GNU ld (GNU Binutils for Ubuntu) 2.42"
GEMINI_DTB = "dtbs/mediatek/mt6797-gemini-pda.dtb"
MT6797_DTBS = [
    "mediatek/mt6797-evb.dtb",
    "mediatek/mt6797-gemini-pda.dtb",
    "mediatek/mt6797-x20-dev.dtb",
]

LK_KERNEL_ADDR = 0x40200000
LK_MT6797_DECOMPRESS_LIMIT = 0x03200000
ARM64_PLACEMENT_ALIGNMENT = 0x00200000
LK_ARM64_IMAGE_FLAGS = 0x0A
ARM64_MAGIC = b"ARM\x64"
PACKAGE_DIRECTORY_MODE = 0o775
PACKAGE_DEFAULT_FILE_MODE = 0o644
PACKAGE_GENERATED_FILE_MODE = 0o664

CMDLINE = (
    "console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr ignore_loglevel "
    "loglevel=8 log_buf_len=1M initcall_debug rdinit=/init panic=0 "
    "g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32"
)
REQUIRED_CONFIG = {
    f'CONFIG_CMDLINE="{CMDLINE}"',
    "CONFIG_CMDLINE_FORCE=y",
    "CONFIG_SMP=y",
    "CONFIG_NR_CPUS=512",
    "CONFIG_HOTPLUG_CPU=y",
    "CONFIG_ARM_PSCI_FW=y",
    "CONFIG_ARM_ARCH_TIMER=y",
    "CONFIG_ARM_GIC_V3=y",
    "CONFIG_ARCH_MEDIATEK=y",
    "CONFIG_FB_SIMPLE=y",
    "CONFIG_USB_GADGET=y",
    "# CONFIG_REGULATOR_DA9211 is not set",
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
FORBIDDEN_ENABLED_CONFIG = {
    "CONFIG_REGULATOR_DA9211=y",
    "CONFIG_MTK_MT6797_A72_POWER=y",
}
REQUIRED_KERNEL_MARKERS = (
    b"mediatek,mt6797-psci\0",
    b"CPU%u boot rejected: A72 power sequence inactive\n\0",
)
FORBIDDEN_KERNEL_MARKERS = (
    b"mediatek,mt6797-a72-power\0",
    b"observer-v1\n\0",
    b"observe-only\n\0",
    b"dlg,da9214\0",
    b"initcall_blacklist=mt6797_a72_power_driver_init",
)
REQUIRED_SYSTEM_MAP = {
    "mt6797_psci_cpu_init",
    "mt6797_psci_cpu_prepare",
    "mt6797_psci_cpu_boot",
    "mt6797_psci_cpu_can_disable",
    "mt6797_psci_ops",
}
FORBIDDEN_SYSTEM_MAP_FRAGMENTS = (
    "mt6797_a72_power",
    "da9211_regulator_driver_init",
    "da9211_regulator_driver_exit",
    "mt6797_psci_cpu_disable",
    "mt6797_psci_cpu_die",
    "mt6797_psci_cpu_kill",
)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    value = json.loads(read_regular(path, label).decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object")
    return value


def normalized_build_bytes(value: dict[str, Any], label: str) -> bytes:
    if "generated_utc" not in value:
        raise ValueError(f"{label} lacks generated_utc")
    normalized = dict(value)
    del normalized["generated_utc"]
    return (json.dumps(normalized, indent=2, sort_keys=True) + "\n").encode()


def inventory(root: pathlib.Path) -> dict[str, pathlib.Path]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe package tree: {root}")
    if stat.S_IMODE(info.st_mode) != PACKAGE_DIRECTORY_MODE:
        raise ValueError(f"package directory mode changed: {root}")
    result: dict[str, pathlib.Path] = {}
    directories: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        path_info = path.lstat()
        if path.is_symlink():
            raise ValueError(f"package contains a symlink: {relative}")
        if stat.S_ISREG(path_info.st_mode):
            result[relative] = path
        elif stat.S_ISDIR(path_info.st_mode):
            if stat.S_IMODE(path_info.st_mode) != PACKAGE_DIRECTORY_MODE:
                raise ValueError(f"package directory mode changed: {relative}")
            directories.add(relative)
        else:
            raise ValueError(f"package contains a special entry: {relative}")

    expected_directories: set[str] = set()
    for relative in result:
        parent = pathlib.PurePosixPath(relative).parent
        while parent != pathlib.PurePosixPath("."):
            expected_directories.add(parent.as_posix())
            parent = parent.parent
    if directories != expected_directories:
        missing = sorted(expected_directories - directories)
        extra = sorted(directories - expected_directories)
        raise ValueError(
            f"package directory inventory changed: missing={missing}, extra={extra}"
        )
    return result


def expected_package_file_mode(relative: str) -> int:
    """Return the exact mode emitted by the pinned kernel packager."""

    if (
        relative == "SHA256SUMS"
        or relative == "provenance/build.json"
        or relative.startswith("dtbs/")
    ):
        return PACKAGE_GENERATED_FILE_MODE
    return PACKAGE_DEFAULT_FILE_MODE


def validate_package_file_modes(
    members: dict[str, pathlib.Path], label: str
) -> None:
    for relative, path in members.items():
        actual = stat.S_IMODE(path.stat().st_mode)
        expected = expected_package_file_mode(relative)
        if actual != expected:
            raise ValueError(
                f"{label} package mode changed: {relative}: "
                f"expected {expected:04o}, found {actual:04o}"
            )


def decompress_lk_image_gz(data: bytes, label: str) -> bytes:
    """Return one bounded LK-compatible arm64 Image gzip member."""

    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        image = decompressor.decompress(data, LK_MT6797_DECOMPRESS_LIMIT + 1)
        if len(image) > LK_MT6797_DECOMPRESS_LIMIT or decompressor.unconsumed_tail:
            raise ValueError(f"{label} exceeds the MT6797 LK decompression limit")
        image += decompressor.flush()
    except zlib.error as exc:
        raise ValueError(f"{label} gzip payload is invalid: {exc}") from exc
    if not decompressor.eof:
        raise ValueError(f"{label} gzip stream is truncated")
    if decompressor.unused_data or decompressor.unconsumed_tail:
        raise ValueError(f"{label} must contain exactly one gzip stream")
    if not image:
        raise ValueError(f"{label} expands empty")
    if len(image) > LK_MT6797_DECOMPRESS_LIMIT:
        raise ValueError(f"{label} exceeds the MT6797 LK decompression limit")
    if len(image) < 64 or image[56:60] != ARM64_MAGIC:
        raise ValueError(f"{label} does not contain an arm64 Image")
    text_offset, image_size, flags = struct.unpack_from("<3Q", image, 8)
    if not 0 < image_size <= LK_MT6797_DECOMPRESS_LIMIT:
        raise ValueError(f"{label} arm64 image_size is invalid")
    if flags != LK_ARM64_IMAGE_FLAGS:
        raise ValueError(f"{label} arm64 flags differ from the LK handoff contract")
    if LK_KERNEL_ADDR < text_offset:
        raise ValueError(f"{label} arm64 text_offset exceeds the kernel address")
    if (LK_KERNEL_ADDR - text_offset) % ARM64_PLACEMENT_ALIGNMENT:
        raise ValueError(f"{label} arm64 placement is not 2 MiB aligned")
    return image


def validate_manifest(package: pathlib.Path) -> dict[str, pathlib.Path]:
    members = inventory(package)
    lines = read_regular(package / "SHA256SUMS", "package manifest").decode(
        "ascii"
    ).splitlines()
    seen: set[str] = set()
    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("package manifest is malformed")
        relative = fields[1].removeprefix("*").removeprefix("./")
        if relative in seen or relative == "SHA256SUMS" or relative not in members:
            raise ValueError("package manifest path is unsafe, missing, or duplicated")
        if digest_bytes(read_regular(members[relative], relative)) != fields[0]:
            raise ValueError(f"package checksum mismatch: {relative}")
        seen.add(relative)
    if seen != set(members) - {"SHA256SUMS"}:
        raise ValueError("package manifest is not an exact inventory")
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
            or len(path.parts) < 2
            or any(character.isspace() for character in line)
        ):
            raise ValueError(f"unsafe patch-series entry at line {number}")
        result.append(line)
    if len(result) != len(set(result)):
        raise ValueError("patch series contains a duplicate entry")
    return result


def patch_inventory(root: pathlib.Path) -> dict[str, pathlib.Path]:
    return inventory(root)


def patchset_digest(series: bytes, root: pathlib.Path, series_rel: str) -> str:
    records = [f"{digest_bytes(series)}  {series_rel}\n"]
    for entry in series_entries(series):
        data = read_regular(root / entry, f"patch {entry}")
        records.append(f"{digest_bytes(data)}  {entry}\n")
    return digest_bytes("".join(records).encode("ascii"))


def validate_series_contract(
    ad_series: bytes,
    ad_patch_root: pathlib.Path,
    candidate_series: bytes,
    candidate_patch_root: pathlib.Path,
    corrected_patch: bytes,
    *,
    expected_ad_series_hash: str = AD_SERIES_SHA256,
    expected_ad_patchset_hash: str = AD_PATCHSET_SHA256,
    expected_ai_series_hash: str = AI_SERIES_SHA256,
    expected_ai_patchset_hash: str = AI_PATCHSET_SHA256,
    expected_patch_hash: str = PATCH_0092_SHA256,
) -> str:
    ad_entries = series_entries(ad_series)
    candidate_entries = series_entries(candidate_series)
    if digest_bytes(ad_series) != expected_ad_series_hash or len(ad_entries) != 88:
        raise ValueError("baseline series is not exact Candidate AD")
    if ad_entries[-1].split("/", 1)[-1][:4] != "0087":
        raise ValueError("Candidate AD series does not end at patch 0087")
    if patchset_digest(ad_series, ad_patch_root, AD_SERIES_REL) != expected_ad_patchset_hash:
        raise ValueError("baseline patch tree is not exact Candidate AD")
    if digest_bytes(corrected_patch) != expected_patch_hash:
        raise ValueError("corrected patch 0092 identity changed")
    if digest_bytes(candidate_series) != expected_ai_series_hash:
        raise ValueError("Candidate AI series checksum changed")
    if candidate_entries != [*ad_entries, PATCH_0092] or len(candidate_entries) != 89:
        raise ValueError("Candidate AI series ordering changed")
    for forbidden in ("/0088-", "/0089-", "/0090-", "/0091-", "/0093-"):
        if any(forbidden in f"/{entry}" for entry in candidate_entries):
            raise ValueError(f"Candidate AI includes forbidden series feature {forbidden}")

    ad_members = patch_inventory(ad_patch_root)
    candidate_members = patch_inventory(candidate_patch_root)
    if set(ad_members) != set(ad_entries):
        raise ValueError("Candidate AD patch provenance inventory changed")
    if set(candidate_members) != set(candidate_entries):
        raise ValueError("Candidate AI patch provenance inventory changed")
    for entry in ad_entries:
        if read_regular(ad_members[entry], entry) != read_regular(
            candidate_members[entry], entry
        ):
            raise ValueError(f"Candidate AI changed inherited AD patch: {entry}")
    if read_regular(candidate_members[PATCH_0092], PATCH_0092) != corrected_patch:
        raise ValueError("Candidate AI packaged a different patch 0092")
    patch_text = corrected_patch.decode("utf-8")
    if (
        "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)" not in patch_text
        or "+\treturn false;" not in patch_text
        or "+\treturn true;" in patch_text
    ):
        raise ValueError("patch 0092 does not contain the corrected disable gate")
    patchset = patchset_digest(candidate_series, candidate_patch_root, AI_SERIES_REL)
    if patchset != expected_ai_patchset_hash:
        raise ValueError("Candidate AI patchset checksum changed")
    return patchset


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


def config_inputs_digest(profile: str, fragments: dict[str, bytes]) -> str:
    records = [f"profile={profile}\n", "base=defconfig\n"]
    for relative in FRAGMENTS:
        records.append(f"{digest_bytes(fragments[relative])}  {relative}\n")
    return digest_bytes("".join(records).encode("ascii"))


def fragment_inventory(
    package: pathlib.Path, profile: str, expected_digest: str
) -> dict[str, bytes]:
    files = inventory(package / "provenance/configs")
    expected = {pathlib.PurePosixPath(path).name for path in FRAGMENTS}
    if set(files) != expected:
        raise ValueError("packaged configuration-fragment inventory changed")
    result: dict[str, bytes] = {}
    for relative in FRAGMENTS:
        name = pathlib.PurePosixPath(relative).name
        result[relative] = read_regular(files[name], f"fragment {name}")
    if config_inputs_digest(profile, result) != expected_digest:
        raise ValueError(f"configuration inputs changed for profile {profile}")
    return result


def validate_kernel_policy(
    image: bytes,
    system_map_data: bytes,
    config_data: bytes,
    *,
    expected_config_hash: str = AD_CONFIG_SHA256,
) -> None:
    if digest_bytes(config_data) != expected_config_hash:
        raise ValueError("resolved configuration is not exact Candidate AD")
    config_map(config_data)
    lines = set(config_data.decode("utf-8").splitlines())
    missing = REQUIRED_CONFIG - lines
    if missing:
        raise ValueError(f"required AD config line is absent: {sorted(missing)[0]}")
    forbidden = FORBIDDEN_ENABLED_CONFIG & lines
    if forbidden:
        raise ValueError(f"forbidden regulator/observer config is enabled: {sorted(forbidden)[0]}")
    cmdline_tokens = CMDLINE.split()
    if cmdline_tokens.count("maxcpus=8") != 1:
        raise ValueError("exact AD maxcpus=8 policy changed")
    forbidden_tokens = (
        "maxcpus=9", "maxcpus=10", "isolcpus=", "irqaffinity=",
        "regulator_ignore_unused", "initcall_blacklist=", "cpu8", "cpu9",
    )
    if any(token.startswith(forbidden_tokens) for token in cmdline_tokens):
        raise ValueError("forced command line contains an active or observer policy")

    for marker in REQUIRED_KERNEL_MARKERS:
        if marker not in image:
            raise ValueError(f"kernel lacks reject-gate marker: {marker!r}")
    for marker in FORBIDDEN_KERNEL_MARKERS:
        if marker in image:
            raise ValueError(f"kernel contains forbidden 0088-0091 marker: {marker!r}")
    system_map = system_map_data.decode("ascii").splitlines()
    symbols = {line.rsplit(" ", 1)[-1] for line in system_map if " " in line}
    missing_symbols = REQUIRED_SYSTEM_MAP - symbols
    if missing_symbols:
        raise ValueError(f"System.map lacks gate symbol: {sorted(missing_symbols)[0]}")
    for line in system_map:
        if any(fragment in line for fragment in FORBIDDEN_SYSTEM_MAP_FRAGMENTS):
            raise ValueError(f"System.map contains forbidden regulator/observer symbol: {line}")


def load_fdt_parser() -> object:
    experiments = pathlib.Path(__file__).resolve().parents[2]
    source = (
        experiments
        / "2026-07-16-lk-handoff-alignment"
        / "scripts/validate-lk-compatible-dtb.py"
    )
    if digest_bytes(read_regular(source, "source-pinned FDT parser")) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("gemini_ai_fdt", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned FDT parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_gate_auditor() -> object:
    source = pathlib.Path(__file__).resolve().parent / "audit-mt6797-psci-cpu-boot.py"
    spec = importlib.util.spec_from_file_location("gemini_ai_gate_audit", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AI compiled-gate auditor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def phandle_map(tree: dict[str, dict[str, bytes]]) -> dict[int, str]:
    handles: dict[int, str] = {}
    for path, props in tree.items():
        values: list[int] = []
        for name in ("phandle", "linux,phandle"):
            raw = props.get(name)
            if raw is None:
                continue
            if len(raw) != 4:
                raise ValueError(f"{path}:{name} is not one cell")
            values.append(struct.unpack(">I", raw)[0])
        if len(set(values)) > 1:
            raise ValueError(f"{path} has conflicting phandle aliases")
        if not values:
            continue
        value = values[0]
        if not value or (value in handles and handles[value] != path):
            raise ValueError(f"invalid or duplicate phandle at {path}")
        handles[value] = path
    return handles


def validate_resource_free_tree(
    tree: dict[str, dict[str, bytes]],
    label: str,
    *,
    require_disabled_i2c6: bool = False,
) -> None:
    for node in ("/a72-power@10222000", "/i2c@1100e000/regulator@68"):
        if node in tree:
            raise ValueError(f"{label} contains forbidden resource node {node}")
    watchdog = "/watchdog@10007000"
    if watchdog not in tree or "#reset-cells" in tree[watchdog]:
        raise ValueError(f"{label} adds or loses the TOPRGU reset-provider boundary")
    if require_disabled_i2c6:
        i2c6 = "/i2c@1100e000"
        if i2c6 not in tree or tree[i2c6].get("status") != b"disabled\0":
            raise ValueError(f"{label} changed the disabled Gemini I2C6 boundary")
    forbidden = (b"mediatek,mt6797-a72-power\0", b"dlg,da9214\0", b"vproc-big\0")
    for path, props in tree.items():
        for name, value in props.items():
            if any(marker in value for marker in forbidden):
                raise ValueError(f"{label} contains a forbidden resource property {path}:{name}")


def validate_dtb_delta(
    baseline_path: pathlib.Path,
    candidate_path: pathlib.Path,
    *,
    expected_baseline_hash: str | None = AD_PACKAGE_DTB_SHA256,
) -> None:
    baseline_data = read_regular(baseline_path, "Candidate AD package DTB")
    read_regular(candidate_path, "Candidate AI package DTB")
    if expected_baseline_hash is not None and digest_bytes(baseline_data) != expected_baseline_hash:
        raise ValueError("baseline package DTB is not exact Candidate AD")
    fdt = load_fdt_parser()
    baseline, base_reservations, base_boot_cpu = fdt.parse_fdt(baseline_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(candidate_path)
    if candidate_reservations != base_reservations:
        raise ValueError("Candidate AI package DTB changed the reservation map")
    if candidate_boot_cpu != base_boot_cpu:
        raise ValueError("Candidate AI package DTB changed boot_cpuid_phys")
    if phandle_map(candidate) != phandle_map(baseline):
        raise ValueError("Candidate AI package DTB changed the phandle map")
    require_disabled_i2c6 = expected_baseline_hash is not None
    validate_resource_free_tree(
        baseline,
        "Candidate AD package DTB",
        require_disabled_i2c6=require_disabled_i2c6,
    )
    validate_resource_free_tree(
        candidate,
        "Candidate AI package DTB",
        require_disabled_i2c6=require_disabled_i2c6,
    )

    expected = copy.deepcopy(baseline)
    for path, reg in (("/cpus/cpu@200", 0x200), ("/cpus/cpu@201", 0x201)):
        fdt.require_prop(baseline, path, "compatible", fdt.string("arm,cortex-a72"))
        fdt.require_prop(baseline, path, "reg", fdt.cells(reg))
        fdt.require_prop(baseline, path, "enable-method", fdt.string("psci"))
        expected[path]["enable-method"] = fdt.string("mediatek,mt6797-psci")
    for path in (
        "/cpus/cpu@0", "/cpus/cpu@1", "/cpus/cpu@2", "/cpus/cpu@3",
        "/cpus/cpu@100", "/cpus/cpu@101", "/cpus/cpu@102", "/cpus/cpu@103",
    ):
        fdt.require_prop(baseline, path, "enable-method", fdt.string("psci"))
    if candidate != expected:
        raise ValueError("package DTB delta is not exactly the two A72 enable methods")


def validate_manifest_contract(data: bytes, label: str, *, require_ai: bool) -> None:
    value = json.loads(data.decode("utf-8"))
    expected_kernel = {
        "version": "7.1.3",
        "released": "2026-07-04",
        "source_url": "https://cdn.kernel.org/pub/linux/kernel/v7.x/linux-7.1.3.tar.xz",
        "sha256": SOURCE_SHA256,
    }
    if (
        not isinstance(value, dict)
        or set(value) != {"schema", "kernel", "architecture", "patch_series", "config"}
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
        raise ValueError(f"{label} configuration contract is absent")
    profiles = config.get("profiles")
    expected_ad = {"base": "defconfig", "fragments": FRAGMENTS}
    expected_ai = {
        "base": "defconfig",
        "patch_series": AI_SERIES_REL,
        "fragments": FRAGMENTS,
    }
    if not isinstance(profiles, dict) or profiles.get(AD_PROFILE) != expected_ad:
        raise ValueError(f"{label} exact AD profile changed")
    if require_ai and profiles.get(PROFILE) != expected_ai:
        raise ValueError(f"{label} path-selected Candidate AI profile changed")
    if PROFILE in profiles and profiles[PROFILE] != expected_ai:
        raise ValueError(f"{label} present Candidate AI profile is malformed")


def expected_build_fields(
    profile: str, patchset: str, config_inputs: str
) -> dict[str, object]:
    return {
        "schema": 1,
        "build_profile": profile,
        "base_config": "defconfig",
        "config_fragments": FRAGMENTS,
        "source_sha256": SOURCE_SHA256,
        "patchset_sha256": patchset,
        "config_sha256": AD_CONFIG_SHA256,
        "config_inputs_sha256": config_inputs,
        "modules_built": False,
        "kernel_release": KERNEL_RELEASE,
        "compiler": COMPILER,
        "linker": LINKER,
    }


def require_build_fields(
    value: dict[str, Any], profile: str, patchset: str,
    config_inputs: str, label: str
) -> None:
    expected_fields = expected_build_fields(profile, patchset, config_inputs)
    inventories = (set(expected_fields), set(expected_fields) | {"generated_utc"})
    if set(value) not in inventories:
        raise ValueError(f"{label} build provenance inventory changed")
    for key, expected in expected_fields.items():
        if value.get(key) != expected:
            raise ValueError(f"{label} build provenance changed: {key}")


def validate_package(
    ad_package: pathlib.Path,
    candidate_package: pathlib.Path,
    patch_path: pathlib.Path,
) -> None:
    if ad_package == candidate_package or ad_package.samefile(candidate_package):
        raise ValueError("AD and AI packages must be independent trees")
    ad_members = validate_manifest(ad_package)
    candidate_members = validate_manifest(candidate_package)
    if digest_bytes(
        read_regular(ad_package / "SHA256SUMS", "AD package manifest")
    ) not in AD_PACKAGE_MANIFEST_SHA256S:
        raise ValueError("baseline package manifest is not an exact accepted Candidate AD build")
    extra_patch_member = f"provenance/patches/{PATCH_0092}"
    if set(candidate_members) != set(ad_members) | {extra_patch_member}:
        raise ValueError("Candidate AI package inventory is not exact AD plus patch 0092")
    validate_package_file_modes(ad_members, "Candidate AD")
    validate_package_file_modes(candidate_members, "Candidate AI")

    ad_series = read_regular(ad_package / "provenance/series", "AD series")
    candidate_series = read_regular(candidate_package / "provenance/series", "AI series")
    corrected_patch = read_regular(patch_path, "corrected repository patch 0092")
    patchset = validate_series_contract(
        ad_series,
        ad_package / "provenance/patches",
        candidate_series,
        candidate_package / "provenance/patches",
        corrected_patch,
    )

    expected_ad_name = (
        f"linux-7.1.3-gemini-{AD_PROFILE}-{AD_PATCHSET_SHA256[:8]}-"
        f"{AD_CONFIG_INPUTS_SHA256[:8]}"
    )
    expected_ai_name = (
        f"linux-7.1.3-gemini-{PROFILE}-{AI_PATCHSET_SHA256[:8]}-"
        f"{AI_CONFIG_INPUTS_SHA256[:8]}"
    )
    if ad_package.name != expected_ad_name:
        raise ValueError("baseline package basename is not exact Candidate AD")
    if candidate_package.name != expected_ai_name:
        raise ValueError("Candidate AI package basename disagrees with its inputs")

    ad_build = load_json(ad_package / "provenance/build.json", "AD build")
    candidate_build = load_json(candidate_package / "provenance/build.json", "AI build")
    require_build_fields(
        ad_build, AD_PROFILE, AD_PATCHSET_SHA256, AD_CONFIG_INPUTS_SHA256, "AD"
    )
    require_build_fields(
        candidate_build, PROFILE, patchset, AI_CONFIG_INPUTS_SHA256, "AI"
    )
    if digest_bytes(normalized_build_bytes(ad_build, "AD build")) != AD_NORMALIZED_BUILD_SHA256:
        raise ValueError("baseline normalized provenance is not exact Candidate AD")
    validate_manifest_contract(
        read_regular(ad_package / "provenance/kernel-manifest.json", "AD manifest"),
        "AD packaged manifest",
        require_ai=False,
    )
    validate_manifest_contract(
        read_regular(candidate_package / "provenance/kernel-manifest.json", "AI manifest"),
        "AI packaged manifest",
        require_ai=True,
    )

    ad_fragments = fragment_inventory(
        ad_package, AD_PROFILE, AD_CONFIG_INPUTS_SHA256
    )
    candidate_fragments = fragment_inventory(
        candidate_package, PROFILE, AI_CONFIG_INPUTS_SHA256
    )
    if ad_fragments != candidate_fragments:
        raise ValueError("Candidate AI changed an exact AD configuration fragment")
    ad_config = read_regular(ad_package / "kernel.config", "AD config")
    candidate_config = read_regular(candidate_package / "kernel.config", "AI config")
    if candidate_config != ad_config or digest_bytes(ad_config) != AD_CONFIG_SHA256:
        raise ValueError("Candidate AI resolved config is not byte-exact Candidate AD")

    ad_image_gz = read_regular(ad_package / "Image.gz", "AD Image.gz")
    ad_system_map = read_regular(ad_package / "System.map", "AD System.map")
    if digest_bytes(ad_image_gz) != AD_IMAGE_GZ_SHA256:
        raise ValueError("baseline Image.gz is not exact Candidate AD")
    if digest_bytes(ad_system_map) != AD_SYSTEM_MAP_SHA256:
        raise ValueError("baseline System.map is not exact Candidate AD")
    image = read_regular(candidate_package / "Image", "AI Image")
    image_gz = read_regular(candidate_package / "Image.gz", "AI Image.gz")
    system_map = read_regular(candidate_package / "System.map", "AI System.map")
    if decompress_lk_image_gz(image_gz, "Candidate AI Image.gz") != image:
        raise ValueError("Candidate AI Image.gz does not expand to Image")
    if digest_bytes(image_gz) in (AD_IMAGE_GZ_SHA256, AF_IMAGE_GZ_SHA256):
        raise ValueError("Candidate AI reused an AD or AF kernel output")
    if digest_bytes(system_map) in (AD_SYSTEM_MAP_SHA256, AF_SYSTEM_MAP_SHA256):
        raise ValueError("Candidate AI reused an AD or AF System.map")
    validate_kernel_policy(image, system_map, candidate_config)
    gate_auditor = load_gate_auditor()
    gate_audit = gate_auditor.audit_kernel(
        candidate_package / "Image", candidate_package / "System.map"
    )

    ad_dtbs = inventory(ad_package / "dtbs")
    candidate_dtbs = inventory(candidate_package / "dtbs")
    if set(ad_dtbs) != set(candidate_dtbs):
        raise ValueError("Candidate AI DTB inventory changed")
    if digest_bytes(read_regular(ad_package / GEMINI_DTB, "AD Gemini DTB")) != AD_PACKAGE_DTB_SHA256:
        raise ValueError("baseline package Gemini DTB is not exact Candidate AD")
    changed_dtbs: list[str] = []
    for relative in sorted(ad_dtbs):
        old = read_regular(ad_dtbs[relative], f"AD DTB {relative}")
        new = read_regular(candidate_dtbs[relative], f"AI DTB {relative}")
        if old == new:
            continue
        validate_dtb_delta(ad_dtbs[relative], candidate_dtbs[relative], expected_baseline_hash=None)
        changed_dtbs.append(relative)
    if changed_dtbs != MT6797_DTBS:
        raise ValueError("Candidate AI DTB delta is not exact for all three MT6797 boards")
    validate_dtb_delta(ad_package / GEMINI_DTB, candidate_package / GEMINI_DTB)

    print("validation=candidate-ai-ad-plus-corrected-0092-package")
    print(f"package={candidate_package.name}")
    print(f"profile={PROFILE}")
    print("patch_count=89")
    print(f"series_path={AI_SERIES_REL}")
    print(f"series_sha256={AI_SERIES_SHA256}")
    print(f"patchset_sha256={patchset}")
    print("patch_delta_from_ad=corrected-0092-only")
    print("patches_0088_0091=absent")
    print(f"config_inputs_sha256={AI_CONFIG_INPUTS_SHA256}")
    print(f"config_sha256={AD_CONFIG_SHA256}")
    print("resolved_config_lineage=byte-exact-candidate-ad")
    print(f"image_sha256={digest_bytes(image)}")
    print(f"image_gz_sha256={digest_bytes(image_gz)}")
    print(f"system_map_sha256={digest_bytes(system_map)}")
    print(f"compiled_gate_audit_sha256={digest_bytes(gate_audit)}")
    print("compiled_gate_calls=logging-only-no-psci-cpu-on")
    print(f"package_dtb_sha256={digest_bytes(read_regular(candidate_package / GEMINI_DTB, 'AI Gemini DTB'))}")
    print("package_dtb_delta=cpu8-and-cpu9-enable-method-only")
    print("cpu_policy=maxcpus-8-cpu8-cpu9-not-requested")
    print("regulator_reset_observer_paths=absent")
    print("active_cpu_request=none")
    print("package_directory_inventory=exact-nonempty-0775")
    print("new_output_identities=pending-reproduction-record")
    print("device_access=none")


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} path")
    return path.resolve(strict=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ad-package", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-package", type=pathlib.Path, required=True)
    parser.add_argument("--patch-0092", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        ad = resolve_directory(args.ad_package, "AD package")
        candidate = resolve_directory(args.candidate_package, "AI package")
        validate_package(ad, candidate, args.patch_0092.resolve(strict=True))
        return 0
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
