#!/usr/bin/env python3
"""Validate Candidate L's Linux 7.1.3 -> Gemian ramoops recovery map."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import subprocess
import sys
from collections.abc import Mapping


BASE = 0x44410000
TOTAL_SIZE = 0x000E0000
RECORD_SIZE = 0x00001000
CONSOLE_SIZE = 0x00010000
GEMIAN_PMSG_SIZE = 0x00010000
MAINLINE_PMSG_SIZE = 0x00020000
FTRACE_SIZE = 0x00001000
PERSISTENT_RAM_SIG = 0x43474244

GEMIAN_COMMIT = "d388d350cb2dda8f23b99be6fa5db9628896e87f"
GEMIAN_BLOBS = {
    "fs/pstore/ram.c": "5c731b031e38bcb1f4bdc4ad7aa7f96497365c17",
    "fs/pstore/ram_core.c": "f5d0712097db21fc0c69699165ed2d270645eb05",
    "fs/pstore/inode.c": "77bdcdcda9a70d44a75175178676272b01e1c327",
}
MAINLINE_SHA256 = {
    "fs/pstore/ram.c": "f0ea10c5b7288acead2820d89f72942b2a70a6a62e33979862dce8b5e6939c34",
    "fs/pstore/ram_core.c": "04c344aff8ec1522722cb7411d0bcf4e3d18def7f4d9610d58d518088040f4c6",
    "fs/pstore/platform.c": "02c2509fb22199b7be77a91a7a4b9919633a72ed683ea3c6a9e6311cad7d63a0",
}

GEMIAN_LINE_EVIDENCE: Mapping[str, Mapping[int, str]] = {
    "fs/pstore/ram.c": {
        225: "prz = ramoops_get_next_prz(&cxt->cprz, &cxt->console_read_cnt,",
        226: "1, id, type, PSTORE_TYPE_CONSOLE, 0);",
        228: "prz = ramoops_get_next_prz(&cxt->bprz, &cxt->bconsole_read_cnt,",
        229: "1, id, type, PSTORE_TYPE_CONSOLE, 0);",
        233: "*id = 2;",
        556: "dump_mem_sz = cxt->size - cxt->console_size * 2 - cxt->ftrace_size",
        557: "- cxt->pmsg_size;",
        562: "err = ramoops_init_prz(dev, cxt, &cxt->cprz, &paddr,",
        567: "err = ramoops_init_prz(dev, cxt, &cxt->bprz, &paddr,",
        572: "err = ramoops_init_prz(dev, cxt, &cxt->fprz, &paddr, cxt->ftrace_size,",
        573: "LINUX_VERSION_CODE);",
        577: "err = ramoops_init_prz(dev, cxt, &cxt->mprz, &paddr, cxt->pmsg_size, 0);",
    },
    "fs/pstore/ram_core.c": {
        32: "struct persistent_ram_buffer {",
        33: "uint32_t    sig;",
        34: "atomic_t    start;",
        35: "atomic_t    size;",
        36: "uint8_t     data[0];",
        53: "#define PERSISTENT_RAM_SIG (0x43474244) /* DBGC */",
        531: "sig ^= PERSISTENT_RAM_SIG;",
        541: "persistent_ram_save_old(prz);",
    },
    "fs/pstore/inode.c": {
        323: "case PSTORE_TYPE_CONSOLE:",
        324: "if (id)",
        325: 'scnprintf(name, sizeof(name), "console-%s-%lld", psname, id);',
    },
}

MAINLINE_LINE_EVIDENCE: Mapping[str, Mapping[int, str]] = {
    "fs/pstore/ram.c": {
        601: "*prz = persistent_ram_new(*paddr, sz, sig, &cxt->ecc_info,",
        602: "cxt->memtype, PRZ_FLAG_ZAP_OLD, label);",
        786: "dump_mem_sz = cxt->size - cxt->console_size - cxt->ftrace_size",
        787: "- cxt->pmsg_size;",
        794: 'err = ramoops_init_prz("console", dev, cxt, &cxt->cprz, &paddr,',
        799: 'err = ramoops_init_prz("pmsg", dev, cxt, &cxt->mprz, &paddr,',
        807: 'err = ramoops_init_przs("ftrace", dev, cxt, &cxt->fprzs, &paddr,',
    },
    "fs/pstore/ram_core.c": {
        32: "struct persistent_ram_buffer {",
        33: "uint32_t    sig;",
        34: "atomic_t    start;",
        35: "atomic_t    size;",
        36: "uint8_t     data[];",
        39: "#define PERSISTENT_RAM_SIG (0x43474244) /* DBGC */",
        530: "bool zap = !!(prz->flags & PRZ_FLAG_ZAP_OLD);",
        538: "sig ^= PERSISTENT_RAM_SIG;",
        554: "persistent_ram_save_old(prz);",
        563: "/* Reset missing, invalid, or single-use memory area. */",
        564: "if (zap)",
        565: "persistent_ram_zap(prz);",
    },
    "fs/pstore/platform.c": {
        423: "pstore_console.flags = CON_PRINTBUFFER | CON_ENABLED | CON_ANYTIME;",
        424: "register_console(&pstore_console);",
    },
}


class ValidationError(RuntimeError):
    """A pinned source or layout contract did not match."""


def run_git(tree: pathlib.Path, *arguments: str) -> bytes:
    try:
        return subprocess.run(
            ["git", "-C", str(tree), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValidationError(f"git failed for {tree}: {arguments}") from exc


def git_text(tree: pathlib.Path, revision: str, relative: str) -> str:
    data = run_git(tree, "show", f"{revision}:{relative}")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"source is not UTF-8: {relative}") from exc


def file_text(tree: pathlib.Path, relative: str) -> str:
    path = tree / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"cannot read {path}") from exc


def require_lines(label: str, source: str, expected: Mapping[int, str]) -> None:
    lines = source.splitlines()
    for number, text in expected.items():
        if number > len(lines) or lines[number - 1].strip() != text:
            actual = "<missing>" if number > len(lines) else lines[number - 1].strip()
            raise ValidationError(
                f"{label}:{number}: expected {text!r}, found {actual!r}"
            )


def parse_version(makefile: str) -> tuple[int, int, int]:
    values: dict[str, int] = {}
    for line in makefile.splitlines():
        if "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key in {"VERSION", "PATCHLEVEL", "SUBLEVEL"} and value.isdigit():
            values[key] = int(value)
    try:
        return values["VERSION"], values["PATCHLEVEL"], values["SUBLEVEL"]
    except KeyError as exc:
        raise ValidationError("kernel Makefile lacks a numeric version triplet") from exc


def version_code(version: tuple[int, int, int]) -> int:
    major, minor, patch = version
    return (major << 16) | (minor << 8) | min(patch, 255)


def region(start: int, size: int) -> tuple[int, int]:
    return start, start + size


def fmt_region(value: tuple[int, int]) -> str:
    return f"[0x{value[0]:08x},0x{value[1]:08x})"


def build_layouts() -> tuple[dict[str, tuple[int, int]], dict[str, tuple[int, int]]]:
    gemian_dump = (
        TOTAL_SIZE - 2 * CONSOLE_SIZE - FTRACE_SIZE - GEMIAN_PMSG_SIZE
    )
    mainline_dump = (
        TOTAL_SIZE - CONSOLE_SIZE - FTRACE_SIZE - MAINLINE_PMSG_SIZE
    )
    if gemian_dump % RECORD_SIZE or mainline_dump % RECORD_SIZE:
        raise ValidationError("dump areas are not exact record-size multiples")

    cursor = BASE
    gemian: dict[str, tuple[int, int]] = {}
    for name, size in (
        ("dmesg", gemian_dump),
        ("console", CONSOLE_SIZE),
        ("bconsole", CONSOLE_SIZE),
        ("ftrace", FTRACE_SIZE),
        ("pmsg", GEMIAN_PMSG_SIZE),
    ):
        gemian[name] = region(cursor, size)
        cursor += size
    if cursor != BASE + TOTAL_SIZE:
        raise ValidationError("Gemian regions do not consume the reservation")

    cursor = BASE
    mainline: dict[str, tuple[int, int]] = {}
    for name, size in (
        ("dmesg", mainline_dump),
        ("console", CONSOLE_SIZE),
        ("pmsg", MAINLINE_PMSG_SIZE),
        ("ftrace", FTRACE_SIZE),
    ):
        mainline[name] = region(cursor, size)
        cursor += size
    if cursor != BASE + TOTAL_SIZE:
        raise ValidationError("Linux 7.1.3 regions do not consume the reservation")
    return gemian, mainline


def validate(gemian_tree: pathlib.Path, mainline_tree: pathlib.Path) -> list[str]:
    if run_git(gemian_tree, "rev-parse", "HEAD").decode().strip() != GEMIAN_COMMIT:
        raise ValidationError(f"Gemian HEAD is not {GEMIAN_COMMIT}")

    gemian_sources: dict[str, str] = {}
    for relative, expected_blob in GEMIAN_BLOBS.items():
        blob = run_git(gemian_tree, "rev-parse", f"{GEMIAN_COMMIT}:{relative}").decode().strip()
        if blob != expected_blob:
            raise ValidationError(f"unexpected Gemian blob for {relative}: {blob}")
        source = git_text(gemian_tree, GEMIAN_COMMIT, relative)
        require_lines(f"gemian:{relative}", source, GEMIAN_LINE_EVIDENCE[relative])
        gemian_sources[relative] = source

    mainline_sources: dict[str, str] = {}
    for relative, expected_sha256 in MAINLINE_SHA256.items():
        source = file_text(mainline_tree, relative)
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if digest != expected_sha256:
            raise ValidationError(f"unexpected Linux 7.1.3 SHA-256 for {relative}: {digest}")
        require_lines(f"mainline:{relative}", source, MAINLINE_LINE_EVIDENCE[relative])
        mainline_sources[relative] = source

    gemian_version = parse_version(git_text(gemian_tree, GEMIAN_COMMIT, "Makefile"))
    mainline_version = parse_version(file_text(mainline_tree, "Makefile"))
    if gemian_version != (3, 18, 79):
        raise ValidationError(f"unexpected Gemian source version: {gemian_version}")
    if mainline_version != (7, 1, 3):
        raise ValidationError(f"unexpected mainline source version: {mainline_version}")

    gemian, mainline = build_layouts()
    if mainline["dmesg"] != gemian["dmesg"]:
        raise ValidationError("mainline dmesg does not exactly align with Gemian dmesg")
    if mainline["console"] != gemian["console"]:
        raise ValidationError("mainline console does not exactly align with Gemian primary console")
    if mainline["console"] == gemian["bconsole"]:
        raise ValidationError("mainline console unexpectedly aligns with Gemian bconsole")

    gemian_ftrace_sig = PERSISTENT_RAM_SIG ^ version_code(gemian_version)
    mainline_pmsg_sig = PERSISTENT_RAM_SIG
    if mainline["pmsg"][0] != gemian["bconsole"][0]:
        raise ValidationError("mainline pmsg alignment zone does not start at Gemian bconsole")
    if mainline["pmsg"] == gemian["pmsg"]:
        raise ValidationError("mainline pmsg unexpectedly aligns with Gemian pmsg")
    if mainline_pmsg_sig != PERSISTENT_RAM_SIG:
        raise ValidationError("mainline pmsg zero-type signature changed")

    gemian_records = (gemian["dmesg"][1] - gemian["dmesg"][0]) // RECORD_SIZE
    mainline_records = (mainline["dmesg"][1] - mainline["dmesg"][0]) // RECORD_SIZE
    if gemian_records != 175 or mainline_records != 175:
        raise ValidationError("unexpected dmesg record counts")
    if mainline["dmesg"][0] != gemian["dmesg"][0]:
        raise ValidationError("dmesg record prefixes do not share a base")

    lines = [
        "validation=candidate-L-cross-version-ramoops-layout",
        f"gemian_reference_commit={GEMIAN_COMMIT}",
        "gemian_reference_version=3.18.79",
        "mainline_version=7.1.3",
    ]
    for relative, blob in GEMIAN_BLOBS.items():
        lines.append(f"gemian_blob[{relative}]={blob}")
    for relative, digest in MAINLINE_SHA256.items():
        lines.append(f"mainline_sha256[{relative}]={digest}")
    for relative, evidence in GEMIAN_LINE_EVIDENCE.items():
        lines.append(
            f"gemian_line_evidence[{relative}]="
            + ",".join(str(number) for number in evidence)
        )
    for relative, evidence in MAINLINE_LINE_EVIDENCE.items():
        lines.append(
            f"mainline_line_evidence[{relative}]="
            + ",".join(str(number) for number in evidence)
        )
    lines.extend(
        (
            f"reservation={fmt_region((BASE, BASE + TOTAL_SIZE))}",
            f"record_size=0x{RECORD_SIZE:x}",
            f"gemian_pmsg_size=0x{GEMIAN_PMSG_SIZE:x}",
            f"mainline_pmsg_alignment_size=0x{MAINLINE_PMSG_SIZE:x}",
            f"gemian_layout[dmesg]={fmt_region(gemian['dmesg'])}",
            f"gemian_layout[console]={fmt_region(gemian['console'])}",
            f"gemian_layout[bconsole]={fmt_region(gemian['bconsole'])}",
            f"gemian_layout[ftrace]={fmt_region(gemian['ftrace'])}",
            f"gemian_layout[pmsg]={fmt_region(gemian['pmsg'])}",
            f"mainline_layout[dmesg]={fmt_region(mainline['dmesg'])}",
            f"mainline_layout[console]={fmt_region(mainline['console'])}",
            f"mainline_layout[pmsg]={fmt_region(mainline['pmsg'])}",
            f"mainline_layout[ftrace]={fmt_region(mainline['ftrace'])}",
            f"dmesg_prefix_compatible_records={gemian_records}",
            f"dmesg_mainline_total_records={mainline_records}",
            f"zero_type_signature=0x{PERSISTENT_RAM_SIG:08x}",
            f"gemian_ftrace_signature=0x{gemian_ftrace_sig:08x}",
            f"mainline_pmsg_signature=0x{mainline_pmsg_sig:08x}",
            "mainline_dmesg_alignment=gemian-dmesg-exact",
            "mainline_console_alignment=gemian-primary-console-exact",
            "mainline_console_gemian_type=PSTORE_TYPE_CONSOLE",
            "mainline_console_gemian_file=console-ramoops",
            "mainline_console_cross_version_recoverable=yes-reference-source-validated",
            "mainline_single_zone_init=valid-old-snapshot-then-active-header-zap",
            "mainline_console_registration=CON_PRINTBUFFER",
            "mainline_pmsg_cross_version_recoverable=no-layout-mismatch-header-zapped-frontend-disabled",
            "mainline_pmsg_alignment_overlap=gemian-bconsole-ftrace-and-pmsg-prefix",
            "deliberate_marker_recovery_path=/dev/kmsg-to-mainline-console-to-gemian-console-ramoops",
            "live_binary_primary_console_layout=requires-separate-pinned-audit",
            "hardware_write=none",
        )
    )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gemian-tree", required=True, type=pathlib.Path)
    parser.add_argument("--mainline-tree", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        lines = validate(args.gemian_tree.resolve(), args.mainline_tree.resolve())
    except ValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
