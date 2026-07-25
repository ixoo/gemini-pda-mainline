#!/usr/bin/env python3
"""Validate Candidate AK's one-fragment profile over exact Candidate AJ."""

from __future__ import annotations

import argparse
import json
import pathlib
import stat
import sys

sys.dont_write_bytecode = True

import candidate_ak as ak


def validate(repository: pathlib.Path) -> None:
    manifest = ak.read_regular(repository / "kernel/manifest.json", "kernel manifest")
    ak.validate_manifest_profile(manifest, "repository manifest")

    fragment = ak.read_regular(repository / ak.FRAGMENT_REL, "Candidate AK fragment")
    if fragment != ak.EXPECTED_FRAGMENT or ak.digest_bytes(fragment) != ak.FRAGMENT_SHA256:
        raise ValueError("Candidate AK fragment bytes changed")

    fragments = {
        relative: ak.read_regular(repository / relative, f"fragment {relative}")
        for relative in ak.FRAGMENTS
    }
    if ak.config_inputs_digest(fragments) != ak.CONFIG_INPUTS_SHA256:
        raise ValueError("Candidate AK configuration-input identity changed")

    aj_validator = ak.load_aj_module("validate-profile.py", "candidate_ak_aj_profile")
    aj_validator.validate(repository)
    series = ak.read_regular(repository / ak.SERIES_REL, "Candidate AK series")
    if ak.digest_bytes(series) != ak.SERIES_SHA256:
        raise ValueError("Candidate AK series differs from exact Candidate AJ")
    patch = ak.read_regular(
        repository / "patches/v7.1.3/0092-arm64-mediatek-gate-MT6797-A72-PSCI-boot.patch",
        "corrected patch 0092",
    )
    if ak.digest_bytes(patch) != ak.PATCH_0092_SHA256:
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
        print("validation=candidate-ak-profile")
        print(f"profile={ak.PROFILE}")
        print(f"series_path={ak.SERIES_REL}")
        print(f"series_sha256={ak.SERIES_SHA256}")
        print(f"patchset_sha256={ak.PATCHSET_SHA256}")
        print(f"fragment_sha256={ak.FRAGMENT_SHA256}")
        print(f"config_inputs_sha256={ak.CONFIG_INPUTS_SHA256}")
        print("resolved_delta=maxcpus-9-to-maxcpus-10-only")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
