#!/usr/bin/env python3
"""Prove that the B2 QEMU classifier rejects decision-changing logs."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("classify-kunit.py")
SPEC = importlib.util.spec_from_file_location("b2_kunit_classifier", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load classifier")
CLASSIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLASSIFIER)

RELEASE = "7.1.3-gemini-i2c6-write-kunit"


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
[    1.0]     1..12
{cases}
[    1.0] # {CLASSIFIER.SUITE}: pass:12 fail:0 skip:0 total:12
[    1.0] # Totals: pass:12 fail:0 skip:0 total:12
[    1.0] ok 1 {CLASSIFIER.SUITE}
[    1.1] {CLASSIFIER.PANIC_PREFIX} on unknown-block(0,0)
[    1.2] {CLASSIFIER.PANIC_END_PREFIX} on unknown-block(0,0) ]---
qemu-system-aarch64: terminating on signal 15
"""


def main() -> None:
    digest = "a" * 64
    manifest = f"{digest}  ./Image\n{'b' * 64}  ./kernel.config\n"
    with tempfile.TemporaryDirectory(prefix="gemini-b2-manifest-") as temporary:
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
    mutations = (
        raw.replace("ok 4 mtk_i2c_idvfs_timeout_classification\n", "", 1),
        raw.replace("ok 5 mtk_i2c_idvfs_nack_classification",
                    "not ok 5 mtk_i2c_idvfs_nack_classification", 1),
        raw.replace("pass:12 fail:0 skip:0 total:12",
                    "pass:11 fail:0 skip:1 total:12", 1),
        raw.replace("# Subtest: mtk-i2c-idvfs-write-contract",
                    "# Subtest: unexpected-suite", 1),
        raw.replace("ok 1 mtk_i2c_idvfs_exact_two_byte_fifo_plan",
                    "ok 1 wrong_case", 1),
        raw.replace(RELEASE, "7.1.3-wrong", 1),
        raw.replace(CLASSIFIER.PANIC_PREFIX,
                    "System halted", 1),
        raw.replace(
            f"[    1.2] {CLASSIFIER.PANIC_END_PREFIX} "
            "on unknown-block(0,0) ]---\n", "", 1),
        raw.replace(
            f"[    1.1] {CLASSIFIER.PANIC_PREFIX} "
            "on unknown-block(0,0)\n",
            f"[    1.1] {CLASSIFIER.PANIC_PREFIX} "
            "on unknown-block(0,0)\n"
            f"[    1.1] {CLASSIFIER.PANIC_PREFIX} "
            "on unknown-block(0,0)\n", 1),
        raw.replace(
            f"[    1.1] {CLASSIFIER.PANIC_PREFIX} "
            "on unknown-block(0,0)\n"
            f"[    1.2] {CLASSIFIER.PANIC_END_PREFIX} "
            "on unknown-block(0,0) ]---",
            f"[    1.1] {CLASSIFIER.PANIC_END_PREFIX} "
            "on unknown-block(0,0) ]---\n"
            f"[    1.2] {CLASSIFIER.PANIC_PREFIX} "
            "on unknown-block(0,0)", 1),
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
    print("validation=mainline-i2c6-write-transport-kunit-classifier")
    print("positive_cases=1")
    print(f"unsafe_runtime_mutations_rejected={rejected}")
    print(f"unsafe_package_manifest_mutations_rejected={manifest_rejected}")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
