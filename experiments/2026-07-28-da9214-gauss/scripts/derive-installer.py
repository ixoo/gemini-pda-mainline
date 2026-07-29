#!/usr/bin/env python3
"""Derive Gauss's guarded boot2 installer from exact Fermi machinery."""

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
import candidate_gauss as co


FERMI_INSTALLER = (
    "experiments/2026-07-28-da9214-fermi/scripts/derive-installer.py"
)
FERMI_INSTALLER_SHA256 = (
    "aed6e8b17efe5cd5ea029977a0d17e83986e98ef091c7411b1569fb34470762b"
)
GAUSS_VERIFIER = (
    "experiments/2026-07-28-da9214-gauss/"
    "scripts/verify-gauss-reproducibility.py"
)
GAUSS_VERIFIER_SHA256 = (
    "56c3ce9f7c74d9fad8c2c97b1ed92507053e235d5be54e2fe3503e2b96a6fd8c"
)
GAUSS_CANDIDATE_MODULE_SHA256 = (
    "a4507861f0ed345715aa573c1604db57c95b5b9b08b27074eceb77d04daf200a"
)
GAUSS_PACKAGE_VALIDATOR_SHA256 = (
    "ad4eecf24f794b8b94a04408bdee5817220289650882448ba393bd76bca5a7bc"
)
GAUSS_BINARY_AUDITOR_SHA256 = (
    "4e9481ccb3243779c493392189a05deade71ab6acb5fefbd35307cd20330f137"
)
BOOT2_SIZE = 16 * 1024 * 1024
FERMI_INSTALLER_PREDECESSOR_SHA256 = (
    "73fceae91606ebf831e503585406df1e2be997edc9fddff1bcae9ec718c91d78"
)
HEX256 = frozenset("0123456789abcdef")
EXTRA_RECORD_KEYS = frozenset(
    {
        "binary_auditor_sha256",
        "binary_audit_sha256",
        "fermi_image_sha256",
        "gauss_image_sha256",
        "fermi_object_sha256",
        "gauss_object_sha256",
        "fermi_vmlinux_sha256",
        "gauss_vmlinux_sha256",
        "binary_delta",
        "lk_identity",
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


def load_fermi_installer(repository: pathlib.Path) -> ModuleType:
    path = repository / FERMI_INSTALLER
    data = regular(path, "source-pinned Fermi installer deriver")
    if hashlib.sha256(data).hexdigest() != FERMI_INSTALLER_SHA256:
        raise ValueError("source-pinned Fermi installer deriver changed")
    spec = importlib.util.spec_from_file_location("gauss_fermi_installer", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load source-pinned Fermi installer deriver")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.fspath(path.parent))
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    finally:
        del sys.path[0]
    return module


def parse_fields(data: bytes) -> dict[str, str]:
    try:
        text = data.decode("ascii", "strict")
    except UnicodeError as exc:
        raise ValueError("Gauss reproducibility record is not ASCII") from exc
    if not text.endswith("\n") or "\0" in text:
        raise ValueError("Gauss reproducibility record framing changed")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.count("=") != 1:
            raise ValueError("Gauss reproducibility record grammar changed")
        key, value = line.split("=", 1)
        if not key or not value or key in fields:
            raise ValueError("Gauss reproducibility record has invalid fields")
        fields[key] = value
    return fields


def validate_record(
    repository: pathlib.Path,
    record_path: pathlib.Path,
    fermi: ModuleType,
) -> dict[str, str]:
    source_pins = {
        repository / GAUSS_VERIFIER: GAUSS_VERIFIER_SHA256,
        pathlib.Path(__file__).with_name(
            "candidate_gauss.py"
        ): GAUSS_CANDIDATE_MODULE_SHA256,
        pathlib.Path(__file__).with_name(
            "validate-package-gauss.py"
        ): GAUSS_PACKAGE_VALIDATOR_SHA256,
        pathlib.Path(__file__).with_name(
            "audit-gauss-binary.py"
        ): GAUSS_BINARY_AUDITOR_SHA256,
    }
    for path, wanted in source_pins.items():
        if digest_path(path) != wanted:
            raise ValueError(f"source-pinned Gauss tool changed: {path.name}")
    fields = parse_fields(regular(record_path, "Gauss reproducibility record"))
    wanted_keys = fermi.REPRODUCIBILITY_KEYS | EXTRA_RECORD_KEYS
    if set(fields) != wanted_keys:
        raise ValueError("Gauss reproducibility record field inventory changed")
    required = {
        "validation": "gauss-two-build-2x2-reproducibility",
        "experiment": co.EXPERIMENT,
        "verifier_sha256": GAUSS_VERIFIER_SHA256,
        "candidate_module_sha256": GAUSS_CANDIDATE_MODULE_SHA256,
        "package_validator_sha256": GAUSS_PACKAGE_VALIDATOR_SHA256,
        "binary_auditor_sha256": GAUSS_BINARY_AUDITOR_SHA256,
        "lk_analyzer_sha256": co.ANALYZER_SHA256,
        "package_lane_count": "2",
        "candidate_lane_count": "4",
        "candidate_raw_member": co.BOOT_MEMBER,
        "candidate_padded_member": co.PADDED_MEMBER,
        "candidate_padded_size": str(BOOT2_SIZE),
        "candidate_boot_dtb_sha256": co.ORION_BOOT_DTB_SHA256,
        "candidate_initramfs_sha256": co.HUBBLE_INITRAMFS_SHA256,
        "package_mode_byte_equality": "exact",
        "candidate_mode_byte_equality": "exact",
        "candidate_lk_validation": "source-pinned-32-gates",
        "candidate_padded_construction": "raw-prefix-zero-tail",
        "fermi_image_sha256": co.FERMI_IMAGE_SHA256,
        "gauss_image_sha256": co.GAUSS_IMAGE_SHA256,
        "fermi_object_sha256": co.FERMI_I2C_OBJECT_SHA256,
        "gauss_object_sha256": co.GAUSS_I2C_OBJECT_SHA256,
        "fermi_vmlinux_sha256": co.FERMI_VMLINUX_SHA256,
        "gauss_vmlinux_sha256": co.GAUSS_VMLINUX_SHA256,
        "binary_delta": "exact-five-source-deltas-plus-gnu-build-id",
        "lk_identity": "exact-fermi-name-cmdline-dt-initramfs",
        "device_access": "none",
        "runtime_result": "not-tested",
    }
    for key, wanted in required.items():
        if fields.get(key) != wanted:
            raise ValueError(f"Gauss reproducibility record changed: {key}")
    hash_keys = tuple(
        key
        for key in fields
        if key.endswith("_sha256")
    )
    for key in hash_keys:
        exact_hash(fields[key], f"record {key}")
    if (
        not fields["candidate_raw_size"].isdecimal()
        or not 0 < int(fields["candidate_raw_size"], 10) < BOOT2_SIZE
    ):
        raise ValueError("Gauss candidate raw size is malformed")
    if fields["candidate_padded_sha256"] == co.CURIE_PADDED_SHA256:
        raise ValueError("Gauss candidate equals the Curie storage predecessor")
    expected_dir = co.ARTIFACT_PREFIX + fields["candidate_raw_sha256"][:8]
    if fields["candidate_directory_name"] != expected_dir:
        raise ValueError("Gauss artifact directory identity changed")
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
            raise ValueError("Gauss reproducibility lane identity mismatch")
    return fields


def validate_manifest(root: pathlib.Path, wanted_sha256: str) -> None:
    data = regular(root / "SHA256SUMS", "Gauss artifact checksum manifest")
    if hashlib.sha256(data).hexdigest() != wanted_sha256:
        raise ValueError("Gauss artifact manifest identity changed")
    seen: set[str] = set()
    for line in data.decode("ascii", "strict").splitlines():
        if len(line) < 67 or line[64:66] != "  ":
            raise ValueError("Gauss artifact checksum line is malformed")
        wanted, name = line[:64], line[66:]
        exact_hash(wanted, "Gauss artifact member hash")
        if not name.startswith("./"):
            raise ValueError("Gauss artifact path lacks canonical ./")
        relative = name[2:]
        pure = pathlib.PurePosixPath(relative)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or pure.as_posix() != relative
            or relative in seen
            or relative == "SHA256SUMS"
        ):
            raise ValueError("Gauss artifact checksum path is unsafe")
        seen.add(relative)
        member = root / relative
        regular(member, f"Gauss artifact member {relative}")
        if digest_path(member) != wanted:
            raise ValueError(f"Gauss artifact checksum failed: {relative}")
    if not {co.BOOT_MEMBER, co.PADDED_MEMBER} <= seen:
        raise ValueError("Gauss artifact manifest lacks boot image members")


def validate_artifact(
    candidate_dir: pathlib.Path,
    fields: dict[str, str],
) -> ArtifactPins:
    root = candidate_dir.resolve(strict=True)
    info = root.lstat()
    if root.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("Gauss artifact directory is unsafe")
    if root.name != fields["candidate_directory_name"]:
        raise ValueError("Gauss artifact directory differs from record")
    validate_manifest(root, fields["candidate_manifest_sha256"])
    raw = root / co.BOOT_MEMBER
    padded = root / co.PADDED_MEMBER
    raw_size = raw.stat().st_size
    if (
        raw_size != int(fields["candidate_raw_size"], 10)
        or digest_path(raw) != fields["candidate_raw_sha256"]
        or padded.stat().st_size != BOOT2_SIZE
        or digest_path(padded) != fields["candidate_padded_sha256"]
    ):
        raise ValueError("Gauss raw or padded artifact differs from record")
    with raw.open("rb") as source, padded.open("rb") as constructed:
        while block := source.read(1024 * 1024):
            if constructed.read(len(block)) != block:
                raise ValueError("Gauss padded image lacks exact raw prefix")
        for block in iter(lambda: constructed.read(1024 * 1024), b""):
            if any(block):
                raise ValueError("Gauss padded image tail is not all zero")
    return ArtifactPins(
        root.name,
        fields["candidate_raw_sha256"],
        raw_size,
        fields["candidate_padded_sha256"],
        fields["candidate_manifest_sha256"],
    )


def derive_text(
    source: str,
    pins: ArtifactPins,
    fermi_pins: ArtifactPins,
) -> str:
    text = source
    for old, new, count in (
        ("FERMI", "GAUSS", 31),
        ("Fermi", "Gauss", 11),
        ("fermi", "gauss", 23),
        (
            "EXPECTED_CURRENT_QUASAR_PADDED_SHA256",
            "EXPECTED_CURRENT_CURIE_PADDED_SHA256",
            8,
        ),
        (
            "Quasar-installed-readback-verified",
            "Curie-installed-readback-verified",
            4,
        ),
        (
            "readonly EXPECTED_CURRENT_CURIE_PADDED_SHA256="
            f"{FERMI_INSTALLER_PREDECESSOR_SHA256}",
            "readonly EXPECTED_CURRENT_CURIE_PADDED_SHA256="
            f"{co.CURIE_PADDED_SHA256}",
            1,
        ),
        (
            f"readonly GAUSS_RAW_SHA256={fermi_pins.raw_sha256}",
            f"readonly GAUSS_RAW_SHA256={pins.raw_sha256}",
            1,
        ),
        (
            f"readonly GAUSS_RAW_SIZE={fermi_pins.raw_size}",
            f"readonly GAUSS_RAW_SIZE={pins.raw_size}",
            1,
        ),
        (
            f"readonly GAUSS_PADDED_SHA256={fermi_pins.padded_sha256}",
            f"readonly GAUSS_PADDED_SHA256={pins.padded_sha256}",
            1,
        ),
        (
            "readonly GAUSS_ARTIFACT_MANIFEST_SHA256="
            f"{fermi_pins.manifest_sha256}",
            "readonly GAUSS_ARTIFACT_MANIFEST_SHA256="
            f"{pins.manifest_sha256}",
            1,
        ),
        (
            'expected_artifact_name="'
            f'{fermi_pins.artifact_dir.replace("Fermi", "Gauss")}"',
            f'expected_artifact_name="{pins.artifact_dir}"',
            1,
        ),
    ):
        text = replace_exact(text, old, new, count)
    required = {
        f"readonly GAUSS_RAW_SHA256={pins.raw_sha256}": 1,
        f"readonly GAUSS_RAW_SIZE={pins.raw_size}": 1,
        f"readonly GAUSS_PADDED_SHA256={pins.padded_sha256}": 1,
        "readonly EXPECTED_CURRENT_CURIE_PADDED_SHA256="
        f"{co.CURIE_PADDED_SHA256}": 1,
        f'expected_artifact_name="{pins.artifact_dir}"': 1,
        f'[[ "$candidate_name" == {co.BOOT_MEMBER} ]]': 1,
        f"experiment={co.EXPERIMENT}": 2,
        "candidate_label=Gauss": 2,
        "EXPECTED_CURRENT_CURIE_PADDED_SHA256": 8,
        "Curie-installed-readback-verified": 4,
        'dd if="$root_stage_file" of="$target"': 1,
        'of="$target"': 1,
        "reboot_or_shutdown_performed=no": 2,
        "[[ \"$(uname -r)\" == 3.18.41+ ]]": 2,
        "[[ \"$active_root\" == /dev/mmcblk0p29 ]]": 1,
        "battery_capacity >= 81 && battery_capacity <= 100": 1,
        'blockdev --flushbufs "$target"': 1,
        'cmp -s "$padded" "$readback_partial"': 1,
    }
    for token, wanted in required.items():
        if text.count(token) != wanted:
            raise ValueError(f"derived Gauss installer changed for {token!r}")
    for forbidden in (
        "EXPECTED_CURRENT_QUASAR",
        "Quasar-installed-readback-verified",
        "gemini-mt6797-da9214-fermi.boot.img",
        "candidate_label=Fermi",
        "of=/dev/mmc",
        "reboot ",
        "shutdown ",
        "poweroff ",
        "kexec ",
        "sysrq",
        "sudo -S",
        "SSH_ASKPASS",
    ):
        if forbidden in text:
            raise ValueError(f"derived Gauss installer retained {forbidden!r}")
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
    parser.add_argument(
        "--reproducibility-record",
        required=True,
        type=pathlib.Path,
    )
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        repository = pathlib.Path(__file__).resolve().parents[3]
        fermi = load_fermi_installer(repository)
        fields = validate_record(
            repository,
            args.reproducibility_record.resolve(strict=True),
            fermi,
        )
        pins = validate_artifact(args.candidate_dir, fields)
        output = safe_output(args.output)

        fermi_fields = fermi.parse_record(repository)
        fermi_pins = fermi.ArtifactPins(
            fermi_fields["candidate_directory_name"],
            fermi_fields["candidate_raw_sha256"],
            int(fermi_fields["candidate_raw_size"], 10),
            fermi_fields["candidate_padded_sha256"],
            fermi_fields["candidate_manifest_sha256"],
        )
        quasar = fermi.load_quasar_deriver(repository)
        with tempfile.TemporaryDirectory(
            prefix=".gauss-fermi-installer.", dir=output.parent
        ) as raw:
            source = quasar.reconstruct_vega(pathlib.Path(raw))
        quasar_text = quasar.derive_text(source, quasar.io.production_pins())
        fermi_text = fermi.derive_text(quasar_text, fermi_pins, quasar)
        text = derive_text(fermi_text, pins, fermi_pins)
        publish(output, text)
        print("validation=gauss-installer-derived")
        print(f"installer_sha256={hashlib.sha256(text.encode()).hexdigest()}")
        print(f"artifact={pins.artifact_dir}")
        print(f"candidate_raw_sha256={pins.raw_sha256}")
        print(f"candidate_raw_size={pins.raw_size}")
        print(f"candidate_manifest_sha256={pins.manifest_sha256}")
        print(f"candidate_padded_sha256={pins.padded_sha256}")
        print(f"expected_predecessor_sha256={co.CURIE_PADDED_SHA256}")
        print("predecessor_role=storage-safety-only")
        print("software_and_binary_baseline=exact-fermi")
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
