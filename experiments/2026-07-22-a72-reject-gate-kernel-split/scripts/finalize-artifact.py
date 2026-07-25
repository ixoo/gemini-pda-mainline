#!/usr/bin/env python3
"""Finalize or verify Candidate AI's flat, deterministic artifact tree."""

from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import stat
import sys

sys.dont_write_bytecode = True


BOOT_MEMBER = "gemini-a72-reject-gate-kernel-split.boot.img"
DTB_MEMBER = "mt6797-gemini-pda-a72-reject-gate-kernel-split.dtb"
INITRAMFS_MEMBER = "gemini-a72-reject-gate-kernel-split-initramfs.img"
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
    BOOT_MEMBER,
    INITRAMFS_MEMBER,
    "gemini-us.bkeymap",
    "input-event-capture",
    "kernel.config",
    "lineage-validation.txt",
    DTB_MEMBER,
    AUDIT_MEMBER,
    "package-validation.txt",
    "provenance.txt",
    "serializer.txt",
    "series-validation.txt",
    "source-build.json",
}
PRE_MANIFEST_MEMBERS = EXPECTED_MEMBERS - {MANIFEST_MEMBER}


def digest(path: pathlib.Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve_tree(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{label} is not a safe directory")
    return path.resolve(strict=True)


def flat_inventory(root: pathlib.Path) -> dict[str, pathlib.Path]:
    members: dict[str, pathlib.Path] = {}
    for path in root.iterdir():
        info = path.lstat()
        if path.is_symlink() or not stat.S_ISREG(info.st_mode):
            raise ValueError(f"artifact member is not a regular file: {path.name}")
        members[path.name] = path
    return members


def expected_mode(member: str) -> int:
    return 0o755 if member in EXECUTABLE_MEMBERS else 0o600


def manifest_bytes(members: dict[str, pathlib.Path]) -> bytes:
    return "".join(
        f"{digest(members[name])}  ./{name}\n"
        for name in sorted(PRE_MANIFEST_MEMBERS)
    ).encode("ascii")


def parse_manifest(
    path: pathlib.Path, members: dict[str, pathlib.Path]
) -> dict[str, str]:
    seen: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  \./([^/]+)", line)
        if match is None:
            raise ValueError("Candidate AI manifest is malformed")
        checksum, member = match.groups()
        if (
            member in seen
            or member == MANIFEST_MEMBER
            or member not in PRE_MANIFEST_MEMBERS
        ):
            raise ValueError("Candidate AI manifest path is unsafe or duplicated")
        if digest(members[member]) != checksum:
            raise ValueError(f"Candidate AI manifest checksum mismatch: {member}")
        seen[member] = checksum
    if set(seen) != PRE_MANIFEST_MEMBERS:
        raise ValueError("Candidate AI manifest is not the exact pre-manifest inventory")
    return seen


def verify(root: pathlib.Path) -> dict[str, pathlib.Path]:
    members = flat_inventory(root)
    if set(members) != EXPECTED_MEMBERS:
        missing = sorted(EXPECTED_MEMBERS - set(members))
        extra = sorted(set(members) - EXPECTED_MEMBERS)
        raise ValueError(
            f"Candidate AI final inventory changed: missing={missing}, extra={extra}"
        )
    for member, path in members.items():
        mode = stat.S_IMODE(path.lstat().st_mode)
        if mode != expected_mode(member):
            raise ValueError(f"Candidate AI artifact mode changed: {member}")
    parse_manifest(members[MANIFEST_MEMBER], members)
    return members


def finalize(root: pathlib.Path) -> dict[str, pathlib.Path]:
    members = flat_inventory(root)
    if set(members) != PRE_MANIFEST_MEMBERS:
        missing = sorted(PRE_MANIFEST_MEMBERS - set(members))
        extra = sorted(set(members) - PRE_MANIFEST_MEMBERS)
        raise ValueError(
            f"Candidate AI pre-manifest inventory changed: missing={missing}, extra={extra}"
        )

    manifest = root / MANIFEST_MEMBER
    descriptor = os.open(
        manifest,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        data = manifest_bytes(members)
        with os.fdopen(descriptor, "wb", closefd=True) as output:
            descriptor = -1
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    for member in EXPECTED_MEMBERS:
        os.chmod(root / member, expected_mode(member), follow_symlinks=False)
    return verify(root)


def resolve_new_output(path: pathlib.Path) -> pathlib.Path:
    if path.name in ("", ".", ".."):
        raise ValueError("Candidate AI output name is unsafe")
    parent_info = path.parent.lstat()
    if path.parent.is_symlink() or not stat.S_ISDIR(parent_info.st_mode):
        raise ValueError("Candidate AI output parent is unsafe")
    parent = path.parent.resolve(strict=True)
    output = parent / path.name
    if output.exists() or output.is_symlink():
        raise ValueError(f"refusing to overwrite {output}")
    return output


def publish(root: pathlib.Path, output_argument: pathlib.Path) -> dict[str, pathlib.Path]:
    """Publish an already-finalized tree and roll it back on verification failure."""

    verify(root)
    output = resolve_new_output(output_argument)
    if root.stat().st_dev != output.parent.stat().st_dev:
        raise ValueError("Candidate AI publication must stay on one filesystem")

    reserved = False
    moved = False
    try:
        os.mkdir(output, 0o700)
        reserved = True
        os.replace(root, output)
        reserved = False
        moved = True
        if os.environ.get("CANDIDATE_AI_TEST_FAIL_AFTER_PUBLISH") == "1":
            raise ValueError("injected post-publication verification failure")
        members = verify(output)
    except Exception:
        if moved:
            try:
                os.replace(output, root)
            except OSError as rollback_error:
                raise RuntimeError(
                    "Candidate AI publication failed and canonical output rollback failed"
                ) from rollback_error
        elif reserved:
            try:
                os.rmdir(output)
            except OSError:
                pass
        raise
    return members


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stage", type=pathlib.Path)
    mode.add_argument("--verify", type=pathlib.Path)
    mode.add_argument("--publish", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    try:
        os.umask(0o077)
        if args.stage is not None:
            if args.output is not None:
                raise ValueError("--output is valid only with --publish")
            root = resolve_tree(args.stage, "staging tree")
            members = finalize(root)
            action = "finalized"
        elif args.verify is not None:
            if args.output is not None:
                raise ValueError("--output is valid only with --publish")
            root = resolve_tree(args.verify, "artifact tree")
            members = verify(root)
            action = "verified"
        else:
            if args.output is None:
                raise ValueError("--publish requires --output")
            root = resolve_tree(args.publish, "staging tree")
            members = publish(root, args.output)
            action = "published-and-verified"
        print("validation=candidate-ai-artifact-finalization")
        print(f"action={action}")
        print(f"members={len(members)}")
        print(f"manifest_entries={len(PRE_MANIFEST_MEMBERS)}")
        print("device_access=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
