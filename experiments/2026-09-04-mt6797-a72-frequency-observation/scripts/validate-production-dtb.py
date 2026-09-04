#!/usr/bin/env python3
"""Independently validate the exact production DT and both allowed deltas."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys


TOPOLOGY_SHA256 = "4b05758f0aa04fb6aeb91e69bed7224fbe411d9d5fe671ff167214725c32f923"
THERMAL_SOURCE_SHA256 = "2f0a9a424d75f3042cabcb54fce0518133deb89a065d5671b87fce287b8cc91a"
PACKAGE_DTB_SHA256 = "df70033883ae3dc7bee7d3af42e7d1677573c153c24fc295b9b79d919f8722a3"
RECORD_JSON_SHA256 = "1cb788595e9af5aa977882308c82938b5d1c1848ae323f4b840172d0994598db"
OUTPUT_SHA256 = "46be0ae62bf66bf8e9f905ec3ad5eebbdc51c79ff3dc21859077ebe3f1aec363"
PARSER_SHA256 = "b76e7fa49f6f02c948a7563613c502d67ef287f0cba0db224d17f312427fe438"
CPU_MAP_VALIDATOR_SHA256 = "99495d59d047f312f416076b788014a64d267cbe4bf899a59d0120d5dd22d7c5"
NODE = "/chosen/gemini-late-cpu-provenance"
THERMAL = "/thermal@1100b000"
ZONE_ROOT = "/thermal-zones"
ZONE = "/thermal-zones/soc-thermal"


class DtbError(ValueError):
    """Production DT validation failed."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path, expected: str, name: str):
    if digest(path) != expected:
        raise DtbError(f"pinned validation source changed: {path}")
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise DtbError(f"cannot load pinned validation source: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def validate(args: argparse.Namespace) -> None:
    inputs = (
        (args.topology_dtb, TOPOLOGY_SHA256, "topology DT"),
        (args.thermal_overlay, THERMAL_SOURCE_SHA256, "thermal overlay source"),
        (args.package_dtb, PACKAGE_DTB_SHA256, "package DT"),
        (args.record_json, RECORD_JSON_SHA256, "package A41 record"),
        (args.candidate, OUTPUT_SHA256, "production DT"),
    )
    for path, expected, label in inputs:
        if not path.is_file() or path.is_symlink() or digest(path) != expected:
            raise DtbError(f"{label} identity changed")

    repository = Path(__file__).resolve().parents[3]
    parser_source = repository / (
        "experiments/2026-08-30-mainline-a72-provenance-serviceability-"
        "composition/scripts/validate-composed-dtb.py"
    )
    parser = load_module(parser_source, PARSER_SHA256,
                         "a72_provenance_parser")
    cpu_map_path = repository / (
        "experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/"
        "validate-cpu-map.py"
    )
    load_module(cpu_map_path, CPU_MAP_VALIDATOR_SHA256,
                "mt6797_cpu_map_validator").validate(args.candidate)

    base, base_reservations, base_boot_cpu = parser.parse_fdt(args.topology_dtb)
    package, _, _ = parser.parse_fdt(args.package_dtb)
    actual, actual_reservations, actual_boot_cpu = parser.parse_fdt(args.candidate)
    record = json.loads(args.record_json.read_text(encoding="ascii"))
    expected_leaf = parser.expected_record(record)
    if NODE in base or any(path.startswith(NODE + "/") for path in base):
        raise DtbError("topology base already contains package provenance")
    if package.get(NODE) != expected_leaf:
        raise DtbError("package DT leaf does not match package record")
    if any(path.startswith(NODE + "/") for path in package):
        raise DtbError("package provenance leaf gained a child")

    expected = copy.deepcopy(base)
    expected["/"]["model"] = b"Planet Computers Gemini PDA (thermal serviceability)\0"
    expected[THERMAL]["phandle"] = struct.pack(">I", 0x1C)
    expected[THERMAL]["resets"] = struct.pack(">II", 3, 0)
    expected[THERMAL]["status"] = b"okay\0"
    expected[ZONE_ROOT] = {}
    expected[ZONE] = {
        "polling-delay-passive": struct.pack(">I", 0),
        "polling-delay": struct.pack(">I", 1000),
        "thermal-sensors": struct.pack(">I", 0x1C),
    }
    expected[NODE] = expected_leaf
    if actual != expected:
        details: list[str] = []
        for path in sorted(set(expected) | set(actual)):
            if path not in expected:
                details.append(f"unexpected node {path}")
            elif path not in actual:
                details.append(f"missing node {path}")
            else:
                for prop in sorted(set(expected[path]) | set(actual[path])):
                    if expected[path].get(prop) != actual[path].get(prop):
                        details.append(f"changed property {path}:{prop}")
        raise DtbError("DT delta escaped thermal plus provenance: " +
                       "; ".join(details[:16]))
    if actual_reservations != base_reservations or actual_boot_cpu != base_boot_cpu:
        raise DtbError("FDT reservation or boot-CPU metadata changed")

    phandles: list[int] = []
    for path, properties in actual.items():
        for name in ("phandle", "linux,phandle"):
            value = properties.get(name)
            if value is None:
                continue
            if len(value) != 4:
                raise DtbError(f"malformed phandle: {path}:{name}")
            phandles.append(struct.unpack(">I", value)[0])
    if phandles.count(0x1C) != 1 or len(phandles) != len(set(phandles)):
        raise DtbError("thermal phandle is absent or collides")
    if any(path.startswith("/__symbols__") for path in actual):
        raise DtbError("overlay symbols leaked into production DT")

    exact = (
        ("/usb@11271000", "status", b"okay\0"),
        ("/t-phy@11290000", "status", b"okay\0"),
        ("/t-phy@11290000/usb-phy@11290800", "status", b"okay\0"),
        ("/keyboard-matrix", "status", b"okay\0"),
        ("/mmc@11230000", "status", b"okay\0"),
        ("/pwrap@1000d000", "resets", struct.pack(">II", 3, 0x40)),
        ("/a72-platform-state@10222000", "status", b"okay\0"),
        (THERMAL, "nvmem-cell-names", b"calibration-data\0"),
        (THERMAL, "status", b"okay\0"),
    )
    for path, name, value in exact:
        if actual.get(path, {}).get(name) != value:
            raise DtbError(f"required serviceability property changed: {path}:{name}")
    calibration = "/firmware/atag-devinfo/calibration-data@0"
    if actual[THERMAL].get("nvmem-cells") != actual[calibration].get("phandle"):
        raise DtbError("thermal calibration reference changed")
    if actual.get("/adc@11001000", {}).get("status") != b"disabled\0":
        raise DtbError("standalone AUXADC unexpectedly enabled")

    blob = args.candidate.read_bytes()
    for compatible in (
        b"mediatek,mt6797-a72-platform-state",
        b"mediatek,mt6797-a72-admission-controller",
        b"mediatek,mt6797-a72-binder",
    ):
        if blob.count(compatible) != 1:
            raise DtbError(f"lifecycle compatible count changed: {compatible!r}")
    if blob.count(b"planet,gemini-a72-runtime-binding-v1") != 1:
        raise DtbError("package provenance compatible count changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--topology-dtb", type=Path, required=True)
    parser.add_argument("--thermal-overlay", type=Path, required=True)
    parser.add_argument("--package-dtb", type=Path, required=True)
    parser.add_argument("--record-json", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    args = parser.parse_args()
    try:
        validate(args)
    except (DtbError, KeyError, OSError, ValueError,
            subprocess.CalledProcessError) as error:
        parser.error(str(error))
    print("validation=mt6797-a72-frequency-thermal-production-dtb-independent")
    print(f"candidate_dtb_sha256={OUTPUT_SHA256}")
    print("dt_delta=exact-thermal-transform-plus-one-package-provenance-leaf")
    print("cpu_topology=4+4+2")
    print("thermal_phandle=0x1c-unique")
    print("thermal_zone=one-policy-free")
    print("usb_keyboard_emmc_pwrap=preserved")
    print("a72_lifecycle_nodes=preserved")
    print("package_provenance=exact")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
