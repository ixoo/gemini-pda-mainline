#!/usr/bin/env python3
"""Independently validate the pmsg-witness Android-v0 candidate."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ASSEMBLER = SCRIPT_DIR / "assemble.py"
BUILDER = SCRIPT_DIR / "build-candidate.sh"
PARENT_ASSEMBLER = (
    SCRIPT_DIR.parent.parent
    / "2026-08-28-a72-target-register-capsule"
    / "scripts"
    / "assemble.py"
)
RAW_NAME = "gemian-a72-pmsg-witness.boot.img"
PADDED_NAME = "boot2-padded.img"
EXPECTED_FILES = {
    RAW_NAME,
    PADDED_NAME,
    "analysis.txt",
    "provenance.txt",
    "SHA256SUMS",
}
EXPECTED_CMDLINE = b"bootopt=64S3,32N2,64N2 log_buf_len=4M"
EXPECTED = {
    "assembler_sha256": "11fd71cdc0551e16422f61ea967b2111647dd39185ac492a98c19ba4df89173a",
    "parent_assembler_sha256": "ed7d52e4bb5f6137c587b446171dfd3fafc8f78fa70e59dacd19b251c7ca5701",
    "builder_sha256": "f0e8d8d0d370a067703d67db03163e921cfe4c193d9f74e96769090232d54dfe",
    "repository_commit": "5899bda178aca1363073c7bcc80eddf4e71c07e8",
    "source_commit": "59e00a9144d782e148332009a835b99c43382467",
    "compile_manifest_sha256": "edb1fd6498e599761cbf0237f9e590388c156fdaf73735ec7af7236be168771d",
    "register_patchset_sha256": "71ef281aae8d0b99d0421b81bd3d61d82ab090125c4885977ba39d8280838469",
    "pmsg_patchset_sha256": "6663fe7b073ce2e939bf2ba6ce3de28e824cf3b30d1653c4d3c272bf3ba2bd46",
    "kernel_field_sha256": "b056043221ba934dc970eb7f22a8444a05aba4a58a25ba66412f7d12735c54e7",
    "active_boot_sha256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "active_ramdisk_sha256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "raw_sha256": "f2be7936996ea5a2d94f236c584e2b41b1b61a6eb8877e615a2b5d344547fdad",
    "padded_sha256": "0814c06b9bb41aa7ec666ad1abbb4bbf86e113e11878ac3de159d6cec3112f78",
    "analysis_sha256": "e7b12b97f72066c661f856172d122ec9e8332d1b69fc841347edac7794ab3b90",
    "provenance_sha256": "37380115c56a85743d56fb43e2f0218c8db9775e9195411e718dc6c3aa76795b",
    "manifest_sha256": "38112dbb0a783c8fac0234f3856ed85488560bb16a4196ad9ec7248cb2b0e8dc",
    "image_id": "deff7d6a49e6fab7e082945b765b6d17f38a8975",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def records(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"([a-z0-9_]+)=([^\r\n]+)", line)
        require(match is not None, f"malformed record: {path.name}: {line!r}")
        key, value = match.groups()
        require(key not in result, f"duplicate record: {path.name}:{key}")
        result[key] = value
    return result


def validate_tools() -> None:
    builder = BUILDER.read_bytes()
    assembler = ASSEMBLER.read_bytes()
    parent = PARENT_ASSEMBLER.read_bytes()
    require(digest(builder) == EXPECTED["builder_sha256"], "builder changed")
    require(digest(assembler) == EXPECTED["assembler_sha256"], "assembler changed")
    require(
        digest(parent) == EXPECTED["parent_assembler_sha256"],
        "parent assembler changed",
    )
    tooling = builder + assembler + parent
    for key, value in EXPECTED.items():
        if key not in {
            "analysis_sha256",
            "builder_sha256",
            "parent_assembler_sha256",
            "provenance_sha256",
            "manifest_sha256",
            "image_id",
        }:
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
        require(re.search(pattern, tooling) is None, f"device action in tooling: {pattern!r}")
    run = subprocess.run(
        [str(BUILDER), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    require("--bundle DIR" in run.stdout, "builder help changed")


def validate_candidate(candidate: Path) -> None:
    entries = list(candidate.iterdir())
    require({entry.name for entry in entries} == EXPECTED_FILES, "inventory changed")
    for entry in entries:
        mode = stat.S_IMODE(entry.stat().st_mode)
        require(
            entry.is_file() and not entry.is_symlink() and entry.stat().st_nlink == 1,
            f"unsafe candidate entry: {entry.name}",
        )
        require(mode == 0o600, f"unsafe candidate mode: {entry.name}")

    manifest = candidate / "SHA256SUMS"
    seen: set[str] = set()
    for line in manifest.read_text().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  \./([A-Za-z0-9_.-]+)", line)
        require(match is not None, f"unsafe manifest record: {line!r}")
        expected, name = match.groups()
        path = candidate / name
        require(
            name not in seen and path.is_file() and not path.is_symlink(),
            f"unsafe file: {name}",
        )
        require(digest(path.read_bytes()) == expected, f"manifest mismatch: {name}")
        seen.add(name)
    require(seen == EXPECTED_FILES - {"SHA256SUMS"}, "manifest inventory changed")

    raw = (candidate / RAW_NAME).read_bytes()
    padded = (candidate / PADDED_NAME).read_bytes()
    require(
        len(raw) == 14_815_232 and digest(raw) == EXPECTED["raw_sha256"],
        "raw changed",
    )
    require(
        len(padded) == 16_777_216 and digest(padded) == EXPECTED["padded_sha256"],
        "padded changed",
    )
    require(
        padded[: len(raw)] == raw and set(padded[len(raw) :]) <= {0},
        "padding changed",
    )
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
    require(ramdisk_offset + align(ramdisk_size, page_size) == len(raw), "extents changed")
    kernel = raw[kernel_offset : kernel_offset + kernel_size]
    ramdisk = raw[ramdisk_offset : ramdisk_offset + ramdisk_size]
    require(
        kernel_size == 8_457_748 and digest(kernel) == EXPECTED["kernel_field_sha256"],
        "kernel changed",
    )
    require(
        ramdisk_size == 6_354_621 and digest(ramdisk) == EXPECTED["active_ramdisk_sha256"],
        "ramdisk changed",
    )
    image_id = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        image_id.update(payload)
        image_id.update(struct.pack("<I", len(payload)))
    require(image_id.hexdigest() == EXPECTED["image_id"], "computed image ID changed")
    require(
        raw[576:596] == image_id.digest() and set(raw[596:608]) <= {0},
        "header image ID changed",
    )

    analysis = records(candidate / "analysis.txt")
    provenance = records(candidate / "provenance.txt")
    for key in analysis.keys() & provenance.keys():
        require(analysis[key] == provenance[key], f"conflicting evidence: {key}")
    expected_records = {
        "experiment": "2026-08-28-a72-pmsg-witness",
        "repository_commit": EXPECTED["repository_commit"],
        "source_commit": EXPECTED["source_commit"],
        "compile_manifest_sha256": EXPECTED["compile_manifest_sha256"],
        "register_patchset_sha256": EXPECTED["register_patchset_sha256"],
        "pmsg_patchset_sha256": EXPECTED["pmsg_patchset_sha256"],
        "kernel_field_sha256": EXPECTED["kernel_field_sha256"],
        "active_boot_sha256": EXPECTED["active_boot_sha256"],
        "active_ramdisk_sha256": EXPECTED["active_ramdisk_sha256"],
        "raw_sha256": EXPECTED["raw_sha256"],
        "raw_size": "14815232",
        "padded_sha256": EXPECTED["padded_sha256"],
        "padded_size": "16777216",
        "raw_assemblies_identical": "yes",
        "padded_constructions_identical": "yes",
        "device_access": "none",
        "partition_write": "none",
        "runtime_result": "not-tested",
    }
    merged = analysis | provenance
    for key, value in expected_records.items():
        require(merged.get(key) == value, f"evidence changed: {key}")
    require(
        digest((candidate / "analysis.txt").read_bytes()) == EXPECTED["analysis_sha256"],
        "analysis changed",
    )
    require(
        digest((candidate / "provenance.txt").read_bytes())
        == EXPECTED["provenance_sha256"],
        "provenance changed",
    )
    require(digest(manifest.read_bytes()) == EXPECTED["manifest_sha256"], "manifest changed")


def refresh_manifest(candidate: Path, name: str) -> None:
    manifest = candidate / "SHA256SUMS"
    suffix = f"  ./{name}"
    lines = manifest.read_text().splitlines()
    indexes = [index for index, line in enumerate(lines) if line.endswith(suffix)]
    require(len(indexes) == 1, f"manifest record missing: {name}")
    lines[indexes[0]] = f"{digest((candidate / name).read_bytes())}{suffix}"
    manifest.write_text("\n".join(lines) + "\n")


def validate_mutations(candidate: Path) -> None:
    def mutate_raw(root: Path) -> None:
        path = root / RAW_NAME
        data = bytearray(path.read_bytes())
        data[0] ^= 0xFF
        path.write_bytes(data)

    def mutate_padding(root: Path) -> None:
        path = root / PADDED_NAME
        data = bytearray(path.read_bytes())
        data[-1] = 1
        path.write_bytes(data)
        refresh_manifest(root, PADDED_NAME)

    def mutate_provenance(root: Path) -> None:
        path = root / "provenance.txt"
        path.write_text(
            path.read_text().replace(EXPECTED["pmsg_patchset_sha256"], "0" * 64)
        )
        refresh_manifest(root, "provenance.txt")

    def duplicate_provenance(root: Path) -> None:
        path = root / "provenance.txt"
        path.write_text(path.read_text() + "partition_write=changed\n")
        refresh_manifest(root, "provenance.txt")

    def add_file(root: Path) -> None:
        (root / "unexpected.txt").write_text("unexpected\n")

    def unsafe_manifest(root: Path) -> None:
        path = root / "SHA256SUMS"
        path.write_text(path.read_text().replace("./analysis.txt", "../analysis.txt", 1))

    mutations = (
        ("raw-manifest", mutate_raw, "manifest mismatch"),
        ("padding", mutate_padding, "padded changed"),
        ("pmsg-provenance", mutate_provenance, "evidence changed"),
        ("duplicate-provenance", duplicate_provenance, "duplicate record"),
        ("unmanifested-file", add_file, "inventory changed"),
        ("unsafe-manifest", unsafe_manifest, "unsafe manifest record"),
    )
    for name, mutate, expected in mutations:
        with tempfile.TemporaryDirectory(prefix=f"a72-pmsg-{name}-") as temporary:
            root = Path(temporary) / "candidate"
            shutil.copytree(candidate, root)
            mutate(root)
            try:
                validate_candidate(root)
            except AssertionError as error:
                require(expected in str(error), f"{name} rejected for wrong reason: {error}")
            else:
                raise AssertionError(f"mutation accepted: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    require(
        args.candidate.is_dir() and not args.candidate.is_symlink(),
        "unsafe candidate root",
    )
    candidate = args.candidate.resolve()
    validate_tools()
    validate_candidate(candidate)
    validate_mutations(candidate)
    print("validation=a72-pmsg-witness-candidate")
    print("assembler_chain=pinned-transitive")
    print("candidate_mutations=6-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
