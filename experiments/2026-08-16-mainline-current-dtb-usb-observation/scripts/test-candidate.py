#!/usr/bin/env python3
"""Validate the three-property current-DT USB observation candidate."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SOURCE_VALIDATOR_SHA256 = "1b650f422147d39884a9484077e3a11efdf5ff17cb2df88ab42158b7f9c7bc71"
DTB_SHA256 = "e93264b32e0a42098fa6556e454abc99b75373e92e1e3b6eef50285542251331"
RAW_SHA256 = "a9d4f9516d761bfb30faf95e8b3d3f9e9d19282bc67d508fbc5ff308e84954be"
PADDED_SHA256 = "fa107a988d860f017905c61a4b52110bc8dc3cc1ce5f407424fa3dd47c9b8b87"
BOOT_FILE = "gemini-mt6797-arm64-entry-ledger-usb-observation.boot.img"
DTB_FILE = "mt6797-gemini-pda-usb-observation.dtb"
BASE_FILES = {
    "boot2-padded.img",
    "container-analysis.txt",
    BOOT_FILE,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
}
FILES = BASE_FILES | {DTB_FILE, "dtb-validation.txt", "SHA256SUMS"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def verify_manifest(candidate: Path) -> None:
    manifest = (candidate / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    seen: set[str] = set()
    for line in manifest:
        fields = line.split(maxsplit=1)
        require(len(fields) == 2, "malformed candidate manifest")
        expected, name = fields
        name = name.removeprefix("*").removeprefix("./")
        require(name in FILES - {"SHA256SUMS"}, "unexpected manifest member")
        require(name not in seen, "duplicate manifest member")
        seen.add(name)
        require(digest((candidate / name).read_bytes()) == expected, f"hash changed: {name}")
    require(seen == FILES - {"SHA256SUMS"}, "candidate manifest inventory changed")


def derive_validator(source: str) -> str:
    replacements = (
        ("exact GAEL/Stage-27-DTB control container",
         "exact GAEL/current-DT USB observation container", 1),
        ("KERNEL_FIELD_SIZE = 4_802_149", "KERNEL_FIELD_SIZE = 4_802_342", 1),
        ("RAW_SHA256 = \"e96d0cc2670bf4de6e0cc88d35d8814c5c3aa05442d0a5bd83818fa078ca2086\"",
         f"RAW_SHA256 = \"{RAW_SHA256}\"", 1),
        ("PADDED_SHA256 = \"68515e0ecbb073b4ee18b318bd869fd5b7dea1c3ac838681ceb42b7451dc1c67\"",
         f"PADDED_SHA256 = \"{PADDED_SHA256}\"", 1),
        ("CONTROL_DTB_SHA256 = \"7ee8421ea03b604e30e1760f6fb5bc98d4d2566694a9da189326ce2c10e0c806\"",
         f"CONTROL_DTB_SHA256 = \"{DTB_SHA256}\"", 1),
        ("gemini-mt6797-arm64-entry-ledger-stage27-dtb.boot.img", BOOT_FILE, 2),
        ("b\"gemini-dtbctl\"", "b\"gemini-usbobs\"", 1),
        ("Stage-27 control DTB", "USB-observation DTB", 1),
        ("validation=lk-handoff-dtb-control-candidate",
         "validation=current-dtb-usb-observation-candidate", 1),
        ("control_dtb=exact-runtime-proven-stage27",
         "usb_observation_dtb=current-package-plus-three-status-properties", 1),
    )
    text = source
    for old, new, count in replacements:
        actual = text.count(old)
        require(actual == count, f"unsafe validator derivation for {old!r}: {actual}")
        text = text.replace(old, new)
    return text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    args = parser.parse_args()

    entries = list(args.candidate.iterdir())
    require({entry.name for entry in entries} == FILES, "candidate inventory changed")
    require(all(entry.is_file() and not entry.is_symlink() for entry in entries), "unsafe entry")
    verify_manifest(args.candidate)
    dtb = args.candidate / DTB_FILE
    require(digest(dtb.read_bytes()) == DTB_SHA256, "derived DTB changed")
    validation = (args.candidate / "dtb-validation.txt").read_text(encoding="ascii")
    for line in (
        "validation=current-dtb-usb-observation-derivation\n",
        "semantic_delta_count=3\n",
        "xhci_status=disabled\n",
        "role=peripheral\n",
        "maximum_speed=high-speed\n",
        "result=pass\n",
    ):
        require(line in validation, f"DT validation gate missing: {line!r}")

    repository = Path(__file__).resolve().parents[3]
    source_path = (
        repository
        / "experiments/2026-08-16-mainline-lk-handoff-dtb-control/scripts/test-candidate.py"
    )
    source_data = source_path.read_bytes()
    require(digest(source_data) == SOURCE_VALIDATOR_SHA256, "source validator changed")
    derived = derive_validator(source_data.decode("utf-8", "strict"))

    with tempfile.TemporaryDirectory(prefix="gemini-usbobs-validator.") as raw:
        temporary = Path(raw)
        shadow = temporary / "candidate"
        shadow.mkdir()
        manifest_lines = []
        for name in sorted(BASE_FILES):
            shutil.copyfile(args.candidate / name, shadow / name)
            manifest_lines.append(f"{digest((shadow / name).read_bytes())}  ./{name}\n")
        (shadow / "SHA256SUMS").write_text("".join(manifest_lines), encoding="ascii")
        validator = temporary / "test-candidate-derived.py"
        validator.write_text(derived, encoding="utf-8")
        subprocess.run(
            [
                sys.executable,
                str(validator),
                "--candidate",
                str(shadow),
                "--package",
                str(args.package),
                "--ramdisk",
                str(args.ramdisk),
                "--control-dtb",
                str(dtb),
            ],
            check=True,
        )
    print("semantic_delta_count=3")
    print("candidate_manifest=passed")
    print("result=pass")


if __name__ == "__main__":
    main()
