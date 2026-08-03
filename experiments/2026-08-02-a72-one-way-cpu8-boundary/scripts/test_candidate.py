#!/usr/bin/env python3
"""Static checks for the one-way CPU8 Android-v0 candidate builder."""

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
    / "2026-08-02-gemian-a72-bounded-observer-boot"
    / "scripts"
    / "assemble.py"
)

EXPECTED = {
    "REPOSITORY_COMMIT": "bd499e234e0849dbc96a5c7274b414564f016b6d",
    "PARENT_PATCHSET_SHA256": "3584e9dd5ffb041573b851f31f3a96eaa0a684acb880fd59560762e5abc58be0",
    "ACCEPTED_ROLLBACK_PATCHSET_SHA256": "76a00aeb9ebefe0c964e70e56b63977071d2f2b12b12ce52ecdb7bb298f8fdd3",
    "ONE_WAY_PATCHSET_SHA256": "d9649e1453a05bc8a016da6fa371e97480ff62aebad3dedd87d148d5cb574890",
    "KERNEL_SHA256": "e65a74cf5445a9e22a537b760e566a5a21d3d314e81689dd01c52bd11e7c6676",
    "ACTIVE_BOOT_SHA256": "1fa78de9f8744a6818bcef2f6773737939f84364de982413910d4958d6d21513",
    "ACTIVE_RAMDISK_SHA256": "a1ee05445e9a2bd8fbc1f75d7cda326b9ca7a6d3b644cbb1d5fc0ac167835be4",
    "EXPECTED_RAW_SHA256": "aae1a0f9a3d9a3c73a4930478c2e0db672d3a12ce020ad852d9e274c7f54858a",
    "EXPECTED_PADDED_SHA256": "fc7368ef0bd56b5c17fea277f78bfeae362da5f685be9f85686f991cdc4fefda",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    assembler = ASSEMBLER.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")
    parent_bytes = PARENT_ASSEMBLER.read_bytes()

    require(
        hashlib.sha256(parent_bytes).hexdigest()
        == "532f6f0dec5030a7b066f3baefa53580ec148317f633d4dd8d43308d30ac03b3",
        "parent Android-v0 assembler identity changed",
    )
    require(
        'KERNEL_FIELD_SHA256 = "e65a74cf5445a9e22a537b760e566a5a21d3d314e81689dd01c52bd11e7c6676"'
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
        "Buildbox manifest verification": "sha256sum --check --strict SHA256SUMS",
        "compile-only provenance rejection": "compile bundle incorrectly claims boot-candidate status",
        "two raw assemblies": "two raw container assemblies differ",
        "two padding constructions": "independent padded constructions differ",
        "zero-tail verification": "padded tail is not zero",
        "raw identity gate": "raw identity changed",
        "padded identity gate": "padded identity changed",
        "final manifest verification": "candidate manifest failed",
        "no runtime claim": "runtime_result=not-tested",
        "no device access claim": "device_access=none",
    }
    for label, token in required.items():
        require(token in builder, f"missing {label}")

    require(
        builder.count('python3 "$assembler" --active-boot "$active_boot"') == 2,
        "builder must perform exactly two raw assemblies",
    )
    require(
        builder.count('cmp -s "$stage/boot2-padded.img" "$replica/boot2-padded.img"')
        == 1,
        "builder must compare the independent padded constructions exactly once",
    )
    forbidden = (
        r"/dev/mmc",
        r"/dev/block",
        r"192\.168\.",
        r"\bssh\b",
        r"\bnc\b",
        r"\bnetcat\b",
        r"\breboot\b",
        r"\bpoweroff\b",
        r"\bshutdown\b",
    )
    for pattern in forbidden:
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
    print("validation=one-way-cpu8-candidate-static")
    print("checks=identity,provenance,reproducibility,padding,manifest,offline-only")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
