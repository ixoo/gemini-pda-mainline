#!/usr/bin/env python3
"""Independently validate the target-register Android-v0 candidate."""

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
EXPERIMENTS = SCRIPT_DIR.parent.parent
ASSEMBLER = SCRIPT_DIR / "assemble.py"
BUILDER = SCRIPT_DIR / "build-candidate.sh"
RAW_NAME = "gemian-a72-target-register-capsule.boot.img"
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
    "assembler_sha256": "ed7d52e4bb5f6137c587b446171dfd3fafc8f78fa70e59dacd19b251c7ca5701",
    "builder_sha256": "b5ea76570e6af821c6595cd455a6be05402f691aa74736791364756e59585501",
    "repository_commit": "f3627d4e9dc23bd102b827eb8011bdac61b6f8a6",
    "source_commit": "59e00a9144d782e148332009a835b99c43382467",
    "compile_manifest_sha256": "6a1eb12128f69fe34ac2942a2a421d6d916939b22fb5966d7201e909489eadd9",
    "scheduler_patchset_sha256": "bd5799cecd14aa34a87562b09507a6d9f18f11cd138420bcba629f12793e7bfe",
    "register_patchset_sha256": "71ef281aae8d0b99d0421b81bd3d61d82ab090125c4885977ba39d8280838469",
    "kernel_field_sha256": "de81aa06953bf1f6a24a97c88f10f1406f6af0b100f0b3f7b34674240eeefdfa",
    "active_boot_sha256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "active_ramdisk_sha256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "raw_sha256": "d4ae9ee1b2f799e06e0195d8b113ef52cbd2491aa54e331bb79309e34c61922d",
    "padded_sha256": "f8e247e5f067fff562e00d1d96447b236c8ea2ec946c9e493589938b0b9d9f7f",
    "analysis_sha256": "98bde19fa9e38202909dcee8995ad4fb40ea57b315df4cbf2ac8672d10b7492e",
    "provenance_sha256": "3c60e70e8c9df28dad086c91b5355ac939e9a55a9a550eb7af924cee7dd6d067",
    "manifest_sha256": "d3a2d9f30d36e9227abf327af27e52c418461236e00a41a705f4514bdfbfe562",
    "image_id": "a8a605389d5d869c9b29dd6a613eda8e3b8b6e95",
}
ASSEMBLER_CHAIN = (
    (ASSEMBLER, EXPECTED["assembler_sha256"]),
    (
        EXPERIMENTS / "2026-08-03-a72-scheduler-context/scripts/assemble.py",
        "0605ef23fce46a376b779b77c3085d6ff1ef9695b6c4bff14dba67668b21ee9e",
    ),
    (
        EXPERIMENTS / "2026-08-03-a72-cpu9-parallel-disjoint-load/scripts/assemble.py",
        "9938defe0e4b83d0845135c4a27b534f5d28fafa5eac4bbe345f7badf2405094",
    ),
    (
        EXPERIMENTS / "2026-08-03-a72-cpu9-multiline-integrity/scripts/assemble.py",
        "a7e14b94947aca21038668463b307bbcf59304d55e329e6d7278b4ae2778ea1d",
    ),
    (
        EXPERIMENTS / "2026-08-03-a72-cpu9-bounded-coherency/scripts/assemble.py",
        "2121b03995070321e49293d7e895433dab7a530de095b760d359910e5598252b",
    ),
    (
        EXPERIMENTS / "2026-08-03-a72-cpu9-terminal-attribution/scripts/assemble.py",
        "ed11b681d25ccd0c902226f04ecd3435b3dc85233adcc3274885ec08491f8145",
    ),
    (
        EXPERIMENTS / "2026-08-03-a72-cpu9-retention-window/scripts/assemble.py",
        "f6d36d5eeafe92936fb8c18bddf34eed92f28dd1b602989fb196e83206812885",
    ),
    (
        EXPERIMENTS / "2026-08-03-a72-cpu9-cluster-reuse/scripts/assemble.py",
        "dbd00ee1f2dfbec6eb8c2d48a8e65a1f2ca888a5e6be400e05620cd04a597358",
    ),
    (
        EXPERIMENTS / "2026-08-03-a72-cpu8-late-hold/scripts/assemble.py",
        "231f916492bc8477064f792e6bb07ea0d5362b60aa364af44912fb0b205d5ce4",
    ),
    (
        EXPERIMENTS / "2026-08-02-a72-cpu8-held-online/scripts/assemble.py",
        "c53c40898a25b1b4a0ddeaab310d7e8cb84e08bb4ba9edd8f0e05129fceaeccf",
    ),
    (
        EXPERIMENTS / "2026-08-02-a72-one-way-cpu8-boundary/scripts/assemble.py",
        "2c6e59da67357c946f1ce6e4300fadaf732add0e124f25ba84aefe2a222bbb4b",
    ),
    (
        EXPERIMENTS / "2026-08-02-gemian-a72-bounded-observer-boot/scripts/assemble.py",
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
    require(digest(builder) == EXPECTED["builder_sha256"], "builder changed")
    tooling = builder
    for path, expected in ASSEMBLER_CHAIN:
        require(
            path.is_file() and not path.is_symlink(),
            f"unsafe assembler: {path}",
        )
        content = path.read_bytes()
        require(
            digest(content) == expected,
            f"assembler changed: {path.parent.parent.name}",
        )
        tooling += content
    for key, value in EXPECTED.items():
        if key not in {
            "analysis_sha256",
            "builder_sha256",
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


def records(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"([a-z0-9_]+)=([^\r\n]+)", line)
        require(match is not None, f"malformed record: {path.name}: {line!r}")
        key, value = match.groups()
        require(key not in result, f"duplicate record: {path.name}:{key}")
        result[key] = value
    return result


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
        kernel_size == 8_456_471
        and digest(kernel) == EXPECTED["kernel_field_sha256"],
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
        "experiment": "2026-08-28-a72-target-register-capsule",
        "repository_commit": EXPECTED["repository_commit"],
        "source_commit": EXPECTED["source_commit"],
        "compile_manifest_sha256": EXPECTED["compile_manifest_sha256"],
        "scheduler_patchset_sha256": EXPECTED["scheduler_patchset_sha256"],
        "register_patchset_sha256": EXPECTED["register_patchset_sha256"],
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
        digest((candidate / "analysis.txt").read_bytes())
        == EXPECTED["analysis_sha256"],
        "analysis changed",
    )
    require(
        digest((candidate / "provenance.txt").read_bytes()) == EXPECTED["provenance_sha256"],
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
            path.read_text().replace(
                EXPECTED["register_patchset_sha256"],
                "0" * 64,
            )
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
        ("register-provenance", mutate_provenance, "evidence changed"),
        ("duplicate-provenance", duplicate_provenance, "duplicate record"),
        ("unmanifested-file", add_file, "inventory changed"),
        ("unsafe-manifest", unsafe_manifest, "unsafe manifest record"),
    )
    for name, mutate, expected in mutations:
        with tempfile.TemporaryDirectory(prefix=f"a72-regcap-{name}-") as temporary:
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
    print("validation=a72-target-register-capsule-candidate")
    print("assembler_chain=12-pinned-offline")
    print("candidate_mutations=6-rejected")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
