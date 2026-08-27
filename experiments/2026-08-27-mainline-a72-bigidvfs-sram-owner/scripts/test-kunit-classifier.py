#!/usr/bin/env python3
"""Mutation tests for the BigiDVFS SRAM-owner QEMU classifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "bigidvfs_sram_classifier", SCRIPT_DIR / "classify-kunit.py")
if SPEC is None or SPEC.loader is None:
    raise SystemExit("unable to load classifier")
CLASSIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLASSIFIER)


def transcript() -> str:
    cases = "\n".join(
        f"    ok {index} {case}"
        for index, case in enumerate(CLASSIFIER.EXPECTED_CASES, start=1)
    )
    return f"""Linux version 7.1.3-gemini-a72-bigidvfs-sram-kunit (builder)
KTAP version 1
1..1
    KTAP version 1
    # Subtest: {CLASSIFIER.SUITE}
    1..8
{cases}
    # {CLASSIFIER.SUITE}: pass:8 fail:0 skip:0 total:8
ok 1 {CLASSIFIER.SUITE}
# Totals: pass:8 fail:0 skip:0 total:8
Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(0,0)
---[ end Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(0,0) ]---
"""


def rejected(raw: str, release: str =
             "7.1.3-gemini-a72-bigidvfs-sram-kunit",
             qemu_exit: int = 124) -> bool:
    try:
        CLASSIFIER.classify_runtime(raw, release, qemu_exit)
    except CLASSIFIER.ClassificationError:
        return True
    return False


def main() -> None:
    raw = transcript()
    CLASSIFIER.classify_runtime(
        raw, "7.1.3-gemini-a72-bigidvfs-sram-kunit", 124)
    mutations = (
        raw.replace("ok 1 mt6797_bigidvfs_sram_success_test",
                    "not ok 1 mt6797_bigidvfs_sram_success_test", 1),
        raw.replace("    1..8", "    1..7", 1),
        raw.replace(CLASSIFIER.EXPECTED_CASES[3], "renamed_case", 1),
        raw.replace("pass:8 fail:0", "pass:7 fail:1", 1),
        raw.replace("# Subtest: mt6797-bigidvfs-sram-owner",
                    "# Subtest: unexpected-suite", 1),
        raw.replace("Kernel panic - not syncing:",
                    "Kernel stopped - not syncing:", 1),
    )
    for index, mutation in enumerate(mutations, start=1):
        if not rejected(mutation):
            raise SystemExit(f"mutation accepted: {index}")
    if not rejected(raw, "7.1.3-wrong-release"):
        raise SystemExit("wrong release accepted")
    if not rejected(raw, qemu_exit=0):
        raise SystemExit("wrong QEMU exit accepted")
    print("validation=bigidvfs-sram-kunit-classifier")
    print("positive_cases=1")
    print("mutations_rejected=8")


if __name__ == "__main__":
    main()
