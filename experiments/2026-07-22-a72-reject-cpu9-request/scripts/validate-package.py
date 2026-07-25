#!/usr/bin/env python3
"""Validate the exact Candidate AJ to AK package transformation."""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
import zlib
from typing import Any

sys.dont_write_bytecode = True

import candidate_ak as ak

NEW_FRAGMENT_MEMBER = "provenance/configs/gemini-a72-reject-cpu9-request.fragment"
GEMINI_DTB = "dtbs/mediatek/mt6797-gemini-pda.dtb"
ALLOWED_CHANGED = {
    "SHA256SUMS", "Image", "Image.gz", "System.map", "kernel.config",
    "provenance/build.json", "provenance/kernel-manifest.json", NEW_FRAGMENT_MEMBER,
}
EXPECTED_PACKAGE_NAME = (
    f"linux-7.1.3-gemini-{ak.PROFILE}-{ak.PATCHSET_SHA256[:8]}-"
    f"{ak.CONFIG_INPUTS_SHA256[:8]}"
)
IKCONFIG_START = b"IKCFG_ST"
IKCONFIG_END = b"IKCFG_ED"
IKCONFIG_LIMIT = 16 * 1024 * 1024
REQUIRED_AUDIT_SEMANTICS = {
    b"compiled_cpu_ops_table=fail-closed\n",
    b"compiled_return_eagain=yes\n",
    b"resolved_calls=logging-only\n",
    b"psci_cpu_on_call=absent\n",
    b"compiled_can_disable_return=false\n",
    b"psci_cpu_off_callback=absent\n",
    b"hardware_transition_path=absent\n",
}


def decode_json_object(data: bytes, label: str) -> dict[str, Any]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate JSON member {key!r}")
            result[key] = value
        return result

    value = json.loads(
        data.decode("utf-8"), object_pairs_hook=unique,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"{label} contains invalid JSON number {value}")
        ),
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not an object")
    return value


def exact_json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            exact_json_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            exact_json_equal(old, new) for old, new in zip(left, right)
        )
    return left == right


def validate_manifest_delta(aj_bytes: bytes, candidate_bytes: bytes) -> dict[str, Any]:
    old = decode_json_object(aj_bytes, "Candidate AJ packaged manifest")
    new = decode_json_object(candidate_bytes, "Candidate AK packaged manifest")
    try:
        old_profiles = old["config"]["profiles"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Candidate AJ packaged manifest lacks config profiles") from exc
    if not isinstance(old_profiles, dict) or ak.PROFILE in old_profiles:
        raise ValueError("Candidate AJ packaged manifest profile boundary changed")
    expected = copy.deepcopy(old)
    expected["config"]["profiles"][ak.PROFILE] = {
        "base": "defconfig", "patch_series": ak.SERIES_REL, "fragments": ak.FRAGMENTS,
    }
    if not exact_json_equal(new, expected):
        raise ValueError("Candidate AK packaged manifest is not exact AJ plus one profile")
    return new


def extract_ikconfig(image: bytes) -> bytes:
    if image.count(IKCONFIG_START) != 1 or image.count(IKCONFIG_END) != 1:
        raise ValueError("Candidate AK Image does not contain one exact IKCONFIG record")
    start = image.index(IKCONFIG_START) + len(IKCONFIG_START)
    end = image.index(IKCONFIG_END)
    if end <= start:
        raise ValueError("Candidate AK Image IKCONFIG record is malformed")
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        config = decompressor.decompress(image[start:end], IKCONFIG_LIMIT + 1)
        if len(config) > IKCONFIG_LIMIT or decompressor.unconsumed_tail:
            raise ValueError("Candidate AK embedded config exceeds the extraction limit")
        config += decompressor.flush(IKCONFIG_LIMIT + 1 - len(config))
    except zlib.error as exc:
        raise ValueError(f"Candidate AK embedded config is invalid: {exc}") from exc
    if len(config) > IKCONFIG_LIMIT or not decompressor.eof:
        raise ValueError("Candidate AK embedded config is incomplete or oversized")
    if decompressor.unused_data or decompressor.unconsumed_tail or not config:
        raise ValueError("Candidate AK embedded config is not exactly one gzip stream")
    return config


def validate_plaintext_cmdline(image: bytes) -> None:
    command_line = ak.CMDLINE.encode("ascii")
    if image.count(command_line) != 2 or image.count(b"maxcpus=10") != 2:
        raise ValueError("Candidate AK Image plaintext maxcpus=10 policy is ambiguous")
    if ak.AJ_CMDLINE.encode("ascii") in image or b"maxcpus=9" in image:
        raise ValueError("Candidate AK Image retains Candidate AJ maxcpus=9 plaintext")


def validate_audit_semantics(audit: bytes) -> None:
    missing = sorted(marker for marker in REQUIRED_AUDIT_SEMANTICS if marker not in audit)
    if missing:
        raise ValueError(f"Candidate AK compiled-gate audit lacks {missing[0]!r}")


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    return decode_json_object(ak.read_regular(path, label), label)


def expected_build() -> dict[str, object]:
    return {
        "schema": 1,
        "kernel_release": "7.1.3-gemini-observability-L",
        "build_profile": ak.PROFILE,
        "base_config": "defconfig",
        "config_fragments": ak.FRAGMENTS,
        "config_inputs_sha256": ak.CONFIG_INPUTS_SHA256,
        "source_sha256": ak.SOURCE_SHA256,
        "patchset_sha256": ak.PATCHSET_SHA256,
        "config_sha256": ak.CONFIG_SHA256,
        "modules_built": False,
        "compiler": "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0",
        "linker": "GNU ld (GNU Binutils for Ubuntu) 2.42",
    }


def require_build(value: dict[str, Any]) -> None:
    expected = expected_build()
    if set(value) != set(expected) | {"generated_utc"}:
        raise ValueError("Candidate AK build-provenance inventory changed")
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ValueError(f"Candidate AK build provenance changed: {key}")
    generated = value.get("generated_utc")
    if not isinstance(generated, str) or not generated.endswith("Z"):
        raise ValueError("Candidate AK generated_utc is malformed")


def validate_package(
    ad_package: pathlib.Path,
    ai_package: pathlib.Path,
    aj_package: pathlib.Path,
    candidate_package: pathlib.Path,
    patch_0092: pathlib.Path,
) -> bytes:
    if len({ad_package, ai_package, aj_package, candidate_package}) != 4:
        raise ValueError("AD, AI, AJ, and AK packages must be distinct trees")
    aj_pin_validator = ak.load_aj_module(
        "validate-package-pins.py", "candidate_ak_exact_aj_package_pins"
    )
    aj_pin_validator.validate(aj_package)
    aj_validator = ak.load_aj_module("validate-package.py", "candidate_ak_aj_package")
    aj_validator.validate_package(ad_package, ai_package, aj_package, patch_0092)
    aj_identity = ak.load_aj_identity("candidate_ak_package_aj_identity")
    ai_validator = aj_identity.load_ai_module(
        "validate-package.py", "candidate_ak_ai_package_foundation"
    )

    aj_members = ai_validator.validate_manifest(aj_package)
    candidate_members = ai_validator.validate_manifest(candidate_package)
    if set(candidate_members) != set(aj_members) | {NEW_FRAGMENT_MEMBER}:
        raise ValueError("Candidate AK package inventory is not exact AJ plus one fragment")
    if len(candidate_members) != 227:
        raise ValueError("Candidate AK package does not contain exactly 227 members")
    ai_validator.validate_package_file_modes(aj_members, "Candidate AJ")
    ai_validator.validate_package_file_modes(candidate_members, "Candidate AK")
    for relative in sorted(set(aj_members) - ALLOWED_CHANGED):
        if ak.read_regular(aj_members[relative], f"AJ member {relative}") != ak.read_regular(
            candidate_members[relative], f"AK member {relative}"
        ):
            raise ValueError(f"Candidate AK changed non-command-line package member: {relative}")

    if candidate_package.name != EXPECTED_PACKAGE_NAME:
        raise ValueError("Candidate AK package basename disagrees with exact inputs")
    fragment = ak.read_regular(candidate_members[NEW_FRAGMENT_MEMBER], "packaged AK fragment")
    if fragment != ak.EXPECTED_FRAGMENT or ak.digest_bytes(fragment) != ak.FRAGMENT_SHA256:
        raise ValueError("packaged Candidate AK fragment changed")

    aj_manifest = ak.read_regular(
        aj_package / "provenance/kernel-manifest.json", "AJ packaged manifest"
    )
    candidate_manifest = ak.read_regular(
        candidate_package / "provenance/kernel-manifest.json", "AK packaged manifest"
    )
    validate_manifest_delta(aj_manifest, candidate_manifest)
    build = decode_json_object(
        ak.read_regular(candidate_package / "provenance/build.json", "AK build"), "AK build"
    )
    require_build(build)

    aj_config = ak.read_regular(aj_package / "kernel.config", "AJ config")
    candidate_config = ak.read_regular(candidate_package / "kernel.config", "AK config")
    if candidate_config != ak.derive_config(aj_config):
        raise ValueError("Candidate AK config is not exact AJ maxcpus transform")

    candidate_image = ak.read_regular(candidate_package / "Image", "AK Image")
    image_gz = ak.read_regular(candidate_package / "Image.gz", "AK Image.gz")
    if ai_validator.decompress_lk_image_gz(image_gz, "Candidate AK Image.gz") != candidate_image:
        raise ValueError("Candidate AK Image.gz does not expand to exact Image")
    if extract_ikconfig(candidate_image) != candidate_config:
        raise ValueError("Candidate AK embedded config is not exact kernel.config")
    validate_plaintext_cmdline(candidate_image)
    system_map = ak.read_regular(candidate_package / "System.map", "AK System.map")
    ak.validate_kernel_policy(candidate_image, system_map, candidate_config, ai_validator)

    gate_auditor = aj_identity.load_ai_module(
        "audit-mt6797-psci-cpu-boot.py", "candidate_ak_gate_auditor"
    )
    audit = gate_auditor.audit_kernel(
        candidate_package / "Image", candidate_package / "System.map"
    )
    validate_audit_semantics(audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ad-package", type=pathlib.Path, required=True)
    parser.add_argument("--ai-package", type=pathlib.Path, required=True)
    parser.add_argument("--aj-package", type=pathlib.Path, required=True)
    parser.add_argument("--candidate-package", type=pathlib.Path, required=True)
    parser.add_argument("--patch-0092", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        ad = ak.resolve_directory(args.ad_package, "AD package")
        ai = ak.resolve_directory(args.ai_package, "AI package")
        aj = ak.resolve_directory(args.aj_package, "AJ package")
        candidate = ak.resolve_directory(args.candidate_package, "AK package")
        patch = args.patch_0092.resolve(strict=True)
        audit = validate_package(ad, ai, aj, candidate, patch)
        print("validation=candidate-ak-package")
        print(f"package={candidate.name}")
        print(f"profile={ak.PROFILE}")
        print(f"series_sha256={ak.SERIES_SHA256}")
        print(f"patchset_sha256={ak.PATCHSET_SHA256}")
        print(f"config_inputs_sha256={ak.CONFIG_INPUTS_SHA256}")
        print(f"config_sha256={ak.CONFIG_SHA256}")
        print(f"package_manifest_sha256={ak.digest_path(candidate / 'SHA256SUMS')}")
        print(f"image_sha256={ak.digest_path(candidate / 'Image')}")
        print(f"image_size={candidate.joinpath('Image').stat().st_size}")
        print(f"image_gz_sha256={ak.digest_path(candidate / 'Image.gz')}")
        print(f"image_gz_size={candidate.joinpath('Image.gz').stat().st_size}")
        print(f"system_map_sha256={ak.digest_path(candidate / 'System.map')}")
        print(f"package_dtb_sha256={ak.digest_path(candidate / GEMINI_DTB)}")
        print(f"compiled_gate_audit_sha256={ak.digest_bytes(audit)}")
        print("embedded_config=byte-exact-kernel.config")
        print("plaintext_cmdline=exact-maxcpus-10")
        print("compiled_gate_semantics=fail-closed-no-hardware-transition")
        print("dtbs=byte-exact-candidate-aj")
        print("active_cpu_request=logical-cpu8-and-cpu9-rejection")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
