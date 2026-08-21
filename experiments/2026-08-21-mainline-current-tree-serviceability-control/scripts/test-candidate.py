#!/usr/bin/env python3
"""Independently validate the current-tree serviceability-control candidate."""

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
KERNEL_FIELD_SIZE = 4_818_388
RAMDISK_SIZE = 2_073_441
REPOSITORY_COMMIT = "27622dfea13e042bd82f036c50664d3b978aee11"
PROFILE = "da921x-current-service-control"
RELEASE = "7.1.3-gemini-service-ctl"
IMAGE_SHA256 = "cae4361ad7cd4b2515526ff2b11863e4ff1eb8ea788a23cb24409795049c5483"
IMAGE_GZIP_SHA256 = "9aa5c9ae497314b7ab089ccf6aa7d2cf1bb2ae9239145456603f08439829a9d6"
CONFIG_SHA256 = "fdba1a02f7592febcbf18fc4c32f7edfe8da48d355241109d79901e37a4dd21b"
SYSTEM_MAP_SHA256 = "39db10ecee35252b5f81fcb52b730f39a30268f6574bed12f55a45e77b92d090"
BUILD_JSON_SHA256 = "7b9d852ad6b4dd524c16ac99878c00dc18ccb6075b49a093706ba61f017ff2a8"
PACKAGE_MANIFEST_SHA256 = "1f59307bdce806bb1576a87266adad1393bcd4512240483ff2cb51848cc98760"
RAMDISK_SHA256 = "e0dffa04a621f60903cf4cf7280d773ec1c89c43ea63ec0f8b3a0879e7cebc0f"
DTB_SHA256 = "b638674b9be209219d51b7dd02538f7a0bc8b402bab7336188cb95011cd912dd"
RAW_SHA256 = "691ff883f05158c9a62d6629befef93f54ba14e51ff4ed5d8ea97678f2fa5094"
PADDED_SHA256 = "7084f2ee87af103dfcf1dfad9956f54c2a9df8d37b5f6d0388ba45464d8d52a3"
BOOT_FILE = "gemini-mt6797-current-service-control.boot.img"
FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    BOOT_FILE,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "SHA256SUMS",
}
CPU_CLOCKS = {
    "/cpus/cpu@0": "1391000000",
    "/cpus/cpu@1": "1391000000",
    "/cpus/cpu@2": "1391000000",
    "/cpus/cpu@3": "1391000000",
    "/cpus/cpu@100": "1950000000",
    "/cpus/cpu@101": "1950000000",
    "/cpus/cpu@102": "1950000000",
    "/cpus/cpu@103": "1950000000",
    "/cpus/cpu@200": "2288000000",
    "/cpus/cpu@201": "2288000000",
}
TPHY = "/t-phy@11290000"
U2PORT0 = f"{TPHY}/usb-phy@11290800"
SSUSB = "/usb@11271000"
XHCI = f"{SSUSB}/usb@11270000"
I2C5 = "/i2c@1101c000"
AW9523 = f"{I2C5}/gpio-expander@5b"
KEYBOARD = "/keyboard-matrix"
I2C6 = "/i2c@1100e000"
DA921X = f"{I2C6}/regulator@68"
HANDOFF = "/dvfsp-handoff@11015000"
DEVINFO = "/firmware/atag-devinfo"
CLOCK_BACKEND = "/dvfsp-clock-backend@1001a000"
BIGIDVFSP_BACKEND = "/dvfsp-bigidvfs-backend"
RAM_CONSOLE = "/ram-console"
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
        ["fdtget", f"-t{value_type}", str(dtb), node, prop],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


def children(dtb: Path, node: str) -> list[str]:
    return subprocess.run(
        ["fdtget", "-l", str(dtb), node],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.splitlines()


def absent(dtb: Path, node: str, prop: str) -> bool:
    return subprocess.run(
        ["fdtget", str(dtb), node, prop],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).returncode != 0


def validate_dtb(dtb: Path, *, pin_identity: bool) -> None:
    if pin_identity:
        require(digest(dtb.read_bytes()) == DTB_SHA256, "DTB identity changed")
    for node, expected in CPU_CLOCKS.items():
        require(
            fdtget(dtb, node, "u", "clock-frequency") == expected,
            f"CPU clock changed: {node}",
        )
    properties = subprocess.run(
        ["fdtget", "-p", str(dtb), DEVINFO],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.splitlines()
    require("read-only" in properties, "devinfo read-only policy changed")
    require(fdtget(dtb, HANDOFF, "s", "status") == "okay", "handoff disabled")
    require(
        fdtget(dtb, HANDOFF, "s", "reg-names") == "cspm scp-cfg devapc-ao",
        "handoff register names changed",
    )
    require(
        fdtget(dtb, HANDOFF, "x", "reg")
        == "0 11015000 0 1000 0 100a0000 0 1000 0 1000e000 0 1000",
        "handoff register windows changed",
    )
    handoff = fdtget(dtb, HANDOFF, "x", "phandle")
    require(fdtget(dtb, I2C6, "s", "status") == "okay", "I2C6 disabled")
    require(
        fdtget(dtb, I2C6, "x", "access-controllers") == handoff,
        "I2C6 access controller changed",
    )
    require(children(dtb, I2C6) == ["regulator@68"], "I2C6 children changed")
    require(
        fdtget(dtb, DA921X, "s", "compatible") == "dlg,da9214-legacy",
        "DA921x compatible changed",
    )
    require(fdtget(dtb, DA921X, "x", "reg") == "68 69", "DA921x addresses changed")
    require(children(dtb, DA921X) == [], "DA921x gained consumers")
    for node in (TPHY, U2PORT0, SSUSB):
        require(fdtget(dtb, node, "s", "status") == "okay", f"USB disabled: {node}")
    require(fdtget(dtb, SSUSB, "s", "dr_mode") == "peripheral", "USB role changed")
    require(fdtget(dtb, SSUSB, "s", "maximum-speed") == "high-speed", "USB speed changed")
    require(fdtget(dtb, XHCI, "s", "status") == "disabled", "xHCI enabled")
    require(fdtget(dtb, SCP, "s", "status") == "disabled", "SCP enabled")
    require(absent(dtb, WDT, "interrupts"), "watchdog IRQ returned")
    require(fdtget(dtb, I2C5, "s", "status") == "okay", "I2C5 disabled")
    require(fdtget(dtb, AW9523, "s", "status") == "okay", "AW9523 disabled")
    for prop in ("interrupt-parent", "interrupts", "interrupt-controller", "#interrupt-cells"):
        require(absent(dtb, AW9523, prop), f"AW9523 interrupt property returned: {prop}")
    require(fdtget(dtb, KEYBOARD, "s", "status") == "okay", "keyboard disabled")
    require(fdtget(dtb, KEYBOARD, "x", "poll-interval") == "14", "keyboard polling changed")
    require(fdtget(dtb, KEYBOARD, "x", "col-scan-delay-us") == "2", "keyboard delay changed")
    require(
        fdtget(dtb, CLOCK_BACKEND, "s", "status") == "disabled",
        "clock backend enabled",
    )
    require(
        fdtget(dtb, BIGIDVFSP_BACKEND, "s", "status") == "disabled",
        "BigiDVFS backend enabled",
    )
    require(fdtget(dtb, RAM_CONSOLE, "s", "status") == "disabled", "ram-console enabled")
    require(
        all("protected-readback" not in name for name in children(dtb, "/")),
        "protected-readback observer returned",
    )


def mutation_rejected(dtb: Path, mutation: list[str]) -> bool:
    with tempfile.TemporaryDirectory(prefix="gemini-service-control-dtb-mutation.") as raw:
        changed = Path(raw) / "mutated.dtb"
        shutil.copyfile(dtb, changed)
        subprocess.run(
            ["fdtput", mutation[0], str(changed), *mutation[1:]],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
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
        require(
            name in FILES - {"SHA256SUMS"} and name not in seen,
            "candidate manifest inventory changed",
        )
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
    parser.add_argument("--dtb", type=Path, required=True)
    args = parser.parse_args()

    require(
        {path.name for path in args.candidate.iterdir()} == FILES,
        "candidate inventory changed",
    )
    verify_manifest(args.candidate)
    package_files = {
        "Image": IMAGE_SHA256,
        "Image.gz": IMAGE_GZIP_SHA256,
        "kernel.config": CONFIG_SHA256,
        "System.map": SYSTEM_MAP_SHA256,
        "provenance/build.json": BUILD_JSON_SHA256,
        "SHA256SUMS": PACKAGE_MANIFEST_SHA256,
    }
    for name, expected in package_files.items():
        path = args.package / name
        require(path.is_file() and not path.is_symlink(), f"unsafe package member: {name}")
        require(digest(path.read_bytes()) == expected, f"package member changed: {name}")
    subprocess.run(
        ["sha256sum", "--check", "--strict", "SHA256SUMS"],
        cwd=args.package,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    build = json.loads((args.package / "provenance/build.json").read_bytes())
    require(build["repository_commit"] == REPOSITORY_COMMIT, "commit changed")
    require(build["repository_dirty"] is False, "Buildbox checkout was dirty")
    require(
        build["build_profile"] == PROFILE and build["kernel_release"] == RELEASE,
        "profile or release changed",
    )
    require(build["target_architecture"] == "arm64", "target architecture changed")
    require(build["build_architecture"] == "x86_64", "Buildbox architecture changed")
    require(build["modules_built"] is False, "module package policy changed")

    config = (args.package / "kernel.config").read_text(encoding="ascii")
    for line in (
        "CONFIG_MODULES=y\n",
        "CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y\n",
        "CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y\n",
        "# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set\n",
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_ATTESTATION=y\n",
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW=y\n",
        "CONFIG_NVMEM_MTK_ATAG_DEVINFO=y\n",
        "CONFIG_CMDLINE_FORCE=y\n",
        "CONFIG_LOCALVERSION=\"-gemini-service-ctl\"\n",
        "CONFIG_NR_CPUS=512\n",
        "# CONFIG_MTK_MT6797_A72_POWER is not set\n",
        "# CONFIG_MTK_MT6797_A72_PLATFORM_STATE is not set\n",
        "# CONFIG_REGULATOR_DA9211 is not set\n",
        "# CONFIG_KUNIT is not set\n",
    ):
        require(config.count(line) == 1, f"configuration gate changed: {line!r}")
    for symbol in (
        "MTK_MT6797_DVFSP_CLOCK_BACKEND",
        "MTK_MT6797_DVFSP_BIGIDVFS_BACKEND",
        "MTK_MT6797_PROTECTED_READBACK_OBSERVER",
        "PSTORE_GEMINI_PROTECTED_READBACK_LEDGER",
        "PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER",
        "PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER",
    ):
        require(f"CONFIG_{symbol}=y\n" not in config, f"forbidden configuration enabled: {symbol}")
    require("maxcpus=8" in config, "CPU8/CPU9 command-line closure is absent")

    image = (args.package / "Image").read_bytes()
    image_gz = (args.package / "Image.gz").read_bytes()
    require(gzip.decompress(image_gz) == image, "Image.gz does not reproduce Image")
    for marker in (
        b"GAEL-20260816-A E0",
        b"GAEL-20260816-A E1",
        b"GAEL-20260816-A E2",
        b"GAEL-20260816-A E3",
    ):
        require(image.count(marker) == 1, f"entry marker changed: {marker!r}")
    for forbidden in (b"GEMINI_CLOCK_BACKEND_ENTRY_LEDGER_V1", b"run-same-value-write-20260819-a"):
        require(forbidden not in image, f"forbidden Image token returned: {forbidden!r}")
    system_map = (args.package / "System.map").read_text(encoding="ascii")
    require(" T __idmap_text_start\n" in system_map, "idmap start missing")
    require(" T __idmap_text_end\n" in system_map, "idmap end missing")
    for forbidden in ("same_value", "clock_backend", "protected_readback", "bigidvfs"):
        require(forbidden not in system_map.lower(), f"forbidden symbol returned: {forbidden}")

    require(args.dtb.is_file() and not args.dtb.is_symlink(), "unsafe DTB")
    validate_dtb(args.dtb, pin_identity=True)
    mutations = (
        ["-d", "/cpus/cpu@0", "clock-frequency"],
        ["-ts", SSUSB, "dr_mode", "host"],
        ["-ts", XHCI, "status", "okay"],
        ["-d", I2C6, "access-controllers"],
        ["-c", f"{DA921X}/regulators"],
        ["-d", DEVINFO, "read-only"],
        ["-ts", I2C5, "status", "disabled"],
        ["-ts", SCP, "status", "okay"],
        ["-ts", HANDOFF, "reg-names", "cspm", "scp-cfg", "wrong"],
        ["-tx", HANDOFF, "reg", "0", "11015000", "0", "1000"],
        ["-ts", CLOCK_BACKEND, "status", "okay"],
        ["-ts", BIGIDVFSP_BACKEND, "status", "okay"],
        ["-ts", RAM_CONSOLE, "status", "okay"],
        ["-ts", SSUSB, "status", "disabled"],
        ["-tx", WDT, "interrupts", "0", "89", "2"],
    )
    rejected = sum(mutation_rejected(args.dtb, list(item)) for item in mutations)
    require(rejected == len(mutations), "a negative DT mutation escaped")

    require(args.ramdisk.is_file() and not args.ramdisk.is_symlink(), "unsafe ramdisk")
    ramdisk = args.ramdisk.read_bytes()
    require(digest(ramdisk) == RAMDISK_SHA256, "ramdisk changed")
    raw = (args.candidate / BOOT_FILE).read_bytes()
    padded = (args.candidate / "boot2-padded.img").read_bytes()
    require(len(raw) == RAW_SIZE and digest(raw) == RAW_SHA256, "raw candidate changed")
    require(
        len(padded) == BOOT2_SIZE and digest(padded) == PADDED_SHA256,
        "padded candidate changed",
    )
    require(padded[: len(raw)] == raw and not any(padded[len(raw) :]), "padding changed")
    require(raw[:8] == b"ANDROID!", "Android-v0 magic changed")
    fields = struct.unpack_from("<10I", raw, 8)
    require(
        fields
        == (
            KERNEL_FIELD_SIZE,
            0x40200000,
            RAMDISK_SIZE,
            0x45000000,
            0,
            0x40F00000,
            0x44000000,
            PAGE,
            0,
            0,
        ),
        "Android-v0 fields changed",
    )
    require(raw[48:64].split(b"\0", 1)[0] == b"gemini-svcctl", "LK name changed")
    cmdline = (raw[64:576] + raw[608:1632]).split(b"\0", 1)[0]
    require(cmdline == b"bootopt=64S3,32N2,64N2", "LK command line changed")
    kernel = image_gz + args.dtb.read_bytes()
    require(len(kernel) == KERNEL_FIELD_SIZE, "kernel field size changed")
    ramdisk_offset = align(PAGE + len(kernel))
    require(raw[PAGE : PAGE + len(kernel)] == kernel, "kernel/DT payload changed")
    require(not any(raw[PAGE + len(kernel) : ramdisk_offset]), "kernel padding changed")
    require(
        raw[ramdisk_offset : ramdisk_offset + len(ramdisk)] == ramdisk,
        "ramdisk payload changed",
    )
    require(raw[576:596] == canonical_id(kernel, ramdisk), "canonical image ID changed")

    analysis = (args.candidate / "container-analysis.txt").read_text(encoding="ascii")
    require(
        len([line for line in analysis.splitlines() if line.startswith("gate_")]) == 32,
        "LK gate count changed",
    )
    require(
        "lk_validation=passed\n" in analysis and "lk_validation_failures=none\n" in analysis,
        "LK validation failed",
    )
    package_validation = (args.candidate / "package-validation.txt").read_text(encoding="ascii")
    for line in (
        f"repository_commit={REPOSITORY_COMMIT}\n",
        f"profile={PROFILE}\n",
        f"kernel_release={RELEASE}\n",
        "sha256sums=passed\n",
        "result=pass\n",
    ):
        require(package_validation.count(line) == 1, f"package validation changed: {line!r}")
    provenance = (args.candidate / "provenance.txt").read_text(encoding="ascii")
    for line in (
        "register_data_writes_expected=AW9523-serviceability-probe-and-keyboard-only\n",
        "DA921x_register_data_writes_expected=0\n",
        "same_value_action_attribute_expected=absent\n",
        "protected_backend_devices_expected=absent\n",
        "cpu8_cpu9_admission=closed\n",
        "device_access=none\n",
        "hardware_write=none\n",
        "boot_candidate=pending-independent-validation\n",
    ):
        require(provenance.count(line) == 1, f"provenance gate changed: {line!r}")

    print("validation=mainline-current-tree-serviceability-control-candidate")
    print(f"kernel_release={RELEASE}")
    print("LK_gates=32-of-32")
    print(f"independent_DT_mutations_rejected={rejected}")
    print("clock_entry_writer=absent")
    print("same_value_action=absent")
    print("DA921x_register_data_writes=0")
    print("CPU8_CPU9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
