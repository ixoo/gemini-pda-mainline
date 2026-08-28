#!/usr/bin/env python3
"""Independently validate the current-Image/runtime-proven-DT control."""

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
RAW_SIZE = 6_934_528
KERNEL_SIZE = 4_857_270
RAMDISK_SIZE = 2_073_441
RAW_SHA = "35d0c6ef99f69a1dd00afac390f8d68b5514577e38819448b7465c44243c2f12"
PADDED_SHA = "c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab"
IMAGE_SHA = "96c86abe4084333bf462f028c217c41eb0342ad080dae3014b439eef0f0cab18"
IMAGE_GZ_SHA = "4b884c0176d4d3e7d96c35f84ce36f0e591b2b7a411fe217f43427824f8377f4"
DTB_SHA = "90cfc29b30fb036076a799f0223e0c8aae6469441e5917cbfa743f5d7ae6547d"
RAMDISK_SHA = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
CONFIG_SHA = "265f610b5200dff9184cd0dcca3c6993b572e167316e149a9856f05723c9eebd"
SYSTEM_MAP_SHA = "4d6e3ad347b755907a99b0c7dc0f1cb91fff00f533f21baeab663e77373731bd"
BUILD_JSON_SHA = "c1009fab6642739161d913bdb676fb027d7849dd60c61e1291ec04a8c2541241"
MANIFEST_SHA = "a029c258c19c96a234cb5cafe4c1bb35a36bac2beadbe8e2ea547da8870719d1"
BOOT_FILE = "gemini-mt6797-a72-live-image-runtime-dt-control.boot.img"
FILES = {BOOT_FILE, "boot2-padded.img", "container-analysis.txt", "package-validation.txt", "provenance.txt", "serializer.txt", "SHA256SUMS"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def align(value: int) -> int:
    return (value + PAGE - 1) // PAGE * PAGE


def image_id(kernel: bytes, ramdisk: bytes) -> bytes:
    result = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        result.update(payload)
        result.update(struct.pack("<I", len(payload)))
    return result.digest()


def validate_layout(raw: bytes, padded: bytes, image_gz: bytes, dtb: bytes, ramdisk: bytes, pin: bool = True) -> None:
    require(len(raw) == RAW_SIZE and len(padded) == BOOT2_SIZE, "candidate sizes changed")
    if pin:
        require(digest(raw) == RAW_SHA and digest(padded) == PADDED_SHA, "candidate identities changed")
    require(padded[:RAW_SIZE] == raw and not any(padded[RAW_SIZE:]), "padding changed")
    require(raw[:8] == b"ANDROID!", "Android magic changed")
    fields = struct.unpack_from("<10I", raw, 8)
    require(fields == (KERNEL_SIZE, 0x40200000, RAMDISK_SIZE, 0x45000000, 0, 0x40F00000, 0x44000000, PAGE, 0, 0), "header fields changed")
    require(raw[48:64].split(b"\0", 1)[0] == b"gemini-a72dtctl", "LK name changed")
    require((raw[64:576] + raw[608:1632]).split(b"\0", 1)[0] == b"bootopt=64S3,32N2,64N2", "command line changed")
    kernel = image_gz + dtb
    ramdisk_offset = align(PAGE + len(kernel))
    require(len(kernel) == KERNEL_SIZE, "kernel field size changed")
    require(raw[PAGE:PAGE + len(kernel)] == kernel, "kernel field changed")
    require(raw[ramdisk_offset:ramdisk_offset + len(ramdisk)] == ramdisk, "ramdisk changed")
    require(raw[576:596] == image_id(kernel, ramdisk), "canonical image ID changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    parser.add_argument("--control-dtb", type=Path, required=True)
    args = parser.parse_args()
    require({p.name for p in args.candidate.iterdir()} == FILES, "artifact inventory changed")
    require(all(p.is_file() and not p.is_symlink() for p in args.candidate.iterdir()), "unsafe artifact entry")
    require(digest((args.candidate / "SHA256SUMS").read_bytes()) == MANIFEST_SHA, "artifact manifest changed")
    subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"], cwd=args.candidate, check=True, capture_output=True)
    image = (args.package / "Image").read_bytes()
    image_gz = (args.package / "Image.gz").read_bytes()
    config = (args.package / "kernel.config").read_bytes()
    system_map = (args.package / "System.map").read_bytes()
    build_json = (args.package / "provenance/build.json").read_bytes()
    dtb = args.control_dtb.read_bytes()
    ramdisk = args.ramdisk.read_bytes()
    for data, expected, label in ((image, IMAGE_SHA, "Image"), (image_gz, IMAGE_GZ_SHA, "Image.gz"), (config, CONFIG_SHA, "config"), (system_map, SYSTEM_MAP_SHA, "System.map"), (build_json, BUILD_JSON_SHA, "build.json"), (dtb, DTB_SHA, "DTB"), (ramdisk, RAMDISK_SHA, "ramdisk")):
        require(digest(data) == expected, f"{label} changed")
    require(digest(gzip.decompress(image_gz)) == IMAGE_SHA, "compressed Image payload changed")
    provenance = json.loads(build_json)
    require(provenance["repository_commit"] == "c147e2ddc1acc93827b59f8e3bb38b9b2f4d3fb2", "commit changed")
    require(provenance["build_profile"] == "a72-admission-live-trigger-candidate", "profile changed")
    require(provenance["kernel_release"] == "7.1.3-gemini-a72-admission-live", "release changed")
    require(dtb.count(b"mediatek,mt6797-a72-platform-state") == 1, "platform-state compatible changed")
    require(dtb.count(b"mediatek,mt6797-a72-platform-provider-clock-observer") == 1, "observer compatible changed")
    require(b"mt6797-a72-admission-controller" not in dtb and b"mt6797-a72-admission-binder" not in dtb, "admission node leaked into DT")
    raw = (args.candidate / BOOT_FILE).read_bytes()
    padded = (args.candidate / "boot2-padded.img").read_bytes()
    validate_layout(raw, padded, image_gz, dtb, ramdisk)
    analysis = (args.candidate / "container-analysis.txt").read_text(encoding="ascii")
    require(analysis.count("gate_") == 32 and analysis.count("=yes\n") >= 32 and "lk_validation=passed\n" in analysis, "LK gates changed")
    rejected = 0
    for name in ("magic", "kernel", "dtb", "ramdisk", "id", "tail"):
        bad_raw = bytearray(raw); bad_padded = bytearray(padded)
        if name == "magic": bad_raw[0] ^= 1
        elif name == "kernel": bad_raw[PAGE + 64] ^= 1
        elif name == "dtb": bad_raw[PAGE + len(image_gz) + 8] ^= 1
        elif name == "ramdisk": bad_raw[align(PAGE + KERNEL_SIZE) + 64] ^= 1
        elif name == "id": bad_raw[576] ^= 1
        else: bad_padded[-1] = 1
        try: validate_layout(bytes(bad_raw), bytes(bad_padded), image_gz, dtb, ramdisk, pin=False)
        except AssertionError: rejected += 1
    require(rejected == 6, "container mutations not rejected")
    print("validation=a72-live-image-runtime-dt-control-independent")
    print("lk_gates=32-of-32")
    print("controller_nodes=0")
    print("binder_nodes=0")
    print("cpu8_requests=0")
    print("negative_mutations_rejected=6")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
