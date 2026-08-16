#!/usr/bin/env python3
"""Independently validate the exact GAEL/Stage-27-DTB control container."""

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
RAW_SIZE = 6_879_232
KERNEL_FIELD_SIZE = 4_802_149
RAMDISK_SIZE = 2_073_441
RAW_SHA256 = "e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086"
PADDED_SHA256 = "68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67"
IMAGE_SHA256 = "37f3897cee5a7eb899273878938b3c98522a98dd2fac64d2f0f72235d2c10d84"
IMAGE_GZIP_SHA256 = "539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe"
CONTROL_DTB_SHA256 = "7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806"
RAMDISK_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
CONFIG_SHA256 = "e622eb1a3acde5c8e351227e7044e34cd894091b2f3b9c210c37e42cced0b323"
SYSTEM_MAP_SHA256 = "dcdfb20bd9102c882366885ffb879885e58b8d88d73e9822a6049c9d5fc7d4ec"
BUILD_JSON_SHA256 = "88ab3409c4026f140cd4a8daa0682799a6e0420b50dd8b30010e14573017fcee"
FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    "gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img",
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
    require(raw[48:64].split(b"\0", 1)[0] == b"gemini-dtbctl", "LK name changed")
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
    parser.add_argument("--control-dtb", type=Path, required=True)
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
    ramdisk = args.ramdisk.read_bytes()
    dtb = args.control_dtb.read_bytes()
    require(not args.ramdisk.is_symlink(), "unsafe ramdisk")
    require(not args.control_dtb.is_symlink(), "unsafe control DTB")
    for data, expected, label in (
        (image, IMAGE_SHA256, "Image"),
        (image_gz, IMAGE_GZIP_SHA256, "Image.gz"),
        (dtb, CONTROL_DTB_SHA256, "Stage-27 control DTB"),
        (ramdisk, RAMDISK_SHA256, "ramdisk"),
        (config, CONFIG_SHA256, "configuration"),
        (system_map, SYSTEM_MAP_SHA256, "System.map"),
        (build_json, BUILD_JSON_SHA256, "build.json"),
    ):
        require(digest(data) == expected, f"{label} changed")
    require(digest(gzip.decompress(image_gz)) == IMAGE_SHA256, "Image.gz payload changed")
    provenance = json.loads(build_json)
    require(
        provenance["repository_commit"] == "98996fdfbf09f8de2a6b86e488defef22fcc7968",
        "commit changed",
    )
    require(provenance["build_profile"] == "da921x-modules-arm64-entry-ledger", "profile changed")
    require(provenance["kernel_release"] == "7.1.3-gemini-entryled-a", "release changed")
    for line in (
        b"CONFIG_MODULES=y\n",
        b"# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set\n",
        b"CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y\n",
        b"# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set\n",
    ):
        require(line in config, f"configuration gate missing: {line!r}")
    for marker in (
        b"GAEL-20260816-A E0",
        b"GAEL-20260816-A E1",
        b"GAEL-20260816-A E2",
        b"GAEL-20260816-A E3",
    ):
        require(image.count(marker) == 1, f"entry-ledger marker not unique: {marker!r}")
    symbols: dict[str, int] = {}
    for line in system_map.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in {b"__idmap_text_start", b"__idmap_text_end"}:
            symbols[fields[2].decode()] = int(fields[0], 16)
    require(
        symbols
        == {
            "__idmap_text_start": 0xFFFF8000808DE000,
            "__idmap_text_end": 0xFFFF8000808DEFB8,
        },
        "identity-map boundaries changed",
    )

    raw = (
        args.candidate / "gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img"
    ).read_bytes()
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
    print("validation=lk-handoff-dtb-control-candidate")
    print("lk_gates=32-of-32")
    print("entry_ledger_markers=E0,E1,E2,E3")
    print("control_dtb=exact-runtime-proven-stage27")
    print("negative_mutations_rejected=6")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
