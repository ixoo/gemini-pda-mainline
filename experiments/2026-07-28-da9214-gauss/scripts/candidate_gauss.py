"""Pinned inputs and safety boundaries for Candidate Gauss."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re
import stat
import sys
from types import ModuleType


EXPERIMENT = "2026-07-28-da9214-gauss"
CANDIDATE = "Gauss"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-gauss"
)
SERIES = "patches/series-gauss-i2c6-exact-d3"
SERIES_SHA256 = "a203482246d00637c397eace5fb8526867ecd1297bae752508f14aeae9d3d66d"
CONFIG_FRAGMENT = "configs/gemini-i2c6-gauss.fragment"
CONFIG_FRAGMENT_SHA256 = (
    "1536480a5f1a5c802921939c5394da46455d79769e815ee53f39b10bd6512e7a"
)
CURIE_PATCH = (
    "v7.1.3/0121-i2c-mediatek-require-exact-Curie-board-control.patch"
)
CURIE_PATCH_SHA256 = (
    "f82ad98c9bb6fb1f99bca9c778d0b1853f9ec3bbed2ce59e9643680826a7750c"
)
GAUSS_PATCH = (
    "v7.1.3/0122-i2c-mediatek-add-Gauss-exact-D3-discriminator.patch"
)
GAUSS_PATCH_SHA256 = (
    "654bac9cf1a97ba49d953a785a57e5cebab683be7a0a5d297acb0209ddf55e5e"
)

FERMI_MODULE = (
    "experiments/2026-07-28-da9214-fermi/scripts/candidate_fermi.py"
)
FERMI_MODULE_SHA256 = (
    "3422bb29490f21f0410d4d45f521fc3ac89eff3679d117535c7b5dcf0cffe5e6"
)
HEX256 = re.compile(r"^[0-9a-f]{64}$")


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_fermi() -> ModuleType:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    source = repository / FERMI_MODULE
    data = read_regular(source, "source-pinned Candidate Fermi module")
    if hashlib.sha256(data).hexdigest() != FERMI_MODULE_SHA256:
        raise ValueError("source-pinned Candidate Fermi module changed")
    spec = importlib.util.spec_from_file_location("gauss_fermi_pins", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Candidate Fermi module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


_FERMI = load_fermi()

# The canonical series reaches Gauss through Curie's unconfigured source
# boundary. Patch 0122 restores the Fermi ABI before the profile is configured.
GAUSS_PATCHES = _FERMI.FERMI_PATCHES + (CURIE_PATCH, GAUSS_PATCH)
GAUSS_PATCH_SHA256S = _FERMI.FERMI_PATCH_SHA256S + (
    CURIE_PATCH_SHA256,
    GAUSS_PATCH_SHA256,
)

# Gauss deliberately preserves Fermi's complete pre-endpoint identity.
KERNEL_LOCALVERSION = "-gemini-fermi"
KERNEL_RELEASE = "7.1.3-gemini-fermi"
USB_PRODUCT = "Gemini-L-Fermi"
USB_SERIAL = "GEMINI_FERMI_20260728"
DEBUGFS_FILE = "fermi-run-native"
READY_MARKER = "GEMINI_FERMI_NATIVE_DIAGNOSTIC"
GATE_MARKER = "GEMINI_FERMI_DIAGNOSTIC_GATE"
LK_NAME = "gemini-fermi"
LK_CMDLINE = "bootopt=64S3,32N2,64N2"

# Exact Fermi package/binary control. The path is caller supplied because the
# recovery VM may retain it in a different artifact root.
FERMI_PACKAGE_DIRECTORY = (
    "linux-7.1.3-gemini-observability-fbcon-rotation-keyboard-wrrd-"
    "manual-reboot-smp8-a72-observer-initcall-blacklist-dvfsp-handoff-"
    "owner-i2c6-consumer-ap-dma-preserve-fermi-f220df68-55d5d7d8"
)
FERMI_IMAGE_SHA256 = (
    "c2907820970265d7cc01950c94e4991f509500869e0601d700b6838ff6635751"
)
FERMI_IMAGE_GZ_SHA256 = (
    "3c581195b37b7d2f9bff1606d2b5e777a94018fe640e3527235d5a677dbd7b39"
)
FERMI_SYSTEM_MAP_SHA256 = (
    "afa62ee60bd10ecc54b35771d80b4a39d47f056d3f152d7ec05d23a6f893cf91"
)
FERMI_CONFIG_SHA256 = (
    "c5b56a23d3711895f826487edf4762bf035d442c0bf29810f9032288adeee407"
)
FERMI_COMPILED_DTB_SHA256 = (
    "0a2aa671dd17e9daf5ce5e3de3d92917129ce639a0a02e0a5041ecf3e3441168"
)
FERMI_I2C_OBJECT_SHA256 = (
    "486d4a46481527827b147d73bc194a31b32f8832b4b0e2cf08ae555ae1937874"
)
GAUSS_I2C_OBJECT_SHA256 = (
    "b4535d44ed14190a8342bca1a18edddcb2c225ea4c3fe6f8ad9baeb60f8d071a"
)
I2C_OBJECT_SIZE = 36296
FERMI_VMLINUX_SHA256 = (
    "15d85f53aa0cfe314e9cae1b59139a540f0bf8dc0a68651c3fef41092720c21e"
)
GAUSS_VMLINUX_SHA256 = (
    "6d50fb720f8a4bd862f08bd4c3b0e262fe254b7033b54736d022c7b7f3b4e6dd"
)
VMLINUX_SIZE = 16377192
GAUSS_IMAGE_SHA256 = (
    "37e3e818952b5d9793d740b8883330a4edc2a1e1065f92a8fed75dfa5fa0a12a"
)
GAUSS_IMAGE_GZ_SHA256 = (
    "d00d6a7d5eeb8fc73666991376a3336d7862b6654699d19ab794e30b0b171f93"
)
FERMI_RAW_SHA256 = (
    "33210b4144ad8b485e8da8284feb7af772f2cc99a762a9a120736b1bdc654635"
)
FERMI_PADDED_SHA256 = (
    "0234c36c401aba7901f76a5ab8cc034d3d6038e132c9d9ad505e983119c69534"
)
CURIE_PADDED_SHA256 = (
    "824c3391f55cc932d146ef2e573642a51fb5c077932c7b6d17316fd34020d52d"
)

# Exact Fermi serviceability, DT, initramfs, LK, and transfer foundation.
CASSINI_PACKAGE_DIR = _FERMI.CASSINI_PACKAGE_DIR
CASSINI_PROVENANCE_SHA256 = _FERMI.CASSINI_PROVENANCE_SHA256
CASSINI_COMPILED_DTB_SHA256 = _FERMI.CASSINI_COMPILED_DTB_SHA256
ORION_COMPILED_DTB_SHA256 = _FERMI.ORION_COMPILED_DTB_SHA256
CASSINI_PACKAGE_VALIDATOR_SHA256 = _FERMI.CASSINI_PACKAGE_VALIDATOR_SHA256
CASSINI_PINS_SHA256 = _FERMI.CASSINI_PINS_SHA256
ORION_DTB_VALIDATOR_SHA256 = _FERMI.ORION_DTB_VALIDATOR_SHA256
ORION_DTB_BUILDER_SHA256 = _FERMI.ORION_DTB_BUILDER_SHA256
DTB_LINEAGE_VALIDATOR_SHA256 = _FERMI.DTB_LINEAGE_VALIDATOR_SHA256
HUBBLE_ARTIFACT_DIR = _FERMI.HUBBLE_ARTIFACT_DIR
HUBBLE_MANIFEST_SHA256 = _FERMI.HUBBLE_MANIFEST_SHA256
HUBBLE_RAW_SHA256 = _FERMI.HUBBLE_RAW_SHA256
HUBBLE_RAW_SIZE = _FERMI.HUBBLE_RAW_SIZE
HUBBLE_PADDED_SHA256 = _FERMI.HUBBLE_PADDED_SHA256
HUBBLE_BOOT_MEMBER = _FERMI.HUBBLE_BOOT_MEMBER
HUBBLE_DTB_MEMBER = _FERMI.HUBBLE_DTB_MEMBER
HUBBLE_DTB_SHA256 = _FERMI.HUBBLE_DTB_SHA256
ORION_BOOT_DTB_SHA256 = _FERMI.ORION_BOOT_DTB_SHA256
HUBBLE_INITRAMFS_MEMBER = _FERMI.HUBBLE_INITRAMFS_MEMBER
HUBBLE_INITRAMFS_SHA256 = _FERMI.HUBBLE_INITRAMFS_SHA256
HUBBLE_VALIDATOR_SHA256 = _FERMI.HUBBLE_VALIDATOR_SHA256
HUBBLE_PINS_SHA256 = _FERMI.HUBBLE_PINS_SHA256
SERIALIZER_SHA256 = _FERMI.SERIALIZER_SHA256
ANALYZER_SHA256 = _FERMI.ANALYZER_SHA256
NORMALIZER_SHA256 = _FERMI.NORMALIZER_SHA256

BOOT_MEMBER = "gemini-mt6797-da9214-gauss.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-da9214-gauss.dtb"
INITRAMFS_MEMBER = HUBBLE_INITRAMFS_MEMBER
PADDED_MEMBER = "boot2-padded.img"
ARTIFACT_PREFIX = "candidate-Gauss-da9214-"
BOOT2_SIZE = _FERMI.BOOT2_SIZE
I2C6_PATH = _FERMI.I2C6_PATH
I2C6_COMPATIBLE = _FERMI.I2C6_COMPATIBLE

PASSES = _FERMI.PASSES
TRANSFER_ORDER = _FERMI.TRANSFER_ORDER
SIGNATURE = _FERMI.SIGNATURE
D3_EXPECTED = 0x1F
STABILITY_REGISTERS = _FERMI.STABILITY_REGISTERS
PREFILLS = _FERMI.PREFILLS
SAMPLE_COUNT = _FERMI.SAMPLE_COUNT


def require_input_pins() -> None:
    _FERMI.require_input_pins()
    for name, value in {
        "SERIES_SHA256": SERIES_SHA256,
        "CONFIG_FRAGMENT_SHA256": CONFIG_FRAGMENT_SHA256,
        "CURIE_PATCH_SHA256": CURIE_PATCH_SHA256,
        "GAUSS_PATCH_SHA256": GAUSS_PATCH_SHA256,
        "FERMI_MODULE_SHA256": FERMI_MODULE_SHA256,
        "FERMI_IMAGE_SHA256": FERMI_IMAGE_SHA256,
        "FERMI_SYSTEM_MAP_SHA256": FERMI_SYSTEM_MAP_SHA256,
        "FERMI_CONFIG_SHA256": FERMI_CONFIG_SHA256,
        "FERMI_COMPILED_DTB_SHA256": FERMI_COMPILED_DTB_SHA256,
        "FERMI_I2C_OBJECT_SHA256": FERMI_I2C_OBJECT_SHA256,
        "GAUSS_I2C_OBJECT_SHA256": GAUSS_I2C_OBJECT_SHA256,
        "FERMI_VMLINUX_SHA256": FERMI_VMLINUX_SHA256,
        "GAUSS_VMLINUX_SHA256": GAUSS_VMLINUX_SHA256,
        "GAUSS_IMAGE_SHA256": GAUSS_IMAGE_SHA256,
        "GAUSS_IMAGE_GZ_SHA256": GAUSS_IMAGE_GZ_SHA256,
        "CURIE_PADDED_SHA256": CURIE_PADDED_SHA256,
    }.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Gauss {name} is unresolved or malformed")
    if len(GAUSS_PATCHES) != len(GAUSS_PATCH_SHA256S):
        raise ValueError("Candidate Gauss patch-pin inventory is inconsistent")
    if TRANSFER_ORDER != _FERMI.TRANSFER_ORDER or PREFILLS != _FERMI.PREFILLS:
        raise ValueError("Candidate Gauss changed Fermi transfer or prefill policy")
    if SAMPLE_COUNT != 14:
        raise ValueError("Candidate Gauss transfer count changed")
    flattened = tuple(value for row in PREFILLS for value in row)
    if len(set(flattened)) != SAMPLE_COUNT or D3_EXPECTED in flattened:
        raise ValueError("Candidate Gauss receive-prefill contract changed")
