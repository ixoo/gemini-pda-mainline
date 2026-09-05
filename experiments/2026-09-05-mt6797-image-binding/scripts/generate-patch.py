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
        for name, item in SPEC["dependencies"].items():
            (target / name).write_bytes(pinned(item))
        makefile = pinned(SPEC["base_makefile"]) + SPEC["base_makefile_suffix"].encode()
        (target / "Makefile").write_bytes(makefile)
        git("init", "--quiet")
        git("add", "drivers")
        git("commit", "--quiet", "--no-gpg-sign", "-m", "Pinned private image-plan inputs")
        base = git("rev-parse", "HEAD").decode().strip()
        for name in ("image-binding.c", "image-binding.h"):
            (target / name).write_bytes((HERE / "src" / name).read_bytes())
        with (target / "Makefile").open("ab") as output:
            output.write(b"obj-y += image-binding.o\n")
        git("add", "drivers")
        git("diff", "--cached", "--check")
        git("commit", "--quiet", "--no-gpg-sign", "-m",
            "wifi: mediatek: retain private immutable image bindings\n\n"
            "Copy firmware before complete-plan validation and retain an opaque\n"
            "snapshot under a persistent, no-wrap generation domain. Serialize\n"
            "passive client claims and distinguish passive release from fault\n"
            "retention. Active entry refuses until a real provider is connected.\n"
            "No registration, hardware effect or recovery shortcut is supplied.\n\n"
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
