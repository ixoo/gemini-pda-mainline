#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Generate one review-only format-patch from bounded, hash-pinned text inputs.

No Linux checkout, backend access, canonical-series edit or device action.
Patch goes to stdout; temporary Git metadata/text are always locally scoped.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]


def require(ok, message):
    if not ok:
        raise SystemExit(message)


def main():
    require(len(sys.argv) == 1, "no arguments accepted")
    spec = json.loads((HERE / "inputs.json").read_text())
    files = {}
    for path, digest in spec["upstream_files"].items():
        url = ("https://raw.githubusercontent.com/torvalds/linux/" +
               spec["upstream_commit"] + "/" + path)
        with urllib.request.urlopen(url, timeout=20) as response:
            data = response.read(262145)
        require(len(data) <= 262144, "oversized upstream input")
        require(hashlib.sha256(data).hexdigest() == digest, "upstream hash: " + path)
        files[path] = data
    additions = {}
    for name, digest in spec["protocol_headers"].items():
        path = spec["protocol_directory"] + "/" + name
        data = subprocess.check_output(
            ["git", "show", spec["protocol_commit"] + ":" + path], cwd=ROOT)
        require(hashlib.sha256(data).hexdigest() == digest, "protocol hash: " + name)
        additions[name] = data
    for name, digest in spec["adapter_files"].items():
        data = (HERE.parent / "2026-09-05-mt6797-wifi-hif-core" / "src" / name).read_bytes()
        require(hashlib.sha256(data).hexdigest() == digest, "adapter hash: " + name)
        additions[name] = data
    managed = ROOT / "artifacts" / "wifi-hif-parser-compile"
    managed.mkdir(parents=True, exist_ok=True)
    require(not managed.is_symlink(), "managed root is a symlink")
    lock_path = managed / ".generator.lock"
    require(not lock_path.is_symlink(), "lock is a symlink")
    lock = lock_path.open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    marker = "mt6797-hif-parser-patch-v1\n"
    # A killed generator releases its advisory lock. Remove only our marked,
    # symlink-free scratch; unknown state refuses instead of being guessed.
    for stale in managed.glob("patch-*"):
        require(stale.is_dir() and not stale.is_symlink(), "unsafe stale scratch")
        stamp = stale / ".owner"
        require(stamp.is_file() and not stamp.is_symlink() and
                stamp.read_text() == marker, "unowned stale scratch")
        require(all(not path.is_symlink() for path in stale.rglob("*")),
                "symlink in stale scratch")
        shutil.rmtree(stale)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_AUTHOR_NAME="MT6797 compile experiment",
               GIT_AUTHOR_EMAIL="nobody@example.invalid",
               GIT_COMMITTER_NAME="MT6797 compile experiment",
               GIT_COMMITTER_EMAIL="nobody@example.invalid",
               GIT_AUTHOR_DATE="2026-09-05T00:00:00+0000",
               GIT_COMMITTER_DATE="2026-09-05T00:00:00+0000")
    # Independent tiny text-only fixture, not a Linux source checkout.
    with tempfile.TemporaryDirectory(prefix="patch-", dir=managed) as directory:
        tree = Path(directory)
        (tree / ".owner").write_text(marker)

        def git(*args):
            return subprocess.check_output(["git", *args], cwd=tree, env=env,
                                           stderr=subprocess.PIPE, timeout=30)

        git("init", "--quiet")
        for path, data in files.items():
            destination = tree / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        git("add", "drivers")
        git("commit", "--quiet", "--no-gpg-sign", "-m", "Pinned upstream text inputs")
        base = git("rev-parse", "HEAD").decode().strip()
        target = tree / "drivers/net/wireless/mediatek/mt6797"
        target.mkdir()
        for name, data in additions.items():
            (target / name).write_bytes(data)
        with (tree / "drivers/net/wireless/mediatek/Makefile").open("ab") as output:
            output.write(b"\nobj-$(CONFIG_MT6797_HIF_CORE) += mt6797/\n")
        kconfig = tree / "drivers/net/wireless/mediatek/Kconfig"
        text = kconfig.read_text()
        anchor = "endif # WLAN_VENDOR_MEDIATEK"
        require(text.count(anchor) == 1, "wireless Kconfig anchor differs")
        kconfig.write_text(text.replace(anchor,
            'source "drivers/net/wireless/mediatek/mt6797/Kconfig"\n' + anchor))
        git("add", "drivers")
        git("diff", "--cached", "--check")
        git("commit", "--quiet", "--no-gpg-sign", "-m",
            "wifi: mediatek: add private MT6797 register and INIT transport\n\n"
            "Provide ordered logical-register reads and bounded ordinary-section\n"
            "CONFIG/ACK/PDA execution with one retained transaction and deadline.\n"
            "The existing provider must own power, mapping and exclusion. No\n"
            "registration, mapping acquisition or runtime caller is added.\n\n"
            "Internal compile experiment only; not an upstream submission.\n"
            "The synthetic author is non-certifying; no DCO is asserted.\n"
            "Assisted-by: LLM")
        # The first commit recreates the pinned private core without changing it.
        base = git("rev-parse", "HEAD").decode().strip()
        for name in ("mtke.c", "mtke.h", "crc-kernel.c"):
            data = (HERE / "src" / name).read_bytes()
            require(hashlib.sha256(data).hexdigest() == spec["parser_files"][name],
                    "parser hash: " + name)
            (target / name).write_bytes(data)
        with (target / "Makefile").open("a") as output:
            output.write("obj-y += mtke.o crc-kernel.o\n")
        configuration = target / "Kconfig"
        configuration.write_text(configuration.read_text().replace(
            "\tdefault n", "\tselect CRC32\n\tdefault n"))
        git("add", "drivers")
        git("diff", "--cached", "--check")
        git("commit", "--quiet", "--no-gpg-sign", "-m",
            "wifi: mediatek: compile structural MTKE parser with private HIF core\n\n"
            "Add the original bounded parser and standard kernel CRC32 adapter.\n"
            "No firmware acquisition, probe or runtime caller is supplied.\n\n"
            "Internal experiment only; synthetic non-certifying author, no DCO.\n"
            "Assisted-by: LLM")
        patch = git("format-patch", "--stdout", "--no-signature", "-1")
        # Independent replay against the exact two original upstream files.
        expected = git("rev-parse", "HEAD^{tree}")
        git("reset", "--hard", "--quiet", base)
        patch_file = tree / "review.patch"
        patch_file.write_bytes(patch)
        git("apply", "--index", "review.patch")
        require(git("write-tree") == expected, "patch replay tree differs")
        sys.stdout.buffer.write(patch)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    main()
