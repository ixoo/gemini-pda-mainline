#!/usr/bin/env python3
"""Validate exact AO plus only childless, fail-closed Cassini I2C6."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True
import candidate_cassini as cc

CPU8 = "/cpus/cpu@200"
CPU9 = "/cpus/cpu@201"
REJECTING_METHOD = "mediatek,mt6797-psci"
I2C6 = "/i2c@1100e000"
FORBIDDEN = (
    I2C6 + "/regulator@68",
    I2C6 + "/regulator@69",
    I2C6 + "/da9214@68",
    I2C6 + "/da9214@69",
    "/a72-power@10222000",
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")


def load_ap_validator() -> ModuleType:
    path = (
        pathlib.Path(__file__).resolve().parents[2]
        / "2026-07-24-mt6797-dvfsp-i2c6-consumer"
        / "scripts"
        / "validate-dtb-delta.py"
    )
    regular(path, "source-pinned childless-I2C6 validator")
    if digest(path) != cc.AP_DTB_VALIDATOR_SHA256:
        raise ValueError("source-pinned childless-I2C6 validator changed")
    spec = importlib.util.spec_from_file_location("cassini_ap_dtb", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load childless-I2C6 validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(ao_path: pathlib.Path, candidate_path: pathlib.Path) -> None:
    regular(ao_path, "exact Candidate AO DT")
    regular(candidate_path, "Candidate Cassini DT")
    validator = load_ap_validator()
    validator.validate(ao_path, candidate_path)
    if digest(candidate_path) != cc.FINAL_DTB_SHA256:
        raise ValueError("Cassini childless-I2C6 DT byte identity changed")

    fdt = validator.load_fdt_parser()
    tree, _reservations, _boot_cpu = fdt.parse_fdt(candidate_path)
    if any(path.startswith(I2C6 + "/") for path in tree):
        raise ValueError("Cassini I2C6 has a child")
    for path in FORBIDDEN:
        if path in tree:
            raise ValueError(f"Cassini contains forbidden node {path}")
    for cpu in (CPU8, CPU9):
        fdt.require_prop(
            tree, cpu, "enable-method", fdt.string(REJECTING_METHOD)
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ao", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        validate(args.ao, args.candidate)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=cassini-exact-ao-plus-childless-i2c6")
    print(f"ao_dtb_sha256={cc.AO_DTB_SHA256}")
    print(f"candidate_dtb_sha256={digest(args.candidate)}")
    print("i2c6=enabled-childless")
    print("i2c6_clients=0")
    print("da9214_0x68_0x69=absent")
    print("a72_power_node=absent")
    print("cpu8_cpu9_enable_method=mediatek,mt6797-psci-fail-closed")
    print("cpu8_cpu9_activation=impossible")
    print("console_usb_keyboard_ramoops=whole-tree-exact-ao")
    print("storage_access=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
