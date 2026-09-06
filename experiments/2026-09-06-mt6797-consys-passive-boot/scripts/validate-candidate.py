#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent offline validator for the passive CONSYS candidate."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[1]
PARENT = REPO / "experiments/2026-09-06-mt6797-toprgu-minimal-restart"
VALIDATE_DTB = PARENT / "scripts/validate-dtb.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_lib as C  # noqa: E402

FILES = {"boot2-padded.img", "Image.gz", "board.dtb", "initramfs.img",
         "kernel.config", "candidate.json"}
MANIFEST_KEYS = {
    "android_v0", "assembly_replays", "base_dtb_sha256", "experiment",
    "initramfs_sha256", "input_id", "members", "package_commit",
    "package_inventory_sha256", "padded_sha256", "padded_size",
    "physical_action", "physical_admission", "preparation_state", "profile",
    "raw_sha256", "raw_size", "release", "schema", "secret_bearing",
    "serviceability_dtb_sha256", "source_commit", "userspace_manifest_sha256",
    "userspace_revision",
}
FIXED_COMMIT = "f9981eaf63381a558f77be251da4c2320cb4321b"
FIXED_REVISION = "e9c028005b88ef8536ecb58c095e8d172253fa12"


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def parent_replay(foundation: Path, userspace: Path, credentials: Path,
                  input_id: str) -> tuple[bytes, dict[str, dict[str, object]]]:
    """Run the independent parent replay path with the new input identity."""
    source = PARENT / "scripts/validate-candidate.py"
    require(C.sha(C.regular(source, "parent replay validator")) ==
            "de4199496f04110d018ba2d89bf747d495ee4106278bff1ac4ccdef114ce71d7",
            "parent replay validator changed")
    spec = importlib.util.spec_from_file_location("consys_parent_replay", source)
    require(spec is not None and spec.loader is not None, "parent replay unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.derive_expected_initramfs(foundation, userspace, credentials, input_id)


def validate_candidate_path(candidate: Path) -> None:
    require(re.fullmatch(r"candidate-[0-9a-f]{64}", candidate.name) is not None,
            "candidate directory name is not full padded identity")
    expected_parent = C.validate_private_root(candidate.parent, "candidates")
    require(candidate.parent == expected_parent and
            candidate.is_relative_to(REPO / "artifacts"),
            "candidate output is outside ignored artifacts")
    info = candidate.lstat()
    require(not candidate.is_symlink() and stat.S_ISDIR(info.st_mode) and
            stat.S_IMODE(info.st_mode) == 0o700 and info.st_uid == os.getuid(),
            "candidate directory is not private")
    require({path.name for path in candidate.iterdir()} == FILES,
            "candidate inventory changed")
    for path in candidate.iterdir():
        member = path.lstat()
        require(stat.S_ISREG(member.st_mode) and not path.is_symlink() and
                member.st_nlink == 1 and stat.S_IMODE(member.st_mode) == 0o600 and
                member.st_uid == os.getuid(), f"unsafe candidate member: {path.name}")


def validate_manifest(manifest: dict, candidate_name: str) -> None:
    require(set(manifest) == MANIFEST_KEYS, "candidate manifest schema changed")
    fixed = {
        "schema": 1, "experiment": HERE.name, "profile": C.PROFILE,
        "release": C.RELEASE, "preparation_state": "preparing",
        "physical_admission": False, "physical_action": "none",
        "secret_bearing": True, "source_commit": FIXED_COMMIT,
        "package_commit": FIXED_COMMIT,
        "package_inventory_sha256": C.PACKAGE_INVENTORY_SHA256,
        "userspace_revision": FIXED_REVISION,
        "userspace_manifest_sha256": C.USERSPACE_MANIFEST_SHA256,
        "base_dtb_sha256": C.BASE_DTB_SHA256,
        "serviceability_dtb_sha256": C.SERVICEABILITY_DTB_SHA256,
        "assembly_replays": 2,
    }
    require(all(manifest.get(key) == value for key, value in fixed.items()),
            "candidate manifest identity/admission changed")
    for key in ("input_id", "initramfs_sha256", "raw_sha256", "padded_sha256"):
        require(isinstance(manifest.get(key), str) and
                re.fullmatch(r"[0-9a-f]{64}", manifest[key]) is not None,
                f"candidate {key} is malformed")
    require(candidate_name == "candidate-" + manifest["padded_sha256"],
            "candidate directory suffix changed")


def validate_dtb(candidate: Path, base_dtb: Path) -> None:
    require(C.sha(C.regular(base_dtb, "base DTB")) == C.BASE_DTB_SHA256,
            "base DTB identity changed")
    subprocess.run([
        sys.executable, str(VALIDATE_DTB), "--base", str(base_dtb),
        "--derived", str(candidate / "board.dtb"),
        "--expected-sha256", C.SERVICEABILITY_DTB_SHA256,
    ], check=True)


def validate_members(candidate: Path, manifest: dict, foundation: Path,
                     userspace: Path, credentials: Path) -> None:
    expected, summary = parent_replay(foundation, userspace, credentials,
                                      manifest["input_id"])
    actual = C.regular(candidate / "initramfs.img", "initramfs")
    require(actual == expected, "initramfs differs from independent replay")
    require(manifest.get("members") == summary, "initramfs manifest metadata changed")
    parse, _ = C.load_newc_tools(REPO)
    members = parse(actual)
    require("bin/reboot" in members and stat.S_IMODE(members["bin/reboot"].mode) == 0o755,
            "inherited TOPRGU wrapper placement changed")
    wrapper = members["bin/reboot"].data
    require(wrapper.count(b"'" + manifest["input_id"].encode("ascii") + b"'") == 1 and
            wrapper.count(b"exec /bin/busybox reboot -n -f") == 1,
            "inherited TOPRGU wrapper identity changed")


def validate_container(candidate: Path, manifest: dict) -> None:
    padded = C.regular(candidate / "boot2-padded.img", "padded candidate")
    raw_size = manifest.get("raw_size")
    require(isinstance(raw_size, int) and not isinstance(raw_size, bool) and
            0 < raw_size < C.LK_LIMIT and len(padded) == C.LK_LIMIT,
            "boot2 size metadata changed")
    require(manifest.get("padded_size") == C.LK_LIMIT, "boot2 padded size changed")
    raw = padded[:raw_size]
    require(padded[raw_size:] == bytes(C.LK_LIMIT - raw_size),
            "boot2 padding is not zero")
    require(C.sha(raw) == manifest["raw_sha256"] and
            C.sha(padded) == manifest["padded_sha256"], "candidate checksum changed")
    require(len(raw) >= C.PAGE and raw[:8] == b"ANDROID!", "Android-v0 header changed")
    values = struct.unpack_from("<10I", raw, 8)
    (kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size,
     second_addr, tags_addr, page, dt_size, unused) = values
    require((kernel_addr, ramdisk_addr, second_size, second_addr, tags_addr,
             page, dt_size, unused) ==
            (0x40200000, 0x45000000, 0, 0x40F00000, 0x44000000, 2048, 0, 0),
            "LK placement changed")
    require(raw[48:64] == b"gemini-consys-P\0", "Android-v0 identity changed")
    cmdline = b"bootopt=64S3,32N2,64N2"
    require(raw[64:576] == cmdline.ljust(512, b"\0") and
            raw[596:608] == b"\0" * 12 and raw[608:1632] == b"\0" * 1024 and
            raw[1632:C.PAGE] == b"\0" * (C.PAGE - 1632),
            "Android-v0 cmdline or reserved bytes changed")
    image = C.regular(candidate / "Image.gz", "kernel Image.gz")
    dtb = C.regular(candidate / "board.dtb", "serviceability DTB")
    ramdisk = C.regular(candidate / "initramfs.img", "initramfs")
    require(kernel_size == len(image) + len(dtb) and ramdisk_size == len(ramdisk),
            "Android-v0 payload sizes changed")
    digest = hashlib.sha1()
    for payload in (image + dtb, ramdisk, b""):
        digest.update(payload)
        digest.update(struct.pack("<I", len(payload)))
    require(raw[576:596] == digest.digest(), "Android-v0 payload ID changed")
    kernel_offset = page
    ramdisk_offset = kernel_offset + ((kernel_size + page - 1) // page) * page
    require(raw[kernel_offset:kernel_offset + len(image)] == image and
            raw[kernel_offset + len(image):kernel_offset + kernel_size] == dtb,
            "kernel/DTB payload changed")
    require(raw[kernel_offset + kernel_size:ramdisk_offset] ==
            bytes(ramdisk_offset - kernel_offset - kernel_size),
            "kernel page padding changed")
    require(raw[ramdisk_offset:ramdisk_offset + len(ramdisk)] == ramdisk,
            "ramdisk payload changed")
    raw_end = ramdisk_offset + ((ramdisk_size + page - 1) // page) * page
    require(raw_end == raw_size and
            raw[ramdisk_offset + ramdisk_size:raw_end] ==
            bytes(raw_end - ramdisk_offset - ramdisk_size),
            "Android-v0 trailing bytes changed")
    stream = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        decompressed = stream.decompress(image) + stream.flush()
    except zlib.error as exc:
        raise ValueError("Image.gz is not canonical gzip") from exc
    require(stream.eof and not stream.unused_data and not stream.unconsumed_tail,
            "Image.gz has trailing or incomplete data")
    require(len(decompressed) >= 64 and decompressed[56:60] == b"ARM\x64",
            "AArch64 Image header missing")
    text_offset, image_size, flags = struct.unpack_from("<3Q", decompressed, 8)
    require(image_size and image_size <= 0x03200000 and
            len(decompressed) <= 0x03200000 and flags == 0x0A and
            kernel_addr >= text_offset and (kernel_addr - text_offset) % 0x200000 == 0,
            "LK ARM64 alignment/header contract changed")
    metadata = {
        "kernel_size": kernel_size, "ramdisk_size": ramdisk_size, "dt_size": 0,
        "page_size": C.PAGE, "kernel_addr": 0x40200000,
        "ramdisk_addr": 0x45000000, "second_addr": 0x40F00000,
        "tags_addr": 0x44000000, "dtb_mode": "append",
        "lk_android8_compatible": "yes", "arm64_text_offset": text_offset,
        "arm64_image_size": image_size, "arm64_flags": flags,
        "arm64_placement_base": kernel_addr - text_offset,
        "decompressed_kernel_size": len(decompressed), "file_size": raw_size,
        "sha1_id": digest.hexdigest(),
    }
    require(manifest.get("android_v0") == metadata,
            "Android-v0 manifest metadata changed")


def validate(candidate: Path, package: Path, foundation: Path, userspace: Path,
             credentials: Path) -> dict[str, str]:
    C.validate_source_pins(REPO)
    candidate = candidate.absolute()
    validate_candidate_path(candidate)
    manifest = json.loads(C.regular(candidate / "candidate.json").decode("utf-8"))
    validate_manifest(manifest, candidate.name)
    C.validate_package(package)
    base_dtb = package / "dtbs/mediatek/mt6797-gemini-pda.dtb"
    validate_dtb(candidate, base_dtb)
    require(C.sha(C.regular(candidate / "Image.gz")) == C.IMAGE_GZ_SHA256 and
            C.sha(C.regular(candidate / "kernel.config")) == C.CONFIG_SHA256 and
            C.sha(C.regular(candidate / "board.dtb")) == C.SERVICEABILITY_DTB_SHA256,
            "kernel candidate input changed")
    C.validate_userspace(userspace)
    expected_id = C.compute_input_id(
        C.regular(candidate / "Image.gz"), C.regular(candidate / "board.dtb"),
        C.regular(foundation, "foundation initramfs"), userspace, credentials)
    require(manifest["input_id"] == expected_id, "candidate input identity changed")
    require(C.sha(C.regular(candidate / "initramfs.img")) == manifest["initramfs_sha256"],
            "initramfs identity changed")
    validate_members(candidate, manifest, foundation, userspace, credentials)
    validate_container(candidate, manifest)
    return {"candidate": manifest["padded_sha256"], "release": C.RELEASE,
            "result": "pass"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--foundation-initramfs", type=Path, required=True)
    parser.add_argument("--userspace", type=Path, required=True)
    parser.add_argument("--credentials", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.candidate, args.package.resolve(strict=True),
                      args.foundation_initramfs.resolve(strict=True),
                      args.userspace.resolve(strict=True),
                      args.credentials.resolve(strict=True))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
