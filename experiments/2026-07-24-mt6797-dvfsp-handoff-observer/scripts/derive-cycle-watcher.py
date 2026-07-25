#!/usr/bin/env python3
"""Derive AN's exact-MAC one-shot watcher from exact Candidate AH."""

from __future__ import annotations

import argparse
import os
import pathlib
import shlex
import stat
import sys


sys.dont_write_bytecode = True

import candidate_an as an


AH_WATCHER_REL = (
    "experiments/2026-07-22-ad-contract-af-kernel-split/scripts/collect-cycle.sh"
)
AH_WATCHER_SHA256 = (
    "b5664f6d883207af9bcb80c6d731dfc8d568e62d203daa38afc9163ba33ca12a"
)
HOST_MAC = "42:00:15:19:82:00"
MAX_WAIT_SECONDS = 900

AH_LOCATION = '''script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(cd -- "$script_dir/../../.." && pwd -P)"
collector="$script_dir/collect-runtime.sh"
readonly script_dir repo_root collector'''
AH_WAIT_CHECK = (
    '[[ "$wait_seconds" =~ ^[1-9][0-9]*$ ]] || '
    "die '--wait-seconds must be positive'"
)
AN_WAIT_CHECK = (
    f'[[ "$wait_seconds" =~ ^[1-9][0-9]*$ && '
    f'"$wait_seconds" -le {MAX_WAIT_SECONDS} ]] || \\\n'
    f"\tdie '--wait-seconds must be in 1..{MAX_WAIT_SECONDS}'"
)


def digest_bytes(data: bytes) -> str:
    return __import__("hashlib").sha256(data).hexdigest()


def replace_exact(text: str, old: str, new: str, count: int) -> str:
    actual = text.count(old)
    if actual != count:
        raise ValueError(
            f"AH watcher token count changed for {old!r}: "
            f"expected {count}, found {actual}"
        )
    return text.replace(old, new)


def validate_directory(path: pathlib.Path, label: str) -> pathlib.Path:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISDIR(info.st_mode):
        raise ValueError(f"{label} is unsafe")
    return path.resolve(strict=True)


def validate_collector(path: pathlib.Path) -> pathlib.Path:
    an.read_regular(path, "Candidate AN runtime collector")
    info = path.lstat()
    if path.is_symlink() or not info.st_mode & stat.S_IXUSR:
        raise ValueError("Candidate AN runtime collector is not executable")
    return path.resolve(strict=True)


def load_foundation(path: pathlib.Path) -> str:
    source = an.read_regular(path, "exact Candidate AH cycle watcher")
    if digest_bytes(source) != AH_WATCHER_SHA256:
        raise ValueError("source-pinned Candidate AH cycle watcher changed")
    return source.decode("utf-8", errors="strict")


def location_replacement(
    repository: pathlib.Path, collector: pathlib.Path
) -> str:
    return (
        f"repo_root={shlex.quote(os.fspath(repository))}\n"
        f"collector={shlex.quote(os.fspath(collector))}\n"
        "readonly repo_root collector"
    )


def watcher_replacements(
    repository: pathlib.Path, collector: pathlib.Path
) -> tuple[tuple[str, str, int], ...]:
    return (
        (
            "readonly EXPECTED_INSTALLED_FULL_SHA256="
            "f107a3e7483c02cb4b2540d185ef2a5fb1f77e4a0acc7b66fce16e37641f5012",
            f"readonly EXPECTED_INSTALLED_FULL_SHA256={an.PADDED_SHA256}",
            1,
        ),
        ("Candidate AH", "Candidate AN", 2),
        (
            "2026-07-22-ad-contract-af-kernel-split",
            an.EXPERIMENT,
            1,
        ),
        ("candidate_label=AH", "candidate_label=AN", 1),
        (
            "exact-ah-runtime-validator-passed",
            "exact-an-runtime-validator-passed",
            1,
        ),
        (AH_WAIT_CHECK, AN_WAIT_CHECK, 1),
        # Keep the absolute AN paths last so reverse validation removes them
        # before restoring experiment-name tokens embedded in those paths.
        (AH_LOCATION, location_replacement(repository, collector), 1),
    )


def validate_derived(
    text: str, repository: pathlib.Path, collector: pathlib.Path
) -> None:
    required = (
        f"readonly HOST_MAC={HOST_MAC}",
        f"readonly EXPECTED_INSTALLED_FULL_SHA256={an.PADDED_SHA256}",
        location_replacement(repository, collector),
        f"experiment={an.EXPERIMENT}",
        "candidate_label=AN",
        "phase='waiting-for-exact-mac'",
        "more than one interface has the exact Gemini USB MAC",
        "exact Gemini interface identity changed before collection",
        AN_WAIT_CHECK,
        'ping -b "$interface" -S "$HOST_ADDRESS" -c 1 -W 1000',
        '"$collector" --interface "$interface" --output "$capture"',
        "collector_invocations=1",
        "installed_full_hash_reverified_during_collection=no",
        "device_explicit_write_operations=none",
    )
    for token in required:
        if token not in text:
            raise ValueError(f"derived Candidate AN watcher lost contract: {token!r}")
    if (
        text.count('"$collector" --interface "$interface" --output "$capture"') != 1
        or text.count("collector_invocations=1\n") != 1
    ):
        raise ValueError("derived Candidate AN watcher is not one-shot")
    forbidden = (
        "Candidate AH",
        "candidate_label=AH",
        "exact-ah-runtime-validator-passed",
        AH_WAIT_CHECK,
    )
    if any(token in text for token in forbidden):
        raise ValueError("derived Candidate AN watcher retains Candidate AH policy")


def derive(
    source: str,
    repository: pathlib.Path,
    collector: pathlib.Path,
) -> str:
    an.require_artifact_pins()
    repository = validate_directory(repository, "repository")
    collector = validate_collector(collector)

    replacements = watcher_replacements(repository, collector)
    text = source
    for old, new, count in replacements:
        text = replace_exact(text, old, new, count)

    restored = text
    for old, new, count in reversed(replacements):
        restored = replace_exact(restored, new, old, count)
    if restored != source:
        raise ValueError("Candidate AN watcher cannot restore exact AH foundation")
    validate_derived(text, repository, collector)
    return text


def validate_output(path: pathlib.Path) -> pathlib.Path:
    if not path.name or path.name in {".", ".."} or path.exists() or path.is_symlink():
        raise ValueError("Candidate AN watcher output is invalid or already exists")
    parent = validate_directory(path.parent, "Candidate AN watcher output parent")
    return parent / path.name


def publish(path: pathlib.Path, text: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o700)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        os.fchmod(stream.fileno(), 0o700)
        stream.write(text)


def repository_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[3]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=pathlib.Path)
    parser.add_argument("--repository", required=True, type=pathlib.Path)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    args = parser.parse_args()
    previous_umask = os.umask(0o077)
    try:
        repository = validate_directory(args.repository, "repository")
        expected_repository = repository_root()
        if repository != expected_repository:
            raise ValueError("Candidate AN watcher repository is not exact")
        expected_source = repository / AH_WATCHER_REL
        if args.source.resolve(strict=True) != expected_source:
            raise ValueError("Candidate AN watcher foundation path is not exact")
        collector = pathlib.Path(__file__).resolve().with_name("collect-runtime.sh")
        source = load_foundation(expected_source)
        output = validate_output(args.output)
        text = derive(source, repository, collector)
        publish(output, text)
        print("validation=candidate-an-cycle-watcher-derived")
        print(f"output={output}")
        print(f"foundation_sha256={AH_WATCHER_SHA256}")
        print(f"installed_full_sha256={an.PADDED_SHA256}")
        print(f"collector={collector}")
        print(f"host_mac={HOST_MAC}")
        print(f"max_wait_seconds={MAX_WAIT_SECONDS}")
        print("collector_invocations=at-most-one")
        print("device_partition_access=none")
        print("reboot_or_slot_selection=none")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    finally:
        os.umask(previous_umask)


if __name__ == "__main__":
    raise SystemExit(main())
