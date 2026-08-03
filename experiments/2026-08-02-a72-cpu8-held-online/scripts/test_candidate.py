#!/usr/bin/env python3
"""Static checks for the CPU8 held-online Android-v0 candidate builder."""

import hashlib
import re
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
ASSEMBLER = SCRIPT_DIR / "assemble.py"
BUILDER = SCRIPT_DIR / "build-candidate.sh"
PARENT_ASSEMBLER = (
    EXPERIMENT.parent
    / "2026-08-02-a72-one-way-cpu8-boundary"
    / "scripts"
    / "assemble.py"
)

EXPECTED = {
    "REPOSITORY_COMMIT": "118ff3cb3e9a2fbee10a44ada748e46bbe9b5312",
    "PARENT_PATCHSET_SHA256": "3584e9dd5ffb041573b851f31f3a96eaa0a684acb880fd59560762e5abc58be0",
    "ACCEPTED_ROLLBACK_PATCHSET_SHA256": "76a00aeb9ebefe0c964e70e56b63977071d2f2b12b12ce52ecdb7bb298f8fdd3",
    "ONE_WAY_PATCHSET_SHA256": "d9649e1453a05bc8a016da6fa371e97480ff62aebad3dedd87d148d5cb574890",
    "HELD_PATCHSET_SHA256": "e6da1e8cc976ad63dd9cf8a254bb7234d73589cfad6afeb07135403a27d03ba3",
    "KERNEL_SHA256": "9158af17b17e483ec68257378e5c4bd923b254e7242b5ba338f1324eec5f960b",
    "ACTIVE_BOOT_SHA256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "ACTIVE_RAMDISK_SHA256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "EXPECTED_RAW_SHA256": "53046cf314f76f213abafa53a1e79758ff835941d78a47ecc878d0a2e1ad3789",
    "EXPECTED_PADDED_SHA256": "936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    assembler = ASSEMBLER.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    require(
        hashlib.sha256(PARENT_ASSEMBLER.read_bytes()).hexdigest()
        == "2c6e59da67357c946f1ce6e4300fadaf732add0e124f25ba84aefe2a222bbb4b",
        "one-way Android-v0 assembler identity changed",
    )
    require(
        'KERNEL_FIELD_SHA256 = "9158af17b17e483ec68257378e5c4bd923b254e7242b5ba338f1324eec5f960b"'
        in assembler,
        "assembler kernel identity changed",
    )
    require(
        "assembler.KERNEL_FIELD_SHA256 = KERNEL_FIELD_SHA256" in assembler,
        "assembler no longer pins the replacement kernel",
    )
    for name, value in EXPECTED.items():
        require(
            f"readonly {name}={value}" in builder,
            f"builder identity changed: {name}",
        )
    required = {
        "Buildbox manifest": "sha256sum --check --strict SHA256SUMS",
        "compile-only provenance": "compile bundle incorrectly claims boot-candidate status",
        "held purpose": "held-online-compile-review-only",
        "two raw assemblies": "two raw container assemblies differ",
        "two padding paths": "independent padded constructions differ",
        "zero tail": "padded tail is not zero",
        "raw identity": "raw identity changed",
        "padded identity": "padded identity changed",
        "final manifest": "candidate manifest failed",
        "no runtime claim": "runtime_result=not-tested",
        "no device access": "device_access=none",
    }
    for label, token in required.items():
        require(token in builder, f"missing {label}")
    require(
        builder.count('python3 "$assembler" --active-boot "$active_boot"') == 2,
        "builder must perform exactly two raw assemblies",
    )
    require(
        builder.count(
            'cmp -s "$stage/boot2-padded.img" "$replica/boot2-padded.img"'
        )
        == 1,
        "builder must compare the two padding paths exactly once",
    )
    for pattern in (
        r"/dev/mmc",
        r"/dev/block",
        r"192\.168\.",
        r"\bssh\b",
        r"\bnc\b",
        r"\bnetcat\b",
        r"\breboot\b",
        r"\bpoweroff\b",
        r"\bshutdown\b",
    ):
        require(
            re.search(pattern, builder) is None,
            f"offline builder gained device/runtime operation: {pattern}",
        )
    help_run = subprocess.run(
        [str(BUILDER), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    require("--bundle DIR" in help_run.stdout, "builder help contract changed")
    print("validation=cpu8-held-online-candidate-static")
    print("checks=identity,provenance,reproducibility,padding,manifest,offline-only")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
