#!/usr/bin/env python3
"""Require exact AD with only CPU8/CPU9 switched to the rejecting method."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import pathlib
import stat
import struct
import sys


AD_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
FDT_PARSER_SHA256 = "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"

CPU8 = "/cpus/cpu@200"
CPU9 = "/cpus/cpu@201"
REJECTING_METHOD = "mediatek,mt6797-psci"
A53_CPUS = {
    "/cpus/cpu@0": 0x000,
    "/cpus/cpu@1": 0x001,
    "/cpus/cpu@2": 0x002,
    "/cpus/cpu@3": 0x003,
    "/cpus/cpu@100": 0x100,
    "/cpus/cpu@101": 0x101,
    "/cpus/cpu@102": 0x102,
    "/cpus/cpu@103": 0x103,
}
PRESERVED_CONTRACTS = {
    "/chosen/framebuffer@7dfb0000": (
        "compatible",
        b"simple-framebuffer\0",
    ),
    "/usb@11271000": ("status", b"okay\0"),
    "/usb@11271000/usb@11270000": ("status", b"disabled\0"),
    "/i2c@1101c000/gpio-expander@5b": ("status", b"okay\0"),
    "/keyboard-matrix": ("status", b"okay\0"),
    "/scp@10020000": ("status", b"disabled\0"),
    "/reserved-memory/reserve-memory-scp_share": (
        "compatible",
        b"mediatek,reserve-memory-scp_share\0",
    ),
    "/reserved-memory/ramoops@44410000": ("compatible", b"ramoops\0"),
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_regular_dtb(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or info.st_size == 0:
        raise ValueError(f"{label} DTB is missing, empty, or unsafe")


def load_fdt_parser() -> object:
    experiments = pathlib.Path(__file__).resolve().parents[2]
    source = (
        experiments
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    if digest(source) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("gemini_ah_fdt", source)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load FDT parser from {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def phandle_map(tree: dict[str, dict[str, bytes]]) -> dict[int, str]:
    handles: dict[int, str] = {}
    for path, props in tree.items():
        aliases: list[int] = []
        for name in ("phandle", "linux,phandle"):
            raw = props.get(name)
            if raw is None:
                continue
            if len(raw) != 4:
                raise ValueError(f"{path}:{name} is not one cell")
            aliases.append(struct.unpack(">I", raw)[0])
        if len(set(aliases)) > 1:
            raise ValueError(f"{path} has conflicting phandle aliases")
        if not aliases:
            continue
        value = aliases[0]
        if value == 0 or (value in handles and handles[value] != path):
            raise ValueError(f"invalid or duplicate phandle 0x{value:x} at {path}")
        handles[value] = path
    return handles


def describe_delta(expected: dict, actual: dict) -> str:
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
    return "; ".join(details[:24])


def validate(ad_path: pathlib.Path, candidate_path: pathlib.Path) -> None:
    require_regular_dtb(ad_path, "Candidate AD")
    require_regular_dtb(candidate_path, "Candidate AH")
    if digest(ad_path) != AD_DTB_SHA256:
        raise ValueError("exact hardware-passed Candidate AD DTB changed")

    fdt = load_fdt_parser()
    ad, ad_reservations, ad_boot_cpu = fdt.parse_fdt(ad_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(
        candidate_path
    )
    if candidate_reservations != ad_reservations:
        raise ValueError("Candidate AH changed AD's FDT reservation map")
    if candidate_boot_cpu != ad_boot_cpu:
        raise ValueError("Candidate AH changed AD's boot_cpuid_phys")
    if phandle_map(candidate) != phandle_map(ad):
        raise ValueError("Candidate AH changed AD's global phandle map")

    for path, reg in A53_CPUS.items():
        fdt.require_prop(ad, path, "compatible", fdt.string("arm,cortex-a53"))
        fdt.require_prop(ad, path, "reg", fdt.cells(reg))
        fdt.require_prop(ad, path, "enable-method", fdt.string("psci"))
    for path, reg in ((CPU8, 0x200), (CPU9, 0x201)):
        fdt.require_prop(ad, path, "compatible", fdt.string("arm,cortex-a72"))
        fdt.require_prop(ad, path, "reg", fdt.cells(reg))
        fdt.require_prop(ad, path, "enable-method", fdt.string("psci"))
    for path, (prop, value) in PRESERVED_CONTRACTS.items():
        fdt.require_prop(ad, path, prop, value)
    fdt.require_prop(ad, "/usb@11271000", "dr_mode", fdt.string("peripheral"))
    fdt.require_prop(
        ad,
        "/i2c@1101c000/gpio-expander@5b",
        "compatible",
        fdt.string("awinic,aw9523-pinctrl"),
    )
    fdt.require_prop(
        ad,
        "/keyboard-matrix",
        "compatible",
        fdt.string("gpio-matrix-keypad"),
    )
    fdt.require_prop(ad, "/i2c@1100e000", "status", fdt.string("disabled"))
    for forbidden in (
        "/a72-power@10222000",
        "/i2c@1100e000/regulator@68",
        "/reserved-memory/mblock-3-framebuffer",
    ):
        if forbidden in ad:
            raise ValueError(f"AD oracle unexpectedly contains forbidden node {forbidden}")

    expected = copy.deepcopy(ad)
    for path in (CPU8, CPU9):
        expected[path]["enable-method"] = fdt.string(REJECTING_METHOD)
    if candidate != expected:
        raise ValueError(
            "Candidate AH DT delta is not exact AD plus two A72 methods: "
            + describe_delta(expected, candidate)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ad", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate(args.ad, args.candidate)
    except (OSError, RuntimeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=candidate-ah-ad-contract-two-property-dtb-delta")
    print(f"ad_dtb_sha256={AD_DTB_SHA256}")
    print(f"candidate_dtb_sha256={digest(args.candidate)}")
    print("changed_properties=/cpus/cpu@200:enable-method,/cpus/cpu@201:enable-method")
    print("old_enable_method=psci")
    print(f"new_enable_method={REJECTING_METHOD}")
    print("cpu0_cpu7_contract=byte-exact-ad")
    print("simplefb_usb_keyboard_scp_reserved_memory=byte-exact-ad")
    print("a72_power_da9214_static_lk_framebuffer_nodes=absent")
    print("fdt_header_reservations_boot_cpu_phandles=byte-exact-ad")
    print("unexpected_semantic_delta=none")
    print("active_a72_operation=none")
    print("raw_framebuffer_write=none")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
