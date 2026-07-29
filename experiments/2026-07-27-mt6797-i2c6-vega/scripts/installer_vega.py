"""Pinned identities and safety boundaries for Vega's boot2 installer."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import pathlib
import re
import stat

import candidate_vega as co


# Calibrate these four values only after two independent Vega kernel builds
# and candidate assemblies reproduce. Until then every production derivation
# fails closed before creating an installer.
VEGA_RAW_SHA256 = (
    "08cf45530de0b15441680fafecad1d56557f2285b1d06307fee6ac55ae9b8975"
)
VEGA_RAW_SIZE = 7_747_584
VEGA_PADDED_SHA256 = (
    "4fc71c508c40081c91a48e13af1c8a0ac5fb79871e04d63f98efa4ddbea3e6a7"
)
VEGA_MANIFEST_SHA256 = (
    "0abe52ebbda743bfd031fe856aa82dd8d9e9625620aa810ab1a71b9356f4ae07"
)

# This may remain unresolved for the first calibrated derivation. Fill it with
# that derivation's printed SHA-256, then derive again to pin the installer
# itself.
INSTALLER_SHA256 = (
    "3df562f45481f1ba5cd854d896113df9b9971616e2ceef77bdb3cf91b10949d3"
)
REPRODUCIBILITY_RECORD = (
    "experiments/2026-07-27-mt6797-i2c6-vega/"
    "results/build-reproducibility.txt"
)
REPRODUCIBILITY_RECORD_SHA256 = (
    "cafd78721f867d065d07925db40ea8c2301e774be1cb50e2df384a9ed00398ae"
)
REPRODUCIBILITY_VERIFIER = (
    "experiments/2026-07-27-mt6797-i2c6-vega/"
    "scripts/verify-vega-reproducibility.py"
)
REPRODUCIBILITY_VERIFIER_SHA256 = (
    "bed4403f37b74b69e688b0960a1e155cf208cebb9d09ed180c7a58ae2ab7242a"
)
REPRODUCIBILITY_CANDIDATE_MODULE_SHA256 = (
    "225d134cf36cd025162bf99ef3a3ea0ad83c462b43577b95f933a3b297f0d379"
)
REPRODUCIBILITY_PACKAGE_VALIDATOR_SHA256 = (
    "ef07f12d82c4db233f30a535500e0a688bcb13228b94fea7f8618fa4a6344eee"
)
REPRODUCIBILITY_LK_ANALYZER_SHA256 = (
    "aa25edb2cf9675ab0c90d2655bbf1ad845b41e697f0b40ba1f357cec7646eb95"
)

BOOT2_SIZE = 16 * 1024 * 1024
TARGET = "gemini@192.168.1.50"

# Exact installed and full-readback-verified Orion predecessor required on the
# complete live boot2 partition immediately before Vega is written.
ORION_PADDED_SHA256 = (
    "74f9d9c8cae1213665db2100dda72e0531e0b221cd74a660fc183edcd7bb50d4"
)

# Source-pinned Orion installer foundation.
ORION_DERIVER_SHA256 = (
    "c731ed435628b8d5a8cc981eb4f11dee2a7d1b165c919d9c998fcda205e4fbe2"
)
ORION_PINS_SHA256 = (
    "20a3ef2c5f2c6b8153adf05914333c9eebeaacc3a2d8fc053b8f88e74f577dac"
)
ORION_INSTALLER_SHA256 = (
    "392a1fa9616ca501db0a4af5d49e1542fb3bf23cd8ecfff7ab3b2d082e280c14"
)

EXPERIMENT = co.EXPERIMENT
BOOT_MEMBER = co.BOOT_MEMBER
ARTIFACT_PREFIX = co.ARTIFACT_PREFIX
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
        raw_sha256=VEGA_RAW_SHA256,
        raw_size=VEGA_RAW_SIZE,
        padded_sha256=VEGA_PADDED_SHA256,
        manifest_sha256=VEGA_MANIFEST_SHA256,
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
    values = {
        "VEGA_RAW_SHA256": pins.raw_sha256,
        "VEGA_PADDED_SHA256": pins.padded_sha256,
        "VEGA_MANIFEST_SHA256": pins.manifest_sha256,
    }
    for name, value in values.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate Vega {name} is unresolved or malformed")
    if (
        not isinstance(pins.raw_size, int)
        or isinstance(pins.raw_size, bool)
        or not 0 < pins.raw_size <= BOOT2_SIZE
    ):
        raise ValueError("Candidate Vega VEGA_RAW_SIZE is unresolved or invalid")
    if pins.padded_sha256 == ORION_PADDED_SHA256:
        raise ValueError("Vega padded identity equals its Orion predecessor")
    if len({pins.raw_sha256, pins.padded_sha256, pins.manifest_sha256}) != 3:
        raise ValueError("Vega raw, padded, and manifest identities are not distinct")


def require_installer_pin() -> None:
    if INSTALLER_SHA256 != "UNRESOLVED" and HEX256.fullmatch(INSTALLER_SHA256) is None:
        raise ValueError("Candidate Vega INSTALLER_SHA256 is malformed")


def parse_reproducibility_record(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("ascii")
    except UnicodeError as exc:
        raise ValueError("Vega reproducibility record is not ASCII") from exc
    if not text.endswith("\n") or "\0" in text:
        raise ValueError("Vega reproducibility record framing changed")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.count("=") != 1:
            raise ValueError("Vega reproducibility record grammar changed")
        key, value = line.split("=", 1)
        if not key or not value or key in fields:
            raise ValueError("Vega reproducibility record field is invalid")
        fields[key] = value
    if set(fields) != REPRODUCIBILITY_KEYS:
        raise ValueError("Vega reproducibility record inventory changed")
    return fields


def validate_reproducibility_record(
    data: bytes,
    pins: ArtifactPins,
    verifier_sha256: str = REPRODUCIBILITY_VERIFIER_SHA256,
) -> dict[str, str]:
    require_artifact_pins(pins)
    if HEX256.fullmatch(verifier_sha256) is None:
        raise ValueError("Vega reproducibility verifier identity is malformed")
    fields = parse_reproducibility_record(data)
    exact = {
        "validation": "vega-two-build-2x2-reproducibility",
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
            raise ValueError(f"Vega reproducibility record changed: {key}")
    package_name = fields["package_directory_name"]
    if (
        "/" in package_name
        or package_name in {".", ".."}
        or not package_name.startswith("linux-7.1.3-gemini-")
    ):
        raise ValueError("Vega reproducibility package identity is malformed")
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
            raise ValueError(f"Vega reproducibility hash is malformed: {key}")
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
            raise ValueError("Vega reproducibility lane identity mismatch")
    for key in ("package_normalized_file_count", "candidate_file_count"):
        value = fields[key]
        if not value.isdecimal() or int(value, 10) <= 0:
            raise ValueError(f"Vega reproducibility count is malformed: {key}")
    generated_a = fields["package_a_generated_utc"]
    generated_b = fields["package_b_generated_utc"]
    if generated_a == generated_b or any(
        character.isspace() for character in generated_a + generated_b
    ):
        raise ValueError("Vega build-lane timestamps are not distinct and canonical")
    return fields


def require_reproducibility_record(
    repository: pathlib.Path,
    pins: ArtifactPins,
) -> str:
    if HEX256.fullmatch(REPRODUCIBILITY_VERIFIER_SHA256) is None:
        raise ValueError("Vega reproducibility verifier pin is unresolved")
    verifier = repository / REPRODUCIBILITY_VERIFIER
    verifier_data = read_regular(
        verifier,
        "Vega reproducibility verifier",
    )
    if hashlib.sha256(verifier_data).hexdigest() != (
        REPRODUCIBILITY_VERIFIER_SHA256
    ):
        raise ValueError("source-pinned Vega reproducibility verifier changed")
    if HEX256.fullmatch(REPRODUCIBILITY_RECORD_SHA256) is None:
        raise ValueError("Vega reproducibility record pin is unresolved")
    record = repository / REPRODUCIBILITY_RECORD
    data = read_regular(record, "Vega reproducibility record")
    actual = hashlib.sha256(data).hexdigest()
    if actual != REPRODUCIBILITY_RECORD_SHA256:
        raise ValueError("source-pinned Vega reproducibility record changed")
    validate_reproducibility_record(data, pins)
    return actual


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
