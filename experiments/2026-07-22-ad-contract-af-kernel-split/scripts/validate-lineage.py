#!/usr/bin/env python3
"""Validate exact AF/AG payload lineage and the hardware-passed AD DT oracle."""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import re
import stat
import sys


AF_NAME = "candidate-AF-a72-observer-initcall-fe43efa8"
AF_MANIFEST_SHA256 = "77e311af022e067185b9c9462137cfb73bb639ef0f29d9eb946d326097636e22"
AF_BOOT_SHA256 = "fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3"
AF_DTB_SHA256 = "3f9e6d977ca1c8060ad4170bdca12eed3d40b112009b8ad93b4a08017221643b"

AG_NAME = "candidate-AG-simplefb-restoration-0552986c"
AG_MANIFEST_SHA256 = "e40e6c262a461b7514ea8a1388d3a544c6fa88a4bc0cbadf969e9da75facf95c"
AG_BOOT_SHA256 = "0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91"
AG_DTB_SHA256 = "7ea5e8f9edb09f2365a112b29359fed897f306422a26449b1cb8870bb1212512"

AD_NAME = "candidate-AD-smp8-final-a1b61d8c"
AD_MANIFEST_SHA256 = "c3aeccf2e6e18a0c4769b909ccf45a77f75cc3677fe61fbd786d0925154fc51f"
AD_BOOT_SHA256 = "a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b"
AD_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"

IMAGE_GZ_SHA256 = "b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912"
SYSTEM_MAP_SHA256 = "a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d"
CONFIG_SHA256 = "bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63"
INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
SOURCE_BUILD_SHA256 = "57ea75dd81ac7389c6a34d47cf9dc6a7300476f7ad85b00d782190585e686094"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"

EXECUTABLE_MEMBERS = {
    "console-keymap-verify",
    "console-unicode-mode",
    "input-event-capture",
}
AF_MEMBERS = {
    "Image.gz",
    "SHA256SUMS",
    "System.map",
    "analysis.txt",
    "boot-validation.txt",
    "console-keymap-verify",
    "console-unicode-mode",
    "gemini-a72-observer-initcall-diagnostic.boot.img",
    "gemini-a72-observer-initcall-diagnostic-initramfs.img",
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "mt6797-gemini-pda-a72-observer-initcall-diagnostic.dtb",
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}
AG_MEMBERS = {
    "Image.gz",
    "SHA256SUMS",
    "System.map",
    "analysis.txt",
    "boot-validation.txt",
    "console-keymap-verify",
    "console-unicode-mode",
    "dtb-validation.txt",
    "gemini-simplefb-observation-restoration.boot.img",
    "gemini-simplefb-observation-restoration-initramfs.img",
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "lineage-validation.txt",
    "mt6797-gemini-pda-simplefb-observation-restoration.dtb",
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}
AD_MEMBERS = {
    "Image.gz",
    "SHA256SUMS",
    "System.map",
    "analysis.txt",
    "boot-validation.txt",
    "console-keymap-verify",
    "console-unicode-mode",
    "gemini-smp8.boot.img",
    "gemini-us.bkeymap",
    "gemini-usb-gadget-ethernet-initramfs.img",
    "input-event-capture",
    "mt6797-gemini-pda-smp8.dtb",
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}
EXPECTED_CMDLINE = (
    'CONFIG_CMDLINE="console=ttyS0,921600n8 earlycon maxcpus=8 nokaslr '
    "ignore_loglevel loglevel=8 log_buf_len=1M initcall_debug rdinit=/init "
    "panic=0 g_ether.dev_addr=42:00:15:19:82:01 "
    "g_ether.host_addr=42:00:15:19:82:00 "
    "g_ether.iManufacturer=gemini-pda-mainline "
    "g_ether.iProduct=Gemini-L-Observability "
    "g_ether.iSerialNumber=GEMINI_OBSERVABILITY_20260717_L "
    "clk_ignore_unused fbcon=rotate:3 consoleblank=0 fbcon=font:TER16x32 "
    "regulator_ignore_unused "
    'initcall_blacklist=mt6797_a72_power_driver_init"'
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_artifact(
    root: pathlib.Path,
    expected_name: str,
    expected_members: set[str],
    manifest_sha256: str,
) -> dict[str, tuple[int, str]]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode) or root.name != expected_name:
        raise ValueError(f"artifact directory identity is unsafe: {root}")
    members: dict[str, tuple[int, str]] = {}
    for path in sorted(root.iterdir()):
        path_info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(path_info.st_mode):
            raise ValueError(f"artifact member is not a regular file: {path.name}")
        members[path.name] = (stat.S_IMODE(path_info.st_mode), digest(path))
    if set(members) != expected_members:
        raise ValueError(f"{expected_name} artifact inventory changed")
    if members["SHA256SUMS"][1] != manifest_sha256:
        raise ValueError(f"{expected_name} manifest identity changed")
    for member, (mode, _) in members.items():
        expected_mode = 0o755 if member in EXECUTABLE_MEMBERS else 0o600
        if mode != expected_mode:
            raise ValueError(f"{expected_name} mode changed: {member}")

    seen: set[str] = set()
    for line in (root / "SHA256SUMS").read_text(encoding="ascii").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError(f"{expected_name} manifest is malformed")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in seen or member == "SHA256SUMS" or member not in members:
            raise ValueError(f"{expected_name} manifest member is unsafe")
        if fields[0] != members[member][1]:
            raise ValueError(f"{expected_name} manifest checksum differs: {member}")
        seen.add(member)
    if seen != expected_members - {"SHA256SUMS"}:
        raise ValueError(f"{expected_name} manifest inventory changed")
    return members


def require_hash(members: dict[str, tuple[int, str]], member: str, expected: str) -> None:
    if members[member][1] != expected:
        raise ValueError(f"exact lineage member changed: {member}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--af-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ag-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ad-artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        supplied = {
            "AF": args.af_artifact,
            "AG": args.ag_artifact,
            "AD": args.ad_artifact,
        }
        resolved: dict[str, pathlib.Path] = {}
        for label, path in supplied.items():
            info = path.lstat()
            if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
                raise ValueError(f"{label} artifact path is unsafe")
            resolved[label] = path.resolve(strict=True)
        if len({path for path in resolved.values()}) != 3:
            raise ValueError("AF, AG, and AD must be independent artifact trees")

        af = validate_artifact(
            resolved["AF"], AF_NAME, AF_MEMBERS, AF_MANIFEST_SHA256
        )
        ag = validate_artifact(
            resolved["AG"], AG_NAME, AG_MEMBERS, AG_MANIFEST_SHA256
        )
        ad = validate_artifact(
            resolved["AD"], AD_NAME, AD_MEMBERS, AD_MANIFEST_SHA256
        )
        for members, member, expected in (
            (af, "gemini-a72-observer-initcall-diagnostic.boot.img", AF_BOOT_SHA256),
            (af, "mt6797-gemini-pda-a72-observer-initcall-diagnostic.dtb", AF_DTB_SHA256),
            (ag, "gemini-simplefb-observation-restoration.boot.img", AG_BOOT_SHA256),
            (ag, "mt6797-gemini-pda-simplefb-observation-restoration.dtb", AG_DTB_SHA256),
            (ad, "gemini-smp8.boot.img", AD_BOOT_SHA256),
            (ad, "mt6797-gemini-pda-smp8.dtb", AD_DTB_SHA256),
        ):
            require_hash(members, member, expected)

        shared = {
            "Image.gz": IMAGE_GZ_SHA256,
            "System.map": SYSTEM_MAP_SHA256,
            "kernel.config": CONFIG_SHA256,
            "source-build.json": SOURCE_BUILD_SHA256,
            "gemini-us.bkeymap": KEYMAP_SHA256,
        }
        for member, expected in shared.items():
            require_hash(af, member, expected)
            require_hash(ag, member, expected)
            if af[member] != ag[member]:
                raise ValueError(f"AF/AG byte or mode lineage differs: {member}")
        initramfs_members = (
            "gemini-a72-observer-initcall-diagnostic-initramfs.img",
            "gemini-simplefb-observation-restoration-initramfs.img",
        )
        require_hash(af, initramfs_members[0], INITRAMFS_SHA256)
        require_hash(ag, initramfs_members[1], INITRAMFS_SHA256)
        require_hash(ad, "gemini-usb-gadget-ethernet-initramfs.img", INITRAMFS_SHA256)
        if not (
            af[initramfs_members[0]]
            == ag[initramfs_members[1]]
            == ad["gemini-usb-gadget-ethernet-initramfs.img"]
        ):
            raise ValueError("AF/AG/AD initramfs byte or mode lineage differs")
        if not (af["gemini-us.bkeymap"] == ag["gemini-us.bkeymap"] == ad["gemini-us.bkeymap"]):
            raise ValueError("AF/AG/AD keymap byte or mode lineage differs")
        for member in EXECUTABLE_MEMBERS:
            if not (af[member] == ag[member] == ad[member]):
                raise ValueError(f"AF/AG/AD userspace helper lineage differs: {member}")

        config = (resolved["AG"] / "kernel.config").read_text(
            encoding="utf-8"
        ).splitlines()
        for exact in (
            EXPECTED_CMDLINE,
            "CONFIG_CMDLINE_FORCE=y",
            "CONFIG_REGULATOR_DA9211=y",
            "CONFIG_MTK_MT6797_A72_POWER=y",
            "CONFIG_FB_SIMPLE=y",
            "CONFIG_USB_GADGET=y",
        ):
            if config.count(exact) != 1:
                raise ValueError(f"exact AF/AG configuration line differs: {exact}")
        system_map = (resolved["AG"] / "System.map").read_text(encoding="ascii")
        for symbol in (
            "mt6797_a72_power_driver_init",
            "mt6797_psci_ops",
            "simplefb_driver_init",
        ):
            if not any(line.endswith(" " + symbol) for line in system_map.splitlines()):
                raise ValueError(f"exact AF/AG symbol is absent: {symbol}")

        print("validation=candidate-ah-exact-af-ag-ad-lineage")
        print(f"af_artifact={resolved['AF'].name}")
        print(f"af_manifest_sha256={AF_MANIFEST_SHA256}")
        print(f"ag_artifact={resolved['AG'].name}")
        print(f"ag_manifest_sha256={AG_MANIFEST_SHA256}")
        print(f"ad_artifact={resolved['AD'].name}")
        print(f"ad_manifest_sha256={AD_MANIFEST_SHA256}")
        print(f"image_gz_sha256={IMAGE_GZ_SHA256}")
        print(f"system_map_sha256={SYSTEM_MAP_SHA256}")
        print(f"config_sha256={CONFIG_SHA256}")
        print(f"initramfs_sha256={INITRAMFS_SHA256}")
        print(f"ad_dtb_sha256={AD_DTB_SHA256}")
        print("kernel_config_system_map=byte-exact-af-and-ag")
        print("initramfs_keymap_helpers=byte-exact-af-ag-and-ad")
        print("dt_contract=byte-exact-hardware-passed-ad")
        print("a72_observer_initcall=blacklisted-by-exact-kernel-cmdline")
        print("device_access=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
