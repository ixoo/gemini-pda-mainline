#!/usr/bin/env python3
"""Derive Gate 3's guarded boot2 installer from the exact Gauss installer."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import stat


GAUSS_INSTALLER_SHA256 = (
    "98e8924c14a219c5437be56b3b8d9f1a68e1c88c08cccb9006abbec152286119"
)
GAUSS_PADDED_SHA256 = (
    "8749c0394dc8d6989eea4fe945da4afb569a1b2cd7727c98b31c5eb5140624cb"
)
CANDIDATE_NAME = "gemini-mt6797-da921x-lifecycle.boot.img"
BOOT2_SIZE = 16 * 1024 * 1024


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def require_regular(path: pathlib.Path, label: str) -> None:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe: {path}")


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"expected one installer token {old!r}, found {count}")
    return text.replace(old, new)


def read_provenance(path: pathlib.Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in values:
            raise ValueError(f"duplicate provenance key: {key}")
        values[key] = value
    return values


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gauss-installer", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    require_regular(args.gauss_installer, "Gauss installer")
    if digest(args.gauss_installer) != GAUSS_INSTALLER_SHA256:
        raise ValueError("source Gauss installer changed")
    artifact = args.candidate_artifact.resolve(strict=True)
    if not artifact.is_dir() or artifact.is_symlink():
        raise ValueError("candidate artifact is missing or unsafe")
    candidate = artifact / CANDIDATE_NAME
    padded = artifact / "boot2-padded.img"
    manifest = artifact / "SHA256SUMS"
    provenance_path = artifact / "provenance.txt"
    for path, label in (
        (candidate, "raw candidate"),
        (padded, "padded candidate"),
        (manifest, "candidate manifest"),
        (provenance_path, "candidate provenance"),
    ):
        require_regular(path, label)
    if args.output.exists() or args.output.is_symlink():
        raise ValueError(f"refusing to overwrite output: {args.output}")

    raw_size = candidate.stat().st_size
    padded_size = padded.stat().st_size
    raw_sha256 = digest(candidate)
    padded_sha256 = digest(padded)
    manifest_sha256 = digest(manifest)
    provenance = read_provenance(provenance_path)
    if raw_size <= 0 or raw_size > BOOT2_SIZE or padded_size != BOOT2_SIZE:
        raise ValueError("candidate sizes do not satisfy boot2")
    for key, actual in (
        ("candidate_sha256", raw_sha256),
        ("candidate_size", str(raw_size)),
        ("padded_sha256", padded_sha256),
        ("padded_size", str(padded_size)),
    ):
        if provenance.get(key) != actual:
            raise ValueError(f"candidate provenance mismatch: {key}")
    if padded_sha256 == GAUSS_PADDED_SHA256:
        raise ValueError("Gate 3 candidate unexpectedly equals Gauss predecessor")

    text = args.gauss_installer.read_text(encoding="utf-8")
    text = text.replace(
        "EXPECTED_CURRENT_CURIE_PADDED_SHA256",
        "EXPECTED_CURRENT_PREDECESSOR_PADDED_SHA256",
    )
    text = text.replace("GAUSS", "GATE3")
    text = text.replace("Gauss", "Gate 3")
    text = text.replace("gauss", "gate3-da921x-lifecycle")
    text = text.replace("Curie", "Gauss")

    text = replace_once(
        text,
        "readonly GATE3_RAW_SHA256=359cce03ac059410ead4b7f5cf85a71ab3b383370dc0f64a334c8fdae329a703",
        f"readonly GATE3_RAW_SHA256={raw_sha256}",
    )
    text = replace_once(
        text,
        "readonly GATE3_RAW_SIZE=7747584",
        f"readonly GATE3_RAW_SIZE={raw_size}",
    )
    text = replace_once(
        text,
        "readonly GATE3_PADDED_SHA256=8749c0394dc8d6989eea4fe945da4afb569a1b2cd7727c98b31c5eb5140624cb",
        f"readonly GATE3_PADDED_SHA256={padded_sha256}",
    )
    text = replace_once(
        text,
        "readonly GATE3_ARTIFACT_MANIFEST_SHA256=9d857688675a5b98eb06e1960b3a2747bd293957bdeea10243f6742df04d3209",
        f"readonly GATE3_ARTIFACT_MANIFEST_SHA256={manifest_sha256}",
    )
    text = replace_once(
        text,
        "readonly EXPECTED_CURRENT_PREDECESSOR_PADDED_SHA256=824c3391f55cc932d146ef2e573642a51fb5c077932c7b6d17316fd34020d52d",
        "readonly EXPECTED_CURRENT_PREDECESSOR_PADDED_SHA256="
        f"{GAUSS_PADDED_SHA256}",
    )
    text = replace_once(
        text,
        "gemini-mt6797-da9214-gate3-da921x-lifecycle.boot.img",
        CANDIDATE_NAME,
    )
    text = replace_once(
        text,
        'expected_artifact_name="candidate-Gate 3-da9214-359cce03"',
        f'expected_artifact_name="{artifact.name}"',
    )
    text = text.replace(
        "experiment=2026-07-28-da9214-gate3-da921x-lifecycle",
        "experiment=2026-07-29-da921x-legacy-lifecycle",
    )
    text = text.replace(
        "exact reproduced Candidate Gate 3 manifest",
        "exact reproduced Gate 3 lifecycle manifest",
    )
    for forbidden in (
        "EXPECTED_CURRENT_CURIE",
        "824c3391f55cc932d146ef2e573642a51fb5c077932c7b6d17316fd34020d52d",
        "359cce03ac059410ead4b7f5cf85a71ab3b383370dc0f64a334c8fdae329a703",
        "9d857688675a5b98eb06e1960b3a2747bd293957bdeea10243f6742df04d3209",
    ):
        if forbidden in text:
            raise ValueError(f"derived installer retained stale token: {forbidden}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        args.output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o700,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        stream.write(text)

    print("validation=gate3-lifecycle-installer-derivation")
    print(f"output={args.output}")
    print(f"candidate_sha256={raw_sha256}")
    print(f"candidate_padded_sha256={padded_sha256}")
    print(f"expected_predecessor_sha256={GAUSS_PADDED_SHA256}")
    print("sole_target=live-gpt-resolved-logical-boot2")
    print("automatic_reboot=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
