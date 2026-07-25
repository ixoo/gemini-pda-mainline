#!/usr/bin/env python3
"""Derive Candidate AH's guarded boot2 installer from exact Candidate AG."""

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


sys.dont_write_bytecode = True


BOOT2_SIZE = 16 * 1024 * 1024
AG_DERIVER_SHA256 = (
    "59663b58eee43faadcb13117218d9a1abd9cb3479223c734b23fa763ff0f02ab"
)
AG_INSTALLER_SHA256 = (
    "00975af6da6e6b87bb370e52c605d88fe9e313873b8a0aa056ebda8e284247ef"
)
AG_RAW_SHA256 = "0552986c885d89fd65d05f3da8513040f756c9cfc84b1b30e1e085ee68238a91"
AG_RAW_SIZE = "7387136"
AG_PADDED_SHA256 = (
    "63e0b3178072b2945a3537e17fda8c50ebce8032ca00110185993b4e2b7b1e14"
)
AF_PADDED_SHA256 = (
    "832965fbf6c9c056d7bcace238e3895dd206fa7e21e0d3bb2636466a6d073588"
)

# Candidate AH reproduced byte-for-byte in two independent VM builds. These
# immutable production pins deliberately have no command-line override surface.
AH_RAW_SHA256 = "e5ba6ee0a257b804a02af11b83e733f861b89de17470470a497f07056b6b3197"
AH_RAW_SIZE = "7385088"
AH_PADDED_SHA256 = "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012"

HEX256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class Calibration:
    raw_sha256: str
    raw_size: str
    padded_sha256: str


PRODUCTION_CALIBRATION = Calibration(
    AH_RAW_SHA256,
    AH_RAW_SIZE,
    AH_PADDED_SHA256,
)

# These are the complete identity/namespace differences permitted between the
# exact AG installer and AH. Counts pin the reviewed AG installer's shape.
IDENTITY_REPLACEMENTS = (
    (
        "candidate-AG-simplefb-restoration",
        "candidate-AH-ad-contract-af-kernel-split",
        1,
    ),
    (
        "gemini-simplefb-observation-restoration",
        "gemini-ad-contract-af-kernel-split",
        1,
    ),
    (
        "2026-07-22-simplefb-observation-restoration",
        "2026-07-22-ad-contract-af-kernel-split",
        2,
    ),
    ("Candidate AG", "Candidate AH", 7),
    ("candidate-ag", "candidate-ah", 14),
    ("AG_RAW", "AH_RAW", 17),
    ("AG_PADDED", "AH_PADDED", 11),
    (
        "EXPECTED_CURRENT_AF_PADDED_SHA256",
        "EXPECTED_CURRENT_AG_PADDED_SHA256",
        8,
    ),
    ("candidate_label=AG", "candidate_label=AH", 2),
    (
        "AF-installed-readback-verified",
        "AG-installed-readback-verified",
        4,
    ),
)

_ag_deriver = None


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_path(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"installer foundation token count changed: {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def validate_calibration(calibration: Calibration) -> None:
    values = (
        ("AH_RAW_SHA256", calibration.raw_sha256),
        ("AH_RAW_SIZE", calibration.raw_size),
        ("AH_PADDED_SHA256", calibration.padded_sha256),
    )
    for name, value in values:
        if value.startswith("TO_PIN_"):
            raise ValueError(f"Candidate AH calibration remains unpinned: {name}")
    if HEX256.fullmatch(calibration.raw_sha256) is None:
        raise ValueError("Candidate AH raw SHA-256 is malformed")
    if HEX256.fullmatch(calibration.padded_sha256) is None:
        raise ValueError("Candidate AH padded SHA-256 is malformed")
    if not calibration.raw_size.isdecimal():
        raise ValueError("Candidate AH raw size is malformed")
    raw_size = int(calibration.raw_size)
    if not 0 < raw_size <= BOOT2_SIZE:
        raise ValueError("Candidate AH raw size is invalid or exceeds boot2")
    if calibration.raw_sha256 == AG_RAW_SHA256:
        raise ValueError("Candidate AH raw identity equals Candidate AG")
    if calibration.padded_sha256 == AG_PADDED_SHA256:
        raise ValueError(
            "Candidate AH padded identity equals installed Candidate AG"
        )


def repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parent.parents[2]


def ag_deriver_path(root: pathlib.Path | None = None) -> pathlib.Path:
    base = root if root is not None else repo_root()
    return (
        base
        / "experiments/2026-07-22-simplefb-observation-restoration"
        / "scripts/derive-installer.py"
    )


def verify_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode):
        raise ValueError(f"{label} is unsafe")


def load_ag_deriver():
    global _ag_deriver
    if _ag_deriver is not None:
        return _ag_deriver
    path = ag_deriver_path()
    verify_regular(path, "Candidate AG installer deriver")
    if digest_path(path) != AG_DERIVER_SHA256:
        raise ValueError("Candidate AG installer deriver identity changed")
    spec = importlib.util.spec_from_file_location("candidate_ah_exact_ag_deriver", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load exact Candidate AG installer deriver")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _ag_deriver = module
    return module


def expected_transform(source_text: str, calibration: Calibration) -> str:
    validate_calibration(calibration)
    text = source_text
    for old, new, count in IDENTITY_REPLACEMENTS:
        text = replace_exact(text, old, new, count)

    pins = (
        (
            f"readonly AH_RAW_SHA256={AG_RAW_SHA256}",
            f"readonly AH_RAW_SHA256={calibration.raw_sha256}",
        ),
        (
            f"readonly AH_RAW_SIZE={AG_RAW_SIZE}",
            f"readonly AH_RAW_SIZE={calibration.raw_size}",
        ),
        (
            f"readonly AH_PADDED_SHA256={AG_PADDED_SHA256}",
            f"readonly AH_PADDED_SHA256={calibration.padded_sha256}",
        ),
        (
            f"readonly EXPECTED_CURRENT_AG_PADDED_SHA256={AF_PADDED_SHA256}",
            f"readonly EXPECTED_CURRENT_AG_PADDED_SHA256={AG_PADDED_SHA256}",
        ),
    )
    for old, new in pins:
        text = replace_exact(text, old, new, 1)
    return text


def restore_ag_contract(text: str, calibration: Calibration) -> str:
    """Map AH identity pins back to AG without changing executable logic."""

    validate_calibration(calibration)
    restored = text
    for old, new, count in reversed(IDENTITY_REPLACEMENTS):
        restored = replace_exact(restored, new, old, count)

    pins = (
        (
            f"readonly AG_RAW_SHA256={calibration.raw_sha256}",
            f"readonly AG_RAW_SHA256={AG_RAW_SHA256}",
        ),
        (
            f"readonly AG_RAW_SIZE={calibration.raw_size}",
            f"readonly AG_RAW_SIZE={AG_RAW_SIZE}",
        ),
        (
            f"readonly AG_PADDED_SHA256={calibration.padded_sha256}",
            f"readonly AG_PADDED_SHA256={AG_PADDED_SHA256}",
        ),
        (
            f"readonly EXPECTED_CURRENT_AF_PADDED_SHA256={AG_PADDED_SHA256}",
            f"readonly EXPECTED_CURRENT_AF_PADDED_SHA256={AF_PADDED_SHA256}",
        ),
    )
    for old, new in pins:
        restored = replace_exact(restored, old, new, 1)
    return restored


def validate_safety(text: str, calibration: Calibration) -> None:
    """Require exact AH identity over AG's complete executable safety contract."""

    ag = load_ag_deriver()
    restored = restore_ag_contract(text, calibration)
    ag.validate_safety(
        restored,
        ag.Calibration(AG_RAW_SHA256, AG_RAW_SIZE, AG_PADDED_SHA256),
    )
    if digest(restored.encode("utf-8")) != AG_INSTALLER_SHA256:
        raise ValueError("Candidate AH installer changed executable AG contract")


def validate_exact_delta(
    source_text: str, text: str, calibration: Calibration
) -> None:
    if text != expected_transform(source_text, calibration):
        raise ValueError("Candidate AH installer is not the exact narrow AG transform")


def derive_text(source_data: bytes, calibration: Calibration) -> str:
    if digest(source_data) != AG_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AG installer foundation changed")
    try:
        source_text = source_data.decode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Candidate AG installer is not UTF-8") from exc
    text = expected_transform(source_text, calibration)
    validate_exact_delta(source_text, text, calibration)
    validate_safety(text, calibration)
    return text


def run_lineage(command: list[str], cwd: pathlib.Path) -> None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(
            f"Candidate AG installer lineage command failed ({result.returncode}): "
            f"{error}"
        )


def verify_lineage_output(path: pathlib.Path) -> None:
    verify_regular(path, "Candidate AG installer lineage output")
    info = path.lstat()
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError("Candidate AG installer lineage mode changed")
    if digest_path(path) != AG_INSTALLER_SHA256:
        raise ValueError("Candidate AG installer lineage identity changed")


def reconstruct_ag_installer(root: pathlib.Path, work: pathlib.Path) -> pathlib.Path:
    """Reproduce exact AG after pinning its deriver and final installer bytes."""

    deriver = ag_deriver_path(root)
    verify_regular(deriver, "Candidate AG installer deriver")
    if digest_path(deriver) != AG_DERIVER_SHA256:
        raise ValueError("Candidate AG installer deriver identity changed")
    output = work / "install-candidate-ag-boot2.sh"
    run_lineage(
        [sys.executable, os.fspath(deriver), "--output", os.fspath(output)],
        root,
    )
    verify_lineage_output(output)
    return output


def read_exact_source(path: pathlib.Path) -> bytes:
    verify_regular(path, "Candidate AG installer foundation")
    data = path.read_bytes()
    if digest(data) != AG_INSTALLER_SHA256:
        raise ValueError("exact validated Candidate AG installer foundation changed")
    return data


def validate_output_path(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."}:
        raise ValueError("Candidate AH installer output name is invalid")
    if path.exists() or path.is_symlink():
        raise ValueError("refusing to overwrite Candidate AH installer")
    parent_info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(parent_info.st_mode):
        raise ValueError("Candidate AH installer output parent is unsafe")
    parent = path.parent.resolve(strict=True)
    return parent / path.name


def publish(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=pathlib.Path,
        help="exact validated AG installer; omit to reconstruct tracked lineage",
    )
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        validate_calibration(PRODUCTION_CALIBRATION)
        output = validate_output_path(args.output)
        root = repo_root()
        if args.source is not None:
            source_data = read_exact_source(args.source)
        else:
            with tempfile.TemporaryDirectory(
                prefix=".candidate-ah-ag-foundation.", dir=output.parent
            ) as raw_temp:
                source = reconstruct_ag_installer(root, pathlib.Path(raw_temp))
                source_data = read_exact_source(source)
        text = derive_text(source_data, PRODUCTION_CALIBRATION)
        publish(output, text)
        print("validation=candidate-ah-installer-derivation")
        print(f"foundation_installer_sha256={AG_INSTALLER_SHA256}")
        print(f"installer_sha256={digest(text.encode('utf-8'))}")
        print(f"candidate_raw_sha256={AH_RAW_SHA256}")
        print(f"candidate_raw_size={AH_RAW_SIZE}")
        print(f"candidate_padded_sha256={AH_PADDED_SHA256}")
        print(f"expected_predecessor_sha256={AG_PADDED_SHA256}")
        print("sole_target_write=one-bounded-16MiB-write")
        print("reboot_or_slot_selection=none")
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
