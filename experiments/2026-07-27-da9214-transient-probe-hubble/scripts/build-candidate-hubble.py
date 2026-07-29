#!/usr/bin/env python3
"""Publish Candidate Hubble as an exact complete Cassini artifact clone."""

from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import stat
import sys
import tempfile
from types import ModuleType

sys.dont_write_bytecode = True
import candidate_hubble as ch


def load_validator(path: pathlib.Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("hubble_artifact_validator", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Hubble artifact validator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def safe_output_root(path: pathlib.Path, source: pathlib.Path) -> pathlib.Path:
    candidate = path.absolute()
    info = candidate.lstat()
    if candidate.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError("output root is missing or unsafe")
    root = candidate.resolve(strict=True)
    if root == source or root in source.parents or source in root.parents:
        raise ValueError("output root and immutable Cassini source overlap")
    target = root / ch.ARTIFACT_DIR
    if target.exists() or target.is_symlink():
        raise ValueError("Hubble artifact output already exists")
    return root


def publish_clone(
    source: pathlib.Path,
    output_root: pathlib.Path,
    files: dict[str, pathlib.Path],
) -> pathlib.Path:
    with tempfile.TemporaryDirectory(
        prefix=".hubble-cassini.", dir=output_root
    ) as raw:
        staging = pathlib.Path(raw)
        os.chmod(staging, 0o700)
        for name in sorted(files):
            source_path = source / name
            data = source_path.read_bytes()
            mode = stat.S_IMODE(source_path.lstat().st_mode)
            destination = staging / name
            descriptor = os.open(
                destination,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                mode,
            )
            with os.fdopen(descriptor, "wb") as stream:
                os.fchmod(stream.fileno(), mode)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        os.rename(staging, output_root / ch.ARTIFACT_DIR)
    return output_root / ch.ARTIFACT_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cassini-artifact", required=True, type=pathlib.Path)
    parser.add_argument("--output-root", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        scripts = pathlib.Path(__file__).resolve().parent
        validator = load_validator(scripts / "validate-hubble-artifact.py")
        source_input = args.cassini_artifact.absolute()
        files = validator.validate(source_input, ch.CASSINI_ARTIFACT_DIR)
        source = source_input.resolve(strict=True)
        output_root = safe_output_root(args.output_root, source)
        output = publish_clone(source, output_root, files)
        output_files = validator.validate(output, ch.ARTIFACT_DIR)
        for name in files:
            if (
                files[name].read_bytes() != output_files[name].read_bytes()
                or stat.S_IMODE(files[name].lstat().st_mode)
                != stat.S_IMODE(output_files[name].lstat().st_mode)
            ):
                raise ValueError(f"published Hubble member changed: {name}")
        print("validation=hubble-complete-cassini-clone")
        print(f"source={source}")
        print(f"output={output}")
        print(f"complete_member_count={len(output_files)}")
        print("complete_member_bytes=exact-cassini")
        print("complete_member_modes=exact-cassini")
        print("boot_image_transform=none")
        print(f"raw_sha256={ch.CASSINI_RAW_SHA256}")
        print(f"padded_sha256={ch.CASSINI_PADDED_SHA256}")
        print("hardware_access=none")
        print("device_write=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
