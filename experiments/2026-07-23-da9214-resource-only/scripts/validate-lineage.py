#!/usr/bin/env python3
"""Validate exact AH functional input and exact AK storage predecessor."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import re
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True

import candidate_al as al


EXECUTABLE_MEMBERS = {
    "console-keymap-verify",
    "console-unicode-mode",
    "input-event-capture",
}
AH_MEMBERS = {
    "Image.gz",
    "SHA256SUMS",
    "System.map",
    "analysis.txt",
    "boot-validation.txt",
    "console-keymap-verify",
    "console-unicode-mode",
    "dtb-validation.txt",
    al.AH_BOOT_MEMBER,
    al.AH_INITRAMFS_MEMBER,
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "lineage-validation.txt",
    al.AH_DTB_MEMBER,
    "provenance.txt",
    "serializer.txt",
    "source-build.json",
}


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} directory")
    return path.resolve(strict=True)


def inventory(root: pathlib.Path, label: str) -> dict[str, tuple[int, str, int]]:
    output: dict[str, tuple[int, str, int]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise ValueError(f"{label} contains a non-regular member: {relative}")
        output[relative] = (
            stat.S_IMODE(info.st_mode),
            al.digest_path(path),
            info.st_size,
        )
    return output


def validate_manifest(
    root: pathlib.Path,
    members: dict[str, tuple[int, str, int]],
    label: str,
) -> None:
    manifest = root / "SHA256SUMS"
    seen: set[str] = set()
    for line in manifest.read_text(encoding="ascii", errors="strict").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError(f"{label} manifest is malformed")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in seen or member == "SHA256SUMS" or member not in members:
            raise ValueError(f"{label} manifest member is unsafe or duplicated")
        if fields[0] != members[member][1]:
            raise ValueError(f"{label} manifest checksum differs: {member}")
        seen.add(member)
    if seen != set(members) - {"SHA256SUMS"}:
        raise ValueError(f"{label} manifest inventory differs")


def load_exact_ak_identity() -> ModuleType:
    source = (
        repository_root()
        / "experiments/2026-07-22-a72-reject-cpu9-request/scripts/candidate_ak.py"
    )
    data = al.read_regular(source, "Candidate AK identity source")
    if hashlib.sha256(data).hexdigest() != al.AK_IDENTITY_SHA256:
        raise ValueError("Candidate AK identity source changed")
    spec = importlib.util.spec_from_file_location("candidate_al_exact_ak", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AK identity source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.require_artifact_pins()
    expected = {
        "artifact directory": (module.CANDIDATE, "AK"),
        "raw SHA-256": (module.RAW_SHA256, al.AK_RAW_SHA256),
        "raw size": (int(module.RAW_SIZE), al.AK_RAW_SIZE),
        "manifest SHA-256": (
            module.ARTIFACT_MANIFEST_SHA256,
            al.AK_MANIFEST_SHA256,
        ),
        "padded SHA-256": (module.PADDED_SHA256, al.AK_PADDED_SHA256),
    }
    for label, (actual, wanted) in expected.items():
        if actual != wanted:
            raise ValueError(f"Candidate AK identity changed: {label}")
    return module


def padded_digest(path: pathlib.Path, raw_size: int) -> str:
    if raw_size <= 0 or raw_size > al.BOOT2_SIZE:
        raise ValueError("raw boot size is invalid")
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    remaining = al.BOOT2_SIZE - raw_size
    zeros = b"\0" * (1024 * 1024)
    while remaining:
        block = zeros[: min(remaining, len(zeros))]
        hasher.update(block)
        remaining -= len(block)
    return hasher.hexdigest()


def validate_ah(root: pathlib.Path) -> None:
    if root.name != al.AH_ARTIFACT_DIR:
        raise ValueError("Candidate AH artifact basename changed")
    members = inventory(root, "Candidate AH")
    if set(members) != AH_MEMBERS:
        raise ValueError("Candidate AH artifact inventory changed")
    for member, (mode, _, _) in members.items():
        expected = 0o755 if member in EXECUTABLE_MEMBERS else 0o600
        if mode != expected:
            raise ValueError(f"Candidate AH artifact mode changed: {member}")
    if members["SHA256SUMS"][1] != al.AH_MANIFEST_SHA256:
        raise ValueError("Candidate AH exact manifest changed")
    validate_manifest(root, members, "Candidate AH")
    expected = {
        al.AH_BOOT_MEMBER: (al.AH_RAW_SHA256, al.AH_RAW_SIZE),
        al.AH_DTB_MEMBER: (al.AH_DTB_SHA256, None),
        al.AH_INITRAMFS_MEMBER: (al.INITRAMFS_SHA256, None),
        "Image.gz": (al.IMAGE_GZ_SHA256, None),
        "System.map": (al.SYSTEM_MAP_SHA256, None),
        "kernel.config": (al.CONFIG_SHA256, None),
        "source-build.json": (al.SOURCE_BUILD_SHA256, None),
        "gemini-us.bkeymap": (al.KEYMAP_SHA256, None),
    }
    for member, (wanted_hash, wanted_size) in expected.items():
        _, actual_hash, actual_size = members[member]
        if actual_hash != wanted_hash or (
            wanted_size is not None and actual_size != wanted_size
        ):
            raise ValueError(f"Candidate AH exact member changed: {member}")
    if padded_digest(root / al.AH_BOOT_MEMBER, al.AH_RAW_SIZE) != al.AH_PADDED_SHA256:
        raise ValueError("Candidate AH padded identity changed")


def validate_ak(root: pathlib.Path) -> None:
    ak = load_exact_ak_identity()
    if root.name != al.AK_ARTIFACT_DIR:
        raise ValueError("Candidate AK artifact basename changed")
    members = inventory(root, "Candidate AK")
    if "SHA256SUMS" not in members or al.AK_BOOT_MEMBER not in members:
        raise ValueError("Candidate AK artifact lacks required members")
    if members["SHA256SUMS"][1] != al.AK_MANIFEST_SHA256:
        raise ValueError("Candidate AK exact manifest changed")
    validate_manifest(root, members, "Candidate AK")
    boot = members[al.AK_BOOT_MEMBER]
    if boot[1] != al.AK_RAW_SHA256 or boot[2] != al.AK_RAW_SIZE:
        raise ValueError("Candidate AK exact boot member changed")
    if padded_digest(root / al.AK_BOOT_MEMBER, al.AK_RAW_SIZE) != al.AK_PADDED_SHA256:
        raise ValueError("Candidate AK padded identity changed")
    # This makes the historical validator, rather than a copied inventory,
    # authoritative for the predecessor artifact's complete contract.
    ak.require_artifact_pins()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ah-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--ak-artifact", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        ah = resolve_directory(args.ah_artifact, "Candidate AH artifact")
        ak = resolve_directory(args.ak_artifact, "Candidate AK artifact")
        if ah == ak or ah.samefile(ak):
            raise ValueError("AH functional baseline and AK predecessor collapsed")
        validate_ah(ah)
        validate_ak(ak)
        print("validation=candidate-al-input-lineage")
        print(f"ah_raw_sha256={al.AH_RAW_SHA256}")
        print(f"ah_dtb_sha256={al.AH_DTB_SHA256}")
        print(f"ah_image_gz_sha256={al.IMAGE_GZ_SHA256}")
        print(f"ah_system_map_sha256={al.SYSTEM_MAP_SHA256}")
        print(f"ah_config_sha256={al.CONFIG_SHA256}")
        print(f"ah_initramfs_sha256={al.INITRAMFS_SHA256}")
        print("functional_baseline=exact-hardware-passed-candidate-ah")
        print(f"ak_padded_sha256={al.AK_PADDED_SHA256}")
        print("installed_predecessor=exact-candidate-ak")
        print("ak_functional_payload_reused=no")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
