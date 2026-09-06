#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Shared bounded helpers for the offline EMI ABI proposal."""
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
    for path, expected in SPEC["predecessor_patches"].items():
        data = git_show(SPEC["frozen_parent"], "patches/" + path)
        actual = digest(data)
        if expected:
            require(actual == expected, "predecessor identity changed: " + path)


def git_environment():
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="MT6797 compile experiment",
               GIT_AUTHOR_EMAIL="nobody@example.invalid",
               GIT_COMMITTER_NAME="MT6797 compile experiment",
               GIT_COMMITTER_EMAIL="nobody@example.invalid",
               GIT_AUTHOR_DATE="2026-09-06T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-09-06T00:00:00+0000")
    return env


@contextmanager
def scratch(kind):
    artifacts = ROOT / "artifacts"
    require(not artifacts.is_symlink(), "artifacts is a symlink")
    managed = artifacts / "emi-abi-compile"
    require(not managed.is_symlink(), "managed root is a symlink")
    managed.mkdir(parents=True, exist_ok=True)
    lock_path = managed / ("." + kind + ".lock")
    require(not lock_path.is_symlink(), "lock is a symlink")
    marker = "mt6797-emi-abi-compile-" + kind + "-v1\n"
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
