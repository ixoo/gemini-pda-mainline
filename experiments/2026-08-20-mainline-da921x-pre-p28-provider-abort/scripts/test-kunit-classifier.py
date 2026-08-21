#!/usr/bin/env python3
"""Prove that the pre-P28 membership-abort classifier fails closed."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("classify-kunit.py")
SPEC = importlib.util.spec_from_file_location("membership_abort_classifier", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load classifier")
CLASSIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLASSIFIER)

RELEASE = "7.1.3-gemini-da921x-pre-p28-provider-abort-kunit"


def fixture() -> str:
    cases = "\n".join(
        f"[    1.0]     ok {index} {name}"
        for index, name in enumerate(CLASSIFIER.EXPECTED_CASES, start=1)
    )
    return f"""\
[    0.0] Linux version {RELEASE} (builder@example.invalid)
[    1.0] KTAP version 1
[    1.0] 1..1
[    1.0]     KTAP version 1
[    1.0]     # Subtest: {CLASSIFIER.SUITE}
[    1.0]     1..6
{cases}
[    1.0] # {CLASSIFIER.SUITE}: pass:6 fail:0 skip:0 total:6
[    1.0] # Totals: pass:6 fail:0 skip:0 total:6
[    1.0] ok 1 {CLASSIFIER.SUITE}
[    1.1] {CLASSIFIER.PANIC_PREFIX} on unknown-block(0,0)
[    1.2] {CLASSIFIER.PANIC_END_PREFIX} on unknown-block(0,0) ]---
qemu-system-aarch64: terminating on signal 15
"""


def main() -> None:
    digest = "a" * 64
    manifest = f"{digest}  ./Image\n{'b' * 64}  ./kernel.config\n"
    with tempfile.TemporaryDirectory(prefix="gemini-membership-abort-") as temporary:
        manifest_path = Path(temporary) / "SHA256SUMS"
        manifest_path.write_text(manifest, encoding="utf-8")
        if CLASSIFIER.manifest_checksum(manifest_path, "./Image") != digest:
            raise SystemExit("positive checksum-manifest fixture changed")
        manifest_mutations = (
            manifest.replace(f"{digest}  ./Image\n", "", 1),
            manifest + f"{digest}  ./Image\n",
            manifest.replace(digest, "g" * 64, 1),
        )
        manifest_rejected = 0
        for candidate in manifest_mutations:
            manifest_path.write_text(candidate, encoding="utf-8")
            try:
                CLASSIFIER.manifest_checksum(manifest_path, "./Image")
            except CLASSIFIER.ClassificationError:
                manifest_rejected += 1
            else:
                raise SystemExit("unsafe checksum-manifest mutation accepted")

    raw = fixture()
    CLASSIFIER.classify_runtime(raw, RELEASE, 124)
    cases = CLASSIFIER.EXPECTED_CASES
    mutations = (
        raw.replace(f"ok 4 {cases[3]}\n", "", 1),
        raw.replace(f"ok 5 {cases[4]}", f"not ok 5 {cases[4]}", 1),
        raw.replace("pass:6 fail:0 skip:0 total:6",
                    "pass:5 fail:0 skip:1 total:6", 1),
        raw.replace(f"# Subtest: {CLASSIFIER.SUITE}",
                    "# Subtest: unexpected-suite", 1),
        raw.replace(f"ok 1 {cases[0]}", "ok 1 wrong_case", 1),
        raw.replace(RELEASE, "7.1.3-wrong", 1),
        raw.replace("1..1", "1..2", 1),
        raw.replace("1..6", "1..7", 1),
        raw.replace(CLASSIFIER.PANIC_PREFIX, "System halted", 1),
        raw.replace(
            f"[    1.2] {CLASSIFIER.PANIC_END_PREFIX} "
            "on unknown-block(0,0) ]---\n", "", 1),
        raw.replace(
            f"[    1.1] {CLASSIFIER.PANIC_PREFIX} on unknown-block(0,0)\n",
            f"[    1.1] {CLASSIFIER.PANIC_PREFIX} on unknown-block(0,0)\n"
            f"[    1.1] {CLASSIFIER.PANIC_PREFIX} on unknown-block(0,0)\n", 1),
        raw.replace(
            f"[    1.1] {CLASSIFIER.PANIC_PREFIX} on unknown-block(0,0)\n"
            f"[    1.2] {CLASSIFIER.PANIC_END_PREFIX} "
            "on unknown-block(0,0) ]---",
            f"[    1.1] {CLASSIFIER.PANIC_END_PREFIX} "
            "on unknown-block(0,0) ]---\n"
            f"[    1.2] {CLASSIFIER.PANIC_PREFIX} on unknown-block(0,0)", 1),
    )
    rejected = 0
    for candidate in mutations:
        try:
            CLASSIFIER.classify_runtime(candidate, RELEASE, 124)
        except CLASSIFIER.ClassificationError:
            rejected += 1
        else:
            raise SystemExit("unsafe KUnit log mutation accepted")
    try:
        CLASSIFIER.classify_runtime(raw, RELEASE, 0)
    except CLASSIFIER.ClassificationError:
        rejected += 1
    else:
        raise SystemExit("unexpected QEMU exit accepted")
    print("validation=mainline-da921x-pre-p28-provider-abort-kunit-classifier")
    print("positive_cases=1")
    print(f"unsafe_runtime_mutations_rejected={rejected}")
    print(f"unsafe_package_manifest_mutations_rejected={manifest_rejected}")
    print("hardware_action=none")
    print("device_action=none")
    print("cpu8_cpu9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
