#!/usr/bin/env python3
"""Independently validate the one-property watchdog IRQ isolation candidate."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "0d6cfc40065c067d8fc1d3e77b714a6e8bf2d58521d301b140cbede5b1d0ad39"
DTB_SHA256 = "49d8189b3801c2e95345857ff704ab0b819001c55101f16dd1949cfa5106d3aa"
RAW_SHA256 = "21cd418951922852c0628d451e52d3a8df032c304e03037195738c41232676d2"
PADDED_SHA256 = "b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d"
BOOT_FILE = "gemini-mt6797-arm64-entry-ledger-wdt-noirq.boot.img"
DTB_FILE = "mt6797-gemini-pda-wdt-noirq.dtb"
WDT = "/watchdog@10007000"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def derive_validator(source: str) -> str:
    replacements = (
        ("one-node MT6797 LK SCP repair candidate",
         "one-property watchdog IRQ isolation candidate", 1),
        ("53ceeaddcae13ff10ddc219441ac46a300324e5490e436626601f0d928c1558b",
         DTB_SHA256, 1),
        ("KERNEL_FIELD_SIZE = 4_802_502",
         "KERNEL_FIELD_SIZE = 4_802_478", 1),
        ("d13f110ad38e3a515d2f339619f32d529c76612543e89d3fe2df45689141c3a4",
         RAW_SHA256, 1),
        ("73be76fd4eb26d6d1d718bb4c0a77653839ca40e00267a5a35defb5b8a45b0f7",
         PADDED_SHA256, 1),
        ("gemini-mt6797-arm64-entry-ledger-scp-handoff.boot.img",
         BOOT_FILE, 1),
        ("mt6797-gemini-pda-scp-handoff.dtb", DTB_FILE, 1),
        ("mainline-scp-handoff-node-derivation",
         "mainline-wdt-irq-isolation-derivation", 1),
        ("semantic_delta=one-disabled-mediatek-scp-node",
         "semantic_delta=delete-watchdog-interrupts-property-only", 1),
        ("scp_handoff_dtb=current-package-plus-three-status-properties-plus-disabled-SCP-node",
         "wdt_noirq_dtb=stopped-predecessor-minus-watchdog-interrupts", 1),
        ("gemini-scpnode", "gemini-wdtnoirq", 1),
        ("MT6797 LK SCP handoff", "watchdog IRQ isolation", 1),
        ("repository = Path(__file__).resolve().parents[3]\n    source_path = (",
         "repository = Path.cwd()\n    source_path = (", 1),
    )
    text = source
    for old, new, count in replacements:
        actual = text.count(old)
        require(actual == count, f"unsafe validator derivation for {old!r}: {actual}")
        text = text.replace(old, new)
    return text


def fdtget(dtb: Path, value_type: str, prop: str) -> str:
    return subprocess.run(
        ["fdtget", f"-t{value_type}", str(dtb), WDT, prop],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout.strip()


def require_no_irq(dtb: Path) -> None:
    result = subprocess.run(
        ["fdtget", "-tx", str(dtb), WDT, "interrupts"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(result.returncode != 0, "watchdog interrupt was restored")


def validate_wdt_contract(dtb: Path) -> None:
    require(
        fdtget(dtb, "s", "compatible")
        == "mediatek,mt6797-wdt mediatek,mt6589-wdt",
        "watchdog compatible changed",
    )
    require(fdtget(dtb, "x", "reg") == "0 10007000 0 100", "watchdog range changed")
    require(fdtget(dtb, "x", "#reset-cells") == "1", "watchdog reset cells changed")
    require_no_irq(dtb)


def mutation_rejected(dtb: Path, prop: str, values: list[str]) -> bool:
    with tempfile.TemporaryDirectory(prefix="gemini-wdt-mutation.") as raw:
        mutated = Path(raw) / DTB_FILE
        shutil.copyfile(dtb, mutated)
        subprocess.run(
            ["fdtput", "-tx", str(mutated), WDT, prop, *values],
            check=True,
            stdout=subprocess.PIPE,
        )
        try:
            validate_wdt_contract(mutated)
        except AssertionError:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[3]
    source_path = (
        repository
        / "experiments/2026-08-16-mainline-scp-handoff-node/scripts/test-candidate.py"
    )
    source_data = source_path.read_bytes()
    require(digest(source_data) == SOURCE_SHA256, "source validator changed")
    derived = derive_validator(source_data.decode("utf-8", "strict"))

    with tempfile.TemporaryDirectory(prefix="gemini-wdt-validator.") as raw:
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
    require(digest(dtb.read_bytes()) == DTB_SHA256, "watchdog isolation DT changed")
    validate_wdt_contract(dtb)
    require(
        mutation_rejected(dtb, "interrupts", ["0", "89", "2"]),
        "restored watchdog interrupt escaped the semantic guard",
    )
    require(
        mutation_rejected(dtb, "#reset-cells", ["2"]),
        "changed watchdog reset cells escaped the semantic guard",
    )
    require(digest((args.candidate / BOOT_FILE).read_bytes()) == RAW_SHA256, "raw image changed")
    require(
        digest((args.candidate / "boot2-padded.img").read_bytes()) == PADDED_SHA256,
        "padded image changed",
    )
    print("watchdog_irq=absent")
    print("watchdog_reset_cells=1")
    print("negative_mutations_rejected=2")
    print("result=pass")


if __name__ == "__main__":
    main()
