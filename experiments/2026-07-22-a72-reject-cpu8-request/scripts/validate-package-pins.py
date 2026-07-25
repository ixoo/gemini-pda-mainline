#!/usr/bin/env python3
"""Validate one reproduced AJ package against post-build selected identities."""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.dont_write_bytecode = True

import candidate_aj as aj


def validate(package: pathlib.Path) -> None:
    aj.require_package_pins()
    manifest = aj.read_regular(package / "SHA256SUMS", "Candidate AJ package manifest")
    if aj.digest_bytes(manifest) not in aj.PACKAGE_MANIFEST_SHA256S:
        raise ValueError("Candidate AJ package manifest is not one of two reproduced builds")

    image = aj.read_regular(package / "Image", "Candidate AJ Image")
    image_gz = aj.read_regular(package / "Image.gz", "Candidate AJ Image.gz")
    system_map = aj.read_regular(package / "System.map", "Candidate AJ System.map")
    config = aj.read_regular(package / "kernel.config", "Candidate AJ config")
    if aj.digest_bytes(image) != aj.IMAGE_SHA256 or len(image) != int(aj.IMAGE_SIZE):
        raise ValueError("Candidate AJ Image differs from the reproduced pin")
    if (
        aj.digest_bytes(image_gz) != aj.IMAGE_GZ_SHA256
        or len(image_gz) != int(aj.IMAGE_GZ_SIZE)
    ):
        raise ValueError("Candidate AJ Image.gz differs from the reproduced pin")
    if aj.digest_bytes(system_map) != aj.SYSTEM_MAP_SHA256:
        raise ValueError("Candidate AJ System.map differs from the reproduced pin")

    ai_package = aj.load_ai_module("validate-package.py", "candidate_aj_pin_package")
    package_dtb = aj.read_regular(
        package / ai_package.GEMINI_DTB, "Candidate AJ packaged Gemini DTB"
    )
    if aj.digest_bytes(package_dtb) != aj.PACKAGE_DTB_SHA256:
        raise ValueError("Candidate AJ packaged Gemini DTB differs from the reproduced pin")
    if ai_package.decompress_lk_image_gz(image_gz, "Candidate AJ Image.gz") != image:
        raise ValueError("Candidate AJ Image.gz does not expand to exact Image")
    aj.validate_kernel_policy(image, system_map, config, ai_package)

    gate_auditor = aj.load_ai_module(
        "audit-mt6797-psci-cpu-boot.py", "candidate_aj_pin_gate_auditor"
    )
    audit = gate_auditor.audit_kernel(package / "Image", package / "System.map")
    if aj.digest_bytes(audit) != aj.GATE_AUDIT_SHA256:
        raise ValueError("Candidate AJ compiled-gate audit differs from the reproduced pin")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        # Refuse before package-path resolution or member I/O until two fresh
        # package builds have reproduced and their identities are selected.
        aj.require_package_pins()
        package = aj.resolve_directory(args.package, "Candidate AJ package")
        validate(package)
        print("validation=candidate-aj-reproduced-package-pins")
        print(f"package_manifest_sha256={aj.digest_path(package / 'SHA256SUMS')}")
        print(f"image_sha256={aj.IMAGE_SHA256}")
        print(f"image_size={aj.IMAGE_SIZE}")
        print(f"image_gz_sha256={aj.IMAGE_GZ_SHA256}")
        print(f"image_gz_size={aj.IMAGE_GZ_SIZE}")
        print(f"system_map_sha256={aj.SYSTEM_MAP_SHA256}")
        print(f"package_dtb_sha256={aj.PACKAGE_DTB_SHA256}")
        print(f"compiled_gate_audit_sha256={aj.GATE_AUDIT_SHA256}")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
