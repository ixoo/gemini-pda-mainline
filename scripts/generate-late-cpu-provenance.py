#!/usr/bin/env python3
"""Inject the package-owned ABI-7 provenance record into the Gemini DTB.

The kernel-side A41 parser treats this record as a static Open Firmware
authority.  The package builder is the only component allowed to populate it:
all running identities are derived independently from the exact linked image,
embedded IKCONFIG, and forced command line.  The output is still compile and
packaging evidence; it does not make a kernel a boot candidate.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn


DOMAIN = b"gemini-a41-runtime-binding-v1\0"
PROFILE_ID = "mt6797-a53-a72-a41-v7"
NODE_NAME = "gemini-late-cpu-provenance"
COMPATIBLE = "planet,gemini-a72-runtime-binding-v1"
TARGET_CPUS = (8, 9)
TARGET_MPIDRS = (0x200, 0x201)
DIGEST_NAMES = (
    "expected-ikconfig-identity",
    "expected-gnu-build-id-identity",
    "expected-cmdline-identity",
    "upstream-source-sha256",
    "patch-series-sha256",
    "config-inputs-sha256",
    "resolved-config-sha256",
    "package-image-sha256",
    "build-provenance-sha256",
)


def fail(message: str) -> NoReturn:
    raise SystemExit(f"error: {message}")


def checked_digest(value: str, label: str) -> bytes:
    if len(value) != hashlib.sha256().digest_size * 2:
        fail(f"{label} must be a 64-character lowercase SHA-256")
    try:
        result = bytes.fromhex(value)
    except ValueError:
        fail(f"{label} is not hexadecimal")
    if result.hex() != value:
        fail(f"{label} must use lowercase hexadecimal")
    if not any(result):
        fail(f"{label} must be nonzero")
    return result


def sha256_hex(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def domain_hash(tag: bytes, length_format: str, value: bytes) -> bytes:
    return hashlib.sha256(
        DOMAIN + tag + struct.pack(length_format, len(value)) + value
    ).digest()


def align4(value: int) -> int:
    return (value + 3) & ~3


@dataclass(frozen=True)
class Section:
    name: str
    kind: int
    address: int
    offset: int
    size: int
    link: int
    entry_size: int


@dataclass(frozen=True)
class Symbol:
    name: str
    section: int
    value: int


class Elf64:
    """Small, strict ELF64 reader for the four linker symbols A41 needs."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.data = path.read_bytes()
        if len(self.data) < 64 or self.data[:4] != b"\x7fELF":
            fail(f"{path} is not an ELF file")
        if self.data[4] != 2 or self.data[5] != 1:
            fail(f"{path} must be little-endian ELF64")

        header = struct.unpack_from("<16sHHIQQQIHHHHHH", self.data, 0)
        (_, _, _, _, _, _, section_offset, _, _, _, _, section_size,
         section_count, string_section) = header
        if section_size < 64 or section_count == 0 or string_section >= section_count:
            fail(f"{path} has invalid ELF section metadata")
        section_end = section_offset + section_size * section_count
        if section_end > len(self.data):
            fail(f"{path} has truncated ELF section headers")

        raw_sections = []
        for index in range(section_count):
            raw_sections.append(struct.unpack_from(
                "<IIQQQQIIQQ", self.data,
                section_offset + index * section_size,
            ))
        shstr = raw_sections[string_section]
        shstr_bytes = self._section_bytes(shstr[4], shstr[5])
        self.sections: list[Section] = []
        for name_offset, kind, _, address, offset, size, link, _, _, entry_size in raw_sections:
            name = self._cstring(shstr_bytes, name_offset)
            self.sections.append(Section(name, kind, address, offset, size,
                                         link, entry_size))
        self.symbols = self._read_symbols()

    def _section_bytes(self, offset: int, size: int) -> bytes:
        if offset + size > len(self.data):
            fail(f"{self.path} has a section outside the file")
        return self.data[offset:offset + size]

    @staticmethod
    def _cstring(value: bytes, offset: int) -> str:
        if offset >= len(value):
            fail("ELF string-table offset is out of range")
        end = value.find(b"\0", offset)
        if end < 0:
            fail("ELF string-table entry is unterminated")
        return value[offset:end].decode("ascii")

    def _read_symbols(self) -> dict[str, Symbol]:
        found: dict[str, Symbol] = {}
        for section in self.sections:
            # SHT_SYMTAB and SHT_DYNSYM.
            if section.kind not in (2, 11) or section.link >= len(self.sections):
                continue
            if section.entry_size < 24 or section.size % section.entry_size:
                fail(f"{self.path} has malformed symbol table {section.name}")
            strings = self._section_bytes(self.sections[section.link].offset,
                                          self.sections[section.link].size)
            for offset in range(0, section.size, section.entry_size):
                (name_offset, _, _, section_index, value,
                 _) = struct.unpack_from(
                     "<IBBHQQ", self.data, section.offset + offset
                 )
                if not name_offset:
                    continue
                name = self._cstring(strings, name_offset)
                if name not in {
                    "kernel_config_data", "kernel_config_data_end",
                    "__start_notes", "__stop_notes",
                }:
                    continue
                candidate = Symbol(name, section_index, value)
                previous = found.get(name)
                if previous and previous != candidate:
                    fail(f"{self.path} contains ambiguous symbol {name}")
                found[name] = candidate
        return found

    def _symbol(self, name: str) -> Symbol:
        symbol = self.symbols.get(name)
        if symbol is None:
            fail(f"{self.path} is missing linker symbol {name}")
        return symbol

    def range_bytes(self, start_name: str, end_name: str) -> bytes:
        start = self._symbol(start_name)
        end = self._symbol(end_name)
        if end.value <= start.value:
            fail(f"{start_name}..{end_name} is empty or reversed")

        candidates = []
        for index, section in enumerate(self.sections):
            # SHT_NOBITS has no file representation.
            if section.kind == 8 or section.size == 0:
                continue
            if (section.address <= start.value <= end.value <=
                    section.address + section.size):
                candidates.append((index, section))
        if len(candidates) != 1:
            fail(f"could not bind {start_name}..{end_name} to one ELF section")
        index, section = candidates[0]
        if start.section not in (0, 0xFFF1, index) or end.section not in (0, 0xFFF1, index):
            fail(f"{start_name}..{end_name} crosses ELF sections")
        start_offset = section.offset + start.value - section.address
        end_offset = section.offset + end.value - section.address
        if start_offset < section.offset or end_offset > section.offset + section.size:
            fail(f"{start_name}..{end_name} exceeds its ELF section")
        return self.data[start_offset:end_offset]


def build_id_from_notes(notes: bytes) -> bytes:
    offset = 0
    build_ids = []
    while offset < len(notes):
        if len(notes) - offset < 12:
            fail("ELF notes contain a truncated header")
        namesz, descsz, note_type = struct.unpack_from("<III", notes, offset)
        name_start = offset + 12
        name_end = name_start + align4(namesz)
        desc_start = name_end
        desc_end = desc_start + align4(descsz)
        if desc_end > len(notes) or name_end < name_start or desc_end < desc_start:
            fail("ELF notes contain truncated padding")
        name = notes[name_start:name_start + namesz]
        desc = notes[desc_start:desc_start + descsz]
        if note_type == 3 and name == b"GNU\0":
            build_ids.append(desc)
        offset = desc_end
    if offset != len(notes) or len(build_ids) != 1:
        fail("ELF notes do not contain exactly one GNU build ID")
    build_id = build_ids[0]
    if len(build_id) != 20 or not any(build_id):
        fail("GNU build ID is not a nonzero 20-byte value")
    return build_id


def forced_cmdline(config: Path) -> bytes:
    values: dict[str, str] = {}
    for raw_line in config.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith("CONFIG_CMDLINE_FORCE="):
            values["force"] = raw_line.split("=", 1)[1]
        elif raw_line.startswith("CONFIG_CMDLINE="):
            values["cmdline"] = raw_line.split("=", 1)[1]
    if values.get("force") != "y" or "cmdline" not in values:
        fail("resolved config does not select forced CONFIG_CMDLINE")
    literal = values["cmdline"]
    try:
        decoded = ast.literal_eval(literal)
    except (SyntaxError, ValueError):
        fail("CONFIG_CMDLINE is not a valid quoted Kconfig string")
    if not isinstance(decoded, str) or not decoded or "\0" in decoded:
        fail("CONFIG_CMDLINE is empty or contains NUL")
    try:
        return decoded.encode("ascii")
    except UnicodeEncodeError:
        fail("CONFIG_CMDLINE contains non-ASCII bytes")


def dts_bytes(value: bytes) -> str:
    return "[" + " ".join(f"{item:02x}" for item in value) + "]"


def run(command: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(command, check=True, stdout=subprocess.PIPE if capture else None,
                              stderr=subprocess.PIPE if capture else None)
    except FileNotFoundError:
        fail(f"required DT/ELF tool is unavailable: {command[0]}")
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode("utf-8", "replace").strip() if error.stderr else ""
        fail(f"command failed ({error.returncode}): {' '.join(command)}{': ' + detail if detail else ''}")


def inject_dtb(dtb: Path, output: Path, record: dict[str, object]) -> None:
    listing = run(["fdtget", "-l", str(dtb), "/chosen"], capture=True)
    children = listing.stdout.decode("utf-8", "replace").splitlines()
    if NODE_NAME in children:
        fail(f"{dtb} already contains /chosen/{NODE_NAME}")
    if output.exists() and output != dtb:
        fail(f"refusing to overwrite existing DTB output {output}")

    digest = record["digests"]
    if not isinstance(digest, dict):
        fail("internal record digest shape is invalid")
    record_identity = record.get("record_identity")
    if not isinstance(record_identity, str):
        fail("internal record identity shape is invalid")
    lines = [
        "/dts-v1/;",
        "/plugin/;",
        "",
        "/ {",
        "\tfragment@0 {",
        "\t\ttarget-path = \"/chosen\";",
        "\t\t__overlay__ {",
        f"\t\t\t{NODE_NAME} {{",
        f"\t\t\t\tcompatible = \"{COMPATIBLE}\";",
        "\t\t\t\tschema-version = <1>;",
        f"\t\t\t\tprofile-id = \"{PROFILE_ID}\";",
        "\t\t\t\ttarget-cpus = <8 9>;",
        "\t\t\t\ttarget-mpidrs = /bits/ 64 <0x200 0x201>;",
    ]
    for name in DIGEST_NAMES:
        value = digest.get(name)
        if not isinstance(value, str):
            fail(f"missing digest {name}")
        lines.append(f"\t\t\t\t{name} = {dts_bytes(bytes.fromhex(value))};")
    lines.extend([
        f"\t\t\t\trecord-identity = {dts_bytes(bytes.fromhex(record_identity))};",
        "\t\t\t};",
        "\t\t};",
        "\t};",
        "};",
        "",
    ])
    with tempfile.TemporaryDirectory(prefix=".a41-provenance.", dir=str(dtb.parent)) as temporary:
        root = Path(temporary)
        source = root / "provenance-overlay.dts"
        overlay = root / "provenance-overlay.dtb"
        result = root / "result.dtb"
        source.write_text("\n".join(lines), encoding="ascii")
        run(["dtc", "-q", "-@", "-I", "dts", "-O", "dtb",
             "-o", str(overlay), str(source)])
        run(["fdtoverlay", "-i", str(dtb), "-o", str(result), str(overlay)])
        if not result.is_file() or result.stat().st_size == 0:
            fail("fdtoverlay produced no DTB")
        os.replace(result, output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vmlinux", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--dtb", type=Path, required=True)
    parser.add_argument("--record-json", type=Path, required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--source-sha256", required=True)
    parser.add_argument("--patchset-sha256", required=True)
    parser.add_argument("--config-inputs-sha256", required=True)
    parser.add_argument("--resolved-config-sha256", required=True)
    parser.add_argument("--build-provenance", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    for path in (args.vmlinux, args.config, args.image, args.dtb, args.build_provenance):
        if not path.is_file() or path.is_symlink():
            fail(f"required input is missing or not regular: {path}")
    if args.profile_id != PROFILE_ID:
        fail(f"unsupported A41 profile ID: {args.profile_id}")

    source_digest = checked_digest(args.source_sha256, "source SHA-256")
    patchset_digest = checked_digest(args.patchset_sha256, "patchset SHA-256")
    config_inputs_digest = checked_digest(args.config_inputs_sha256, "config-inputs SHA-256")
    resolved_config_digest = checked_digest(args.resolved_config_sha256, "resolved-config SHA-256")

    elf = Elf64(args.vmlinux)
    ikconfig = elf.range_bytes("kernel_config_data", "kernel_config_data_end")
    notes = elf.range_bytes("__start_notes", "__stop_notes")
    build_id = build_id_from_notes(notes)
    cmdline = forced_cmdline(args.config)

    expected_ikconfig = domain_hash(b"ikconfig\0", ">Q", ikconfig)
    expected_build_id = domain_hash(b"gnu-build-id\0", ">I", build_id)
    expected_cmdline = domain_hash(b"cmdline\0", ">Q", cmdline)
    package_image_digest = bytes.fromhex(sha256_hex(args.image))
    build_provenance_digest = bytes.fromhex(sha256_hex(args.build_provenance))
    digests = (
        expected_ikconfig, expected_build_id, expected_cmdline,
        source_digest, patchset_digest, config_inputs_digest,
        resolved_config_digest, package_image_digest, build_provenance_digest,
    )
    record_payload = (
        DOMAIN + b"record\0" + struct.pack(">I", 1) +
        struct.pack(">H", len(PROFILE_ID.encode("ascii"))) + PROFILE_ID.encode("ascii") +
        struct.pack(">I", len(TARGET_CPUS)) +
        b"".join(struct.pack(">I", cpu) for cpu in TARGET_CPUS) +
        struct.pack(">I", len(TARGET_MPIDRS)) +
        b"".join(struct.pack(">Q", mpidr) for mpidr in TARGET_MPIDRS) +
        b"".join(digests)
    )
    record_identity = hashlib.sha256(record_payload).digest()
    record = {
        "schema": 1,
        "compatible": COMPATIBLE,
        "profile_id": PROFILE_ID,
        "target_cpus": list(TARGET_CPUS),
        "target_mpidrs": list(TARGET_MPIDRS),
        "digests": {
            name: value.hex() for name, value in zip(DIGEST_NAMES, digests)
        },
        "record_identity": record_identity.hex(),
        "build_id": build_id.hex(),
        "ikconfig_size": len(ikconfig),
        "cmdline_size": len(cmdline),
    }
    args.record_json.parent.mkdir(parents=True, exist_ok=True)
    args.record_json.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n",
                                encoding="ascii")
    inject_dtb(args.dtb, args.dtb, record)
    print(f"a41_record_identity={record_identity.hex()}")
    print(f"a41_expected_ikconfig_identity={expected_ikconfig.hex()}")
    print(f"a41_expected_build_id_identity={expected_build_id.hex()}")
    print(f"a41_expected_cmdline_identity={expected_cmdline.hex()}")
    print("a41_provenance_node=/chosen/gemini-late-cpu-provenance")
    print("a41_provenance_status=emitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
