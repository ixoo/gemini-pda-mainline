#!/usr/bin/env python3
"""Validate AL as byte-exact AH payload plus the exact resource-only DT."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import pathlib
import stat
import struct
import sys
import zlib
from types import ModuleType

sys.dont_write_bytecode = True

import candidate_al as al


BLACKLIST_TOKEN = b"initcall_blacklist=mt6797_a72_power_driver_init"
REJECTING_METHOD = b"mediatek,mt6797-psci\0"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_ah_boot_validator() -> ModuleType:
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "2026-07-22-ad-contract-af-kernel-split/scripts/validate-boot.py"
    )
    data = read_regular(source, "Candidate AH boot validator")
    if digest(data) != al.AH_BOOT_VALIDATOR_SHA256:
        raise ValueError("source-pinned Candidate AH boot validator changed")
    spec = importlib.util.spec_from_file_location("candidate_al_ah_boot", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AH boot validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_dtb_validator() -> ModuleType:
    source = pathlib.Path(__file__).resolve().with_name("validate-dtb-delta.py")
    spec = importlib.util.spec_from_file_location("candidate_al_dtb_delta", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AL DT validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def exact_ah_member(root: pathlib.Path, member: str, expected: str) -> bytes:
    data = read_regular(root / member, f"exact Candidate AH {member}")
    if digest(data) != expected:
        raise ValueError(f"exact Candidate AH member changed: {member}")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ah-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--dtb", required=True, type=pathlib.Path)
    parser.add_argument("--image-gz", required=True, type=pathlib.Path)
    parser.add_argument("--system-map", required=True, type=pathlib.Path)
    parser.add_argument("--kernel-config", required=True, type=pathlib.Path)
    parser.add_argument("--initramfs", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        info = args.ah_artifact.lstat()
        if (
            args.ah_artifact.is_symlink()
            or not stat.S_ISDIR(info.st_mode)
            or args.ah_artifact.name != al.AH_ARTIFACT_DIR
        ):
            raise ValueError("exact Candidate AH artifact directory is unsafe")
        ah_root = args.ah_artifact.resolve(strict=True)
        ah_boot = exact_ah_member(
            ah_root, al.AH_BOOT_MEMBER, al.AH_RAW_SHA256
        )
        ah_dtb = exact_ah_member(ah_root, al.AH_DTB_MEMBER, al.AH_DTB_SHA256)
        ah_image_gz = exact_ah_member(ah_root, "Image.gz", al.IMAGE_GZ_SHA256)
        ah_system_map = exact_ah_member(
            ah_root, "System.map", al.SYSTEM_MAP_SHA256
        )
        ah_config = exact_ah_member(ah_root, "kernel.config", al.CONFIG_SHA256)
        ah_initramfs = exact_ah_member(
            ah_root, al.AH_INITRAMFS_MEMBER, al.INITRAMFS_SHA256
        )

        candidate = read_regular(args.candidate, "Candidate AL boot")
        dtb = read_regular(args.dtb, "Candidate AL DT")
        image_gz = read_regular(args.image_gz, "Candidate AL Image.gz")
        system_map = read_regular(args.system_map, "Candidate AL System.map")
        config = read_regular(args.kernel_config, "Candidate AL kernel config")
        initramfs = read_regular(args.initramfs, "Candidate AL initramfs")
        if image_gz != ah_image_gz:
            raise ValueError("Candidate AL Image.gz is not byte-exact AH")
        if system_map != ah_system_map:
            raise ValueError("Candidate AL System.map is not byte-exact AH")
        if config != ah_config:
            raise ValueError("Candidate AL kernel config is not byte-exact AH")
        if initramfs != ah_initramfs:
            raise ValueError("Candidate AL initramfs is not byte-exact AH")
        if dtb == ah_dtb:
            raise ValueError("Candidate AL did not add its final-DT delta")

        config_text = config.decode("utf-8", errors="strict")
        expected_cmdline = (
            'CONFIG_CMDLINE="console=ttyS0,921600n8 earlycon maxcpus=8 '
            "nokaslr ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug "
            "rdinit=/init panic=0 g_ether.dev_addr=42:00:15:19:82:01 "
            "g_ether.host_addr=42:00:15:19:82:00 "
            "g_ether.iManufacturer=gemini-pda-mainline "
            "g_ether.iProduct=Gemini-L-Observability "
            "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
            "clk_ignore_unused fbcon=rotate:3 consoleblank=0 "
            "fbcon=font:TER16x32 regulator_ignore_unused "
            'initcall_blacklist=mt6797_a72_power_driver_init"'
        )
        if config_text.splitlines().count(expected_cmdline) != 1:
            raise ValueError("Candidate AL exact maxcpus=8/blacklist command line changed")
        for required in (
            "CONFIG_CMDLINE_FORCE=y",
            "CONFIG_REGULATOR_DA9211=y",
            "CONFIG_MTK_MT6797_A72_POWER=y",
        ):
            if config_text.splitlines().count(required) != 1:
                raise ValueError(f"Candidate AL required config changed: {required}")
        map_text = system_map.decode("ascii", errors="strict")
        if len(
            [
                line
                for line in map_text.splitlines()
                if line.endswith(" mt6797_a72_power_driver_init")
            ]
        ) != 1:
            raise ValueError("blacklisted observer initcall symbol is not unique")

        image = gzip.decompress(image_gz)
        if not image:
            raise ValueError("exact AH Image.gz expands empty")
        for marker in (
            b"dlg,da9214\0",
            b"da9211\0",
            b"mediatek,mt6797-a72-power\0",
            REJECTING_METHOD,
            BLACKLIST_TOKEN,
        ):
            if marker not in image:
                raise ValueError(f"exact AH kernel marker is absent: {marker!r}")

        dtb_validator = load_dtb_validator()
        dtb_validator.validate(ah_root / al.AH_DTB_MEMBER, args.dtb)
        ah = load_ah_boot_validator()
        baseline = ah.parse_boot(ah_boot, "Candidate AH")
        result = ah.parse_boot(candidate, "Candidate AL")
        if result["kernel"] != image_gz + dtb:
            raise ValueError("AL kernel field is not exact AH Image.gz plus AL DT")
        if result["ramdisk"] != initramfs:
            raise ValueError("AL ramdisk is not byte-exact AH")
        if result["header"] != ah.canonical_header(
            result["fields"], result["kernel"], result["ramdisk"]
        ):
            raise ValueError("Candidate AL Android-v0 header is not canonical")
        if baseline["header"] != ah.canonical_header(
            baseline["fields"], baseline["kernel"], baseline["ramdisk"]
        ):
            raise ValueError("Candidate AH Android-v0 baseline is not canonical")
        if ah.normalized_header(result["header"]) != ah.normalized_header(
            baseline["header"]
        ):
            raise ValueError("AL Android header changed outside kernel_size and ID")
        if result["fields"][1:] != baseline["fields"][1:]:
            raise ValueError("AL Android-v0 fields changed outside kernel_size")
        if result["fields"][0] != len(image_gz) + len(dtb):
            raise ValueError("AL kernel_size does not equal Image.gz plus AL DT")
        if candidate == ah_boot or digest(candidate) in {
            al.AH_RAW_SHA256,
            al.AK_RAW_SHA256,
        }:
            raise ValueError("Candidate AL boot identity equals a predecessor")

        print("validation=candidate-al-da9214-resource-only-android-v0")
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"image_gz_sha256={al.IMAGE_GZ_SHA256}")
        print(f"system_map_sha256={al.SYSTEM_MAP_SHA256}")
        print(f"config_sha256={al.CONFIG_SHA256}")
        print(f"initramfs_sha256={al.INITRAMFS_SHA256}")
        print(f"ah_dtb_sha256={al.AH_DTB_SHA256}")
        print(f"al_dtb_sha256={digest(dtb)}")
        print("kernel_config_system_map_initramfs=byte-exact-candidate-ah")
        print("final_dtb_delta=patch-0089-i2c6-da9214-only")
        print("android_header_delta=kernel-size-and-payload-id-only")
        print("maxcpus=8")
        print("observer_initcall=blacklisted")
        print("a72_power_node=absent")
        print("cpu8_cpu9_request=none")
        print("within_boot2_capacity=yes")
        print("device_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
        gzip.BadGzipFile,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
