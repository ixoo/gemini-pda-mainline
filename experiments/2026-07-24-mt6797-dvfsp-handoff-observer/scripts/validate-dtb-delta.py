#!/usr/bin/env python3
"""Require exact AH plus only Candidate AN's DVFSP observer node."""

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

INFRACFG = "/syscon@10001000"
INFRACFG_PHANDLE = 0x3
I2C6 = "/i2c@1100e000"
DA9214 = I2C6 + "/regulator@68"
A72_POWER = "/a72-power@10222000"
LEGACY_DVFSP = "/dvfsp@11015000"
OBSERVER = "/dvfsp-observer@11015000"
CPU8 = "/cpus/cpu@200"
CPU9 = "/cpus/cpu@201"
REJECTING_METHOD = "mediatek,mt6797-psci"


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
    spec = importlib.util.spec_from_file_location("candidate_an_fdt", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load FDT parser from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def require_ah_contract(fdt: ModuleType, ah: dict[str, dict[str, bytes]]) -> None:
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
    for prop in (
        "clock-frequency",
        "mediatek,use-push-pull",
        "pinctrl-names",
        "pinctrl-0",
    ):
        if prop in ah[I2C6]:
            raise ValueError(f"AH I2C6 unexpectedly has active property {prop}")
    for path in (DA9214, A72_POWER, LEGACY_DVFSP, OBSERVER):
        if path in ah:
            raise ValueError(f"AH unexpectedly contains forbidden node {path}")

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
    fdt.require_prop(
        ah, INFRACFG, "phandle", fdt.cells(INFRACFG_PHANDLE)
    )


def validate(ah_path: pathlib.Path, candidate_path: pathlib.Path) -> None:
    require_regular(ah_path, "exact Candidate AH DT")
    require_regular(candidate_path, "Candidate AN DT")
    if digest(ah_path) != AH_DTB_SHA256:
        raise ValueError("exact hardware-passed Candidate AH DT changed")

    fdt = load_fdt_parser()
    ah, ah_reservations, ah_boot_cpu = fdt.parse_fdt(ah_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(
        candidate_path
    )
    if candidate_reservations != ah_reservations:
        raise ValueError("Candidate AN changed AH's FDT reservation map")
    if candidate_boot_cpu != ah_boot_cpu:
        raise ValueError("Candidate AN changed AH's boot_cpuid_phys")

    require_ah_contract(fdt, ah)
    ah_handles = phandle_map(ah)
    if ah_handles.get(INFRACFG_PHANDLE) != INFRACFG:
        raise ValueError("AH infracfg phandle does not resolve exactly")

    expected = copy.deepcopy(ah)
    expected[OBSERVER] = {
        "compatible": fdt.string(
            "mediatek,mt6797-dvfsp-handoff-observer"
        ),
        "reg": fdt.cells(0, 0x11015000, 0, 0x1000),
        "mediatek,infracfg": fdt.cells(INFRACFG_PHANDLE),
        "status": fdt.string("okay"),
    }
    if candidate != expected:
        raise ValueError(
            "Candidate AN DT is not exact AH plus the observer node: "
            + describe_delta(expected, candidate)
        )
    if phandle_map(candidate) != ah_handles:
        raise ValueError("Candidate AN changed AH's global phandle map")
    reference = struct.unpack(
        ">I", candidate[OBSERVER]["mediatek,infracfg"]
    )[0]
    if ah_handles.get(reference) != INFRACFG:
        raise ValueError("observer infracfg reference does not resolve exactly")


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

    print("validation=candidate-an-exact-ah-plus-dvfsp-observer")
    print(f"ah_dtb_sha256={AH_DTB_SHA256}")
    print(f"candidate_dtb_sha256={digest(args.candidate)}")
    print(f"added_node={OBSERVER}")
    print("added_nodes=1")
    print("added_properties=4")
    print("changed_existing_nodes=0")
    print("compatible=mediatek,mt6797-dvfsp-handoff-observer")
    print("reg=0x11015000+0x1000")
    print(f"infracfg_path={INFRACFG}")
    print(f"infracfg_phandle=0x{INFRACFG_PHANDLE:x}")
    print("existing_ah_phandles=unchanged")
    print("i2c6=disabled")
    print("da9214_a72_power_legacy_dvfsp_nodes=absent")
    print("cpu8_cpu9_request=none")
    print("console_usb_keyboard_ramoops=whole-tree-exact-ah")
    print("fdt_reservations_boot_cpu=exact-ah")
    print("unexpected_semantic_delta=none")
    print("driver_validation=none")
    print("device_access=none")
    print("storage_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
