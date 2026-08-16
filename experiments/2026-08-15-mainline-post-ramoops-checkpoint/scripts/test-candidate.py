#!/usr/bin/env python3
"""Source-pin and derive the independent post-ramoops candidate validator."""

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
        ("module-policy candidate validator", "post-ramoops candidate validator"),
        ("DA921x module-policy serviceability control", "post-ramoops checkpoint candidate"),
        ("KERNEL_FIELD_SIZE = 4_802_756", "KERNEL_FIELD_SIZE = 4_803_523"),
        ("782850c4854e9454fc5c0ac22243b25233f7b4e6ebb5cecdf4d2872fd45ae040",
         "e16405f0a9061e98898f7fac5312033d56b1ab2aec162673fbebac564672e788"),
        ("044461e57d207f5ddd6e68cc463ea3ee1dd65260c27afe5fd00730137d13a2ff",
         "ae6b354d51a9e5096b9f6f74ee9037c47ba026e00895e6f4c8028f15bc9bd348"),
        ("ca9d18d721916efa994a8e5623adc52f08a105b3676ada960077236f78e101df",
         "3fa0d577fc953544b8dcd3a76720c18973ec6942120bdaf441d238d486ae4d6c"),
        ("86cdcb5bec92aa8cd6d292e27f44df06e3cca78305862bbb5026b6c094174b7e",
         "89ebdafc9c7360900d341787dc9f63884b51ecfc2919563b7f058f471723ccd6"),
        ("f65d2cf39070e8ba0427e8745bd8aa615869abf048698a18251c6c07a69d26b2",
         "be742f54afc6a3ac3f1622589c98d68f3904cd8f0b8191236d1da1017413b112"),
        ("7093fe54510224c1c4cbf83562a8d6650f6ac0b03fa71a2da19c81f7b3846b34",
         "bbb63ccfd6486483dedfd5190a4db666eb1202bd22fa1a0ef2da8b4f383a5ad9"),
        ("bdd3bd798f2edc5f0936d3a05bf21c58a24b1fa6f424e62c47c34a1decf4cacf",
         "ccbc30998640777f99f296cb5ee57ca9e391b566e04cdec3a98e3b19d7d64a3c"),
        ("gemini-mt6797-da921x-module-policy-control.boot.img",
         "gemini-mt6797-post-ramoops-checkpoint.boot.img", 1),
        (r'b\"gemini-modctl\"', r'b\"gemini-postram\"'),
        ("09ba93dbe1aa462795f1a1f4f0e82e31f5392989",
         "cac458c1cbd228390b94f2ae7154db34160adac2"),
        ("da921x-resource-only-provider-modules-control",
         "da921x-modules-post-ramoops-checkpoint"),
        ("7.1.3-gemini-da921x-modctl", "7.1.3-gemini-postram-a"),
        ("validation=da921x-module-policy-control-candidate",
         "validation=post-ramoops-checkpoint-candidate"),
        ("runtime_marker=absent", "runtime_marker=post-ramoops-present"),
        (
            r'require(b\"da921x-observer-v1 event=bound\" not in image, \"observer marker leaked\")',
            r'require(b\"da921x-observer-v1 event=bound\" not in image, \"observer marker leaked\")\n'
            r'    require(b\"CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT=y\\n\" in config, \"checkpoint config absent\")\n'
            r'    require(image.count(b\"GEMINI_MAINLINE_POST_RAMOOPS_20260815_A\") == 1, \"checkpoint marker not unique\")',
        ),
    )
    for replacement in replacements:
        text = replace_exact(text, *replacement)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=".post-ramoops-checkpoint-", suffix=".py",
        dir=SCRIPT_DIR,
    ) as derived:
        derived.write(text)
        derived.flush()
        return subprocess.run([sys.executable, derived.name, *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
