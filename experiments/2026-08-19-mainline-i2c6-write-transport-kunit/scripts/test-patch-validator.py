#!/usr/bin/env python3
"""Exercise the B2 normal-patch validator and unsafe patch mutations."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_patches.py")
SPEC = importlib.util.spec_from_file_location("b2_patch_validator", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load patch validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def production_patch() -> str:
    additions = (
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
    )
    body = "\n".join(f"+{token}" for token in additions)
    return f"""\
From 1111111111111111111111111111111111111111 Mon Sep 17 00:00:00 2001
From: Gemini Mainline Experiment <gemini-mainline@example.invalid>
Subject: [PATCH 1/2] i2c: mediatek: factor MT6797 short-write contract

---
diff --git a/drivers/i2c/busses/i2c-mt65xx-gemini-write-contract.h b/drivers/i2c/busses/i2c-mt65xx-gemini-write-contract.h
--- /dev/null
+++ b/drivers/i2c/busses/i2c-mt65xx-gemini-write-contract.h
@@
+contract
diff --git a/drivers/i2c/busses/i2c-mt65xx.c b/drivers/i2c/busses/i2c-mt65xx.c
--- a/drivers/i2c/busses/i2c-mt65xx.c
+++ b/drivers/i2c/busses/i2c-mt65xx.c
@@
{body}
"""


def kunit_patch() -> str:
    cases = "\n".join(f"+KUNIT_CASE(case_{index})," for index in range(12))
    tokens = "\n".join(f"+{token}" for token in (
        "#define MTK_I2C_TEST_ADDR\t0x2a",
        "#define MTK_I2C_TEST_BYTE0\t0xa5",
        "#define MTK_I2C_TEST_BYTE1\t0x5a",
        "mtk_i2c_idvfs_no_retry_eagain",
        "fake.lock_calls, 1U",
        "fake.unlock_calls, 1U",
        "fake.locked_during",
        "fake.retries_during, 0U",
        "mtk_i2c_idvfs_lease_failure_overrides_success",
        "mtk_i2c_idvfs_transport_failure_retains_precedence",
    ))
    return f"""\
From 2222222222222222222222222222222222222222 Mon Sep 17 00:00:00 2001
From: Gemini Mainline Experiment <gemini-mainline@example.invalid>
Subject: [PATCH 2/2] i2c: mediatek: add MT6797 short-write contract KUnit

---
diff --git a/drivers/i2c/busses/Kconfig b/drivers/i2c/busses/Kconfig
--- a/drivers/i2c/busses/Kconfig
+++ b/drivers/i2c/busses/Kconfig
@@
+config I2C_MT65XX_GEMINI_WRITE_TRANSPORT_KUNIT_TEST
diff --git a/drivers/i2c/busses/Makefile b/drivers/i2c/busses/Makefile
--- a/drivers/i2c/busses/Makefile
+++ b/drivers/i2c/busses/Makefile
@@
+obj-test
diff --git a/drivers/i2c/busses/i2c-mt65xx-gemini-write-test.c b/drivers/i2c/busses/i2c-mt65xx-gemini-write-test.c
--- /dev/null
+++ b/drivers/i2c/busses/i2c-mt65xx-gemini-write-test.c
@@
{tokens}
{cases}
"""


def validate_pair(production: str, kunit: str,
                  extra: dict[str, str] | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="gemini-b2-patch-test.") as tmp:
        root = Path(tmp)
        (root / VALIDATOR.PATCH_NAMES[0]).write_text(
            production, encoding="utf-8")
        (root / VALIDATOR.PATCH_NAMES[1]).write_text(kunit, encoding="utf-8")
        for name, text in (extra or {}).items():
            (root / name).write_text(text, encoding="utf-8")
        VALIDATOR.validate(root)


def main() -> None:
    production = production_patch()
    kunit = kunit_patch()
    validate_pair(production, kunit)
    mutations = (
        (production.replace("gemini-mainline@example.invalid",
                            "wrong@example.invalid", 1), kunit, None),
        (production.replace("Subject: [PATCH 1/2]", "Subject: [PATCH]", 1),
         kunit, None),
        (production.replace("---\n", "Signed-off-by: Synthetic <nobody@example.invalid>\n---\n", 1),
         kunit, None),
        (production.replace("+mtk_i2c_idvfs_transfer_once\n", "", 1),
         kunit, None),
        (production, kunit.replace("+KUNIT_CASE(case_11),\n", "", 1), None),
        (production, kunit + "+0x68\n", None),
        (production, kunit + "+writel(value, OFFSET_START);\n", None),
        (production +
         "diff --git a/drivers/i2c/busses/unexpected.c b/drivers/i2c/busses/unexpected.c\n",
         kunit, None),
        (production, kunit, {"9999-extra.patch": production}),
    )
    rejected = 0
    for changed_production, changed_kunit, extra in mutations:
        try:
            validate_pair(changed_production, changed_kunit, extra)
        except VALIDATOR.ValidationError:
            rejected += 1
        else:
            raise SystemExit("unsafe normal-patch mutation accepted")
    print("validation=mainline-i2c6-write-transport-format-patch-validator")
    print("positive_cases=1")
    print(f"unsafe_patch_mutations_rejected={rejected}")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
