#!/usr/bin/env python3
"""Validate Candidate AI's manifest-selected, path-sensitive patch series."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import pathlib
import stat
import sys

sys.dont_write_bytecode = True

AD_SERIES_SHA256 = "124db1a0c4d3d4f5ee43d75bbced9d4b5f28a649ef92c04acdb8ccb67be4117a"
AI_SERIES_SHA256 = "b172d419cc1e331932e734dda57be076872a442719dd6d406b217d81547dfd00"
AI_PATCHSET_SHA256 = "ba2cd5a66bd1fcff6552674d6d875d363e4ef0a24cfd10ede4f304136f0dc0dd"
PATCH_0092_SHA256 = "cbd54d048e2233ffcb268174037248ade9ab8716f9816481d926b20b4bd3bba5"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_package_validator() -> object:
    source = pathlib.Path(__file__).resolve().with_name("validate-package.py")
    spec = importlib.util.spec_from_file_location("gemini_ai_series_package", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AI package validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def derive_ad_series(current: bytes) -> bytes:
    output: list[bytes] = []
    saw_0087 = False
    for line in current.splitlines(keepends=True):
        text = line.decode("utf-8").rstrip("\r\n")
        if text and not text.startswith("#"):
            name = pathlib.PurePosixPath(text).name
            if not name[:4].isdigit():
                raise ValueError(f"series entry lacks a numeric prefix: {text}")
            if int(name[:4]) > 87:
                continue
            if name.startswith("0087-"):
                saw_0087 = True
        output.append(line)
    result = b"".join(output)
    if not saw_0087 or digest(result) != AD_SERIES_SHA256:
        raise ValueError("global series cannot reconstruct exact Candidate AD")
    return result


def validate(repository: pathlib.Path) -> None:
    package_validator = load_package_validator()
    manifest_data = read_regular(repository / "kernel/manifest.json", "kernel manifest")
    manifest = json.loads(manifest_data.decode("utf-8"))
    package_validator.validate_manifest_contract(
        manifest_data, "repository manifest", require_ai=True
    )
    profile = manifest["config"]["profiles"][package_validator.PROFILE]
    if profile.get("patch_series") != package_validator.AI_SERIES_REL:
        raise ValueError("Candidate AI profile did not select the isolated series path")

    ad_series = derive_ad_series(
        read_regular(repository / package_validator.AD_SERIES_REL, "global series")
    )
    ai_series = read_regular(
        repository / package_validator.AI_SERIES_REL, "Candidate AI series"
    )
    ad_entries = package_validator.series_entries(ad_series)
    ai_entries = package_validator.series_entries(ai_series)
    if digest(ai_series) != AI_SERIES_SHA256:
        raise ValueError("Candidate AI selected-series content changed")
    if len(ai_series.decode("utf-8").splitlines()) != 93:
        raise ValueError("Candidate AI selected-series line count changed")
    if ai_entries != [*ad_entries, package_validator.PATCH_0092]:
        raise ValueError("selected series is not exact AD entries plus corrected 0092")
    if len(ad_entries) != 88 or len(ai_entries) != 89:
        raise ValueError("Candidate AD/AI patch counts changed")
    for forbidden in ("/0088-", "/0089-", "/0090-", "/0091-", "/0093-"):
        if any(forbidden in f"/{entry}" for entry in ai_entries):
            raise ValueError(f"selected series includes forbidden feature {forbidden}")

    patch = read_regular(
        repository / "patches" / package_validator.PATCH_0092,
        "corrected patch 0092",
    )
    if digest(patch) != PATCH_0092_SHA256:
        raise ValueError("corrected patch 0092 changed")
    if (
        b"static bool mt6797_psci_cpu_can_disable(unsigned int cpu)" not in patch
        or b"+\treturn false;" not in patch
        or b"+\treturn true;" in patch
    ):
        raise ValueError("corrected patch 0092 no longer closes CPU disable")
    patchset = package_validator.patchset_digest(
        ai_series, repository / "patches", package_validator.AI_SERIES_REL
    )
    if patchset != AI_PATCHSET_SHA256:
        raise ValueError("path-sensitive Candidate AI patchset changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        info = args.repository.lstat()
        if args.repository.is_symlink() or not stat.S_ISDIR(info.st_mode):
            raise ValueError("repository path is unsafe")
        root = args.repository.resolve(strict=True)
        validate(root)
        print("validation=candidate-ai-path-selected-series")
        print("profile=observability-fbcon-rotation-keyboard-wrrd-manual-reboot-smp8-a72-reject-gate")
        print("series_path=patches/series-a72-reject-gate")
        print("series_lines=93")
        print("patch_count=89")
        print(f"series_sha256={AI_SERIES_SHA256}")
        print(f"patchset_sha256={AI_PATCHSET_SHA256}")
        print("series_entries=exact-ad-plus-corrected-0092")
        print("patches_0088_0091=absent")
        print("repository_modified=no")
        print("device_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
