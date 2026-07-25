#!/usr/bin/env python3
"""Compare distinct Candidate AI package outputs without claiming build attestation."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import re
import stat
import sys

sys.dont_write_bytecode = True


DYNAMIC_MEMBERS = {"SHA256SUMS", "provenance/build.json"}


def load_module(path: pathlib.Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest_map(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("package manifest is malformed")
        member = fields[1].removeprefix("*").removeprefix("./")
        if member in result or member == "SHA256SUMS":
            raise ValueError("package manifest path is unsafe or duplicated")
        result[member] = fields[0]
    return result


def normalized_build(
    path: pathlib.Path, label: str
) -> tuple[dict[str, object], str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value).isdisjoint({"generated_utc"}):
        raise ValueError(f"{label} build provenance lacks generated_utc")
    generated = value.pop("generated_utc")
    if not isinstance(generated, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated
    ) is None:
        raise ValueError(f"{label} generated_utc is malformed")
    return value, generated


def compare_substantive(
    first: pathlib.Path, second: pathlib.Path, package_validator: object
) -> dict[str, pathlib.Path]:
    if first == second or first.samefile(second):
        raise ValueError("reproduction requires two distinct package trees")
    left = package_validator.validate_manifest(first)
    right = package_validator.validate_manifest(second)
    if set(left) != set(right):
        raise ValueError("reproduced package inventories differ")

    for relative in sorted(left):
        left_mode = stat.S_IMODE(left[relative].lstat().st_mode)
        right_mode = stat.S_IMODE(right[relative].lstat().st_mode)
        if left_mode != right_mode:
            raise ValueError(f"reproduced package mode differs: {relative}")
        if relative not in DYNAMIC_MEMBERS and left[relative].read_bytes() != right[
            relative
        ].read_bytes():
            raise ValueError(f"reproduced substantive bytes differ: {relative}")

    left_build, left_generated = normalized_build(
        first / "provenance/build.json", "first"
    )
    right_build, right_generated = normalized_build(
        second / "provenance/build.json", "second"
    )
    if left_build != right_build:
        raise ValueError("normalized build provenance differs")
    if left_generated == right_generated:
        raise ValueError("package trees have the same generation timestamp; possible clone")

    left_manifest = manifest_map(first / "SHA256SUMS")
    right_manifest = manifest_map(second / "SHA256SUMS")
    if set(left_manifest) != set(right_manifest):
        raise ValueError("reproduced manifest inventories differ")
    changed_manifest_entries = {
        member
        for member in left_manifest
        if left_manifest[member] != right_manifest[member]
    }
    if changed_manifest_entries != {"provenance/build.json"}:
        unexpected = changed_manifest_entries - {"provenance/build.json"}
        if not unexpected:
            raise ValueError("package manifests are identical; possible cloned tree")
        changed = sorted(unexpected)[0]
        raise ValueError(f"manifest records a substantive difference: {changed}")
    return left


def resolve_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"unsafe {label} directory")
    return path.resolve(strict=True)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=pathlib.Path, required=True)
    parser.add_argument("--second", type=pathlib.Path, required=True)
    parser.add_argument("--ad-package", type=pathlib.Path, required=True)
    parser.add_argument("--patch-0092", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        first = resolve_directory(args.first, "first package")
        second = resolve_directory(args.second, "second package")
        ad = resolve_directory(args.ad_package, "AD package")
        patch = args.patch_0092.resolve(strict=True)
        validator = load_module(
            pathlib.Path(__file__).resolve().parent / "validate-package.py",
            "gemini_ai_package_reproduction_validator",
        )
        validator.validate_package(ad, first, patch)
        validator.validate_package(ad, second, patch)
        members = compare_substantive(first, second, validator)
        print("validation=candidate-ai-distinct-package-output-reproduction")
        print(f"members={len(members)}")
        print("payloads=byte-identical")
        print("modes=identical")
        print("directory_inventory_and_modes=exact-0775")
        print("normalized_build_provenance=identical")
        print("generation_timestamps=distinct")
        print("independent_build_execution=requires-external-fresh-root-record")
        print("only_permitted_difference=generated_utc-and-derived-manifest-entry")
        for member in (
            "Image",
            "Image.gz",
            "System.map",
            "kernel.config",
            "dtbs/mediatek/mt6797-gemini-pda.dtb",
        ):
            print(f"{member.replace('/', '_').replace('.', '_')}_sha256={digest(members[member])}")
        print("compiled_gate_audited_twice=yes")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
