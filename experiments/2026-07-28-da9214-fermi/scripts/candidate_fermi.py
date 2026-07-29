"""Pinned inputs and safety boundaries for Candidate Fermi."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re
import stat
import sys
from types import ModuleType


EXPERIMENT = "2026-07-28-da9214-fermi"
CANDIDATE = "Fermi"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-fermi"
)
SERIES = "patches/series-fermi-i2c6-topology-fingerprint"
SERIES_SHA256 = "c6141bbf97e5b65a76d6519bf614c1a349ab5b32b9146ee7e302405870c7af4e"
CONFIG_FRAGMENT = "configs/gemini-i2c6-fermi.fragment"
CONFIG_FRAGMENT_SHA256 = (
    "e16d1508b3c9001e1106cf6677de39b7a814753f635db442277978322b91ea42"
)
FERMI_PATCH = (
    "v7.1.3/0120-i2c-mediatek-add-fixed-Fermi-topology-fingerprint.patch"
)
FERMI_PATCH_SHA256 = (
    "bf1f7fec2352d0681a6ee00ab506e4bd42bea21681af62db1dd739539b876872"
)

QUASAR_MODULE = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/scripts/candidate_quasar.py"
)
QUASAR_MODULE_SHA256 = (
    "8ecca91a9ae34d2a77017341d20dbd5787aa5c105110e64fdb78fd06c0acce88"
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


def load_quasar() -> ModuleType:
    script = pathlib.Path(__file__).resolve()
    repository = script.parents[3]
    source = repository / QUASAR_MODULE
    data = read_regular(source, "source-pinned Candidate Quasar module")
    if hashlib.sha256(data).hexdigest() != QUASAR_MODULE_SHA256:
        raise ValueError("source-pinned Candidate Quasar module changed")
    spec = importlib.util.spec_from_file_location("fermi_quasar_pins", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Candidate Quasar module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


_QUASAR = load_quasar()

FERMI_PATCHES = _QUASAR.QUASAR_PATCHES + (FERMI_PATCH,)
FERMI_PATCH_SHA256S = _QUASAR.QUASAR_PATCH_SHA256S + (FERMI_PATCH_SHA256,)

# Exact Quasar serviceability, DT, initramfs, and LK assembly foundation.
CASSINI_PACKAGE_DIR = _QUASAR.CASSINI_PACKAGE_DIR
CASSINI_PROVENANCE_SHA256 = _QUASAR.CASSINI_PROVENANCE_SHA256
CASSINI_COMPILED_DTB_SHA256 = _QUASAR.CASSINI_COMPILED_DTB_SHA256
ORION_COMPILED_DTB_SHA256 = _QUASAR.ORION_COMPILED_DTB_SHA256
CASSINI_PACKAGE_VALIDATOR_SHA256 = _QUASAR.CASSINI_PACKAGE_VALIDATOR_SHA256
CASSINI_PINS_SHA256 = _QUASAR.CASSINI_PINS_SHA256
ORION_DTB_VALIDATOR_SHA256 = _QUASAR.ORION_DTB_VALIDATOR_SHA256
ORION_DTB_BUILDER_SHA256 = _QUASAR.ORION_DTB_BUILDER_SHA256
DTB_LINEAGE_VALIDATOR_SHA256 = _QUASAR.DTB_LINEAGE_VALIDATOR_SHA256
HUBBLE_ARTIFACT_DIR = _QUASAR.HUBBLE_ARTIFACT_DIR
HUBBLE_MANIFEST_SHA256 = _QUASAR.HUBBLE_MANIFEST_SHA256
HUBBLE_RAW_SHA256 = _QUASAR.HUBBLE_RAW_SHA256
HUBBLE_RAW_SIZE = _QUASAR.HUBBLE_RAW_SIZE
HUBBLE_PADDED_SHA256 = _QUASAR.HUBBLE_PADDED_SHA256
HUBBLE_BOOT_MEMBER = _QUASAR.HUBBLE_BOOT_MEMBER
HUBBLE_DTB_MEMBER = _QUASAR.HUBBLE_DTB_MEMBER
HUBBLE_DTB_SHA256 = _QUASAR.HUBBLE_DTB_SHA256
ORION_BOOT_DTB_SHA256 = _QUASAR.ORION_BOOT_DTB_SHA256
HUBBLE_INITRAMFS_MEMBER = _QUASAR.HUBBLE_INITRAMFS_MEMBER
HUBBLE_INITRAMFS_SHA256 = _QUASAR.HUBBLE_INITRAMFS_SHA256
HUBBLE_VALIDATOR_SHA256 = _QUASAR.HUBBLE_VALIDATOR_SHA256
HUBBLE_PINS_SHA256 = _QUASAR.HUBBLE_PINS_SHA256
SERIALIZER_SHA256 = _QUASAR.SERIALIZER_SHA256
ANALYZER_SHA256 = _QUASAR.ANALYZER_SHA256
NORMALIZER_SHA256 = _QUASAR.NORMALIZER_SHA256

BOOT_MEMBER = "gemini-mt6797-da9214-fermi.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-da9214-fermi.dtb"
INITRAMFS_MEMBER = HUBBLE_INITRAMFS_MEMBER
PADDED_MEMBER = "boot2-padded.img"
ARTIFACT_PREFIX = "candidate-Fermi-da9214-"
BOOT2_SIZE = _QUASAR.BOOT2_SIZE
I2C6_PATH = _QUASAR.I2C6_PATH
I2C6_COMPATIBLE = _QUASAR.I2C6_COMPATIBLE

PASSES = 2
TRANSFER_ORDER = (
    (0x69, 0x05),
    (0x69, 0x06),
    (0x69, 0x47),
    (0x68, 0xD3),
    (0x68, 0x5E),
    (0x68, 0xD9),
    (0x68, 0xDA),
)
SIGNATURE = (0xD9, 0xD0, 0xC0)
TOPOLOGY_MASK = 0x07
TOPOLOGY_EXPECTED = 0x05
STABILITY_REGISTERS = (0xD3, 0x5E, 0xD9, 0xDA)
PREFILLS = (
    (0xA5, 0x5A, 0x3C, 0x96, 0x69, 0xC3, 0x87),
    (0x78, 0xB4, 0x4B, 0xD2, 0x2D, 0xE1, 0x1E),
)
SAMPLE_COUNT = PASSES * len(TRANSFER_ORDER)


def require_input_pins() -> None:
    _QUASAR.require_input_pins()
    for name, value in {
        "SERIES_SHA256": SERIES_SHA256,
        "CONFIG_FRAGMENT_SHA256": CONFIG_FRAGMENT_SHA256,
        "FERMI_PATCH_SHA256": FERMI_PATCH_SHA256,
        "QUASAR_MODULE_SHA256": QUASAR_MODULE_SHA256,
    }.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Fermi {name} is unresolved or malformed")
    if len(FERMI_PATCHES) != len(FERMI_PATCH_SHA256S):
        raise ValueError("Candidate Fermi patch-pin inventory is inconsistent")
    flattened = tuple(value for row in PREFILLS for value in row)
    if len(flattened) != SAMPLE_COUNT or len(set(flattened)) != SAMPLE_COUNT:
        raise ValueError("Candidate Fermi receive prefills are not all distinct")
    known = set(SIGNATURE) | {TOPOLOGY_EXPECTED}
    if known & set(flattened):
        raise ValueError("Candidate Fermi receive prefill equals a required value")
    if SAMPLE_COUNT != 14:
        raise ValueError("Candidate Fermi transfer count changed")
