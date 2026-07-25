#!/usr/bin/env python3
"""Validate AH as the AF/AG payloads plus the two-property AD-derived DT."""

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
AG_BOOT_SHA256 = "0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91"
AD_BOOT_SHA256 = "a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b"
IMAGE_GZ_SHA256 = "b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912"
AD_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
BLACKLIST_TOKEN = b"initcall_blacklist=mt6797_a72_power_driver_init"
REJECTING_METHOD = b"mediatek,mt6797-psci\0"


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
    spec = importlib.util.spec_from_file_location("gemini_ah_dtb_delta", source)
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
    parser.add_argument("--ag-boot", required=True, type=pathlib.Path)
    parser.add_argument("--ad-boot", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--image-gz", required=True, type=pathlib.Path)
    parser.add_argument("--ad-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--ah-dtb", required=True, type=pathlib.Path)
    parser.add_argument("--initramfs", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        af_boot = read_regular(args.af_boot, "exact Candidate AF boot")
        ag_boot = read_regular(args.ag_boot, "exact Candidate AG boot")
        ad_boot = read_regular(args.ad_boot, "exact Candidate AD boot")
        candidate = read_regular(args.candidate, "Candidate AH boot")
        image_gz = read_regular(args.image_gz, "exact Candidate AF/AG Image.gz")
        ad_dtb = read_regular(args.ad_dtb, "exact hardware-passed Candidate AD DTB")
        ah_dtb = read_regular(args.ah_dtb, "Candidate AH DTB")
        initramfs = read_regular(args.initramfs, "exact Candidate AF/AG initramfs")
        for data, expected, label in (
            (af_boot, AF_BOOT_SHA256, "AF boot"),
            (ag_boot, AG_BOOT_SHA256, "AG boot"),
            (ad_boot, AD_BOOT_SHA256, "AD boot"),
            (image_gz, IMAGE_GZ_SHA256, "AF/AG Image.gz"),
            (ad_dtb, AD_DTB_SHA256, "AD DTB"),
            (initramfs, INITRAMFS_SHA256, "AF/AG initramfs"),
        ):
            if digest(data) != expected:
                raise ValueError(f"exact {label} changed")

        image = gzip.decompress(image_gz)
        if not image:
            raise ValueError("exact AF/AG Image.gz expands empty")
        for marker in (
            b"mediatek,mt6797-a72-power\0",
            REJECTING_METHOD,
            b"observer-v1\n\0",
            b"observe-only\n\0",
            BLACKLIST_TOKEN,
        ):
            if marker not in image:
                raise ValueError(f"exact AF/AG kernel marker is absent: {marker!r}")

        dtb_validator = load_dtb_validator()
        dtb_validator.validate(args.ad_dtb, args.ah_dtb)
        baselines = {
            "Candidate AF": parse_boot(af_boot, "Candidate AF"),
            "Candidate AG": parse_boot(ag_boot, "Candidate AG"),
            "Candidate AD": parse_boot(ad_boot, "Candidate AD"),
        }
        result = parse_boot(candidate, "Candidate AH")
        if result["kernel"] != image_gz + ah_dtb:
            raise ValueError("AH kernel field is not exact AF/AG Image.gz plus AH DTB")
        if result["ramdisk"] != initramfs:
            raise ValueError("AH ramdisk is not byte-exact AF/AG")
        if result["header"] != canonical_header(
            result["fields"], result["kernel"], result["ramdisk"]
        ):
            raise ValueError("Candidate AH Android-v0 header is not canonical")

        reference_header: bytes | None = None
        reference_fields: tuple[int, ...] | None = None
        for label, baseline in baselines.items():
            if baseline["ramdisk"] != initramfs:
                raise ValueError(f"{label} ramdisk lineage changed")
            if baseline["header"] != canonical_header(
                baseline["fields"], baseline["kernel"], baseline["ramdisk"]
            ):
                raise ValueError(f"{label} Android-v0 baseline is not canonical")
            normalized = normalized_header(baseline["header"])
            if reference_header is None:
                reference_header = normalized
                reference_fields = baseline["fields"]
            elif normalized != reference_header:
                raise ValueError("AF/AG/AD normalized Android headers differ")
            if baseline["fields"][1:] != reference_fields[1:]:
                raise ValueError("AF/AG/AD fields differ outside kernel_size")
        if normalized_header(result["header"]) != reference_header:
            raise ValueError("AH Android header changed outside kernel_size and ID")
        if result["fields"][1:] != reference_fields[1:]:
            raise ValueError("AH Android-v0 fields changed outside kernel_size")
        if result["fields"][0] != len(image_gz) + len(ah_dtb):
            raise ValueError("AH kernel_size does not equal Image.gz plus AH DTB")
        if candidate in (af_boot, ag_boot, ad_boot) or ah_dtb == ad_dtb:
            raise ValueError("Candidate AH did not make the component-split delta")

        print("validation=candidate-ah-ad-contract-af-kernel-split-android-v0")
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"image_gz_sha256={IMAGE_GZ_SHA256}")
        print(f"ad_dtb_sha256={AD_DTB_SHA256}")
        print(f"ah_dtb_sha256={digest(ah_dtb)}")
        print(f"initramfs_sha256={INITRAMFS_SHA256}")
        print("kernel_config_system_map_lineage=byte-exact-candidate-af-and-ag")
        print("initramfs_userspace_lineage=byte-exact-candidate-af-ag-and-ad")
        print("dtb_baseline=byte-exact-hardware-passed-candidate-ad")
        print("dtb_delta=cpu8-and-cpu9-enable-method-only")
        print("android_header_delta=kernel-size-and-payload-id-only")
        print("trailing_fdt=none")
        print("within_boot2_capacity=yes")
        print("active_a72_operation=none")
        print("raw_framebuffer_write=none")
        print("device_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        gzip.BadGzipFile,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
