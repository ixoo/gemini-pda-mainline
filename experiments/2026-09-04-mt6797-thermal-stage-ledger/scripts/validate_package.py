#!/usr/bin/env python3
"""Validate the exact MT6797 thermal-stage-ledger production package."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import stat
import struct
import subprocess
from pathlib import Path, PurePosixPath


PROFILE = "mt6797-thermal-stage-ledger"
ORIGIN = "https://github.com/ixoo/gemini-pda-mainline.git"
BUILD_COMMIT = "b66b03c722cd67584fb8fb15de493ebb084954b4"
KERNEL_RELEASE = "7.1.3-gemini-mt6797-thermal-stage-ledger"
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
PATCHSET_SHA256 = "593cac6163b1b4084da791cd68be803dc8452a68cea3ec590d299367cf313cd4"
CONFIG_SHA256 = "f0a135b24055229447d56ae6bda16e1ada683ebe4612af3ba0b96ec7febd375a"
IMAGE_SHA256 = "14f1a31e5bff236bf56972717d1364e03e9b1fcda992066c28a36b177703de1e"
IMAGE_GZ_SHA256 = "3e1ebb8de1aeb9ff1c6c6cbe655f18d1affd751959967bfd85507d280dedd2a2"
SYSTEM_MAP_SHA256 = "dc7809a74259d616afe263a3f2846cd48edf1e6cbafe5d68483f844604f78c88"
BASE_DTB = "dtbs/mediatek/mt6797-gemini-pda.dtb"
BASE_DTB_SHA256 = "d7b583545fc3b4916c363d9e4b70d0ee7aef815675ca8ba58894bdbaa2e1dccc"
SERVICE_DTB = "dtbs/mediatek/mt6797-gemini-pda-thermal-serviceability.dtb"
SERVICE_DTB_SHA256 = "966351e9795e1aaada61d6d9c3d2280b1413ca6a4493d03b5dd8c3425bd4aaa3"
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
    "configs/gemini-mt6797-thermal-stage-ledger.fragment",
]
REQUIRED_CONFIG = (
    'CONFIG_LOCALVERSION="-gemini-mt6797-thermal-stage-ledger"',
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
    "CONFIG_THERMAL=y",
    "CONFIG_THERMAL_OF=y",
    "CONFIG_MTK_THERMAL=y",
    "CONFIG_MTK_SOC_THERMAL=y",
    "CONFIG_NVMEM=y",
    "CONFIG_NVMEM_MTK_ATAG_DEVINFO=y",
    "CONFIG_MTK_MT6797_DVFSP_HANDOFF=y",
    "CONFIG_PSTORE=y",
    "CONFIG_PSTORE_RAM=y",
    "CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER=y",
    "# CONFIG_KUNIT is not set",
    "# CONFIG_CPU_FREQ is not set",
    "# CONFIG_CPU_IDLE is not set",
    "# CONFIG_SUSPEND is not set",
    "# CONFIG_MODULES is not set",
)
FORBIDDEN_CONFIG = (
    "CONFIG_COMMON_CLK_MT6797_RESET_KUNIT_TEST=y",
    "CONFIG_MTK_SOC_THERMAL_KUNIT_TEST=y",
    "CONFIG_MTK_SOC_THERMAL_TRANSACTION_KUNIT_TEST=y",
    "CONFIG_PSTORE_GEMINI_MT6797_THERMAL_LEDGER_KUNIT_TEST=y",
)
REQUIRED_SYMBOLS = (
    " pwrap_probe\n",
    " mt6351_regulator_probe\n",
    " msdc_drv_probe\n",
    " mt6797_atag_devinfo_probe\n",
    " mt6797_thermal_first_sample\n",
    " gemini_mt6797_thermal_ledger_begin\n",
    " gemini_mt6797_thermal_ledger_checkpoint\n",
    " mt6797_thermal_trace\n",
    " mtk_thermal_probe\n",
    " mtk_register_reset_controller_with_dev\n",
    " mtk_reset_assert_set_clr\n",
    " mtk_reset_deassert_set_clr\n",
    " mt6797_dvfsp_handoff_is_ready_atomic\n",
)
THERMAL_PATCHES = {
    "v7.1.3/0512-thermal-mediatek-require-valid-MT6797-calibration.patch":
        "d27656cdd77c808927d6c097d79773570205e8357a2fbbd14502244c794c8a72",
    "v7.1.3/0513-thermal-mediatek-test-calibration-requirement-policy.patch":
        "6a0c947f15a1d2fae0a39a34e1aaf2907212b2761bd8cf538d60726a0596431a",
    "v7.1.3/0514-dt-bindings-reset-mediatek-correct-MT6797-infracfg-resets.patch":
        "7b7e88138f47892b642c230c9ac9e9306f06a467e397a0cc9f3f96c0791351a7",
    "v7.1.3/0515-clk-mediatek-repair-MT6797-infracfg-resets.patch":
        "4b11d7021bc3c6f033ce2fdec34fef39df442fae2df9be759a5d591763cfb562",
    "v7.1.3/0516-clk-mediatek-test-MT6797-infracfg-reset-translation.patch":
        "6eee979cc78256f008d08ddf2dd5d9e46650c6729f5a37d9b9011bfcbd9391d7",
    "v7.1.3/0517-thermal-mediatek-add-MT6797-ordered-transaction.patch":
        "0294379afe28944485b4e07c49e55db2e845ac1609d7af44403b5a8df2324a9d",
    "v7.1.3/0518-thermal-mediatek-test-MT6797-ordered-transaction.patch":
        "456e4651d806538088f1533be40b3f51d432f2fe7ca31c769884c6fd74769ec2",
    "v7.1.3/0519-arm64-dts-mediatek-add-MT6797-thermal-reset.patch":
        "d6fedffc8e8aaf69e4a53f62b630a0058916d7265172028ea19a048fe736e56c",
    "v7.1.3/0520-arm64-dts-mediatek-add-Gemini-thermal-serviceability.patch":
        "0bfcf858c289605fe26bb53320a86949d3aea2c7dc953d4ec8e4de9f27890fcb",
    "v7.1.3/0521-pstore-add-Gemini-MT6797-thermal-stage-ledger.patch":
        "ad6b9c2068de438749dc8681e3637be0a49279620effcfba7e7840558e3c26b4",
    "v7.1.3/0522-pstore-test-Gemini-MT6797-thermal-stage-ledger.patch":
        "6a6cdb3ff9391ca166d1529df6d10500a325cde44ee4310854d2836b65b57d5d",
    "v7.1.3/0523-thermal-mediatek-trace-MT6797-probe-stages.patch":
        "018e9d34c3f642249303b73b4886ec13684a533eb067a7c9e3c4a9898bf0c0e3",
}

FDT_MAGIC = 0xD00DFEED
FDT_BEGIN_NODE = 1
FDT_END_NODE = 2
FDT_PROP = 3
FDT_NOP = 4
FDT_END = 9


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


def u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise PackageError("truncated FDT word")
    return struct.unpack_from(">I", data, offset)[0]


def align4(value: int) -> int:
    return (value + 3) & ~3


def cstring(data: bytes, offset: int, limit: int) -> tuple[str, int]:
    if offset < 0 or offset >= limit:
        raise PackageError("FDT string offset is outside its block")
    end = data.find(b"\0", offset, limit)
    if end < 0:
        raise PackageError("unterminated FDT string")
    try:
        return data[offset:end].decode("ascii"), end + 1
    except UnicodeDecodeError as exc:
        raise PackageError("non-ASCII FDT name") from exc


def parse_fdt(data: bytes) -> tuple[set[str], dict[tuple[str, str], bytes]]:
    if len(data) < 40:
        raise PackageError("FDT header is truncated")
    header = struct.unpack_from(">10I", data, 0)
    magic, total, off_struct, off_strings, _, _, _, _, size_strings, size_struct = header
    if magic != FDT_MAGIC or total != len(data):
        raise PackageError("FDT magic or exact total size changed")
    struct_end = off_struct + size_struct
    strings_end = off_strings + size_strings
    if not (40 <= off_struct < struct_end <= len(data)):
        raise PackageError("invalid FDT structure bounds")
    if not (40 <= off_strings < strings_end <= len(data)):
        raise PackageError("invalid FDT strings bounds")

    nodes: set[str] = set()
    props: dict[tuple[str, str], bytes] = {}
    stack: list[str] = []
    pos = off_struct
    ended = False
    while pos < struct_end:
        token = u32(data, pos)
        pos += 4
        if token == FDT_BEGIN_NODE:
            name, after = cstring(data, pos, struct_end)
            pos = align4(after)
            stack.append(name)
            path = "/" + "/".join(part for part in stack if part)
            if path in nodes:
                raise PackageError(f"duplicate FDT node: {path}")
            nodes.add(path)
        elif token == FDT_END_NODE:
            if not stack:
                raise PackageError("unbalanced FDT end-node token")
            stack.pop()
        elif token == FDT_PROP:
            length = u32(data, pos)
            name_offset = u32(data, pos + 4)
            pos += 8
            value_end = pos + length
            if value_end > struct_end:
                raise PackageError("FDT property exceeds structure block")
            name, _ = cstring(data, off_strings + name_offset, strings_end)
            path = "/" + "/".join(part for part in stack if part)
            key = (path, name)
            if key in props:
                raise PackageError(f"duplicate FDT property: {path}:{name}")
            props[key] = data[pos:value_end]
            pos = align4(value_end)
        elif token == FDT_NOP:
            continue
        elif token == FDT_END:
            if stack:
                raise PackageError("FDT ended with open nodes")
            ended = True
            break
        else:
            raise PackageError(f"unknown FDT token: {token}")
    if not ended:
        raise PackageError("FDT end token is absent")
    return nodes, props


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


def prop(props: dict[tuple[str, str], bytes], path: str, name: str) -> bytes:
    try:
        return props[(path, name)]
    except KeyError as exc:
        raise PackageError(f"required FDT property absent: {path}:{name}") from exc


def validate_dtbs(package: Path) -> None:
    base_data = regular(package / BASE_DTB, "base Gemini DTB")
    service_data = regular(package / SERVICE_DTB, "thermal serviceability DTB")
    if digest(base_data) != BASE_DTB_SHA256 or digest(service_data) != SERVICE_DTB_SHA256:
        raise PackageError("pinned Gemini DTB identity changed")
    base_nodes, base = parse_fdt(base_data)
    service_nodes, service = parse_fdt(service_data)

    thermal = "/thermal@1100b000"
    pwrap = "/pwrap@1000d000"
    auxadc = "/adc@11001000"
    zone = "/thermal-zones/soc-thermal"
    calibration = "/firmware/atag-devinfo/calibration-data@0"
    infracfg = prop(service, thermal, "resets")[:4]
    for props in (base, service):
        if prop(props, "/", "model").split(b"\0", 1)[0] not in (
            b"Planet Computers Gemini PDA",
            b"Planet Computers Gemini PDA (thermal serviceability)",
        ):
            raise PackageError("Gemini model identity changed")
        if prop(props, pwrap, "compatible") != b"mediatek,mt6797-pwrap\0":
            raise PackageError("PWRAP compatible changed")
        if prop(props, pwrap, "resets") != infracfg + struct.pack(">I", 1):
            raise PackageError("PWRAP reset is not exact input 1")
        if prop(props, pwrap + "/pmic", "compatible") != b"mediatek,mt6351\0":
            raise PackageError("MT6351 child changed")
        if prop(props, "/mmc@11230000", "status") != b"okay\0":
            raise PackageError("eMMC status is not okay")
        if prop(props, thermal, "compatible") != b"mediatek,mt6797-thermal\0":
            raise PackageError("thermal compatible changed")
        if prop(props, thermal, "resets") != infracfg + struct.pack(">I", 0):
            raise PackageError("thermal reset is not exact input 0")
        if (thermal, "reset-names") in props:
            raise PackageError("thermal reset unexpectedly gained reset-names")
        if prop(props, thermal, "nvmem-cell-names") != b"calibration-data\0":
            raise PackageError("thermal NVMEM cell name changed")
        if prop(props, thermal, "nvmem-cells") != prop(props, calibration, "phandle"):
            raise PackageError("thermal NVMEM phandle does not name calibration data")
        if prop(props, auxadc, "status") != b"disabled\0":
            raise PackageError("standalone AUXADC consumer is not disabled")

    if prop(base, thermal, "status") != b"disabled\0":
        raise PackageError("base thermal consumer is not disabled")
    if any(path.startswith("/thermal-zones") for path in base_nodes):
        raise PackageError("base DT unexpectedly contains thermal-zone policy")
    if prop(service, "/", "model") != b"Planet Computers Gemini PDA (thermal serviceability)\0":
        raise PackageError("serviceability model is not exact")
    if prop(service, thermal, "status") != b"okay\0":
        raise PackageError("serviceability thermal consumer is not enabled")
    service_zone_nodes = {path for path in service_nodes if path.startswith("/thermal-zones")}
    if service_zone_nodes != {"/thermal-zones", zone}:
        raise PackageError("serviceability DT does not contain exactly one policy-free zone")
    if prop(service, zone, "polling-delay-passive") != struct.pack(">I", 0):
        raise PackageError("passive polling delay changed")
    if prop(service, zone, "polling-delay") != struct.pack(">I", 1000):
        raise PackageError("thermal polling delay changed")
    if prop(service, zone, "thermal-sensors") != prop(service, thermal, "phandle"):
        raise PackageError("thermal zone sensor does not name the MT6797 controller")
    if any("trips" in path or "cooling-map" in path for path in service_nodes):
        raise PackageError("serviceability DT unexpectedly contains thermal policy")


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
    if git(repository, "cat-file", "-t", BUILD_COMMIT) != "commit":
        raise PackageError("pinned Buildbox commit is absent")
    published = subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor", BUILD_COMMIT,
         "origin/main"], check=False,
    )
    if published.returncode != 0:
        raise PackageError("pinned Buildbox commit is not published at origin/main")
    if git(repository, "remote", "get-url", "origin") != ORIGIN:
        raise PackageError("unexpected origin URL")
    if package.parent != repository / "artifacts/buildbox" / BUILD_COMMIT:
        raise PackageError("package is outside the exact Buildbox commit root")

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
    for line in REQUIRED_CONFIG:
        if line not in config_lines:
            raise PackageError(f"required configuration missing: {line}")
    for line in FORBIDDEN_CONFIG:
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
    for symbol in REQUIRED_SYMBOLS:
        if symbol not in system_map:
            raise PackageError(f"required linked symbol absent: {symbol.strip()}")
    series = regular(package / "provenance/series", "packaged series").decode().splitlines()
    selected = [line for line in series if line and not line.startswith("#")]
    if len(selected) != 512:
        raise PackageError("canonical patch count changed")
    for relative, expected_hash in THERMAL_PATCHES.items():
        if selected.count(relative) != 1:
            raise PackageError(f"thermal patch inventory changed: {relative}")
        packaged = regular(package / "provenance/patches" / relative, relative)
        repository_patch = regular(repository / "patches" / relative, relative)
        if packaged != repository_patch or digest(packaged) != expected_hash:
            raise PackageError(f"thermal patch content changed: {relative}")
    validate_dtbs(package)
    return build


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    repository = args.repository.resolve(strict=True)
    package = args.package.resolve(strict=True)
    build = validate(repository, package)
    print("validation=mt6797-thermal-stage-ledger-package")
    print(f"repository_commit={build['repository_commit']}")
    print(f"build_profile={build['build_profile']}")
    print(f"kernel_release={build['kernel_release']}")
    print(f"source_sha256={build['source_sha256']}")
    print(f"patchset_sha256={build['patchset_sha256']}")
    print(f"config_sha256={build['config_sha256']}")
    print(f"image_sha256={IMAGE_SHA256}")
    print(f"image_gz_sha256={IMAGE_GZ_SHA256}")
    print(f"base_dtb_sha256={BASE_DTB_SHA256}")
    print(f"service_dtb_sha256={SERVICE_DTB_SHA256}")
    print("patch_count=512")
    print("thermal_zones=1")
    print("thermal_trips=0")
    print("cooling_maps=0")
    print("standalone_auxadc=disabled")
    print("hardware_action=none")
    print("boot_candidate=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

