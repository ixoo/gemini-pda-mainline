#!/usr/bin/env python3
"""Validate byte-exact admission of the Buildbox repair package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


EXPERIMENT = "2026-08-25-mainline-a72-platform-provider-deferred-bind-repair"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def read(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"safe regular file: {path}")
    return path.read_text(encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path)
    args = parser.parse_args()
    root = (
        args.repository_root.resolve()
        if args.repository_root
        else Path(__file__).resolve().parents[3]
    )
    package = args.package.resolve()
    require(package.is_dir() and not package.is_symlink(), "safe package directory")
    contract = json.loads(read(root / "experiments" / EXPERIMENT / "contract.json"))
    patches = tuple(contract["planned_patches"])
    package_series = read(package / "patches/series").splitlines()
    require(tuple(package_series) == patches, "package patch order")
    canonical_series = read(root / "patches/series").splitlines()
    require(tuple(canonical_series[-len(patches):])
            == tuple(f"v7.1.3/{patch}" for patch in patches),
            "canonical series suffix")
    for patch in patches:
        generated = package / "patches" / patch
        admitted = root / "patches/v7.1.3" / patch
        require(generated.read_bytes() == admitted.read_bytes(),
                f"byte-identical patch: {patch}")

    provenance = read(package / "provenance/generation.txt").splitlines()
    expected = {
        "purpose=experiment-only-a72-platform-provider-readiness-repair",
        "repository_commit=9a2ca8279df983de2d7cd102aab83ef4140e1738",
        "parent_source_state=2fe5ef253a8c2fa73af53fa2f3b6a98df04da4faf35263ab145a69e2a6bd795e",
        "parent_source_integrity=7abaf44dfe744882e4fdbf46db13ae0ea4a558f197ec5a39137ede67e42da718",
        "generated_patch_count=3",
        "provider_not_ready_result=-EPROBE_DEFER",
        "provider_not_ready_platform_calls=0",
        "provider_not_ready_checkpoint_calls=0",
        "provider_not_ready_provider_calls=0",
        "provider_i2c_reads=10",
        "provider_i2c_writes=0",
        "hardware_free_tests=7",
        "device_action=none",
        "boot_candidate=false",
    }
    require(expected <= set(provenance), "exact package provenance markers")
    sums = package / "SHA256SUMS"
    require(hashlib.sha256(sums.read_bytes()).hexdigest()
            == "dfd2125eea25612e14271366625218750e11e44a083e896ffb25d324b732babc",
            "package checksum-manifest identity")
    print("admission_validation=pass")
    print("admitted_patches=3")


if __name__ == "__main__":
    main()
