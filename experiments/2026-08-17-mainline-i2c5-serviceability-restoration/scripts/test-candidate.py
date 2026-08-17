#!/usr/bin/env python3
"""Independently validate the coherent I2C5 serviceability candidate."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "73f6ddea964b0c0ca945184bf19a2572049d4ff576dac5220c55b08b63a3decd"
DTB_SHA256 = "a6b76ffc352e818d90709712a372c583ee275baf5f06ebf2cd11f593022b429c"
RAW_SHA256 = "e115127db5b4e2bbcf8e5fa12ebf5f8da88f8e87c76712605181160fa7b6917c"
PADDED_SHA256 = "8d04c2c7e9c67dcd17189422d1968e416eb9eec304e2b9300b83f48dc9e0ebb5"
BOOT_FILE = "gemini-mt6797-arm64-entry-ledger-i2c5-serviceability.boot.img"
DTB_FILE = "mt6797-gemini-pda-i2c5-serviceability.dtb"
PINCTRL = "/pinctrl@10005000"
I2C5 = "/i2c@1101c000"
AW9523 = f"{I2C5}/gpio-expander@5b"
KEYBOARD = "/keyboard-matrix"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def derive_validator(source: str) -> str:
    replacements = (
        ("one-property watchdog IRQ isolation candidate",
         "coherent I2C5 serviceability restoration candidate", 2),
        ("49d8189b3801c2e95345857ff704ab0b819001c55101f16dd1949cfa5106d3aa",
         DTB_SHA256, 1),
        ("KERNEL_FIELD_SIZE = 4_802_478", "KERNEL_FIELD_SIZE = 4_802_482", 1),
        ("21cd418951922852c0628d451e52d3a8df032c304e03037195738c41232676d2",
         RAW_SHA256, 1),
        ("b103dd6dbe46caba7a635efb744885b66bfde7c0ef7ea538e93644dc6bf1169d",
         PADDED_SHA256, 1),
        ("gemini-mt6797-arm64-entry-ledger-wdt-noirq.boot.img", BOOT_FILE, 1),
        ("mt6797-gemini-pda-wdt-noirq.dtb", DTB_FILE, 1),
        ("mainline-wdt-irq-isolation-derivation",
         "mainline-i2c5-serviceability-restoration-derivation", 1),
        ("semantic_delta=delete-watchdog-interrupts-property-only",
         "semantic_delta=exact-I2C5-AW9523-polling-keyboard-positive-control-group", 1),
        ("wdt_noirq_dtb=stopped-predecessor-minus-watchdog-interrupts",
         "i2c5_serviceability_dtb=stopped-predecessor-plus-positive-control-serviceability-group", 1),
        ("gemini-wdtnoirq", "gemini-i2c5svc", 1),
        ("watchdog IRQ isolation", "I2C5 serviceability restoration", 1),
        ("repository = Path(__file__).resolve().parents[3]\n    source_path = (",
         "repository = Path.cwd()\n    source_path = (", 1),
    )
    text = source
    for old, new, count in replacements:
        actual = text.count(old)
        require(actual == count, f"unsafe validator derivation for {old!r}: {actual}")
        text = text.replace(old, new)
    return text


def fdtget(dtb: Path, node: str, value_type: str, prop: str) -> str:
    return subprocess.run(
        ["fdtget", f"-t{value_type}", str(dtb), node, prop],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def require_absent(dtb: Path, node: str, prop: str) -> None:
    result = subprocess.run(
        ["fdtget", str(dtb), node, prop],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(result.returncode != 0, f"property must be absent: {node}/{prop}")


def cells(dtb: Path, node: str, prop: str) -> list[str]:
    return fdtget(dtb, node, "x", prop).split()


def validate_serviceability_contract(dtb: Path) -> None:
    i2c5_pins = fdtget(dtb, f"{PINCTRL}/i2c5-pins", "x", "phandle")
    keyboard_pins = fdtget(dtb, f"{PINCTRL}/keyboard-soc-pins", "x", "phandle")
    row_pins = fdtget(dtb, f"{AW9523}/keyboard-matrix-row-pins", "x", "phandle")
    col_pins = fdtget(dtb, f"{AW9523}/keyboard-matrix-col-pins", "x", "phandle")
    aw_phandle = fdtget(dtb, AW9523, "x", "phandle")

    require(fdtget(dtb, I2C5, "s", "status") == "okay", "I2C5 is not enabled")
    require(fdtget(dtb, I2C5, "x", "clock-frequency") == "61a80", "I2C5 frequency changed")
    require(fdtget(dtb, I2C5, "s", "pinctrl-names") == "default", "I2C5 pinctrl name changed")
    require(fdtget(dtb, I2C5, "x", "pinctrl-0") == i2c5_pins, "I2C5 pinctrl target changed")

    require(fdtget(dtb, AW9523, "s", "status") == "okay", "AW9523 is not enabled")
    require(fdtget(dtb, AW9523, "s", "compatible") == "awinic,aw9523-pinctrl", "AW9523 identity changed")
    require(fdtget(dtb, AW9523, "x", "reg") == "5b", "AW9523 address changed")
    require(fdtget(dtb, AW9523, "x", "pinctrl-0") == keyboard_pins, "AW9523 SoC pins changed")
    for prop in ("interrupt-parent", "interrupts", "interrupt-controller", "#interrupt-cells"):
        require_absent(dtb, AW9523, prop)
    gpio_ranges = cells(dtb, AW9523, "gpio-ranges")
    require(gpio_ranges == [aw_phandle, "0", "0", "10"], "AW9523 GPIO range changed")

    require(fdtget(dtb, KEYBOARD, "s", "status") == "okay", "keyboard is not enabled")
    require(fdtget(dtb, KEYBOARD, "s", "compatible") == "gpio-matrix-keypad", "keyboard identity changed")
    require(fdtget(dtb, KEYBOARD, "x", "poll-interval") == "14", "keyboard poll interval changed")
    require(fdtget(dtb, KEYBOARD, "x", "col-scan-delay-us") == "2", "keyboard scan delay changed")
    require(cells(dtb, KEYBOARD, "pinctrl-0") == [row_pins, col_pins], "keyboard pin states changed")
    row_gpios = cells(dtb, KEYBOARD, "row-gpios")
    col_gpios = cells(dtb, KEYBOARD, "col-gpios")
    require(len(row_gpios) == 24 and row_gpios[::3] == [aw_phandle] * 8, "keyboard rows changed")
    require(len(col_gpios) == 21 and col_gpios[::3] == [aw_phandle] * 7, "keyboard columns changed")


def mutation_rejected(dtb: Path, command: list[str]) -> bool:
    with tempfile.TemporaryDirectory(prefix="gemini-i2c5-mutation.") as raw:
        mutated = Path(raw) / DTB_FILE
        shutil.copyfile(dtb, mutated)
        subprocess.run(
            ["fdtput", command[0], str(mutated), *command[1:]],
            check=True,
            stdout=subprocess.PIPE,
        )
        try:
            validate_serviceability_contract(mutated)
        except (AssertionError, subprocess.CalledProcessError):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()

    repository = Path(__file__).resolve().parents[3]
    source_path = repository / "experiments/2026-08-16-mainline-wdt-irq-isolation/scripts/test-candidate.py"
    source_data = source_path.read_bytes()
    require(digest(source_data) == SOURCE_SHA256, "source validator changed")
    derived = derive_validator(source_data.decode("utf-8", "strict"))

    with tempfile.TemporaryDirectory(prefix="gemini-i2c5-validator.") as raw:
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
    require(digest(dtb.read_bytes()) == DTB_SHA256, "I2C5 serviceability DT changed")
    validate_serviceability_contract(dtb)
    mutations = (
        ["-ts", I2C5, "status", "disabled"],
        ["-d", I2C5, "clock-frequency"],
        ["-ts", AW9523, "status", "disabled"],
        ["-tx", AW9523, "interrupts", "0", "a", "8"],
        ["-ts", KEYBOARD, "status", "disabled"],
    )
    require(all(mutation_rejected(dtb, list(mutation)) for mutation in mutations),
            "a serviceability mutation escaped the semantic guard")
    provenance = (args.candidate / "provenance.txt").read_text(encoding="ascii")
    require("register_data_writes_expected=AW9523-serviceability-probe-and-keyboard-only\n" in provenance,
            "runtime write scope is absent")
    require("hardware_write=AW9523-serviceability-probe-and-keyboard-only\n" in provenance,
            "runtime hardware write scope is absent")
    require(digest((args.candidate / BOOT_FILE).read_bytes()) == RAW_SHA256, "raw image changed")
    require(digest((args.candidate / "boot2-padded.img").read_bytes()) == PADDED_SHA256,
            "padded image changed")
    print("I2C5_status=okay")
    print("AW9523_status=okay")
    print("AW9523_parent_IRQ=absent")
    print("keyboard_mode=polling")
    print("negative_serviceability_mutations_rejected=5")
    print("runtime_hardware_write=AW9523-serviceability-probe-and-keyboard-only")
    print("result=pass")


if __name__ == "__main__":
    main()
