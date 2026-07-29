"""Pinned inputs and safety boundaries for Candidate Curie."""

from __future__ import annotations

import hashlib
import importlib.util
import pathlib
import re
import stat
import sys
from types import ModuleType


EXPERIMENT = "2026-07-28-da9214-curie"
CANDIDATE = "Curie"
PROFILE = (
    "observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-"
    "a72-observer-initcall-blacklist-dvfsp-handoff-owner-i2c6-consumer-"
    "ap-dma-preserve-curie"
)
SERIES = "patches/series-curie-i2c6-board-tuple"
SERIES_SHA256 = "cf383ee6397130dfd9d3b725c13619a6bfb0a250ddb40a28e4440a5de961de49"
CONFIG_FRAGMENT = "configs/gemini-i2c6-curie.fragment"
CONFIG_FRAGMENT_SHA256 = (
    "a6b0f0e52ce5904de5f55a0c8bad66e7df001d493c7012a3823d570d2243a2a0"
)
CURIE_PATCH = (
    "v7.1.3/0121-i2c-mediatek-require-exact-Curie-board-control.patch"
)
CURIE_PATCH_SHA256 = (
    "f82ad98c9bb6fb1f99bca9c778d0b1853f9ec3bbed2ce59e9643680826a7750c"
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
    spec = importlib.util.spec_from_file_location("curie_fermi_pins", source)
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

CURIE_PATCHES = _FERMI.FERMI_PATCHES + (CURIE_PATCH,)
CURIE_PATCH_SHA256S = _FERMI.FERMI_PATCH_SHA256S + (CURIE_PATCH_SHA256,)

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

BOOT_MEMBER = "gemini-mt6797-da9214-curie.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-da9214-curie.dtb"
INITRAMFS_MEMBER = HUBBLE_INITRAMFS_MEMBER
PADDED_MEMBER = "boot2-padded.img"
ARTIFACT_PREFIX = "candidate-Curie-da9214-"
BOOT2_SIZE = _FERMI.BOOT2_SIZE
I2C6_PATH = _FERMI.I2C6_PATH
I2C6_COMPATIBLE = _FERMI.I2C6_COMPATIBLE

PASSES = _FERMI.PASSES
TRANSFER_ORDER = _FERMI.TRANSFER_ORDER
SIGNATURE = _FERMI.SIGNATURE
BOARD_CONTROL_REGISTER = 0xD3
BOARD_CONTROL_EXPECTED = 0x1F
STABILITY_REGISTERS = _FERMI.STABILITY_REGISTERS
PREFILLS = _FERMI.PREFILLS
SAMPLE_COUNT = PASSES * len(TRANSFER_ORDER)

# Independent private Gemian boot logs, with trackable hash provenance, carry
# this comparison tuple. It is not a Curie acceptance gate or a silicon ID.
GEMIAN_PRIMARY_TUPLE = (0x1F, 0x00, 0x46, 0x46)


def require_input_pins() -> None:
    _FERMI.require_input_pins()
    for name, value in {
        "SERIES_SHA256": SERIES_SHA256,
        "CONFIG_FRAGMENT_SHA256": CONFIG_FRAGMENT_SHA256,
        "CURIE_PATCH_SHA256": CURIE_PATCH_SHA256,
        "FERMI_MODULE_SHA256": FERMI_MODULE_SHA256,
    }.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Curie {name} is unresolved or malformed")
    if len(CURIE_PATCHES) != len(CURIE_PATCH_SHA256S):
        raise ValueError("Candidate Curie patch-pin inventory is inconsistent")
    if TRANSFER_ORDER != _FERMI.TRANSFER_ORDER or PREFILLS != _FERMI.PREFILLS:
        raise ValueError("Candidate Curie changed Fermi transfer or prefill policy")
    flattened = tuple(value for row in PREFILLS for value in row)
    if len(flattened) != SAMPLE_COUNT or len(set(flattened)) != SAMPLE_COUNT:
        raise ValueError("Candidate Curie receive prefills are not all distinct")
    required_values = set(SIGNATURE) | {BOARD_CONTROL_EXPECTED}
    if required_values & set(flattened):
        raise ValueError("Candidate Curie receive prefill equals a required value")
    if set(GEMIAN_PRIMARY_TUPLE) & set(flattened):
        raise ValueError("Candidate Curie receive prefill collides with Gemian tuple")
    if SAMPLE_COUNT != 14:
        raise ValueError("Candidate Curie transfer count changed")
