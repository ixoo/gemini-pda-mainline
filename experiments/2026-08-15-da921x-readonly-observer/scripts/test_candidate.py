#!/usr/bin/env python3
"""Independently validate the exact DA921x read-only observer container."""

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
RAW_SIZE = 7_761_920
KERNEL_FIELD_SIZE = 5_684_030
RAMDISK_SIZE = 2_073_441
RAW_SHA256 = "1a55a25b7d6bff448802db3259ba65371c34657b341f0e621dc134bd700e7b14"
PADDED_SHA256 = "7a3ce120de99d7c5ad26dce618f81d50bfeb1ca95b5f2a0bdb9fbf4acba1f564"
IMAGE_SHA256 = "3483fb980c8c59ea0a10bf356737391aaa6b49969e39b4a3cee3831774f5fbf9"
IMAGE_GZIP_SHA256 = "5609a9a30b2959fd93144900461e4a07ba274adda04454ef534a2961d6a8c1b1"
DTB_SHA256 = "61ea34a4f780afe04da1257f8c3655be7f8490a7c3af2df727dd8592bb6e6285"
RAMDISK_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
CONFIG_SHA256 = "0d707f8483ce7a5599625bb2a09889c642b3ee945d2ad3fa6cf6f7289363581a"
SYSTEM_MAP_SHA256 = "665d70c58f771abc43d39b2b9b7244a28df9ae7ad4eb8856e4fbf678dd7e88dc"
BUILD_JSON_SHA256 = "1643441936f8f88d8a7dc221007c4d5fc0616a9c697cda8fcb0b4eb380e61b4e"
FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    "gemini-mt6797-da921x-readonly-observer.boot.img",
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
    require(raw[48:64].split(b"\0", 1)[0] == b"gemini-daobs", "LK name changed")
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
    dtb = (args.package / "dtbs/mediatek/mt6797-gemini-pda.dtb").read_bytes()
    config = (args.package / "kernel.config").read_bytes()
    system_map = (args.package / "System.map").read_bytes()
    build_json = (args.package / "provenance/build.json").read_bytes()
    ramdisk = args.ramdisk.read_bytes()
    require(not args.ramdisk.is_symlink(), "unsafe ramdisk")
    for data, expected, label in (
        (image, IMAGE_SHA256, "Image"),
        (image_gz, IMAGE_GZIP_SHA256, "Image.gz"),
        (dtb, DTB_SHA256, "DTB"),
        (ramdisk, RAMDISK_SHA256, "ramdisk"),
        (config, CONFIG_SHA256, "configuration"),
        (system_map, SYSTEM_MAP_SHA256, "System.map"),
        (build_json, BUILD_JSON_SHA256, "build.json"),
    ):
        require(digest(data) == expected, f"{label} changed")
    require(digest(gzip.decompress(image_gz)) == IMAGE_SHA256, "Image.gz payload changed")
    provenance = json.loads(build_json)
    require(provenance["repository_commit"] == "d0d511e60af343bdcc880b41b50acd2be877fa2b", "commit changed")
    require(provenance["build_profile"] == "da921x-readonly-observer", "profile changed")
    require(provenance["kernel_release"] == "7.1.3-gemini-da921x-observer", "release changed")
    require(b"CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y\n" in config, "observer absent")
    require(b"# CONFIG_KUNIT is not set\n" in config, "KUnit leaked into runtime")
    require(b" da9213_legacy_observer_collect\n" in system_map, "observer symbol absent")
    require(b"da9213_legacy_observer_test_suite" not in system_map, "test symbol leaked")
    require(b"da921x-observer-v1 event=bound" in image, "runtime marker absent")

    raw = (args.candidate / "gemini-mt6797-da921x-readonly-observer.boot.img").read_bytes()
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
    print("validation=da921x-readonly-observer-candidate")
    print("lk_gates=32-of-32")
    print("negative_mutations_rejected=6")
    print("runtime_marker=present")
    print("kunit_payload=absent")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
