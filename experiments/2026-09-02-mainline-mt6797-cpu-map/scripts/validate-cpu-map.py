#!/usr/bin/env python3
"""Validate the compiled MT6797 three-cluster CPU map with fdtget."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


EXPECTED = {
    "cluster0": [
        ("core0", 0x000, "arm,cortex-a53"),
        ("core1", 0x001, "arm,cortex-a53"),
        ("core2", 0x002, "arm,cortex-a53"),
        ("core3", 0x003, "arm,cortex-a53"),
    ],
    "cluster1": [
        ("core0", 0x100, "arm,cortex-a53"),
        ("core1", 0x101, "arm,cortex-a53"),
        ("core2", 0x102, "arm,cortex-a53"),
        ("core3", 0x103, "arm,cortex-a53"),
    ],
    "cluster2": [
        ("core0", 0x200, "arm,cortex-a72"),
        ("core1", 0x201, "arm,cortex-a72"),
    ],
}


def run_fdtget(
    dtb: Path, options: list[str], operands: list[str]
) -> str:
    completed = subprocess.run(
        ["fdtget", *options, str(dtb), *operands],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode:
        raise ValueError(completed.stderr.strip() or "fdtget failed")
    return completed.stdout.strip()


def children(dtb: Path, node: str) -> list[str]:
    output = run_fdtget(dtb, ["-l"], [node])
    return output.splitlines() if output else []


def prop(dtb: Path, node: str, name: str, value_type: str) -> str:
    return run_fdtget(dtb, ["-t", value_type], [node, name])


def hex_value(value: str) -> int:
    fields = value.split()
    if len(fields) != 1:
        raise ValueError(f"expected one cell, got {value!r}")
    return int(fields[0], 16)


def validate(dtb: Path) -> None:
    if not dtb.is_file():
        raise ValueError(f"not a file: {dtb}")

    map_path = "/cpus/cpu-map"
    actual_clusters = children(dtb, map_path)
    if actual_clusters != list(EXPECTED):
        raise ValueError(
            f"clusters changed: expected {list(EXPECTED)!r}, "
            f"got {actual_clusters!r}"
        )

    cpu_nodes: dict[int, tuple[str, int, str]] = {}
    for child in children(dtb, "/cpus"):
        if not child.startswith("cpu@"):
            continue
        path = f"/cpus/{child}"
        handle = hex_value(prop(dtb, path, "phandle", "x"))
        reg = hex_value(prop(dtb, path, "reg", "x"))
        compatible = prop(dtb, path, "compatible", "s")
        if handle in cpu_nodes:
            raise ValueError(f"duplicate CPU phandle {handle:#x}")
        cpu_nodes[handle] = (path, reg, compatible)

    referenced: set[int] = set()
    for cluster, expected_cores in EXPECTED.items():
        cluster_path = f"{map_path}/{cluster}"
        actual_cores = children(dtb, cluster_path)
        expected_names = [item[0] for item in expected_cores]
        if actual_cores != expected_names:
            raise ValueError(
                f"{cluster} cores changed: expected {expected_names!r}, "
                f"got {actual_cores!r}"
            )
        for core, expected_reg, expected_compatible in expected_cores:
            core_path = f"{cluster_path}/{core}"
            handle = hex_value(prop(dtb, core_path, "cpu", "x"))
            if handle in referenced:
                raise ValueError(f"CPU phandle {handle:#x} is referenced twice")
            referenced.add(handle)
            try:
                cpu_path, reg, compatible = cpu_nodes[handle]
            except KeyError as error:
                raise ValueError(
                    f"{core_path} references unknown CPU phandle {handle:#x}"
                ) from error
            if reg != expected_reg:
                raise ValueError(
                    f"{core_path} points to {cpu_path} reg {reg:#x}, "
                    f"expected {expected_reg:#x}"
                )
            if compatible != expected_compatible:
                raise ValueError(
                    f"{core_path} points to {compatible!r}, "
                    f"expected {expected_compatible!r}"
                )

    if len(referenced) != 10:
        raise ValueError(f"expected ten unique CPU references, got {len(referenced)}")
    expected_regs = {item[1] for cores in EXPECTED.values() for item in cores}
    actual_regs = {cpu_nodes[handle][1] for handle in referenced}
    if actual_regs != expected_regs:
        raise ValueError("referenced CPU register set changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dtb", type=Path)
    args = parser.parse_args()
    try:
        validate(args.dtb)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print("validation=mt6797-cpu-map")
    print("clusters=0-3,4-7,8-9")
    print("unique_cpu_references=10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
