#!/usr/bin/env python3
"""Independently validate the unpark Android-v0 candidate."""

import argparse
import hashlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENTS = SCRIPT_DIR.parent.parent
ASSEMBLER = SCRIPT_DIR / "assemble.py"
BUILDER = SCRIPT_DIR / "build-candidate.sh"
PARENT_ASSEMBLER = (
    EXPERIMENTS
    / "2026-08-03-a72-cpu9-parallel-disjoint-load"
    / "scripts"
    / "assemble.py"
)
SOURCE_BUILDER = (
    EXPERIMENTS
    / "2026-08-02-a72-cpu8-held-online"
    / "scripts"
    / "build-candidate.sh"
)
EXPECTED = {
    "assembler_sha256": "0605ef23fce46a376b779b77c3085d6ff1ef9695b6c4bff14dba67668b21ee9e",
    "parent_assembler_sha256": "9938defe0e4b83d0845135c4a27b534f5d28fafa5eac4bbe345f7badf2405094",
    "builder_sha256": "9d21928e9b8b23a8fd3edfe676df3b9fce4ca9e2f5be152b25205ac85ac5a1b8",
    "source_builder_sha256": "65c39fa45b1f76fb85780473feb3b675bd5e6647934e68be2761bc823c07e0fe",
    "compile_package_sha256sums": "d36a6a12e2ef4d0501df78f8fa9a94e763c1907f155c5f008182eed2d1f0b7f2",
    "repository_commit": "4f647c333056fd51aa2850957bb94ace508bedee",
    "parallel_patchset_sha256": "94d3b07355e1ddb67f3f643165570255bb1f42131b3b67c074d270e8581989e2",
    "scheduler_phase_parent_patchset_sha256": "b2c971d4a1860ec09616a61dbd8a29fde488f7d99deb8bd6bfbf2c517b2c3493",
    "scheduler_patchset_sha256": "bd5799cecd14aa34a87562b09507a6d9f18f11cd138420bcba629f12793e7bfe",
    "kernel_field_sha256": "b7ed626161490c64939f791e1caaaf6f4ffb03ecf55466776a19b74f02bb349c",
    "active_boot_sha256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "active_ramdisk_sha256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "raw_sha256": "f3e235f3c196667e892f6ed611db37f77ab465ce90b59be763bf3dddedc1fd5c",
    "padded_sha256": "5b38e542586cf70f3fcf3de049f351671f96fab985e0d93fa79f90e2d04012c5",
}
RAW_NAME = "gemian-a72-scheduler-unpark.boot.img"
PADDED_NAME = "boot2-padded.img"
EXPECTED_FILES = {RAW_NAME, PADDED_NAME, "analysis.txt", "provenance.txt", "SHA256SUMS"}
EXPECTED_FILE_SHA256 = {
    "analysis.txt": "92e91589e1c2ed8277975db362a8f2244a421cd8496e17a279001dac5c5bc524",
    "provenance.txt": "519df6a18a67dac2805ca4022073e3ca619034d9a088f6b9090b7a4b822883ee",
    "SHA256SUMS": "9928d416e8ad50a35652ab58721c6a3747b1e8f00ff5fa4883e3100550c634f5",
}
EXPECTED_CMDLINE = b"bootopt=64S3,32N2,64N2 log_buf_len=4M"
ASSEMBLER_CHAIN = (
    (ASSEMBLER, EXPECTED["assembler_sha256"]),
    (PARENT_ASSEMBLER, EXPECTED["parent_assembler_sha256"]),
    (
        EXPERIMENTS
        / "2026-08-03-a72-cpu9-multiline-integrity"
        / "scripts"
        / "assemble.py",
        "a7e14b94947aca21038668463b307bbcf59304d55e329e6d7278b4ae2778ea1d",
    ),
    (
        EXPERIMENTS
        / "2026-08-03-a72-cpu9-bounded-coherency"
        / "scripts"
        / "assemble.py",
        "2121b03995070321e49293d7e895433dab7a530de095b760d359910e5598252b",
    ),
    (
        EXPERIMENTS
        / "2026-08-03-a72-cpu9-terminal-attribution"
        / "scripts"
        / "assemble.py",
        "ed11b681d25ccd0c902226f04ecd3435b3dc85233adcc3274885ec08491f8145",
    ),
    (
        EXPERIMENTS
        / "2026-08-03-a72-cpu9-retention-window"
        / "scripts"
        / "assemble.py",
        "f6d36d5eeafe92936fb8c18bddf34eed92f28dd1b602989fb196e83206812885",
    ),
    (
        EXPERIMENTS
        / "2026-08-03-a72-cpu9-cluster-reuse"
        / "scripts"
        / "assemble.py",
        "dbd00ee1f2dfbec6eb8c2d48a8e65a1f2ca888a5e6be400e05620cd04a597358",
    ),
    (
        EXPERIMENTS
        / "2026-08-03-a72-cpu8-late-hold"
        / "scripts"
        / "assemble.py",
        "231f916492bc8477064f792e6bb07ea0d5362b60aa364af44912fb0b205d5ce4",
    ),
    (
        EXPERIMENTS
        / "2026-08-02-a72-cpu8-held-online"
        / "scripts"
        / "assemble.py",
        "c53c40898a25b1b4a0ddeaab310d7e8cb84e08bb4ba9edd8f0e05129fceaeccf",
    ),
    (
        EXPERIMENTS
        / "2026-08-02-a72-one-way-cpu8-boundary"
        / "scripts"
        / "assemble.py",
        "2c6e59da67357c946f1ce6e4300fadaf732add0e124f25ba84aefe2a222bbb4b",
    ),
    (
        EXPERIMENTS
        / "2026-08-02-gemian-a72-bounded-observer-boot"
        / "scripts"
        / "assemble.py",
        "532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3",
    ),
)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int, page: int) -> int:
    return (value + page - 1) // page * page


def validate_tools() -> None:
    builder = BUILDER.read_bytes()
    source_builder = SOURCE_BUILDER.read_bytes()
    assembler_parts = []
    for path, expected in ASSEMBLER_CHAIN:
        require(
            path.is_file() and not path.is_symlink(),
            f"unsafe assembler: {path.name}",
        )
        content = path.read_bytes()
        require(
            digest(content) == expected,
            f"assembler chain changed: {path.parent.parent.name}",
        )
        assembler_parts.append(content)
    require(digest(builder) == EXPECTED["builder_sha256"], "builder changed")
    require(
        digest(source_builder) == EXPECTED["source_builder_sha256"],
        "source builder changed",
    )
    tooling = b"".join(assembler_parts) + builder + source_builder
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
        require(
            re.search(pattern, tooling) is None,
            f"device action in executed tooling: {pattern!r}",
        )
    run = subprocess.run(
        [str(BUILDER), "--help"], check=True, capture_output=True, text=True
    )
    require("--bundle DIR" in run.stdout, "builder help changed")


def validate_candidate(candidate: Path) -> None:
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
        seen == EXPECTED_FILES - {"SHA256SUMS"},
        "inventory changed",
    )

    raw = (candidate / RAW_NAME).read_bytes()
    padded = (candidate / PADDED_NAME).read_bytes()
    require(
        len(raw) == 14_813_184 and digest(raw) == EXPECTED["raw_sha256"],
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
        kernel_size == 8_455_343
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
    evidence_files = ("analysis.txt", "provenance.txt")
    evidence_records = {}
    for name in evidence_files:
        records = {}
        for line in (candidate / name).read_text().splitlines():
            match = re.fullmatch(r"([a-z0-9_]+)=([^\r\n]+)", line)
            require(match is not None, f"malformed evidence record: {name}: {line!r}")
            key, value = match.groups()
            require(key not in records, f"duplicate evidence key: {name}:{key}")
            records[key] = value
        for key in evidence_records.keys() & records.keys():
            require(
                evidence_records[key] == records[key],
                f"conflicting evidence key: {key}",
            )
        evidence_records.update(records)
    expected_evidence = {
        "repository_commit": EXPECTED["repository_commit"],
        "parallel_patchset_sha256": EXPECTED["parallel_patchset_sha256"],
        "scheduler_phase_parent_patchset_sha256": EXPECTED[
            "scheduler_phase_parent_patchset_sha256"
        ],
        "scheduler_patchset_sha256": EXPECTED["scheduler_patchset_sha256"],
        "kernel_field_sha256": EXPECTED["kernel_field_sha256"],
        "active_boot_sha256": EXPECTED["active_boot_sha256"],
        "active_ramdisk_sha256": EXPECTED["active_ramdisk_sha256"],
        "raw_sha256": EXPECTED["raw_sha256"],
        "padded_sha256": EXPECTED["padded_sha256"],
        "experiment": "2026-08-03-a72-scheduler-context",
        "device_access": "none",
        "partition_write": "none",
        "runtime_result": "not-tested",
        "raw_assemblies_identical": "yes",
        "padded_constructions_identical": "yes",
    }
    for key, value in expected_evidence.items():
        require(evidence_records.get(key) == value, f"evidence changed: {key}")
    for name, expected in EXPECTED_FILE_SHA256.items():
        require(digest((candidate / name).read_bytes()) == expected, f"{name} changed")


def refresh_manifest_record(candidate: Path, name: str) -> None:
    manifest = candidate / "SHA256SUMS"
    suffix = f"  ./{name}"
    lines = manifest.read_text().splitlines()
    matches = [index for index, line in enumerate(lines) if line.endswith(suffix)]
    require(len(matches) == 1, f"manifest record missing: {name}")
    lines[matches[0]] = f"{digest((candidate / name).read_bytes())}{suffix}"
    manifest.write_text("\n".join(lines) + "\n")


def validate_mutations(candidate: Path) -> None:
    def raw_manifest_mismatch(mutated: Path) -> None:
        path = mutated / RAW_NAME
        data = bytearray(path.read_bytes())
        data[0] ^= 0xFF
        path.write_bytes(data)

    def padded_identity_mismatch(mutated: Path) -> None:
        path = mutated / PADDED_NAME
        data = bytearray(path.read_bytes())
        data[-1] = 1
        path.write_bytes(data)
        refresh_manifest_record(mutated, PADDED_NAME)

    def provenance_boundary_missing(mutated: Path) -> None:
        path = mutated / "provenance.txt"
        text = path.read_text()
        require("partition_write=none" in text, "test provenance changed")
        path.write_text(text.replace("partition_write=none", "partition_write=changed"))
        refresh_manifest_record(mutated, "provenance.txt")

    def conflicting_provenance(mutated: Path) -> None:
        path = mutated / "provenance.txt"
        path.write_text(path.read_text() + "partition_write=changed\n")
        refresh_manifest_record(mutated, "provenance.txt")

    def unmanifested_entry(mutated: Path) -> None:
        (mutated / "unexpected.txt").write_text("unexpected\n")

    def unsafe_manifest_path(mutated: Path) -> None:
        path = mutated / "SHA256SUMS"
        text = path.read_text()
        require("./analysis.txt" in text, "test manifest changed")
        path.write_text(text.replace("./analysis.txt", "../analysis.txt", 1))

    mutations = (
        ("raw-manifest", raw_manifest_mismatch, f"manifest mismatch: {RAW_NAME}"),
        ("padded-identity", padded_identity_mismatch, "padded changed"),
        (
            "provenance-boundary",
            provenance_boundary_missing,
            "evidence changed: partition_write",
        ),
        ("conflicting-provenance", conflicting_provenance, "duplicate evidence key"),
        ("unmanifested-entry", unmanifested_entry, "inventory changed"),
        ("unsafe-manifest-path", unsafe_manifest_path, "unsafe manifest record"),
    )
    for name, mutate, expected in mutations:
        with tempfile.TemporaryDirectory(prefix=f"a72-unpark-{name}-") as temporary:
            mutated = Path(temporary) / "candidate"
            shutil.copytree(candidate, mutated)
            mutate(mutated)
            try:
                validate_candidate(mutated)
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
    print("validation=a72-scheduler-unpark-candidate")
    print("checks=tool-pins,manifest,android-v0,ramdisk,padding,provenance,offline-only")
    print("assembler_chain=11-pinned-offline")
    print("candidate_mutations=6-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
