#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Shared bounded helpers for the offline remap-fields proposal."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
SPEC = json.loads((HERE / "inputs.json").read_text())


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git_show(commit, path):
    return subprocess.check_output(["git", "show", commit + ":" + path],
                                   cwd=ROOT, timeout=30)


def verify_predecessors():
    series = git_show(SPEC["frozen_parent"], SPEC["series_path"])
    require(digest(series) == SPEC["series_sha256"],
            "named series identity changed")
    actual_entries = []
    for raw_line in series.decode("utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            require(line == raw_line, "series entry has surrounding whitespace")
            actual_entries.append(line)
    expected_entries = [entry["path"] for entry in SPEC["series_entries"]]
    require(actual_entries == expected_entries, "named series order changed")
    for entry in SPEC["series_entries"]:
        actual = digest(git_show(SPEC["frozen_parent"],
                                 "patches/" + entry["path"]))
        require(actual == entry["sha256"],
                "series entry identity changed: " + entry["path"])
    for path, expected in SPEC["evidence_documents"].items():
        actual = digest(git_show(SPEC["frozen_parent"], path))
        require(actual == expected, "evidence identity changed: " + path)


def git_environment():
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="MT6797 remap-fields experiment",
               GIT_AUTHOR_EMAIL="nobody@example.invalid",
               GIT_COMMITTER_NAME="MT6797 remap-fields experiment",
               GIT_COMMITTER_EMAIL="nobody@example.invalid",
               GIT_AUTHOR_DATE="2026-09-06T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-09-06T00:00:00+0000")
    return env


@contextmanager
def scratch(kind):
    artifacts = ROOT / "artifacts"
    require(not artifacts.is_symlink(), "artifacts is a symlink")
    managed = artifacts / "remap-fields-compile"
    require(not managed.is_symlink(), "managed root is a symlink")
    managed.mkdir(parents=True, exist_ok=True)
    lock_path = managed / ("." + kind + ".lock")
    require(not lock_path.is_symlink(), "lock is a symlink")
    marker = "mt6797-remap-fields-compile-" + kind + "-v1\n"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for stale in managed.glob(kind + "-*"):
            require(stale.is_dir() and not stale.is_symlink(),
                    "unsafe stale scratch")
            stamp = stale / ".owner"
            require(stamp.is_file() and not stamp.is_symlink() and
                    stamp.read_text() == marker, "unowned stale scratch")
            require(all(not path.is_symlink() for path in stale.rglob("*")),
                    "symlink in stale scratch")
            shutil.rmtree(stale)
        with tempfile.TemporaryDirectory(prefix=kind + "-", dir=managed) as name:
            path = Path(name)
            (path / ".owner").write_text(marker)
            yield path
