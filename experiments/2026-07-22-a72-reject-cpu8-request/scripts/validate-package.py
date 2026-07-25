#!/usr/bin/env python3
"""Validate the exact Candidate AI to AJ package transformation."""

from __future__ import annotations

import argparse
import copy
import json
import pathlib
import sys
import zlib
from typing import Any

sys.dont_write_bytecode = True

import candidate_aj as aj

NEW_FRAGMENT_MEMBER = "provenance/configs/gemini-a72-reject-cpu8-request.fragment"
GEMINI_DTB = "dtbs/mediatek/mt6797-gemini-pda.dtb"
ALLOWED_CHANGED = {
    "SHA256SUMS",
    "Image",
    "Image.gz",
    "System.map",
    "kernel.config",
    "provenance/build.json",
    "provenance/kernel-manifest.json",
    NEW_FRAGMENT_MEMBER,
}
EXPECTED_PACKAGE_NAME = (
    f"linux-7.1.3-gemini-{aj.PROFILE}-{aj.PATCHSET_SHA256[:8]}-"
    f"{aj.CONFIG_INPUTS_SHA256[:8]}"
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
    """Decode one JSON object while rejecting duplicate member names."""

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate JSON member {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"{label} contains invalid JSON number {value}")

    value = json.loads(
        data.decode("utf-8"),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not an object")
    return value


def exact_json_equal(left: Any, right: Any) -> bool:
    """Compare decoded JSON values without Python's bool/int coercion."""

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


def validate_manifest_delta(
    ai_bytes: bytes, candidate_bytes: bytes
) -> dict[str, Any]:
    """Require the candidate manifest to be exact AI plus the AJ profile."""

    ai_value = decode_json_object(ai_bytes, "Candidate AI packaged manifest")
    candidate_value = decode_json_object(
        candidate_bytes, "Candidate AJ packaged manifest"
    )
    try:
        ai_profiles = ai_value["config"]["profiles"]
    except (KeyError, TypeError) as exc:
        raise ValueError("Candidate AI packaged manifest lacks config profiles") from exc
    if not isinstance(ai_profiles, dict):
        raise ValueError("Candidate AI packaged manifest profiles are not an object")
    if aj.PROFILE in ai_profiles:
        raise ValueError("Candidate AI packaged manifest already contains Candidate AJ")

    expected = copy.deepcopy(ai_value)
    expected["config"]["profiles"][aj.PROFILE] = {
        "base": "defconfig",
        "patch_series": aj.SERIES_REL,
        "fragments": aj.FRAGMENTS,
    }
    if not exact_json_equal(candidate_value, expected):
        raise ValueError(
            "Candidate AJ packaged manifest is not exact Candidate AI plus one AJ profile"
        )
    return candidate_value


def extract_ikconfig(image: bytes) -> bytes:
    """Extract one bounded, single-member CONFIG_IKCONFIG payload."""

    if image.count(IKCONFIG_START) != 1 or image.count(IKCONFIG_END) != 1:
        raise ValueError("Candidate AJ Image does not contain one exact IKCONFIG record")
    start = image.index(IKCONFIG_START) + len(IKCONFIG_START)
    end = image.index(IKCONFIG_END)
    if end <= start:
        raise ValueError("Candidate AJ Image IKCONFIG record is malformed")

    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        config = decompressor.decompress(image[start:end], IKCONFIG_LIMIT + 1)
        if len(config) > IKCONFIG_LIMIT or decompressor.unconsumed_tail:
            raise ValueError("Candidate AJ embedded config exceeds the extraction limit")
        config += decompressor.flush(IKCONFIG_LIMIT + 1 - len(config))
    except zlib.error as exc:
        raise ValueError(f"Candidate AJ embedded config is invalid: {exc}") from exc
    if len(config) > IKCONFIG_LIMIT:
        raise ValueError("Candidate AJ embedded config exceeds the extraction limit")
    if not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
        raise ValueError("Candidate AJ embedded config is not exactly one gzip stream")
    if not config:
        raise ValueError("Candidate AJ embedded config is empty")
    return config


def validate_plaintext_cmdline(image: bytes) -> None:
    """Require only the exact AJ forced command line in compiled plaintext."""

    command_line = aj.CMDLINE.encode("ascii")
    if image.count(command_line) != 2:
        raise ValueError("Candidate AJ Image lacks two exact plaintext command lines")
    if image.count(b"maxcpus=9") != 2:
        raise ValueError("Candidate AJ Image plaintext maxcpus=9 policy is ambiguous")
    if aj.AI_CMDLINE.encode("ascii") in image or b"maxcpus=8" in image:
        raise ValueError("Candidate AJ Image retains Candidate AI maxcpus=8 plaintext")


def validate_audit_semantics(audit: bytes) -> None:
    """Confirm the source-pinned auditor reported every fail-closed property."""

    missing = sorted(marker for marker in REQUIRED_AUDIT_SEMANTICS if marker not in audit)
    if missing:
        raise ValueError(f"Candidate AJ compiled-gate audit lacks {missing[0]!r}")


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    return decode_json_object(aj.read_regular(path, label), label)


def expected_build() -> dict[str, object]:
    return {
        "schema": 1,
        "kernel_release": "7.1.3-gemini-observability-L",
        "build_profile": aj.PROFILE,
        "base_config": "defconfig",
        "config_fragments": aj.FRAGMENTS,
        "config_inputs_sha256": aj.CONFIG_INPUTS_SHA256,
        "source_sha256": aj.SOURCE_SHA256,
        "patchset_sha256": aj.PATCHSET_SHA256,
        "config_sha256": aj.CONFIG_SHA256,
        "modules_built": False,
        "compiler": "gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0",
        "linker": "GNU ld (GNU Binutils for Ubuntu) 2.42",
    }


def require_build(value: dict[str, Any]) -> None:
    expected = expected_build()
    if set(value) != set(expected) | {"generated_utc"}:
        raise ValueError("Candidate AJ build-provenance inventory changed")
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ValueError(f"Candidate AJ build provenance changed: {key}")
    generated = value.get("generated_utc")
    if not isinstance(generated, str) or not generated.endswith("Z"):
        raise ValueError("Candidate AJ generated_utc is malformed")


def compare_unchanged_members(
    ai_members: dict[str, pathlib.Path], candidate_members: dict[str, pathlib.Path]
) -> None:
    for relative in sorted(set(ai_members) - ALLOWED_CHANGED):
        old = aj.read_regular(ai_members[relative], f"AI package member {relative}")
        new = aj.read_regular(candidate_members[relative], f"AJ package member {relative}")
        if old != new:
            raise ValueError(f"Candidate AJ changed non-command-line package member: {relative}")


def validate_package(
    ad_package: pathlib.Path,
    ai_package: pathlib.Path,
    candidate_package: pathlib.Path,
    patch_0092: pathlib.Path,
) -> bytes:
    if len({ad_package, ai_package, candidate_package}) != 3:
        raise ValueError("AD, AI, and AJ packages must be distinct trees")
    ai_validator = aj.load_ai_module("validate-package.py", "candidate_aj_ai_package")
    ai_validator.validate_package(ad_package, ai_package, patch_0092)

    ai_members = ai_validator.validate_manifest(ai_package)
    candidate_members = ai_validator.validate_manifest(candidate_package)
    ai_manifest_hash = aj.digest_bytes(
        aj.read_regular(ai_package / "SHA256SUMS", "Candidate AI package manifest")
    )
    if ai_manifest_hash not in aj.AI_PACKAGE_MANIFEST_SHA256S:
        raise ValueError("baseline package is not an accepted Candidate AI build")
    if set(candidate_members) != set(ai_members) | {NEW_FRAGMENT_MEMBER}:
        raise ValueError("Candidate AJ package inventory is not exact AI plus one fragment")
    if len(candidate_members) != 226:
        raise ValueError("Candidate AJ package does not contain exactly 226 members")
    ai_validator.validate_package_file_modes(ai_members, "Candidate AI")
    ai_validator.validate_package_file_modes(candidate_members, "Candidate AJ")
    compare_unchanged_members(ai_members, candidate_members)

    if candidate_package.name != EXPECTED_PACKAGE_NAME:
        raise ValueError("Candidate AJ package basename disagrees with exact inputs")
    fragment = aj.read_regular(candidate_members[NEW_FRAGMENT_MEMBER], "packaged AJ fragment")
    if fragment != aj.EXPECTED_FRAGMENT or aj.digest_bytes(fragment) != aj.FRAGMENT_SHA256:
        raise ValueError("packaged Candidate AJ fragment changed")

    ai_manifest = aj.read_regular(
        ai_package / "provenance/kernel-manifest.json", "AI packaged manifest"
    )
    ai_validator.validate_manifest_contract(ai_manifest, "AI packaged manifest", require_ai=True)
    candidate_manifest = aj.read_regular(
        candidate_package / "provenance/kernel-manifest.json", "AJ packaged manifest"
    )
    validate_manifest_delta(ai_manifest, candidate_manifest)

    require_build(load_json(candidate_package / "provenance/build.json", "AJ build"))

    ai_config = aj.read_regular(ai_package / "kernel.config", "AI config")
    candidate_config = aj.read_regular(candidate_package / "kernel.config", "AJ config")
    if candidate_config != aj.derive_config(ai_config):
        raise ValueError("Candidate AJ config is not exact AI maxcpus transform")
    if b"CONFIG_HOTPLUG_PARALLEL=y" in candidate_config:
        raise ValueError("Candidate AJ unexpectedly enables parallel CPU hotplug")

    candidate_image = aj.read_regular(candidate_package / "Image", "AJ Image")
    image_gz = aj.read_regular(candidate_package / "Image.gz", "AJ Image.gz")
    if ai_validator.decompress_lk_image_gz(image_gz, "Candidate AJ Image.gz") != candidate_image:
        raise ValueError("Candidate AJ Image.gz does not expand to exact Image")
    embedded_config = extract_ikconfig(candidate_image)
    if embedded_config != candidate_config:
        raise ValueError("Candidate AJ embedded config is not exact kernel.config")
    validate_plaintext_cmdline(candidate_image)

    system_map = aj.read_regular(candidate_package / "System.map", "AJ System.map")
    aj.validate_kernel_policy(
        candidate_image,
        system_map,
        candidate_config,
        ai_validator=ai_validator,
    )
    gate_auditor = aj.load_ai_module(
        "audit-mt6797-psci-cpu-boot.py", "candidate_aj_gate_auditor"
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
    parser.add_argument("--candidate-package", type=pathlib.Path, required=True)
    parser.add_argument("--patch-0092", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        ad = aj.resolve_directory(args.ad_package, "AD package")
        ai = aj.resolve_directory(args.ai_package, "AI package")
        candidate = aj.resolve_directory(args.candidate_package, "AJ package")
        patch = args.patch_0092.resolve(strict=True)
        audit = validate_package(ad, ai, candidate, patch)
        print("validation=candidate-aj-package")
        print(f"package={candidate.name}")
        print(f"profile={aj.PROFILE}")
        print(f"series_sha256={aj.SERIES_SHA256}")
        print(f"patchset_sha256={aj.PATCHSET_SHA256}")
        print(f"config_inputs_sha256={aj.CONFIG_INPUTS_SHA256}")
        print(f"config_sha256={aj.CONFIG_SHA256}")
        print(f"package_manifest_sha256={aj.digest_path(candidate / 'SHA256SUMS')}")
        print(f"image_sha256={aj.digest_path(candidate / 'Image')}")
        print(f"image_size={candidate.joinpath('Image').stat().st_size}")
        print(f"image_gz_sha256={aj.digest_path(candidate / 'Image.gz')}")
        print(f"image_gz_size={candidate.joinpath('Image.gz').stat().st_size}")
        print(f"system_map_sha256={aj.digest_path(candidate / 'System.map')}")
        print(f"package_dtb_sha256={aj.digest_path(candidate / GEMINI_DTB)}")
        print(f"compiled_gate_audit_sha256={aj.digest_bytes(audit)}")
        print("embedded_config=byte-exact-kernel.config")
        print("plaintext_cmdline=exact-maxcpus-9")
        print("compiled_gate_semantics=fail-closed-no-hardware-transition")
        print("dtbs=byte-exact-candidate-ai")
        print("active_cpu_request=logical-cpu8-rejection-only")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
