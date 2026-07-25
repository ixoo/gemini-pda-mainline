#!/usr/bin/env python3
"""Immutable identities for Candidate AC's hardware-passed AB foundation."""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-21-usb-gadget-ethernet"
CANDIDATE = "AC"
MARKER = "GEMINI_USB_GADGET_ETHERNET_20260721_AC"
PROMPT = "GEMINI-AC-USB#"
BOOT2_CAPACITY = 16 * 1024 * 1024

AC_INITRAMFS_FILE = "gemini-usb-gadget-ethernet-initramfs.img"
AC_BOOT_FILE = "gemini-usb-gadget-ethernet.boot.img"
AC_DTB_FILE = "mt6797-gemini-pda-usb-gadget-ethernet.dtb"

DEVICE_INTERFACE = "usb0"
DEVICE_ADDRESS = "10.15.19.82/24"
HOST_ADDRESS = "10.15.19.1/24"
DEVICE_MAC = "42:00:15:19:82:01"
HOST_MAC = "42:00:15:19:82:00"
TCP_PORT = 2323

AB_ARTIFACT_NAME = "candidate-AB-mt6797-kernel-restart-final-61c74592"
AB_MANIFEST_SHA256 = "f7500569b83cf36e2bfcb0c7db3cef33a3c3776e85615c5719acf64e6f2accb0"

AB_BOOT_FILE = "gemini-mt6797-kernel-restart.boot.img"
AB_BOOT_SHA256 = "61c74592267466735164c19f8b831ea18db2892de95e32109f2aacd7ec5c5446"
AB_BOOT_SIZE = 7_378_944

AB_INITRAMFS_FILE = "gemini-mt6797-kernel-restart-initramfs.img"
AB_INITRAMFS_SHA256 = "b57dc3143e7ca7df90d742bcacc692221b4d7b6d346e5192d7bc68acaac00ea7"
AB_INITRAMFS_SIZE = 1_818_771

AB_IMAGE_GZ_FILE = "Image.gz"
AB_IMAGE_GZ_SHA256 = "37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f"
AB_IMAGE_GZ_SIZE = 5_529_652

AB_DTB_FILE = "mt6797-gemini-pda-kernel-restart.dtb"
AB_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
AB_DTB_SIZE = 26_259

AB_KEYMAP_FILE = "gemini-us.bkeymap"
AB_KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
AB_KEYMAP_SIZE = 2_311

AB_SYSTEM_MAP_SHA256 = "355a547d5ce17dc295d5c66760415c7a2056be1897db57d8325b303eb32c4e63"
AB_SOURCE_BUILD_SHA256 = "c672d58074bde6505e892cf94336de08e2135c6b1197e046db45d83f3551b8a5"
AB_PROVENANCE_SHA256 = "d60aae5fcb1fd12413d4c145f7270552af0fab1038ae43b58f070d8b794250ae"

# Exact executables carried by the AB artifact and its initramfs.  These are
# the same helper identities pinned by Candidate AB's own contract.
AB_KEYMAP_VERIFIER_SHA256 = "29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238"
AB_UNICODE_HELPER_SHA256 = "5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650"
AB_INPUT_HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
AB_LOCAL_SHELL_SHA256 = "2569bb4ebe8f1617e5e3c7f0885d9a487f36a4a687a663851b5f21240583047d"
AB_REBOOT_SHA256 = "3f439dbb0572b0f6f463c168d5b795dc93c9f41efd096f2154bd7f6b8524a2f7"
DISPATCH_ENV_SHA256 = "8255ad7ab034cd3d760690a8b57eebcb67c974d321249ed8ee3a4f142f53e90a"
AB_INIT_SHA256 = "c0884780dac376a4d18b34c52a2f15898026edf573b794290dd29149503bac91"
AB_X_RECORD_SHA256 = "fdd918a9a023af443dda24c2e12e1d307e583326605f190f9a00eacc4439f55e"
AB_X_PROBE_SHA256 = "f2ccbf92828f1288f2e8745c2aab273a44bad960a5323518a1b30f07214d1fcd"
AB_INITTAB_SHA256 = "48820916541c1fdb73e4d3ef294724a8606cc32abc8fea24f4b8cb7e0e679489"

# Compatibility aliases keep consumers from having to drop the AB lineage
# prefix for helper identities shared by the new candidate.
KEYMAP_SHA256 = AB_KEYMAP_SHA256
KEYMAP_VERIFIER_SHA256 = AB_KEYMAP_VERIFIER_SHA256
UNICODE_HELPER_SHA256 = AB_UNICODE_HELPER_SHA256
INPUT_HELPER_SHA256 = AB_INPUT_HELPER_SHA256

AB_EXPECTED_FILES = frozenset(
    {
        "Image.gz",
        "SHA256SUMS",
        "System.map",
        "aa-baseline-validation.txt",
        "analysis.txt",
        "ash-dispatch-validation.txt",
        "boot-validation.txt",
        "console-keymap-verify",
        "console-unicode-mode",
        AB_INITRAMFS_FILE,
        AB_BOOT_FILE,
        AB_KEYMAP_FILE,
        "initramfs-build.txt",
        "initramfs-validation.txt",
        "input-event-capture",
        "input-tree.sha256",
        AB_DTB_FILE,
        "package-foundation.txt",
        "package-validation.txt",
        "provenance.txt",
        "serializer.txt",
        "source-build.json",
    }
)
AB_EXECUTABLE_FILES = frozenset(
    {"console-keymap-verify", "console-unicode-mode", "input-event-capture"}
)

AB_INITRAMFS_DIRECTORIES = frozenset({".", "bin", "dev", "etc", "proc", "run", "sys"})
AB_INITRAMFS_SYMLINKS = {
    name: b"busybox"
    for name in (
        "bin/ash",
        "bin/cat",
        "bin/chvt",
        "bin/clear",
        "bin/init",
        "bin/mount",
        "bin/readlink",
        "bin/sh",
        "bin/sleep",
        "bin/stty",
        "bin/true",
    )
}
AB_INITRAMFS_REGULAR_MODES = {
    "bin/busybox": 0o755,
    "bin/console-keymap-verify": 0o755,
    "bin/console-unicode-mode": 0o755,
    "bin/input-event-capture": 0o755,
    "bin/local-shell": 0o755,
    "bin/reboot": 0o755,
    "bin/reboot-dispatch.env": 0o444,
    "bin/x-probe": 0o755,
    "bin/x-record": 0o755,
    "etc/gemini-us.bkeymap": 0o444,
    "etc/inittab": 0o644,
    "init": 0o755,
}
AB_INITRAMFS_EXPECTED_MEMBERS = frozenset(
    AB_INITRAMFS_DIRECTORIES
    | AB_INITRAMFS_SYMLINKS.keys()
    | AB_INITRAMFS_REGULAR_MODES.keys()
)
AB_INITRAMFS_CRITICAL = {
    "bin/busybox": (BUSYBOX_SHA256, 1_914_704),
    "bin/console-keymap-verify": (AB_KEYMAP_VERIFIER_SHA256, 537_576),
    "bin/console-unicode-mode": (AB_UNICODE_HELPER_SHA256, 537_584),
    "bin/input-event-capture": (AB_INPUT_HELPER_SHA256, 710_808),
    "bin/local-shell": (AB_LOCAL_SHELL_SHA256, 3_119),
    "bin/reboot": (AB_REBOOT_SHA256, 653),
    "bin/reboot-dispatch.env": (DISPATCH_ENV_SHA256, 27),
    "bin/x-probe": (AB_X_PROBE_SHA256, 3_468),
    "bin/x-record": (AB_X_RECORD_SHA256, 366),
    "etc/gemini-us.bkeymap": (AB_KEYMAP_SHA256, AB_KEYMAP_SIZE),
    "etc/inittab": (AB_INITTAB_SHA256, 62),
    "init": (AB_INIT_SHA256, 1_624),
}

HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_regular(
    path: pathlib.Path,
    label: str,
    mode: int | None = None,
    size: int | None = None,
) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    if mode is not None and stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f"{label} mode is not {mode:04o}")
    if size is not None and info.st_size != size:
        raise ValueError(f"{label} size is not {size}")
    data = path.read_bytes()
    if len(data) != info.st_size:
        raise ValueError(f"{label} changed while being read")
    return data
