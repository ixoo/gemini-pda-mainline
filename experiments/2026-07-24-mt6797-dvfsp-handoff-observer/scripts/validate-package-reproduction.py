#!/usr/bin/env python3
"""Compare two independently generated Candidate AN package outputs."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import stat
import struct
import sys
import zlib
from types import ModuleType
from typing import Any


sys.dont_write_bytecode = True
DYNAMIC_MEMBERS = {"SHA256SUMS", "provenance/build.json"}


def load_validator() -> ModuleType:
    source = pathlib.Path(__file__).resolve().with_name("validate-package.py")
    spec = importlib.util.spec_from_file_location(
        "candidate_an_package_validator", source
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AN package validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_build(
    validator: ModuleType, path: pathlib.Path, label: str
) -> tuple[bytes, str]:
    value = validator.load_json(path, f"{label} build provenance")
    generated = value.get("generated_utc")
    normalized = validator.normalized_build_bytes(value, f"{label} build")
    if not isinstance(generated, str):
        raise ValueError(f"{label} build generation timestamp is malformed")
    return normalized, generated


def compare_packages(
    validator: ModuleType,
    first: pathlib.Path,
    second: pathlib.Path,
) -> dict[str, pathlib.Path]:
    if first == second or first.samefile(second):
        raise ValueError("reproduction requires two distinct package trees")
    left = validator.validate_package_manifest(first)
    right = validator.validate_package_manifest(second)
    if set(left) != set(right):
        raise ValueError("Candidate AN package inventories differ")

    changed: set[str] = set()
    for relative in sorted(left):
        left_mode = stat.S_IMODE(left[relative].lstat().st_mode)
        right_mode = stat.S_IMODE(right[relative].lstat().st_mode)
        if left_mode != right_mode:
            raise ValueError(f"reproduced package mode differs: {relative}")
        if left[relative].read_bytes() != right[relative].read_bytes():
            changed.add(relative)
    if changed != DYNAMIC_MEMBERS:
        raise ValueError(
            "package differences are not only generated_utc and its manifest: "
            f"unexpected={sorted(changed - DYNAMIC_MEMBERS)}, "
            f"missing={sorted(DYNAMIC_MEMBERS - changed)}"
        )

    left_build, left_generated = normalized_build(
        validator, first / "provenance/build.json", "first"
    )
    right_build, right_generated = normalized_build(
        validator, second / "provenance/build.json", "second"
    )
    if left_build != right_build:
        raise ValueError("normalized Candidate AN build provenance differs")
    if left_generated == right_generated:
        raise ValueError(
            "package generation timestamps are identical; independent execution "
            "is not attributable"
        )

    left_manifest = validator.manifest_map(first / "SHA256SUMS")
    right_manifest = validator.manifest_map(second / "SHA256SUMS")
    if set(left_manifest) != set(right_manifest):
        raise ValueError("Candidate AN manifest inventories differ")
    changed_entries = {
        relative
        for relative in left_manifest
        if left_manifest[relative] != right_manifest[relative]
    }
    if changed_entries != {"provenance/build.json"}:
        raise ValueError(
            "Candidate AN manifests differ outside generated build provenance"
        )
    if (
        left_manifest["provenance/build.json"]
        != digest_bytes(left["provenance/build.json"].read_bytes())
        or right_manifest["provenance/build.json"]
        != digest_bytes(right["provenance/build.json"].read_bytes())
    ):
        raise ValueError("Candidate AN manifest build entries are inconsistent")
    return left


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=pathlib.Path, required=True)
    parser.add_argument("--first", type=pathlib.Path, required=True)
    parser.add_argument("--second", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        validator = load_validator()
        repository = validator.resolve_directory(args.repository, "repository")
        first = validator.resolve_directory(args.first, "first Candidate AN package")
        second = validator.resolve_directory(
            args.second, "second Candidate AN package"
        )
        first_calibration = validator.validate_package(repository, first)
        second_calibration = validator.validate_package(repository, second)
        members = compare_packages(validator, first, second)
        for key in (
            "normalized_build_sha256",
            "config_sha256",
            "image_sha256",
            "image_size",
            "image_gz_sha256",
            "image_gz_size",
            "system_map_sha256",
            "compiled_gate_audit_sha256",
            "package_dtb_sha256",
        ):
            if first_calibration[key] != second_calibration[key]:
                raise ValueError(f"reproduced calibration differs: {key}")

        normalized, _ = normalized_build(
            validator, first / "provenance/build.json", "first"
        )
        print("validation=candidate-an-package-reproduction-calibration")
        print(f"profile={validator.PROFILE}")
        print(f"members={len(members)}")
        print("substantive_bytes_identical=yes")
        print("modes_identical=yes")
        print("normalized_build_provenance=identical")
        print("generation_timestamps=distinct")
        print("only_permitted_difference=generated_utc-and-derived-manifest-entry")
        print(
            "calibration_package_manifest_sha256_first="
            f"{validator.digest_path(first / 'SHA256SUMS')}"
        )
        print(
            "calibration_package_manifest_sha256_second="
            f"{validator.digest_path(second / 'SHA256SUMS')}"
        )
        print(f"calibration_normalized_build_sha256={digest_bytes(normalized)}")
        for key in (
            "config_sha256",
            "image_sha256",
            "image_size",
            "image_gz_sha256",
            "image_gz_size",
            "system_map_sha256",
            "compiled_gate_audit_sha256",
            "package_dtb_sha256",
        ):
            print(f"calibration_{key}={first_calibration[key]}")
        print("output_hashes_pinned=no")
        print("independent_build_execution=requires-external-fresh-root-record")
        print("artifact_build=none")
        print("device_access=none")
        print("storage_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
        struct.error,
        zlib.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
