#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Managed, bounded text/test scratch and exact existing C dependencies."""
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


def pinned(item):
    data = subprocess.check_output(
        ["git", "show", item["commit"] + ":" + item["path"]],
        cwd=ROOT, timeout=30)
    require(digest(data) == item["sha256"], "dependency identity changed")
    return data


@contextmanager
def scratch(kind):
    artifacts = ROOT / "artifacts"
    require(not artifacts.is_symlink(), "artifacts is a symlink")
    managed = artifacts / "dynamic-reserved-binding"
    require(not managed.is_symlink(), "managed root is a symlink")
    managed.mkdir(parents=True, exist_ok=True)
    lock_path = managed / ("." + kind + ".lock")
    require(not lock_path.is_symlink(), "lock is a symlink")
    marker = "mt6797-dynamic-reserved-binding-" + kind + "-v1\n"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for stale in managed.glob(kind + "-*"):
            require(stale.is_dir() and not stale.is_symlink(), "unsafe stale path")
            stamp = stale / ".owner"
            require(stamp.is_file() and not stamp.is_symlink() and
                    stamp.read_text() == marker, "unowned stale path")
            require(all(not p.is_symlink() for p in stale.rglob("*")),
                    "symlink in stale path")
            shutil.rmtree(stale)
        # The context owns cleanup immediately, including exceptions/signals.
        with tempfile.TemporaryDirectory(prefix=kind + "-", dir=managed) as name:
            path = Path(name)
            (path / ".owner").write_text(marker)
            yield path


def git_environment():
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="MT6797 binding experiment",
               GIT_AUTHOR_EMAIL="nobody@example.invalid",
               GIT_COMMITTER_NAME="MT6797 binding experiment",
               GIT_COMMITTER_EMAIL="nobody@example.invalid",
               GIT_AUTHOR_DATE="2026-09-05T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-09-05T00:00:00+0000")
    return env
