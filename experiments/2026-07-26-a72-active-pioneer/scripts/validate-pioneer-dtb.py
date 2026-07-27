#!/usr/bin/env python3
"""Require exact AO plus Pioneer's active A72 provider DT contract."""

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

AO_DTB_SHA256 = "de40b972b068c728f7ef3a77e2eb193a687ed6f77ff80e3e5f2b39c701a892b7"
FDT_PARSER_SHA256 = (
    "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"
)
FDT_MAGIC = 0xD00DFEED
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
AS_HEADER = None
I2C6 = "/i2c@1100e000"
I2C6_PINS = "/pinctrl@10005000/i2c6-pins"
HANDOFF = "/dvfsp-handoff@11015000"
HANDOFF_PHANDLE = 0x2C
I2C6_PINS_PHANDLE = 0x2D
CPU8 = "/cpus/cpu@200"
CPU9 = "/cpus/cpu@201"
CPU8_PHANDLE = 0x2E
CPU9_PHANDLE = 0x2F
SCPSYS = "/power-controller@10006000"
SCPSYS_PHANDLE = 0x0B
WATCHDOG = "/watchdog@10007000"
WATCHDOG_PHANDLE = 0x30
BUCKB_PHANDLE = 0x31
DEPENDENCY_PROPERTY = "access-controllers"
ACCESS_CELLS_PROPERTY = "#access-controller-cells"
DA9214 = I2C6 + "/regulator@68"
REGULATORS = DA9214 + "/regulators"
BUCKA = REGULATORS + "/BUCKA"
BUCKB = REGULATORS + "/BUCKB"
A72_POWER = "/a72-power@10222000"
LEGACY_DVFSP = "/dvfsp@11015000"
OBSERVER = "/dvfsp-observer@11015000"
ACTIVE_I2C6_PROPERTIES = (
    "clock-frequency",
    "mediatek,use-push-pull",
    "pinctrl-names",
    "pinctrl-0",
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")


def load_fdt_parser() -> ModuleType:
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    require_regular(source, "source-pinned FDT parser")
    if digest(source) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("candidate_ap_fdt", source)
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
    path: pathlib.Path, expected: tuple[int, ...] | None, label: str
) -> tuple[int, ...]:
    data = path.read_bytes()
    actual = fdt_header(path)
    if expected is not None and actual != expected:
        raise ValueError(
            f"{label} FDT header changed: "
            + describe_header_delta(expected, actual)
        )
    (
        _magic,
        totalsize,
        off_struct,
        off_strings,
        off_reserve,
        _version,
        _last_compatible,
        _boot_cpu,
        size_strings,
        size_struct,
    ) = actual
    if totalsize != len(data):
        raise ValueError(f"{label} totalsize does not match the file")
    if (
        off_reserve != 40
        or off_struct % 4
        or off_strings % 4
        or size_struct % 4
        or not off_reserve < off_struct
        or off_struct + size_struct != off_strings
        or off_strings + size_strings != totalsize
    ):
        raise ValueError(
            f"{label} FDT blocks are not canonical, packed, and in bounds"
        )
    return actual


def reservation_map_bytes(path: pathlib.Path, header: tuple[int, ...]) -> bytes:
    data = path.read_bytes()
    off_struct = header[2]
    off_reserve = header[4]
    if not 40 <= off_reserve < off_struct <= len(data):
        raise ValueError(f"{path}: invalid reservation-map placement")
    return data[off_reserve:off_struct]


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


def require_ao_contract(
    fdt: ModuleType, tree: dict[str, dict[str, bytes]]
) -> dict[int, str]:
    fdt.require_prop(tree, I2C6, "status", fdt.string("disabled"))
    if any(path.startswith(I2C6 + "/") for path in tree):
        raise ValueError("Candidate AO I2C6 is not childless")
    for prop in (*ACTIVE_I2C6_PROPERTIES, DEPENDENCY_PROPERTY):
        if prop in tree[I2C6]:
            raise ValueError(f"Candidate AO I2C6 unexpectedly contains {prop}")

    fdt.require_prop(
        tree,
        HANDOFF,
        "compatible",
        fdt.string("mediatek,mt6797-dvfsp-handoff"),
    )
    fdt.require_prop(tree, HANDOFF, "status", fdt.string("okay"))
    fdt.require_prop(tree, HANDOFF, "clock-names", fdt.string("i2c"))
    if "phandle" in tree[HANDOFF] or "linux,phandle" in tree[HANDOFF]:
        raise ValueError("Candidate AO handoff unexpectedly has a phandle")
    if ACCESS_CELLS_PROPERTY in tree[HANDOFF]:
        raise ValueError(
            f"Candidate AO handoff unexpectedly has {ACCESS_CELLS_PROPERTY}"
        )

    for forbidden in (DA9214, A72_POWER, LEGACY_DVFSP, OBSERVER):
        if forbidden in tree:
            raise ValueError(f"Candidate AO contains forbidden node {forbidden}")

    handles = phandle_map(tree)
    if set(handles) != set(range(1, HANDOFF_PHANDLE)):
        raise ValueError("Candidate AO phandle allocation is not exact 0x01..0x2b")
    return handles


def validate(ao_path: pathlib.Path, candidate_path: pathlib.Path) -> None:
    require_regular(ao_path, "exact Candidate AO DT")
    require_regular(candidate_path, "Candidate Pioneer DT")
    if digest(ao_path) != AO_DTB_SHA256:
        raise ValueError("exact hardware-passed Candidate AO DT changed")

    ao_header = require_header(ao_path, AO_HEADER, "Candidate AO")
    candidate_header = require_header(candidate_path, AS_HEADER, "Candidate Pioneer")
    if reservation_map_bytes(candidate_path, candidate_header) != (
        reservation_map_bytes(ao_path, ao_header)
    ):
        raise ValueError("Candidate Pioneer changed AO's raw FDT reservation map")

    fdt = load_fdt_parser()
    ao, ao_reservations, ao_boot_cpu = fdt.parse_fdt(ao_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(
        candidate_path
    )
    if candidate_reservations != ao_reservations:
        raise ValueError("Candidate Pioneer changed AO's FDT reservation map")
    if candidate_boot_cpu != ao_boot_cpu:
        raise ValueError("Candidate Pioneer changed AO's boot_cpuid_phys")

    ao_handles = require_ao_contract(fdt, ao)
    expected = copy.deepcopy(ao)
    expected[HANDOFF][ACCESS_CELLS_PROPERTY] = fdt.cells(0)
    expected[HANDOFF]["phandle"] = fdt.cells(HANDOFF_PHANDLE)
    expected[I2C6][DEPENDENCY_PROPERTY] = fdt.cells(HANDOFF_PHANDLE)
    expected[I2C6].update(
        {
            "status": fdt.string("okay"),
            "clock-frequency": fdt.cells(3_400_000),
            "mediatek,use-push-pull": b"",
            "pinctrl-names": fdt.string("default"),
            "pinctrl-0": fdt.cells(I2C6_PINS_PHANDLE),
        }
    )
    expected[I2C6_PINS]["phandle"] = fdt.cells(I2C6_PINS_PHANDLE)
    expected[DA9214] = {
        "compatible": fdt.string("dlg,da9214"),
        "reg": fdt.cells(0x68),
    }
    expected[REGULATORS] = {}
    expected[BUCKA] = {"regulator-name": fdt.string("da9214-bucka")}
    expected[BUCKB] = {
        "regulator-name": fdt.string("vproc-big"),
        "phandle": fdt.cells(BUCKB_PHANDLE),
    }
    expected[CPU8]["phandle"] = fdt.cells(CPU8_PHANDLE)
    expected[CPU9]["phandle"] = fdt.cells(CPU9_PHANDLE)
    expected[SCPSYS]["compatible"] = b"mediatek,mt6797-scpsys\0syscon\0"
    expected[WATCHDOG]["#reset-cells"] = fdt.cells(1)
    expected[WATCHDOG]["phandle"] = fdt.cells(WATCHDOG_PHANDLE)
    expected[A72_POWER] = {
        "compatible": fdt.string("mediatek,mt6797-a72-power"),
        "reg": fdt.cells(0, 0x10222000, 0, 0x1000),
        "mediatek,spm": fdt.cells(SCPSYS_PHANDLE),
        "cpus": fdt.cells(CPU8_PHANDLE, CPU9_PHANDLE),
        "vproc-big-supply": fdt.cells(BUCKB_PHANDLE),
        "resets": fdt.cells(WATCHDOG_PHANDLE, 11),
        "reset-names": fdt.string("pwrap"),
        "status": fdt.string("okay"),
    }
    if candidate != expected:
        raise ValueError(
            "Candidate Pioneer DT is not exact AO plus the active A72 contract: "
            + describe_delta(expected, candidate)
        )

    handles = phandle_map(candidate)
    expected_handles = dict(ao_handles)
    expected_handles[HANDOFF_PHANDLE] = HANDOFF
    expected_handles[I2C6_PINS_PHANDLE] = I2C6_PINS
    expected_handles[CPU8_PHANDLE] = CPU8
    expected_handles[CPU9_PHANDLE] = CPU9
    expected_handles[WATCHDOG_PHANDLE] = WATCHDOG
    expected_handles[BUCKB_PHANDLE] = BUCKB
    if handles != expected_handles:
        raise ValueError("Candidate Pioneer phandle map changed beyond active A72 contract")
    if candidate[HANDOFF][ACCESS_CELLS_PROPERTY] != fdt.cells(0):
        raise ValueError("Candidate Pioneer handoff access-controller cells changed")
    reference = candidate[I2C6][DEPENDENCY_PROPERTY]
    if len(reference) != 4:
        raise ValueError("Candidate Pioneer I2C6 dependency is not one phandle")
    if handles.get(struct.unpack(">I", reference)[0]) != HANDOFF:
        raise ValueError("Candidate Pioneer I2C6 dependency does not resolve to handoff")

    if A72_POWER not in candidate:
        raise ValueError("Candidate Pioneer is missing the active A72 provider node")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ao", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate(args.ao, args.candidate)
    except (OSError, RuntimeError, TypeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=candidate-pioneer-exact-active-a72-dtb-contract")
    print(f"ao_dtb_sha256={AO_DTB_SHA256}")
    print(f"candidate_dtb_sha256={digest(args.candidate)}")
    print("added_nodes=5")
    print("added_properties=22")
    print("changed_properties=3")
    print("handoff_phandle=0x2c")
    print("handoff_access_controller_cells=0")
    print(f"i2c6_dependency_property={DEPENDENCY_PROPERTY}")
    print("i2c6=enabled-with-legacy-da9214-child")
    print("i2c6_pinctrl_frequency_push_pull=3400000-push-pull")
    print("da9214_regulators=BUCKA,BUCKB")
    print("a72_power=enabled-with-cpu8-cpu9-watchdog-buckb-references")
    print("cpu8_retry=kernel-late-initcall-add_cpu")
    print("console_usb_keyboard_ramoops=whole-tree-exact-ao")
    print("unexpected_semantic_delta=none")
    print("device_access=none")
    print("storage_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
