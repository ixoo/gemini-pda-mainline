#!/usr/bin/env python3
"""Independently validate the parallel-disjoint-load Android-v0 candidate."""

import argparse
import hashlib
import re
import struct
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ASSEMBLER = SCRIPT_DIR / "assemble.py"
BUILDER = SCRIPT_DIR / "build-candidate.sh"
PARENT_ASSEMBLER = (
    SCRIPT_DIR.parent.parent
    / "2026-08-03-a72-cpu9-multiline-integrity"
    / "scripts"
    / "assemble.py"
)
SOURCE_BUILDER = (
    SCRIPT_DIR.parent.parent
    / "2026-08-02-a72-cpu8-held-online"
    / "scripts"
    / "build-candidate.sh"
)
EXPECTED = {
    "assembler_sha256": "9938defe0e4b83d0845135c4a27b534f5d28fafa5eac4bbe345f7badf2405094",
    "parent_assembler_sha256": "a7e14b94947aca21038668463b307bbcf59304d55e329e6d7278b4ae2778ea1d",
    "builder_sha256": "66545973771b49d79a903f620ca81ed3ecff041e941c14bacb31d45419e45972",
    "source_builder_sha256": "65c39fa45b1f76fb85780473feb3b675bd5e6647934e68be2761bc823c07e0fe",
    "repository_commit": "ad7807ccc50bebd0aaeafcbe4dadb4c11c44b850",
    "terminal_patchset_sha256": "2d94a2cd489e33a7df854ffec7533fbf969dc9c810e9eece57d118b905060310",
    "coherence_patchset_sha256": "d4c40577b9e91fedfde048b29cb203311de264c526c71e3abd907fc6fafcf67f",
    "multiline_patchset_sha256": "c7a9b020563c4abb74059bbf72705839c528a81d577c7031ddfb36de647fd896",
    "parallel_patchset_sha256": "94d3b07355e1ddb67f3f643165570255bb1f42131b3b67c074d270e8581989e2",
    "kernel_field_sha256": "8bbbc62e997c7140f2648d5da2d825622ef19cb0eba94684218ab4d049a96e0a",
    "active_boot_sha256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "active_ramdisk_sha256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "raw_sha256": "6673d9ff6b9ff0a2bb4cf7a89815d73022208975dca713176c71a3b0865c7c51",
    "padded_sha256": "0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb",
}
RAW_NAME = "gemian-a72-cpu9-parallel-disjoint-load.boot.img"
PADDED_NAME = "boot2-padded.img"
EXPECTED_CMDLINE = b"bootopt=64S3,32N2,64N2 log_buf_len=4M"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def validate_tools() -> None:
    assembler = ASSEMBLER.read_bytes()
    builder = BUILDER.read_bytes()
    parent_assembler = PARENT_ASSEMBLER.read_bytes()
    source_builder = SOURCE_BUILDER.read_bytes()
    require(digest(assembler) == EXPECTED["assembler_sha256"], "assembler changed")
    require(digest(builder) == EXPECTED["builder_sha256"], "builder changed")
    require(
        digest(parent_assembler) == EXPECTED["parent_assembler_sha256"],
        "parent assembler changed",
    )
    require(
        digest(source_builder) == EXPECTED["source_builder_sha256"],
        "source builder changed",
    )
    tooling = assembler + builder + parent_assembler + source_builder
    tool_hashes = {
        "assembler_sha256",
        "parent_assembler_sha256",
        "builder_sha256",
        "source_builder_sha256",
    }
    for key, value in EXPECTED.items():
        if key not in tool_hashes | {"active_ramdisk_sha256"}:
            require(value.encode() in tooling, f"tooling lacks {key}")
    for pattern in (
        rb"/dev/mmc",
        rb"/dev/block",
        rb"192\.168\.",
        rb"\bssh\b",
        rb"\bnc\b",
        rb"\breboot\b",
        rb"\bpoweroff\b",
        rb"\bshutdown\b",
    ):
        require(re.search(pattern, builder) is None, f"device action in builder: {pattern!r}")
    run = subprocess.run(
        [str(BUILDER), "--help"], check=True, capture_output=True, text=True
    )
    require("--bundle DIR" in run.stdout, "builder help changed")


def validate_candidate(candidate: Path) -> None:
    manifest = candidate / "SHA256SUMS"
    require(manifest.is_file() and not manifest.is_symlink(), "unsafe manifest")
    seen = set()
    for line in manifest.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (?:\./)?([A-Za-z0-9_.-]+)", line)
        require(match is not None, f"unsafe manifest record: {line!r}")
        expected, name = match.groups()
        path = candidate / name
        require(
            name not in seen and path.is_file() and not path.is_symlink(),
            f"unsafe file: {name}",
        )
        require(digest(path.read_bytes()) == expected, f"manifest mismatch: {name}")
        seen.add(name)
    require(
        seen == {RAW_NAME, PADDED_NAME, "analysis.txt", "provenance.txt"},
        "inventory changed",
    )

    raw = (candidate / RAW_NAME).read_bytes()
    padded = (candidate / PADDED_NAME).read_bytes()
    require(
        len(raw) == 14_809_088 and digest(raw) == EXPECTED["raw_sha256"],
        "raw changed",
    )
    require(
        len(padded) == 16_777_216
        and digest(padded) == EXPECTED["padded_sha256"],
        "padded changed",
    )
    require(padded[: len(raw)] == raw and set(padded[len(raw) :]) <= {0}, "padding changed")
    require(raw[:8] == b"ANDROID!", "Android magic changed")
    fields = struct.unpack_from("<10I", raw, 8)
    kernel_size, kernel_addr, ramdisk_size, ramdisk_addr = fields[:4]
    second_size, second_addr, tags_addr, page_size, dt_size, unused = fields[4:]
    require(
        (kernel_addr, ramdisk_addr, second_addr, tags_addr, page_size)
        == (0x40080000, 0x45000000, 0x40F00000, 0x44000000, 2048),
        "header addresses changed",
    )
    require((second_size, dt_size, unused) == (0, 0, 0), "v0 layout changed")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(
        cmdline == EXPECTED_CMDLINE and raw[48:64].rstrip(b"\0") == b"",
        "header strings changed",
    )
    kernel_offset = page_size
    ramdisk_offset = kernel_offset + align(kernel_size, page_size)
    require(
        ramdisk_offset + align(ramdisk_size, page_size) == len(raw),
        "extents changed",
    )
    kernel = raw[kernel_offset : kernel_offset + kernel_size]
    ramdisk = raw[ramdisk_offset : ramdisk_offset + ramdisk_size]
    require(
        kernel_size == 8_451_693
        and digest(kernel) == EXPECTED["kernel_field_sha256"],
        "kernel changed",
    )
    require(
        ramdisk_size == 6_354_621
        and digest(ramdisk) == EXPECTED["active_ramdisk_sha256"],
        "ramdisk changed",
    )
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    require(
        raw[576:596] == image_id.digest() and set(raw[596:608]) <= {0},
        "legacy image ID changed",
    )
    evidence = (candidate / "analysis.txt").read_text() + (
        candidate / "provenance.txt"
    ).read_text()
    for key, value in EXPECTED.items():
        if key not in {
            "assembler_sha256",
            "parent_assembler_sha256",
            "builder_sha256",
            "source_builder_sha256",
        }:
            require(f"{key}={value}" in evidence, f"evidence lacks {key}")
    for token in (
        "experiment=2026-08-03-a72-cpu9-parallel-disjoint-load",
        "device_access=none",
        "partition_write=none",
        "runtime_result=not-tested",
        "raw_assemblies_identical=yes",
        "padded_constructions_identical=yes",
    ):
        require(token in evidence, f"evidence lacks {token}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    validate_tools()
    validate_candidate(args.candidate.resolve())
    print("validation=cpu9-parallel-disjoint-load-candidate")
    print("checks=tool-pins,manifest,android-v0,ramdisk,padding,provenance,offline-only")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
