#!/usr/bin/env python3
"""Validate the exact AD, AH, and AF artifact inputs for Candidate AI."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import re
import stat
import sys

sys.dont_write_bytecode = True


AD_NAME = "candidate-AD-smp8-final-a1b61d8c"
AD_MANIFEST_SHA256 = "c3aeccf2e6e18a0c4769b909ccf45a77f75cc3677fe61fbd786d0925154fc51f"
AD_BOOT_SHA256 = "a1b61d8c34b5a447f1f672663f4e74fed6eb465b90154392a3c42f4db030826b"
AD_IMAGE_GZ_SHA256 = "1ab084bd427f9fade4adb43a83cca879c3289929485ad1469c6dffa539d3548b"
AD_SYSTEM_MAP_SHA256 = "63dc89816c1cee5b62e3f514e12512b199415e81be37f5577168465787a42890"
AD_SOURCE_BUILD_SHA256 = "41e930eb6743b3d145c7f4e10155b3d8e1e807931bd858736de9b27fda3dd0d5"
AD_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"

AH_NAME = "candidate-AH-ad-contract-af-kernel-split-e5ba6ee0"
AH_MANIFEST_SHA256 = "04b25bfc5e72645318273e03adc80191df7d52994acc7ade8202a64d95223997"
AH_BOOT_SHA256 = "e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197"
AH_DTB_SHA256 = "27175804f052259c86ed068d2c318e83d5b2090f4aa705e063f9c9b33a4ca845"

AF_NAME = "candidate-AF-a72-observer-initcall-fe43efa8"
AF_MANIFEST_SHA256 = "77e311af022e067185b9c9462137cfb73bb639ef0f29d9eb946d326097636e22"
AF_BOOT_SHA256 = "fe43efa8c9d18174fec97ab7ad6cbe59bbc490df92366bcd254c55daa932d0a3"
AF_IMAGE_GZ_SHA256 = "b03ec8816b6a8908991c38c0f9fc9218fa3608b2aefe8959fb2ffe7c02a57912"
AF_CONFIG_SHA256 = "bfd71f6618fab738d378530f73d1c75d73c69f19334b84d9c663aaa98740eb63"
AF_SYSTEM_MAP_SHA256 = "a0bf3087fb2225e17192606cb2150204ce89cfb51ea0719e4ce200800b1a407d"

INITRAMFS_SHA256 = "166c0f03ab9ca1062f36d55132141b4be5f06187380d17ab2f6e9e7db75d1dd3"
KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
HELPER_SHA256 = {
    "console-keymap-verify": "29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238",
    "console-unicode-mode": "5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650",
    "input-event-capture": "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602",
}

AD_MEMBERS = {
    "Image.gz", "SHA256SUMS", "System.map", "analysis.txt",
    "boot-validation.txt", "console-keymap-verify", "console-unicode-mode",
    "gemini-smp8.boot.img", "gemini-us.bkeymap",
    "gemini-usb-gadget-ethernet-initramfs.img", "input-event-capture",
    "mt6797-gemini-pda-smp8.dtb", "package-validation.txt", "provenance.txt",
    "serializer.txt", "source-build.json",
}
AH_MEMBERS = {
    "Image.gz", "SHA256SUMS", "System.map", "analysis.txt",
    "boot-validation.txt", "console-keymap-verify", "console-unicode-mode",
    "dtb-validation.txt", "gemini-ad-contract-af-kernel-split.boot.img",
    "gemini-ad-contract-af-kernel-split-initramfs.img", "gemini-us.bkeymap",
    "input-event-capture", "kernel.config", "lineage-validation.txt",
    "mt6797-gemini-pda-ad-contract-af-kernel-split.dtb", "provenance.txt",
    "serializer.txt", "source-build.json",
}
AF_MEMBERS = {
    "Image.gz", "SHA256SUMS", "System.map", "analysis.txt",
    "boot-validation.txt", "console-keymap-verify", "console-unicode-mode",
    "gemini-a72-observer-initcall-diagnostic.boot.img",
    "gemini-a72-observer-initcall-diagnostic-initramfs.img",
    "gemini-us.bkeymap", "input-event-capture", "kernel.config",
    "mt6797-gemini-pda-a72-observer-initcall-diagnostic.dtb",
    "package-validation.txt", "provenance.txt", "serializer.txt",
    "source-build.json",
}
EXECUTABLE_MEMBERS = set(HELPER_SHA256)
AH_DTB_VALIDATOR_SHA256 = "8dd73ac13d0aa6bd90754ff0061a7c1d0c19f561f7029a6ca6a4dde7fdfcb28f"


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_artifact(
    root: pathlib.Path,
    name: str,
    expected_members: set[str],
    manifest_hash: str,
) -> dict[str, tuple[int, str]]:
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode) or root.name != name:
        raise ValueError(f"unsafe or unexpected artifact root: {root}")
    members: dict[str, tuple[int, str]] = {}
    for path in sorted(root.iterdir()):
        path_info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(path_info.st_mode):
            raise ValueError(f"artifact contains a non-regular member: {path.name}")
        members[path.name] = (stat.S_IMODE(path_info.st_mode), digest(path))
    if set(members) != expected_members:
        raise ValueError(f"{name} inventory changed")
    if members["SHA256SUMS"][1] != manifest_hash:
        raise ValueError(f"{name} manifest identity changed")
    for member, (mode, _) in members.items():
        expected_mode = 0o755 if member in EXECUTABLE_MEMBERS else 0o600
        if mode != expected_mode:
            raise ValueError(f"{name} mode changed: {member}")

    seen: set[str] = set()
    lines = (root / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError(f"{name} manifest is malformed")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in seen or member == "SHA256SUMS" or member not in members:
            raise ValueError(f"{name} manifest path is unsafe or duplicated")
        if fields[0] != members[member][1]:
            raise ValueError(f"{name} checksum mismatch: {member}")
        seen.add(member)
    if seen != expected_members - {"SHA256SUMS"}:
        raise ValueError(f"{name} manifest is not an exact inventory")
    return members


def require_hash(
    members: dict[str, tuple[int, str]], member: str, expected: str
) -> None:
    if members[member][1] != expected:
        raise ValueError(f"exact lineage member changed: {member}")


def load_ah_dtb_validator() -> object:
    experiments = pathlib.Path(__file__).resolve().parents[2]
    source = (
        experiments
        / "2026-07-22-ad-contract-af-kernel-split"
        / "scripts/validate-dtb-delta.py"
    )
    if digest(source) != AH_DTB_VALIDATOR_SHA256:
        raise ValueError("source-pinned AH DT validator changed")
    spec = importlib.util.spec_from_file_location("gemini_ai_ah_dtb", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned AH DT validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(ad_root: pathlib.Path, ah_root: pathlib.Path, af_root: pathlib.Path) -> None:
    roots = (ad_root, ah_root, af_root)
    if len(set(roots)) != 3:
        raise ValueError("AD, AH, and AF must be independent artifact trees")
    ad = validate_artifact(ad_root, AD_NAME, AD_MEMBERS, AD_MANIFEST_SHA256)
    ah = validate_artifact(ah_root, AH_NAME, AH_MEMBERS, AH_MANIFEST_SHA256)
    af = validate_artifact(af_root, AF_NAME, AF_MEMBERS, AF_MANIFEST_SHA256)

    for members, member, expected in (
        (ad, "gemini-smp8.boot.img", AD_BOOT_SHA256),
        (ad, "Image.gz", AD_IMAGE_GZ_SHA256),
        (ad, "System.map", AD_SYSTEM_MAP_SHA256),
        (ad, "source-build.json", AD_SOURCE_BUILD_SHA256),
        (ad, "mt6797-gemini-pda-smp8.dtb", AD_DTB_SHA256),
        (ah, "gemini-ad-contract-af-kernel-split.boot.img", AH_BOOT_SHA256),
        (ah, "mt6797-gemini-pda-ad-contract-af-kernel-split.dtb", AH_DTB_SHA256),
        (af, "gemini-a72-observer-initcall-diagnostic.boot.img", AF_BOOT_SHA256),
        (af, "Image.gz", AF_IMAGE_GZ_SHA256),
        (af, "kernel.config", AF_CONFIG_SHA256),
        (af, "System.map", AF_SYSTEM_MAP_SHA256),
    ):
        require_hash(members, member, expected)

    initramfs_members = (
        (ad, "gemini-usb-gadget-ethernet-initramfs.img"),
        (ah, "gemini-ad-contract-af-kernel-split-initramfs.img"),
        (af, "gemini-a72-observer-initcall-diagnostic-initramfs.img"),
    )
    identities = set()
    for members, member in initramfs_members:
        require_hash(members, member, INITRAMFS_SHA256)
        identities.add(members[member])
    if len(identities) != 1:
        raise ValueError("AD/AH/AF initramfs byte or mode lineage differs")
    for members in (ad, ah, af):
        require_hash(members, "gemini-us.bkeymap", KEYMAP_SHA256)
        for member, expected in HELPER_SHA256.items():
            require_hash(members, member, expected)
    for member in {"gemini-us.bkeymap", *HELPER_SHA256}:
        if len({ad[member], ah[member], af[member]}) != 1:
            raise ValueError(f"AD/AH/AF userspace lineage differs: {member}")

    validator = load_ah_dtb_validator()
    validator.validate(
        ad_root / "mt6797-gemini-pda-smp8.dtb",
        ah_root / "mt6797-gemini-pda-ad-contract-af-kernel-split.dtb",
    )


def resolve_artifact(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} artifact path")
    return path.resolve(strict=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ad-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--ah-artifact", type=pathlib.Path, required=True)
    parser.add_argument("--af-artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        ad = resolve_artifact(args.ad_artifact, "AD")
        ah = resolve_artifact(args.ah_artifact, "AH")
        af = resolve_artifact(args.af_artifact, "AF")
        validate(ad, ah, af)
        print("validation=candidate-ai-exact-ad-ah-af-lineage")
        print(f"ad_artifact={AD_NAME}")
        print(f"ad_manifest_sha256={AD_MANIFEST_SHA256}")
        print(f"ah_artifact={AH_NAME}")
        print(f"ah_manifest_sha256={AH_MANIFEST_SHA256}")
        print(f"af_artifact={AF_NAME}")
        print(f"af_manifest_sha256={AF_MANIFEST_SHA256}")
        print(f"initramfs_sha256={INITRAMFS_SHA256}")
        print(f"final_dtb_sha256={AH_DTB_SHA256}")
        print("final_dtb_delta=exact-ad-plus-two-a72-enable-method-properties")
        print("keyboard_usb_console_reboot=byte-exact-ad")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
