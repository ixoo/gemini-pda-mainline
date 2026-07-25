#!/usr/bin/env python3
"""Validate Candidate AI's canonical Android-v0 image and exact components."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import stat
import struct
import sys

sys.dont_write_bytecode = True


PAGE_SIZE = 2048
BOOT2_CAPACITY = 16 * 1024 * 1024
KERNEL_ADDR = 0x40200000
RAMDISK_ADDR = 0x45000000
SECOND_ADDR = 0x40F00000
TAGS_ADDR = 0x44000000
NAME = "gemini-obs-L"
CMDLINE = "bootopt=64S3,32N2,64N2"

AD_BOOT_SHA256 = "a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b"
AH_BOOT_SHA256 = "e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197"
AF_BOOT_SHA256 = "fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3"
AD_IMAGE_GZ_SHA256 = "1ab084bd427f9fade4adb43a83cca879c3289929485ad1469c6dffa539d3548b"
AF_IMAGE_GZ_SHA256 = "b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912"
AH_DTB_SHA256 = "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845"
AD_INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
AD_CONFIG_SHA256 = "32dd13a6704e5fa591236ba114d43e8e7e1aeb3eb123d9d4f124b5f551301d46"
AD_SYSTEM_MAP_SHA256 = "63dc89816c1cee5b62e3f514e12512b199415e81be37f5577168465787a42890"
AF_SYSTEM_MAP_SHA256 = "a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d"


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
        raise ValueError(f"{label} Android-v0 address or layout contract changed")
    kernel_offset = PAGE_SIZE
    kernel_end = kernel_offset + kernel_size
    ramdisk_offset = align(kernel_end)
    ramdisk_end = ramdisk_offset + ramdisk_size
    if kernel_end > len(data) or ramdisk_end > len(data):
        raise ValueError(f"{label} payload exceeds the container")
    if len(data) != align(ramdisk_end):
        raise ValueError(f"{label} trailing length is not canonical")
    if any(data[kernel_end:ramdisk_offset]) or any(data[ramdisk_end:]):
        raise ValueError(f"{label} padding is not zero")
    return {
        "fields": fields,
        "header": data[:PAGE_SIZE],
        "kernel": data[kernel_offset:kernel_end],
        "ramdisk": data[ramdisk_offset:ramdisk_end],
    }


def canonical_header(
    fields: tuple[int, ...], kernel: bytes, ramdisk: bytes
) -> bytes:
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
    output = bytearray(header)
    output[8:12] = b"\0" * 4
    output[576:596] = b"\0" * 20
    return bytes(output)


def validate_container(
    candidate: bytes,
    image_gz: bytes,
    dtb: bytes,
    initramfs: bytes,
    *,
    label: str = "Candidate AI",
) -> dict[str, object]:
    package_validator = load_package_validator()
    package_validator.decompress_lk_image_gz(image_gz, f"{label} Image.gz")
    result = parse_boot(candidate, label)
    expected_kernel = image_gz + dtb
    if result["kernel"] != expected_kernel:
        raise ValueError(f"{label} kernel field is not exact Image.gz plus DTB")
    if result["ramdisk"] != initramfs:
        raise ValueError(f"{label} ramdisk field changed")
    fields = result["fields"]
    if not isinstance(fields, tuple):
        raise TypeError("parsed Android fields have an invalid type")
    if fields[0] != len(expected_kernel) or fields[2] != len(initramfs):
        raise ValueError(f"{label} payload sizes changed")
    if result["header"] != canonical_header(fields, expected_kernel, initramfs):
        raise ValueError(f"{label} Android-v0 header is not canonical")
    return result


def load_package_validator() -> object:
    source = pathlib.Path(__file__).resolve().with_name("validate-package.py")
    spec = importlib.util.spec_from_file_location("gemini_ai_boot_package", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AI package validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--kernel-config", type=pathlib.Path, required=True)
    parser.add_argument("--system-map", type=pathlib.Path, required=True)
    parser.add_argument("--ad-boot", type=pathlib.Path, required=True)
    parser.add_argument("--ah-boot", type=pathlib.Path, required=True)
    parser.add_argument("--af-boot", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        candidate = read_regular(args.candidate, "Candidate AI boot")
        image_gz = read_regular(args.image_gz, "Candidate AI Image.gz")
        dtb = read_regular(args.dtb, "exact Candidate AH final DTB")
        initramfs = read_regular(args.initramfs, "exact Candidate AD initramfs")
        config = read_regular(args.kernel_config, "Candidate AI kernel config")
        system_map = read_regular(args.system_map, "Candidate AI System.map")
        baselines = []
        for path, label, expected in (
            (args.ad_boot, "Candidate AD", AD_BOOT_SHA256),
            (args.ah_boot, "Candidate AH", AH_BOOT_SHA256),
            (args.af_boot, "Candidate AF", AF_BOOT_SHA256),
        ):
            data = read_regular(path, f"exact {label} boot")
            if digest(data) != expected:
                raise ValueError(f"exact {label} boot identity changed")
            parsed = parse_boot(data, label)
            fields = parsed["fields"]
            if not isinstance(fields, tuple):
                raise TypeError(f"{label} fields have an invalid type")
            if parsed["header"] != canonical_header(
                fields, parsed["kernel"], parsed["ramdisk"]  # type: ignore[arg-type]
            ):
                raise ValueError(f"{label} baseline header is not canonical")
            baselines.append((data, parsed))

        if digest(dtb) != AH_DTB_SHA256:
            raise ValueError("final DTB is not exact Candidate AH")
        if digest(initramfs) != AD_INITRAMFS_SHA256:
            raise ValueError("initramfs is not exact Candidate AD")
        if digest(config) != AD_CONFIG_SHA256:
            raise ValueError("resolved config is not exact Candidate AD")
        if digest(image_gz) in (AD_IMAGE_GZ_SHA256, AF_IMAGE_GZ_SHA256):
            raise ValueError("Candidate AI reused an AD or AF kernel")
        if digest(system_map) in (AD_SYSTEM_MAP_SHA256, AF_SYSTEM_MAP_SHA256):
            raise ValueError("Candidate AI reused an AD or AF System.map")

        package_validator = load_package_validator()
        image = package_validator.decompress_lk_image_gz(
            image_gz, "Candidate AI Image.gz"
        )
        package_validator.validate_kernel_policy(image, system_map, config)
        result = validate_container(candidate, image_gz, dtb, initramfs)
        if any(candidate == baseline for baseline, _ in baselines):
            raise ValueError("Candidate AI is byte-identical to an earlier candidate")

        reference_header = normalized_header(baselines[0][1]["header"])  # type: ignore[arg-type]
        reference_fields = baselines[0][1]["fields"]
        if not isinstance(reference_fields, tuple):
            raise TypeError("baseline fields have an invalid type")
        for _, parsed in baselines[1:]:
            if normalized_header(parsed["header"]) != reference_header:  # type: ignore[arg-type]
                raise ValueError("AD/AH/AF normalized Android headers differ")
            fields = parsed["fields"]
            if not isinstance(fields, tuple) or fields[1:] != reference_fields[1:]:
                raise ValueError("AD/AH/AF fields differ outside kernel_size")
        if normalized_header(result["header"]) != reference_header:  # type: ignore[arg-type]
            raise ValueError("Candidate AI header changed outside kernel_size and ID")
        fields = result["fields"]
        if not isinstance(fields, tuple) or fields[1:] != reference_fields[1:]:
            raise ValueError("Candidate AI fields changed outside kernel_size")

        print("validation=candidate-ai-a72-reject-gate-android-v0")
        print(f"candidate_sha256={digest(candidate)}")
        print(f"candidate_size={len(candidate)}")
        print(f"image_gz_sha256={digest(image_gz)}")
        print(f"system_map_sha256={digest(system_map)}")
        print(f"config_sha256={AD_CONFIG_SHA256}")
        print(f"dtb_sha256={AH_DTB_SHA256}")
        print(f"initramfs_sha256={AD_INITRAMFS_SHA256}")
        print("kernel_boundary=exact-ad-series-plus-corrected-0092-only")
        print("android_header_delta=kernel-size-and-payload-id-only")
        print("cpu_policy=maxcpus-8-cpu8-cpu9-not-requested")
        print("regulator_reset_observer_paths=absent")
        print("within_boot2_capacity=yes")
        print("new_output_identity=pending-reproduction-record")
        print("device_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
        struct.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
