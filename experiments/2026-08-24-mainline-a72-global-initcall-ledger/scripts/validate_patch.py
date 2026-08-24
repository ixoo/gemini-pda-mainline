#!/usr/bin/env python3
"""Validate the generated A72 global-initcall ledger patch shape."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


PATCH = "0361-pstore-add-Gemini-A72-global-initcall-ledger.patch"
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
            r"^Subject: \[PATCH 1/1\] pstore: add Gemini A72 global initcall ledger$",
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
        "config PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER",
        "GEMINI_A72_INITCALL_V1",
        "checkpoint=subsys-init slot=1 crc32=cf2a6946",
        "checkpoint=fs-init slot=2 crc32=91ac2a49",
        "subsys_initcall(gemini_a72_subsys_initcall_checkpoint)",
        "fs_initcall(gemini_a72_fs_initcall_checkpoint)",
        "CONFIG_PSTORE_GEMINI_A72_GLOBAL_INITCALL_LEDGER",
    ):
        require(token in text, f"patch token: {token}")
    added = "\n".join(
        line[1:]
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    require(added.count("return 0;") == 1,
            "one observer-registration suppression return")
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
    print("validation=a72-global-initcall-ledger-patch")
    print("patch_count=1")
    print("changed_files=3")
    print("observer_registrations=0")
    print("result=pass")


if __name__ == "__main__":
    main()
