#!/usr/bin/env python3
"""Require exact AH plus only patch 0089's I2C6/DA9214 semantic delta."""

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

import candidate_al as al


I2C6 = "/i2c@1100e000"
I2C6_PINS = "/pinctrl@10005000/i2c6-pins"
DA9214 = I2C6 + "/regulator@68"
REGULATORS = DA9214 + "/regulators"
BUCKA = REGULATORS + "/BUCKA"
BUCKB = REGULATORS + "/BUCKB"
CPU8 = "/cpus/cpu@200"
CPU9 = "/cpus/cpu@201"
REJECTING_METHOD = "mediatek,mt6797-psci"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")


def load_ah_validator() -> ModuleType:
    source = (
        pathlib.Path(__file__).resolve().parents[2]
        / "2026-07-22-ad-contract-af-kernel-split/scripts/validate-dtb-delta.py"
    )
    require_regular(source, "Candidate AH DT validator")
    if digest(source) != al.AH_DTB_VALIDATOR_SHA256:
        raise ValueError("source-pinned Candidate AH DT validator changed")
    spec = importlib.util.spec_from_file_location("candidate_al_ah_dtb", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AH DT validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
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
            raise ValueError(f"invalid or duplicate phandle 0x{handle:x}")
        handles[handle] = path
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
    return "; ".join(details[:32])


def validate(ah_path: pathlib.Path, candidate_path: pathlib.Path) -> None:
    require_regular(ah_path, "exact Candidate AH DT")
    require_regular(candidate_path, "Candidate AL DT")
    if digest(ah_path) != al.AH_DTB_SHA256:
        raise ValueError("exact hardware-passed Candidate AH DT changed")

    ah_validator = load_ah_validator()
    fdt = ah_validator.load_fdt_parser()
    ah, ah_reservations, ah_boot_cpu = fdt.parse_fdt(ah_path)
    candidate, candidate_reservations, candidate_boot_cpu = fdt.parse_fdt(
        candidate_path
    )
    if candidate_reservations != ah_reservations:
        raise ValueError("Candidate AL changed AH's FDT reservation map")
    if candidate_boot_cpu != ah_boot_cpu:
        raise ValueError("Candidate AL changed AH's boot_cpuid_phys")

    fdt.require_prop(ah, I2C6, "status", fdt.string("disabled"))
    for forbidden in (
        "clock-frequency",
        "mediatek,use-push-pull",
        "pinctrl-names",
        "pinctrl-0",
    ):
        if forbidden in ah[I2C6]:
            raise ValueError(f"AH I2C6 unexpectedly has {forbidden}")
    if DA9214 in ah:
        raise ValueError("AH unexpectedly contains a DA9214 client")
    if "phandle" in ah[I2C6_PINS] or "linux,phandle" in ah[I2C6_PINS]:
        raise ValueError("AH I2C6 pin group unexpectedly has a phandle")

    ah_handles = phandle_map(ah)
    expected_handles = set(range(1, al.PINCTRL_PHANDLE))
    if set(ah_handles) != expected_handles:
        raise ValueError("exact AH phandle allocation is not contiguous 0x01--0x2b")
    if al.PINCTRL_PHANDLE in ah_handles:
        raise ValueError("selected AL pinctrl phandle is already used")

    for cpu in (CPU8, CPU9):
        fdt.require_prop(
            ah, cpu, "enable-method", fdt.string(REJECTING_METHOD)
        )
    if "/a72-power@10222000" in ah:
        raise ValueError("AH unexpectedly contains an A72-power node")

    expected = copy.deepcopy(ah)
    expected[I2C6_PINS]["phandle"] = fdt.cells(al.PINCTRL_PHANDLE)
    expected[I2C6].update(
        {
            "status": fdt.string("okay"),
            "clock-frequency": fdt.cells(3_400_000),
            "mediatek,use-push-pull": b"",
            "pinctrl-names": fdt.string("default"),
            "pinctrl-0": fdt.cells(al.PINCTRL_PHANDLE),
        }
    )
    expected[DA9214] = {
        "compatible": fdt.string("dlg,da9214"),
        "reg": fdt.cells(0x68),
    }
    expected[REGULATORS] = {}
    expected[BUCKA] = {"regulator-name": fdt.string("da9214-bucka")}
    expected[BUCKB] = {"regulator-name": fdt.string("vproc-big")}

    if candidate != expected:
        raise ValueError(
            "Candidate AL DT is not exact AH plus patch 0089: "
            + describe_delta(expected, candidate)
        )
    expected_map = dict(ah_handles)
    expected_map[al.PINCTRL_PHANDLE] = I2C6_PINS
    if phandle_map(candidate) != expected_map:
        raise ValueError("Candidate AL changed AH's phandle map outside I2C6 pins")
    if "/a72-power@10222000" in candidate:
        raise ValueError("Candidate AL contains forbidden A72-power node")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ah", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate(args.ah, args.candidate)
        print("validation=candidate-al-exact-ah-plus-0089-dtb")
        print(f"ah_dtb_sha256={al.AH_DTB_SHA256}")
        print(f"candidate_dtb_sha256={digest(args.candidate)}")
        print("functional_baseline=byte-exact-hardware-passed-candidate-ah")
        print("changed_existing_node=/i2c@1100e000")
        print("added_client=/i2c@1100e000/regulator@68")
        print("added_regulators=BUCKA,BUCKB")
        print("i2c6_clock_hz=3400000")
        print("i2c6_electrical_mode=push-pull")
        print("pinctrl_phandle=0x2c")
        print("existing_ah_phandles=unchanged")
        print("a72_power_node=absent")
        print("cpu8_cpu9_request=none")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, TypeError, ValueError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
