#!/usr/bin/env python3
"""Exercise positive validation and selected safety tripwires."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
VALIDATOR = EXPERIMENT / "scripts" / "validate.py"


def run_validator(root):
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--experiment-root", str(root)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def mutate(root, relative_path, old, new):
    path = root / relative_path
    text = path.read_text()
    if text.count(old) != 1:
        raise AssertionError(
            "{}: expected one mutation target {!r}, found {}".format(
                relative_path, old, text.count(old)
            )
        )
    path.write_text(text.replace(old, new, 1))


def expect_rejected(label, relative_path, old, new, expected_error):
    with tempfile.TemporaryDirectory(prefix="mt6797-a72-observer-test-") as tmp:
        copied = Path(tmp) / "experiment"
        shutil.copytree(EXPERIMENT, copied)
        mutate(copied, relative_path, old, new)
        result = run_validator(copied)
        if result.returncode == 0:
            raise AssertionError("{} mutation was accepted".format(label))
        output = result.stdout + result.stderr
        if expected_error not in output:
            raise AssertionError(
                "{} rejected for an unexpected reason:\n{}".format(label, output)
            )


def main():
    result = run_validator(EXPERIMENT)
    if result.returncode != 0:
        raise AssertionError("unmodified series failed:\n{}".format(result.stderr))

    patch1 = (
        "patches/0001-diagnostic-add-fixed-MT6797-A72-transition-ring.patch"
    )
    patch2 = (
        "patches/0002-diagnostic-add-owner-local-fixed-A72-snapshots.patch"
    )
    expect_rejected(
        "writable proc mode",
        patch1,
        "proc_create(MT6797_A72_OBS_PROC_NAME, 0400, NULL,",
        "proc_create(MT6797_A72_OBS_PROC_NAME, 0600, NULL,",
        "missing 'proc_create(MT6797_A72_OBS_PROC_NAME, 0400, NULL,'",
    )
    expect_rejected(
        "secure address drift",
        patch2,
        "0x10222470",
        "0x10222474",
        "secure address 0x10222470 count changed",
    )
    expect_rejected(
        "proc write callback",
        patch1,
        "\t.read = seq_read,\n",
        "\t.read = seq_read,\n+\t.write = seq_write,\n",
        "writable file operation",
    )
    expect_rejected(
        "toolchain package checksum drift",
        "inputs/stretch-cross-toolchain.tsv",
        "b7b3b0605b86f795f0a10d197fbfe161a281d1b081eb73c38d331c7db6b5f9dc",
        "a7b3b0605b86f795f0a10d197fbfe161a281d1b081eb73c38d331c7db6b5f9dc",
        "pinned toolchain manifest hash changed",
    )
    expect_rejected(
        "boot-candidate promotion",
        "scripts/build-on-buildbox",
        "boot_candidate: false",
        "boot_candidate: true",
        "missing 'boot_candidate: false'",
    )
    print("PASS: positive validation and 5 mutation tripwires")
    return 0


if __name__ == "__main__":
    sys.exit(main())
