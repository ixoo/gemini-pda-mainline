"""Pinned identities and safety boundaries for Quasar's boot2 installer."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import pathlib
import re
import stat

import candidate_quasar as co


# Resolve only after both Quasar build lanes and all four assembly lanes
# reproduce. Production derivation fails closed while any value is unresolved.
QUASAR_RAW_SHA256 = (
    "c621e87431641a16af65ae3d144bfc97cd6c01c28b4ce4e9f81fc6e7ea428010"
)
QUASAR_RAW_SIZE = 7_747_584
QUASAR_PADDED_SHA256 = (
    "73fceae91606ebf831e503585406df1e2be997edc9fddff1bcae9ec718c91d78"
)
QUASAR_MANIFEST_SHA256 = (
    "d5a57361181385e39d12a0c0ee6761318b18fa33dd2b90d7af8ea3fff4b9d62c"
)
INSTALLER_SHA256 = (
    "04e565aede2c2680ea648e593dc66f40f017f0ab78c208965aa6c6437637e395"
)

REPRODUCIBILITY_RECORD = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/"
    "results/build-reproducibility.txt"
)
REPRODUCIBILITY_RECORD_SHA256 = (
    "ce99a7496ba328bde6b2bcf432653a2c97e86bae2b8eee07a90353acfab47f88"
)
REPRODUCIBILITY_VERIFIER = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/"
    "scripts/verify-quasar-reproducibility.py"
)
REPRODUCIBILITY_VERIFIER_SHA256 = (
    "88b9257cd21ee81a92b72d1beb99819bd8773e2c49e128cea3645d7a46011b14"
)
REPRODUCIBILITY_CANDIDATE_MODULE_SHA256 = (
    "8ecca91a9ae34d2a77017341d20dbd5787aa5c105110e64fdb78fd06c0acce88"
)
REPRODUCIBILITY_PACKAGE_VALIDATOR_SHA256 = (
    "bdf18fcf4b8dd1668ff80d50645ea57488e98eee05bb6eb65520faaad40602d5"
)
REPRODUCIBILITY_LK_ANALYZER_SHA256 = co.ANALYZER_SHA256

TARGET = "gemini@192.168.1.50"
BOOT2_SIZE = co.BOOT2_SIZE
EXPERIMENT = co.EXPERIMENT
BOOT_MEMBER = co.BOOT_MEMBER
ARTIFACT_PREFIX = co.ARTIFACT_PREFIX

# The predecessor is not inferred from a filename. It is pinned by the exact
# durable Vega installation record, whose post-flush and full local readback
# both name this complete 16 MiB partition identity.
VEGA_PADDED_SHA256 = (
    "4fc71c508c40081c91a48e13af1c8a0ac5fb79871e04d63f98efa4ddbea3e6a7"
)
VEGA_INSTALL_RECORD = (
    "experiments/2026-07-27-mt6797-i2c6-vega/"
    "results/install-boot2-20260727.txt"
)
VEGA_INSTALL_RECORD_SHA256 = (
    "d95e715c4278297565e14bb1023d94f8b32ce5e386ec73b36f44030b9cc1dea5"
)

# Exact source-pinned machinery used to reconstruct the complete Vega
# installer foundation before applying Quasar-only identities.
VEGA_DERIVER = (
    "experiments/2026-07-27-mt6797-i2c6-vega/scripts/derive-installer.py"
)
VEGA_DERIVER_SHA256 = (
    "3fc2322f18c542c474f62b2fee543e0fc65e558f8c4fcb031238063c550db164"
)
VEGA_PINS = (
    "experiments/2026-07-27-mt6797-i2c6-vega/scripts/installer_vega.py"
)
VEGA_PINS_SHA256 = (
    "e13a627aed840bc8f0fb800cb934cf2d0918e76b959c700a1be67fad3b92de42"
)
VEGA_INSTALLER_SHA256 = (
    "3df562f45481f1ba5cd854d896113df9b9971616e2ceef77bdb3cf91b10949d3"
)

HEX256 = re.compile(r"^[0-9a-f]{64}$")
REPRODUCIBILITY_KEYS = frozenset(
    {
        "validation",
        "experiment",
        "verifier_sha256",
        "candidate_module_sha256",
        "package_validator_sha256",
        "lk_analyzer_sha256",
        "package_lane_count",
        "candidate_lane_count",
        "matrix",
        "package_directory_name",
        "package_a_manifest_sha256",
        "package_b_manifest_sha256",
        "package_a_generated_utc",
        "package_b_generated_utc",
        "package_normalized_file_count",
        "package_normalized_inventory_sha256",
        "package_a_normalized_inventory_sha256",
        "package_b_normalized_inventory_sha256",
        "package_normalized_build_sha256",
        "package_a_normalized_build_sha256",
        "package_b_normalized_build_sha256",
        "candidate_directory_name",
        "candidate_file_count",
        "candidate_inventory_sha256",
        "candidate_a_a_inventory_sha256",
        "candidate_a_b_inventory_sha256",
        "candidate_b_a_inventory_sha256",
        "candidate_b_b_inventory_sha256",
        "candidate_raw_member",
        "candidate_raw_size",
        "candidate_raw_sha256",
        "candidate_padded_member",
        "candidate_padded_size",
        "candidate_padded_sha256",
        "candidate_manifest_sha256",
        "candidate_boot_dtb_sha256",
        "candidate_initramfs_sha256",
        "candidate_lk_analysis_sha256",
        "package_a_candidate_lanes",
        "package_b_candidate_lanes",
        "package_mode_byte_equality",
        "candidate_mode_byte_equality",
        "normalized_build_provenance",
        "candidate_lk_validation",
        "candidate_padded_construction",
        "device_access",
        "runtime_result",
    }
)


@dataclass(frozen=True)
class ArtifactPins:
    raw_sha256: str
    raw_size: int
    padded_sha256: str
    manifest_sha256: str

    @property
    def artifact_dir(self) -> str:
        return f"{ARTIFACT_PREFIX}{self.raw_sha256[:8]}"


def production_pins() -> ArtifactPins:
    return ArtifactPins(
        raw_sha256=QUASAR_RAW_SHA256,
        raw_size=QUASAR_RAW_SIZE,
        padded_sha256=QUASAR_PADDED_SHA256,
        manifest_sha256=QUASAR_MANIFEST_SHA256,
    )


def pins_resolved(pins: ArtifactPins) -> bool:
    return (
        HEX256.fullmatch(pins.raw_sha256) is not None
        and HEX256.fullmatch(pins.padded_sha256) is not None
        and HEX256.fullmatch(pins.manifest_sha256) is not None
        and HEX256.fullmatch(REPRODUCIBILITY_RECORD_SHA256) is not None
        and isinstance(pins.raw_size, int)
        and not isinstance(pins.raw_size, bool)
        and 0 < pins.raw_size <= BOOT2_SIZE
    )


def require_artifact_pins(pins: ArtifactPins) -> None:
    for name, value in {
        "QUASAR_RAW_SHA256": pins.raw_sha256,
        "QUASAR_PADDED_SHA256": pins.padded_sha256,
        "QUASAR_MANIFEST_SHA256": pins.manifest_sha256,
    }.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Quasar {name} is unresolved or malformed")
    if (
        not isinstance(pins.raw_size, int)
        or isinstance(pins.raw_size, bool)
        or not 0 < pins.raw_size <= BOOT2_SIZE
    ):
        raise ValueError("Candidate Quasar QUASAR_RAW_SIZE is unresolved or invalid")
    if pins.padded_sha256 == VEGA_PADDED_SHA256:
        raise ValueError("Quasar padded identity equals its Vega predecessor")
    if len({pins.raw_sha256, pins.padded_sha256, pins.manifest_sha256}) != 3:
        raise ValueError("Quasar raw, padded, and manifest identities are not distinct")


def require_installer_pin() -> None:
    if INSTALLER_SHA256 != "UNRESOLVED" and HEX256.fullmatch(INSTALLER_SHA256) is None:
        raise ValueError("Candidate Quasar INSTALLER_SHA256 is malformed")


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def parse_key_values(data: bytes, label: str) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise ValueError(f"{label} is not ASCII") from exc
    if not text.endswith("\n") or "\0" in text:
        raise ValueError(f"{label} framing changed")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.count("=") != 1:
            raise ValueError(f"{label} grammar changed")
        key, value = line.split("=", 1)
        if not key or not value or key in fields:
            raise ValueError(f"{label} contains an invalid field")
        fields[key] = value
    return fields


def require_predecessor_evidence(repository: pathlib.Path) -> str:
    record = repository / VEGA_INSTALL_RECORD
    data = read_regular(record, "exact Vega boot2 installation record")
    actual = hashlib.sha256(data).hexdigest()
    if actual != VEGA_INSTALL_RECORD_SHA256:
        raise ValueError("source-pinned Vega boot2 installation record changed")
    fields = parse_key_values(data, "Vega boot2 installation record")
    exact = {
        "experiment": "2026-07-27-mt6797-i2c6-vega",
        "candidate": "Vega",
        "target_resolution": "live-GPT-exact-single-boot2-row",
        "target_size": str(BOOT2_SIZE),
        "target_writable": "yes",
        "target_mounted": "no",
        "target_active_swap": "no",
        "target_holders": "none",
        "target_active_root": "no",
        "candidate_padded_size": str(BOOT2_SIZE),
        "candidate_padded_sha256": VEGA_PADDED_SHA256,
        "remote_post_flush_sha256": VEGA_PADDED_SHA256,
        "local_full_readback_bytes": str(BOOT2_SIZE),
        "local_full_readback_sha256": VEGA_PADDED_SHA256,
        "local_full_readback_byte_equality": "exact",
        "remote_staging_removed": "yes",
        "result": "write-synced-flushed-full-readback-verified",
        "reboot_or_shutdown_performed": "no",
    }
    for key, wanted in exact.items():
        if fields.get(key) != wanted:
            raise ValueError(f"Vega predecessor evidence changed: {key}")
    return actual


def parse_reproducibility_record(data: bytes) -> dict[str, str]:
    fields = parse_key_values(data, "Quasar reproducibility record")
    if set(fields) != REPRODUCIBILITY_KEYS:
        raise ValueError("Quasar reproducibility record inventory changed")
    return fields


def validate_reproducibility_record(
    data: bytes,
    pins: ArtifactPins,
    verifier_sha256: str = REPRODUCIBILITY_VERIFIER_SHA256,
) -> dict[str, str]:
    require_artifact_pins(pins)
    if HEX256.fullmatch(verifier_sha256) is None:
        raise ValueError("Quasar reproducibility verifier identity is malformed")
    fields = parse_reproducibility_record(data)
    exact = {
        "validation": "quasar-two-build-2x2-reproducibility",
        "experiment": EXPERIMENT,
        "verifier_sha256": verifier_sha256,
        "candidate_module_sha256": REPRODUCIBILITY_CANDIDATE_MODULE_SHA256,
        "package_validator_sha256": REPRODUCIBILITY_PACKAGE_VALIDATOR_SHA256,
        "lk_analyzer_sha256": REPRODUCIBILITY_LK_ANALYZER_SHA256,
        "package_lane_count": "2",
        "candidate_lane_count": "4",
        "matrix": (
            "package-a/cassini-a,package-a/cassini-b,"
            "package-b/cassini-a,package-b/cassini-b"
        ),
        "candidate_directory_name": pins.artifact_dir,
        "candidate_raw_member": BOOT_MEMBER,
        "candidate_raw_size": str(pins.raw_size),
        "candidate_raw_sha256": pins.raw_sha256,
        "candidate_padded_member": co.PADDED_MEMBER,
        "candidate_padded_size": str(BOOT2_SIZE),
        "candidate_padded_sha256": pins.padded_sha256,
        "candidate_manifest_sha256": pins.manifest_sha256,
        "candidate_boot_dtb_sha256": co.ORION_BOOT_DTB_SHA256,
        "candidate_initramfs_sha256": co.HUBBLE_INITRAMFS_SHA256,
        "package_a_candidate_lanes": "2",
        "package_b_candidate_lanes": "2",
        "package_mode_byte_equality": "exact",
        "candidate_mode_byte_equality": "exact",
        "normalized_build_provenance": "exact-except-generated_utc",
        "candidate_lk_validation": "source-pinned-32-gates",
        "candidate_padded_construction": "raw-prefix-zero-tail",
        "device_access": "none",
        "runtime_result": "not-tested",
    }
    for key, wanted in exact.items():
        if fields.get(key) != wanted:
            raise ValueError(f"Quasar reproducibility record changed: {key}")
    package = fields["package_directory_name"]
    if "/" in package or package in {".", ".."} or not package.startswith(
        "linux-7.1.3-gemini-"
    ):
        raise ValueError("Quasar reproducibility package identity is malformed")
    hash_fields = (
        "package_a_manifest_sha256",
        "package_b_manifest_sha256",
        "package_normalized_inventory_sha256",
        "package_a_normalized_inventory_sha256",
        "package_b_normalized_inventory_sha256",
        "package_normalized_build_sha256",
        "package_a_normalized_build_sha256",
        "package_b_normalized_build_sha256",
        "candidate_inventory_sha256",
        "candidate_a_a_inventory_sha256",
        "candidate_a_b_inventory_sha256",
        "candidate_b_a_inventory_sha256",
        "candidate_b_b_inventory_sha256",
        "candidate_lk_analysis_sha256",
    )
    for key in hash_fields:
        if HEX256.fullmatch(fields[key]) is None:
            raise ValueError(f"Quasar reproducibility hash is malformed: {key}")
    equality_groups = (
        (
            "package_normalized_inventory_sha256",
            "package_a_normalized_inventory_sha256",
            "package_b_normalized_inventory_sha256",
        ),
        (
            "package_normalized_build_sha256",
            "package_a_normalized_build_sha256",
            "package_b_normalized_build_sha256",
        ),
        (
            "candidate_inventory_sha256",
            "candidate_a_a_inventory_sha256",
            "candidate_a_b_inventory_sha256",
            "candidate_b_a_inventory_sha256",
            "candidate_b_b_inventory_sha256",
        ),
    )
    for keys in equality_groups:
        if len({fields[key] for key in keys}) != 1:
            raise ValueError("Quasar reproducibility lane identity mismatch")
    for key in ("package_normalized_file_count", "candidate_file_count"):
        if not fields[key].isdecimal() or int(fields[key], 10) <= 0:
            raise ValueError(f"Quasar reproducibility count is malformed: {key}")
    if fields["package_a_generated_utc"] == fields["package_b_generated_utc"]:
        raise ValueError("Quasar build-lane timestamps are not distinct")
    return fields


def require_reproducibility_record(
    repository: pathlib.Path,
    pins: ArtifactPins,
) -> str:
    verifier = repository / REPRODUCIBILITY_VERIFIER
    if HEX256.fullmatch(REPRODUCIBILITY_VERIFIER_SHA256) is None:
        raise ValueError("Quasar reproducibility verifier pin is unresolved")
    if digest_path(verifier) != REPRODUCIBILITY_VERIFIER_SHA256:
        raise ValueError("source-pinned Quasar reproducibility verifier changed")
    if HEX256.fullmatch(REPRODUCIBILITY_RECORD_SHA256) is None:
        raise ValueError("Quasar reproducibility record pin is unresolved")
    data = read_regular(
        repository / REPRODUCIBILITY_RECORD,
        "Quasar reproducibility record",
    )
    actual = hashlib.sha256(data).hexdigest()
    if actual != REPRODUCIBILITY_RECORD_SHA256:
        raise ValueError("source-pinned Quasar reproducibility record changed")
    validate_reproducibility_record(data, pins)
    return actual
