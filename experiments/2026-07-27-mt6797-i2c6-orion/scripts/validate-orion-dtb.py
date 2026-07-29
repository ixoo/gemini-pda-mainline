#!/usr/bin/env python3
"""Require exact Hubble DT plus only Orion's standalone I2C6 compatible."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True
import candidate_orion as co


FDT_PARSER_SHA256 = (
    "444c2da04a41ce297333e3ab67f3101dc276f1a82200e7aa467971c4cc346d66"
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path: pathlib.Path, label: str) -> None:
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
    regular(source, "source-pinned FDT parser")
    if digest(source) != FDT_PARSER_SHA256:
        raise ValueError("source-pinned FDT parser changed")
    spec = importlib.util.spec_from_file_location("orion_candidate_fdt", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned FDT parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def describe_delta(
    expected: dict[str, dict[str, bytes]],
    actual: dict[str, dict[str, bytes]],
) -> str:
    details: list[str] = []
    for node in sorted(set(expected) | set(actual)):
        if node not in expected:
            details.append(f"unexpected node {node}")
            continue
        if node not in actual:
            details.append(f"missing node {node}")
            continue
        for prop in sorted(set(expected[node]) | set(actual[node])):
            if prop not in expected[node]:
                details.append(f"unexpected property {node}:{prop}")
            elif prop not in actual[node]:
                details.append(f"missing property {node}:{prop}")
            elif expected[node][prop] != actual[node][prop]:
                details.append(f"changed property {node}:{prop}")
    return "; ".join(details[:32])


def validate(hubble_path: pathlib.Path, candidate_path: pathlib.Path) -> None:
    regular(hubble_path, "exact Candidate Hubble DT")
    regular(candidate_path, "Candidate Orion DT")
    if digest(hubble_path) != co.HUBBLE_DTB_SHA256:
        raise ValueError("exact hardware-passed Hubble DT changed")

    fdt = load_fdt_parser()
    hubble, hubble_reservations, hubble_boot_cpu = fdt.parse_fdt(hubble_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(
        candidate_path
    )
    if candidate_reservations != hubble_reservations:
        raise ValueError("Orion changed Hubble's FDT reservation map")
    if candidate_boot_cpu != hubble_boot_cpu:
        raise ValueError("Orion changed Hubble's boot_cpuid_phys")

    i2c6 = co.I2C6_PATH
    fdt.require_prop(
        hubble,
        i2c6,
        "compatible",
        fdt.string("mediatek,mt6797-i2c")
        + fdt.string("mediatek,mt6577-i2c"),
    )
    expected = copy.deepcopy(hubble)
    expected[i2c6]["compatible"] = fdt.string(co.I2C6_COMPATIBLE[0])
    if candidate != expected:
        raise ValueError(
            "Orion DT is not exact Hubble plus one compatible change: "
            + describe_delta(expected, candidate)
        )

    fdt.require_prop(candidate, i2c6, "status", fdt.string("okay"))
    if "access-controllers" not in candidate[i2c6]:
        raise ValueError("Orion I2C6 lost its handoff dependency")
    if any(node.startswith(i2c6 + "/") for node in candidate):
        raise ValueError("Orion I2C6 is not childless")
    for forbidden in (
        i2c6 + "/regulator@68",
        i2c6 + "/regulator@69",
        i2c6 + "/da9214@68",
        i2c6 + "/da9214@69",
        "/a72-power@10222000",
    ):
        if forbidden in candidate:
            raise ValueError(f"Orion contains forbidden node {forbidden}")
    for cpu in ("/cpus/cpu@200", "/cpus/cpu@201"):
        fdt.require_prop(
            candidate,
            cpu,
            "enable-method",
            fdt.string("mediatek,mt6797-psci"),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hubble", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate(
            args.hubble.resolve(strict=True),
            args.candidate.resolve(strict=True),
        )
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=orion-exact-hubble-plus-standalone-i2c6-compatible")
    print(f"hubble_dtb_sha256={co.HUBBLE_DTB_SHA256}")
    print(f"candidate_dtb_sha256={digest(args.candidate)}")
    print("changed_nodes=0")
    print("changed_properties=/i2c@1100e000:compatible")
    print("i2c6_compatible=mediatek,mt6797-idvfs-i2c")
    print("i2c6=enabled-childless")
    print("da9214_a72_nodes=absent")
    print("cpu8_cpu9=fail-closed-unrequested")
    print("device_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
