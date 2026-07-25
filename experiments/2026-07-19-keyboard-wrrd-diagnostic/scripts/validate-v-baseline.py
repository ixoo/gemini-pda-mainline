#!/usr/bin/env python3
"""Fail-closed validation of the exact Candidate V baseline artifact."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import shutil
import stat
import subprocess
import sys


BASELINE_BASENAME = "candidate-V-keyboard-watchdog-final-9ef0ee8d"
MANIFEST_SHA256 = "0ab8291fef437cc4d2cc2b415852d21e6ccfb9deff67e8bec41b4dbfc8068ef9"
BOOT_SHA256 = "9ef0ee8dc1eb49752f9cf8f60b247b9b85e4fd2a9f090473f1d91848114087b0"
DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
INITRAMFS_SHA256 = (
    "9382288385b50fed67b47ae494609f4ee9d314cfac0257c738e33e86094508b6"
)
HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
ANALYSIS_SHA256 = "32eac681d106df0ce84d914137c2f0b5dcce5087d8b65c9f310f3d845fb5ce91"
IMAGE_GZ_SHA256 = (
    "69095483a984eb05a94e5ae212aeeb87cc3ffbded2d753f09f89661972ed89a3"
)
BOOT_SIZE = 6_864_896
INITRAMFS_SIZE = 1_306_797
DTB_SIZE = 26_259

BOOT_NAME = "gemini-keyboard-watchdog.boot.img"
DTB_NAME = "mt6797-gemini-pda-keyboard-watchdog.dtb"
INITRAMFS_NAME = "gemini-keyboard-watchdog-initramfs.img"
HELPER_NAME = "input-event-capture"
ANALYSIS_NAME = "analysis.txt"

EXPECTED_INVENTORY = frozenset(
    {
        ANALYSIS_NAME,
        "boot-validation.txt",
        "dtb-build.txt",
        "dtb-validation.txt",
        INITRAMFS_NAME,
        BOOT_NAME,
        "helper-build.txt",
        "initramfs-build.txt",
        "initramfs-validation.txt",
        HELPER_NAME,
        "input-tree.sha256",
        DTB_NAME,
        "package-foundation.txt",
        "package-validation.txt",
        "polling-patch.txt",
        "provenance.txt",
        "serializer.txt",
        "source-build.json",
    }
)
MANIFEST_LINE = re.compile(r"^([0-9a-f]{64})  \./([A-Za-z0-9][A-Za-z0-9._-]*)$")

FRAMEBUFFER = "/chosen/framebuffer@7dfb0000"
RAMOOPS = "/reserved-memory/ramoops@44410000"
OLD_RAMOOPS = "/reserved-memory/memory@44410000"
WATCHDOG = "/watchdog@10007000"
PINCTRL = "/pinctrl@10005000"
I2C5_PINS = f"{PINCTRL}/i2c5-pins"
I2C5_BUS_PINS = f"{I2C5_PINS}/pins-bus"
KEYBOARD_PINS = f"{PINCTRL}/keyboard-soc-pins"
RESET_PINS = f"{KEYBOARD_PINS}/pins-reset"
IRQ_PINS = f"{KEYBOARD_PINS}/pins-irq"
I2C5 = "/i2c@1101c000"
AW9523 = f"{I2C5}/gpio-expander@5b"
ROW_PINS = f"{AW9523}/keyboard-matrix-row-pins"
COL_PINS = f"{AW9523}/keyboard-matrix-col-pins"
MATRIX = "/keyboard-matrix"


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_exact_file(
    path: pathlib.Path, expected_sha256: str, expected_size: int | None = None
) -> None:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required regular file is missing: {path.name}")
    if expected_size is not None and path.stat().st_size != expected_size:
        raise ValueError(f"unexpected size for {path.name}")
    if digest(path) != expected_sha256:
        raise ValueError(f"unexpected SHA-256 for {path.name}")


def validate_manifest(baseline: pathlib.Path) -> None:
    manifest = baseline / "SHA256SUMS"
    require_exact_file(manifest, MANIFEST_SHA256)
    listed: dict[str, str] = {}
    for number, line in enumerate(
        manifest.read_text(encoding="ascii").splitlines(), start=1
    ):
        match = MANIFEST_LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"malformed SHA256SUMS line {number}")
        checksum, relative = match.groups()
        if relative in listed:
            raise ValueError(f"duplicate SHA256SUMS entry: {relative}")
        listed[relative] = checksum
    if frozenset(listed) != EXPECTED_INVENTORY:
        raise ValueError("Candidate V SHA256SUMS inventory is not exact")

    children = list(baseline.iterdir())
    for child in children:
        mode = child.lstat().st_mode
        if child.is_symlink() or not stat.S_ISREG(mode):
            raise ValueError(f"unexpected non-regular artifact entry: {child.name}")
    actual = {child.name for child in children if child.name != "SHA256SUMS"}
    if actual != EXPECTED_INVENTORY:
        raise ValueError("Candidate V on-disk inventory is not exact")
    for relative, expected in listed.items():
        if digest(baseline / relative) != expected:
            raise ValueError(f"SHA256SUMS verification failed: {relative}")


def parse_key_values(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="ascii").splitlines(), 1):
        if "=" not in line:
            raise ValueError(f"malformed analysis line {number}")
        key, value = line.split("=", 1)
        if not key or key in values:
            raise ValueError(f"duplicate or empty analysis key at line {number}")
        values[key] = value
    return values


def validate_android_v0_analysis(path: pathlib.Path) -> None:
    require_exact_file(path, ANALYSIS_SHA256)
    values = parse_key_values(path)
    expected = {
        "kernel_size": "5553796",
        "kernel_addr": "1075838976",
        "ramdisk_size": str(INITRAMFS_SIZE),
        "ramdisk_addr": "1157627904",
        "second_size": "0",
        "second_addr": "1089470464",
        "tags_addr": "1140850688",
        "page_size": "2048",
        "dt_size": "0",
        "unused": "0",
        "image_size": str(BOOT_SIZE),
        "image_sha256": BOOT_SHA256,
        "image_layout_size": str(BOOT_SIZE),
        "image_layout_exact": "yes",
        "payload_padding_zero": "yes",
        "kernel_gzip_magic": "yes",
        "gzip_error": "none",
        "gzip_eof": "yes",
        "gzip_unconsumed_tail_size": "0",
        "name": "gemini-obs-L",
        "cmdline": "bootopt=64S3,32N2,64N2",
        "canonical_sha1_id_matches": "yes",
        "id_padding_zero": "yes",
        "header_padding_zero": "yes",
        "appended_dtb_size": str(DTB_SIZE),
        "appended_dtb_sha256": DTB_SHA256,
        "expected_dtb_sha256": DTB_SHA256,
        "expected_dtb_matches": "yes",
        "expected_image_gz_sha256": IMAGE_GZ_SHA256,
        "expected_image_gz_matches": "yes",
        "expected_ramdisk_sha256": INITRAMFS_SHA256,
        "expected_ramdisk_matches": "yes",
        "expected_name": "gemini-obs-L",
        "expected_name_matches": "yes",
        "expected_cmdline": "bootopt=64S3,32N2,64N2",
        "expected_cmdline_matches": "yes",
        "header_dt_size": "0",
        "lk_validation": "passed",
        "lk_validation_failures": "none",
        "hardware_write": "none",
    }
    for key, expected_value in expected.items():
        if values.get(key) != expected_value:
            raise ValueError(f"Candidate V Android-v0 fact changed: {key}")
    if values.get("stored_sha1_id") != values.get("computed_sha1_id"):
        raise ValueError("Candidate V Android-v0 canonical ID is inconsistent")
    gates = {key: value for key, value in values.items() if key.startswith("gate_")}
    if len(gates) != 32 or set(gates.values()) != {"yes"}:
        raise ValueError("Candidate V Android-v0 gate set is not wholly passing")


class FdtGet:
    def __init__(self, path: pathlib.Path) -> None:
        tool = shutil.which("fdtget")
        if tool is None:
            raise ValueError("fdtget is required for Candidate V DT validation")
        self.tool = tool
        self.path = path

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.tool, *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="ascii",
        )

    def _present(self, type_name: str, node: str, prop: str) -> str:
        result = self._run("-t", type_name, str(self.path), node, prop)
        if result.returncode != 0:
            raise ValueError(f"missing or invalid DT property {node}:{prop}")
        return result.stdout.strip()

    def strings(self, node: str, prop: str) -> tuple[str, ...]:
        value = self._present("s", node, prop)
        if not value:
            raise ValueError(f"empty DT string property {node}:{prop}")
        return tuple(value.split())

    def cells(self, node: str, prop: str) -> tuple[int, ...]:
        value = self._present("x", node, prop)
        tokens = value.split()
        if not tokens or any(
            re.fullmatch(r"[0-9a-fA-F]+", item) is None for item in tokens
        ):
            raise ValueError(f"invalid DT cell property {node}:{prop}")
        return tuple(int(item, 16) for item in tokens)

    def boolean(self, node: str, prop: str) -> None:
        result = self._run(str(self.path), node, prop)
        if result.returncode != 0 or result.stdout.strip():
            raise ValueError(f"missing or non-empty DT boolean {node}:{prop}")

    def properties(self, node: str) -> frozenset[str]:
        result = self._run("-p", str(self.path), node)
        if result.returncode != 0:
            raise ValueError(f"missing DT node: {node}")
        return frozenset(result.stdout.splitlines())

    def absent(self, node: str, prop: str) -> None:
        result = self._run(str(self.path), node, prop)
        if not (
            result.returncode == 1 and "FDT_ERR_NOTFOUND" in result.stderr
        ):
            raise ValueError(f"unexpected DT property present: {node}:{prop}")

    def node_absent(self, node: str) -> None:
        result = self._run("-p", str(self.path), node)
        if not (
            result.returncode == 1 and "FDT_ERR_NOTFOUND" in result.stderr
        ):
            raise ValueError(f"unexpected DT node present: {node}")


def require_properties(fdt: FdtGet, node: str, expected: set[str]) -> None:
    if fdt.properties(node) != frozenset(expected):
        raise ValueError(f"DT property inventory changed: {node}")


def validate_display_pstore_watchdog(fdt: FdtGet) -> None:
    require_properties(
        fdt,
        FRAMEBUFFER,
        {"compatible", "reg", "width", "height", "stride", "format", "clocks"},
    )
    if fdt.strings(FRAMEBUFFER, "compatible") != ("simple-framebuffer",):
        raise ValueError("Candidate V simplefb compatible changed")
    if fdt.cells(FRAMEBUFFER, "reg") != (0, 0x7DFB0000, 0, 0x1F90000):
        raise ValueError("Candidate V simplefb memory window changed")
    for prop, expected in (("width", 1080), ("height", 2160), ("stride", 4352)):
        if fdt.cells(FRAMEBUFFER, prop) != (expected,):
            raise ValueError(f"Candidate V simplefb {prop} changed")
    if fdt.strings(FRAMEBUFFER, "format") != ("a8r8g8b8",):
        raise ValueError("Candidate V simplefb format changed")
    if fdt.cells(FRAMEBUFFER, "clocks") != (3, 45, 6, 6):
        raise ValueError("Candidate V simplefb clocks changed")

    require_properties(
        fdt,
        RAMOOPS,
        {
            "compatible",
            "reg",
            "record-size",
            "console-size",
            "ftrace-size",
            "pmsg-size",
            "mem-type",
            "no-map",
        },
    )
    if fdt.strings(RAMOOPS, "compatible") != ("ramoops",):
        raise ValueError("Candidate V ramoops compatible changed")
    if fdt.cells(RAMOOPS, "reg") != (0, 0x44410000, 0, 0xE0000):
        raise ValueError("Candidate V ramoops reservation changed")
    ramoops_cells = {
        "record-size": 0x1000,
        "console-size": 0x10000,
        "ftrace-size": 0x1000,
        "pmsg-size": 0x20000,
        "mem-type": 0,
    }
    for prop, expected in ramoops_cells.items():
        if fdt.cells(RAMOOPS, prop) != (expected,):
            raise ValueError(f"Candidate V ramoops {prop} changed")
    fdt.boolean(RAMOOPS, "no-map")
    fdt.node_absent(OLD_RAMOOPS)

    require_properties(fdt, WATCHDOG, {"compatible", "reg"})
    if fdt.strings(WATCHDOG, "compatible") != (
        "mediatek,mt6797-wdt",
        "mediatek,mt6589-wdt",
    ):
        raise ValueError("Candidate V watchdog compatible changed")
    if fdt.cells(WATCHDOG, "reg") != (0, 0x10007000, 0, 0x100):
        raise ValueError("Candidate V watchdog register window changed")
    fdt.absent(WATCHDOG, "interrupts")


def validate_i2c_aw9523(fdt: FdtGet) -> None:
    require_properties(
        fdt,
        I2C5,
        {
            "compatible",
            "reg",
            "interrupts",
            "clocks",
            "clock-names",
            "clock-div",
            "#address-cells",
            "#size-cells",
            "status",
            "clock-frequency",
            "pinctrl-0",
            "pinctrl-names",
        },
    )
    if fdt.strings(I2C5, "compatible") != (
        "mediatek,mt6797-i2c",
        "mediatek,mt6577-i2c",
    ):
        raise ValueError("Candidate V I2C5 compatible changed")
    if fdt.cells(I2C5, "reg") != (
        0,
        0x1101C000,
        0,
        0x1000,
        0,
        0x11000380,
        0,
        0x80,
    ):
        raise ValueError("Candidate V I2C5 register windows changed")
    i2c_cells = {
        "interrupts": (0, 0x53, 8),
        "clocks": (3, 0x3C, 3, 0x2E),
        "clock-div": (10,),
        "#address-cells": (1,),
        "#size-cells": (0,),
        "clock-frequency": (400000,),
        "pinctrl-0": (0x2A,),
    }
    for prop, expected in i2c_cells.items():
        if fdt.cells(I2C5, prop) != expected:
            raise ValueError(f"Candidate V I2C5 {prop} changed")
    if fdt.strings(I2C5, "clock-names") != ("main", "dma"):
        raise ValueError("Candidate V I2C5 clock names changed")
    if fdt.strings(I2C5, "status") != ("okay",):
        raise ValueError("Candidate V I2C5 is not enabled")
    if fdt.strings(I2C5, "pinctrl-names") != ("default",):
        raise ValueError("Candidate V I2C5 pinctrl state changed")
    if fdt.cells(I2C5_BUS_PINS, "pinmux") != (0xF001, 0xF101):
        raise ValueError("Candidate V I2C5 bus pins changed")

    require_properties(
        fdt,
        AW9523,
        {
            "compatible",
            "reg",
            "gpio-controller",
            "#gpio-cells",
            "gpio-ranges",
            "reset-gpios",
            "status",
            "phandle",
            "pinctrl-0",
            "pinctrl-names",
        },
    )
    if fdt.strings(AW9523, "compatible") != ("awinic,aw9523-pinctrl",):
        raise ValueError("Candidate V AW9523 compatible changed")
    aw_cells = {
        "reg": (0x5B,),
        "#gpio-cells": (2,),
        "gpio-ranges": (0x28, 0, 0, 16),
        "reset-gpios": (9, 58, 0),
        "phandle": (0x28,),
        "pinctrl-0": (0x2B,),
    }
    for prop, expected in aw_cells.items():
        if fdt.cells(AW9523, prop) != expected:
            raise ValueError(f"Candidate V AW9523 {prop} changed")
    fdt.boolean(AW9523, "gpio-controller")
    if fdt.strings(AW9523, "status") != ("okay",):
        raise ValueError("Candidate V AW9523 is not enabled")
    if fdt.strings(AW9523, "pinctrl-names") != ("default",):
        raise ValueError("Candidate V AW9523 pinctrl state changed")
    for prop in (
        "interrupt-parent",
        "interrupts",
        "interrupt-controller",
        "#interrupt-cells",
    ):
        fdt.absent(AW9523, prop)
    if fdt.cells(RESET_PINS, "pinmux") != (0x3A00,):
        raise ValueError("Candidate V AW9523 reset pin changed")
    fdt.boolean(RESET_PINS, "output-high")
    if fdt.cells(IRQ_PINS, "pinmux") != (0x5701,):
        raise ValueError("Candidate V AW9523 EINT pin changed")


def validate_matrix(fdt: FdtGet) -> None:
    require_properties(
        fdt,
        MATRIX,
        {
            "compatible",
            "pinctrl-names",
            "gpio-activelow",
            "drive-inactive-cols",
            "pinctrl-0",
            "row-gpios",
            "col-gpios",
            "linux,keymap",
            "status",
            "poll-interval",
            "col-scan-delay-us",
        },
    )
    if fdt.strings(MATRIX, "compatible") != ("gpio-matrix-keypad",):
        raise ValueError("Candidate V matrix compatible changed")
    if fdt.strings(MATRIX, "status") != ("okay",):
        raise ValueError("Candidate V matrix is not enabled")
    if fdt.strings(MATRIX, "pinctrl-names") != ("default",):
        raise ValueError("Candidate V matrix pinctrl state changed")
    matrix_cells = {
        "pinctrl-0": (0x26, 0x27),
        "poll-interval": (20,),
        "col-scan-delay-us": (2,),
    }
    for prop, expected in matrix_cells.items():
        if fdt.cells(MATRIX, prop) != expected:
            raise ValueError(f"Candidate V matrix {prop} changed")
    expected_rows = tuple(value for pin in range(8) for value in (0x28, pin, 0))
    expected_cols = tuple(
        value for pin in range(8, 15) for value in (0x28, pin, 0)
    )
    if fdt.cells(MATRIX, "row-gpios") != expected_rows:
        raise ValueError("Candidate V matrix row GPIOs changed")
    if fdt.cells(MATRIX, "col-gpios") != expected_cols:
        raise ValueError("Candidate V matrix column GPIOs changed")
    fdt.boolean(MATRIX, "gpio-activelow")
    fdt.boolean(MATRIX, "drive-inactive-cols")
    fdt.absent(MATRIX, "debounce-delay-ms")

    keymap = fdt.cells(MATRIX, "linux,keymap")
    if len(keymap) != 52:
        raise ValueError("Candidate V matrix keymap size changed")
    required_keys = {
        "P": (6, 3, 25),
        "A": (2, 5, 30),
        "S": (2, 0, 31),
        "Enter": (6, 5, 28),
    }
    for label, (row, column, keycode) in required_keys.items():
        encoded = (row << 24) | (column << 16) | keycode
        matching_codes = [entry for entry in keymap if entry & 0xFFFF == keycode]
        if matching_codes != [encoded]:
            raise ValueError(f"Candidate V keymap lacks exact {label} key")

    if fdt.cells(ROW_PINS, "phandle") != (0x26,):
        raise ValueError("Candidate V matrix row pin phandle changed")
    if fdt.cells(COL_PINS, "phandle") != (0x27,):
        raise ValueError("Candidate V matrix column pin phandle changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        baseline = args.baseline.resolve(strict=True)
        if not baseline.is_dir() or baseline.name != BASELINE_BASENAME:
            raise ValueError("baseline is not the exact Candidate V artifact")
        validate_manifest(baseline)
        require_exact_file(baseline / BOOT_NAME, BOOT_SHA256, BOOT_SIZE)
        require_exact_file(baseline / DTB_NAME, DTB_SHA256, DTB_SIZE)
        require_exact_file(
            baseline / INITRAMFS_NAME, INITRAMFS_SHA256, INITRAMFS_SIZE
        )
        require_exact_file(baseline / HELPER_NAME, HELPER_SHA256)
        if not os.access(baseline / HELPER_NAME, os.X_OK):
            raise ValueError("Candidate V helper lost its executable mode")
        validate_android_v0_analysis(baseline / ANALYSIS_NAME)

        fdt = FdtGet(baseline / DTB_NAME)
        validate_display_pstore_watchdog(fdt)
        validate_i2c_aw9523(fdt)
        validate_matrix(fdt)

        print("validation=candidate-v-baseline")
        print(f"baseline={BASELINE_BASENAME}")
        print(f"manifest_sha256={MANIFEST_SHA256}")
        print(f"artifact_files={len(EXPECTED_INVENTORY)}")
        print(f"boot_sha256={BOOT_SHA256}")
        print(f"dtb_sha256={DTB_SHA256}")
        print(f"initramfs_sha256={INITRAMFS_SHA256}")
        print(f"helper_sha256={HELPER_SHA256}")
        print("android_v0=exact-layout-padding-id-addresses-and-payloads")
        print("keymap=P:25,A:30,S:31,Enter:28")
        print("simplefb=exact-retained")
        print("ramoops=exact-retained")
        print("watchdog_irq=absent")
        print("keyboard_path=i2c5-aw9523-polled-matrix")
        print("hardware_write=none")
        return 0
    except (
        OSError,
        UnicodeError,
        ValueError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
