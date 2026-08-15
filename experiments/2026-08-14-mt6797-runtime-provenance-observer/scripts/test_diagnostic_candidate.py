#!/usr/bin/env python3
"""Independently validate the vendor-RNDIS observer derivative."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import struct
import subprocess
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent / "initramfs"
PARSER = SCRIPT_DIR.parents[1] / "2026-07-21-usb-gadget-ethernet" / "scripts" / "validate-initramfs.py"
EXPECTED = {
    "parser": "6ffaa2cb0c0aa8520be344abe585c91734420d9e6a37f5ed9875f20828e8c570",
    "builder": "b426337ecb44fe7ba21b710763baa71bd7757173f953a420a0b8d78d44b055bd",
    "init_builder": "0abe8a8b02ec3767c21fc018c69cc7e2db5ddb475a00e443247474a582f29f38",
    "assembler": "66b5617e1aee8befdaf3d064b0966a6d2cebe256e0e8092e19fb10b34c2fa0f2",
    "source_init": "9f8965f8b80c064ce9c637d7e3c0543561e9207be95cfeb19ca9384d81a55ad3",
    "source_record": "30989efbb268624bd5004cf1c1c227a09ab566068622fe012aa1c2e4fe66945d",
    "source_usb": "f0a6623f5a396973e2a009cdd4921811b0cdcf0ed5521103ccd452ddb334592b",
    "active": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "kernel": "d49d03911837af1519efc3089018e505e2a213f4682dd7cb25a751e65f8cdb7d",
    "ac_initramfs": "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3",
    "diagnostic_initramfs": "86a112ef29fecdb8f47b003cbfb08b77b478c4f511cba46acd987af09c921358",
    "attempt1_raw": "e354ee4b8265d2226e49d2c9376ec3e6e39eee83fd413490de29de1c1500b72b",
    "raw": "1d303dda10b47248f51a1fb2c8f3b1a7b8098522536f4f54ff763c17e75ff310",
    "padded": "ea603c1b1a64d4f1aa9cac3e53957a3e858a7ce04127f1aef36d4b0e8173cb02",
    "manifest": "ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a",
}
FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    "diagnostic-initramfs.img",
    "initramfs-analysis.txt",
    "provenance-observer-vendor-rndis.boot.img",
    "provenance.txt",
    "SHA256SUMS",
}
PAGE = 2048


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int) -> int:
    return (value + PAGE - 1) // PAGE * PAGE


def fields(image: bytes) -> tuple[int, ...]:
    require(image[:8] == b"ANDROID!" and len(image) >= PAGE, "Android-v0 header changed")
    return struct.unpack_from("<10I", image, 8)


def validate_serialization(raw: bytes, padded: bytes, active: bytes, kernel: bytes, ramdisk: bytes) -> None:
    require(len(raw) == 10_108_928 and digest(raw) == EXPECTED["raw"], "raw candidate changed")
    require(len(padded) == 16_777_216 and digest(padded) == EXPECTED["padded"], "padded candidate changed")
    require(padded[: len(raw)] == raw and not any(padded[len(raw) :]), "exact zero padding changed")
    expected_fields = (8_287_407, 0x40080000, 1_818_169, 0x45000000, 0, 0x40F00000, 0x44000000, PAGE, 0, 0)
    require(fields(raw) == expected_fields, "Android-v0 fields changed")
    require(not any(raw[48:64]), "Android-v0 name changed")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(cmdline == b"bootopt=64S3,32N2,64N2 log_buf_len=4M", "command line changed")
    ramdisk_offset = align(PAGE + len(kernel))
    require(raw[PAGE : PAGE + len(kernel)] == kernel, "embedded kernel changed")
    require(raw[ramdisk_offset : ramdisk_offset + len(ramdisk)] == ramdisk, "embedded ramdisk changed")
    require(not any(raw[PAGE + len(kernel) : ramdisk_offset]), "kernel alignment padding changed")
    require(not any(raw[ramdisk_offset + len(ramdisk) :]), "ramdisk padding changed")
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    require(raw[576:596] == image_id.digest(), "Android image ID changed")
    require(raw[48:576] == active[48:576], "inherited header strings changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--attempt1", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--active-boot", type=Path, required=True)
    parser.add_argument("--ac-initramfs", type=Path, required=True)
    args = parser.parse_args()

    tools = {
        "parser": PARSER,
        "builder": SCRIPT_DIR / "build-diagnostic-candidate.sh",
        "init_builder": SCRIPT_DIR / "build-diagnostic-initramfs.py",
        "assembler": SCRIPT_DIR / "assemble-diagnostic.py",
        "source_init": SOURCE_DIR / "init",
        "source_record": SOURCE_DIR / "provenance-record",
        "source_usb": SOURCE_DIR / "usb-net",
    }
    for name, path in tools.items():
        require(path.is_file() and not path.is_symlink(), f"unsafe tool: {name}")
        require(digest(path.read_bytes()) == EXPECTED[name], f"tool changed: {name}")

    entries = list(args.candidate.iterdir())
    require({entry.name for entry in entries} == FILES, "candidate inventory changed")
    require(all(entry.is_file() and not entry.is_symlink() for entry in entries), "unsafe candidate entry")
    manifest = args.candidate / "SHA256SUMS"
    require(digest(manifest.read_bytes()) == EXPECTED["manifest"], "manifest changed")
    subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"], cwd=args.candidate, check=True, capture_output=True)

    active = args.active_boot.read_bytes()
    kernel = (args.bundle / "outputs/Image.gz-dtb").read_bytes()
    ac_initramfs = args.ac_initramfs.read_bytes()
    ramdisk = (args.candidate / "diagnostic-initramfs.img").read_bytes()
    attempt1 = args.attempt1.read_bytes()
    raw = (args.candidate / "provenance-observer-vendor-rndis.boot.img").read_bytes()
    padded = (args.candidate / "boot2-padded.img").read_bytes()
    for data, name in (
        (active, "active"),
        (kernel, "kernel"),
        (ac_initramfs, "ac_initramfs"),
        (ramdisk, "diagnostic_initramfs"),
        (attempt1, "attempt1_raw"),
    ):
        require(digest(data) == EXPECTED[name], f"input changed: {name}")
    validate_serialization(raw, padded, active, kernel, ramdisk)

    require(fields(attempt1)[0:2] == fields(raw)[0:2], "kernel address or size differs from attempt 1")
    require(attempt1[PAGE : PAGE + len(kernel)] == raw[PAGE : PAGE + len(kernel)], "kernel/DT differs from attempt 1")
    require(attempt1[48:576] == raw[48:576], "header strings differ from attempt 1")

    spec = importlib.util.spec_from_file_location("diagnostic_parser", PARSER)
    require(spec is not None and spec.loader is not None, "cannot load initramfs parser")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    baseline_members = module.parse_newc(ac_initramfs)
    members = module.parse_newc(ramdisk)
    require(set(members) == set(baseline_members) | {"bin/provenance-record"}, "initramfs inventory changed")
    for name in set(baseline_members) - {"init", "bin/usb-net"}:
        require(members[name] == baseline_members[name], f"unexpected initramfs delta: {name}")
    for source, member in (("init", "init"), ("usb-net", "bin/usb-net"), ("provenance-record", "bin/provenance-record")):
        require(members[member].data == (SOURCE_DIR / source).read_bytes(), f"source mismatch: {source}")
    joined = b"".join(members[name].data for name in ("init", "bin/usb-net", "bin/provenance-record"))
    for token in (
        b"GEMINI_DVFSP_PROVENANCE_DIAGNOSTIC_20260815",
        b"/sys/kernel/debug/gemini_dvfsp_provenance/state",
        b"legacy-android-rndis-enabled",
        b"42:00:15:19:84:00",
        b"10.15.19.82/24",
        b"sysfs=restored-ro",
        b"automatic_reboot=none",
    ):
        require(token in joined, f"diagnostic contract missing: {token!r}")
    for pattern in (rb"/dev/mmc", rb"/dev/watchdog", rb"reboot\s+-", rb"cpu.*/online.*>"):
        require(re.search(pattern, joined) is None, f"unsafe diagnostic action: {pattern!r}")

    mutation_count = 0
    for mutate in ("magic", "kernel", "ramdisk", "tail", "id"):
        bad_raw = bytearray(raw)
        bad_padded = bytearray(padded)
        if mutate == "magic":
            bad_raw[0] ^= 1
        elif mutate == "kernel":
            bad_raw[PAGE + 10] ^= 1
        elif mutate == "ramdisk":
            bad_raw[align(PAGE + len(kernel)) + 10] ^= 1
        elif mutate == "tail":
            bad_padded[-1] = 1
        else:
            bad_raw[576] ^= 1
        try:
            validate_serialization(bytes(bad_raw), bytes(bad_padded), active, kernel, ramdisk)
        except AssertionError:
            mutation_count += 1
    require(mutation_count == 5, "negative mutations were not all rejected")
    print("validation=provenance-observer-vendor-rndis-candidate")
    print("kernel_dtb_config_identical_to_attempt_1=yes")
    print("ramdisk_observation_path_delta=exact")
    print("negative_mutations_rejected=5")
    print("result=pass")


if __name__ == "__main__":
    main()
