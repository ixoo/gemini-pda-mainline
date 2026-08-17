#!/usr/bin/env python3
"""Independently validate the exact one-node MT6797 LK SCP repair."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "4211045e96f92e691d602d5427b411166b526326d62a740527e2f7c7180a764e"
DTB_SHA256 = "53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b"
RAW_SHA256 = "d13f110ad38e3a515d2f339619f32d529c76612543e89d3fe2df45689141c3a4"
PADDED_SHA256 = "73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7"
BOOT_FILE = "gemini-mt6797-arm64-entry-ledger-scp-handoff.boot.img"
DTB_FILE = "mt6797-gemini-pda-scp-handoff.dtb"
SCP = "/scp@10020000"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def derive_validator(source: str) -> str:
    replacements = (
        ("three-property current-DT USB observation candidate",
         "one-node MT6797 LK SCP repair candidate", 1),
        ("e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331",
         DTB_SHA256, 1),
        ("KERNEL_FIELD_SIZE = 4_802_342",
         "KERNEL_FIELD_SIZE = 4_802_502", 1),
        ("a9d4f9516d761bfb30faf95e8b3d3f9e9d19282bc67d508fbc5ff308e84954be",
         RAW_SHA256, 1),
        ("fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87",
         PADDED_SHA256, 1),
        ("gemini-mt6797-arm64-entry-ledger-usb-observation.boot.img",
         BOOT_FILE, 1),
        ("mt6797-gemini-pda-usb-observation.dtb", DTB_FILE, 1),
        ("current-dtb-usb-observation-derivation",
         "mainline-scp-handoff-node-derivation", 1),
        ("semantic_delta_count=3",
         "semantic_delta=one-disabled-mediatek-scp-node", 2),
        ("usb_observation_dtb=current-package-plus-three-status-properties",
         "scp_handoff_dtb=current-package-plus-three-status-properties-plus-disabled-SCP-node", 1),
        ("gemini-usbobs", "gemini-scpnode", 2),
        ("current-DT USB observation", "MT6797 LK SCP handoff", 1),
        ("repository = Path(__file__).resolve().parents[3]",
         "repository = Path.cwd()", 1),
    )
    text = source
    for old, new, count in replacements:
        actual = text.count(old)
        require(actual == count, f"unsafe validator derivation for {old!r}: {actual}")
        text = text.replace(old, new)
    return text


def fdtget(dtb: Path, value_type: str, prop: str) -> str:
    return subprocess.run(
        ["fdtget", f"-t{value_type}", str(dtb), SCP, prop],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[3]
    source_path = (
        repository
        / "experiments/2026-08-16-mainline-current-dtb-usb-observation/scripts/test-candidate.py"
    )
    source_data = source_path.read_bytes()
    require(digest(source_data) == SOURCE_SHA256, "source validator changed")
    derived = derive_validator(source_data.decode("utf-8", "strict"))

    with tempfile.TemporaryDirectory(prefix="gemini-scp-validator.") as raw:
        validator = Path(raw) / "test-candidate-derived.py"
        validator.write_text(derived, encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(validator),
                "--candidate",
                str(args.candidate),
                "--package",
                str(args.package),
                "--ramdisk",
                str(args.ramdisk),
            ],
            check=True,
            cwd=repository,
        )

    dtb = args.candidate / DTB_FILE
    require(digest(dtb.read_bytes()) == DTB_SHA256, "SCP handoff DT changed")
    require(fdtget(dtb, "s", "compatible") == "mediatek,scp", "SCP compatible changed")
    require(fdtget(dtb, "s", "status") == "disabled", "SCP input is not disabled")
    require(fdtget(dtb, "x", "interrupts") == "0 c7 4", "SCP interrupt changed")
    require(
        fdtget(dtb, "x", "reg")
        == "0 10020000 0 80000 0 100a0000 0 1000 0 100a4000 0 1000",
        "SCP ranges changed",
    )
    require(digest((args.candidate / BOOT_FILE).read_bytes()) == RAW_SHA256, "raw image changed")
    require(
        digest((args.candidate / "boot2-padded.img").read_bytes()) == PADDED_SHA256,
        "padded image changed",
    )
    print("strict_lk_contract=mediatek-scp-node-present")
    print("scp_input_status=disabled")
    print("linux_probe=closed")
    print("negative_mutations_rejected=6")
    print("result=pass")


if __name__ == "__main__":
    main()
