#!/usr/bin/env python3
"""Validate one reproduced Candidate AK package against selected identities."""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.dont_write_bytecode = True

import candidate_ak as ak


def validate(package: pathlib.Path) -> None:
    ak.require_package_pins()
    manifest = ak.read_regular(package / "SHA256SUMS", "Candidate AK package manifest")
    if ak.digest_bytes(manifest) not in ak.PACKAGE_MANIFEST_SHA256S:
        raise ValueError("Candidate AK package manifest is not one of two reproduced builds")
    image = ak.read_regular(package / "Image", "Candidate AK Image")
    image_gz = ak.read_regular(package / "Image.gz", "Candidate AK Image.gz")
    system_map = ak.read_regular(package / "System.map", "Candidate AK System.map")
    config = ak.read_regular(package / "kernel.config", "Candidate AK config")
    if ak.digest_bytes(image) != ak.IMAGE_SHA256 or len(image) != int(ak.IMAGE_SIZE):
        raise ValueError("Candidate AK Image differs from the reproduced pin")
    if ak.digest_bytes(image_gz) != ak.IMAGE_GZ_SHA256 or len(image_gz) != int(ak.IMAGE_GZ_SIZE):
        raise ValueError("Candidate AK Image.gz differs from the reproduced pin")
    if ak.digest_bytes(system_map) != ak.SYSTEM_MAP_SHA256:
        raise ValueError("Candidate AK System.map differs from the reproduced pin")
    aj = ak.load_aj_identity("candidate_ak_pin_aj_identity")
    ai_package = aj.load_ai_module("validate-package.py", "candidate_ak_pin_ai_package")
    dtb = ak.read_regular(package / ai_package.GEMINI_DTB, "Candidate AK packaged DTB")
    if ak.digest_bytes(dtb) != ak.PACKAGE_DTB_SHA256:
        raise ValueError("Candidate AK packaged DTB differs from the reproduced pin")
    if ai_package.decompress_lk_image_gz(image_gz, "Candidate AK Image.gz") != image:
        raise ValueError("Candidate AK Image.gz does not expand to exact Image")
    ak.validate_kernel_policy(image, system_map, config, ai_package)
    auditor = aj.load_ai_module(
        "audit-mt6797-psci-cpu-boot.py", "candidate_ak_pin_gate_auditor"
    )
    audit = auditor.audit_kernel(package / "Image", package / "System.map")
    if ak.digest_bytes(audit) != ak.GATE_AUDIT_SHA256:
        raise ValueError("Candidate AK compiled-gate audit differs from the reproduced pin")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        ak.require_package_pins()
        package = ak.resolve_directory(args.package, "Candidate AK package")
        validate(package)
        print("validation=candidate-ak-reproduced-package-pins")
        print(f"package_manifest_sha256={ak.digest_path(package / 'SHA256SUMS')}")
        print(f"image_sha256={ak.IMAGE_SHA256}")
        print(f"image_size={ak.IMAGE_SIZE}")
        print(f"image_gz_sha256={ak.IMAGE_GZ_SHA256}")
        print(f"image_gz_size={ak.IMAGE_GZ_SIZE}")
        print(f"system_map_sha256={ak.SYSTEM_MAP_SHA256}")
        print(f"package_dtb_sha256={ak.PACKAGE_DTB_SHA256}")
        print(f"compiled_gate_audit_sha256={ak.GATE_AUDIT_SHA256}")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
