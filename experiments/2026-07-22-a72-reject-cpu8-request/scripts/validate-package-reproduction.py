#!/usr/bin/env python3
"""Compare two distinct Candidate AJ package outputs for reproduction."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import re
import stat
import sys

sys.dont_write_bytecode = True

import candidate_aj as aj


def load_package_validator() -> object:
    path = pathlib.Path(__file__).resolve().with_name("validate-package.py")
    spec = importlib.util.spec_from_file_location("candidate_aj_reproduction_package", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AJ package validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def inventory(root: pathlib.Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        info = path.lstat()
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise ValueError(f"package contains symlink: {relative}")
        if stat.S_ISREG(info.st_mode):
            result[relative] = (stat.S_IMODE(info.st_mode), aj.digest_path(path))
        elif not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"package contains special member: {relative}")
    return result


def normalized_build(path: pathlib.Path) -> tuple[bytes, str]:
    value = json.loads(aj.read_regular(path, "build provenance").decode("utf-8"))
    if not isinstance(value, dict) or "generated_utc" not in value:
        raise ValueError("build provenance is malformed")
    value = dict(value)
    generated = value.pop("generated_utc")
    if not isinstance(generated, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated
    ) is None:
        raise ValueError("build generation timestamp is malformed")
    normalized = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    return normalized, generated


def manifest_map(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    lines = aj.read_regular(path, "package manifest").decode("ascii").splitlines()
    for line in lines:
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or re.fullmatch(r"[0-9a-f]{64}", fields[0]) is None:
            raise ValueError("package manifest is malformed")
        relative = fields[1].removeprefix("*").removeprefix("./")
        if relative in result or relative == "SHA256SUMS":
            raise ValueError("package manifest path is unsafe or duplicated")
        result[relative] = fields[0]
    return result


def compare(first: pathlib.Path, second: pathlib.Path) -> dict[str, tuple[int, str]]:
    first_inventory = inventory(first)
    second_inventory = inventory(second)
    if set(first_inventory) != set(second_inventory) or len(first_inventory) != 226:
        raise ValueError("Candidate AJ package inventories differ")
    permitted = {"SHA256SUMS", "provenance/build.json"}
    changed = {
        name for name in first_inventory if first_inventory[name] != second_inventory[name]
    }
    if changed != permitted:
        unexpected = sorted(changed - permitted)
        missing = sorted(permitted - changed)
        raise ValueError(
            "Candidate AJ package differences do not prove a fresh reproduction: "
            f"unexpected={unexpected}, missing={missing}"
        )
    first_build, first_generated = normalized_build(first / "provenance/build.json")
    second_build, second_generated = normalized_build(second / "provenance/build.json")
    if first_build != second_build:
        raise ValueError("Candidate AJ normalized build provenance differs")
    if first_generated == second_generated:
        raise ValueError("Candidate AJ package generation timestamps are not distinct")
    for relative in set(first_inventory) - permitted:
        if (first / relative).read_bytes() != (second / relative).read_bytes():
            raise ValueError(f"Candidate AJ package bytes differ: {relative}")
    first_manifest = manifest_map(first / "SHA256SUMS")
    second_manifest = manifest_map(second / "SHA256SUMS")
    if set(first_manifest) != set(second_manifest):
        raise ValueError("Candidate AJ package-manifest inventories differ")
    changed_entries = {
        relative
        for relative in first_manifest
        if first_manifest[relative] != second_manifest[relative]
    }
    if changed_entries != {"provenance/build.json"}:
        raise ValueError(
            "Candidate AJ package manifests differ outside generated build provenance"
        )
    return first_inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=pathlib.Path, required=True)
    parser.add_argument("--second", type=pathlib.Path, required=True)
    parser.add_argument("--ad-package", type=pathlib.Path, required=True)
    parser.add_argument("--ai-package", type=pathlib.Path, required=True)
    parser.add_argument("--patch-0092", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        package_validator = load_package_validator()
        first = aj.resolve_directory(args.first, "first AJ package")
        second = aj.resolve_directory(args.second, "second AJ package")
        if first == second or first.samefile(second):
            raise ValueError("reproduction requires distinct package trees")
        ad = aj.resolve_directory(args.ad_package, "AD package")
        ai = aj.resolve_directory(args.ai_package, "AI package")
        patch = args.patch_0092.resolve(strict=True)
        first_audit = package_validator.validate_package(ad, ai, first, patch)
        second_audit = package_validator.validate_package(ad, ai, second, patch)
        members = compare(first, second)
        if first_audit != second_audit:
            raise ValueError("Candidate AJ compiled-gate audit reports differ")
        print("validation=candidate-aj-package-reproduction")
        print(f"members={len(members)}")
        print("substantive_bytes_identical=yes")
        print("modes_identical=yes")
        print("normalized_build_provenance=identical")
        print("generation_timestamps=distinct")
        print("independent_build_execution=requires-external-fresh-root-record")
        print("only_permitted_difference=generated_utc-and-derived-manifest-entry")
        print(f"package_manifest_sha256_first={aj.digest_path(first / 'SHA256SUMS')}")
        print(f"package_manifest_sha256_second={aj.digest_path(second / 'SHA256SUMS')}")
        print(f"image_sha256={aj.digest_path(first / 'Image')}")
        print(f"image_size={first.joinpath('Image').stat().st_size}")
        print(f"image_gz_sha256={aj.digest_path(first / 'Image.gz')}")
        print(f"image_gz_size={first.joinpath('Image.gz').stat().st_size}")
        print(f"system_map_sha256={aj.digest_path(first / 'System.map')}")
        print(
            "package_dtb_sha256="
            f"{aj.digest_path(first / package_validator.GEMINI_DTB)}"
        )
        print(f"compiled_gate_audit_sha256={aj.digest_bytes(first_audit)}")
        print("compiled_gate_audited_twice=yes")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
