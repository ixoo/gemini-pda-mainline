#!/usr/bin/env python3
"""Validate a private post-LK live FDT without emitting sensitive values."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import stat
import struct
import sys
from types import ModuleType


sys.dont_write_bytecode = True

FDT_PARSER_SHA256 = "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"
EXPECTED_LIVE_FDT_SHA256 = (
    "1ffc67486e68a08da3d946d7fd0bb43d83a92bbc44c7d2fef6c2e77d8c9d4b50"
)
EXPECTED_LIVE_FDT_SIZE = 52547

OBSERVER = "/dvfsp-observer@11015000"
I2C6 = "/i2c@1100e000"
DA9214 = I2C6 + "/regulator@68"
A72_POWER = "/a72-power@10222000"
LEGACY_DVFSP = "/dvfsp@11015000"
CPU8 = "/cpus/cpu@200"
CPU9 = "/cpus/cpu@201"

EXPECTED_CHANGED_PROPERTIES = {
    ("/", "model"),
    ("/scp@10020000", "status"),
}
EXPECTED_ADDED_PROPERTIES = {
    ("/chosen", name)
    for name in (
        "atag,boot",
        "atag,boot_voltage",
        "atag,cmdline",
        "atag,devinfo",
        "atag,fg_swocv_i",
        "atag,fg_swocv_v",
        "atag,imix_r",
        "atag,masp",
        "atag,mdinfo",
        "atag,mem",
        "atag,ptp",
        "atag,shutdown_time",
        "atag,two_sec_reboot",
        "atag,videolfb",
        "bootargs",
        "ccci,modem_info_v2",
        "linux,initrd-end",
        "linux,initrd-start",
        "non_secure_sram",
    )
} | {
    ("/memory@40000000", name)
    for name in (
        "lca_reserved_mem",
        "mblock_info",
        "orig_dram_info",
        "tee_reserved_mem",
    )
}
EXPECTED_ADDED_NODES = {
    "/firmware/android",
    "/reserved-memory/mblock-1-log-store",
    "/reserved-memory/mblock-2-atf-log-reserved",
    "/reserved-memory/mblock-3-framebuffer",
    "/reserved-memory/mblock-4-SCP-reserved",
    "/reserved-memory/mblock-5-ccci",
    "/reserved-memory/mblock-6-ccci",
    "/reserved-memory/mblock-7-ccci",
    "/reserved-memory/reserve-memory-dram_r0_dummy_read",
    "/reserved-memory/reserve-memory-dram_r1_dummy_read",
}
EXPECTED_REMOVED_NODES = {
    "/reserved-memory/reserve-memory-ccci_md1",
    "/reserved-memory/reserve-memory-ccci_share",
}
EXPECTED_EXISTING_PROPERTY_LENGTHS = {
    ("/chosen", "atag,boot"): 12,
    ("/chosen", "atag,boot_voltage"): 1,
    ("/chosen", "atag,cmdline"): 516,
    ("/chosen", "atag,devinfo"): 412,
    ("/chosen", "atag,fg_swocv_i"): 1,
    ("/chosen", "atag,fg_swocv_v"): 1,
    ("/chosen", "atag,imix_r"): 4,
    ("/chosen", "atag,masp"): 88,
    ("/chosen", "atag,mdinfo"): 12,
    ("/chosen", "atag,mem"): 48,
    ("/chosen", "atag,ptp"): 24,
    ("/chosen", "atag,shutdown_time"): 1,
    ("/chosen", "atag,two_sec_reboot"): 1,
    ("/chosen", "atag,videolfb"): 60,
    ("/chosen", "bootargs"): 508,
    ("/chosen", "ccci,modem_info_v2"): 48,
    ("/chosen", "linux,initrd-end"): 4,
    ("/chosen", "linux,initrd-start"): 4,
    ("/chosen", "non_secure_sram"): 8,
    ("/memory@40000000", "lca_reserved_mem"): 16,
    ("/memory@40000000", "mblock_info"): 22552,
    ("/memory@40000000", "orig_dram_info"): 72,
    ("/memory@40000000", "tee_reserved_mem"): 16,
}
ANDROID_PROPERTY_LENGTHS = {
    "compatible": 17,
    "hardware": 7,
    "mode": 7,
    "opt_c2k_lte_mode": 2,
    "opt_c2k_support": 2,
    "opt_eccci_c2k": 2,
    "opt_irat_support": 2,
    "opt_lte_support": 2,
    "opt_md1_support": 3,
    "opt_md3_support": 2,
    "opt_ps1_rat": 14,
    "opt_using_default": 2,
    "serialno": 17,
}
MBLOCK_NODES = {
    "/reserved-memory/mblock-1-log-store": ("mediatek,log-store", False),
    "/reserved-memory/mblock-2-atf-log-reserved": (
        "mediatek,atf-log-reserved",
        True,
    ),
    "/reserved-memory/mblock-3-framebuffer": ("mediatek,framebuffer", True),
    "/reserved-memory/mblock-4-SCP-reserved": ("mediatek,SCP-reserved", True),
    "/reserved-memory/mblock-5-ccci": ("mediatek,ccci", True),
    "/reserved-memory/mblock-6-ccci": ("mediatek,ccci", False),
    "/reserved-memory/mblock-7-ccci": ("mediatek,ccci", False),
}


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_inputs() -> tuple[ModuleType, ModuleType]:
    script = pathlib.Path(__file__).resolve()
    candidate = script.with_name("candidate_an.py")
    require_regular(candidate, "Candidate AN identity module")
    identity = load_module(candidate, "candidate_an_live_fdt_identity")
    parser = (
        script.parents[2]
        / "2026-07-16-lk-handoff-alignment"
        / "scripts"
        / "validate-lk-compatible-dtb.py"
    )
    require_regular(parser, "source-pinned FDT parser")
    if digest(parser) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    return identity, load_module(parser, "candidate_an_live_fdt_parser")


def cstring(value: bytes, label: str) -> None:
    if (
        not value
        or not value.endswith(b"\0")
        or value.count(b"\0") != 1
        or any(byte < 0x20 or byte > 0x7e for byte in value[:-1])
    ):
        raise ValueError(f"{label} is not one printable NUL-terminated string")


def region(value: bytes, label: str) -> tuple[int, int]:
    if len(value) != 16:
        raise ValueError(f"{label} is not one two-cell address/size pair")
    address_hi, address_lo, size_hi, size_lo = struct.unpack(">4I", value)
    address = (address_hi << 32) | address_lo
    size = (size_hi << 32) | size_lo
    if not size or address + size > 1 << 64:
        raise ValueError(f"{label} has an invalid or overflowing range")
    return address, size


def delta(
    artifact: dict[str, dict[str, bytes]],
    live: dict[str, dict[str, bytes]],
) -> tuple[
    set[str],
    set[str],
    set[tuple[str, str]],
    set[tuple[str, str]],
    set[tuple[str, str]],
]:
    added_nodes = set(live) - set(artifact)
    removed_nodes = set(artifact) - set(live)
    added_properties: set[tuple[str, str]] = set()
    removed_properties: set[tuple[str, str]] = set()
    changed_properties: set[tuple[str, str]] = set()
    for path in set(artifact) & set(live):
        for name in set(live[path]) - set(artifact[path]):
            added_properties.add((path, name))
        for name in set(artifact[path]) - set(live[path]):
            removed_properties.add((path, name))
        for name in set(artifact[path]) & set(live[path]):
            if artifact[path][name] != live[path][name]:
                changed_properties.add((path, name))
    return (
        added_nodes,
        removed_nodes,
        added_properties,
        removed_properties,
        changed_properties,
    )


def require_exact_delta(
    artifact: dict[str, dict[str, bytes]],
    live: dict[str, dict[str, bytes]],
) -> None:
    actual = delta(artifact, live)
    expected = (
        EXPECTED_ADDED_NODES,
        EXPECTED_REMOVED_NODES,
        EXPECTED_ADDED_PROPERTIES,
        set(),
        EXPECTED_CHANGED_PROPERTIES,
    )
    labels = (
        "added node",
        "removed node",
        "added property",
        "removed property",
        "changed property",
    )
    for label, found, wanted in zip(labels, actual, expected):
        if found != wanted:
            raise ValueError(
                f"post-LK {label} inventory differs "
                f"(found={len(found)}, expected={len(wanted)})"
            )


def require_live_shapes(
    fdt: ModuleType,
    artifact: dict[str, dict[str, bytes]],
    live: dict[str, dict[str, bytes]],
) -> None:
    fdt.require_prop(
        artifact, "/", "model", fdt.string("Planet Computers Gemini PDA")
    )
    fdt.require_prop(live, "/", "model", fdt.string("MT6797X"))
    fdt.require_prop(artifact, "/scp@10020000", "status", fdt.string("disabled"))
    # Retained LK writes exactly four bytes here, without a string terminator.
    fdt.require_prop(live, "/scp@10020000", "status", b"okay")

    for (path, name), length in EXPECTED_EXISTING_PROPERTY_LENGTHS.items():
        if len(live[path][name]) != length:
            raise ValueError(f"post-LK property shape differs: {path}:{name}")
    cstring(live["/chosen"]["bootargs"], "/chosen:bootargs")
    start = struct.unpack(">I", live["/chosen"]["linux,initrd-start"])[0]
    end = struct.unpack(">I", live["/chosen"]["linux,initrd-end"])[0]
    if start >= end:
        raise ValueError("post-LK initramfs range is empty or reversed")

    android = live["/firmware/android"]
    if set(android) != set(ANDROID_PROPERTY_LENGTHS):
        raise ValueError("post-LK Android firmware metadata inventory differs")
    for name, length in ANDROID_PROPERTY_LENGTHS.items():
        if len(android[name]) != length:
            raise ValueError(f"post-LK Android firmware field shape differs: {name}")
        cstring(android[name], f"/firmware/android:{name}")
    if android["compatible"] != fdt.string("android,firmware"):
        raise ValueError("post-LK Android firmware compatible differs")
    if android["hardware"] != fdt.string("mt6797"):
        raise ValueError("post-LK Android hardware class differs")
    if android["mode"] != fdt.string("normal"):
        raise ValueError("post-LK Android boot mode differs")

    memory_start, memory_size = region(
        live["/memory@40000000"]["reg"], "/memory@40000000:reg"
    )
    memory_end = memory_start + memory_size
    added_ranges: list[tuple[int, int, str]] = []
    for path, (compatible, no_map) in MBLOCK_NODES.items():
        properties = live[path]
        wanted = {"compatible", "reg"} | ({"no-map"} if no_map else set())
        if set(properties) != wanted:
            raise ValueError(f"post-LK mblock property inventory differs: {path}")
        if properties["compatible"] != fdt.string(compatible):
            raise ValueError(f"post-LK mblock compatible differs: {path}")
        if no_map and properties["no-map"] != b"":
            raise ValueError(f"post-LK mblock no-map encoding differs: {path}")
        address, size = region(properties["reg"], f"{path}:reg")
        if address < memory_start or address + size > memory_end:
            raise ValueError(f"post-LK mblock is outside DRAM: {path}")
        added_ranges.append((address, address + size, path))

    framebuffer = region(
        live["/chosen/framebuffer@7dfb0000"]["reg"], "simplefb:reg"
    )
    if framebuffer != region(
        live["/reserved-memory/mblock-3-framebuffer"]["reg"],
        "framebuffer mblock:reg",
    ):
        raise ValueError("post-LK framebuffer reservation differs from simplefb")

    for index, (left_start, left_end, left_path) in enumerate(
        sorted(added_ranges)
    ):
        for right_start, right_end, right_path in sorted(added_ranges)[index + 1 :]:
            if left_start < right_end and right_start < left_end:
                raise ValueError(
                    f"post-LK mblock overlap: {left_path} and {right_path}"
                )

    for suffix in ("r0", "r1"):
        path = f"/reserved-memory/reserve-memory-dram_{suffix}_dummy_read"
        properties = live[path]
        if set(properties) != {
            "alignment",
            "alloc-ranges",
            "compatible",
            "size",
        }:
            raise ValueError(f"post-LK dummy-read inventory differs: {path}")
        if properties["compatible"] != fdt.string(
            f"reserve-memory-dram_{suffix}_dummy_read"
        ):
            raise ValueError(f"post-LK dummy-read compatible differs: {path}")
        if (
            len(properties["alignment"]) != 8
            or len(properties["alloc-ranges"]) != 16
            or len(properties["size"]) != 8
        ):
            raise ValueError(f"post-LK dummy-read property shape differs: {path}")


def require_observer_contract(
    fdt: ModuleType,
    artifact: dict[str, dict[str, bytes]],
    live: dict[str, dict[str, bytes]],
) -> None:
    if live[OBSERVER] != artifact[OBSERVER]:
        raise ValueError("post-LK observer node is not byte-exact Candidate AN")
    fdt.require_prop(
        live,
        OBSERVER,
        "compatible",
        fdt.string("mediatek,mt6797-dvfsp-handoff-observer"),
    )
    fdt.require_prop(live, OBSERVER, "reg", fdt.cells(0, 0x11015000, 0, 0x1000))
    fdt.require_prop(live, I2C6, "status", fdt.string("disabled"))
    if any(path.startswith(I2C6 + "/") for path in live):
        raise ValueError("post-LK I2C6 unexpectedly gained a child")
    for path in (DA9214, A72_POWER, LEGACY_DVFSP):
        if path in live:
            raise ValueError(f"post-LK forbidden active-resource node exists: {path}")
    for cpu in (CPU8, CPU9):
        fdt.require_prop(
            live, cpu, "enable-method", fdt.string("mediatek,mt6797-psci")
        )


def validate(
    artifact_path: pathlib.Path, live_path: pathlib.Path
) -> dict[str, int | str]:
    require_regular(artifact_path, "Candidate AN artifact DTB")
    require_regular(live_path, "private post-LK live FDT")
    identity, fdt = load_inputs()
    if digest(artifact_path) != identity.FINAL_DTB_SHA256:
        raise ValueError("artifact DTB is not exact Candidate AN")
    if digest(live_path) != EXPECTED_LIVE_FDT_SHA256:
        raise ValueError("private live FDT is not the audited Candidate AN capture")
    if live_path.stat().st_size != EXPECTED_LIVE_FDT_SIZE:
        raise ValueError("private live FDT size differs from its audited identity")

    artifact, artifact_reservations, artifact_boot_cpu = fdt.parse_fdt(artifact_path)
    live, live_reservations, live_boot_cpu = fdt.parse_fdt(live_path)
    if live_reservations != artifact_reservations:
        raise ValueError("LK changed the FDT header reservation map")
    if live_boot_cpu != artifact_boot_cpu:
        raise ValueError("LK changed boot_cpuid_phys")

    require_exact_delta(artifact, live)
    require_live_shapes(fdt, artifact, live)
    require_observer_contract(fdt, artifact, live)

    structural_entries = (
        len(EXPECTED_ADDED_NODES)
        + len(EXPECTED_REMOVED_NODES)
        + len(EXPECTED_ADDED_PROPERTIES)
        + len(EXPECTED_CHANGED_PROPERTIES)
    )
    return {
        "artifact_nodes": len(artifact),
        "live_nodes": len(live),
        "structural_entries": structural_entries,
        "artifact_sha256": identity.FINAL_DTB_SHA256,
        "live_sha256": EXPECTED_LIVE_FDT_SHA256,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--live", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = validate(args.artifact, args.live)
    except (OSError, RuntimeError, TypeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=candidate-an-post-lk-live-fdt-allowlisted")
    print(f"artifact_dtb_sha256={result['artifact_sha256']}")
    print(f"live_fdt_sha256={result['live_sha256']}")
    print(f"artifact_nodes={result['artifact_nodes']}")
    print(f"live_nodes={result['live_nodes']}")
    print(f"structural_delta_entries={result['structural_entries']}")
    print("added_nodes=10")
    print("removed_nodes=2")
    print("added_properties_on_existing_nodes=23")
    print("changed_properties=2")
    print("fdt_header_reservations_and_boot_cpu=unchanged")
    print("lk_dynamic_metadata=shape-validated-values-not-emitted")
    print("device_unique_serial=validated-in-memory-not-emitted")
    print("observer_node=byte-exact-pre-lk-candidate-an")
    print("i2c6=disabled-no-child")
    print("da9214_a72_power_legacy_dvfsp_nodes=absent")
    print("cpu8_cpu9_enable_method=unchanged-fail-closed")
    print("unexpected_semantic_delta=none")
    print("device_access=none")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
