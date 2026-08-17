#!/usr/bin/env python3
"""Independently validate the LK CPU-clock iterator repair candidate."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Callable


SOURCE_VALIDATOR_SHA256 = "1b650f422147d39884a9484077e3a11efdf5ff17cb2df88ab42158b7f9c7bc71"
DTB_SHA256 = "a87558efd982007798b1c706b4df9e8048b71954423d45bbaf5fbe32515e2f14"
RAW_SHA256 = "fe22ae352abcaf72ed2f456e6946b462c4a343589698685244ef9b3b6333e9f1"
PADDED_SHA256 = "b478b79a983889514b2b8d122fb6d5ff5057e52c332882b186b82698d1de62b8"
BOOT_FILE = "gemini-mt6797-arm64-entry-ledger-lk-cpu-clocks.boot.img"
DTB_FILE = "mt6797-gemini-pda-lk-cpu-clocks.dtb"
BASE_FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    BOOT_FILE,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
}
FILES = BASE_FILES | {DTB_FILE, "dtb-validation.txt", "SHA256SUMS"}
PINCTRL = "/pinctrl@10005000"
I2C5 = "/i2c@1101c000"
AW9523 = f"{I2C5}/gpio-expander@5b"
KEYBOARD = "/keyboard-matrix"
CPU_CLOCKS = {
    "/cpus/cpu@0": 1_391_000_000,
    "/cpus/cpu@1": 1_391_000_000,
    "/cpus/cpu@2": 1_391_000_000,
    "/cpus/cpu@3": 1_391_000_000,
    "/cpus/cpu@100": 1_950_000_000,
    "/cpus/cpu@101": 1_950_000_000,
    "/cpus/cpu@102": 1_950_000_000,
    "/cpus/cpu@103": 1_950_000_000,
    "/cpus/cpu@200": 2_288_000_000,
    "/cpus/cpu@201": 2_288_000_000,
}
CPU_PROPERTIES = {
    "clock-frequency", "compatible", "device_type", "enable-method", "reg"
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_manifest(candidate: Path) -> None:
    manifest = (candidate / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    seen: set[str] = set()
    for line in manifest:
        fields = line.split(maxsplit=1)
        require(len(fields) == 2, "malformed candidate manifest")
        expected, name = fields
        name = name.removeprefix("*").removeprefix("./")
        require(name in FILES - {"SHA256SUMS"}, "unexpected manifest member")
        require(name not in seen, "duplicate manifest member")
        seen.add(name)
        require(digest((candidate / name).read_bytes()) == expected, f"hash changed: {name}")
    require(seen == FILES - {"SHA256SUMS"}, "candidate manifest inventory changed")


def derive_validator(source: str) -> str:
    replacements = (
        ("exact GAEL/Stage-27-DTB control container",
         "exact GAEL/LK CPU-clock iterator repair container", 1),
        ("RAW_SIZE = 6_879_232", "RAW_SIZE = 6_881_280", 1),
        ("KERNEL_FIELD_SIZE = 4_802_149", "KERNEL_FIELD_SIZE = 4_802_642", 1),
        ("RAW_SHA256 = \"e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086\"",
         f"RAW_SHA256 = \"{RAW_SHA256}\"", 1),
        ("PADDED_SHA256 = \"68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67\"",
         f"PADDED_SHA256 = \"{PADDED_SHA256}\"", 1),
        ("CONTROL_DTB_SHA256 = \"7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806\"",
         f"CONTROL_DTB_SHA256 = \"{DTB_SHA256}\"", 1),
        ("gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img", BOOT_FILE, 2),
        ("b\"gemini-dtbctl\"", "b\"gemini-lkclk\"", 1),
        ("Stage-27 control DTB", "LK CPU-clock DTB", 1),
        ("validation=lk-handoff-dtb-control-candidate",
         "validation=mainline-lk-cpu-clock-iterator-repair-candidate", 1),
        ("control_dtb=exact-runtime-proven-stage27",
         "lk_cpu_clock_dtb=stopped-I2C5-plus-exact-Stage27-CPU-clocks", 1),
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


def cells(dtb: Path, node: str, prop: str) -> list[str]:
    return fdtget(dtb, node, "x", prop).split()


def require_absent(dtb: Path, node: str, prop: str) -> None:
    result = subprocess.run(
        ["fdtget", str(dtb), node, prop],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(result.returncode != 0, f"property must be absent: {node}/{prop}")


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
    require(fdtget(dtb, AW9523, "s", "compatible") == "awinic,aw9523-pinctrl",
            "AW9523 identity changed")
    require(fdtget(dtb, AW9523, "x", "reg") == "5b", "AW9523 address changed")
    require(fdtget(dtb, AW9523, "x", "pinctrl-0") == keyboard_pins,
            "AW9523 SoC pins changed")
    for prop in ("interrupt-parent", "interrupts", "interrupt-controller", "#interrupt-cells"):
        require_absent(dtb, AW9523, prop)
    require(cells(dtb, AW9523, "gpio-ranges") == [aw_phandle, "0", "0", "10"],
            "AW9523 GPIO range changed")
    require(fdtget(dtb, KEYBOARD, "s", "status") == "okay", "keyboard is not enabled")
    require(fdtget(dtb, KEYBOARD, "s", "compatible") == "gpio-matrix-keypad",
            "keyboard identity changed")
    require(fdtget(dtb, KEYBOARD, "x", "poll-interval") == "14",
            "keyboard poll interval changed")
    require(fdtget(dtb, KEYBOARD, "x", "col-scan-delay-us") == "2",
            "keyboard scan delay changed")
    require(cells(dtb, KEYBOARD, "pinctrl-0") == [row_pins, col_pins],
            "keyboard pin states changed")
    rows = cells(dtb, KEYBOARD, "row-gpios")
    columns = cells(dtb, KEYBOARD, "col-gpios")
    require(len(rows) == 24 and rows[::3] == [aw_phandle] * 8, "keyboard rows changed")
    require(len(columns) == 21 and columns[::3] == [aw_phandle] * 7,
            "keyboard columns changed")


def validate_cpu_clock_contract(dtb: Path) -> None:
    cpu_names = subprocess.run(
        ["fdtget", "-l", str(dtb), "/cpus"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.splitlines()
    require(cpu_names == [node.rsplit("/", 1)[1] for node in CPU_CLOCKS],
            "CPU node order changed")
    for node, clock in CPU_CLOCKS.items():
        require(fdtget(dtb, node, "u", "clock-frequency") == str(clock),
                f"CPU clock value changed: {node}")
        properties = set(
            subprocess.run(
                ["fdtget", "-p", str(dtb), node],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.splitlines()
        )
        require(properties == CPU_PROPERTIES, f"CPU property inventory changed: {node}")


def mutation_rejected(
    dtb: Path, command: list[str], validator: Callable[[Path], None]
) -> bool:
    with tempfile.TemporaryDirectory(prefix="gemini-lk-cpu-clock-mutation.") as raw:
        mutated = Path(raw) / DTB_FILE
        shutil.copyfile(dtb, mutated)
        subprocess.run(
            ["fdtput", command[0], str(mutated), *command[1:]],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            validator(mutated)
        except (AssertionError, subprocess.CalledProcessError):
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()

    entries = list(args.candidate.iterdir())
    require({entry.name for entry in entries} == FILES, "candidate inventory changed")
    require(all(entry.is_file() and not entry.is_symlink() for entry in entries), "unsafe entry")
    verify_manifest(args.candidate)
    dtb = args.candidate / DTB_FILE
    require(digest(dtb.read_bytes()) == DTB_SHA256, "LK CPU-clock DT changed")
    validation = (args.candidate / "dtb-validation.txt").read_text(encoding="ascii")
    for line in (
        "validation=mainline-lk-cpu-clock-iterator-repair-derivation\n",
        "semantic_delta=exact-Stage27-CPU-clock-frequency-group\n",
        "CPU_clock_properties_added=10\n",
        "LK_iterator_progress_prerequisite=present\n",
        "CPU8_CPU9_admission=closed\n",
        "xhci_status=disabled\n",
        "role=peripheral\n",
        "maximum_speed=high-speed\n",
        "result=pass\n",
    ):
        require(line in validation, f"DT validation gate missing: {line!r}")

    repository = Path(__file__).resolve().parents[3]
    source_path = (
        repository
        / "experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/test-candidate.py"
    )
    source_data = source_path.read_bytes()
    require(digest(source_data) == SOURCE_VALIDATOR_SHA256, "source validator changed")
    derived = derive_validator(source_data.decode("utf-8", "strict"))
    with tempfile.TemporaryDirectory(prefix="gemini-lk-cpu-clock-validator.") as raw:
        temporary = Path(raw)
        shadow = temporary / "candidate"
        shadow.mkdir()
        manifest_lines = []
        for name in sorted(BASE_FILES):
            shutil.copyfile(args.candidate / name, shadow / name)
            manifest_lines.append(f"{digest((shadow / name).read_bytes())}  ./{name}\n")
        (shadow / "SHA256SUMS").write_text("".join(manifest_lines), encoding="ascii")
        validator = temporary / "test-candidate-derived.py"
        validator.write_text(derived, encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(validator),
                "--candidate",
                str(shadow),
                "--package",
                str(args.package),
                "--ramdisk",
                str(args.ramdisk),
                "--control-dtb",
                str(dtb),
            ],
            check=True,
        )

    validate_serviceability_contract(dtb)
    validate_cpu_clock_contract(dtb)
    serviceability_mutations = (
        ["-ts", I2C5, "status", "disabled"],
        ["-d", I2C5, "clock-frequency"],
        ["-ts", AW9523, "status", "disabled"],
        ["-tx", AW9523, "interrupts", "0", "a", "8"],
        ["-ts", KEYBOARD, "status", "disabled"],
    )
    cpu_mutations = (
        ["-d", "/cpus/cpu@0", "clock-frequency"],
        ["-d", "/cpus/cpu@100", "clock-frequency"],
        ["-d", "/cpus/cpu@200", "clock-frequency"],
        ["-tu", "/cpus/cpu@3", "clock-frequency", "1391000001"],
        ["-tu", "/cpus/cpu@201", "clock-frequency", "2288000001"],
    )
    require(all(mutation_rejected(dtb, list(m), validate_serviceability_contract)
                for m in serviceability_mutations),
            "a serviceability mutation escaped the semantic guard")
    require(all(mutation_rejected(dtb, list(m), validate_cpu_clock_contract)
                for m in cpu_mutations),
            "an LK CPU-clock mutation escaped the semantic guard")
    provenance = (args.candidate / "provenance.txt").read_text(encoding="ascii")
    require("runtime_hypothesis=exact_Stage27_CPU_clocks_allow_LK_CPU_iterator_to_reach_Image\n"
            in provenance, "LK iterator hypothesis is absent")
    require("cpu8_cpu9_admission=closed\n" in provenance, "CPU8/9 closure is absent")
    require("register_data_writes_expected=AW9523-serviceability-probe-and-keyboard-only\n"
            in provenance, "runtime write scope is absent")
    print("lk_gates=32-of-32")
    print("negative_container_mutations_rejected=6")
    print("negative_serviceability_mutations_rejected=5")
    print("negative_CPU_clock_mutations_rejected=5")
    print("CPU_clock_properties=10-of-10-exact-Stage27-values")
    print("CPU_property_inventories=10-of-10-Stage27-match")
    print("LK_iterator_progress_prerequisite=present")
    print("CPU8_CPU9_admission=closed")
    print("candidate_manifest=passed")
    print("result=pass")


if __name__ == "__main__":
    main()
