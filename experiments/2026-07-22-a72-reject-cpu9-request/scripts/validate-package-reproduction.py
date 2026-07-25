#!/usr/bin/env python3
"""Compare two distinct Candidate AK package outputs for reproduction."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import re
import stat
import sys

sys.dont_write_bytecode = True

import candidate_ak as ak


def load_validator() -> object:
    path = pathlib.Path(__file__).resolve().with_name("validate-package.py")
    ak.read_regular(path, "Candidate AK package validator")
    spec = importlib.util.spec_from_file_location("candidate_ak_reproduction_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AK package validator")
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
            result[relative] = (stat.S_IMODE(info.st_mode), ak.digest_path(path))
        elif not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"package contains special member: {relative}")
    return result


def normalized_build(path: pathlib.Path) -> tuple[bytes, str]:
    value = json.loads(ak.read_regular(path, "build provenance").decode("utf-8"))
    if not isinstance(value, dict) or "generated_utc" not in value:
        raise ValueError("build provenance is malformed")
    value = dict(value)
    generated = value.pop("generated_utc")
    if not isinstance(generated, str) or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", generated
    ) is None:
        raise ValueError("build generation timestamp is malformed")
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode(), generated


def manifest_map(path: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in ak.read_regular(path, "package manifest").decode("ascii").splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) != 2 or ak.HEX256.fullmatch(fields[0]) is None:
            raise ValueError("package manifest is malformed")
        relative = fields[1].removeprefix("*").removeprefix("./")
        if relative in result or relative == "SHA256SUMS":
            raise ValueError("package manifest path is unsafe or duplicated")
        result[relative] = fields[0]
    return result


def compare(first: pathlib.Path, second: pathlib.Path) -> dict[str, tuple[int, str]]:
    one = inventory(first)
    two = inventory(second)
    if set(one) != set(two) or len(one) != 227:
        raise ValueError("Candidate AK package inventories differ")
    permitted = {"SHA256SUMS", "provenance/build.json"}
    changed = {name for name in one if one[name] != two[name]}
    if changed != permitted:
        raise ValueError(
            "Candidate AK package differences do not prove a fresh reproduction: "
            f"unexpected={sorted(changed - permitted)}, missing={sorted(permitted - changed)}"
        )
    first_build, first_time = normalized_build(first / "provenance/build.json")
    second_build, second_time = normalized_build(second / "provenance/build.json")
    if first_build != second_build or first_time == second_time:
        raise ValueError("Candidate AK normalized build provenance or timestamps disagree")
    for relative in set(one) - permitted:
        if (first / relative).read_bytes() != (second / relative).read_bytes():
            raise ValueError(f"Candidate AK package bytes differ: {relative}")
    first_manifest = manifest_map(first / "SHA256SUMS")
    second_manifest = manifest_map(second / "SHA256SUMS")
    if set(first_manifest) != set(second_manifest):
        raise ValueError("Candidate AK package-manifest inventories differ")
    changed_entries = {
        relative for relative in first_manifest
        if first_manifest[relative] != second_manifest[relative]
    }
    if changed_entries != {"provenance/build.json"}:
        raise ValueError("Candidate AK manifests differ outside generated build provenance")
    return one


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("first", "second", "ad-package", "ai-package", "aj-package", "patch-0092"):
        parser.add_argument(f"--{name}", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        validator = load_validator()
        first = ak.resolve_directory(args.first, "first AK package")
        second = ak.resolve_directory(args.second, "second AK package")
        if first == second or first.samefile(second):
            raise ValueError("reproduction requires distinct package trees")
        ad = ak.resolve_directory(args.ad_package, "AD package")
        ai = ak.resolve_directory(args.ai_package, "AI package")
        aj = ak.resolve_directory(args.aj_package, "AJ package")
        patch = args.patch_0092.resolve(strict=True)
        first_audit = validator.validate_package(ad, ai, aj, first, patch)
        second_audit = validator.validate_package(ad, ai, aj, second, patch)
        members = compare(first, second)
        if first_audit != second_audit:
            raise ValueError("Candidate AK compiled-gate audit reports differ")
        print("validation=candidate-ak-package-reproduction")
        print(f"members={len(members)}")
        print("substantive_bytes_identical=yes")
        print("modes_identical=yes")
        print("normalized_build_provenance=identical")
        print("generation_timestamps=distinct")
        print("only_permitted_difference=generated_utc-and-derived-manifest-entry")
        print(f"package_manifest_sha256_first={ak.digest_path(first / 'SHA256SUMS')}")
        print(f"package_manifest_sha256_second={ak.digest_path(second / 'SHA256SUMS')}")
        print(f"image_sha256={ak.digest_path(first / 'Image')}")
        print(f"image_size={first.joinpath('Image').stat().st_size}")
        print(f"image_gz_sha256={ak.digest_path(first / 'Image.gz')}")
        print(f"image_gz_size={first.joinpath('Image.gz').stat().st_size}")
        print(f"system_map_sha256={ak.digest_path(first / 'System.map')}")
        print(f"config_sha256={ak.digest_path(first / 'kernel.config')}")
        print(f"package_dtb_sha256={ak.digest_path(first / validator.GEMINI_DTB)}")
        print(f"compiled_gate_audit_sha256={ak.digest_bytes(first_audit)}")
        print("compiled_gate_audited_twice=yes")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
