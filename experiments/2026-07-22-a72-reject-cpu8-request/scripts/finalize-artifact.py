#!/usr/bin/env python3
"""Finalize or verify Candidate AJ's flat deterministic artifact tree."""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

sys.dont_write_bytecode = True

import candidate_aj as aj

AUDIT_MEMBER = "mt6797-psci-cpu-boot-audit.txt"
MANIFEST_MEMBER = "SHA256SUMS"
EXECUTABLE_MEMBERS = {
    "console-keymap-verify",
    "console-unicode-mode",
    "input-event-capture",
}
EXPECTED_MEMBERS = {
    "Image.gz",
    MANIFEST_MEMBER,
    "System.map",
    "analysis.txt",
    "boot-validation.txt",
    "console-keymap-verify",
    "console-unicode-mode",
    aj.BOOT_MEMBER,
    aj.INITRAMFS_MEMBER,
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "lineage-validation.txt",
    aj.DTB_MEMBER,
    AUDIT_MEMBER,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "series-validation.txt",
    "source-build.json",
}
PRE_MANIFEST_MEMBERS = EXPECTED_MEMBERS - {MANIFEST_MEMBER}


def foundation() -> object:
    module = aj.load_ai_module("finalize-artifact.py", "candidate_aj_ai_finalizer")
    module.BOOT_MEMBER = aj.BOOT_MEMBER
    module.DTB_MEMBER = aj.DTB_MEMBER
    module.INITRAMFS_MEMBER = aj.INITRAMFS_MEMBER
    module.AUDIT_MEMBER = AUDIT_MEMBER
    module.MANIFEST_MEMBER = MANIFEST_MEMBER
    module.EXECUTABLE_MEMBERS = EXECUTABLE_MEMBERS
    module.EXPECTED_MEMBERS = EXPECTED_MEMBERS
    module.PRE_MANIFEST_MEMBERS = PRE_MANIFEST_MEMBERS
    return module


def require_selected_members(members: dict[str, pathlib.Path]) -> None:
    aj.require_package_pins()
    image_gz = aj.read_regular(members["Image.gz"], "Candidate AJ artifact Image.gz")
    if (
        len(image_gz) != int(aj.IMAGE_GZ_SIZE)
        or aj.digest_bytes(image_gz) != aj.IMAGE_GZ_SHA256
    ):
        raise ValueError("Candidate AJ artifact Image.gz differs from package pins")
    if aj.digest_path(members["System.map"]) != aj.SYSTEM_MAP_SHA256:
        raise ValueError("Candidate AJ artifact System.map differs from package pins")
    if aj.digest_path(members[AUDIT_MEMBER]) != aj.GATE_AUDIT_SHA256:
        raise ValueError("Candidate AJ artifact compiled-gate audit differs from package pins")
    if aj.digest_path(members["kernel.config"]) != aj.CONFIG_SHA256:
        raise ValueError("Candidate AJ artifact config differs from the static identity")
    if aj.digest_path(members[aj.DTB_MEMBER]) != aj.FINAL_DTB_SHA256:
        raise ValueError("Candidate AJ artifact final DT differs from exact Candidate AI")
    if aj.digest_path(members[aj.INITRAMFS_MEMBER]) != aj.INITRAMFS_SHA256:
        raise ValueError("Candidate AJ artifact initramfs differs from exact Candidate AI")


def verify(root: pathlib.Path) -> dict[str, pathlib.Path]:
    aj.require_package_pins()
    members = foundation().verify(root)
    require_selected_members(members)
    return members


def finalize(root: pathlib.Path) -> dict[str, pathlib.Path]:
    aj.require_package_pins()
    members = foundation().finalize(root)
    require_selected_members(members)
    return members


def publish(
    root: pathlib.Path, output: pathlib.Path
) -> dict[str, pathlib.Path]:
    aj.require_package_pins()
    require_selected_members(foundation().verify(root))
    members = foundation().publish(root, output)
    require_selected_members(members)
    return members


def resolve_tree(path: pathlib.Path, label: str) -> pathlib.Path:
    return foundation().resolve_tree(path, label)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage", type=pathlib.Path)
    mode.add_argument("--verify", type=pathlib.Path)
    mode.add_argument("--publish", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        # Refuse before resolving or reading an artifact tree until the two
        # bootstrap package builds have selected exact binary identities.
        aj.require_package_pins()
        if args.stage is not None:
            if args.output is not None:
                raise ValueError("--output is valid only with --publish")
            root = resolve_tree(args.stage, "Candidate AJ staging tree")
            members = finalize(root)
            action = "finalized"
        elif args.verify is not None:
            if args.output is not None:
                raise ValueError("--output is valid only with --publish")
            root = resolve_tree(args.verify, "Candidate AJ artifact tree")
            members = verify(root)
            action = "verified"
        else:
            if args.output is None:
                raise ValueError("--publish requires --output")
            root = resolve_tree(args.publish, "Candidate AJ staging tree")
            members = publish(root, args.output)
            action = "published-and-verified"
        print("validation=candidate-aj-artifact-finalization")
        print(f"action={action}")
        print(f"members={len(members)}")
        print(f"manifest_entries={len(PRE_MANIFEST_MEMBERS)}")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
