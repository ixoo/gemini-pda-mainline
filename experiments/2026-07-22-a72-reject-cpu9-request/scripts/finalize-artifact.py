#!/usr/bin/env python3
"""Finalize or verify Candidate AK's flat deterministic artifact tree."""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

sys.dont_write_bytecode = True

import candidate_ak as ak

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
    ak.BOOT_MEMBER,
    ak.INITRAMFS_MEMBER,
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "lineage-validation.txt",
    ak.DTB_MEMBER,
    AUDIT_MEMBER,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "series-validation.txt",
    "source-build.json",
}
PRE_MANIFEST_MEMBERS = EXPECTED_MEMBERS - {MANIFEST_MEMBER}


def foundation() -> object:
    aj_finalizer = ak.load_aj_module(
        "finalize-artifact.py", "candidate_ak_aj_finalizer"
    )
    # Ask AJ's source-pinned adapter for its generic AI finalizer only after
    # replacing the adapter's member-name contract. Calling AJ.verify() would
    # incorrectly re-apply AJ's binary pins to AK members.
    aj_finalizer.BOOT_MEMBER = ak.BOOT_MEMBER
    aj_finalizer.DTB_MEMBER = ak.DTB_MEMBER
    aj_finalizer.INITRAMFS_MEMBER = ak.INITRAMFS_MEMBER
    aj_finalizer.AUDIT_MEMBER = AUDIT_MEMBER
    aj_finalizer.MANIFEST_MEMBER = MANIFEST_MEMBER
    aj_finalizer.EXECUTABLE_MEMBERS = EXECUTABLE_MEMBERS
    aj_finalizer.EXPECTED_MEMBERS = EXPECTED_MEMBERS
    aj_finalizer.PRE_MANIFEST_MEMBERS = PRE_MANIFEST_MEMBERS
    return aj_finalizer.foundation()


def require_selected_members(members: dict[str, pathlib.Path]) -> None:
    ak.require_package_pins()
    image_gz = ak.read_regular(members["Image.gz"], "Candidate AK artifact Image.gz")
    if (
        len(image_gz) != int(ak.IMAGE_GZ_SIZE)
        or ak.digest_bytes(image_gz) != ak.IMAGE_GZ_SHA256
    ):
        raise ValueError("Candidate AK artifact Image.gz differs from package pins")
    if ak.digest_path(members["System.map"]) != ak.SYSTEM_MAP_SHA256:
        raise ValueError("Candidate AK artifact System.map differs from package pins")
    if ak.digest_path(members[AUDIT_MEMBER]) != ak.GATE_AUDIT_SHA256:
        raise ValueError("Candidate AK artifact compiled-gate audit differs from package pins")
    if ak.digest_path(members["kernel.config"]) != ak.CONFIG_SHA256:
        raise ValueError("Candidate AK artifact config differs from the static identity")
    if ak.digest_path(members[ak.DTB_MEMBER]) != ak.FINAL_DTB_SHA256:
        raise ValueError("Candidate AK artifact final DT differs from exact Candidate AJ")
    if ak.digest_path(members[ak.INITRAMFS_MEMBER]) != ak.INITRAMFS_SHA256:
        raise ValueError("Candidate AK artifact initramfs differs from exact Candidate AJ")


def verify(root: pathlib.Path) -> dict[str, pathlib.Path]:
    ak.require_package_pins()
    members = foundation().verify(root)
    require_selected_members(members)
    return members


def finalize(root: pathlib.Path) -> dict[str, pathlib.Path]:
    ak.require_package_pins()
    members = foundation().finalize(root)
    require_selected_members(members)
    return members


def publish(
    root: pathlib.Path, output: pathlib.Path
) -> dict[str, pathlib.Path]:
    ak.require_package_pins()
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
        ak.require_package_pins()
        if args.stage is not None:
            if args.output is not None:
                raise ValueError("--output is valid only with --publish")
            root = resolve_tree(args.stage, "Candidate AK staging tree")
            members = finalize(root)
            action = "finalized"
        elif args.verify is not None:
            if args.output is not None:
                raise ValueError("--output is valid only with --publish")
            root = resolve_tree(args.verify, "Candidate AK artifact tree")
            members = verify(root)
            action = "verified"
        else:
            if args.output is None:
                raise ValueError("--publish requires --output")
            root = resolve_tree(args.publish, "Candidate AK staging tree")
            members = publish(root, args.output)
            action = "published-and-verified"
        print("validation=candidate-ak-artifact-finalization")
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
