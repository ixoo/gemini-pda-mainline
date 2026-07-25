#!/usr/bin/env python3
"""Write deterministic Candidate AB artifact provenance."""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

from ab_contract import (
    AA_ARTIFACT_NAME,
    AA_BOOT_SHA256,
    AA_DTB_SHA256,
    AA_INITRAMFS_SHA256,
    AA_KEYMAP_SHA256,
    AA_KEYMAP_VERIFIER_SHA256,
    BOOT2_CAPACITY,
    CANDIDATE,
    CONFIG_INPUTS_SHA256,
    CONFIG_SHA256,
    EXPERIMENT,
    IMAGE_GZ_SHA256,
    IMAGE_SHA256,
    KERNEL_BUILD_SCRIPT_SHA256,
    KERNEL_MANIFEST_SHA256,
    MARKER,
    PACKAGE_DTB_SHA256,
    PACKAGE_NAME,
    PATCHSET_SHA256,
    PATCH_0087_SHA256,
    SERIES_SHA256,
    SOURCE_SHA256,
    SYSTEM_MAP_SHA256,
    digest_path,
    read_regular,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--repo-revision", required=True)
    parser.add_argument("--boot", type=pathlib.Path, required=True)
    parser.add_argument("--initramfs", type=pathlib.Path, required=True)
    parser.add_argument("--dtb", type=pathlib.Path, required=True)
    parser.add_argument("--image", type=pathlib.Path, required=True)
    parser.add_argument("--image-gz", type=pathlib.Path, required=True)
    parser.add_argument("--system-map", type=pathlib.Path, required=True)
    parser.add_argument("--source-build", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite Candidate AB provenance")
        if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", args.repo_revision) is None:
            raise ValueError("repository revision is not a full object ID")
        for path, label in (
            (args.boot, "AB boot"),
            (args.initramfs, "AB initramfs"),
            (args.dtb, "AB DTB"),
            (args.image, "AB Image"),
            (args.image_gz, "AB Image.gz"),
            (args.system_map, "AB System.map"),
            (args.source_build, "normalized build provenance"),
        ):
            read_regular(path, label)
        exact = (
            (args.dtb, AA_DTB_SHA256, "hardware-passed AA r1 DTB"),
            (args.image, IMAGE_SHA256, "AB Image"),
            (args.image_gz, IMAGE_GZ_SHA256, "AB Image.gz"),
            (args.system_map, SYSTEM_MAP_SHA256, "AB System.map"),
        )
        for path, expected, label in exact:
            if digest_path(path) != expected:
                raise ValueError(f"{label} identity changed")
        boot_size = args.boot.stat().st_size
        if not 0 < boot_size <= BOOT2_CAPACITY:
            raise ValueError("Candidate AB size is invalid or exceeds boot2")

        fields = (
            ("experiment", EXPERIMENT),
            ("candidate_label", CANDIDATE),
            ("marker", MARKER),
            ("repo_revision", args.repo_revision),
            ("aa_artifact", AA_ARTIFACT_NAME),
            ("aa_boot_sha256", AA_BOOT_SHA256),
            ("aa_initramfs_sha256", AA_INITRAMFS_SHA256),
            ("aa_dtb_sha256", AA_DTB_SHA256),
            ("aa_keymap_sha256", AA_KEYMAP_SHA256),
            ("aa_keymap_verifier_sha256", AA_KEYMAP_VERIFIER_SHA256),
            ("kernel_package", PACKAGE_NAME),
            ("source_sha256", SOURCE_SHA256),
            ("kernel_manifest_sha256", KERNEL_MANIFEST_SHA256),
            ("kernel_build_script_sha256", KERNEL_BUILD_SCRIPT_SHA256),
            ("patchset_sha256", PATCHSET_SHA256),
            ("series_sha256", SERIES_SHA256),
            ("patch_0087_sha256", PATCH_0087_SHA256),
            ("config_inputs_sha256", CONFIG_INPUTS_SHA256),
            ("config_sha256", CONFIG_SHA256),
            ("image_sha256", IMAGE_SHA256),
            ("image_gz_sha256", IMAGE_GZ_SHA256),
            ("system_map_sha256", SYSTEM_MAP_SHA256),
            ("package_dtb_sha256", PACKAGE_DTB_SHA256),
            ("source_build_normalized_sha256", digest_path(args.source_build)),
            ("candidate_dtb_sha256", AA_DTB_SHA256),
            ("dtb_lineage", "byte-exact-hardware-passed-aa-r1"),
            ("candidate_initramfs_sha256", digest_path(args.initramfs)),
            ("candidate_sha256", digest_path(args.boot)),
            ("candidate_size", str(boot_size)),
            ("boot2_capacity", str(BOOT2_CAPACITY)),
            (
                "initramfs_delta",
                "init,bin/local-shell,bin/reboot,bin/x-record",
            ),
            (
                "keymap_and_gate",
                "exact-aa-r1-with-attribution-only-shell-transform",
            ),
            ("reboot_dispatch", "ENV-alias-absolute-wrapper"),
            ("manual_reboot", "busybox-reboot-no-sync-force"),
            (
                "watchdog_userspace",
                "start-none,open-none,ping-none,countdown-none,fallback-none",
            ),
            ("automatic_reboot", "none"),
            ("kernel_restart_priority", "MT6797-255,other-MediaTek-128"),
            ("kernel_virtual_console", "none"),
            ("serial_console", "ttyS0,921600n8"),
            ("font", "TER16x32"),
            ("fbcon_rotation", "3"),
            (
                "deterministic_replica",
                "initramfs-and-android-v0-byte-identical",
            ),
            ("storage_access", "none"),
            ("runtime_networking", "none"),
            ("hardware_write", "none"),
            ("flash", "none"),
            ("runtime_result", "not-tested"),
        )
        encoded = "".join(f"{key}={value}\n" for key, value in fields).encode("utf-8")
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
        return 0
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
