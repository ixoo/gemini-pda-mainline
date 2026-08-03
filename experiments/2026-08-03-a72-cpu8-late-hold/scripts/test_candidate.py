#!/usr/bin/env python3
"""Independently validate the late-hold Android-v0 boot candidate."""

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
SOURCE_BUILDER = (
    SCRIPT_DIR.parent.parent
    / "2026-08-02-a72-cpu8-held-online"
    / "scripts"
    / "build-candidate.sh"
)

EXPECTED = {
    "assembler_sha256": "c53c40898a25b1b4a0ddeaab310d7e8cb84e08bb4ba9edd8f0e05129fceaeccf",
    "source_builder_sha256": "65c39fa45b1f76fb85780473feb3b675bd5e6647934e68be2761bc823c07e0fe",
    "repository_commit": "cc20c4a57fa467ee803d0a4b5b31e5babb7b52b5",
    "late_patchset_sha256": "f2bebc4a04888a6c83f0dc72c2de56d350c2a52ab9779ef07e3a01cb5b544d91",
    "kernel_field_sha256": "9827c9c8c66501a913e38c255aa8a15e6eaf784f3e7c57d032d76809e80710cf",
    "active_boot_sha256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "active_ramdisk_sha256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "raw_sha256": "53ba2e4dbc204962e7b195bbda80c5e592375878105702731420b24f9466c475",
    "padded_sha256": "2e81e18610d99c69bee8867d2fe960245dfcdda1ca583965724598255ea871af",
}
RAW_NAME = "gemian-a72-cpu8-late-hold.boot.img"
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
        require(path.is_file() and not path.is_symlink(), f"unsafe candidate file: {name}")
        require(digest(path.read_bytes()) == expected, f"manifest mismatch: {name}")
    require(
        seen == {RAW_NAME, PADDED_NAME, "analysis.txt", "provenance.txt"},
        "candidate manifest inventory changed",
    )


def validate_tools() -> None:
    assembler = ASSEMBLER.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    source_builder = SOURCE_BUILDER.read_text(encoding="utf-8")
    require(
        digest((SCRIPT_DIR.parent.parent / "2026-08-02-a72-cpu8-held-online" / "scripts" / "assemble.py").read_bytes())
        == EXPECTED["assembler_sha256"],
        "pinned held-online assembler changed",
    )
    require(
        digest(SOURCE_BUILDER.read_bytes()) == EXPECTED["source_builder_sha256"],
        "pinned held-online builder changed",
    )
    require(EXPECTED["kernel_field_sha256"] in assembler, "assembler kernel changed")
    for value in EXPECTED.values():
        require(
            value in assembler or value in builder or value in source_builder,
            f"tooling lacks identity: {value}",
        )
    for token in (
        "late-hold-compile-review-only",
        "source held-online candidate builder changed",
        "late-hold patchset changed",
        "gemian-a72-cpu8-late-hold-candidate",
    ):
        require(token in builder, f"builder contract lacks: {token}")
    for pattern in (
        r"/dev/mmc",
        r"/dev/block",
        r"192\.168\.",
        r"\bssh\b",
        r"\bnc\b",
        r"\bnetcat\b",
        r"\breboot\b",
        r"\bpoweroff\b",
        r"\bshutdown\b",
    ):
        require(re.search(pattern, builder) is None, f"builder gained device action: {pattern}")
    help_run = subprocess.run(
        [str(BUILDER), "--help"], check=True, capture_output=True, text=True
    )
    require("--bundle DIR" in help_run.stdout, "builder help contract changed")


def validate_candidate(candidate: Path) -> None:
    parse_manifest(candidate)
    raw = (candidate / RAW_NAME).read_bytes()
    padded = (candidate / PADDED_NAME).read_bytes()
    require(len(raw) == 14_802_944, "raw size changed")
    require(digest(raw) == EXPECTED["raw_sha256"], "raw identity changed")
    require(len(padded) == 16_777_216, "padded size changed")
    require(digest(padded) == EXPECTED["padded_sha256"], "padded identity changed")
    require(padded[: len(raw)] == raw, "padded prefix differs from raw image")
    require(set(padded[len(raw) :]) <= {0}, "padded tail is not zero")

    require(raw[:8] == b"ANDROID!", "Android magic changed")
    fields = struct.unpack_from("<10I", raw, 8)
    (
        kernel_size,
        kernel_addr,
        ramdisk_size,
        ramdisk_addr,
        second_size,
        second_addr,
        tags_addr,
        page_size,
        dt_size,
        unused,
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
    require(kernel_size == 8_444_490, "kernel field size changed")
    require(digest(kernel) == EXPECTED["kernel_field_sha256"], "kernel field changed")
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
        if key not in {"assembler_sha256", "source_builder_sha256"}:
            require(f"{key}={value}" in provenance or f"{key}={value}" in analysis,
                    f"candidate evidence lacks: {key}")
    for token in (
        "device_access=none",
        "partition_write=none",
        "runtime_result=not-tested",
        "raw_assemblies_identical=yes",
        "padded_constructions_identical=yes",
    ):
        require(token in provenance or token in analysis, f"evidence lacks: {token}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    validate_tools()
    validate_candidate(args.candidate.resolve())
    print("validation=cpu8-late-hold-candidate")
    print("checks=tool-pins,manifest,android-v0,ramdisk,padding,provenance,offline-only")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
