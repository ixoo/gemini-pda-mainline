#!/usr/bin/env python3
"""Derive Candidate AK's guarded boot2 installer from exact Candidate AJ."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from types import ModuleType

sys.dont_write_bytecode = True

BOOT2_SIZE = 16 * 1024 * 1024
AK_IDENTITY_SHA256 = "c52e133767f305045664b2274883e8f145170ee4fd8ae34418b7a14ed42360a0"
AJ_DERIVER_SHA256 = "07ac69c75f412a4478bf54f4156fd4375c1f0c9e108cb8ef41ce00728d607a0f"
AJ_INSTALLER_SHA256 = "5cd0d3f59a8a95705f11819ff2cf52c69fd14da04476b132e6000faee1b8c764"
AJ_RAW_SHA256 = "a3c649b5ca7a9ac07e290ca9a8838f0a3be33ab9e39554c4bafe50c98d18e2a8"
AJ_RAW_SIZE = "7380992"
AJ_MANIFEST_SHA256 = "143307167adcfe000e7ffc331217248404c1fa45e133600d5e21043d93186ac7"
AJ_PADDED_SHA256 = "8e322ed2a8fc82a4746ec118c2b0adad6003d03f0670284b9ab281c92120b257"
AJ_ARTIFACT_DIR = "candidate-AJ-a72-reject-cpu8-a3c649b5"
AK_ARTIFACT_PREFIX = "candidate-AK-a72-reject-cpu9-"
AK_BOOT_FILENAME = "gemini-a72-reject-cpu9-request.boot.img"
HEX256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Calibration:
    raw_sha256: str
    raw_size: str
    artifact_manifest_sha256: str
    padded_sha256: str


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def verify_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")


def load_module(path: pathlib.Path, expected: str, name: str, label: str) -> ModuleType:
    verify_regular(path, label)
    if digest_path(path) != expected:
        raise ValueError(f"{label} identity changed")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {label}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_ak_identity() -> ModuleType:
    if AK_IDENTITY_SHA256.startswith("TO_PIN_"):
        raise ValueError("Candidate AK identity source remains unpinned")
    return load_module(
        pathlib.Path(__file__).resolve().with_name("candidate_ak.py"),
        AK_IDENTITY_SHA256,
        "candidate_ak_installer_pinned_identities",
        "Candidate AK identity module",
    )


def aj_deriver_path(root: pathlib.Path | None = None) -> pathlib.Path:
    base = root if root is not None else repository_root()
    return base / "experiments/2026-07-22-a72-reject-cpu8-request/scripts/derive-installer.py"


def load_aj_deriver() -> ModuleType:
    return load_module(
        aj_deriver_path(), AJ_DERIVER_SHA256,
        "candidate_ak_exact_aj_installer_deriver", "Candidate AJ installer deriver",
    )


def validate_calibration(calibration: Calibration) -> None:
    values = {
        "raw": calibration.raw_sha256,
        "artifact manifest": calibration.artifact_manifest_sha256,
        "padded": calibration.padded_sha256,
    }
    if any(value.startswith("TO_PIN_") for value in (*values.values(), calibration.raw_size)):
        raise ValueError("Candidate AK artifact calibration remains unpinned")
    for name, value in values.items():
        if HEX256.fullmatch(value) is None:
            raise ValueError(f"Candidate AK {name} SHA-256 is malformed")
    if not calibration.raw_size.isdecimal() or not 0 < int(calibration.raw_size) <= BOOT2_SIZE:
        raise ValueError("Candidate AK raw size is malformed or exceeds boot2")
    if calibration.raw_sha256 == AJ_RAW_SHA256:
        raise ValueError("Candidate AK raw identity equals Candidate AJ")
    if calibration.artifact_manifest_sha256 == AJ_MANIFEST_SHA256:
        raise ValueError("Candidate AK artifact manifest equals Candidate AJ")
    if calibration.padded_sha256 == AJ_PADDED_SHA256:
        raise ValueError("Candidate AK padded identity equals Candidate AJ predecessor")


def production_calibration() -> Calibration:
    ak = load_ak_identity()
    exact = {
        "experiment": (ak.EXPERIMENT, "2026-07-22-a72-reject-cpu9-request"),
        "candidate": (ak.CANDIDATE, "AK"),
        "boot member": (ak.BOOT_MEMBER, AK_BOOT_FILENAME),
        "AJ raw predecessor": (ak.AJ_RAW_SHA256, AJ_RAW_SHA256),
        "AJ manifest predecessor": (ak.AJ_ARTIFACT_MANIFEST_SHA256, AJ_MANIFEST_SHA256),
        "AJ padded predecessor": (ak.AJ_PADDED_SHA256, AJ_PADDED_SHA256),
    }
    for label, (actual, expected) in exact.items():
        if actual != expected:
            raise ValueError(f"{label} changed")
    ak.require_artifact_pins()
    calibration = Calibration(
        ak.RAW_SHA256, ak.RAW_SIZE, ak.ARTIFACT_MANIFEST_SHA256, ak.PADDED_SHA256
    )
    validate_calibration(calibration)
    return calibration


def artifact_directory(calibration: Calibration) -> str:
    return AK_ARTIFACT_PREFIX + calibration.raw_sha256[:8]


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer foundation token count changed: {old!r}: expected {count}, found {actual}"
        )
    return text.replace(old, new)


def identity_replacements(calibration: Calibration) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            f'expected_artifact_name="{AJ_ARTIFACT_DIR}"',
            f'expected_artifact_name="{artifact_directory(calibration)}"', 1,
        ),
        ("gemini-a72-reject-cpu8-request", "gemini-a72-reject-cpu9-request", 1),
        ("2026-07-22-a72-reject-cpu8-request", "2026-07-22-a72-reject-cpu9-request", 2),
        ("Candidate AJ", "Candidate AK", 8),
        ("candidate-aj", "candidate-ak", 14),
        ("AJ_RAW", "AK_RAW", 16),
        ("AJ_PADDED", "AK_PADDED", 11),
        ("AJ_ARTIFACT", "AK_ARTIFACT", 4),
        ("EXPECTED_CURRENT_AI_PADDED_SHA256", "EXPECTED_CURRENT_AJ_PADDED_SHA256", 8),
        ("candidate_label=AJ", "candidate_label=AK", 2),
        ("AI-installed-readback-verified", "AJ-installed-readback-verified", 4),
    )


def expected_transform(source: str, calibration: Calibration) -> str:
    validate_calibration(calibration)
    text = source
    for old, new, count in identity_replacements(calibration):
        text = replace_exact(text, old, new, count)
    pins = (
        (f"readonly AK_RAW_SHA256={AJ_RAW_SHA256}", f"readonly AK_RAW_SHA256={calibration.raw_sha256}"),
        (f"readonly AK_RAW_SIZE={AJ_RAW_SIZE}", f"readonly AK_RAW_SIZE={calibration.raw_size}"),
        (f"readonly AK_PADDED_SHA256={AJ_PADDED_SHA256}", f"readonly AK_PADDED_SHA256={calibration.padded_sha256}"),
        (f"readonly AK_ARTIFACT_MANIFEST_SHA256={AJ_MANIFEST_SHA256}", f"readonly AK_ARTIFACT_MANIFEST_SHA256={calibration.artifact_manifest_sha256}"),
        (
            "readonly EXPECTED_CURRENT_AJ_PADDED_SHA256="
            "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86",
            f"readonly EXPECTED_CURRENT_AJ_PADDED_SHA256={AJ_PADDED_SHA256}",
        ),
    )
    for old, new in pins:
        text = replace_exact(text, old, new, 1)
    return text


def restore_aj_contract(text: str, calibration: Calibration) -> str:
    restored = text
    pins = (
        (f"readonly AK_RAW_SHA256={calibration.raw_sha256}", f"readonly AK_RAW_SHA256={AJ_RAW_SHA256}"),
        (f"readonly AK_RAW_SIZE={calibration.raw_size}", f"readonly AK_RAW_SIZE={AJ_RAW_SIZE}"),
        (f"readonly AK_PADDED_SHA256={calibration.padded_sha256}", f"readonly AK_PADDED_SHA256={AJ_PADDED_SHA256}"),
        (f"readonly AK_ARTIFACT_MANIFEST_SHA256={calibration.artifact_manifest_sha256}", f"readonly AK_ARTIFACT_MANIFEST_SHA256={AJ_MANIFEST_SHA256}"),
        (
            f"readonly EXPECTED_CURRENT_AJ_PADDED_SHA256={AJ_PADDED_SHA256}",
            "readonly EXPECTED_CURRENT_AJ_PADDED_SHA256="
            "8b7439dda7d50dfd509dd66acb5eeedda86d538f0b4f0fab9b328bcc93ed8b86",
        ),
    )
    for old, new in pins:
        restored = replace_exact(restored, old, new, 1)
    for old, new, count in reversed(identity_replacements(calibration)):
        restored = replace_exact(restored, new, old, count)
    return restored


def derive_text(source_data: bytes, calibration: Calibration) -> str:
    if digest(source_data) != AJ_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AJ installer foundation changed")
    try:
        source = source_data.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Candidate AJ installer is not UTF-8") from exc
    text = expected_transform(source, calibration)
    restored = restore_aj_contract(text, calibration)
    if restored != source or digest(restored.encode()) != AJ_INSTALLER_SHA256:
        raise ValueError("Candidate AK installer does not restore exact AJ contract")
    aj_deriver = load_aj_deriver()
    aj_deriver.validate_safety(restored, aj_deriver.production_calibration())
    return text


def run_lineage(command: list[str], cwd: pathlib.Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, cwd=cwd, env=environment, capture_output=True, check=False)
    if result.returncode:
        detail = result.stderr.decode(errors="replace").strip() or "no diagnostic"
        raise ValueError(f"Candidate AJ installer reconstruction failed: {detail}")


def reconstruct_aj_installer(root: pathlib.Path, work: pathlib.Path) -> pathlib.Path:
    deriver = aj_deriver_path(root)
    verify_regular(deriver, "Candidate AJ installer deriver")
    if digest_path(deriver) != AJ_DERIVER_SHA256:
        raise ValueError("Candidate AJ installer deriver changed")
    output = work / "install-candidate-aj-boot2.sh"
    run_lineage([sys.executable, os.fspath(deriver), "--output", os.fspath(output)], root)
    verify_regular(output, "Candidate AJ installer reconstruction")
    if stat.S_IMODE(output.lstat().st_mode) != 0o700 or digest_path(output) != AJ_INSTALLER_SHA256:
        raise ValueError("Candidate AJ installer reconstruction identity changed")
    return output


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ValueError("Candidate AK installer output is invalid or already exists")
    info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("Candidate AK installer output parent is unsafe")
    return path.parent.resolve(strict=True) / path.name


def publish(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(text)


def produce(source_path: pathlib.Path | None, output_path: pathlib.Path) -> tuple[pathlib.Path, str, Calibration]:
    calibration = production_calibration()
    output = validate_output_path(output_path)
    root = repository_root()
    if source_path is None:
        with tempfile.TemporaryDirectory(prefix=".candidate-ak-aj-foundation.", dir=output.parent) as raw:
            source_data = reconstruct_aj_installer(root, pathlib.Path(raw)).read_bytes()
    else:
        verify_regular(source_path, "Candidate AJ installer foundation")
        source_data = source_path.read_bytes()
    text = derive_text(source_data, calibration)
    publish(output, text)
    return output, text, calibration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        output, text, calibration = produce(args.source, args.output)
        print("validation=candidate-ak-installer-derivation")
        print(f"foundation_installer_sha256={AJ_INSTALLER_SHA256}")
        print(f"installer_sha256={digest(text.encode())}")
        print(f"candidate_raw_sha256={calibration.raw_sha256}")
        print(f"candidate_raw_size={calibration.raw_size}")
        print(f"candidate_artifact_manifest_sha256={calibration.artifact_manifest_sha256}")
        print(f"candidate_padded_sha256={calibration.padded_sha256}")
        print(f"expected_predecessor_sha256={AJ_PADDED_SHA256}")
        print(f"artifact_directory={artifact_directory(calibration)}")
        print(f"boot_filename={AK_BOOT_FILENAME}")
        print(f"output={output}")
        print("sole_target_write=one-bounded-16MiB-write")
        print("reboot_or_slot_selection=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
