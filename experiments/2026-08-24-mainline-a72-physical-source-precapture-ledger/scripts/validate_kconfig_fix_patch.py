#!/usr/bin/env python3
"""Validate the generated pre-capture Kconfig fix patch."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0358-pstore-fix-A72-pre-capture-ledger-dependency.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    patch_dir = parser.parse_args().patch_dir.resolve()
    patches = sorted(path for path in patch_dir.iterdir() if path.suffix == ".patch")
    require([path.name for path in patches] == [PATCH], "one exact fix patch")
    text = patches[0].read_text(encoding="utf-8")
    require(
        re.search(
            r"^Subject: \[PATCH 1/1\] pstore: fix A72 pre-capture ledger dependency$",
            text,
            re.MULTILINE,
        )
        is not None,
        "exact subject",
    )
    require("Signed-off-by:" not in text, "synthetic patch must not certify DCO")
    require(
        re.findall(r"^diff --git a/(.+?) b/", text, re.MULTILINE)
        == ["fs/pstore/Kconfig"],
        "one Kconfig file",
    )
    removed = (
        "-\tdepends on "
        "!PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"
    )
    require(text.count(removed) == 1, "one reverse dependency deletion")
    require("drivers/" not in text and "gemini_protected_readback_ledger.c" not in text,
            "runtime source changed")
    print("validation=a72-physical-source-precapture-kconfig-fix-patch")
    print("changed_files=1")
    print("runtime_source_changed=false")
    print("result=pass")


if __name__ == "__main__":
    main()
