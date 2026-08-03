#!/usr/bin/env python3
"""Independently validate the CPU9 Android-v0 boot candidate."""

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
    / "2026-08-03-a72-cpu8-late-hold"
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
    "assembler_sha256": "dbd00ee1f2dfbec6eb8c2d48a8e65a1f2ca888a5e6be400e05620cd04a597358",
    "parent_assembler_sha256": "231f916492bc8477064f792e6bb07ea0d5362b60aa364af44912fb0b205d5ce4",
    "builder_sha256": "6c0e9c313f8273375f96c121ba338238c7963e91aabe801484a359d39366472a",
    "source_builder_sha256": "65c39fa45b1f76fb85780473feb3b675bd5e6647934e68be2761bc823c07e0fe",
    "repository_commit": "c82acf76c6c18fd3280bf8cb4e91a3ac49eaacf1",
    "late_patchset_sha256": "f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91",
    "cpu9_patchset_sha256": "17733d2ae50c16f9d0db2d4bd4075fa5a72ce081606db7d3bf1bfe83f4159a2b",
    "kernel_field_sha256": "7a592d62d837fa61b7c57ec2e8be65d4a25203685b4936f2848fc3600563039a",
    "active_boot_sha256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "active_ramdisk_sha256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "raw_sha256": "fef3d814c217f68ce56e12ca92616915a78e48be5945dee79e87adf149d0e2d3",
    "padded_sha256": "b32bca348efc0fcaffe2b5909c6246d66a4d0fec4102cee091103c42db604d69",
}
RAW_NAME = "gemian-a72-cpu9-cluster-reuse.boot.img"
PADDED_NAME = "boot2-padded.img"
EXPECTED_CMDLINE = b"bootopt=64S3,32N2,64N2 log_buf_len=4M"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int, page_size: int) -> int:
    return (value + page_size - 1) // page_size * page_size


def parse_manifest(candidate: Path) -> None:
    manifest = candidate / "SHA256SUMS"
    require(manifest.is_file() and not manifest.is_symlink(), "unsafe manifest")
    seen = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (?:\./)?([A-Za-z0-9_.-]+)", line)
        require(match is not None, f"unsafe manifest record: {line!r}")
        expected, name = match.groups()
        require(name not in seen, f"duplicate manifest entry: {name}")
        seen.add(name)
        path = candidate / name
        require(path.is_file() and not path.is_symlink(), f"unsafe file: {name}")
        require(digest(path.read_bytes()) == expected, f"manifest mismatch: {name}")
    require(
        seen == {RAW_NAME, PADDED_NAME, "analysis.txt", "provenance.txt"},
        "candidate manifest inventory changed",
    )


def validate_tools() -> None:
    assembler = ASSEMBLER.read_bytes()
    builder = BUILDER.read_bytes()
    source_builder = SOURCE_BUILDER.read_bytes()
    require(digest(assembler) == EXPECTED["assembler_sha256"], "assembler changed")
    require(digest(builder) == EXPECTED["builder_sha256"], "builder changed")
    require(
        digest(PARENT_ASSEMBLER.read_bytes()) == EXPECTED["parent_assembler_sha256"],
        "pinned late-CPU8 assembler changed",
    )
    require(
        digest(source_builder) == EXPECTED["source_builder_sha256"],
        "pinned held-online builder changed",
    )
    tooling = assembler + builder + source_builder
    for value in EXPECTED.values():
        require(value.encode() in tooling or value in {
            EXPECTED["assembler_sha256"], EXPECTED["builder_sha256"]
        }, f"tooling lacks identity: {value}")
    for token in (
        b"cpu9-cluster-reuse-compile-review-only",
        b"late-CPU8 parent patchset changed",
        b"CPU9 patchset changed",
        b"gemian-a72-cpu9-cluster-reuse-candidate",
    ):
        require(token in builder, f"builder contract lacks: {token!r}")
    for pattern in (
        rb"/dev/mmc", rb"/dev/block", rb"192\.168\.", rb"\bssh\b",
        rb"\bnc\b", rb"\bnetcat\b", rb"\breboot\b", rb"\bpoweroff\b",
        rb"\bshutdown\b",
    ):
        require(re.search(pattern, builder) is None, f"builder gained device action: {pattern!r}")
    help_run = subprocess.run(
        [str(BUILDER), "--help"], check=True, capture_output=True, text=True
    )
    require("--bundle DIR" in help_run.stdout, "builder help contract changed")


def validate_candidate(candidate: Path) -> None:
    parse_manifest(candidate)
    raw = (candidate / RAW_NAME).read_bytes()
    padded = (candidate / PADDED_NAME).read_bytes()
    require(len(raw) == 14_804_992, "raw size changed")
    require(digest(raw) == EXPECTED["raw_sha256"], "raw identity changed")
    require(len(padded) == 16_777_216, "padded size changed")
    require(digest(padded) == EXPECTED["padded_sha256"], "padded identity changed")
    require(padded[: len(raw)] == raw, "padded prefix differs from raw image")
    require(set(padded[len(raw) :]) <= {0}, "padded tail is not zero")

    require(raw[:8] == b"ANDROID!", "Android magic changed")
    fields = struct.unpack_from("<10I", raw, 8)
    (
        kernel_size, kernel_addr, ramdisk_size, ramdisk_addr, second_size,
        second_addr, tags_addr, page_size, dt_size, unused,
    ) = fields
    require(page_size == 2048, "page size changed")
    require(kernel_addr == 0x40080000, "kernel address changed")
    require(ramdisk_addr == 0x45000000, "ramdisk address changed")
    require(second_addr == 0x40F00000, "second-stage address changed")
    require(tags_addr == 0x44000000, "tags address changed")
    require(second_size == 0 and dt_size == 0 and unused == 0, "v0 layout changed")
    require(raw[48:64].rstrip(b"\0") == b"", "boot name is not empty")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(cmdline == EXPECTED_CMDLINE, "kernel command line changed")
    require(set(raw[596:608]) <= {0}, "legacy image ID suffix changed")

    kernel_offset = page_size
    ramdisk_offset = kernel_offset + align(kernel_size, page_size)
    end = ramdisk_offset + align(ramdisk_size, page_size)
    require(end == len(raw), "Android-v0 extent does not equal raw image")
    kernel = raw[kernel_offset : kernel_offset + kernel_size]
    ramdisk = raw[ramdisk_offset : ramdisk_offset + ramdisk_size]
    require(kernel_size == 8_446_361, "kernel field size changed")
    require(digest(kernel) == EXPECTED["kernel_field_sha256"], "kernel changed")
    require(ramdisk_size == 6_354_621, "ramdisk size changed")
    require(digest(ramdisk) == EXPECTED["active_ramdisk_sha256"], "ramdisk changed")
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    require(raw[576:596] == image_id.digest(), "legacy image ID is inconsistent")

    provenance = (candidate / "provenance.txt").read_text(encoding="utf-8")
    analysis = (candidate / "analysis.txt").read_text(encoding="utf-8")
    for key, value in EXPECTED.items():
        if key.endswith("_sha256") and key in {
            "assembler_sha256", "parent_assembler_sha256", "builder_sha256",
            "source_builder_sha256",
        }:
            continue
        require(
            f"{key}={value}" in provenance or f"{key}={value}" in analysis,
            f"candidate evidence lacks: {key}",
        )
    for token in (
        "device_access=none", "partition_write=none", "runtime_result=not-tested",
        "raw_assemblies_identical=yes", "padded_constructions_identical=yes",
    ):
        require(token in provenance or token in analysis, f"evidence lacks: {token}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    validate_tools()
    validate_candidate(args.candidate.resolve())
    print("validation=cpu9-cluster-reuse-candidate")
    print("checks=tool-pins,manifest,android-v0,ramdisk,padding,provenance,offline-only")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
