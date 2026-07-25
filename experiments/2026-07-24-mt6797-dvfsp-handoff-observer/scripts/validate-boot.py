#!/usr/bin/env python3
"""Validate Candidate AN's canonical Android-v0 container and safety boundary."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import pathlib
import stat
import struct
import subprocess
import sys
import zlib

import candidate_an as an


PAGE_SIZE = 2048
KERNEL_ADDR = 0x40200000
RAMDISK_ADDR = 0x45000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x44000000
NAME = "gemini-obs-L"
CMDLINE = "bootopt=64S3,32N2,64N2"
KERNEL_CMDLINE = (
    'CONFIG_CMDLINE="console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr '
    "ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug rdinit=/init "
    "panic=0 g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    'regulator_ignore_unused initcall_blacklist=mt6797_a72_power_driver_init"'
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def align(value: int) -> int:
    return (value + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def put_string(header: bytearray, offset: int, size: int, value: str) -> None:
    encoded = value.encode("ascii")
    if len(encoded) >= size:
        raise ValueError("canonical string is oversized")
    header[offset : offset + size] = encoded + b"\0" * (size - len(encoded))


def validate_config(data: bytes) -> None:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise ValueError("kernel configuration is not ASCII") from exc
    symbols: set[str] = set()
    for line in lines:
        if line.startswith("CONFIG_") and "=" in line:
            symbol = line.split("=", 1)[0]
        elif line.startswith("# CONFIG_") and line.endswith(" is not set"):
            symbol = line[2:-11]
        else:
            continue
        if symbol in symbols:
            raise ValueError(f"kernel configuration duplicates {symbol}")
        symbols.add(symbol)
    required = {
        "CONFIG_MTK_MT6797_DVFSP_HANDOFF_OBSERVER=y",
        "CONFIG_MTK_MT6797_A72_POWER=y",
        "CONFIG_CMDLINE_FORCE=y",
        KERNEL_CMDLINE,
    }
    missing = sorted(required - set(lines))
    if missing:
        raise ValueError("kernel configuration contract changed: " + missing[0])
    if "CONFIG_MODULES=y" in lines:
        raise ValueError("Candidate AN unexpectedly enables loadable modules")


def validate_system_map(data: bytes) -> None:
    try:
        symbols = {
            line.split(maxsplit=2)[2]
            for line in data.decode("ascii").splitlines()
            if len(line.split(maxsplit=2)) == 3
        }
    except UnicodeError as exc:
        raise ValueError("System.map is not ASCII") from exc
    required = {
        "mt6797_dvfsp_observer_driver",
        "mt6797_dvfsp_observer_driver_init",
    }
    if not required <= symbols:
        raise ValueError(
            "System.map lacks the built-in read-only DVFSP observer symbols"
        )
    forbidden = {
        "mt6797_a72_power_cpu_boot_ready",
        "mt6797_a72_power_cpu_on_complete",
        "mt6797_a72_power_cpu_on_failed",
        "mt6797_a72_power_prepare_first",
    }
    present = sorted(forbidden & symbols)
    if present:
        raise ValueError("active A72 sequence symbol is present: " + present[0])


def run_dtb_validator(
    script_dir: pathlib.Path, ah_dtb: pathlib.Path, candidate_dtb: pathlib.Path
) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(script_dir / "validate-dtb-delta.py"),
            "--ah",
            str(ah_dtb),
            "--candidate",
            str(candidate_dtb),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or "no diagnostic"
        raise ValueError("final DT semantic validator rejected Candidate AN: " + detail)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--image-gz", required=True, type=pathlib.Path)
    parser.add_argument("--system-map", required=True, type=pathlib.Path)
    parser.add_argument("--kernel-config", required=True, type=pathlib.Path)
    parser.add_argument("--dtb", required=True, type=pathlib.Path)
    parser.add_argument("--ah-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--initramfs", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        candidate = read_regular(args.candidate, "Candidate AN boot")
        image_gz = read_regular(args.image_gz, "Candidate AN Image.gz")
        system_map = read_regular(args.system_map, "Candidate AN System.map")
        kernel_config = read_regular(args.kernel_config, "Candidate AN config")
        dtb = read_regular(args.dtb, "Candidate AN final DT")
        ah_dtb = read_regular(args.ah_dtb, "exact Candidate AH final DT")
        initramfs = read_regular(args.initramfs, "exact Candidate AH initramfs")

        if digest(ah_dtb) != an.AH_DTB_SHA256:
            raise ValueError("exact Candidate AH final DT changed")
        if digest(dtb) != an.FINAL_DTB_SHA256:
            raise ValueError("Candidate AN final-DT identity changed")
        if digest(initramfs) != an.INITRAMFS_SHA256:
            raise ValueError("Candidate AN initramfs is not byte-exact Candidate AH")
        validate_config(kernel_config)
        validate_system_map(system_map)
        run_dtb_validator(pathlib.Path(__file__).resolve().parent, args.ah_dtb, args.dtb)

        image = gzip.decompress(image_gz)
        for marker in (
            b"mediatek,mt6797-dvfsp-handoff-observer\0",
            b"mt6797-dvfsp-handoff-observer\0",
            b"quiescent-stopped\0",
            b"state=%s i2c6_policy=disabled\n\0",
            b"snapshot=%d timer_before=%08x timer_after=%08x ",
        ):
            if marker not in image:
                raise ValueError(
                    f"Candidate AN kernel lacks observer marker: {marker!r}"
                )

        if not 0 < len(candidate) <= an.BOOT2_SIZE:
            raise ValueError("Candidate AN size is invalid or exceeds boot2")
        if len(candidate) < PAGE_SIZE or candidate[:8] != b"ANDROID!":
            raise ValueError("Candidate AN is not Android boot image v0")
        fields = struct.unpack_from("<10I", candidate, 8)
        (
            kernel_size,
            kernel_addr,
            ramdisk_size,
            ramdisk_addr,
            second_size,
            second_addr,
            tags_addr,
            page_size,
            dt_size,
            unused,
        ) = fields
        if (
            kernel_addr != KERNEL_ADDR
            or ramdisk_addr != RAMDISK_ADDR
            or second_addr != SECOND_ADDR
            or tags_addr != TAGS_ADDR
            or page_size != PAGE_SIZE
            or second_size
            or dt_size
            or unused
        ):
            raise ValueError("Android-v0 address or layout contract changed")

        kernel = image_gz + dtb
        if kernel_size != len(kernel) or ramdisk_size != len(initramfs):
            raise ValueError("Android-v0 payload sizes changed")
        kernel_offset = PAGE_SIZE
        kernel_end = kernel_offset + kernel_size
        ramdisk_offset = align(kernel_end)
        ramdisk_end = ramdisk_offset + ramdisk_size
        if candidate[kernel_offset:kernel_end] != kernel:
            raise ValueError("kernel field is not AN Image.gz plus final AN DT")
        if candidate[ramdisk_offset:ramdisk_end] != initramfs:
            raise ValueError("ramdisk field is not byte-exact Candidate AH initramfs")
        if any(candidate[kernel_end:ramdisk_offset]) or any(candidate[ramdisk_end:]):
            raise ValueError("Android-v0 padding is not zero")
        if len(candidate) != align(ramdisk_end):
            raise ValueError("Android-v0 trailing length changed")

        image_id = hashlib.sha1(usedforsecurity=False)
        for payload in (kernel, initramfs, b""):
            image_id.update(payload)
            image_id.update(struct.pack("<I", len(payload)))
        expected_header = bytearray(PAGE_SIZE)
        struct.pack_into("<8s10I", expected_header, 0, b"ANDROID!", *fields)
        put_string(expected_header, 48, 16, NAME)
        command_line = CMDLINE.encode("ascii")
        expected_header[64:576] = command_line[:512].ljust(512, b"\0")
        expected_header[608:1632] = command_line[512:].ljust(1024, b"\0")
        expected_header[576:596] = image_id.digest()
        if candidate[:PAGE_SIZE] != expected_header:
            raise ValueError("Android-v0 header is not canonical")

        print("validation=candidate-an-mt6797-dvfsp-handoff-android-v0")
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"image_gz_sha256={digest(image_gz)}")
        print(f"system_map_sha256={digest(system_map)}")
        print(f"config_sha256={digest(kernel_config)}")
        print(f"dtb_sha256={digest(dtb)}")
        print(f"initramfs_sha256={an.INITRAMFS_SHA256}")
        print("dtb_lineage=exact-candidate-ah-plus-observer-only")
        print("i2c6=disabled")
        print("da9214_node=absent")
        print("a72_power_node=absent")
        print("within_boot2_capacity=yes")
        print("hardware_write=none")
        return 0
    except (
        OSError,
        ValueError,
        gzip.BadGzipFile,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
