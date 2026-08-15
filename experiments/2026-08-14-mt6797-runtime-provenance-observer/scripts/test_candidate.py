#!/usr/bin/env python3
"""Independently validate the provenance-observer Android-v0 container."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path
from typing import Callable


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENTS = SCRIPT_DIR.parent.parent
ASSEMBLER = SCRIPT_DIR / "assemble.py"
BUILDER = SCRIPT_DIR / "build-candidate.sh"
PARENT_ASSEMBLER = (
    EXPERIMENTS
    / "2026-08-02-gemian-a72-bounded-observer-boot"
    / "scripts"
    / "assemble.py"
)
EXPECTED = {
    "assembler_sha256": "3e9ec896c3ff3e7f4f9849cd8f87c5fba28e65368a4abe335c2309773e826c2e",
    "builder_sha256": "7182554f5a72720b990c2527e7198a5f33aea6cea8b3ef64ff6f8360b1ab4a72",
    "parent_assembler_sha256": "532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3",
    "repository_commit": "3556a9b07b841cc3ba99f0a5a5e9c2a03575e009",
    "source_commit": "d388d350cb2dda8f23b99be6fa5db9628896e87f",
    "patched_commit": "f3d2a14bd1b8355c68e59e8bd4be6bc1525f9c24",
    "patch_sha256": "3520538de1c31ea592c2f0c76af7deef10f5c1ee00689d74bdac17def48dbb11",
    "package_sha256sums": "4ed3b81a09f992bb0c80e66d35aa0f9a91bab72b9a14f288f284648abcb76821",
    "kernel_sha256": "d49d03911837af1519efc3089018e505e2a213f4682dd7cb25a751e65f8cdb7d",
    "active_boot_sha256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "ramdisk_sha256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "raw_sha256": "e354ee4b8265d2226e49d2c9376ec3e6e39eee83fd413490de29de1c1500b72b",
    "padded_sha256": "b17400c59f0a68db602c66cb5d83ec1c6161e98dcbd3e5d3ffece0b5c69f23a9",
}
RAW_NAME = "gemian-runtime-provenance-observer.boot.img"
EXPECTED_FILES = {
    RAW_NAME,
    "boot2-padded.img",
    "analysis.txt",
    "provenance.txt",
    "SHA256SUMS",
}
CMDLINE = b"bootopt=64S3,32N2,64N2 log_buf_len=4M"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int, page: int = 2048) -> int:
    return (value + page - 1) // page * page


def records(path: Path, expected_keys: set[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"([a-z0-9_]+)=([^\r\n]+)", line)
        require(match is not None, f"malformed evidence record: {path.name}")
        key, value = match.groups()
        require(key not in result, f"duplicate evidence key: {path.name}:{key}")
        result[key] = value
    require(set(result) == expected_keys, f"evidence inventory changed: {path.name}")
    return result


def validate_tools() -> None:
    assembler = ASSEMBLER.read_bytes()
    builder = BUILDER.read_bytes()
    parent = PARENT_ASSEMBLER.read_bytes()
    require(digest(assembler) == EXPECTED["assembler_sha256"], "assembler changed")
    require(digest(builder) == EXPECTED["builder_sha256"], "builder changed")
    require(
        digest(parent) == EXPECTED["parent_assembler_sha256"],
        "pinned parent assembler changed",
    )
    tooling = assembler + builder
    for key, value in EXPECTED.items():
        if key not in {"builder_sha256", "active_boot_sha256", "ramdisk_sha256"}:
            require(value.encode() in tooling, f"tooling lacks pinned identity: {key}")
    for pattern in (
        rb"/dev/mmc",
        rb"/dev/block",
        rb"192\.168\.",
        rb"\bssh\b",
        rb"\bscp\b",
        rb"\brsync\b",
        rb"\bnc\b",
        rb"\bnetcat\b",
        rb"\breboot\b",
        rb"\bpoweroff\b",
        rb"\bshutdown\b",
    ):
        require(
            re.search(pattern, tooling) is None,
            f"device or remote action in offline tooling: {pattern!r}",
        )
    require(
        builder.count(b'python3 "${assembler}" --active-boot "${active_boot}"') == 2,
        "builder must perform exactly two raw assemblies",
    )
    require(
        builder.count(
            b'cmp -s "${stage}/boot2-padded.img" "${replica}/boot2-padded.img"'
        )
        == 1,
        "builder must compare exactly two padding constructions",
    )
    run = subprocess.run(
        [str(BUILDER), "--help"], check=True, capture_output=True, text=True
    )
    require("--bundle DIR" in run.stdout, "builder help changed")


def validate_bundle(bundle: Path) -> bytes:
    manifest = bundle / "SHA256SUMS"
    build_json = bundle / "provenance/build.json"
    kernel_path = bundle / "outputs/Image.gz-dtb"
    for path in (manifest, build_json, kernel_path):
        require(path.is_file() and not path.is_symlink(), f"unsafe bundle input: {path}")
    require(
        digest(manifest.read_bytes()) == EXPECTED["package_sha256sums"],
        "package manifest changed",
    )
    subprocess.run(
        ["sha256sum", "--check", "--strict", "SHA256SUMS"],
        cwd=bundle,
        check=True,
        capture_output=True,
        text=True,
    )
    kernel = kernel_path.read_bytes()
    require(digest(kernel) == EXPECTED["kernel_sha256"], "bundle kernel changed")
    provenance = json.loads(build_json.read_text())
    expected_provenance = {
        "repository_commit": EXPECTED["repository_commit"],
        "source_commit": EXPECTED["source_commit"],
        "patched_commit": EXPECTED["patched_commit"],
        "patch_sha256": EXPECTED["patch_sha256"],
        "purpose": "vendor-runtime-provenance-full-link-compile-review-only",
        "build_mode": "provenance-observer",
        "normal_patch_application": True,
        "config_delta_exact": True,
        "dct_project": "k97v1_64_bsp",
        "dct_project_matches_config": True,
        "full_kernel_link": True,
        "unresolved_symbol_count": 0,
        "hardware_write": "none",
        "cpu8_cpu9_admission": "closed",
        "boot_candidate": False,
    }
    for key, value in expected_provenance.items():
        require(provenance.get(key) == value, f"compile provenance changed: {key}")
    return kernel


def validate_candidate(candidate: Path, bundle: Path, active_boot: Path) -> None:
    entries = list(candidate.iterdir())
    require(
        all(
            entry.is_file()
            and not entry.is_symlink()
            and entry.stat().st_nlink == 1
            for entry in entries
        ),
        "unsafe candidate entry",
    )
    require({entry.name for entry in entries} == EXPECTED_FILES, "inventory changed")

    manifest = candidate / "SHA256SUMS"
    seen: set[str] = set()
    for line in manifest.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (?:\./)?([A-Za-z0-9_.-]+)", line)
        require(match is not None, "unsafe manifest record")
        expected, name = match.groups()
        path = candidate / name
        require(name not in seen and path.is_file() and not path.is_symlink(), "unsafe file")
        require(digest(path.read_bytes()) == expected, f"manifest mismatch: {name}")
        seen.add(name)
    require(seen == EXPECTED_FILES - {"SHA256SUMS"}, "manifest inventory changed")

    bundle_kernel = validate_bundle(bundle)
    active = active_boot.read_bytes()
    require(
        active_boot.is_file()
        and not active_boot.is_symlink()
        and len(active) == 16_777_216
        and digest(active) == EXPECTED["active_boot_sha256"],
        "known-good active boot changed",
    )

    raw = (candidate / RAW_NAME).read_bytes()
    padded = (candidate / "boot2-padded.img").read_bytes()
    require(
        len(raw) == 14_645_248 and digest(raw) == EXPECTED["raw_sha256"],
        "raw candidate changed",
    )
    require(
        len(padded) == 16_777_216 and digest(padded) == EXPECTED["padded_sha256"],
        "padded candidate changed",
    )
    require(padded[: len(raw)] == raw and not any(padded[len(raw) :]), "padding changed")
    require(raw[:8] == b"ANDROID!", "Android-v0 magic changed")
    fields = struct.unpack_from("<10I", raw, 8)
    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr = fields[:4]
    second_size, second_addr, tags_addr, page_size, dt_size, unused = fields[4:]
    require(
        (kernel_size, kernel_addr, ramdisk_size, ramdisk_addr)
        == (8_287_407, 0x40080000, 6_354_621, 0x45000000),
        "primary Android-v0 fields changed",
    )
    require(
        (second_size, second_addr, tags_addr, page_size, dt_size, unused)
        == (0, 0x40F00000, 0x44000000, 2048, 0, 0),
        "secondary Android-v0 fields changed",
    )
    require(not any(raw[48:64]), "Android-v0 name changed")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(cmdline == CMDLINE, "Android-v0 command line changed")
    kernel_offset = page_size
    ramdisk_offset = align(kernel_offset + kernel_size, page_size)
    raw_end = align(ramdisk_offset + ramdisk_size, page_size)
    require(raw_end == len(raw), "raw extents changed")
    kernel = raw[kernel_offset : kernel_offset + kernel_size]
    ramdisk = raw[ramdisk_offset : ramdisk_offset + ramdisk_size]
    require(kernel == bundle_kernel, "embedded kernel differs from Buildbox")
    require(digest(ramdisk) == EXPECTED["ramdisk_sha256"], "ramdisk changed")
    require(
        not any(raw[kernel_offset + kernel_size : ramdisk_offset])
        and not any(raw[ramdisk_offset + ramdisk_size :]),
        "raw payload padding changed",
    )

    active_fields = struct.unpack_from("<10I", active, 8)
    active_ramdisk_offset = align(2048 + active_fields[0], 2048)
    active_ramdisk = active[
        active_ramdisk_offset : active_ramdisk_offset + active_fields[2]
    ]
    require(ramdisk == active_ramdisk, "ramdisk differs from known-good Gemian")
    require(raw[48:576] == active[48:576], "header strings differ from Gemian")

    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    image = decompressor.decompress(kernel) + decompressor.flush()
    dtb = decompressor.unused_data
    require(
        decompressor.eof
        and not decompressor.unconsumed_tail
        and len(kernel) - len(dtb) == 8_134_495,
        "kernel gzip stream changed",
    )
    require(len(image) == 19_414_312 and image[56:60] == b"ARM\x64", "Image changed")
    require(
        struct.unpack_from("<3Q", image, 8) == (524_288, 22_691_840, 0),
        "arm64 Image header changed",
    )
    require(
        len(dtb) == 152_912
        and dtb[:4] == b"\xd0\x0d\xfe\xed"
        and struct.unpack_from(">I", dtb, 4)[0] == len(dtb),
        "appended DTB changed",
    )
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    require(
        raw[576:596] == image_id.digest() and not any(raw[596:608]),
        "legacy Android-v0 image ID changed",
    )

    analysis_keys = {
        "active_boot_sha256",
        "kernel_field_sha256",
        "kernel_field_size",
        "decompressed_image_size",
        "appended_dtb_size",
        "ramdisk_sha256",
        "ramdisk_size",
        "raw_size",
        "raw_sha256",
        "device_access",
    }
    provenance_keys = {
        "experiment",
        "repository_commit",
        "source_commit",
        "patched_commit",
        "patch_sha256",
        "package_sha256sums",
        "kernel_field_sha256",
        "active_boot_sha256",
        "ramdisk_sha256",
        "raw_sha256",
        "raw_size",
        "padded_sha256",
        "padded_size",
        "raw_assemblies_identical",
        "padded_constructions_identical",
        "container_review",
        "boot_candidate",
        "device_access",
        "partition_write",
        "runtime_result",
    }
    evidence = records(candidate / "analysis.txt", analysis_keys)
    provenance = records(candidate / "provenance.txt", provenance_keys)
    for key in evidence.keys() & provenance.keys():
        require(evidence[key] == provenance[key], f"conflicting evidence: {key}")
    evidence.update(provenance)
    expected_evidence = {
        "experiment": "2026-08-14-mt6797-runtime-provenance-observer",
        "repository_commit": EXPECTED["repository_commit"],
        "source_commit": EXPECTED["source_commit"],
        "patched_commit": EXPECTED["patched_commit"],
        "patch_sha256": EXPECTED["patch_sha256"],
        "package_sha256sums": EXPECTED["package_sha256sums"],
        "kernel_field_sha256": EXPECTED["kernel_sha256"],
        "kernel_field_size": "8287407",
        "decompressed_image_size": "19414312",
        "appended_dtb_size": "152912",
        "active_boot_sha256": EXPECTED["active_boot_sha256"],
        "ramdisk_sha256": EXPECTED["ramdisk_sha256"],
        "ramdisk_size": "6354621",
        "raw_sha256": EXPECTED["raw_sha256"],
        "raw_size": "14645248",
        "padded_sha256": EXPECTED["padded_sha256"],
        "padded_size": "16777216",
        "raw_assemblies_identical": "yes",
        "padded_constructions_identical": "yes",
        "container_review": "offline",
        "boot_candidate": "container-review-pending",
        "device_access": "none",
        "partition_write": "none",
        "runtime_result": "not-tested",
    }
    require(evidence == expected_evidence, "candidate evidence changed")


def refresh_manifest(candidate: Path, name: str) -> None:
    manifest = candidate / "SHA256SUMS"
    suffixes = (f"  ./{name}", f"  {name}")
    lines = manifest.read_text().splitlines()
    matches = [
        index
        for index, line in enumerate(lines)
        if any(line.endswith(suffix) for suffix in suffixes)
    ]
    require(len(matches) == 1, f"manifest record missing: {name}")
    suffix = lines[matches[0]][64:]
    lines[matches[0]] = f"{digest((candidate / name).read_bytes())}{suffix}"
    manifest.write_text("\n".join(lines) + "\n")


def expect_rejected(
    candidate: Path,
    bundle: Path,
    active_boot: Path,
    label: str,
    mutate: Callable[[Path], None],
) -> None:
    with tempfile.TemporaryDirectory(prefix="gemini-provenance-mutation-") as root:
        changed = Path(root) / "candidate"
        shutil.copytree(candidate, changed)
        mutate(changed)
        try:
            validate_candidate(changed, bundle, active_boot)
        except (AssertionError, OSError, ValueError, subprocess.CalledProcessError):
            return
        raise AssertionError(f"mutation accepted: {label}")


def mutation_tests(candidate: Path, bundle: Path, active_boot: Path) -> None:
    def raw_magic(changed: Path) -> None:
        path = changed / RAW_NAME
        payload = bytearray(path.read_bytes())
        payload[0] ^= 1
        path.write_bytes(payload)
        refresh_manifest(changed, RAW_NAME)

    def padded_tail(changed: Path) -> None:
        path = changed / "boot2-padded.img"
        with path.open("r+b") as handle:
            handle.seek(-1, 2)
            handle.write(b"\x01")
        refresh_manifest(changed, "boot2-padded.img")

    def runtime_claim(changed: Path) -> None:
        path = changed / "provenance.txt"
        text = path.read_text().replace("runtime_result=not-tested", "runtime_result=pass")
        path.write_text(text)
        refresh_manifest(changed, "provenance.txt")

    def unsafe_manifest(changed: Path) -> None:
        manifest = changed / "SHA256SUMS"
        manifest.write_text(manifest.read_text() + f"{'0' * 64}  ../escape\n")

    def unsafe_symlink(changed: Path) -> None:
        path = changed / "analysis.txt"
        path.unlink()
        path.symlink_to(changed / "provenance.txt")

    for label, mutate in (
        ("raw-magic", raw_magic),
        ("padded-tail", padded_tail),
        ("runtime-claim", runtime_claim),
        ("unsafe-manifest", unsafe_manifest),
        ("unsafe-symlink", unsafe_symlink),
    ):
        expect_rejected(candidate, bundle, active_boot, label, mutate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--active-boot", type=Path, required=True)
    args = parser.parse_args()
    validate_tools()
    validate_candidate(args.candidate, args.bundle, args.active_boot)
    mutation_tests(args.candidate, args.bundle, args.active_boot)
    print("validation=gemian-runtime-provenance-observer-container")
    print("checks=tooling,bundle,android-v0,kernel,dtb,ramdisk,padding,evidence")
    print("mutation_cases=5")
    print("device_access=none")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
