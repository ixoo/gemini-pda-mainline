#!/usr/bin/env python3

"""Extract kernel-facing path, property, and ioctl-name strings from ELFs."""

from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys


PRINTABLE = re.compile(rb"[\x20-\x7e]{4,}")
KERNEL_PATH = re.compile(
    r"/(?:dev|sys|proc|d)/(?:[A-Za-z0-9_.:+%*-]+/)*[A-Za-z0-9_.:+%*-]+"
)
PROPERTY = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"(?:ro|persist|sys|ctl|vendor)\.[A-Za-z0-9_.-]{2,}"
)
IOCTL_NAME = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:[A-Z][A-Z0-9]*_)*(?:IOCTL|IOC)(?:_[A-Z0-9]+)+"
)

SEARCH_ROOTS = (
    "system/vendor/bin",
    "system/vendor/lib",
    "system/vendor/lib64",
    "system/bin",
    "usr/bin",
    "usr/sbin",
    "usr/lib",
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan extracted Gemini ELF files for kernel-facing strings."
    )
    parser.add_argument(
        "root",
        type=pathlib.Path,
        help="extraction root, normally ~/reverse-engineering/gemini-vendor",
    )
    parser.add_argument(
        "--kind",
        choices=("all", "path", "property", "ioctl"),
        default="all",
        help="limit emitted evidence type",
    )
    parser.add_argument(
        "--consumer-limit",
        type=int,
        default=12,
        help="maximum consumer paths shown per value",
    )
    return parser.parse_args()


def elf_files(root: pathlib.Path):
    for relative_root in SEARCH_ROOTS:
        candidate = root / relative_root
        if not candidate.is_dir():
            continue
        for path in sorted(candidate.rglob("*")):
            if not path.is_file():
                continue
            try:
                with path.open("rb") as stream:
                    if stream.read(4) == b"\x7fELF":
                        yield path
            except OSError:
                continue


def ascii_strings(path: pathlib.Path):
    try:
        data = path.read_bytes()
    except OSError:
        return
    for match in PRINTABLE.finditer(data):
        yield match.group().decode("ascii", errors="ignore")


def main() -> int:
    args = arguments()
    root = args.root.expanduser().resolve()
    if not root.is_dir():
        print(f"error: extraction root not found: {root}", file=sys.stderr)
        return 2

    evidence: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    patterns = (
        ("path", KERNEL_PATH),
        ("property", PROPERTY),
        ("ioctl", IOCTL_NAME),
    )

    for path in elf_files(root):
        consumer = path.relative_to(root).as_posix()
        for string in ascii_strings(path):
            for kind, pattern in patterns:
                if args.kind not in ("all", kind):
                    continue
                for value in pattern.findall(string):
                    evidence[(kind, value)].add(consumer)

    print("kind\tvalue\tconsumers")
    for (kind, value), consumers in sorted(evidence.items()):
        selected = sorted(consumers)
        if len(selected) > args.consumer_limit:
            hidden = len(selected) - args.consumer_limit
            selected = selected[: args.consumer_limit] + [f"...+{hidden}"]
        print(f"{kind}\t{value}\t{','.join(selected)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
