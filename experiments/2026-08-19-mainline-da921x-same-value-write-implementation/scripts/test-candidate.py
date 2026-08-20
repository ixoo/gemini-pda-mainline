#!/usr/bin/env python3
"""Independently validate the exact Gate-6 same-value-write candidate."""

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
RAW_SIZE = 6_895_616
KERNEL_FIELD_SIZE = 4_818_736
RAMDISK_SIZE = 2_073_441
REPOSITORY_COMMIT = "7c012d736f78898be08bfd8430a25c8708a62e1d"
PROFILE = "da921x-same-value-write"
RELEASE = "7.1.3-gemini-da921x-same-write"
IMAGE_SHA256 = "595056ac4cee9ff0a5b79287dca18bdc24f48374ffa7a3ef2647a0255cf1773c"
IMAGE_GZIP_SHA256 = "9327bd97af0ef8b2470c6eb769b0f96b562b855d4049289d3e0890c2739a5b29"
CONFIG_SHA256 = "61590965540ad27624b64c8906a58f87d36ed15821e769f5ec93871f39695614"
SYSTEM_MAP_SHA256 = "321606b03dbeff1facfe8c9fa1404550457458eb862320054d0e1d823b8a91b2"
BUILD_JSON_SHA256 = "4c39328d8a75d173ac262ba07159064d1069a0d1097964a23a48aaef40e19bd2"
PACKAGE_MANIFEST_SHA256 = "e6932a0803b69071b64fc7c4a4ec8fa98c08112eec1e06f2c48a039c54ec5e20"
RAMDISK_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
DTB_SHA256 = "d7dba05efa272c8264c8ea15c776fb88c21a0012603214b49dfd9e2893e87d48"
RAW_SHA256 = "b84f3ba8d86ea9f1b34234794e71be786853da7d1942ce755b175f6c7289509d"
PADDED_SHA256 = "b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22"
BOOT_FILE = "gemini-mt6797-da921x-same-value-write.boot.img"
DTB_FILE = "mt6797-gemini-pda-da921x-same-value-write.dtb"
FILES = {
    "boot2-padded.img", "container-analysis.txt", BOOT_FILE,
    "package-validation.txt", "provenance.txt", "serializer.txt", DTB_FILE,
    "dtb-validation.txt", "SHA256SUMS",
}
CPU_CLOCKS = {
    "/cpus/cpu@0": "1391000000", "/cpus/cpu@1": "1391000000",
    "/cpus/cpu@2": "1391000000", "/cpus/cpu@3": "1391000000",
    "/cpus/cpu@100": "1950000000", "/cpus/cpu@101": "1950000000",
    "/cpus/cpu@102": "1950000000", "/cpus/cpu@103": "1950000000",
    "/cpus/cpu@200": "2288000000", "/cpus/cpu@201": "2288000000",
}
I2C5 = "/i2c@1101c000"
AW9523 = f"{I2C5}/gpio-expander@5b"
KEYBOARD = "/keyboard-matrix"
I2C6 = "/i2c@1100e000"
DA921X = f"{I2C6}/regulator@68"
HANDOFF = "/dvfsp-handoff@11015000"
DEVINFO = "/firmware/atag-devinfo"
SSUSB = "/usb@11271000"
XHCI = f"{SSUSB}/usb@11270000"
SCP = "/scp@10020000"
WDT = "/watchdog@10007000"


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
        ["fdtget", f"-t{value_type}", str(dtb), node, prop], check=True,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.strip()


def children(dtb: Path, node: str) -> list[str]:
    return subprocess.run(
        ["fdtget", "-l", str(dtb), node], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.splitlines()


def absent(dtb: Path, node: str, prop: str) -> bool:
    return subprocess.run(
        ["fdtget", str(dtb), node, prop], check=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).returncode != 0


def validate_dtb(dtb: Path, *, pin_identity: bool) -> None:
    if pin_identity:
        require(digest(dtb.read_bytes()) == DTB_SHA256, "DTB identity changed")
    for node, expected in CPU_CLOCKS.items():
        require(fdtget(dtb, node, "u", "clock-frequency") == expected,
                f"CPU clock changed: {node}")
    properties = subprocess.run(
        ["fdtget", "-p", str(dtb), DEVINFO], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout.splitlines()
    require("read-only" in properties, "devinfo read-only policy changed")
    handoff = fdtget(dtb, HANDOFF, "x", "phandle")
    require(fdtget(dtb, HANDOFF, "s", "status") == "okay", "handoff disabled")
    require(fdtget(dtb, I2C6, "s", "status") == "okay", "I2C6 disabled")
    require(fdtget(dtb, I2C6, "x", "access-controllers") == handoff,
            "I2C6 access controller changed")
    require(children(dtb, I2C6) == ["regulator@68"], "I2C6 children changed")
    require(fdtget(dtb, DA921X, "s", "compatible") == "dlg,da9214-legacy",
            "DA921x compatible changed")
    require(fdtget(dtb, DA921X, "x", "reg") == "68 69", "DA921x addresses changed")
    require(children(dtb, DA921X) == [], "DA921x gained consumers")
    require(fdtget(dtb, SSUSB, "s", "status") == "okay", "USB disabled")
    require(fdtget(dtb, SSUSB, "s", "dr_mode") == "peripheral", "USB role changed")
    require(fdtget(dtb, XHCI, "s", "status") == "disabled", "xHCI enabled")
    require(fdtget(dtb, SCP, "s", "status") == "disabled", "SCP enabled")
    require(absent(dtb, WDT, "interrupts"), "watchdog IRQ returned")
    require(fdtget(dtb, I2C5, "s", "status") == "okay", "I2C5 disabled")
    require(fdtget(dtb, AW9523, "s", "status") == "okay", "AW9523 disabled")
    require(absent(dtb, AW9523, "interrupts"), "AW9523 IRQ returned")
    require(fdtget(dtb, KEYBOARD, "s", "status") == "okay", "keyboard disabled")
    require(fdtget(dtb, KEYBOARD, "x", "poll-interval") == "14",
            "keyboard polling changed")


def mutation_rejected(dtb: Path, mutation: list[str]) -> bool:
    with tempfile.TemporaryDirectory(prefix="gemini-same-value-dtb-mutation.") as raw:
        changed = Path(raw) / DTB_FILE
        shutil.copyfile(dtb, changed)
        subprocess.run(["fdtput", mutation[0], str(changed), *mutation[1:]], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            validate_dtb(changed, pin_identity=False)
        except (AssertionError, subprocess.CalledProcessError):
            return True
    return False


def verify_manifest(candidate: Path) -> None:
    lines = (candidate / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    seen: set[str] = set()
    for line in lines:
        expected, name = line.split(maxsplit=1)
        name = name.removeprefix("*").removeprefix("./")
        require(name in FILES - {"SHA256SUMS"} and name not in seen,
                "candidate manifest inventory changed")
        path = candidate / name
        require(path.is_file() and not path.is_symlink(), "unsafe candidate member")
        require(digest(path.read_bytes()) == expected, f"candidate hash changed: {name}")
        seen.add(name)
    require(seen == FILES - {"SHA256SUMS"}, "candidate manifest is incomplete")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()

    require({path.name for path in args.candidate.iterdir()} == FILES,
            "candidate inventory changed")
    verify_manifest(args.candidate)
    package_files = {
        "Image": IMAGE_SHA256, "Image.gz": IMAGE_GZIP_SHA256,
        "kernel.config": CONFIG_SHA256, "System.map": SYSTEM_MAP_SHA256,
        "provenance/build.json": BUILD_JSON_SHA256,
        "SHA256SUMS": PACKAGE_MANIFEST_SHA256,
    }
    for name, expected in package_files.items():
        require(digest((args.package / name).read_bytes()) == expected,
                f"package member changed: {name}")
    subprocess.run(["sha256sum", "--check", "--strict", "SHA256SUMS"],
                   cwd=args.package, check=True, stdout=subprocess.PIPE,
                   stderr=subprocess.PIPE)
    build = json.loads((args.package / "provenance/build.json").read_bytes())
    require(build["repository_commit"] == REPOSITORY_COMMIT, "commit changed")
    require(build["repository_dirty"] is False, "Buildbox checkout was dirty")
    require(build["build_profile"] == PROFILE and build["kernel_release"] == RELEASE,
            "profile or release changed")
    require(build["target_architecture"] == "arm64", "target architecture changed")

    config = (args.package / "kernel.config").read_text(encoding="ascii")
    for line in (
        "CONFIG_MODULES=y\n", "CONFIG_NVMEM=y\n",
        "CONFIG_NVMEM_MTK_ATAG_DEVINFO=y\n",
        "CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y\n",
        "CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y\n",
        "CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE=y\n",
        "# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set\n",
        "# CONFIG_KUNIT is not set\n", "# CONFIG_MTK_MT6797_A72_POWER is not set\n",
        "# CONFIG_MTK_MT6797_DVFSP_RESOURCE_OWNER is not set\n",
    ):
        require(config.count(line) == 1, f"configuration gate changed: {line!r}")
    require("SAME_VALUE_WRITE_KUNIT_TEST=y" not in config, "KUnit trigger leaked")
    require("maxcpus=8" in config, "CPU8/CPU9 closure is absent")

    image = (args.package / "Image").read_bytes()
    image_gz = (args.package / "Image.gz").read_bytes()
    require(digest(gzip.decompress(image_gz)) == IMAGE_SHA256, "Image.gz changed")
    for marker in (b"GAEL-20260816-A E0", b"GAEL-20260816-A E1",
                   b"GAEL-20260816-A E2", b"GAEL-20260816-A E3"):
        require(image.count(marker) == 1, f"entry marker changed: {marker!r}")
    system_map = (args.package / "System.map").read_text(encoding="ascii")
    require("ffff8000808e2000 T __idmap_text_start\n" in system_map,
            "idmap start changed")
    require("ffff8000808e2fb8 T __idmap_text_end\n" in system_map,
            "idmap end changed")

    dtb = args.candidate / DTB_FILE
    validate_dtb(dtb, pin_identity=True)
    mutations = (
        ["-d", "/cpus/cpu@0", "clock-frequency"],
        ["-ts", SSUSB, "dr_mode", "host"], ["-ts", XHCI, "status", "okay"],
        ["-d", I2C6, "access-controllers"], ["-c", f"{DA921X}/regulators"],
        ["-d", DEVINFO, "read-only"], ["-ts", I2C5, "status", "disabled"],
        ["-ts", SCP, "status", "okay"],
    )
    require(all(mutation_rejected(dtb, list(item)) for item in mutations),
            "a negative DT mutation escaped")

    ramdisk = args.ramdisk.read_bytes()
    require(digest(ramdisk) == RAMDISK_SHA256, "ramdisk changed")
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
    require(raw[48:64].split(b"\0", 1)[0] == b"gemini-da921x-w", "LK name changed")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(cmdline == b"bootopt=64S3,32N2,64N2", "LK command line changed")
    kernel = image_gz + dtb.read_bytes()
    require(len(kernel) == KERNEL_FIELD_SIZE, "kernel field size changed")
    ramdisk_offset = align(PAGE + len(kernel))
    require(raw[PAGE:PAGE + len(kernel)] == kernel, "kernel/DT payload changed")
    require(not any(raw[PAGE + len(kernel):ramdisk_offset]), "kernel padding changed")
    require(raw[ramdisk_offset:ramdisk_offset + len(ramdisk)] == ramdisk,
            "ramdisk payload changed")
    require(raw[576:596] == canonical_id(kernel, ramdisk), "canonical image ID changed")

    analysis = (args.candidate / "container-analysis.txt").read_text(encoding="ascii")
    require(len([line for line in analysis.splitlines() if line.startswith("gate_")]) == 32,
            "LK gate count changed")
    require("lk_validation=passed\n" in analysis and "lk_validation_failures=none\n" in analysis,
            "LK validation failed")
    provenance = (args.candidate / "provenance.txt").read_text(encoding="ascii")
    for line in (
        "DA921x_register_data_writes_expected=1-exact-0xda-0x46\n",
        "DA921x_runtime_operations=identity-reads,provider-reads,one-shot-same-value-write-with-readbacks\n",
        "I2C6_ledger_pretrigger_entries=20\n", "I2C6_ledger_posttrigger_entries=32\n",
        "I2C6_ledger_capacity=32\n", "cpu8_cpu9_admission=closed\n",
        "boot_candidate=pending-independent-validation\n",
    ):
        require(provenance.count(line) == 1, f"provenance gate changed: {line!r}")

    print("validation=mainline-da921x-same-value-write-candidate")
    print(f"kernel_release={RELEASE}")
    print("LK_gates=32-of-32")
    print("independent_DT_mutations_rejected=8")
    print("payload=0xda,0x46")
    print("action_transfers=12")
    print("CPU8_CPU9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
