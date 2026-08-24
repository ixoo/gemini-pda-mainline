#!/usr/bin/env python3
"""Validate the generated A72 early-initcall ledger patch shape."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0362-pstore-add-Gemini-A72-early-initcall-ledger.patch"
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
            r"^Subject: \[PATCH 1/1\] pstore: add Gemini A72 early initcall ledger$",
            text,
            re.MULTILINE,
        ) is not None,
        "exact subject",
    )
    require("Signed-off-by:" not in text, "synthetic patch must not certify DCO")
    require("gemini-mainline@example.invalid" in text, "synthetic author identity")
    changed = set(re.findall(r"^diff --git a/(.+?) b/", text, re.MULTILINE))
    require(changed == FILES, "exact three-file boundary")
    for token in (
        "config PSTORE_GEMINI_A72_EARLY_INITCALL_LEDGER",
        "GEMINI_A72_EARLY_INIT_V1",
        "checkpoint=pure-init outcome=commit slot=1 crc32=03d9627f",
        "checkpoint=core-init outcome=commit slot=2 crc32=57dd63b5",
        "checkpoint=pure-init outcome=primary-refused slot=2",
        "pure_initcall(gemini_a72_pure_initcall_checkpoint)",
        "core_initcall(gemini_a72_core_initcall_checkpoint)",
        "gemini_a72_pure_refusal_checkpoint",
    ):
        require(token in text, f"patch token: {token}")
    added = "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    require(added.count("gemini_prb_write(slot, gemini_prb_refusal_record)") == 1,
            "one fallback writer call")
    require(added.count("return 0;") == 1,
            "one pure success return; observer reuses existing return")
    for forbidden in (
        "platform_driver_register(",
        "kvzalloc",
        "get_device(",
        "mt6797_a72_platform_state_snapshot(",
        "mt6797_a72_provider_snapshot(",
        "mt6797_dvfsp_clock_backend_read(",
        "mt6797_bigidvfs_backend_read(",
        "cpu_up(",
        "cpu_down(",
        "arm_smccc_smc(",
        "regmap_write(",
        "i2c_transfer(",
        "kernel_restart(",
        "orderly_poweroff(",
    ):
        require(forbidden not in added, f"forbidden added operation: {forbidden}")
    print("validation=a72-early-initcall-ledger-patch")
    print("patch_count=1")
    print("changed_files=3")
    print("retained_write_attempts_maximum=2")
    print("observer_registrations=0")
    print("result=pass")


if __name__ == "__main__":
    main()
