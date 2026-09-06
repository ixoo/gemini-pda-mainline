#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Generate the one-object remap-fields delta from frozen text inputs."""
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
        (target / "remap-fields.c").write_bytes(
            (HERE / "src" / "remap-fields.c").read_bytes())
        (target / "remap-fields.h").write_bytes(
            (HERE / "src" / "remap-fields.h").read_bytes())
        with (target / "Makefile").open("a") as output:
            output.write("obj-y += remap-fields.o\n")
        git("add", "drivers")
        git("diff", "--cached", "--check")
        git("commit", "--quiet", "--no-gpg-sign", "-m",
            "wifi: mediatek: compile checked MT6797 remap fields\n\n"
            "Add pure checked encoders and expected-state masked replacements\n"
            "for the shared remap register as a separately compiled private\n"
            "object. No runtime caller, MMIO or hardware admission is supplied.\n\n"
            "Internal experiment only; synthetic non-certifying author, no DCO.\n"
            "Assisted-by: LLM")
        patch = git("format-patch", "--stdout", "--no-signature", "-1")
        expected = git("rev-parse", "HEAD^{tree}")
        git("reset", "--hard", "--quiet", base)
        patch_file = tree / "review.patch"
        patch_file.write_bytes(patch)
        git("apply", "--index", "review.patch")
        require(git("write-tree") == expected, "patch replay tree differs")
        require(digest((HERE / "src" / "remap-fields.c").read_bytes()),
                "empty implementation")
        return patch


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    require(len(sys.argv) == 1, "no arguments accepted")
    sys.stdout.buffer.write(generate())
