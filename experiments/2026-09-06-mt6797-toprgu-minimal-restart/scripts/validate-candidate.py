#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Independent offline validator for the private TOPRGU candidate."""
from __future__ import annotations
import argparse
from dataclasses import replace
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import struct
import subprocess
import sys
import zlib

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parents[1]
VALIDATE_DTB = HERE / "scripts" / "validate-dtb.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import candidate_lib as C  # noqa: E402

FILES = {"boot2-padded.img", "Image.gz", "board.dtb", "initramfs.img", "kernel.config", "candidate.json"}
RELEASE = C.RELEASE
PAGE = 2048
FOUNDATION_INITRAMFS_SHA256 = "344d8a8464bee60764df467f166aa73eddfcbd4d362d835aa2d6895534c31c4b"

def require(ok: bool, reason: str) -> None:
    if not ok: raise ValueError(reason)

def derive_expected_initramfs(foundation_initramfs: Path, userspace: Path,
                             credentials: Path, input_id: str) -> tuple[bytes, dict[str, dict[str, object]]]:
    """Independently replay the frozen initramfs assembly contract.

    This intentionally does not call ``candidate_lib.compose_initramfs``: the
    validator must retain an independent assembly path so a production
    builder bug cannot bless its own output.
    """
    foundation = C.regular(foundation_initramfs, "foundation initramfs")
    require(C.sha(foundation) == FOUNDATION_INITRAMFS_SHA256,
            "foundation initramfs identity changed")
    parse, encode = C.load_newc_tools(REPO)
    baseline = parse(foundation)
    require({"init", "bin/busybox", "bin/reboot"} <= set(baseline),
            "foundation initramfs inventory incomplete")
    members = {name: item for name, item in baseline.items() if name not in C.REMOVED}
    template = members["bin/reboot"]
    source_root = REPO / "experiments/2026-09-06-mt6797-toprgu-minimal-restart/initramfs"
    require({path.name for path in source_root.iterdir()} == set(C.PUBLIC_INIT_SOURCE_DIGESTS),
            "published init source inventory changed")
    source_map = {"init": "init", "inittab": "etc/inittab", "usb-auth": "bin/usb-auth",
                  "console-status": "bin/console-status", "admin-shell": "bin/admin-shell",
                  "reboot-toprgu": "bin/reboot"}
    for source, target in source_map.items():
        data = C.regular(source_root / source, source)
        require(C.sha(data) == C.PUBLIC_INIT_SOURCE_DIGESTS[source],
                f"published init source changed: {source}")
        if source in {"init", "reboot-toprgu"}:
            require(data.count(b"INPUT_ID_PLACEHOLDER") == 1, "input marker placeholder missing")
            data = data.replace(b"INPUT_ID_PLACEHOLDER", input_id.encode("ascii"))
        if source != "reboot-toprgu":
            require(not any(token in data for token in C.FORBIDDEN_TEXT),
                    f"unsafe initramfs source: {source}")
        mode = 0o644 if source == "inittab" else 0o755
        members[target] = replace(template, mode=stat.S_IFREG | mode, data=data)
    auth = C.validate_credentials(credentials)
    for name, mode in (("root", stat.S_IFDIR | 0o700), ("root/.ssh", stat.S_IFDIR | 0o700),
                       ("etc/dropbear", stat.S_IFDIR | 0o700)):
        if name not in members:
            members[name] = replace(template, mode=mode, nlink=2, data=b"")
    added = {
        "bin/dropbear": (C.regular(userspace / "dropbear"), 0o755),
        "bin/dropbearkey": (C.regular(userspace / "dropbearkey"), 0o755),
        "bin/dropbearconvert": (C.regular(userspace / "dropbearconvert"), 0o755),
        "bin/keyboard-observe": (C.regular(userspace / "keyboard-observe"), 0o755),
        "bin/kmsg-capture": (C.regular(userspace / "kmsg-capture"), 0o755),
        "bin/kmsg-seal": (C.regular(userspace / "kmsg-seal"), 0o755),
        "etc/passwd": (b"root:x:0:0:Administrator:/root:/bin/admin-shell\n", 0o644),
        "etc/group": (b"root:x:0:\n", 0o644),
        "etc/shells": (b"/bin/admin-shell\n", 0o644),
        "root/.ssh/authorized_keys": (auth["authorized_keys"], 0o600),
        "etc/dropbear/host_key": (auth["dropbear_host_key"], 0o600),
    }
    for name, (data, mode) in added.items():
        require(name not in members, f"initramfs member collision: {name}")
        members[name] = replace(template, mode=stat.S_IFREG | mode, data=data)
    for name, item in members.items():
        if stat.S_ISREG(item.mode) and name not in {"bin/busybox", "bin/reboot"}:
            require(not any(token in item.data for token in C.FORBIDDEN_TEXT),
                    f"forbidden runtime action in {name}")
        if stat.S_ISREG(item.mode) and stat.S_IMODE(item.mode) & 0o111:
            require(not any(token in item.data for token in C.OLD_EXECUTABLE_TEXT),
                    f"old executable marker in {name}")
    first = encode(members)
    require(first == encode(parse(first)), "independent initramfs serialization changed")
    return first, {name: {"mode": oct(item.mode), "size": len(item.data),
                           "sha256": C.sha(item.data)} for name, item in sorted(members.items())}

def validate_members(path: Path, manifest: dict, *, foundation_initramfs: Path,
                     userspace: Path, credentials: Path) -> None:
    # Rebuild the expected archive from the frozen public inputs.  The
    # candidate's member manifest is metadata to check, never the source of
    # truth for expected bytes, modes, sizes, or inventory.
    input_id = manifest.get("input_id", "")
    require(isinstance(input_id, str) and re.fullmatch(r"[0-9a-f]{64}", input_id),
            "candidate input identity missing")
    expected_archive, expected_summary = derive_expected_initramfs(
        foundation_initramfs, userspace, credentials, input_id)
    parse, _ = C.load_newc_tools(REPO)
    expected_members = parse(expected_archive)
    actual_archive = C.regular(path, "initramfs")
    require(actual_archive == expected_archive, "initramfs archive differs from exact derived inputs")
    members = parse(actual_archive)
    require(set(members) == set(expected_members), "initramfs inventory differs from exact derived inputs")
    for name, expected in expected_members.items():
        member = members[name]
        require(member.mode == expected.mode and member.nlink == expected.nlink and
                len(member.data) == len(expected.data) and member.data == expected.data,
                f"initramfs member bytes/mode changed: {name}")
    manifest_members = manifest.get("members")
    require(isinstance(manifest_members, dict) and set(manifest_members) == set(expected_summary),
            "initramfs manifest inventory changed")
    for name, summary in expected_summary.items():
        require(manifest_members.get(name) == summary,
                f"initramfs manifest metadata changed: {name}")
    require("bin/reboot" in members and "bin/reboot-toprgu" not in members, "candidate wrapper placement changed")
    require(stat.S_IMODE(members["bin/reboot"].mode) == 0o755, "candidate wrapper mode changed")
    wrapper = members["bin/reboot"].data
    source_root = REPO / "experiments/2026-09-06-mt6797-toprgu-minimal-restart/initramfs"
    for source_name, member_name in (("init", "init"), ("reboot-toprgu", "bin/reboot")):
        template = C.regular(source_root / source_name, source_name)
        require(template.count(b"INPUT_ID_PLACEHOLDER") == 1 and
                members[member_name].data == template.replace(
                    b"INPUT_ID_PLACEHOLDER", input_id.encode("ascii")),
                f"candidate {member_name} differs from exact input-bound source")
    require(b"input_id=" + input_id.encode("ascii") in members["init"].data and
            wrapper.count(b"input_id=%s") == 1 and
            wrapper.count(b"'" + input_id.encode("ascii") + b"'") == 1,
            "on-device marker input identity changed")
    require(wrapper.count(b"[ \"$#\" -eq 1 ]") == 1 and
            wrapper.count(b"expected_boot=$1") == 1 and
            wrapper.count(b"/proc/sys/kernel/random/boot_id") >= 2 and
            wrapper.count(b"/run/a53/boot-id") >= 2 and
            wrapper.count(b'[ "$boot_id" = "$expected_boot" ]') >= 2 and
            wrapper.count(b"exec /bin/busybox reboot -n -f") == 1 and
            wrapper.count(b"phase=request") == 1 and
            wrapper.count(b"wrapper=busybox-reboot-n-f-v1") == 1,
            "candidate wrapper is not exactly one-shot")
    require(b"wrapper=busybox-reboot-n-f-v1" in members["init"].data,
            "entry marker wrapper contract missing")
    require(b"/bin/reboot\n" not in wrapper and b"Candidate AB" not in wrapper, "old reboot wrapper leaked")
    for name, member in members.items():
        if not stat.S_ISREG(member.mode) or not stat.S_IMODE(member.mode) & 0o111 or member.data.startswith(b"\x7fELF"):
            continue
        require(not any(token in member.data for token in C.OLD_EXECUTABLE_TEXT), f"old executable marker: {name}")
        # Effectful applets remain in BusyBox; only the admitted shell scripts
        # are closed here, with the restart wrapper as the sole reboot owner.
        if name != "bin/reboot":
            require(not any(token in member.data for token in C.FORBIDDEN_TEXT), f"unadmitted action in {name}")
    required = {"bin/dropbear", "bin/kmsg-capture", "bin/kmsg-seal", "bin/keyboard-observe",
                "etc/dropbear/host_key", "root/.ssh/authorized_keys", "bin/reboot"}
    require(required <= set(members), "runtime inventory incomplete")
    for name in ("etc/dropbear/host_key", "root/.ssh/authorized_keys"):
        require(stat.S_IMODE(members[name].mode) == 0o600, f"credential mode changed: {name}")

def validate_container(candidate: Path, manifest: dict) -> None:
    padded = C.regular(candidate / "boot2-padded.img", "padded candidate")
    raw_size = manifest.get("raw_size")
    require(isinstance(raw_size, int) and not isinstance(raw_size, bool),
            "boot2 raw size metadata missing")
    require(len(padded) == 0x01000000 and 0 < raw_size < len(padded), "boot2 size changed")
    require(manifest.get("padded_size") == len(padded), "boot2 padded size metadata changed")
    raw = padded[:raw_size]
    require(padded[raw_size:] == bytes(len(padded) - raw_size), "boot2 padding is not zero")
    require(C.sha(raw) == manifest["raw_sha256"] and C.sha(padded) == manifest["padded_sha256"], "candidate checksum changed")
    require(len(raw) >= PAGE, "Android-v0 header is truncated")
    require(raw[:8] == b"ANDROID!", "Android-v0 magic changed")
    values = struct.unpack_from("<10I", raw, 8)
    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size, second_addr, tags_addr, page, dt_size, unused = values
    require((kernel_addr, ramdisk_addr, second_size, second_addr, tags_addr, page, dt_size, unused) ==
            (0x40200000, 0x45000000, 0, 0x40F00000, 0x44000000, 2048, 0, 0), "LK placement contract changed")
    require(raw[48:64] == b"gemini-toprgu-L\0", "Android-v0 name changed")
    expected_cmdline = b"bootopt=64S3,32N2,64N2"
    require(raw[64:576] == expected_cmdline.ljust(512, b"\0") and
            raw[608:1632] == b"\0" * 1024 and raw[596:608] == b"\0" * 12 and
            raw[1632:PAGE] == b"\0" * (PAGE - 1632),
            "Android-v0 cmdline or reserved header bytes changed")
    image = C.regular(candidate / "Image.gz")
    dtb = C.regular(candidate / "board.dtb")
    ramdisk = C.regular(candidate / "initramfs.img")
    require(kernel_size == len(image) + len(dtb) and ramdisk_size == len(ramdisk), "appended-DTB sizes changed")
    kernel_payload = image + dtb
    digest = hashlib.sha1()
    for payload in (kernel_payload, ramdisk, b""):
        digest.update(payload)
        digest.update(struct.pack("<I", len(payload)))
    require(raw[576:596] == digest.digest(), "Android-v0 payload ID changed")
    kernel_offset = page
    ramdisk_offset = kernel_offset + ((kernel_size + page - 1) // page) * page
    require(raw[kernel_offset:kernel_offset + len(image)] == image and
            raw[kernel_offset + len(image):kernel_offset + kernel_size] == dtb,
            "kernel/DTB payload changed")
    require(raw[kernel_offset + kernel_size:ramdisk_offset] ==
            bytes(ramdisk_offset - (kernel_offset + kernel_size)),
            "kernel page padding changed")
    require(raw[ramdisk_offset:ramdisk_offset + len(ramdisk)] == ramdisk, "ramdisk payload changed")
    raw_end = ramdisk_offset + ((len(ramdisk) + page - 1) // page) * page
    require(raw_end == raw_size, "Android-v0 has trailing or missing raw bytes")
    require(raw[ramdisk_offset + len(ramdisk):raw_end] ==
            bytes(raw_end - (ramdisk_offset + len(ramdisk))),
            "ramdisk page padding changed")
    stream = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        decompressed = stream.decompress(image) + stream.flush()
    except zlib.error as exc:
        raise ValueError("Image.gz is not canonical gzip") from exc
    require(stream.eof and not stream.unused_data and not stream.unconsumed_tail,
            "Image.gz has trailing or incomplete gzip data")
    require(len(decompressed) >= 64 and decompressed[56:60] == b"ARM\x64", "AArch64 Image header missing")
    text_offset, image_size, flags = struct.unpack_from("<3Q", decompressed, 8)
    require(image_size and image_size <= 0x03200000 and len(decompressed) <= 0x03200000 and
            flags == 0x0A and kernel_addr >= text_offset and
            (kernel_addr - text_offset) % 0x200000 == 0,
            "LK ARM64 alignment/header contract changed")
    expected_metadata = {
        "kernel_size": kernel_size, "ramdisk_size": ramdisk_size, "dt_size": 0,
        "page_size": PAGE, "kernel_addr": 0x40200000, "ramdisk_addr": 0x45000000,
        "second_addr": 0x40F00000, "tags_addr": 0x44000000, "dtb_mode": "append",
        "lk_android8_compatible": "yes", "arm64_text_offset": text_offset,
        "arm64_image_size": image_size, "arm64_flags": flags,
        "arm64_placement_base": kernel_addr - text_offset,
        "decompressed_kernel_size": len(decompressed), "file_size": raw_size,
        "sha1_id": digest.hexdigest(),
    }
    require(manifest.get("android_v0") == expected_metadata,
            "Android-v0 manifest metadata changed")

def validate_dtb(candidate: Path, base_dtb: Path, manifest: dict) -> None:
    base_dtb = base_dtb.resolve(strict=True)
    require(C.sha(C.regular(base_dtb, "base DTB")) == C.BASE_DTB_SHA256,
            "base DTB identity changed")
    require(manifest.get("serviceability_dtb_sha256") == C.SERVICEABILITY_DTB_SHA256,
            "serviceability DTB identity changed")
    require(VALIDATE_DTB.is_file() and not VALIDATE_DTB.is_symlink(),
            "DT validator sibling is missing or unsafe")
    subprocess.run([sys.executable, str(VALIDATE_DTB),
                    "--base", str(base_dtb), "--derived", str(candidate / "board.dtb"),
                    "--expected-sha256", C.SERVICEABILITY_DTB_SHA256], check=True)


def validate(candidate: Path, *, base_dtb: Path, foundation_initramfs: Path,
             userspace: Path, credentials: Path) -> dict:
    C.validate_source_pins(REPO)
    require(re.fullmatch(r"candidate-[0-9a-f]{64}", candidate.name) is not None,
            "candidate directory name is not full padded identity")
    require(candidate.is_relative_to(REPO / "artifacts") and
            subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", "--", str(candidate)],
                           check=False).returncode == 0,
            "candidate output is outside ignored artifacts")
    info = candidate.lstat()
    require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700 and
            info.st_uid == os.getuid() and info.st_nlink == 1,
            "candidate directory is not private")
    require({p.name for p in candidate.iterdir()} == FILES, "candidate inventory changed")
    for path in candidate.iterdir():
        member = path.lstat()
        require(stat.S_ISREG(member.st_mode) and member.st_nlink == 1 and
                stat.S_IMODE(member.st_mode) == 0o600, f"candidate member mode changed: {path.name}")
    manifest = json.loads(C.regular(candidate / "candidate.json").decode("utf-8"))
    require(candidate.name == "candidate-" + manifest.get("padded_sha256", ""),
            "candidate directory suffix is not its padded identity")
    require(manifest["release"] == RELEASE and manifest["profile"] == C.PROFILE and
            manifest["physical_admission"] is False, "candidate identity/admission changed")
    require(manifest["package_inventory_sha256"] == C.PACKAGE_INVENTORY_SHA256 and
            manifest["userspace_manifest_sha256"] == C.USERSPACE_MANIFEST_SHA256 and
            manifest["base_dtb_sha256"] == C.BASE_DTB_SHA256, "source identities changed")
    require(C.sha(C.regular(candidate / "Image.gz")) == C.IMAGE_GZ_SHA256 and
            C.sha(C.regular(candidate / "kernel.config")) == C.CONFIG_SHA256 and
            C.sha(C.regular(candidate / "board.dtb")) == manifest["serviceability_dtb_sha256"], "kernel input changed")
    require(C.sha(C.regular(candidate / "initramfs.img")) == manifest["initramfs_sha256"],
            "initramfs identity changed")
    validate_dtb(candidate, base_dtb, manifest)
    C.validate_userspace(userspace)
    expected_input = C.compute_input_id(
        C.regular(candidate / "Image.gz"), C.regular(candidate / "board.dtb"),
        C.regular(foundation_initramfs, "foundation initramfs"), userspace, credentials)
    require(expected_input == manifest.get("input_id"), "candidate input identity changed")
    validate_container(candidate, manifest)
    validate_members(candidate / "initramfs.img", manifest,
                     foundation_initramfs=foundation_initramfs,
                     userspace=userspace, credentials=credentials)
    return {"candidate": manifest["padded_sha256"], "release": RELEASE, "result": "pass"}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--base-dtb", type=Path, required=True)
    p.add_argument("--foundation-initramfs", type=Path, required=True)
    p.add_argument("--userspace", type=Path, required=True)
    p.add_argument("--credentials", type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(validate(a.candidate.resolve(strict=True), base_dtb=a.base_dtb,
                              foundation_initramfs=a.foundation_initramfs,
                              userspace=a.userspace, credentials=a.credentials), sort_keys=True))
    return 0
if __name__ == "__main__": raise SystemExit(main())
