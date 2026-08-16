#!/usr/bin/env python3
"""Source-pin and derive the independent pre-ramoops candidate validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "18ce2c8a687abd1d54492b6025ba762c2af90b886debceba545be57b5546ddc3"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
SOURCE = REPO_ROOT / "experiments/2026-08-15-mainline-module-policy-control/scripts/test-candidate.py"


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"unsafe validator derivation: expected {count}, found {actual}: {old}"
        )
    return text.replace(old, new)


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: test-candidate.py --candidate DIR --package DIR --ramdisk FILE"
        )
    source = SOURCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise AssertionError("source validator identity changed")
    text = source.decode("utf-8")
    replacements = (
        ("module-policy candidate validator", "pre-ramoops ledger candidate validator"),
        ("DA921x module-policy serviceability control", "pre-ramoops stage-ledger candidate"),
        ("RAW_SIZE = 6_881_280", "RAW_SIZE = 6_877_184"),
        ("KERNEL_FIELD_SIZE = 4_802_756", "KERNEL_FIELD_SIZE = 4_799_033"),
        ("782850c4854e9454fc5c0ac22243b25233f7b4e6ebb5cecdf4d2872fd45ae040",
         "00455398cf1ffa3f57ad5083322e5541b0a58dbdec9ff63883b1427990cff8c3"),
        ("044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff",
         "ac849d9aca9454d5d6a29d25a67b5d27fcef94e16bb881f4d14db09d0d29d75f"),
        ("ca9d18d721916efa994a8e5623adc52f08a105b3676ada960077236f78e101df",
         "8fbd12d6494c72882daa6b4d49fe2596e38796561b83a6252133c8587c89db5c"),
        ("86cdcb5bec92aa8cd6d292e27f44df06e3cca78305862bbb5026b6c094174b7e",
         "c68da1d645c750f9d60c4ab067e70bf8da276273d60eca78b72b06e7b70741e4"),
        ("f65d2cf39070e8ba0427e8745bd8aa615869abf048698a18251c6c07a69d26b2",
         "9f93f48aec1e215b07d89d38d8e4a653b041a46a0df939d542cc11e7e65efbca"),
        ("7093fe54510224c1c4cbf83562a8d6650f6ac0b03fa71a2da19c81f7b3846b34",
         "9832806c73e8ae2b10f139bdac9bb4e11722df76bea216c2e49422ff496f4f7c"),
        ("bdd3bd798f2edc5f0936d3a05bf21c58a24b1fa6f424e62c47c34a1decf4cacf",
         "49b9c33a0dbb619e978b59bea22bfb89b2b884e4843d9236484a7f8520871812"),
        ("gemini-mt6797-da921x-module-policy-control.boot.img",
         "gemini-mt6797-pre-ramoops-ledger.boot.img"),
        (r'b\"gemini-modctl\"', r'b\"gemini-preledg\"'),
        ("09ba93dbe1aa462795f1a1f4f0e82e31f5392989",
         "ca56f0161f6d67900d0fc58719e9190e7d1bb4a3"),
        ("da921x-resource-only-provider-modules-control",
         "da921x-modules-pre-ramoops-ledger"),
        ("7.1.3-gemini-da921x-modctl", "7.1.3-gemini-preledger-a"),
        ("validation=da921x-module-policy-control-candidate",
         "validation=pre-ramoops-ledger-candidate"),
        ("runtime_marker=absent", "runtime_marker=four-stage-ledger-present"),
        (
            r'require(b\"da921x-observer-v1 event=bound\" not in image, \"observer marker leaked\")',
            r'require(b\"da921x-observer-v1 event=bound\" not in image, \"observer marker leaked\")\n'
            r'    require(b\"CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER=y\\n\" in config, \"ledger config absent\")\n'
            r'    require(b\"# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set\\n\" in config, \"post-ramoops config leaked\")\n'
            r'    for marker in (\n'
            r'        b\"stage=reserved-scan slot=171 crc32=45d42a00\",\n'
            r'        b\"stage=early-initcall slot=172 crc32=c1884938\",\n'
            r'        b\"stage=core-initcall slot=173 crc32=ba03bc4b\",\n'
            r'        b\"stage=postcore-initcall slot=174 crc32=b129c993\",\n'
            r'    ):\n'
            r'        require(image.count(marker) == 1, \"ledger marker not unique\")',
        ),
    )
    for replacement in replacements:
        text = replace_exact(text, *replacement)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=".pre-ramoops-ledger-", suffix=".py",
        dir=SCRIPT_DIR,
    ) as derived:
        derived.write(text)
        derived.flush()
        return subprocess.run([sys.executable, derived.name, *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
