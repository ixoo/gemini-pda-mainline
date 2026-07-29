#!/usr/bin/env python3
"""Audit Gauss's exact object, ELF, and Image delta from Candidate Fermi."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import gzip
import hashlib
import pathlib
import stat
import struct
import sys

sys.dont_write_bytecode = True
import candidate_gauss as co


class AuditError(ValueError):
    """The Fermi/Gauss binary-control contract was not exact."""


GEMINI_DTB = pathlib.Path("dtbs/mediatek/mt6797-gemini-pda.dtb")
IMAGE_COMPARATOR_OFFSET = 0x6463DC
IMAGE_BUILD_ID_NOTE_OFFSET = 0xA50838
BUILD_ID_SIZE = 20
SEMANTIC_NONEXECUTABLE_DIFF_COUNT = 34
BUILD_ID_NOTE = struct.pack("<III4s", 4, BUILD_ID_SIZE, 3, b"GNU\0")
OLD_COMPARATOR = bytes.fromhex("41 08 00 12 3f 14 00 71")
NEW_COMPARATOR = bytes.fromhex("21 cc 42 39 3f 00 02 6b")
COMPARATOR_DIFF_OFFSETS = tuple(
    IMAGE_COMPARATOR_OFFSET + index
    for index, (old, new) in enumerate(zip(OLD_COMPARATOR, NEW_COMPARATOR))
    if old != new
)
OBJECT_CHANGES = (
    (".text", 0x1534, OLD_COMPARATOR, NEW_COMPARATOR),
    (".rodata", 0x6F, b"\x05", b"\x1f"),
    (
        ".rodata.str1.1",
        0x276,
        b"topology-stable",
        b"exact-d3-stable",
    ),
    (".rodata.str1.1", 0x29A, b"Fermi", b"Gauss"),
    (
        ".rodata.str1.1",
        0x38D,
        b"topology_mask=07 topology_expected=05",
        b"d3_exact_mask=ff d3_exact_expected=1f",
    ),
)
IMAGE_RODATA_REPLACEMENTS = (
    (b"Fermi\0", b"Gauss\0"),
    (b"topology-stable\0", b"exact-d3-stable\0"),
    (
        b"topology_mask=07 topology_expected=05 ",
        b"d3_exact_mask=ff d3_exact_expected=1f ",
    ),
)
SHF_ALLOC = 0x2
SHF_EXECINSTR = 0x4
EM_AARCH64 = 183
ET_REL = 1
ET_DYN = 3


@dataclass(frozen=True)
class ElfSection:
    name: str
    kind: int
    flags: int
    address: int
    offset: int
    size: int
    link: int
    info: int
    alignment: int
    entry_size: int

    def layout(self) -> tuple[object, ...]:
        return (
            self.name,
            self.kind,
            self.flags,
            self.address,
            self.offset,
            self.size,
            self.link,
            self.info,
            self.alignment,
            self.entry_size,
        )


@dataclass(frozen=True)
class ElfFile:
    kind: int
    machine: int
    sections: tuple[ElfSection, ...]
    programs: tuple[tuple[int, ...], ...]

    def section(self, name: str) -> ElfSection:
        matches = tuple(section for section in self.sections if section.name == name)
        if len(matches) != 1:
            raise AuditError(f"ELF section inventory changed: {name}")
        return matches[0]


@dataclass(frozen=True)
class BuildAudit:
    fermi_object_sha256: str
    gauss_object_sha256: str
    fermi_vmlinux_sha256: str
    gauss_vmlinux_sha256: str

    def render(self) -> tuple[str, ...]:
        return (
            "object=i2c-mt65xx.o-whole-file-exact-transform",
            f"fermi_object_sha256={self.fermi_object_sha256}",
            f"gauss_object_sha256={self.gauss_object_sha256}",
            "object_comparator=.text+0x1534",
            "object_comparator_old=410800123f140071",
            "object_comparator_new=21cc42393f00026b",
            "object_expected_d3=.rodata+0x6f:05>1f",
            "object_expected_kind=.rodata.str1.1+0x276:"
            "topology-stable>exact-d3-stable",
            "object_candidate=.rodata.str1.1+0x29a:Fermi>Gauss",
            "object_header=.rodata.str1.1+0x38d:"
            "topology-mask-expected>d3-exact-mask-expected",
            "object_other_sections_and_relocations=byte-exact",
            f"fermi_vmlinux_sha256={self.fermi_vmlinux_sha256}",
            f"gauss_vmlinux_sha256={self.gauss_vmlinux_sha256}",
            "vmlinux_section_layout=byte-exact",
            "vmlinux_program_header_layout=byte-exact",
            "vmlinux_all_alloc_executable_sections=exact-except-comparator",
            "vmlinux_build_id_note=located-and-validated",
            "vmlinux_whole_file=exact-five-source-deltas-plus-build-id",
        )


@dataclass(frozen=True)
class Audit:
    fermi_image_sha256: str
    gauss_image_sha256: str
    image_size: int
    expected_array_offset: int
    build_id_diff_count: int
    executable_diff_offsets: tuple[int, ...]
    executable_diff_pairs: tuple[tuple[int, int], ...]
    semantic_nonexecutable_diff_count: int
    build: BuildAudit | None = None

    def render(self) -> bytes:
        offsets = ",".join(f"{offset:08x}" for offset in self.executable_diff_offsets)
        pairs = ",".join(
            f"{old:02x}>{new:02x}" for old, new in self.executable_diff_pairs
        )
        lines = [
            "validation=gauss-fermi-binary-audit",
            f"fermi_image_sha256={self.fermi_image_sha256}",
            f"gauss_image_sha256={self.gauss_image_sha256}",
            f"image_size={self.image_size}",
            "image_gzip_round_trip=exact",
            "system_map=byte-exact",
            "resolved_config=byte-exact",
            "compiled_gemini_dtb=byte-exact",
            "all_packaged_dtbs=byte-exact",
            "kernel_release=7.1.3-gemini-fermi",
            "debugfs_endpoint=fermi-run-native",
            "ready_marker=GEMINI_FERMI_NATIVE_DIAGNOSTIC",
            f"comparator_offset={IMAGE_COMPARATOR_OFFSET:08x}",
            "comparator_old=410800123f140071",
            "comparator_new=21cc42393f00026b",
            f"executable_diff_count={len(self.executable_diff_offsets)}",
            f"executable_diff_offsets={offsets}",
            f"executable_diff_pairs={pairs}",
            "executable_diff_scope=exact-post-trigger-comparator-instruction-pair",
            f"d3_expected_offset={self.expected_array_offset:08x}",
            "d3_expected_array=05-to-1f",
            f"semantic_nonexecutable_diff_count="
            f"{self.semantic_nonexecutable_diff_count}",
            "semantic_nonexecutable_delta="
            "expected-array-plus-three-fixed-length-report-substitutions",
            f"gnu_build_id_note_offset={IMAGE_BUILD_ID_NOTE_OFFSET:08x}",
            f"gnu_build_id_digest_offset="
            f"{IMAGE_BUILD_ID_NOTE_OFFSET + len(BUILD_ID_NOTE):08x}",
            f"gnu_build_id_digest_size={BUILD_ID_SIZE}",
            f"gnu_build_id_diff_count={self.build_id_diff_count}",
            "gnu_build_id_delta=link-generated-digest-only",
            "candidate_report=Fermi-to-Gauss",
            "expected_kind=topology-stable-to-exact-d3-stable",
            "header_report=topology-mask-expected-to-exact-d3-mask-expected",
        ]
        if self.build is not None:
            lines.extend(self.build.render())
        return ("\n".join(lines) + "\n").encode("ascii")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise AuditError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def parse_symbols(data: bytes) -> dict[str, int]:
    try:
        lines = data.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise AuditError("System.map is not ASCII") from exc
    required = {
        "_text",
        "mtk_i2c_fermi_write",
        "mtk_i2c_quasar_expected",
    }
    found: dict[str, int] = {}
    for line in lines:
        parts = line.split()
        if len(parts) != 3:
            raise AuditError("System.map line grammar changed")
        name = parts[2]
        if name not in required:
            continue
        try:
            address = int(parts[0], 16)
        except ValueError as exc:
            raise AuditError("System.map address is malformed") from exc
        if name in found:
            raise AuditError(f"required System.map symbol is duplicated: {name}")
        found[name] = address
    if set(found) != required:
        raise AuditError("Fermi System.map lacks a Gauss audit boundary")
    return found


def parse_elf(data: bytes, label: str) -> ElfFile:
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        raise AuditError(f"{label} is not ELF64 little-endian")
    header = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    (
        elf_kind,
        machine,
        version,
        _entry,
        program_offset,
        section_offset,
        _flags,
        header_size,
        program_entry_size,
        program_count,
        section_entry_size,
        section_count,
        string_index,
    ) = header
    if (
        version != 1
        or machine != EM_AARCH64
        or header_size != 64
        or section_entry_size != 64
        or section_count == 0
        or section_count == 0xFFFF
        or string_index >= section_count
    ):
        raise AuditError(f"{label} ELF header contract changed")
    if program_count and program_entry_size != 56:
        raise AuditError(f"{label} ELF program-header contract changed")
    if section_offset + section_count * section_entry_size > len(data):
        raise AuditError(f"{label} ELF section table is truncated")
    if program_offset + program_count * program_entry_size > len(data):
        raise AuditError(f"{label} ELF program table is truncated")

    raw_sections = tuple(
        struct.unpack_from("<IIQQQQIIQQ", data, section_offset + index * 64)
        for index in range(section_count)
    )
    strings_header = raw_sections[string_index]
    strings_offset, strings_size = strings_header[4], strings_header[5]
    if strings_offset + strings_size > len(data):
        raise AuditError(f"{label} ELF section-name table is truncated")
    strings = data[strings_offset : strings_offset + strings_size]

    def name_at(offset: int) -> str:
        if offset >= len(strings):
            raise AuditError(f"{label} ELF section name is out of bounds")
        end = strings.find(b"\0", offset)
        if end < 0:
            raise AuditError(f"{label} ELF section name is unterminated")
        try:
            return strings[offset:end].decode("ascii")
        except UnicodeError as exc:
            raise AuditError(f"{label} ELF section name is not ASCII") from exc

    sections = []
    for raw in raw_sections:
        name_offset, kind, flags, address, offset, size, link, info, align, entsize = raw
        if kind != 8 and offset + size > len(data):
            raise AuditError(f"{label} ELF section is truncated")
        sections.append(
            ElfSection(
                name_at(name_offset),
                kind,
                flags,
                address,
                offset,
                size,
                link,
                info,
                align,
                entsize,
            )
        )
    programs = tuple(
        struct.unpack_from("<IIQQQQQQ", data, program_offset + index * 56)
        for index in range(program_count)
    )
    return ElfFile(elf_kind, machine, tuple(sections), programs)


def section_bytes(data: bytes, section: ElfSection, label: str) -> bytes:
    if section.kind == 8:
        raise AuditError(f"{label} unexpectedly names a NOBITS section")
    return data[section.offset : section.offset + section.size]


def replace_at(
    data: bytearray,
    offset: int,
    old: bytes,
    new: bytes,
    label: str,
) -> None:
    if len(old) != len(new):
        raise AuditError(f"{label} replacement changed length")
    if data[offset : offset + len(old)] != old:
        raise AuditError(f"{label} Fermi bytes changed")
    data[offset : offset + len(old)] = new


def unique_replace(data: bytearray, old: bytes, new: bytes, label: str) -> None:
    if len(old) != len(new):
        raise AuditError(f"{label} substitution changed size")
    immutable = bytes(data)
    if immutable.count(old) != 1 or new in immutable:
        raise AuditError(f"Fermi {label} token inventory changed")
    replace_at(data, immutable.index(old), old, new, label)


def package_dtbs(package: pathlib.Path) -> dict[str, bytes]:
    root = package / "dtbs"
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise AuditError("packaged DT directory is missing or unsafe")
    result: dict[str, bytes] = {}
    for path in root.rglob("*.dtb"):
        relative = path.relative_to(root).as_posix()
        result[relative] = regular(path, f"packaged DT {relative}")
    if not result:
        raise AuditError("packaged DT inventory is empty")
    return result


def audit_build(
    fermi_object_path: pathlib.Path,
    gauss_object_path: pathlib.Path,
    fermi_vmlinux_path: pathlib.Path,
    gauss_vmlinux_path: pathlib.Path,
    fermi_image: bytes,
    gauss_image: bytes,
    symbols: dict[str, int],
) -> BuildAudit:
    fermi_object = regular(fermi_object_path, "exact Fermi i2c-mt65xx.o")
    gauss_object = regular(gauss_object_path, "Gauss i2c-mt65xx.o")
    if (
        len(fermi_object) != co.I2C_OBJECT_SIZE
        or len(gauss_object) != co.I2C_OBJECT_SIZE
        or digest(fermi_object) != co.FERMI_I2C_OBJECT_SHA256
        or digest(gauss_object) != co.GAUSS_I2C_OBJECT_SHA256
    ):
        raise AuditError("Fermi/Gauss i2c-mt65xx.o pinned identity changed")
    fermi_object_elf = parse_elf(fermi_object, "Fermi i2c-mt65xx.o")
    gauss_object_elf = parse_elf(gauss_object, "Gauss i2c-mt65xx.o")
    if fermi_object_elf.kind != ET_REL or gauss_object_elf.kind != ET_REL:
        raise AuditError("i2c-mt65xx object ELF type changed")
    if tuple(s.layout() for s in fermi_object_elf.sections) != tuple(
        s.layout() for s in gauss_object_elf.sections
    ):
        raise AuditError("i2c-mt65xx.o section layout changed")
    if fermi_object_elf.programs != gauss_object_elf.programs:
        raise AuditError("i2c-mt65xx.o unexpectedly has different program headers")
    expected_object = bytearray(fermi_object)
    for section_name, relative, old, new in OBJECT_CHANGES:
        section = fermi_object_elf.section(section_name)
        if relative + len(old) > section.size:
            raise AuditError(f"object delta escaped {section_name}")
        replace_at(
            expected_object,
            section.offset + relative,
            old,
            new,
            f"object {section_name}+0x{relative:x}",
        )
    if bytes(expected_object) != gauss_object:
        raise AuditError(
            "Gauss i2c-mt65xx.o differs outside the five exact source deltas"
        )

    fermi_vmlinux = regular(fermi_vmlinux_path, "exact Fermi vmlinux")
    gauss_vmlinux = regular(gauss_vmlinux_path, "Gauss vmlinux")
    if (
        len(fermi_vmlinux) != co.VMLINUX_SIZE
        or len(gauss_vmlinux) != co.VMLINUX_SIZE
        or digest(fermi_vmlinux) != co.FERMI_VMLINUX_SHA256
        or digest(gauss_vmlinux) != co.GAUSS_VMLINUX_SHA256
    ):
        raise AuditError("Fermi/Gauss vmlinux pinned identity changed")
    fermi_elf = parse_elf(fermi_vmlinux, "Fermi vmlinux")
    gauss_elf = parse_elf(gauss_vmlinux, "Gauss vmlinux")
    if fermi_elf.kind != ET_DYN or gauss_elf.kind != ET_DYN:
        raise AuditError("vmlinux ELF type changed")
    if tuple(s.layout() for s in fermi_elf.sections) != tuple(
        s.layout() for s in gauss_elf.sections
    ):
        raise AuditError("Gauss vmlinux section layout differs from Fermi")
    if fermi_elf.programs != gauss_elf.programs:
        raise AuditError("Gauss vmlinux program-header layout differs from Fermi")

    comparator_address = symbols["_text"] + IMAGE_COMPARATOR_OFFSET
    comparator_seen = False
    for fermi_section, gauss_section in zip(
        fermi_elf.sections, gauss_elf.sections, strict=True
    ):
        if fermi_section.flags & (SHF_ALLOC | SHF_EXECINSTR) != (
            SHF_ALLOC | SHF_EXECINSTR
        ):
            continue
        fermi_bytes = section_bytes(
            fermi_vmlinux, fermi_section, f"Fermi {fermi_section.name}"
        )
        gauss_bytes = section_bytes(
            gauss_vmlinux, gauss_section, f"Gauss {gauss_section.name}"
        )
        expected = bytearray(fermi_bytes)
        if (
            fermi_section.address
            <= comparator_address
            < fermi_section.address + fermi_section.size
        ):
            relative = comparator_address - fermi_section.address
            replace_at(
                expected,
                relative,
                OLD_COMPARATOR,
                NEW_COMPARATOR,
                "vmlinux exact comparator",
            )
            comparator_seen = True
        if bytes(expected) != gauss_bytes:
            raise AuditError(
                f"Gauss executable ELF section changed: {fermi_section.name}"
            )
    if not comparator_seen:
        raise AuditError("vmlinux executable sections do not contain comparator")

    fermi_notes = section_bytes(
        fermi_vmlinux,
        fermi_elf.section(".notes"),
        "Fermi ELF notes",
    )
    gauss_notes = section_bytes(
        gauss_vmlinux,
        gauss_elf.section(".notes"),
        "Gauss ELF notes",
    )
    if (
        len(fermi_notes) != 0x54
        or len(gauss_notes) != len(fermi_notes)
        or fermi_notes[: len(BUILD_ID_NOTE)] != BUILD_ID_NOTE
        or gauss_notes[: len(BUILD_ID_NOTE)] != BUILD_ID_NOTE
        or fermi_notes[len(BUILD_ID_NOTE) : len(BUILD_ID_NOTE) + BUILD_ID_SIZE]
        != fermi_image[
            IMAGE_BUILD_ID_NOTE_OFFSET
            + len(BUILD_ID_NOTE) : IMAGE_BUILD_ID_NOTE_OFFSET
            + len(BUILD_ID_NOTE)
            + BUILD_ID_SIZE
        ]
        or gauss_notes[len(BUILD_ID_NOTE) : len(BUILD_ID_NOTE) + BUILD_ID_SIZE]
        != gauss_image[
            IMAGE_BUILD_ID_NOTE_OFFSET
            + len(BUILD_ID_NOTE) : IMAGE_BUILD_ID_NOTE_OFFSET
            + len(BUILD_ID_NOTE)
            + BUILD_ID_SIZE
        ]
        or fermi_notes[len(BUILD_ID_NOTE) + BUILD_ID_SIZE :]
        != gauss_notes[len(BUILD_ID_NOTE) + BUILD_ID_SIZE :]
    ):
        raise AuditError("vmlinux/Image GNU build-ID note mapping changed")

    expected_vmlinux = bytearray(fermi_vmlinux)

    def linked_file_offset(image_offset: int, size: int) -> int:
        address = symbols["_text"] + image_offset
        matches = tuple(
            section
            for section in fermi_elf.sections
            if section.kind != 8
            and section.flags & SHF_ALLOC
            and section.address <= address
            and address + size <= section.address + section.size
        )
        if len(matches) != 1:
            raise AuditError("Image/vmlinux allocated-section mapping changed")
        return matches[0].offset + address - matches[0].address

    linked_changes = [
        (IMAGE_COMPARATOR_OFFSET, OLD_COMPARATOR, NEW_COMPARATOR),
        (
            symbols["mtk_i2c_quasar_expected"] - symbols["_text"] + 3,
            b"\x05",
            b"\x1f",
        ),
    ]
    for old, new in IMAGE_RODATA_REPLACEMENTS:
        if fermi_image.count(old) != 1:
            raise AuditError("Fermi linked report token inventory changed")
        linked_changes.append((fermi_image.index(old), old, new))
    for image_offset, old, new in linked_changes:
        replace_at(
            expected_vmlinux,
            linked_file_offset(image_offset, len(old)),
            old,
            new,
            f"whole-vmlinux image mapping 0x{image_offset:x}",
        )
    notes_section = fermi_elf.section(".notes")
    replace_at(
        expected_vmlinux,
        notes_section.offset + len(BUILD_ID_NOTE),
        fermi_notes[len(BUILD_ID_NOTE) : len(BUILD_ID_NOTE) + BUILD_ID_SIZE],
        gauss_notes[len(BUILD_ID_NOTE) : len(BUILD_ID_NOTE) + BUILD_ID_SIZE],
        "whole-vmlinux GNU build-ID digest",
    )
    if bytes(expected_vmlinux) != gauss_vmlinux:
        raise AuditError(
            "Gauss vmlinux differs outside exact source deltas and build-ID"
        )

    return BuildAudit(
        digest(fermi_object),
        digest(gauss_object),
        digest(fermi_vmlinux),
        digest(gauss_vmlinux),
    )


def audit(
    fermi_package: pathlib.Path,
    gauss_package: pathlib.Path,
    *,
    fermi_object: pathlib.Path | None = None,
    gauss_object: pathlib.Path | None = None,
    fermi_vmlinux: pathlib.Path | None = None,
    gauss_vmlinux: pathlib.Path | None = None,
) -> Audit:
    co.require_input_pins()
    if fermi_package.name != co.FERMI_PACKAGE_DIRECTORY:
        raise AuditError("Fermi package directory identity changed")

    fermi_image = regular(fermi_package / "Image", "exact Fermi Image")
    gauss_image = regular(gauss_package / "Image", "Gauss Image")
    fermi_gzip = regular(fermi_package / "Image.gz", "exact Fermi Image.gz")
    gauss_gzip = regular(gauss_package / "Image.gz", "Gauss Image.gz")
    fermi_map = regular(fermi_package / "System.map", "exact Fermi System.map")
    gauss_map = regular(gauss_package / "System.map", "Gauss System.map")
    fermi_config = regular(fermi_package / "kernel.config", "exact Fermi config")
    gauss_config = regular(gauss_package / "kernel.config", "Gauss config")
    fermi_dtb = regular(fermi_package / GEMINI_DTB, "exact Fermi Gemini DT")
    gauss_dtb = regular(gauss_package / GEMINI_DTB, "Gauss Gemini DT")

    exact_hashes = {
        "Fermi Image": (digest(fermi_image), co.FERMI_IMAGE_SHA256),
        "Fermi Image.gz": (digest(fermi_gzip), co.FERMI_IMAGE_GZ_SHA256),
        "Gauss Image": (digest(gauss_image), co.GAUSS_IMAGE_SHA256),
        "Gauss Image.gz": (digest(gauss_gzip), co.GAUSS_IMAGE_GZ_SHA256),
        "Fermi System.map": (digest(fermi_map), co.FERMI_SYSTEM_MAP_SHA256),
        "Fermi config": (digest(fermi_config), co.FERMI_CONFIG_SHA256),
        "Fermi Gemini DT": (digest(fermi_dtb), co.FERMI_COMPILED_DTB_SHA256),
    }
    for label, (actual, wanted) in exact_hashes.items():
        if actual != wanted:
            raise AuditError(f"{label} source identity changed")
    try:
        if gzip.decompress(fermi_gzip) != fermi_image:
            raise AuditError("exact Fermi Image.gz does not decompress to Image")
        if gzip.decompress(gauss_gzip) != gauss_image:
            raise AuditError("Gauss Image.gz does not decompress to Image")
    except (EOFError, gzip.BadGzipFile) as exc:
        raise AuditError("kernel Image gzip stream is malformed") from exc
    if fermi_map != gauss_map:
        raise AuditError("Gauss System.map differs from Fermi")
    if fermi_config != gauss_config:
        raise AuditError("Gauss resolved config differs from Fermi")
    if fermi_dtb != gauss_dtb:
        raise AuditError("Gauss compiled Gemini DT differs from Fermi")
    if package_dtbs(fermi_package) != package_dtbs(gauss_package):
        raise AuditError("Gauss packaged DT inventory differs from Fermi")
    if len(fermi_image) != len(gauss_image):
        raise AuditError("Gauss Image size differs from Fermi")

    symbols = parse_symbols(fermi_map)
    if symbols["mtk_i2c_fermi_write"] - symbols["_text"] + 0x5A8 != (
        IMAGE_COMPARATOR_OFFSET
    ):
        raise AuditError("post-trigger comparator offset changed")
    expected_offset = symbols["mtk_i2c_quasar_expected"] - symbols["_text"] + 3

    expected = bytearray(fermi_image)
    replace_at(
        expected,
        IMAGE_COMPARATOR_OFFSET,
        OLD_COMPARATOR,
        NEW_COMPARATOR,
        "linked post-trigger comparator",
    )
    replace_at(expected, expected_offset, b"\x05", b"\x1f", "linked D3 expected")
    for index, (old, new) in enumerate(IMAGE_RODATA_REPLACEMENTS):
        unique_replace(expected, old, new, f"linked report token {index}")

    note_end = IMAGE_BUILD_ID_NOTE_OFFSET + len(BUILD_ID_NOTE)
    digest_end = note_end + BUILD_ID_SIZE
    if (
        fermi_image[IMAGE_BUILD_ID_NOTE_OFFSET:note_end] != BUILD_ID_NOTE
        or gauss_image[IMAGE_BUILD_ID_NOTE_OFFSET:note_end] != BUILD_ID_NOTE
        or digest_end > len(fermi_image)
    ):
        raise AuditError("GNU build-ID note location or header changed")
    fermi_build_id = fermi_image[note_end:digest_end]
    gauss_build_id = gauss_image[note_end:digest_end]
    if fermi_build_id == gauss_build_id:
        raise AuditError("Gauss GNU build-ID digest did not change")
    expected[note_end:digest_end] = gauss_build_id
    if bytes(expected) != gauss_image:
        raise AuditError(
            "Gauss Image differs outside comparator, reports, and GNU build-ID"
        )

    all_differences = tuple(
        index
        for index, (old, new) in enumerate(
            zip(fermi_image, gauss_image, strict=True)
        )
        if old != new
    )
    executable_differences = tuple(
        index
        for index in all_differences
        if IMAGE_COMPARATOR_OFFSET
        <= index
        < IMAGE_COMPARATOR_OFFSET + len(OLD_COMPARATOR)
    )
    if executable_differences != COMPARATOR_DIFF_OFFSETS:
        raise AuditError("Gauss executable delta is not the exact seven bytes")
    pairs = tuple(
        (fermi_image[offset], gauss_image[offset])
        for offset in executable_differences
    )
    build_id_differences = sum(
        old != new for old, new in zip(fermi_build_id, gauss_build_id, strict=True)
    )
    semantic_nonexec = (
        len(all_differences) - len(executable_differences) - build_id_differences
    )
    if build_id_differences != BUILD_ID_SIZE:
        raise AuditError("Gauss GNU build-ID digest delta is not exactly 20 bytes")
    if semantic_nonexec != SEMANTIC_NONEXECUTABLE_DIFF_COUNT:
        raise AuditError("Gauss semantic non-executable delta is not 34 bytes")

    build_paths = (fermi_object, gauss_object, fermi_vmlinux, gauss_vmlinux)
    if any(path is None for path in build_paths) and any(
        path is not None for path in build_paths
    ):
        raise AuditError("object/vmlinux audit inputs must be supplied together")
    build = None
    if all(path is not None for path in build_paths):
        build = audit_build(
            fermi_object,  # type: ignore[arg-type]
            gauss_object,  # type: ignore[arg-type]
            fermi_vmlinux,  # type: ignore[arg-type]
            gauss_vmlinux,  # type: ignore[arg-type]
            fermi_image,
            gauss_image,
            symbols,
        )
    return Audit(
        digest(fermi_image),
        digest(gauss_image),
        len(gauss_image),
        expected_offset,
        build_id_differences,
        executable_differences,
        pairs,
        semantic_nonexec,
        build,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fermi-package", required=True, type=pathlib.Path)
    parser.add_argument("--gauss-package", required=True, type=pathlib.Path)
    parser.add_argument("--fermi-object", type=pathlib.Path)
    parser.add_argument("--gauss-object", type=pathlib.Path)
    parser.add_argument("--fermi-vmlinux", type=pathlib.Path)
    parser.add_argument("--gauss-vmlinux", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = audit(
            args.fermi_package.resolve(strict=True),
            args.gauss_package.resolve(strict=True),
            fermi_object=(
                args.fermi_object.resolve(strict=True)
                if args.fermi_object is not None
                else None
            ),
            gauss_object=(
                args.gauss_object.resolve(strict=True)
                if args.gauss_object is not None
                else None
            ),
            fermi_vmlinux=(
                args.fermi_vmlinux.resolve(strict=True)
                if args.fermi_vmlinux is not None
                else None
            ),
            gauss_vmlinux=(
                args.gauss_vmlinux.resolve(strict=True)
                if args.gauss_vmlinux is not None
                else None
            ),
        )
    except (AuditError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(result.render().decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
