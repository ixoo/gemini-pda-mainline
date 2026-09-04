#!/usr/bin/env python3
"""Reproduce the one-predicate thermal-ledger live-model patch."""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path


PARENT_PATCH = "patches/v7.1.3/0521-pstore-add-Gemini-MT6797-thermal-stage-ledger.patch"
PARENT_PATCH_SHA256 = "ad6b9c2068de438749dc8681e3637be0a49279620effcfba7e7840558e3c26b4"
SOURCE = "fs/pstore/gemini_mt6797_thermal_ledger.c"
SOURCE_SHA256 = "17e2b62ef8342af4dfe1665a1ce1b2d22276f59e326c7ca9fd356ac0b17bf837"
OUTPUT_SHA256 = "c99d16ced8952df6c8c6eefa27304e9bfe6e3685bef6f3e554f58fa79a022e03"
OLD = '''\tif (!of_machine_is_compatible("planet,gemini-pda") ||
\t    of_property_read_string(of_root, "model", &model) ||
\t    strcmp(model,
\t\t   "Planet Computers Gemini PDA (thermal serviceability)"))
'''
NEW = '''\tif (!of_machine_is_compatible("planet,gemini-pda") ||
\t    of_property_read_string(of_root, "model", &model) ||
\t    strcmp(model, "MT6797X"))
'''


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_added_file(patch: str) -> bytes:
    header = f"diff --git a/{SOURCE} b/{SOURCE}"
    if patch.count(header) != 1:
        raise ValueError("parent patch target-file boundary changed")
    segment = patch.split(header, 1)[1]
    if "\ndiff --git " in segment:
        segment = segment.split("\ndiff --git ", 1)[0]
    lines = [
        line[1:]
        for line in segment.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    data = ("\n".join(lines) + "\n").encode()
    if digest(data) != SOURCE_SHA256:
        raise ValueError("reconstructed parent source changed")
    return data


def run(repository: Path, output: Path) -> None:
    parent_path = repository / PARENT_PATCH
    parent = parent_path.read_bytes()
    if digest(parent) != PARENT_PATCH_SHA256:
        raise ValueError("parent patch identity changed")
    source = extract_added_file(parent.decode())
    text = source.decode()
    if text.count(OLD) != 1 or "MT6797X" in text:
        raise ValueError("live-model edit anchor changed")
    repaired = text.replace(OLD, NEW, 1)
    if output.exists() or output.is_symlink():
        raise ValueError("refusing to overwrite output")
    output.parent.resolve(strict=True)

    with tempfile.TemporaryDirectory(prefix="gemini-thermal-model-") as temporary:
        tree = Path(temporary) / "source"
        target = tree / SOURCE
        target.parent.mkdir(parents=True)
        target.write_text(text)
        subprocess.run(["git", "-C", os.fspath(tree), "init", "--quiet"], check=True)
        subprocess.run(["git", "-C", os.fspath(tree), "config", "user.name", "Gemini Mainline Experiment"], check=True)
        subprocess.run(["git", "-C", os.fspath(tree), "config", "user.email", "gemini-mainline@example.invalid"], check=True)
        subprocess.run(["git", "-C", os.fspath(tree), "add", SOURCE], check=True)
        environment = os.environ.copy()
        environment.update(
            GIT_AUTHOR_DATE="2026-09-04T20:00:00Z",
            GIT_COMMITTER_DATE="2026-09-04T20:00:00Z",
        )
        subprocess.run(
            ["git", "-C", os.fspath(tree), "commit", "--quiet", "--no-gpg-sign", "-m", "exact thermal-ledger source parent"],
            check=True, env=environment,
        )
        target.write_text(repaired)
        subprocess.run(["git", "-C", os.fspath(tree), "diff", "--check"], check=True)
        subprocess.run(["git", "-C", os.fspath(tree), "add", SOURCE], check=True)
        environment.update(
            GIT_AUTHOR_NAME="Gemini Mainline Experiment",
            GIT_AUTHOR_EMAIL="gemini-mainline@example.invalid",
            GIT_COMMITTER_NAME="Gemini Mainline Experiment",
            GIT_COMMITTER_EMAIL="gemini-mainline@example.invalid",
            GIT_AUTHOR_DATE="2026-09-04T20:01:00Z",
            GIT_COMMITTER_DATE="2026-09-04T20:01:00Z",
        )
        subprocess.run(
            [
                "git", "-C", os.fspath(tree), "commit", "--quiet", "--no-gpg-sign",
                "-m", "pstore: match Gemini thermal ledger after LK model rewrite",
                "-m", "LK publishes the live Gemini root model as MT6797X. Match that\nestablished runtime identity so the optional diagnostic ledger cannot\nreject the thermal probe before calibration or hardware access.",
                "-m", "Keep the compatible, ramoops, address, size, reset, thermal, and zone\ngates unchanged.",
            ],
            check=True, env=environment,
        )
        generated = subprocess.check_output(
            ["git", "-C", os.fspath(tree), "format-patch", "-1", "--stdout", "--no-signature"],
            env={**environment, "LC_ALL": "C"},
        )
    if digest(generated) != OUTPUT_SHA256:
        raise ValueError("generated patch identity changed")
    output.write_bytes(generated)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.repository.resolve(strict=True), args.output)
    print(f"patch_sha256={OUTPUT_SHA256}")
    print("changed_paths=1")
    print("changed_predicates=1")
    print("hardware_action=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
