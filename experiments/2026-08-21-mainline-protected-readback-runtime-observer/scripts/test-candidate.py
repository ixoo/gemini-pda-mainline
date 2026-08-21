#!/usr/bin/env python3
"""Independently validate the exact protected-readback observer candidate."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess


PAGE = 2048
BOOT2_SIZE = 16_777_216
RAW_SIZE = 7_636_992
KERNEL_FIELD_SIZE = 5_560_167
RAMDISK_SIZE = 2_073_441
RAW_SHA256 = "a3cb0e1c79447345d700fefc5eb68f3d136c893db8a87ecf0ebf54d0ffc0189c"
PADDED_SHA256 = "30ec9c56d6be78635f0ccf3ea626727763d71590c23778774c5c6366e4a5e75a"
IMAGE_SHA256 = "670d963560c654df75f7282959141a0170d04eb2babf26a9ea56869e321b36e3"
IMAGE_GZIP_SHA256 = "95d11ee7f26cba1085d24af60f6d60b029fcaf8dfca3e93df5e9bbf55dc013e5"
DTB_SHA256 = "34f24e49600e16e9b00f25ecba1d0806c4ce325944e176acccc6751a236b8998"
RAMDISK_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
CONFIG_SHA256 = "6b47a8d9014044ff7a9769304d2bb02cf2c56bcf6407a316f8c6068a51af89f0"
SYSTEM_MAP_SHA256 = "71db0783b2504fd6dfaac567b7ca0020e1610ad7ec2a23b3f0d49f569fd5990a"
BUILD_JSON_SHA256 = "21de87b3ce8ac54abf23dfd774bc80b722220c2297b08e96eeecb8f0b35006d4"
BOOT_FILE = "gemini-mt6797-protected-readback-ro.boot.img"
FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    BOOT_FILE,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "SHA256SUMS",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int) -> int:
    return (value + PAGE - 1) // PAGE * PAGE


def canonical_id(kernel: bytes, ramdisk: bytes) -> bytes:
    result = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        result.update(payload)
        result.update(struct.pack("<I", len(payload)))
    return result.digest()


def validate_serialization(
    raw: bytes,
    padded: bytes,
    image_gz: bytes,
    dtb: bytes,
    ramdisk: bytes,
    *,
    pin_identity: bool = True,
) -> None:
    require(len(raw) == RAW_SIZE, "raw size changed")
    require(len(padded) == BOOT2_SIZE, "padded size changed")
    if pin_identity:
        require(digest(raw) == RAW_SHA256, "raw identity changed")
        require(digest(padded) == PADDED_SHA256, "padded identity changed")
    require(padded[: len(raw)] == raw and not any(padded[len(raw) :]), "padding changed")
    require(raw[:8] == b"ANDROID!", "Android-v0 magic changed")
    fields = struct.unpack_from("<10I", raw, 8)
    require(
        fields
        == (
            KERNEL_FIELD_SIZE,
            0x40200000,
            RAMDISK_SIZE,
            0x45000000,
            0,
            0x40F00000,
            0x44000000,
            PAGE,
            0,
            0,
        ),
        "Android-v0 fields changed",
    )
    require(raw[48:64].split(b"\0", 1)[0] == b"gemini-prbro", "LK name changed")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(cmdline == b"bootopt=64S3,32N2,64N2", "LK command line changed")
    require(not any(raw[596:PAGE]), "header padding changed")

    kernel = image_gz + dtb
    kernel_offset = PAGE
    ramdisk_offset = align(kernel_offset + len(kernel))
    image_end = align(ramdisk_offset + len(ramdisk))
    require(len(kernel) == KERNEL_FIELD_SIZE, "kernel field size changed")
    require(raw[kernel_offset : kernel_offset + len(kernel)] == kernel, "kernel/DTB changed")
    require(not any(raw[kernel_offset + len(kernel) : ramdisk_offset]), "kernel padding changed")
    require(raw[ramdisk_offset : ramdisk_offset + len(ramdisk)] == ramdisk, "ramdisk changed")
    require(not any(raw[ramdisk_offset + len(ramdisk) : image_end]), "ramdisk padding changed")
    require(image_end == len(raw), "layout end changed")
    require(raw[576:596] == canonical_id(kernel, ramdisk), "canonical image ID changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()

    entries = list(args.candidate.iterdir())
    require({entry.name for entry in entries} == FILES, "candidate inventory changed")
    require(all(entry.is_file() and not entry.is_symlink() for entry in entries), "unsafe entry")
    subprocess.run(
        ["sha256sum", "--check", "--strict", "SHA256SUMS"],
        cwd=args.candidate,
        check=True,
        capture_output=True,
    )

    image = (args.package / "Image").read_bytes()
    image_gz = (args.package / "Image.gz").read_bytes()
    config = (args.package / "kernel.config").read_bytes()
    system_map = (args.package / "System.map").read_bytes()
    build_json = (args.package / "provenance/build.json").read_bytes()
    dtb = (
        args.package
        / "dtbs/mediatek/mt6797-gemini-pda-protected-readback.dtb"
    ).read_bytes()
    ramdisk = args.ramdisk.read_bytes()
    require(not args.ramdisk.is_symlink(), "unsafe ramdisk")
    for data, expected, label in (
        (image, IMAGE_SHA256, "Image"),
        (image_gz, IMAGE_GZIP_SHA256, "Image.gz"),
        (dtb, DTB_SHA256, "candidate DTB"),
        (ramdisk, RAMDISK_SHA256, "ramdisk"),
        (config, CONFIG_SHA256, "configuration"),
        (system_map, SYSTEM_MAP_SHA256, "System.map"),
        (build_json, BUILD_JSON_SHA256, "build.json"),
    ):
        require(digest(data) == expected, f"{label} changed")
    require(digest(gzip.decompress(image_gz)) == IMAGE_SHA256, "Image.gz payload changed")
    provenance = json.loads(build_json)
    require(
        provenance["repository_commit"]
        == "1bd49d97673731509f0e2c7dcadbb2f03ed343ca",
        "commit changed",
    )
    require(provenance["build_profile"] == "protected-readback-observer", "profile changed")
    require(
        provenance["kernel_release"] == "7.1.3-gemini-protected-readback-ro",
        "release changed",
    )
    for line in (
        b"CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND=y\n",
        b"CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND=y\n",
        b"CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER=y\n",
        b"# CONFIG_MTK_MT6797_A72_POWER is not set\n",
        b"# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set\n",
        b"# CONFIG_REGULATOR_DA9211 is not set\n",
        b"# CONFIG_KUNIT is not set\n",
    ):
        require(line in config, f"configuration gate missing: {line!r}")
    require(b"maxcpus=8" in config, "maxcpus=8 policy missing")
    for symbol in (
        b"mt6797_dvfsp_clock_backend_read",
        b"mt6797_bigidvfs_backend_read",
        b"mt6797_readback_observer_probe",
        b"mt6797_readback_observer_driver_init",
    ):
        require(system_map.count(b" " + symbol + b"\n") == 1, f"linked symbol changed: {symbol!r}")
    for marker in (
        b"GEMINI_PROTECTED_READBACK_V1 clock ret=%d",
        b"GEMINI_PROTECTED_READBACK_V1 bigidvfs ret=%d",
        b"GEMINI_PROTECTED_READBACK_V1 state=complete attempts=1 clock_calls=1 bigidvfs_calls=1 cpu_requests=0 owner_registration=0",
    ):
        require(image.count(marker) == 1, f"runtime marker not unique: {marker!r}")

    raw = (args.candidate / BOOT_FILE).read_bytes()
    padded = (args.candidate / "boot2-padded.img").read_bytes()
    validate_serialization(raw, padded, image_gz, dtb, ramdisk)
    analysis = (args.candidate / "container-analysis.txt").read_text(encoding="ascii")
    require(analysis.count("=yes\n") >= 32, "LK analysis lost gates")
    require(analysis.count("gate_") == 32, "LK gate count changed")
    require("lk_validation=passed\n" in analysis, "LK validation did not pass")

    rejected = 0
    for mutation in ("magic", "kernel", "dtb", "ramdisk", "id", "tail"):
        bad_raw = bytearray(raw)
        bad_padded = bytearray(padded)
        if mutation == "magic":
            bad_raw[0] ^= 1
        elif mutation == "kernel":
            bad_raw[PAGE + 64] ^= 1
        elif mutation == "dtb":
            bad_raw[PAGE + len(image_gz) + 8] ^= 1
        elif mutation == "ramdisk":
            bad_raw[align(PAGE + KERNEL_FIELD_SIZE) + 64] ^= 1
        elif mutation == "id":
            bad_raw[576] ^= 1
        else:
            bad_padded[-1] = 1
        try:
            validate_serialization(
                bytes(bad_raw),
                bytes(bad_padded),
                image_gz,
                dtb,
                ramdisk,
                pin_identity=False,
            )
        except AssertionError:
            rejected += 1
    require(rejected == 6, "not all container mutations were rejected")
    print("validation=protected-readback-observer-candidate")
    print("lk_gates=32-of-32")
    print("runtime_markers=clock,bigidvfs,complete")
    print("negative_mutations_rejected=6")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
