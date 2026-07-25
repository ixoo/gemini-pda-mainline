#!/usr/bin/env python3
"""Validate Candidate AJ's isolated profile and unchanged AI patch boundary."""

from __future__ import annotations

import argparse
import json
import pathlib
import stat
import sys

sys.dont_write_bytecode = True

import candidate_aj as aj


def validate(repository: pathlib.Path) -> None:
    manifest_data = aj.read_regular(repository / "kernel/manifest.json", "kernel manifest")
    aj.validate_manifest_profile(manifest_data, "repository manifest")

    fragment = aj.read_regular(repository / aj.FRAGMENT_REL, "Candidate AJ fragment")
    if fragment != aj.EXPECTED_FRAGMENT or aj.digest_bytes(fragment) != aj.FRAGMENT_SHA256:
        raise ValueError("Candidate AJ fragment bytes changed")

    fragments = {
        relative: aj.read_regular(repository / relative, f"fragment {relative}")
        for relative in aj.FRAGMENTS
    }
    if aj.config_inputs_digest(fragments) != aj.CONFIG_INPUTS_SHA256:
        raise ValueError("Candidate AJ configuration-input identity changed")

    ai_series_validator = aj.load_ai_module(
        "validate-series-selection.py", "candidate_aj_ai_series_validator"
    )
    ai_series_validator.validate(repository)
    series = aj.read_regular(repository / aj.SERIES_REL, "Candidate AJ series")
    if aj.digest_bytes(series) != aj.SERIES_SHA256:
        raise ValueError("Candidate AJ series differs from exact Candidate AI")

    patch = aj.read_regular(
        repository / "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch",
        "corrected patch 0092",
    )
    if aj.digest_bytes(patch) != aj.PATCH_0092_SHA256:
        raise ValueError("corrected patch 0092 changed")


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
        print("validation=candidate-aj-profile")
        print(f"profile={aj.PROFILE}")
        print(f"series_path={aj.SERIES_REL}")
        print(f"series_sha256={aj.SERIES_SHA256}")
        print(f"patchset_sha256={aj.PATCHSET_SHA256}")
        print(f"fragment_sha256={aj.FRAGMENT_SHA256}")
        print(f"config_inputs_sha256={aj.CONFIG_INPUTS_SHA256}")
        print("resolved_delta=maxcpus-8-to-maxcpus-9-only")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
