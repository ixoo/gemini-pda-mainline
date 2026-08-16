#!/usr/bin/env python3
"""Source-pin and derive the independent arm64 entry-ledger validator."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile


SOURCE_SHA256 = "2f15976deadb6ff7598ae58227cf71ebde052d2758ea24ed32954916f7d8019c"
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent
SOURCE = REPO_ROOT / "experiments/2026-08-16-mainline-pre-ramoops-ledger/scripts/test-candidate.py"


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    actual = text.count(old)
    if actual != count:
        raise AssertionError(
            f"unsafe validator derivation: expected {count}, found {actual}: {old}"
        )
    return text.replace(old, new)


def validate_entry_ledger_inputs() -> None:
    try:
        package = Path(sys.argv[sys.argv.index("--package") + 1])
    except (ValueError, IndexError) as exc:
        raise AssertionError("--package is required") from exc
    config = (package / "kernel.config").read_bytes()
    image = (package / "Image").read_bytes()
    system_map = (package / "System.map").read_text(encoding="ascii")
    required_config = (
        b"CONFIG_MODULES=y\n",
        b"# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set\n",
        b"CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y\n",
        b"# CONFIG_PSTORE_GEMINI_POST_RAMOOPS_CHECKPOINT is not set\n",
    )
    for line in required_config:
        if line not in config:
            raise AssertionError(f"configuration gate missing: {line!r}")
    for marker in (
        b"GAEL-20260816-A E0",
        b"GAEL-20260816-A E1",
        b"GAEL-20260816-A E2",
        b"GAEL-20260816-A E3",
    ):
        if image.count(marker) != 1:
            raise AssertionError(f"entry-ledger marker not unique: {marker!r}")
    symbols: dict[str, int] = {}
    for line in system_map.splitlines():
        fields = line.split()
        if len(fields) == 3 and fields[2] in {
            "__idmap_text_start",
            "__idmap_text_end",
        }:
            symbols[fields[2]] = int(fields[0], 16)
    if symbols != {
        "__idmap_text_start": 0xFFFF8000808DE000,
        "__idmap_text_end": 0xFFFF8000808DEFB8,
    }:
        raise AssertionError("identity-map boundaries changed")
    if symbols["__idmap_text_end"] - symbols["__idmap_text_start"] != 0xFB8:
        raise AssertionError("identity-map size changed")


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit(
            "usage: test-candidate.py --candidate DIR --package DIR --ramdisk FILE"
        )
    source = SOURCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise AssertionError("source validator identity changed")
    validate_entry_ledger_inputs()
    text = source.decode("utf-8")
    replacements = (
        ("pre-ramoops candidate validator", "arm64 entry-ledger candidate validator"),
        ("pre-ramoops ledger candidate validator", "arm64 entry-ledger candidate validator"),
        ("pre-ramoops stage-ledger candidate", "arm64 entry four-stage ledger candidate"),
        ("RAW_SIZE = 6_877_184", "RAW_SIZE = 6_879_232"),
        ("KERNEL_FIELD_SIZE = 4_799_033", "KERNEL_FIELD_SIZE = 4_802_354"),
        ("00455398cf1ffa3f57ad5083322e5541b0a58dbdec9ff63883b1427990cff8c3",
         "1249d907795ab80c5a290887847e497bf672e5bdf2c7617096a1209db464341c"),
        ("ac849d9aca9454d5d6a29d25a67b5d27fcef94e16bb881f4d14db09d0d29d75f",
         "a81939b41a64a362744580bec559baecb3fe13938187f34b3f1b9ad5f09527f2"),
        ("8fbd12d6494c72882daa6b4d49fe2596e38796561b83a6252133c8587c89db5c",
         "37f3897cee5a7eb899273878938b3c98522a98dd2fac64d2f0f72235d2c10d84"),
        ("c68da1d645c750f9d60c4ab067e70bf8da276273d60eca78b72b06e7b70741e4",
         "539f83bf4e6f31e21edacde26399ea285c1e87cdf4df25fb2896d364822a89fe"),
        ("9f93f48aec1e215b07d89d38d8e4a653b041a46a0df939d542cc11e7e65efbca",
         "e622eb1a3acde5c8e351227e7044e34cd894091b2f3b9c210c37e42cced0b323"),
        ("9832806c73e8ae2b10f139bdac9bb4e11722df76bea216c2e49422ff496f4f7c",
         "dcdfb20bd9102c882366885ffb879885e58b8d88d73e9822a6049c9d5fc7d4ec"),
        ("49b9c33a0dbb619e978b59bea22bfb89b2b884e4843d9236484a7f8520871812",
         "88ab3409c4026f140cd4a8daa0682799a6e0420b50dd8b30010e14573017fcee"),
        ("gemini-mt6797-pre-ramoops-ledger.boot.img",
         "gemini-mt6797-arm64-entry-ledger.boot.img"),
        (r'b\"gemini-preledg\"', r'b\"gemini-entryled\"'),
        ("ca56f0161f6d67900d0fc58719e9190e7d1bb4a3",
         "98996fdfbf09f8de2a6b86e488defef22fcc7968"),
        ("da921x-modules-pre-ramoops-ledger",
         "da921x-modules-arm64-entry-ledger"),
        ("7.1.3-gemini-preledger-a", "7.1.3-gemini-entryled-a"),
        ("validation=pre-ramoops-ledger-candidate",
         "validation=arm64-entry-ledger-candidate"),
        ("runtime_marker=four-stage-ledger-present",
         "runtime_marker=four-stage-arm64-entry-ledger-present"),
        (r"CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER=y\\n",
         r"CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y\\n"),
        (r"stage=reserved-scan slot=171 crc32=45d42a00",
         r"GAEL-20260816-A E0"),
        (r"stage=early-initcall slot=172 crc32=c1884938",
         r"GAEL-20260816-A E1"),
        (r"stage=core-initcall slot=173 crc32=ba03bc4b",
         r"GAEL-20260816-A E2"),
        (r"stage=postcore-initcall slot=174 crc32=b129c993",
         r"GAEL-20260816-A E3"),
        (".pre-ramoops-ledger-", ".arm64-entry-ledger-"),
    )
    for replacement in replacements:
        text = replace_exact(text, *replacement)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", prefix=".arm64-entry-ledger-", suffix=".py",
        dir=SCRIPT_DIR,
    ) as derived:
        derived.write(text)
        derived.flush()
        return subprocess.run(
            [sys.executable, derived.name, *sys.argv[1:]], check=False
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
