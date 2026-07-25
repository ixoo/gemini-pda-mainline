#!/usr/bin/env python3
"""Single-source immutable identities for Candidate AB construction.

The two timestamp-bearing package-file pairs are the completed build-3/build-4
calibration gate. Candidate output hashes are deliberately not pinned: the
builder derives their names only after two byte-identical constructions.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import stat


EXPERIMENT = "2026-07-20-mt6797-kernel-restart-diagnostic"
CANDIDATE = "AB"
MARKER = "GEMINI_MT6797_KERNEL_RESTART_20260720_AB"
PROMPT = "GEMINI-AB#"
BOOT2_CAPACITY = 16 * 1024 * 1024

AA_ARTIFACT_NAME = "candidate-AA-keyboard-console-map-final-37e82bf3"
AA_MANIFEST_SHA256 = "2a291c5e8f20442140ce025028af578272a06f41c53498baec728ba61c49c343"
AA_BOOT_SHA256 = "37e82bf3be87dd9e52fb8d60597b69f92a5c0dc5aebd51d178f1e7efd33343d7"
AA_BOOT_SIZE = 7_378_944
AA_INITRAMFS_SHA256 = "4218be56af7b844f8b572f57e49ddeb106d48331bd34c61bec58afb7215c2aa7"
AA_INITRAMFS_SIZE = 1_819_953
AA_IMAGE_GZ_SHA256 = "d69b2cdc0a2dca05919e5e0dc25c54920a509af89eb1a7f16336e82d368fda41"
AA_DTB_SHA256 = "bc160c428b83903524aa92046d5ed1da44e87f0f1c6dacfbb33cb6a9f2ee963f"
AA_DTB_SIZE = 26_259
AA_KEYMAP_SHA256 = "02f8048d76aa0cedf73617b13ea03a2a4e74de88222cb1922d9d19630906675c"
AA_UNICODE_HELPER_SHA256 = "5949ee28aedeb8f8ba7b5486abbec7714034f7b833265bace9a1438b8a1dd650"
AA_KEYMAP_VERIFIER_SHA256 = "29735d212e74d0b0040a3ead173a83223b89ce5d947b697a115707eb3d23b238"
AA_INPUT_HELPER_SHA256 = "b9b555ce176a8bb29b492a73f06288784baf4f54786bed514ff1230efd732602"
AA_SOURCE_BUILD_SHA256 = "6c04e871811902799ff4fc68d2b4440ba2e42026b4ca8142e7bfbd425a0ce071"
AA_R1_INSTALLER_SHA256 = "f081ef03b2dce68d28458eacdcc184a5550c88eeb75579fab61359e936a40f9f"
AA_R1_PADDED_SHA256 = "38b49c7c19c2d97fa0c48436545219489221aa367aedf491ae6ebd4ec4856703"
AB_INSTALLER_WRAPPER_TEMPLATE_SHA256 = (
    "d9bc5480fba2e814c1352c2ecb0d595550e07845201884f3e2c821f06fb81ce6"
)
BUSYBOX_SHA256 = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
DISPATCH_ENV_SHA256 = "8255ad7ab034cd3d760690a8b57eebcb67c974d321249ed8ee3a4f142f53e90a"

AA_EXPECTED_FILES = frozenset(
    {
        "SHA256SUMS",
        "Image.gz",
        "boot-build.txt",
        "boot-validation.txt",
        "console-keymap-verify",
        "console-unicode-mode",
        "gemini-keyboard-console-map-initramfs.img",
        "gemini-keyboard-console-map.boot.img",
        "gemini-us.bkeymap",
        "initramfs-build.txt",
        "initramfs-validation.txt",
        "input-event-capture",
        "input-tree.sha256",
        "keymap-test.txt",
        "keymap-validation.txt",
        "keymap-verifier-test.txt",
        "lk-analysis.txt",
        "mt6797-gemini-pda-keyboard-console-map.dtb",
        "provenance.txt",
        "source-build.json",
        "z-baseline-validation.txt",
    }
)
AA_EXECUTABLE_FILES = frozenset(
    {"console-keymap-verify", "console-unicode-mode", "input-event-capture"}
)

PROFILE = "observability-fbcon-rotation-keyboard-wrrd-manual-reboot"
EXPECTED_FRAGMENTS = (
    "configs/gemini-handoff.fragment",
    "configs/gemini-usbdiag.fragment",
    "configs/gemini-clk-ignore-unused.fragment",
    "configs/gemini-observability.fragment",
    "configs/gemini-fbcon-rotation.fragment",
    "configs/gemini-keyboard.fragment",
    "configs/gemini-keyboard-wrrd.fragment",
    "configs/gemini-keyboard-manual-reboot.fragment",
)
PACKAGE_NAME = (
    "linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-"
    "manual-reboot-efb79d0c-c811a159"
)
SOURCE_SHA256 = "be41c068e88f5242a19bccdbffbe077b18c47b45f627e2325504b4fab79dd1dc"
KERNEL_MANIFEST_SHA256 = "a3e42edc371ffa82b4eec174614d1af13ece0b2e02f6d5c6a682d0098d360f4d"
KERNEL_BUILD_SCRIPT_SHA256 = "75995c6cde44cefb50950097bff26c62f26df01ca0f487e2a3bcfc8fcf159634"
PATCHSET_SHA256 = "efb79d0ced5ebee485e337f224075faaa4abf7eb7d5e6a38326383274cd75f93"
SERIES_SHA256 = "124db1a0c4d3d4f5ee43d75bbced9d4b5f28a649ef92c04acdb8ccb67be4117a"
PATCH_0087_SHA256 = "81168e4cc12d9ffad7645f667c0211d8dff73b0dadda3ebd422f63378e411d56"
CONFIG_INPUTS_SHA256 = "c811a1595510716777871637672f4298f4808b1d4fcea5c5da1d05d37676baa2"
CONFIG_SHA256 = "0a0e4ef39d5d89d0d54f55be44da753c93779d88bb94b35623679d1b08b66e74"
IMAGE_SHA256 = "0ccb5490bc97e288210637b04ede52cf01b0105e1d4d3ee88e7ad21608ecf004"
IMAGE_GZ_SHA256 = "37ba538e76e329f3e57cfa78b481151e2d1e5eabcc321a29c7b54d476b6ec26f"
SYSTEM_MAP_SHA256 = "355a547d5ce17dc295d5c66760415c7a2056be1897db57d8325b303eb32c4e63"
PACKAGE_DTB_SHA256 = "f9be46ffed6cf598f7892d88d8702ff6a4ede074c5b477734ae11bcb4c093db5"
KERNEL_RELEASE = "7.1.3-gemini-observability-L"
COMPILER = "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0"
LINKER = "GNU ld (GNU Binutils for Ubuntu) 2.42"

# Raw build.json and SHA256SUMS differ when only generated_utc changes.  These
# are the two accepted build-3/build-4 pairs from the completed reproduction
# gate; all payload and semantic provenance identities remain common.
PACKAGE_FILE_PAIRS = (
    (
        "4ae390b4b12e6db31f51fcc90dff8b575c22115be7dc070ed0628169a696b091",
        "934b432900817a4edc4062c8a801df0b59478d8c9979962a35b4df79ae5a8e08",
    ),
    (
        "91f4ddc6c7fd52095c588d80063ecf50721c1bb2b9e0bcb20143a01ae86a4df7",
        "70cb6cf4223d2d753d47478d863986c3b20d8c52f3dc7d8359152af3476ca093",
    ),
)

PATCH_COUNT = 88
LAST_PATCH = "v7.1.3/0087-watchdog-mtk-prioritize-MT6797-TOPRGU-restart.patch"
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_regular(path: pathlib.Path, label: str, mode: int | None = None) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is not a regular non-symlink file")
    if mode is not None and stat.S_IMODE(info.st_mode) != mode:
        raise ValueError(f"{label} mode is not {mode:04o}")
    return path.read_bytes()


def require_package_calibration() -> None:
    values = [value for pair in PACKAGE_FILE_PAIRS for value in pair]
    if any(value.startswith("REPLACE_AFTER_") for value in values):
        raise ValueError(
            "build-3/build-4 package-file calibration remains intentionally closed"
        )
    if any(HEX256.fullmatch(value) is None for value in values):
        raise ValueError("calibrated package-file SHA-256 is malformed")
