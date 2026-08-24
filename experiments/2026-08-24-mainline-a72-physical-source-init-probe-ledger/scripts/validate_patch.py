#!/usr/bin/env python3
"""Validate the generated A72 observer init/probe ledger patch shape."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0360-soc-mediatek-move-A72-ledger-before-registration.patch"
FILES = {
    "fs/pstore/Kconfig",
    "fs/pstore/gemini_protected_readback_ledger.c",
    "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    patch_dir = parser.parse_args().patch_dir.resolve()
    patches = sorted(path for path in patch_dir.iterdir() if path.suffix == ".patch")
    require([path.name for path in patches] == [PATCH], "one exact patch")
    text = patches[0].read_text(encoding="utf-8")
    require(
        re.search(
            r"^Subject: \[PATCH 1/1\] soc: mediatek: move A72 ledger before registration$",
            text,
            re.MULTILINE,
        )
        is not None,
        "exact subject",
    )
    require("Signed-off-by:" not in text, "synthetic patch must not certify DCO")
    require("gemini-mainline@example.invalid" in text, "synthetic author identity")
    changed = set(re.findall(r"^diff --git a/(.+?) b/", text, re.MULTILINE))
    require(changed == FILES, "exact three-file boundary")
    for token in (
        "GEMINI_A72_INIT_PROBE_V1",
        "checkpoint=driver-init slot=1 crc32=85e5f336",
        "checkpoint=probe-enter slot=2 crc32=85116721",
        "static int __init mt6797_a72_physical_source_init(void)",
        "device_initcall(mt6797_a72_physical_source_init)",
        "init/probe ledger complete; source lookup disabled",
    ):
        require(token in text, f"patch token: {token}")
    for forbidden in (
        "cpu_up(",
        "cpu_down(",
        "arm_smccc_smc(",
        "regmap_write(",
        "i2c_transfer(",
        "kernel_restart(",
    ):
        require(forbidden not in text, f"forbidden operation: {forbidden}")
    print("validation=a72-physical-source-init-probe-patch")
    print("patch_count=1")
    print("changed_files=3")
    print("result=pass")


if __name__ == "__main__":
    main()
