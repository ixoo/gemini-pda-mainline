#!/usr/bin/env python3
"""Derive Fermi's guarded boot2 installer from exact Quasar machinery."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import os
import pathlib
import stat
import subprocess
import sys
import tempfile
from types import ModuleType

sys.dont_write_bytecode = True
import candidate_fermi as co


QUASAR_DERIVER = (
    "experiments/2026-07-27-mt6797-i2c6-quasar/scripts/derive-installer.py"
)
QUASAR_DERIVER_SHA256 = (
    "585fb3094aefd96d866b393c201abd7f0670a39a2ecb7d11e887e35e7b0d9400"
)
QUASAR_PADDED_SHA256 = (
    "73fceae91606ebf831e503585406df1e2be997edc9fddff1bcae9ec718c91d78"
)
REPRODUCIBILITY_RECORD = (
    "experiments/2026-07-28-da9214-fermi/results/build-reproducibility.txt"
)
REPRODUCIBILITY_RECORD_SHA256 = "bddb4e126d87289b253872063713d12e61a36b088e551e61afc63534634a5fd6"
REPRODUCIBILITY_VERIFIER = (
    "experiments/2026-07-28-da9214-fermi/"
    "scripts/verify-fermi-reproducibility.py"
)
REPRODUCIBILITY_VERIFIER_SHA256 = (
    "11bbabe6f913dc93943e525f3587e1f1b2979ff5846f924c6edf19f5eb8ee4af"
)
CANDIDATE_MODULE = (
    "experiments/2026-07-28-da9214-fermi/scripts/candidate_fermi.py"
)
CANDIDATE_MODULE_SHA256 = (
    "3422bb29490f21f0410d4d45f521fc3ac89eff3679d117535c7b5dcf0cffe5e6"
)
PACKAGE_VALIDATOR = (
    "experiments/2026-07-28-da9214-fermi/"
    "scripts/validate-package-fermi.py"
)
PACKAGE_VALIDATOR_SHA256 = (
    "20c15b859a1fb04f562ff4955fff034bec65edbdceea17c1a9062f4be3585fc2"
)
BOOT2_SIZE = 16 * 1024 * 1024
HEX256 = frozenset("0123456789abcdef")
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
    artifact_dir: str
    raw_sha256: str
    raw_size: int
    padded_sha256: str
    manifest_sha256: str


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def regular(path: pathlib.Path, label: str) -> bytes:
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


def exact_hash(value: str, label: str) -> str:
    if len(value) != 64 or any(character not in HEX256 for character in value):
        raise ValueError(f"{label} is not lowercase SHA-256")
    return value


def validate_record(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("ascii", "strict")
    except UnicodeError as exc:
        raise ValueError("Fermi reproducibility record is not ASCII") from exc
    if not text.endswith("\n") or "\0" in text:
        raise ValueError("Fermi reproducibility record framing changed")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.count("=") != 1:
            raise ValueError("Fermi reproducibility record grammar changed")
        key, value = line.split("=", 1)
        if not key or not value or key in fields:
            raise ValueError("Fermi reproducibility record has invalid fields")
        fields[key] = value
    if set(fields) != REPRODUCIBILITY_KEYS:
        raise ValueError("Fermi reproducibility record field inventory changed")
    required = {
        "validation": "fermi-two-build-2x2-reproducibility",
        "experiment": co.EXPERIMENT,
        "verifier_sha256": REPRODUCIBILITY_VERIFIER_SHA256,
        "candidate_module_sha256": CANDIDATE_MODULE_SHA256,
        "package_validator_sha256": PACKAGE_VALIDATOR_SHA256,
        "lk_analyzer_sha256": co.ANALYZER_SHA256,
        "package_lane_count": "2",
        "candidate_lane_count": "4",
        "matrix": (
            "package-a/cassini-a,package-a/cassini-b,"
            "package-b/cassini-a,package-b/cassini-b"
        ),
        "candidate_raw_member": co.BOOT_MEMBER,
        "candidate_padded_member": co.PADDED_MEMBER,
        "candidate_padded_size": str(BOOT2_SIZE),
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
    for key, wanted in required.items():
        if fields.get(key) != wanted:
            raise ValueError(f"Fermi reproducibility record changed: {key}")
    hash_fields = (
        "verifier_sha256",
        "candidate_module_sha256",
        "package_validator_sha256",
        "lk_analyzer_sha256",
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
        "candidate_raw_sha256",
        "candidate_padded_sha256",
        "candidate_manifest_sha256",
        "candidate_lk_analysis_sha256",
    )
    for key in hash_fields:
        exact_hash(fields.get(key, ""), f"record {key}")
    if not fields.get("candidate_raw_size", "").isdecimal():
        raise ValueError("Fermi raw size is malformed")
    raw_size = int(fields["candidate_raw_size"], 10)
    if not 0 < raw_size < BOOT2_SIZE:
        raise ValueError("Fermi raw size is out of bounds")
    if fields["candidate_padded_sha256"] == QUASAR_PADDED_SHA256:
        raise ValueError("Fermi padded image equals exact Quasar predecessor")
    identities = {
        fields["candidate_raw_sha256"],
        fields["candidate_padded_sha256"],
        fields["candidate_manifest_sha256"],
    }
    if len(identities) != 3:
        raise ValueError("Fermi raw, padded, and manifest identities collide")
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
            raise ValueError("Fermi reproducibility lane identity mismatch")
    for key in ("package_normalized_file_count", "candidate_file_count"):
        if not fields[key].isdecimal() or int(fields[key], 10) <= 0:
            raise ValueError(f"Fermi reproducibility count is malformed: {key}")
    if fields["package_a_generated_utc"] == fields["package_b_generated_utc"]:
        raise ValueError("Fermi build-lane timestamps are not distinct")
    package = fields["package_directory_name"]
    if (
        "/" in package
        or package in {".", ".."}
        or not package.startswith("linux-7.1.3-gemini-")
    ):
        raise ValueError("Fermi package directory identity is malformed")
    expected_dir = co.ARTIFACT_PREFIX + fields["candidate_raw_sha256"][:8]
    if fields.get("candidate_directory_name") != expected_dir:
        raise ValueError("Fermi artifact directory identity changed")
    return fields


def parse_record(repository: pathlib.Path) -> dict[str, str]:
    if len(REPRODUCIBILITY_RECORD_SHA256) != 64 or any(
        character not in HEX256 for character in REPRODUCIBILITY_RECORD_SHA256
    ):
        raise ValueError("Fermi reproducibility-record pin is unresolved")
    sources = {
        REPRODUCIBILITY_VERIFIER: REPRODUCIBILITY_VERIFIER_SHA256,
        CANDIDATE_MODULE: CANDIDATE_MODULE_SHA256,
        PACKAGE_VALIDATOR: PACKAGE_VALIDATOR_SHA256,
    }
    for relative, wanted in sources.items():
        if digest_path(repository / relative) != wanted:
            raise ValueError(f"source-pinned Fermi tool changed: {relative}")
    data = regular(
        repository / REPRODUCIBILITY_RECORD,
        "source-pinned Fermi reproducibility record",
    )
    if hashlib.sha256(data).hexdigest() != REPRODUCIBILITY_RECORD_SHA256:
        raise ValueError("source-pinned Fermi reproducibility record changed")
    return validate_record(data)


def validate_manifest(root: pathlib.Path, wanted_sha256: str) -> None:
    manifest_path = root / "SHA256SUMS"
    data = regular(manifest_path, "Fermi artifact checksum manifest")
    if hashlib.sha256(data).hexdigest() != wanted_sha256:
        raise ValueError("Fermi artifact checksum-manifest identity changed")
    seen: set[str] = set()
    for line in data.decode("ascii", "strict").splitlines():
        if len(line) < 67 or line[64:66] != "  ":
            raise ValueError("Fermi artifact checksum line is malformed")
        wanted, name = line[:64], line[66:]
        exact_hash(wanted, "artifact member hash")
        if not name.startswith("./"):
            raise ValueError("Fermi artifact checksum path lacks canonical ./")
        relative = name[2:]
        path = pathlib.PurePosixPath(relative)
        if (
            path.is_absolute()
            or ".." in path.parts
            or path.as_posix() != relative
            or relative in seen
            or relative == "SHA256SUMS"
        ):
            raise ValueError("Fermi artifact checksum path is unsafe")
        seen.add(relative)
        member = root / relative
        regular(member, f"Fermi artifact member {relative}")
        if digest_path(member) != wanted:
            raise ValueError(f"Fermi artifact checksum failed: {relative}")
    for required in (co.BOOT_MEMBER, co.PADDED_MEMBER):
        if required not in seen:
            raise ValueError(f"Fermi artifact manifest lacks {required}")


def validate_artifact(
    candidate_dir: pathlib.Path,
    fields: dict[str, str],
) -> ArtifactPins:
    root = candidate_dir.resolve(strict=True)
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("Fermi artifact directory is unsafe")
    if root.name != fields["candidate_directory_name"]:
        raise ValueError("Fermi artifact directory differs from record")
    validate_manifest(root, fields["candidate_manifest_sha256"])
    raw = root / co.BOOT_MEMBER
    padded = root / co.PADDED_MEMBER
    raw_size = raw.stat().st_size
    if raw_size != int(fields["candidate_raw_size"], 10):
        raise ValueError("Fermi raw size differs from record")
    if digest_path(raw) != fields["candidate_raw_sha256"]:
        raise ValueError("Fermi raw hash differs from record")
    if padded.stat().st_size != BOOT2_SIZE:
        raise ValueError("Fermi padded size changed")
    if digest_path(padded) != fields["candidate_padded_sha256"]:
        raise ValueError("Fermi padded hash differs from record")
    with raw.open("rb") as source, padded.open("rb") as constructed:
        while block := source.read(1024 * 1024):
            if constructed.read(len(block)) != block:
                raise ValueError("Fermi padded image lacks exact raw prefix")
        for block in iter(lambda: constructed.read(1024 * 1024), b""):
            if any(block):
                raise ValueError("Fermi padded image tail is not all zero")
    return ArtifactPins(
        artifact_dir=root.name,
        raw_sha256=fields["candidate_raw_sha256"],
        raw_size=raw_size,
        padded_sha256=fields["candidate_padded_sha256"],
        manifest_sha256=fields["candidate_manifest_sha256"],
    )


def load_quasar_deriver(repository: pathlib.Path) -> ModuleType:
    path = repository / QUASAR_DERIVER
    data = regular(path, "source-pinned Quasar installer deriver")
    if hashlib.sha256(data).hexdigest() != QUASAR_DERIVER_SHA256:
        raise ValueError("source-pinned Quasar installer deriver changed")
    spec = importlib.util.spec_from_file_location("fermi_quasar_installer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Quasar installer deriver")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.fspath(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.path[0]
    return module


def derive_text(source: str, pins: ArtifactPins, quasar: ModuleType) -> str:
    qio = quasar.io
    specific = (
        (
            f"readonly QUASAR_RAW_SHA256={qio.QUASAR_RAW_SHA256}",
            f"readonly QUASAR_RAW_SHA256={pins.raw_sha256}",
            1,
        ),
        (
            f"readonly QUASAR_RAW_SIZE={qio.QUASAR_RAW_SIZE}",
            f"readonly QUASAR_RAW_SIZE={pins.raw_size}",
            1,
        ),
        (
            f"readonly QUASAR_PADDED_SHA256={qio.QUASAR_PADDED_SHA256}",
            f"readonly QUASAR_PADDED_SHA256={pins.padded_sha256}",
            1,
        ),
        (
            "readonly QUASAR_ARTIFACT_MANIFEST_SHA256="
            f"{qio.QUASAR_MANIFEST_SHA256}",
            "readonly QUASAR_ARTIFACT_MANIFEST_SHA256="
            f"{pins.manifest_sha256}",
            1,
        ),
        (
            f'expected_artifact_name="{qio.production_pins().artifact_dir}"',
            f'expected_artifact_name="{pins.artifact_dir}"',
            1,
        ),
        (
            "gemini-mt6797-i2c6-quasar.boot.img",
            co.BOOT_MEMBER,
            1,
        ),
        (
            "2026-07-27-mt6797-i2c6-quasar",
            co.EXPERIMENT,
            2,
        ),
    )
    text = source
    for old, new, count in specific:
        text = replace_exact(text, old, new, count)
    identity = (
        ("QUASAR", "FERMI", 31),
        ("Quasar", "Fermi", 10),
        ("quasar", "fermi", 20),
    )
    for old, new, count in identity:
        text = replace_exact(text, old, new, count)
    predecessor = (
        (
            "EXPECTED_CURRENT_VEGA_PADDED_SHA256",
            "EXPECTED_CURRENT_QUASAR_PADDED_SHA256",
            8,
        ),
        (
            "Vega-installed-readback-verified",
            "Quasar-installed-readback-verified",
            4,
        ),
        (
            f"readonly EXPECTED_CURRENT_QUASAR_PADDED_SHA256={qio.VEGA_PADDED_SHA256}",
            "readonly EXPECTED_CURRENT_QUASAR_PADDED_SHA256="
            f"{QUASAR_PADDED_SHA256}",
            1,
        ),
    )
    for old, new, count in predecessor:
        text = replace_exact(text, old, new, count)

    required_counts = {
        f"readonly FERMI_RAW_SHA256={pins.raw_sha256}": 1,
        f"readonly FERMI_RAW_SIZE={pins.raw_size}": 1,
        f"readonly FERMI_PADDED_SHA256={pins.padded_sha256}": 1,
        "readonly FERMI_ARTIFACT_MANIFEST_SHA256="
        f"{pins.manifest_sha256}": 1,
        "readonly EXPECTED_CURRENT_QUASAR_PADDED_SHA256="
        f"{QUASAR_PADDED_SHA256}": 1,
        f'expected_artifact_name="{pins.artifact_dir}"': 1,
        f'[[ "$candidate_name" == {co.BOOT_MEMBER} ]]': 1,
        f"experiment={co.EXPERIMENT}": 2,
        "candidate_label=Fermi": 2,
        "EXPECTED_CURRENT_QUASAR_PADDED_SHA256": 8,
        "Quasar-installed-readback-verified": 4,
        'dd if="$root_stage_file" of="$target"': 1,
        'of="$target"': 1,
        "reboot_or_shutdown_performed=no": 2,
        "[[ \"$(uname -r)\" == 3.18.41+ ]]": 2,
        "[[ \"$active_root\" == /dev/mmcblk0p29 ]]": 1,
        "battery_capacity >= 81 && battery_capacity <= 100": 1,
        'blockdev --flushbufs "$target"': 1,
        'cmp -s "$padded" "$readback_partial"': 1,
    }
    for token, wanted in required_counts.items():
        if text.count(token) != wanted:
            raise ValueError(
                f"derived Fermi installer safety contract changed for {token!r}"
            )
    for stale in (
        "EXPECTED_CURRENT_VEGA",
        "Vega-installed-readback-verified",
        "gemini-mt6797-i2c6-quasar.boot.img",
        "2026-07-27-mt6797-i2c6-quasar",
    ):
        if stale in text:
            raise ValueError(f"derived Fermi installer retains stale token: {stale}")
    for forbidden in (
        "reboot ",
        "shutdown ",
        "poweroff ",
        "kexec ",
        "sysrq",
        "sudo -S",
        "SSH_ASKPASS",
        "of=/dev/mmc",
    ):
        if forbidden in text:
            raise ValueError(f"derived Fermi installer gained {forbidden!r}")
    return text


def safe_output(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ValueError("installer output is invalid or already exists")
    parent = path.parent.resolve(strict=True)
    info = parent.lstat()
    if parent.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("installer output parent is unsafe")
    return parent / path.name


def publish(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-dir", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        repository = pathlib.Path(__file__).resolve().parents[3]
        fields = parse_record(repository)
        pins = validate_artifact(args.candidate_dir, fields)
        output = safe_output(args.output)
        quasar = load_quasar_deriver(repository)
        with tempfile.TemporaryDirectory(
            prefix=".fermi-quasar-installer.", dir=output.parent
        ) as raw:
            source = quasar.reconstruct_vega(pathlib.Path(raw))
        quasar_text = quasar.derive_text(source, quasar.io.production_pins())
        text = derive_text(quasar_text, pins, quasar)
        publish(output, text)
        print("validation=fermi-installer-derived")
        print(f"installer_sha256={hashlib.sha256(text.encode()).hexdigest()}")
        print(f"artifact={pins.artifact_dir}")
        print(f"candidate_raw_sha256={pins.raw_sha256}")
        print(f"candidate_raw_size={pins.raw_size}")
        print(f"candidate_manifest_sha256={pins.manifest_sha256}")
        print(f"candidate_padded_sha256={pins.padded_sha256}")
        print(f"expected_predecessor_sha256={QUASAR_PADDED_SHA256}")
        print("accepted_target=gemini@192.168.1.50")
        print("sole_target_write=one-bounded-16MiB-boot2-write")
        print("stable_power=battery-present-health-Good-capacity-81..100")
        print("ac_usb_online=observational-only")
        print("reboot_or_slot_selection=none")
        print(f"output={output}")
        return 0
    except (
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        UnicodeError,
        ValueError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
