#!/usr/bin/env python3
"""Reject decision-changing mutations of the READY validator repair."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile

import source_edits
import validate_source


MUTATIONS = (
    (
        "restore-stale-required-bit",
        "\t    evidence->blocker_mask & ~allowed_blockers ||\n",
        "\t    !(evidence->blocker_mask &\n"
        "\t      ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS) ||\n"
        "\t    evidence->blocker_mask & ~allowed_blockers ||\n",
    ),
    (
        "allow-runtime-binding",
        "ARM64_LATE_CPU_BLOCK_CONFIGURATION |\n",
        "ARM64_LATE_CPU_BLOCK_RUNTIME_BINDING |\n"
        "\t\tARM64_LATE_CPU_BLOCK_CONFIGURATION |\n",
    ),
    (
        "allow-source-identity",
        "ARM64_LATE_CPU_BLOCK_CONFIGURATION |\n",
        "ARM64_LATE_CPU_BLOCK_SOURCE_IDENTITY |\n"
        "\t\tARM64_LATE_CPU_BLOCK_CONFIGURATION |\n",
    ),
    (
        "drop-topology-conditional",
        "\t\tARM64_LATE_CPU_BLOCK_TOPOLOGY;\n",
        "\t\t0;\n",
    ),
    (
        "alter-fixture-closure",
        "\t ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS |\t\t\t\\\n",
        "",
    ),
    (
        "add-cpu-action",
        "\tunsigned int target;\n",
        "\tunsigned int target;\n\tadd_cpu(8);\n",
    ),
)


def mutate(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise ValueError(f"mutation anchor count changed: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    rejected = 0
    with tempfile.TemporaryDirectory(prefix="a72-ready-plan-mutations-") as name:
        temporary = Path(name)
        for index, (label, old, new) in enumerate(MUTATIONS):
            root = temporary / str(index)
            target = root / source_edits.TARGET
            target.parent.mkdir(parents=True)
            shutil.copyfile(source / source_edits.TARGET, target)
            mutate(target, old, new)
            try:
                validate_source.validate(root)
            except ValueError:
                rejected += 1
            else:
                raise SystemExit(f"unsafe mutation accepted: {label}")
    print(f"unsafe_source_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
