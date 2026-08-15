#!/usr/bin/env python3
"""Independently validate the changed-kernel pre-init recovery container."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import zlib


SCRIPT_DIR = Path(__file__).resolve().parent
EXPECTED = {
    "assembler": "b7a02f4df0c8558124903be1ea5871fd8d5a1a545ff2292222d0bb5a25ba25d3",
    "builder": "cf5d74bcf7972fe1ce419d40b47b1877a9f894ed46fa3af328462c5053e22e69",
    "active": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "corrected_raw": "1d303dda10b47248f51a1fb2c8f3b1a7b8098522536f4f54ff763c17e75ff310",
    "corrected_manifest": "ad92d496dfb4fd183c35e6e0f32ce626b2045528657fb2567d8561dd02540f1a",
    "bundle_manifest": "8fee014106f2efdf2944227f9615bb6493d63da79b947e34e1d612a32cbd3862",
    "reference_kernel": "d49d03911837af1519efc3089018e505e2a213f4682dd7cb25a751e65f8cdb7d",
    "kernel": "5a8db7fba3b4eb83932042e1105039157d4c8bb70c5794c00b03f9ac46526725",
    "ramdisk": "86a112ef29fecdb8f47b003cbfb08b77b478c4f511cba46acd987af09c921358",
    "dtb": "d70cb5f679ca1135280b80cfc0308e9c4c74bf6a5b8b1a0a8c281a50d4a3d787",
    "raw": "455a85907827e823fea039a721b55f092783aa30130361ebfebef0d07c7eed11",
    "padded": "99414cdecc4e031b12b93114b355fb3d44366d6e7b5092cb4f5f9132755d61c7",
    "manifest": "ac4432bf07785b653473e2b3acf89e4fc1f48dbe952f54e3695349239a8bc596",
}
FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    "provenance-preinit-recovery.boot.img",
    "provenance.txt",
    "SHA256SUMS",
}
PAGE_SIZE = 2048
TARGET_SIZE = 16 * 1024 * 1024


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int) -> int:
    return (value + PAGE_SIZE - 1) // PAGE_SIZE * PAGE_SIZE


def fields(image: bytes) -> tuple[int, ...]:
    require(len(image) >= PAGE_SIZE and image[:8] == b"ANDROID!",
            "Android-v0 header changed")
    return struct.unpack_from("<10I", image, 8)


def appended_dtb(kernel: bytes) -> bytes:
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    decompressor.decompress(kernel)
    decompressor.flush()
    require(decompressor.eof and not decompressor.unconsumed_tail,
            "kernel gzip stream changed")
    dtb = decompressor.unused_data
    require(len(dtb) >= 8 and dtb[:4] == b"\xd0\x0d\xfe\xed",
            "appended DTB magic changed")
    require(struct.unpack_from(">I", dtb, 4)[0] == len(dtb),
            "appended DTB size changed")
    return dtb


def validate_serialization(
    raw: bytes,
    padded: bytes,
    active: bytes,
    corrected: bytes,
    kernel: bytes,
    enforce_identity: bool = True,
) -> None:
    if enforce_identity:
        require(digest(raw) == EXPECTED["raw"], "raw candidate changed")
        require(digest(padded) == EXPECTED["padded"], "padded candidate changed")
    require(len(raw) == 10_108_928, "raw size changed")
    require(len(padded) == TARGET_SIZE, "padded size changed")
    require(padded[: len(raw)] == raw and not any(padded[len(raw) :]),
            "exact zero padding changed")
    expected_fields = (
        8_287_380,
        0x40080000,
        1_818_169,
        0x45000000,
        0,
        0x40F00000,
        0x44000000,
        PAGE_SIZE,
        0,
        0,
    )
    require(fields(raw) == expected_fields, "Android-v0 fields changed")
    require(raw[48:576] == active[48:576] == corrected[48:576],
            "inherited header strings changed")
    require(not any(raw[48:64]), "Android-v0 name changed")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(cmdline == b"bootopt=64S3,32N2,64N2 log_buf_len=4M",
            "command line changed")

    corrected_fields = fields(corrected)
    reference_kernel = corrected[PAGE_SIZE : PAGE_SIZE + corrected_fields[0]]
    corrected_ramdisk_offset = align(PAGE_SIZE + corrected_fields[0])
    ramdisk = corrected[
        corrected_ramdisk_offset : corrected_ramdisk_offset + corrected_fields[2]
    ]
    require(digest(reference_kernel) == EXPECTED["reference_kernel"],
            "reference kernel changed")
    require(digest(ramdisk) == EXPECTED["ramdisk"],
            "corrected diagnostic ramdisk changed")
    require(digest(kernel) == EXPECTED["kernel"], "pre-init kernel changed")
    require(kernel != reference_kernel, "kernel did not change")
    require(appended_dtb(kernel) == appended_dtb(reference_kernel),
            "appended DTB differs from corrected image")
    require(digest(appended_dtb(kernel)) == EXPECTED["dtb"],
            "appended DTB identity changed")

    ramdisk_offset = align(PAGE_SIZE + len(kernel))
    require(raw[PAGE_SIZE : PAGE_SIZE + len(kernel)] == kernel,
            "embedded pre-init kernel changed")
    require(raw[ramdisk_offset : ramdisk_offset + len(ramdisk)] == ramdisk,
            "embedded corrected ramdisk changed")
    require(not any(raw[PAGE_SIZE + len(kernel) : ramdisk_offset]),
            "kernel alignment padding changed")
    require(not any(raw[ramdisk_offset + len(ramdisk) :]),
            "ramdisk alignment padding changed")
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    require(raw[576:596] == image_id.digest(), "canonical Android image ID changed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--active-boot", type=Path, required=True)
    parser.add_argument("--corrected-candidate", type=Path, required=True)
    args = parser.parse_args()

    tools = {
        "assembler": SCRIPT_DIR / "assemble-preinit.py",
        "builder": SCRIPT_DIR / "build-preinit-candidate.sh",
    }
    for name, path in tools.items():
        require(path.is_file() and not path.is_symlink(), f"unsafe tool: {name}")
        require(digest(path.read_bytes()) == EXPECTED[name], f"tool changed: {name}")

    entries = list(args.candidate.iterdir())
    require({entry.name for entry in entries} == FILES, "candidate inventory changed")
    require(all(entry.is_file() and not entry.is_symlink() for entry in entries),
            "unsafe candidate entry")
    require(digest((args.candidate / "SHA256SUMS").read_bytes()) == EXPECTED["manifest"],
            "candidate manifest changed")
    subprocess.run(
        ["sha256sum", "--check", "--strict", "SHA256SUMS"],
        cwd=args.candidate,
        check=True,
        capture_output=True,
    )

    bundle_manifest = args.bundle / "SHA256SUMS"
    corrected_manifest = args.corrected_candidate / "SHA256SUMS"
    require(digest(bundle_manifest.read_bytes()) == EXPECTED["bundle_manifest"],
            "Buildbox manifest changed")
    require(digest(corrected_manifest.read_bytes()) == EXPECTED["corrected_manifest"],
            "corrected candidate manifest changed")
    active = args.active_boot.read_bytes()
    corrected = (
        args.corrected_candidate / "provenance-observer-vendor-rndis.boot.img"
    ).read_bytes()
    kernel = (args.bundle / "outputs/Image.gz-dtb").read_bytes()
    raw = (args.candidate / "provenance-preinit-recovery.boot.img").read_bytes()
    padded = (args.candidate / "boot2-padded.img").read_bytes()
    require(digest(active) == EXPECTED["active"], "active boot changed")
    require(digest(corrected) == EXPECTED["corrected_raw"],
            "corrected observation image changed")
    validate_serialization(raw, padded, active, corrected, kernel)

    provenance = (args.candidate / "provenance.txt").read_text()
    analysis = (args.candidate / "container-analysis.txt").read_text()
    for token in (
        "kernel_changed=yes",
        "appended_dtb_identical_to_corrected=yes",
        "ramdisk_identical_to_corrected=yes",
        "recovery_deadline_seconds=120",
        "automatic_restart=one-emergency-restart",
        "device_storage_access=none",
        "dvfsp_hardware_write=none",
        "cpu8_cpu9_admission=closed",
        "boot_candidate=offline-container-review-pending",
        "device_access=none",
    ):
        require(token in provenance, f"candidate provenance missing: {token}")
    for token in (
        f"kernel_field_sha256={EXPECTED['kernel']}",
        f"ramdisk_sha256={EXPECTED['ramdisk']}",
        f"appended_dtb_sha256={EXPECTED['dtb']}",
        f"raw_sha256={EXPECTED['raw']}",
        "device_access=none",
    ):
        require(token in analysis, f"container analysis missing: {token}")

    dtb = appended_dtb(kernel)
    mutation_count = 0
    for mutation in ("magic", "kernel", "dtb", "ramdisk", "id", "tail"):
        bad_raw = bytearray(raw)
        bad_padded = bytearray(padded)
        if mutation == "magic":
            bad_raw[0] ^= 1
        elif mutation == "kernel":
            bad_raw[PAGE_SIZE + 10] ^= 1
        elif mutation == "dtb":
            bad_raw[PAGE_SIZE + len(kernel) - len(dtb) + 10] ^= 1
        elif mutation == "ramdisk":
            bad_raw[align(PAGE_SIZE + len(kernel)) + 10] ^= 1
        elif mutation == "id":
            bad_raw[576] ^= 1
        else:
            bad_padded[-1] = 1
        if mutation != "tail":
            bad_padded[: len(bad_raw)] = bad_raw
        try:
            validate_serialization(
                bytes(bad_raw), bytes(bad_padded), active, corrected, kernel,
                enforce_identity=False,
            )
        except AssertionError:
            mutation_count += 1
            continue
        raise AssertionError(f"unsafe candidate mutation accepted: {mutation}")
    require(mutation_count == 6, "negative mutations were not all rejected")
    print("validation=provenance-preinit-candidate")
    print("independent_structure=passed")
    print("kernel_changed=yes")
    print("appended_dtb_identical_to_corrected=yes")
    print("ramdisk_identical_to_corrected=yes")
    print("negative_mutations_rejected=6")
    print("device_access=none")
    print("result=pass")


if __name__ == "__main__":
    main()
