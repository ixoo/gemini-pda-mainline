#!/usr/bin/env python3
"""Validate one exact, fully pinned Candidate AJ artifact without modifying it."""

from __future__ import annotations

import argparse
import importlib.util
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True

import candidate_aj as aj


MANIFEST_MEMBER = "SHA256SUMS"
PADDED_SIZE = 16 * 1024 * 1024


def load_finalizer() -> ModuleType:
    """Load AJ's finalizer without introducing a reciprocal source hash."""

    path = pathlib.Path(__file__).resolve().with_name("finalize-artifact.py")
    aj.read_regular(path, "Candidate AJ artifact finalizer")
    spec = importlib.util.spec_from_file_location(
        "candidate_aj_pinned_artifact_finalizer", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Candidate AJ artifact finalizer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for attribute in (
        "verify",
        "EXPECTED_MEMBERS",
        "PRE_MANIFEST_MEMBERS",
        "MANIFEST_MEMBER",
    ):
        if not hasattr(module, attribute):
            raise ValueError(f"Candidate AJ finalizer lacks {attribute}")
    return module


def validate_selected_tree(
    root: pathlib.Path, finalizer: ModuleType
) -> dict[str, pathlib.Path]:
    expected_name = f"candidate-AJ-a72-reject-cpu8-{aj.RAW_SHA256[:8]}"
    if root.name != expected_name:
        raise ValueError("Candidate AJ artifact directory name disagrees with raw hash")

    members = finalizer.verify(root)
    expected_members = set(finalizer.EXPECTED_MEMBERS)
    if (
        len(expected_members) != 20
        or len(members) != 20
        or set(members) != expected_members
        or finalizer.MANIFEST_MEMBER != MANIFEST_MEMBER
        or len(finalizer.PRE_MANIFEST_MEMBERS) != 19
    ):
        raise ValueError("Candidate AJ finalizer did not return the exact 20-member tree")

    manifest = members[MANIFEST_MEMBER]
    if aj.digest_path(manifest) != aj.ARTIFACT_MANIFEST_SHA256:
        raise ValueError("Candidate AJ artifact manifest differs from the selected pin")

    boot = members[aj.BOOT_MEMBER]
    boot_info = boot.lstat()
    if boot.is_symlink() or not stat.S_ISREG(boot_info.st_mode):
        raise ValueError("Candidate AJ raw boot member is unsafe")
    if boot_info.st_size != int(aj.RAW_SIZE):
        raise ValueError("Candidate AJ raw boot size differs from the selected pin")
    if aj.digest_path(boot) != aj.RAW_SHA256:
        raise ValueError("Candidate AJ raw boot SHA-256 differs from the selected pin")
    return members


def validate_candidate(path: pathlib.Path) -> dict[str, pathlib.Path]:
    """Fail on unresolved pins before any caller-supplied path operation."""

    aj.require_artifact_pins()
    finalizer = load_finalizer()
    root = aj.resolve_directory(path, "Candidate AJ artifact")
    return validate_selected_tree(root, finalizer)


def emit_report(root: pathlib.Path, members: dict[str, pathlib.Path]) -> None:
    print("validation=candidate-aj-artifact-pins")
    print(f"artifact={root.name}")
    print(f"members={len(members)}")
    print(f"manifest_entries={len(members) - 1}")
    print(f"raw_member={aj.BOOT_MEMBER}")
    print(f"raw_sha256={aj.RAW_SHA256}")
    print(f"raw_size={aj.RAW_SIZE}")
    print(f"artifact_manifest_sha256={aj.ARTIFACT_MANIFEST_SHA256}")
    print(f"padded_size={PADDED_SIZE}")
    print(f"padded_sha256={aj.PADDED_SHA256}")
    print("padded_artifact_construction=not-performed")
    print("artifact_write=none")
    print("device_access=none")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        # argparse constructs a Path value but performs no filesystem access.
        # validate_candidate closes every pin before resolving or reading it.
        members = validate_candidate(args.artifact)
        root = args.artifact.resolve(strict=True)
        emit_report(root, members)
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
