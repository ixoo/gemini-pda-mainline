#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Generate the resource-layout delta from frozen text inputs."""
import signal
import subprocess
import sys
from support import HERE, SPEC, digest, git_environment, require, scratch, verify_predecessors


MAKEFILE = """# SPDX-License-Identifier: GPL-2.0-only
obj-y += hif.o
obj-y += mtke.o crc-kernel.o
obj-y += image-plan.o
obj-y += image-binding.o
obj-y += emi-abi.o
obj-y += remap-fields.o
"""


def generate():
    verify_predecessors()
    with scratch("patch") as tree:
        env = git_environment()

        def git(*args):
            return subprocess.check_output(["git", *args], cwd=tree, env=env,
                                           stderr=subprocess.PIPE, timeout=30)

        target = tree / SPEC["kernel_directory"]
        target.mkdir(parents=True)
        (target / "Makefile").write_text(MAKEFILE)
        git("init", "--quiet")
        git("add", "drivers")
        git("commit", "--quiet", "--no-gpg-sign", "-m",
            "Pinned predecessor private MT6797 Kbuild")
        base = git("rev-parse", "HEAD").decode().strip()
        for name in ("resource-layout.c", "resource-layout.h"):
            (target / name).write_bytes((HERE / "src" / name).read_bytes())
        with (target / "Makefile").open("a") as output:
            output.write("obj-y += resource-layout.o\n")
        git("add", "drivers")
        git("diff", "--cached", "--check")
        git("commit", "--quiet", "--no-gpg-sign", "-m",
            "wifi: mediatek: compile reserved-resource layout bridge\n\n"
            "Compose the initialized reserved-memory description into checked\n"
            "remap and descriptive EMI ranges without selecting policy or\n"
            "adding a runtime caller or hardware effect.\n\n"
            "Internal experiment only; synthetic non-certifying author, no DCO.\n"
            "Assisted-by: LLM")
        patch = git("format-patch", "--stdout", "--no-signature", "-1")
        expected = git("rev-parse", "HEAD^{tree}")
        git("reset", "--hard", "--quiet", base)
        patch_file = tree / "review.patch"
        patch_file.write_bytes(patch)
        git("apply", "--index", "review.patch")
        require(git("write-tree") == expected, "patch replay tree differs")
        require(digest((HERE / "src" / "resource-layout.c").read_bytes()),
                "empty implementation")
        return patch


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    require(len(sys.argv) == 1, "no arguments accepted")
    sys.stdout.buffer.write(generate())
