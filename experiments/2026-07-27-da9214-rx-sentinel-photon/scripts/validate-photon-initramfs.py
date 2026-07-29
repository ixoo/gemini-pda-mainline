#!/usr/bin/env python3
"""Require exact Cassini initramfs with only bin/cassini-probe bytes changed."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import pathlib
import stat
import sys
from types import ModuleType

sys.dont_write_bytecode = True
import candidate_photon as cp


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def regular(path: pathlib.Path, label: str) -> bytes:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValueError(f"{label} is missing, empty, or unsafe")
    return path.read_bytes()


def load_module(path: pathlib.Path, name: str) -> ModuleType:
    regular(path, name)
    module_directory = str(path.parent)
    sys.path.insert(0, module_directory)
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if sys.path[0] == module_directory:
            del sys.path[0]


def cassini_archive_validator() -> ModuleType:
    root = pathlib.Path(__file__).resolve().parents[3]
    path = (
        root
        / "experiments/2026-07-27-da9214-direct-address-cassini/"
        "scripts/validate-cassini-initramfs.py"
    )
    if cp.digest_path(path) != cp.CASSINI_INITRAMFS_VALIDATOR_SHA256:
        raise ValueError("source-pinned Cassini initramfs parser changed")
    return load_module(path, "photon_cassini_archive_validator")


def photon_probe_validator() -> ModuleType:
    path = pathlib.Path(__file__).resolve().parent / "validate-photon-probe.py"
    return load_module(path, "photon_probe_validator")


def validate(
    baseline_path: pathlib.Path,
    candidate_path: pathlib.Path,
    source_path: pathlib.Path,
    helper_path: pathlib.Path,
) -> bytes:
    archive = cassini_archive_validator()
    baseline_data = regular(baseline_path, "exact Cassini initramfs")
    candidate_data = regular(candidate_path, "Photon initramfs")
    if digest(baseline_data) != cp.CASSINI_INITRAMFS_SHA256:
        raise ValueError("baseline is not exact Candidate Cassini initramfs")
    if cp.HEX256.fullmatch(cp.INITRAMFS_SHA256) is not None:
        if digest(candidate_data) != cp.INITRAMFS_SHA256:
            raise ValueError("calibrated Photon initramfs changed")
    baseline = archive.parse_newc(baseline_data)
    candidate = archive.parse_newc(candidate_data)
    if set(candidate) != set(baseline):
        raise ValueError("Photon initramfs inventory differs from Cassini")
    if cp.EMBEDDED_PROBE_MEMBER not in baseline:
        raise ValueError("Cassini initramfs lacks its fixed helper member")

    for name, member in baseline.items():
        actual = candidate[name]
        if name == cp.EMBEDDED_PROBE_MEMBER:
            if (
                member.mode != actual.mode
                or member.uid != actual.uid
                or member.gid != actual.gid
                or member.nlink != actual.nlink
                or member.mtime != actual.mtime
                or member.devmajor != actual.devmajor
                or member.devminor != actual.devminor
                or member.rdevmajor != actual.rdevmajor
                or member.rdevminor != actual.rdevminor
            ):
                raise ValueError("embedded helper metadata differs from Cassini")
            if (
                not stat.S_ISREG(actual.mode)
                or stat.S_IMODE(actual.mode) != 0o755
                or actual.data == member.data
            ):
                raise ValueError("embedded helper is absent or unchanged")
            if actual.data != regular(helper_path, "built Photon helper"):
                raise ValueError("embedded helper differs from validated binary")
            continue
        if not archive.inherited_member_equal(member, actual):
            fields = archive.member_delta(member, actual)
            raise ValueError(
                f"inherited Cassini initramfs member changed: {name} "
                f"fields={fields}"
            )

    probe = photon_probe_validator()
    probe.validate_source(source_path)
    probe.validate_binary(helper_path)

    for name, member in baseline.items():
        if (
            name != cp.EMBEDDED_PROBE_MEMBER
            and stat.S_ISREG(member.mode)
            and b"photon" in member.data.lower()
        ):
            raise ValueError(f"inherited member unexpectedly invokes Photon: {name}")
    return candidate_data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=pathlib.Path)
    parser.add_argument("--candidate", required=True, type=pathlib.Path)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--helper", required=True, type=pathlib.Path)
    args = parser.parse_args()
    try:
        data = validate(
            args.baseline, args.candidate, args.source, args.helper
        )
    except (
        OSError,
        RuntimeError,
        UnicodeError,
        ValueError,
        gzip.BadGzipFile,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print("validation=photon-exact-cassini-one-member-byte-delta")
    print(f"candidate_sha256={digest(data)}")
    print(f"baseline_sha256={cp.CASSINI_INITRAMFS_SHA256}")
    print(f"probe_source_sha256={cp.PROBE_SOURCE_SHA256}")
    print(f"probe_binary_sha256={cp.digest_path(args.helper)}")
    print("archive_inventory=byte-exact-cassini")
    print("sole_changed_member=bin/cassini-probe-data")
    print("changed_member_metadata=none")
    print("automatic_invocation=none")
    print("manual_post_usb_invocation=/bin/cassini-probe")
    print("kernel_dtb_config_change=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
