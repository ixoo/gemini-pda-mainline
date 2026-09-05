#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""One review-only kernel delta; no Linux tree, series edit or backend access."""
import signal
import subprocess
import sys
from support import HERE, SPEC, git_environment, pinned, require, scratch


def generate():
    with scratch("patch") as tree:
        env = git_environment()

        def git(*args):
            return subprocess.check_output(["git", *args], cwd=tree, env=env,
                                           stderr=subprocess.PIPE, timeout=30)

        target = tree / "drivers/net/wireless/mediatek/mt6797"
        target.mkdir(parents=True)
        for name, item in SPEC["base_binding"].items():
            (target / name).write_bytes(pinned(item))
        git("init", "--quiet")
        git("add", "drivers")
        git("commit", "--quiet", "--no-gpg-sign", "-m", "Pinned private image binding inputs")
        base = git("rev-parse", "HEAD").decode().strip()
        for name in ("image-binding.c", "image-binding.h"):
            (target / name).write_bytes((HERE / "src" / name).read_bytes())
        git("add", "drivers")
        git("diff", "--cached", "--check")
        git("commit", "--quiet", "--no-gpg-sign", "-m",
            "wifi: mediatek: describe reserved memory in private image owner\n\n"
            "Retain a passive descriptor from Linux OF reserved-memory APIs and\n"
            "revalidate its identity and ranges before describing image readiness.\n"
            "Keep the same owner, generation domain and conservative fault lifetime.\n"
            "No exclusive claim, mapping, region callback or hardware effect occurs.\n"
            "Active entry remains unsupported.\n\n"
            "Internal experiment only; synthetic non-certifying author, no DCO.\n"
            "Assisted-by: LLM")
        patch = git("format-patch", "--stdout", "--no-signature", "-1")
        expected = git("rev-parse", "HEAD^{tree}")
        git("reset", "--hard", "--quiet", base)
        (tree / "review.patch").write_bytes(patch)
        git("apply", "--index", "review.patch")
        require(git("write-tree") == expected, "patch replay tree differs")
        return patch


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    require(len(sys.argv) == 1, "no arguments accepted")
    sys.stdout.buffer.write(generate())
