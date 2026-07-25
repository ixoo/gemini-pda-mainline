#!/usr/bin/env python3
"""Derive AL's exact-MAC one-shot watcher from Candidate AH's watcher."""

from __future__ import annotations

import argparse
import os
import pathlib
import shlex
import stat
import sys

sys.dont_write_bytecode = True

import candidate_al as al


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"AH cycle collector token count changed: expected {count}, found {actual}"
        )
    return text.replace(old, new)


def derive(source: str, repo_root: pathlib.Path, collector: pathlib.Path) -> str:
    al.require_artifact_pins()
    text = replace_exact(
        source,
        "readonly EXPECTED_INSTALLED_FULL_SHA256=" + al.AH_PADDED_SHA256,
        "readonly EXPECTED_INSTALLED_FULL_SHA256=" + al.PADDED_SHA256,
        1,
    )
    location = '''script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
collector="$script_dir/collect-runtime.sh"
readonly script_dir repo_root collector'''
    replacement = (
        f"repo_root={shlex.quote(os.fspath(repo_root))}\n"
        f"collector={shlex.quote(os.fspath(collector))}\n"
        "readonly repo_root collector"
    )
    text = replace_exact(text, location, replacement, 1)
    text = text.replace("Candidate AH", "Candidate AL")
    text = text.replace("candidate-ah", "candidate-al")
    text = replace_exact(
        text,
        "2026-07-22-ad-contract-af-kernel-split",
        al.EXPERIMENT,
        1,
    )
    text = replace_exact(text, "candidate_label=AH", "candidate_label=AL", 1)
    text = text.replace("exact-ah-runtime-validator-passed", "exact-al-runtime-validator-passed")
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--collector", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        source = al.read_regular(args.source, "exact Candidate AH cycle collector")
        if al.digest_path(args.source) != al.AH_CYCLE_COLLECTOR_SHA256:
            raise ValueError("source-pinned Candidate AH cycle collector changed")
        repository = args.repository.resolve(strict=True)
        collector = args.collector.resolve(strict=True)
        if not stat.S_ISDIR(repository.lstat().st_mode) or repository.is_symlink():
            raise ValueError("repository root is unsafe")
        al.read_regular(collector, "Candidate AL runtime collector")
        if args.output.exists() or args.output.is_symlink():
            raise ValueError("refusing to overwrite derived cycle collector")
        parent = args.output.parent.resolve(strict=True)
        if args.output.parent.is_symlink() or not stat.S_ISDIR(
            args.output.parent.lstat().st_mode
        ):
            raise ValueError("derived cycle output parent is unsafe")
        output = parent / args.output.name
        text = derive(
            source.decode("utf-8", errors="strict"),
            repository,
            collector,
        )
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), 0o700)
            stream.write(text)
        print("validation=candidate-al-cycle-collector-derived")
        print(f"output={output}")
        print(f"foundation_sha256={al.AH_CYCLE_COLLECTOR_SHA256}")
        print("collector_invocations=at-most-one")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
