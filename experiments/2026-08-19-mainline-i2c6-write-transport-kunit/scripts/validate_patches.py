#!/usr/bin/env python3
"""Validate the two normal format-patches generated for Gate-6 B2."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATCH_NAMES = (
    "0288-i2c-mediatek-factor-MT6797-short-write-contract.patch",
    "0289-i2c-mediatek-add-MT6797-short-write-contract-KUnit.patch",
)


class ValidationError(RuntimeError):
    """Raised when generated patches violate the B2 boundary."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def changed_paths(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"^diff --git a/(\S+) b/\S+$", text, re.MULTILINE))


def added_lines(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def validate(patch_dir: Path) -> None:
    actual = tuple(sorted(path.name for path in patch_dir.glob("*.patch")))
    require(actual == PATCH_NAMES, f"unexpected patch inventory: {actual}")
    production = (patch_dir / PATCH_NAMES[0]).read_text(encoding="utf-8")
    kunit = (patch_dir / PATCH_NAMES[1]).read_text(encoding="utf-8")

    for name, text in zip(PATCH_NAMES, (production, kunit), strict=True):
        require(text.startswith("From "), f"{name}: not a normal format-patch")
        require("From: Gemini Mainline Experiment <gemini-mainline@example.invalid>"
                in text, f"{name}: synthetic archive identity changed")
        require("Signed-off-by:" not in text,
                f"{name}: synthetic sign-off is forbidden")
        require("device_action=none" not in text,
                f"{name}: provenance text leaked into kernel patch")

    require("Subject: [PATCH 1/2] i2c: mediatek: factor MT6797 short-write contract"
            in production, "production subject changed")
    require("Subject: [PATCH 2/2] i2c: mediatek: add MT6797 short-write contract KUnit"
            in kunit, "KUnit subject changed")
    require(changed_paths(production) == (
        "drivers/i2c/busses/i2c-mt65xx-gemini-write-contract.h",
        "drivers/i2c/busses/i2c-mt65xx.c",
    ), "production patch path inventory changed")
    require(changed_paths(kunit) == (
        "drivers/i2c/busses/Kconfig",
        "drivers/i2c/busses/Makefile",
        "drivers/i2c/busses/i2c-mt65xx-gemini-write-test.c",
    ), "KUnit patch path inventory changed")

    production_added = added_lines(production)
    kunit_added = added_lines(kunit)
    for token in (
        "mtk_i2c_idvfs_plan_short_write",
        "mtk_i2c_idvfs_emit_short_write",
        "mtk_i2c_idvfs_completion_result",
        "mtk_i2c_idvfs_result_after_lease",
        "mtk_i2c_idvfs_transfer_once",
        "adap->retries = 0",
        "i2c_lock_bus(adap, I2C_LOCK_ROOT_ADAPTER)",
        "ret = __i2c_transfer(adap, msgs, num)",
        "i2c_unlock_bus(adap, I2C_LOCK_ROOT_ADAPTER)",
        "mtk_i2c_idvfs_result_after_lease(ret, lease_ret)",
    ):
        require(token in production_added,
                f"production addition missing: {token}")
    require(kunit_added.count("KUNIT_CASE(") == 12,
            "KUnit patch case count changed")
    for token in (
        "MTK_I2C_TEST_ADDR\t0x2a",
        "MTK_I2C_TEST_BYTE0\t0xa5",
        "MTK_I2C_TEST_BYTE1\t0x5a",
        "mtk_i2c_idvfs_no_retry_eagain",
        "fake.lock_calls, 1U",
        "fake.unlock_calls, 1U",
        "fake.locked_during",
        "fake.retries_during, 0U",
        "mtk_i2c_idvfs_lease_failure_overrides_success",
        "mtk_i2c_idvfs_transport_failure_retains_precedence",
    ):
        require(token in kunit_added, f"KUnit addition missing: {token}")
    for forbidden in (
        "0x68", "0x69", "0xda", "0x46", "i2c_add_adapter",
        "i2c_new_client", "ioremap", "module_param", "OFFSET_START",
        "I2C_TRANSAC_START", "writel(",
    ):
        require(forbidden not in kunit_added,
                f"KUnit additions contain forbidden token: {forbidden}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-dir", type=Path, required=True)
    args = parser.parse_args()
    patch_dir = args.patch_dir.resolve()
    validate(patch_dir)
    print("validation=mainline-i2c6-write-transport-format-patches")
    print("patches=2")
    print("changed_paths=5")
    print("synthetic_signoff=absent")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
