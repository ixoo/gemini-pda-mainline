#!/usr/bin/env python3
"""Independently validate the read-only DA921x provider boot candidate."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile


PAGE = 2048
BOOT2_SIZE = 16_777_216
RAW_SIZE = 6_891_520
KERNEL_FIELD_SIZE = 4_814_197
RAMDISK_SIZE = 2_073_441
REPOSITORY_COMMIT = "7199e8229c6a805a941e33a6862956949dfebd3a"
PROFILE = "da921x-lk-clock-readonly-provider"
RELEASE = "7.1.3-gemini-da921x-lkro"
IMAGE_SHA256 = "c5d73e077165f0f22b0d8ff109661edc29763c12f4ed6fbd64b2d0fef910e1cc"
IMAGE_GZIP_SHA256 = "086d109464533194abed2c19fa56e647033edd957dafb2ee2512acd3100ed9f1"
CONFIG_SHA256 = "4ea4743024f6e8f10beeaf7db837af153d1bada99c704835143d9d5e691e9326"
SYSTEM_MAP_SHA256 = "12b760eee8c704cfd968a084d4a81a293ebeb95edbfa6504c56a2c8e14c684c1"
BUILD_JSON_SHA256 = "5732eff6428a1dbc983ed2dc096209693fef752919e13d196d8bb97701a1a82d"
PACKAGE_MANIFEST_SHA256 = "c0cb589e35ca1b49860317bd343fa0fbf195e456469b4eff3b193ecaa0fe3566"
RAMDISK_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
DTB_SHA256 = "d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48"
RAW_SHA256 = "ab86ce3950a335cc863f4d0a5921b17348cb1c184fcc69f3efa326f8ed22a321"
PADDED_SHA256 = "eeee7adea53134c8146e10591708725649a8331bdef7ad418a847b5d04c8e854"
BOOT_FILE = "gemini-mt6797-da921x-lkro-provider.boot.img"
DTB_FILE = "mt6797-gemini-pda-da921x-lkro-provider.dtb"
FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    BOOT_FILE,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    DTB_FILE,
    "dtb-validation.txt",
    "SHA256SUMS",
}
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
CPU_PROPERTIES = {"clock-frequency", "compatible", "device_type", "enable-method", "reg"}
PINCTRL = "/pinctrl@10005000"
I2C5 = "/i2c@1101c000"
AW9523 = f"{I2C5}/gpio-expander@5b"
KEYBOARD = "/keyboard-matrix"
SCP = "/scp@10020000"
WDT = "/watchdog@10007000"
TPHY = "/t-phy@11290000"
U2PORT0 = f"{TPHY}/usb-phy@11290800"
SSUSB = "/usb@11271000"
XHCI = f"{SSUSB}/usb@11270000"
I2C6 = "/i2c@1100e000"
DA921X = f"{I2C6}/regulator@68"
HANDOFF = "/dvfsp-handoff@11015000"
DEVINFO = "/firmware/atag-devinfo"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def align(value: int) -> int:
    return (value + PAGE - 1) // PAGE * PAGE


def canonical_id(kernel: bytes, ramdisk: bytes) -> bytes:
    result = hashlib.sha1(usedforsecurity=False)
    for payload in (kernel, ramdisk, b""):
        result.update(payload)
        result.update(struct.pack("<I", len(payload)))
    return result.digest()


def fdtget(dtb: Path, node: str, value_type: str, prop: str) -> str:
    return subprocess.run(
        ["fdtget", f"-t{value_type}", str(dtb), node, prop],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def properties(dtb: Path, node: str) -> set[str]:
    return set(
        subprocess.run(
            ["fdtget", "-p", str(dtb), node],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.splitlines()
    )


def children(dtb: Path, node: str) -> list[str]:
    return subprocess.run(
        ["fdtget", "-l", str(dtb), node],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.splitlines()


def require_absent(dtb: Path, node: str, prop: str) -> None:
    result = subprocess.run(
        ["fdtget", str(dtb), node, prop],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    require(result.returncode != 0, f"property must be absent: {node}/{prop}")


def validate_dtb(dtb: Path, *, pin_identity: bool = True) -> None:
    if pin_identity:
        require(digest(dtb.read_bytes()) == DTB_SHA256, "provider DT identity changed")
    require(
        children(dtb, "/cpus") == [node.rsplit("/", 1)[1] for node in CPU_CLOCKS],
        "CPU node order changed",
    )
    for node, clock in CPU_CLOCKS.items():
        require(fdtget(dtb, node, "u", "clock-frequency") == str(clock),
                f"CPU clock changed: {node}")
        require(properties(dtb, node) == CPU_PROPERTIES, f"CPU properties changed: {node}")
    require(fdtget(dtb, "/cpus/cpu@200", "s", "enable-method") == "mediatek,mt6797-psci",
            "CPU8 enable method changed")
    require(fdtget(dtb, "/cpus/cpu@201", "s", "enable-method") == "mediatek,mt6797-psci",
            "CPU9 enable method changed")

    require(fdtget(dtb, DEVINFO, "s", "compatible") == "mediatek,mt6797-atag-devinfo",
            "LK devinfo identity changed")
    require("read-only" in properties(dtb, DEVINFO), "LK devinfo lost read-only policy")
    require(children(dtb, DEVINFO) == [
        "calibration-data@0", "ptp-calibration-data@c", "cpu-efuse-identity@58"
    ], "LK devinfo cell inventory changed")
    require(fdtget(dtb, f"{DEVINFO}/ptp-calibration-data@c", "x", "reg") == "c 4c",
            "PTP cell changed")
    require(fdtget(dtb, f"{DEVINFO}/cpu-efuse-identity@58", "x", "reg") == "58 c",
            "CPU identity cell changed")
    ptp_phandle = fdtget(dtb, f"{DEVINFO}/ptp-calibration-data@c", "x", "phandle")
    cpu_id_phandle = fdtget(dtb, f"{DEVINFO}/cpu-efuse-identity@58", "x", "phandle")
    require(fdtget(dtb, HANDOFF, "s", "status") == "okay", "handoff is not enabled")
    require(fdtget(dtb, HANDOFF, "x", "nvmem-cells").split() ==
            [ptp_phandle, cpu_id_phandle], "handoff NVMEM references changed")
    require(fdtget(dtb, HANDOFF, "s", "nvmem-cell-names") ==
            "ptp-calibration-data cpu-efuse-identity", "handoff NVMEM names changed")
    handoff_phandle = fdtget(dtb, HANDOFF, "x", "phandle")
    require(fdtget(dtb, I2C6, "s", "status") == "okay", "I2C6 is not enabled")
    require(fdtget(dtb, I2C6, "x", "access-controllers") == handoff_phandle,
            "I2C6 access-controller changed")
    require(children(dtb, I2C6) == ["regulator@68"], "I2C6 child inventory changed")
    require(fdtget(dtb, DA921X, "s", "compatible") == "dlg,da9214-legacy",
            "DA921x identity changed")
    require(fdtget(dtb, DA921X, "x", "reg") == "68 69", "DA921x addresses changed")
    require(children(dtb, DA921X) == [], "DA921x gained a consumer child")

    for node in (TPHY, U2PORT0, SSUSB):
        require(fdtget(dtb, node, "s", "status") == "okay", f"USB node disabled: {node}")
    require(fdtget(dtb, SSUSB, "s", "dr_mode") == "peripheral", "USB role changed")
    require(fdtget(dtb, SSUSB, "s", "maximum-speed") == "high-speed", "USB speed changed")
    require(fdtget(dtb, XHCI, "s", "status") == "disabled", "xHCI closure changed")
    require(fdtget(dtb, SCP, "s", "status") == "disabled", "SCP closure changed")
    require_absent(dtb, WDT, "interrupts")

    i2c5_pins = fdtget(dtb, f"{PINCTRL}/i2c5-pins", "x", "phandle")
    require(fdtget(dtb, I2C5, "s", "status") == "okay", "I2C5 is not enabled")
    require(fdtget(dtb, I2C5, "x", "clock-frequency") == "61a80", "I2C5 speed changed")
    require(fdtget(dtb, I2C5, "x", "pinctrl-0") == i2c5_pins, "I2C5 pins changed")
    require(fdtget(dtb, AW9523, "s", "status") == "okay", "AW9523 is not enabled")
    for prop in ("interrupt-parent", "interrupts", "interrupt-controller", "#interrupt-cells"):
        require_absent(dtb, AW9523, prop)
    require(fdtget(dtb, KEYBOARD, "s", "status") == "okay", "keyboard is not enabled")
    require(fdtget(dtb, KEYBOARD, "x", "poll-interval") == "14", "keyboard polling changed")
    require(fdtget(dtb, KEYBOARD, "x", "col-scan-delay-us") == "2",
            "keyboard scan delay changed")


def mutation_rejected(dtb: Path, command: list[str]) -> bool:
    with tempfile.TemporaryDirectory(prefix="gemini-da921x-lkro-mutation.") as raw:
        mutated = Path(raw) / DTB_FILE
        shutil.copyfile(dtb, mutated)
        subprocess.run(
            ["fdtput", command[0], str(mutated), *command[1:]],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            validate_dtb(mutated, pin_identity=False)
        except (AssertionError, subprocess.CalledProcessError):
            return True
    return False


def verify_manifest(candidate: Path) -> None:
    lines = (candidate / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    seen: set[str] = set()
    for line in lines:
        fields = line.split(maxsplit=1)
        require(len(fields) == 2, "malformed candidate manifest")
        expected, name = fields
        name = name.removeprefix("*").removeprefix("./")
        require(name in FILES - {"SHA256SUMS"}, "unexpected manifest member")
        require(name not in seen, "duplicate manifest member")
        seen.add(name)
        require(digest((candidate / name).read_bytes()) == expected, f"hash changed: {name}")
    require(seen == FILES - {"SHA256SUMS"}, "candidate manifest inventory changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()

    entries = list(args.candidate.iterdir())
    require({entry.name for entry in entries} == FILES, "candidate inventory changed")
    require(all(entry.is_file() and not entry.is_symlink() for entry in entries), "unsafe candidate")
    verify_manifest(args.candidate)
    require(not args.ramdisk.is_symlink(), "unsafe ramdisk")

    package_files = {
        "Image": IMAGE_SHA256,
        "Image.gz": IMAGE_GZIP_SHA256,
        "kernel.config": CONFIG_SHA256,
        "System.map": SYSTEM_MAP_SHA256,
        "provenance/build.json": BUILD_JSON_SHA256,
        "SHA256SUMS": PACKAGE_MANIFEST_SHA256,
    }
    for name, expected in package_files.items():
        require(digest((args.package / name).read_bytes()) == expected, f"package member changed: {name}")
    subprocess.run(
        ["sha256sum", "--check", "--strict", "SHA256SUMS"],
        cwd=args.package,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    provenance = json.loads((args.package / "provenance/build.json").read_bytes())
    require(provenance["repository_commit"] == REPOSITORY_COMMIT, "repository commit changed")
    require(provenance["repository_dirty"] is False, "build repository was dirty")
    require(provenance["build_profile"] == PROFILE, "profile changed")
    require(provenance["kernel_release"] == RELEASE, "release changed")

    config = (args.package / "kernel.config").read_text(encoding="ascii")
    for line in (
        "CONFIG_MODULES=y\n",
        "CONFIG_NVMEM=y\n",
        "CONFIG_NVMEM_MTK_ATAG_DEVINFO=y\n",
        "CONFIG_REGULATOR_DA9213_LEGACY=y\n",
        "CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER=y\n",
        "CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER=y\n",
        "CONFIG_MTK_MT6797_DVFSP_HANDOFF=y\n",
        "CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y\n",
        "# CONFIG_KUNIT is not set\n",
        "# CONFIG_MTK_MT6797_A72_POWER is not set\n",
        "# CONFIG_MTK_MT6797_DVFSP_RESOURCE_OWNER is not set\n",
        "# CONFIG_ARM64_MT6797_A72_CAPABILITY_PROFILE is not set\n",
    ):
        require(line in config, f"configuration gate missing: {line!r}")
    require("maxcpus=8" in config, "CPU8/CPU9 closure is absent")
    image = (args.package / "Image").read_bytes()
    image_gz = (args.package / "Image.gz").read_bytes()
    require(digest(gzip.decompress(image_gz)) == IMAGE_SHA256, "Image.gz payload changed")
    for marker in (b"GAEL-20260816-A E0", b"GAEL-20260816-A E1",
                   b"GAEL-20260816-A E2", b"GAEL-20260816-A E3"):
        require(image.count(marker) == 1, f"entry-ledger marker not unique: {marker!r}")
    system_map = (args.package / "System.map").read_text(encoding="ascii")
    require("ffff8000808e1000 T __idmap_text_start\n" in system_map, "idmap start changed")
    require("ffff8000808e1fb8 T __idmap_text_end\n" in system_map, "idmap end changed")

    dtb = args.candidate / DTB_FILE
    validate_dtb(dtb)
    dtb_validation = (args.candidate / "dtb-validation.txt").read_text(encoding="ascii")
    for line in (
        "validation=mainline-da921x-readonly-provider-dtb\n",
        "package_CPU_clock_properties=10\n",
        "postbuild_CPU_clock_mutations=0\n",
        "LK_devinfo_NVMEM=read-only\n",
        "I2C6_access_controller=preserved\n",
        "DA921x_consumers=0\n",
        "DA921x_register_data_writes_expected=0\n",
        "CPU8_CPU9_admission=closed\n",
        "result=pass\n",
    ):
        require(line in dtb_validation, f"DT validation gate missing: {line!r}")

    mutations = (
        ["-d", "/cpus/cpu@0", "clock-frequency"],
        ["-ts", SSUSB, "dr_mode", "host"],
        ["-ts", XHCI, "status", "okay"],
        ["-d", I2C6, "access-controllers"],
        ["-c", f"{DA921X}/regulators"],
        ["-d", DEVINFO, "read-only"],
        ["-ts", I2C5, "status", "disabled"],
        ["-tx", AW9523, "interrupts", "0", "a", "8"],
        ["-ts", KEYBOARD, "status", "disabled"],
        ["-tx", WDT, "interrupts", "0", "89", "2"],
        ["-ts", SCP, "status", "okay"],
        ["-ts", DA921X, "compatible", "dlg,da9213-legacy"],
    )
    require(all(mutation_rejected(dtb, list(mutation)) for mutation in mutations),
            "a negative DT mutation escaped validation")

    ramdisk = args.ramdisk.read_bytes()
    require(digest(ramdisk) == RAMDISK_SHA256, "serviceability ramdisk changed")
    raw = (args.candidate / BOOT_FILE).read_bytes()
    padded = (args.candidate / "boot2-padded.img").read_bytes()
    require(len(raw) == RAW_SIZE and digest(raw) == RAW_SHA256, "raw candidate changed")
    require(len(padded) == BOOT2_SIZE and digest(padded) == PADDED_SHA256,
            "padded candidate changed")
    require(padded[:len(raw)] == raw and not any(padded[len(raw):]), "padding changed")
    require(raw[:8] == b"ANDROID!", "Android-v0 magic changed")
    fields = struct.unpack_from("<10I", raw, 8)
    require(fields == (KERNEL_FIELD_SIZE, 0x40200000, RAMDISK_SIZE, 0x45000000,
                       0, 0x40F00000, 0x44000000, PAGE, 0, 0),
            "Android-v0 fields changed")
    require(raw[48:64].split(b"\0", 1)[0] == b"gemini-lkro", "LK name changed")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(cmdline == b"bootopt=64S3,32N2,64N2", "LK command line changed")
    require(not any(raw[596:PAGE]), "header padding changed")
    kernel = image_gz + dtb.read_bytes()
    require(len(kernel) == KERNEL_FIELD_SIZE, "kernel field size changed")
    kernel_offset = PAGE
    ramdisk_offset = align(kernel_offset + len(kernel))
    require(raw[kernel_offset:kernel_offset + len(kernel)] == kernel, "kernel/DT changed")
    require(not any(raw[kernel_offset + len(kernel):ramdisk_offset]), "kernel padding changed")
    require(raw[ramdisk_offset:ramdisk_offset + len(ramdisk)] == ramdisk, "ramdisk changed")
    require(not any(raw[ramdisk_offset + len(ramdisk):]), "ramdisk padding changed")
    require(raw[576:596] == canonical_id(kernel, ramdisk), "canonical image ID changed")

    analysis = (args.candidate / "container-analysis.txt").read_text(encoding="ascii")
    require(analysis.count("gate_") == 32, "LK gate count changed")
    require(analysis.count("=yes\n") >= 32, "an LK gate failed")
    require("lk_validation=passed\n" in analysis, "LK validation did not pass")
    candidate_provenance = (args.candidate / "provenance.txt").read_text(encoding="ascii")
    for line in (
        "DA921x_register_data_writes_expected=0\n",
        "DA921x_provider_operations=get_voltage_sel,list_voltage,is_enabled\n",
        "cpu8_cpu9_admission=closed\n",
        "boot_candidate=pending-independent-validation\n",
    ):
        require(line in candidate_provenance, f"candidate provenance gate missing: {line!r}")

    print("validation=mainline-da921x-readonly-provider-candidate")
    print("kernel_release=7.1.3-gemini-da921x-lkro")
    print("LK_gates=32-of-32")
    print("package_CPU_clock_properties=10")
    print("postbuild_CPU_clock_mutations=0")
    print("LK_devinfo_NVMEM=read-only")
    print("I2C6_access_controller=preserved")
    print("DA921x_consumers=0")
    print("DA921x_register_data_writes_expected=0")
    print("CPU8_CPU9_admission=closed")
    print("negative_DT_mutations_rejected=12")
    print("runtime_hardware_write=AW9523-serviceability-probe-and-keyboard-only")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
