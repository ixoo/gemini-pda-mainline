#!/usr/bin/env python3
"""Validate the generated pre-capture cleanup-label patch."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0359-soc-mediatek-fix-A72-pre-capture-cleanup-label.patch"
SOURCE = "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"


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
            r"^Subject: \[PATCH 1/1\] soc: mediatek: fix A72 pre-capture cleanup label$",
            text,
            re.MULTILINE,
        ) is not None,
        "exact subject",
    )
    require("Signed-off-by:" not in text, "synthetic patch must not certify DCO")
    require(
        re.findall(r"^diff --git a/(.+?) b/", text, re.MULTILINE) == [SOURCE],
        "one observer source file",
    )
    require(text.count("+put_bigidvfs:") == 1, "one cleanup label addition")
    require(
        text.count(
            "+#ifdef CONFIG_PSTORE_GEMINI_A72_PHYSICAL_SOURCE_PRECAPTURE_LEDGER"
        ) == 1 and text.count("+#endif") == 1,
        "label has one exact mode guard",
    )
    require("+\tput_device(" not in text and "-\tput_device(" not in text,
            "existing releases changed")
    print("validation=a72-physical-source-precapture-control-flow-fix-patch")
    print("changed_files=1")
    print("added_cleanup_labels=1")
    print("hardware_actions_changed=false")
    print("result=pass")


if __name__ == "__main__":
    main()
