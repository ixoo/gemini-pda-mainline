#!/usr/bin/env python3
"""Validate Candidate AG as exact AF with only the simplefb DT transform."""

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


PAGE_SIZE = 2048
BOOT2_CAPACITY = 16 * 1024 * 1024
KERNEL_ADDR = 0x40200000
RAMDISK_ADDR = 0x45000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x44000000
NAME = "gemini-obs-L"
CMDLINE = "bootopt=64S3,32N2,64N2"

AF_BOOT_SHA256 = "fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3"
AF_IMAGE_GZ_SHA256 = "b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912"
AF_DTB_SHA256 = "3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b"
AD_INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AG_DTB_SHA256 = "7ea5e8f9edb09f2365a112b29359fed897f306422a26449b1cb8870bb1212512"
AG_BOOT_SHA256 = "0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91"
BLACKLIST_TOKEN = b"initcall_blacklist=mt6797_a72_power_driver_init"


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


def load_dtb_validator() -> object:
    source = pathlib.Path(__file__).resolve().with_name("validate-dtb-delta.py")
    spec = importlib.util.spec_from_file_location("gemini_ag_dtb_delta", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load DT validator from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_boot(data: bytes, label: str) -> dict[str, object]:
    if not 0 < len(data) <= BOOT2_CAPACITY:
        raise ValueError(f"{label} size is invalid or exceeds boot2")
    if len(data) < PAGE_SIZE or data[:8] != b"ANDROID!":
        raise ValueError(f"{label} is not Android boot image v0")
    fields = struct.unpack_from("<10I", data, 8)
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
        raise ValueError(f"{label} address or layout contract changed")
    kernel_offset = PAGE_SIZE
    kernel_end = kernel_offset + kernel_size
    ramdisk_offset = align(kernel_end)
    ramdisk_end = ramdisk_offset + ramdisk_size
    if ramdisk_end > len(data) or len(data) != align(ramdisk_end):
        raise ValueError(f"{label} payload boundaries are not canonical")
    if any(data[kernel_end:ramdisk_offset]) or any(data[ramdisk_end:]):
        raise ValueError(f"{label} padding is not zero")
    return {
        "fields": fields,
        "header": data[:PAGE_SIZE],
        "kernel": data[kernel_offset:kernel_end],
        "ramdisk": data[ramdisk_offset:ramdisk_end],
    }


def canonical_header(fields: tuple[int, ...], kernel: bytes, ramdisk: bytes) -> bytes:
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    header = bytearray(PAGE_SIZE)
    struct.pack_into("<8s10I", header, 0, b"ANDROID!", *fields)
    put_string(header, 48, 16, NAME)
    command_line = CMDLINE.encode("ascii")
    header[64:576] = command_line[:512].ljust(512, b"\0")
    header[608:1632] = command_line[512:].ljust(1024, b"\0")
    header[576:596] = image_id.digest()
    return bytes(header)


def normalized_header(header: bytes) -> bytes:
    normalized = bytearray(header)
    normalized[8:12] = b"\0" * 4
    normalized[576:596] = b"\0" * 20
    return bytes(normalized)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--af-boot", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--image-gz", required=True, type=pathlib.Path)
    parser.add_argument("--af-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--ad-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--ag-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--initramfs", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        af_boot = read_regular(args.af_boot, "exact Candidate AF boot")
        candidate = read_regular(args.candidate, "Candidate AG boot")
        image_gz = read_regular(args.image_gz, "exact Candidate AF Image.gz")
        af_dtb = read_regular(args.af_dtb, "exact Candidate AF DTB")
        read_regular(args.ad_dtb, "exact hardware-passed Candidate AD DTB")
        ag_dtb = read_regular(args.ag_dtb, "Candidate AG DTB")
        initramfs = read_regular(args.initramfs, "exact Candidate AD initramfs")
        if digest(af_boot) != AF_BOOT_SHA256:
            raise ValueError("exact Candidate AF boot changed")
        if digest(image_gz) != AF_IMAGE_GZ_SHA256:
            raise ValueError("Candidate AG Image.gz is not byte-exact AF")
        if digest(af_dtb) != AF_DTB_SHA256:
            raise ValueError("exact Candidate AF DTB changed")
        if digest(initramfs) != AD_INITRAMFS_SHA256:
            raise ValueError("Candidate AG initramfs is not byte-exact AF/AD")
        if digest(ag_dtb) != AG_DTB_SHA256:
            raise ValueError("Candidate AG DTB is not the reproduced exact transform")
        if digest(candidate) != AG_BOOT_SHA256:
            raise ValueError("Candidate AG boot is not the reproduced exact artifact")
        image = gzip.decompress(image_gz)
        for marker in (
            b"mediatek,mt6797-a72-power\0",
            b"mediatek,mt6797-psci\0",
            b"observer-v1\n\0",
            b"observe-only\n\0",
            BLACKLIST_TOKEN,
        ):
            if marker not in image:
                raise ValueError(f"exact AF kernel marker is absent: {marker!r}")

        dtb_validator = load_dtb_validator()
        dtb_validator.validate(args.af_dtb, args.ad_dtb, args.ag_dtb)
        baseline = parse_boot(af_boot, "Candidate AF")
        result = parse_boot(candidate, "Candidate AG")
        if baseline["kernel"] != image_gz + af_dtb:
            raise ValueError("AF baseline kernel field lineage changed")
        if result["kernel"] != image_gz + ag_dtb:
            raise ValueError("AG kernel field is not exact AF Image.gz plus AG DTB")
        if baseline["ramdisk"] != initramfs or result["ramdisk"] != initramfs:
            raise ValueError("AF/AG ramdisk is not byte-exact Candidate AD")
        if result["header"] != canonical_header(
            result["fields"], result["kernel"], result["ramdisk"]
        ):
            raise ValueError("Candidate AG Android-v0 header is not canonical")
        if baseline["header"] != canonical_header(
            baseline["fields"], baseline["kernel"], baseline["ramdisk"]
        ):
            raise ValueError("Candidate AF Android-v0 baseline is not canonical")
        if normalized_header(result["header"]) != normalized_header(baseline["header"]):
            raise ValueError("Android header changed outside DT-derived size and ID")
        baseline_fields = baseline["fields"]
        result_fields = result["fields"]
        if baseline_fields[1:] != result_fields[1:]:
            raise ValueError("Android-v0 fields changed outside kernel_size")
        if result_fields[0] != len(image_gz) + len(ag_dtb):
            raise ValueError("AG kernel_size does not equal Image.gz plus AG DTB")
        if candidate == af_boot or ag_dtb == af_dtb:
            raise ValueError("Candidate AG did not make the observation-path delta")

        print("validation=candidate-ag-simplefb-restoration-android-v0")
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"image_gz_sha256={AF_IMAGE_GZ_SHA256}")
        print(f"af_dtb_sha256={AF_DTB_SHA256}")
        print(f"ag_dtb_sha256={digest(ag_dtb)}")
        print(f"initramfs_sha256={AD_INITRAMFS_SHA256}")
        print("kernel_lineage=byte-exact-candidate-af")
        print("config_lineage=byte-exact-candidate-af")
        print("initramfs_lineage=byte-exact-candidate-af-ad")
        print("dtb_delta=ad-hardware-passed-simplefb-only")
        print("android_header_delta=kernel-size-and-payload-id-only")
        print("trailing_fdt=none")
        print("raw_framebuffer_write=none")
        print("within_boot2_capacity=yes")
        print("device_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        ValueError,
        gzip.BadGzipFile,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
