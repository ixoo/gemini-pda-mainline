#!/usr/bin/env python3
"""Validate Candidate AK's canonical Android-v0 image and exact components."""

from __future__ import annotations

import argparse
import pathlib
import struct
import sys

sys.dont_write_bytecode = True

import candidate_ak as ak


def validate_bytes(
    candidate: bytes,
    image_gz: bytes,
    dtb: bytes,
    initramfs: bytes,
    config: bytes,
    system_map: bytes,
    baselines: list[tuple[str, bytes, str]],
) -> dict[str, object]:
    ak.require_package_pins()
    aj = ak.load_aj_identity("candidate_ak_boot_aj_identity")
    ai_boot = aj.load_ai_module("validate-boot.py", "candidate_ak_ai_boot")
    ai_package = aj.load_ai_module("validate-package.py", "candidate_ak_boot_package")
    ai_boot.load_package_validator = lambda: ai_package

    parsed_baselines: list[tuple[bytes, dict[str, object]]] = []
    for label, data, expected_hash in baselines:
        if ak.digest_bytes(data) != expected_hash:
            raise ValueError(f"exact {label} boot identity changed")
        parsed = ai_boot.parse_boot(data, label)
        fields = parsed["fields"]
        if not isinstance(fields, tuple):
            raise TypeError(f"{label} Android fields have an invalid type")
        if parsed["header"] != ai_boot.canonical_header(
            fields, parsed["kernel"], parsed["ramdisk"]
        ):
            raise ValueError(f"{label} baseline header is not canonical")
        parsed_baselines.append((data, parsed))

    if ak.digest_bytes(dtb) != ak.FINAL_DTB_SHA256:
        raise ValueError("final DTB is not exact Candidate AJ/AH")
    if ak.digest_bytes(initramfs) != ak.INITRAMFS_SHA256:
        raise ValueError("initramfs is not exact Candidate AJ/AD")
    if ak.digest_bytes(config) != ak.CONFIG_SHA256:
        raise ValueError("resolved config is not exact Candidate AK")
    if ak.digest_bytes(system_map) != ak.SYSTEM_MAP_SHA256:
        raise ValueError("System.map is not the reproduced Candidate AK output")
    if (
        len(image_gz) != int(ak.IMAGE_GZ_SIZE)
        or ak.digest_bytes(image_gz) != ak.IMAGE_GZ_SHA256
    ):
        raise ValueError("Candidate AK Image.gz differs from the reproduced output")
    image = ai_package.decompress_lk_image_gz(image_gz, "Candidate AK Image.gz")
    if ak.digest_bytes(image) != ak.IMAGE_SHA256 or len(image) != int(ak.IMAGE_SIZE):
        raise ValueError("Candidate AK Image identity changed")
    ak.validate_kernel_policy(image, system_map, config, ai_package)

    result = ai_boot.validate_container(
        candidate, image_gz, dtb, initramfs, label="Candidate AK"
    )
    if any(candidate == baseline for baseline, _ in parsed_baselines):
        raise ValueError("Candidate AK is byte-identical to an earlier candidate")
    if ak.digest_bytes(candidate) == ak.AJ_RAW_SHA256:
        raise ValueError("Candidate AK reused Candidate AJ's Android image")

    reference_header = ai_boot.normalized_header(parsed_baselines[0][1]["header"])
    reference_fields = parsed_baselines[0][1]["fields"]
    if not isinstance(reference_fields, tuple):
        raise TypeError("baseline Android fields have an invalid type")
    for _, parsed in parsed_baselines[1:]:
        if ai_boot.normalized_header(parsed["header"]) != reference_header:
            raise ValueError("baseline normalized Android headers differ")
        fields = parsed["fields"]
        if not isinstance(fields, tuple) or fields[1:] != reference_fields[1:]:
            raise ValueError("baseline Android fields differ outside kernel_size")
    if ai_boot.normalized_header(result["header"]) != reference_header:
        raise ValueError("Candidate AK header changed outside kernel_size and ID")
    fields = result["fields"]
    if not isinstance(fields, tuple) or fields[1:] != reference_fields[1:]:
        raise ValueError("Candidate AK fields changed outside kernel_size")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--kernel-config", type=pathlib.Path, required=True)
    parser.add_argument("--system-map", type=pathlib.Path, required=True)
    parser.add_argument("--ad-boot", type=pathlib.Path, required=True)
    parser.add_argument("--ah-boot", type=pathlib.Path, required=True)
    parser.add_argument("--af-boot", type=pathlib.Path, required=True)
    parser.add_argument("--ai-boot", type=pathlib.Path, required=True)
    parser.add_argument("--aj-boot", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        # Artifact construction must not begin from a merely plausible fresh
        # package. Two independent package builds select these identities first.
        ak.require_package_pins()
        inputs = {
            name: ak.read_regular(path, label)
            for name, path, label in (
                ("candidate", args.candidate, "Candidate AK boot"),
                ("image_gz", args.image_gz, "Candidate AK Image.gz"),
                ("dtb", args.dtb, "exact Candidate AJ final DTB"),
                ("initramfs", args.initramfs, "exact Candidate AJ initramfs"),
                ("config", args.kernel_config, "Candidate AK config"),
                ("system_map", args.system_map, "Candidate AK System.map"),
            )
        }
        aj = ak.load_aj_identity("candidate_ak_boot_constants_aj")
        ai_boot = aj.load_ai_module("validate-boot.py", "candidate_ak_boot_constants")
        baselines = [
            (
                "Candidate AD",
                ak.read_regular(args.ad_boot, "exact Candidate AD boot"),
                ai_boot.AD_BOOT_SHA256,
            ),
            (
                "Candidate AH",
                ak.read_regular(args.ah_boot, "exact Candidate AH boot"),
                ai_boot.AH_BOOT_SHA256,
            ),
            (
                "Candidate AF",
                ak.read_regular(args.af_boot, "exact Candidate AF boot"),
                ai_boot.AF_BOOT_SHA256,
            ),
            (
                "Candidate AI",
                ak.read_regular(args.ai_boot, "exact Candidate AI boot"),
                aj.AI_RAW_SHA256,
            ),
            (
                "Candidate AJ",
                ak.read_regular(args.aj_boot, "exact Candidate AJ boot"),
                ak.AJ_RAW_SHA256,
            ),
        ]
        validate_bytes(
            inputs["candidate"],
            inputs["image_gz"],
            inputs["dtb"],
            inputs["initramfs"],
            inputs["config"],
            inputs["system_map"],
            baselines,
        )
        print("validation=candidate-ak-android-v0")
        print(f"candidate_sha256={ak.digest_bytes(inputs['candidate'])}")
        print(f"candidate_size={len(inputs['candidate'])}")
        print(f"image_gz_sha256={ak.IMAGE_GZ_SHA256}")
        print(f"image_sha256={ak.IMAGE_SHA256}")
        print(f"image_size={ak.IMAGE_SIZE}")
        print(f"system_map_sha256={ak.SYSTEM_MAP_SHA256}")
        print(f"config_sha256={ak.CONFIG_SHA256}")
        print(f"dtb_sha256={ak.FINAL_DTB_SHA256}")
        print(f"initramfs_sha256={ak.INITRAMFS_SHA256}")
        print("android_header_delta=kernel-size-and-payload-id-only")
        print("cpu_policy=maxcpus-10-cpu8-and-cpu9-rejection-request")
        print("raw_output_identity=pending-two-artifact-reproductions")
        print("device_access=none")
        return 0
    except (
        OSError,
        RuntimeError,
        TypeError,
        UnicodeError,
        ValueError,
        struct.error,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
