#!/usr/bin/env python3
"""Require exact AH plus only Candidate AO's one-way DVFSP handoff node."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import pathlib
import stat
import struct
import sys
from types import ModuleType

sys.dont_write_bytecode = True


AH_DTB_SHA256 = "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845"
FDT_PARSER_SHA256 = "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"
FDT_MAGIC = 0xD00DFEED

INFRACFG = "/syscon@10001000"
INFRACFG_PHANDLE = 0x3
I2C6 = "/i2c@1100e000"
I2C6_MAIN_CLOCK = (INFRACFG_PHANDLE, 0x36)
I2C6_DMA_CLOCK = (INFRACFG_PHANDLE, 0x2E)
DA9214 = I2C6 + "/regulator@68"
A72_POWER = "/a72-power@10222000"
LEGACY_DVFSP = "/dvfsp@11015000"
OBSERVER = "/dvfsp-observer@11015000"
HANDOFF = "/dvfsp-handoff@11015000"
CPU8 = "/cpus/cpu@200"
CPU9 = "/cpus/cpu@201"
REJECTING_METHOD = "mediatek,mt6797-psci"

HEADER_NAMES = (
    "magic",
    "totalsize",
    "off_dt_struct",
    "off_dt_strings",
    "off_mem_rsvmap",
    "version",
    "last_comp_version",
    "boot_cpuid_phys",
    "size_dt_strings",
    "size_dt_struct",
)
AH_HEADER = (
    FDT_MAGIC,
    0x66B3,
    0x38,
    0x60F8,
    0x28,
    17,
    16,
    0,
    0x5BB,
    0x60C0,
)
AO_HEADER = (
    FDT_MAGIC,
    0x6763,
    0x38,
    0x61A8,
    0x28,
    17,
    16,
    0,
    0x5BB,
    0x6170,
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")


def load_fdt_parser() -> ModuleType:
    experiments = pathlib.Path(__file__).resolve().parents[2]
    source = (
        experiments
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    require_regular(source, "source-pinned FDT parser")
    if digest(source) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("candidate_ao_fdt", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load FDT parser from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fdt_header(path: pathlib.Path) -> tuple[int, ...]:
    data = path.read_bytes()
    if len(data) < 40:
        raise ValueError(f"{path}: truncated FDT header")
    return struct.unpack_from(">10I", data)


def describe_header_delta(
    expected: tuple[int, ...], actual: tuple[int, ...]
) -> str:
    return ", ".join(
        f"{name}=0x{value:x} (expected 0x{wanted:x})"
        for name, wanted, value in zip(HEADER_NAMES, expected, actual)
        if wanted != value
    )


def require_header(
    path: pathlib.Path, expected: tuple[int, ...], label: str
) -> tuple[int, ...]:
    actual = fdt_header(path)
    if actual != expected:
        raise ValueError(
            f"{label} FDT header changed: "
            + describe_header_delta(expected, actual)
        )
    if actual[1] != path.stat().st_size:
        raise ValueError(f"{label} totalsize does not match the file")
    return actual


def fdt_block(path: pathlib.Path, offset: int, size: int) -> bytes:
    data = path.read_bytes()
    end = offset + size
    if offset < 0 or size < 0 or end > len(data):
        raise ValueError(f"{path}: invalid FDT block extent")
    return data[offset:end]


def reservation_map_bytes(
    path: pathlib.Path, header: tuple[int, ...]
) -> bytes:
    off_struct = header[2]
    off_reserve = header[4]
    if not 40 <= off_reserve < off_struct:
        raise ValueError(f"{path}: invalid reservation-map placement")
    return fdt_block(path, off_reserve, off_struct - off_reserve)


def strings_block(path: pathlib.Path, header: tuple[int, ...]) -> bytes:
    return fdt_block(path, header[3], header[8])


def phandle_map(tree: dict[str, dict[str, bytes]]) -> dict[int, str]:
    handles: dict[int, str] = {}
    for path, properties in tree.items():
        aliases: list[int] = []
        for name in ("phandle", "linux,phandle"):
            raw = properties.get(name)
            if raw is None:
                continue
            if len(raw) != 4:
                raise ValueError(f"{path}:{name} is not one cell")
            aliases.append(struct.unpack(">I", raw)[0])
        if len(set(aliases)) > 1:
            raise ValueError(f"{path} has conflicting phandle aliases")
        if not aliases:
            continue
        handle = aliases[0]
        if handle == 0 or (handle in handles and handles[handle] != path):
            raise ValueError(f"invalid or duplicate phandle 0x{handle:x} at {path}")
        handles[handle] = path
    return handles


def string_list(raw: bytes, label: str) -> tuple[str, ...]:
    if not raw or not raw.endswith(b"\0"):
        raise ValueError(f"{label} is not a terminated string list")
    values = raw[:-1].split(b"\0")
    if not values or any(not value for value in values):
        raise ValueError(f"{label} has an empty string")
    try:
        return tuple(value.decode("ascii") for value in values)
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not ASCII") from exc


def clock_references(
    fdt: ModuleType,
    tree: dict[str, dict[str, bytes]],
    handles: dict[int, str],
    path: str,
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    raw = tree.get(path, {}).get("clocks")
    if raw is None or not raw or len(raw) % 4:
        raise ValueError(f"{path}:clocks is not a non-empty cell list")
    cells = struct.unpack(">" + "I" * (len(raw) // 4), raw)
    references: list[tuple[int, tuple[int, ...]]] = []
    index = 0
    while index < len(cells):
        handle = cells[index]
        index += 1
        provider = handles.get(handle)
        if provider is None:
            raise ValueError(f"{path}:clocks has unresolved phandle 0x{handle:x}")
        raw_count = tree[provider].get("#clock-cells")
        if raw_count is None or len(raw_count) != 4:
            raise ValueError(f"{provider}:#clock-cells is not one cell")
        count = struct.unpack(">I", raw_count)[0]
        if count > len(cells) - index:
            raise ValueError(f"{path}:clocks has a truncated clock specifier")
        specifier = tuple(cells[index : index + count])
        index += count
        references.append((handle, specifier))
    return tuple(references)


def named_clock(
    fdt: ModuleType,
    tree: dict[str, dict[str, bytes]],
    handles: dict[int, str],
    path: str,
    name: str,
) -> tuple[int, tuple[int, ...]]:
    names = string_list(
        tree.get(path, {}).get("clock-names", b""),
        f"{path}:clock-names",
    )
    references = clock_references(fdt, tree, handles, path)
    if len(names) != len(references):
        raise ValueError(f"{path} clock names and references do not align")
    if names.count(name) != 1:
        raise ValueError(f"{path} does not name exactly one {name!r} clock")
    return references[names.index(name)]


def describe_delta(
    expected: dict[str, dict[str, bytes]],
    actual: dict[str, dict[str, bytes]],
) -> str:
    details: list[str] = []
    for path in sorted(set(expected) | set(actual)):
        if path not in expected:
            details.append(f"unexpected node {path}")
            continue
        if path not in actual:
            details.append(f"missing node {path}")
            continue
        for prop in sorted(set(expected[path]) | set(actual[path])):
            if prop not in expected[path]:
                details.append(f"unexpected property {path}:{prop}")
            elif prop not in actual[path]:
                details.append(f"missing property {path}:{prop}")
            elif expected[path][prop] != actual[path][prop]:
                details.append(f"changed property {path}:{prop}")
    return "; ".join(details[:32])


def require_ah_contract(
    fdt: ModuleType, ah: dict[str, dict[str, bytes]]
) -> dict[int, str]:
    fdt.require_prop(
        ah, "/", "model", fdt.string("Planet Computers Gemini PDA")
    )
    fdt.require_prop(
        ah,
        "/",
        "compatible",
        fdt.string("planet,gemini-pda") + fdt.string("mediatek,mt6797"),
    )
    fdt.require_prop(ah, "/", "#address-cells", fdt.cells(2))
    fdt.require_prop(ah, "/", "#size-cells", fdt.cells(2))

    framebuffer = "/chosen/framebuffer@7dfb0000"
    fdt.require_prop(
        ah, framebuffer, "compatible", fdt.string("simple-framebuffer")
    )
    fdt.require_prop(
        ah, framebuffer, "reg", fdt.cells(0, 0x7DFB0000, 0, 0x01F90000)
    )

    fdt.require_prop(ah, "/usb@11271000", "status", fdt.string("okay"))
    fdt.require_prop(
        ah, "/usb@11271000", "dr_mode", fdt.string("peripheral")
    )
    fdt.require_prop(
        ah,
        "/usb@11271000/usb@11270000",
        "status",
        fdt.string("disabled"),
    )

    fdt.require_prop(ah, "/i2c@1101c000", "status", fdt.string("okay"))
    expander = "/i2c@1101c000/gpio-expander@5b"
    fdt.require_prop(
        ah,
        expander,
        "compatible",
        fdt.string("awinic,aw9523-pinctrl"),
    )
    fdt.require_prop(ah, expander, "status", fdt.string("okay"))
    fdt.require_prop(
        ah,
        "/keyboard-matrix",
        "compatible",
        fdt.string("gpio-matrix-keypad"),
    )
    fdt.require_prop(
        ah, "/keyboard-matrix", "status", fdt.string("okay")
    )

    ramoops = "/reserved-memory/ramoops@44410000"
    fdt.require_prop(ah, ramoops, "compatible", fdt.string("ramoops"))
    fdt.require_prop(
        ah, ramoops, "reg", fdt.cells(0, 0x44410000, 0, 0x000E0000)
    )

    fdt.require_prop(ah, I2C6, "status", fdt.string("disabled"))
    if any(path.startswith(I2C6 + "/") for path in ah):
        raise ValueError("AH I2C6 is not childless")
    for prop in (
        "clock-frequency",
        "mediatek,use-push-pull",
        "pinctrl-names",
        "pinctrl-0",
    ):
        if prop in ah[I2C6]:
            raise ValueError(f"AH I2C6 unexpectedly has active property {prop}")

    for path in (DA9214, A72_POWER, LEGACY_DVFSP, OBSERVER, HANDOFF):
        if path in ah:
            raise ValueError(f"AH unexpectedly contains forbidden node {path}")
    for path in ah:
        if path.rsplit("/", 1)[-1].startswith("dvfsp"):
            raise ValueError(f"AH unexpectedly contains DVFSP node {path}")

    for cpu in (CPU8, CPU9):
        fdt.require_prop(
            ah, cpu, "enable-method", fdt.string(REJECTING_METHOD)
        )

    fdt.require_prop(
        ah,
        INFRACFG,
        "compatible",
        fdt.string("mediatek,mt6797-infracfg") + fdt.string("syscon"),
    )
    fdt.require_prop(
        ah, INFRACFG, "reg", fdt.cells(0, 0x10001000, 0, 0x1000)
    )
    fdt.require_prop(ah, INFRACFG, "#clock-cells", fdt.cells(1))
    fdt.require_prop(
        ah, INFRACFG, "phandle", fdt.cells(INFRACFG_PHANDLE)
    )

    handles = phandle_map(ah)
    if handles.get(INFRACFG_PHANDLE) != INFRACFG:
        raise ValueError("AH infracfg phandle does not resolve exactly")
    references = clock_references(fdt, ah, handles, I2C6)
    if references != (
        (I2C6_MAIN_CLOCK[0], (I2C6_MAIN_CLOCK[1],)),
        (I2C6_DMA_CLOCK[0], (I2C6_DMA_CLOCK[1],)),
    ):
        raise ValueError("AH I2C6 clock references changed")
    if string_list(ah[I2C6]["clock-names"], f"{I2C6}:clock-names") != (
        "main",
        "dma",
    ):
        raise ValueError("AH I2C6 clock names changed")
    main_clock = named_clock(fdt, ah, handles, I2C6, "main")
    if main_clock != (I2C6_MAIN_CLOCK[0], (I2C6_MAIN_CLOCK[1],)):
        raise ValueError("AH I2C6 main clock is not <0x3 0x36>")
    return handles


def validate(ah_path: pathlib.Path, candidate_path: pathlib.Path) -> None:
    require_regular(ah_path, "exact Candidate AH DT")
    require_regular(candidate_path, "Candidate AO DT")
    if digest(ah_path) != AH_DTB_SHA256:
        raise ValueError("exact hardware-passed Candidate AH DT changed")

    ah_header = require_header(ah_path, AH_HEADER, "Candidate AH")
    candidate_header = require_header(
        candidate_path, AO_HEADER, "Candidate AO"
    )
    if reservation_map_bytes(candidate_path, candidate_header) != (
        reservation_map_bytes(ah_path, ah_header)
    ):
        raise ValueError("Candidate AO changed AH's raw FDT reservation map")
    if strings_block(candidate_path, candidate_header) != strings_block(
        ah_path, ah_header
    ):
        raise ValueError("Candidate AO changed AH's raw FDT strings block")

    fdt = load_fdt_parser()
    ah, ah_reservations, ah_boot_cpu = fdt.parse_fdt(ah_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(
        candidate_path
    )
    if candidate_reservations != ah_reservations:
        raise ValueError("Candidate AO changed AH's FDT reservation map")
    if candidate_boot_cpu != ah_boot_cpu:
        raise ValueError("Candidate AO changed AH's boot_cpuid_phys")

    ah_handles = require_ah_contract(fdt, ah)
    if candidate.get(I2C6) != ah[I2C6]:
        raise ValueError("Candidate AO changed AH's I2C6 node bytes")
    if any(path.startswith(I2C6 + "/") for path in candidate):
        raise ValueError("Candidate AO made disabled I2C6 non-childless")

    main_handle, main_specifier = named_clock(
        fdt, ah, ah_handles, I2C6, "main"
    )
    expected = copy.deepcopy(ah)
    expected[HANDOFF] = {
        "compatible": fdt.string("mediatek,mt6797-dvfsp-handoff"),
        "reg": fdt.cells(0, 0x11015000, 0, 0x1000),
        "clocks": fdt.cells(main_handle, *main_specifier),
        "clock-names": fdt.string("i2c"),
        "mediatek,infracfg": fdt.cells(INFRACFG_PHANDLE),
        "status": fdt.string("okay"),
    }
    if candidate != expected:
        raise ValueError(
            "Candidate AO DT is not exact AH plus the handoff node: "
            + describe_delta(expected, candidate)
        )
    if len(candidate[HANDOFF]) != 6:
        raise ValueError("Candidate AO handoff node does not have six properties")

    candidate_handles = phandle_map(candidate)
    if candidate_handles != ah_handles:
        raise ValueError("Candidate AO changed AH's global phandle map")
    handoff_clocks = clock_references(
        fdt, candidate, candidate_handles, HANDOFF
    )
    if handoff_clocks != ((main_handle, main_specifier),):
        raise ValueError("handoff clock is not the AH I2C6 main clock")
    if named_clock(
        fdt, candidate, candidate_handles, HANDOFF, "i2c"
    ) != (main_handle, main_specifier):
        raise ValueError("handoff i2c clock name does not select that clock")
    reference = struct.unpack(
        ">I", candidate[HANDOFF]["mediatek,infracfg"]
    )[0]
    if candidate_handles.get(reference) != INFRACFG:
        raise ValueError("handoff infracfg reference does not resolve exactly")

    for forbidden in (DA9214, A72_POWER, LEGACY_DVFSP, OBSERVER):
        if forbidden in candidate:
            raise ValueError(f"Candidate AO contains forbidden node {forbidden}")
    dvfsp_nodes = {
        path
        for path in candidate
        if path.rsplit("/", 1)[-1].startswith("dvfsp")
    }
    if dvfsp_nodes != {HANDOFF}:
        raise ValueError("Candidate AO has an unexpected DVFSP node set")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ah", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate(args.ah, args.candidate)
    except (OSError, RuntimeError, TypeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=candidate-ao-exact-ah-plus-one-way-dvfsp-handoff")
    print(f"ah_dtb_sha256={AH_DTB_SHA256}")
    print(f"candidate_dtb_sha256={digest(args.candidate)}")
    print(f"added_node={HANDOFF}")
    print("added_nodes=1")
    print("added_properties=6")
    print("changed_existing_nodes=0")
    print("compatible=mediatek,mt6797-dvfsp-handoff")
    print("reg=0x11015000+0x1000")
    print("clock_source=/i2c@1100e000:clocks[name=main]")
    print("clocks=<0x3 0x36>")
    print("clock-names=i2c")
    print(f"infracfg_path={INFRACFG}")
    print(f"infracfg_phandle=0x{INFRACFG_PHANDLE:x}")
    print("existing_ah_phandles=unchanged")
    print("i2c6=byte-exact-disabled-childless")
    print("observer_legacy_dvfsp_da9214_a72_power_nodes=absent")
    print("cpu8_cpu9_request=none")
    print("console_usb_keyboard_ramoops=whole-tree-exact-ah")
    print("fdt_header=exact-ao-layout-derived-from-ah")
    print("fdt_reservation_map=raw-byte-exact-ah")
    print("fdt_strings_block=raw-byte-exact-ah")
    print("unexpected_semantic_delta=none")
    print("device_access=none")
    print("storage_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
