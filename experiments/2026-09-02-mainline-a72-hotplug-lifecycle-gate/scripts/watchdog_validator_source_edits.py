#!/usr/bin/env python3
"""Add a read-only exact-owner validator to the MTK recovery watchdog."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


HEADER_OLD = dedent("""\
    #ifdef CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER
    int mtk_wdt_recovery_takeover(struct device *dev, unsigned int timeout_ms,
    \t\t\t      struct mtk_wdt_recovery_result *result);
    #else
    static inline int
    mtk_wdt_recovery_takeover(struct device *dev, unsigned int timeout_ms,
    \t\t\t  struct mtk_wdt_recovery_result *result)
    {
    \t(void)dev;
    \t(void)timeout_ms;
    \tif (result)
    \t\t*result = (struct mtk_wdt_recovery_result){};
    \treturn -EOPNOTSUPP;
    }
    #endif
    """)


HEADER_NEW = dedent("""\
    struct mtk_wdt_recovery_validation {
    \tu64 identity;
    \tu32 mode;
    \tu32 length;
    \tu32 owned;
    };

    #ifdef CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER
    int mtk_wdt_recovery_takeover(struct device *dev, unsigned int timeout_ms,
    \t\t\t      struct mtk_wdt_recovery_result *result);
    int mtk_wdt_recovery_validate(
    \tstruct device *dev, u64 identity,
    \tstruct mtk_wdt_recovery_validation *validation);
    #else
    static inline int
    mtk_wdt_recovery_takeover(struct device *dev, unsigned int timeout_ms,
    \t\t\t  struct mtk_wdt_recovery_result *result)
    {
    \t(void)dev;
    \t(void)timeout_ms;
    \tif (result)
    \t\t*result = (struct mtk_wdt_recovery_result){};
    \treturn -EOPNOTSUPP;
    }

    static inline int mtk_wdt_recovery_validate(
    \tstruct device *dev, u64 identity,
    \tstruct mtk_wdt_recovery_validation *validation)
    {
    \t(void)dev;
    \t(void)identity;
    \tif (validation)
    \t\t*validation = (struct mtk_wdt_recovery_validation){};
    \treturn -EOPNOTSUPP;
    }
    #endif
    """)


VALIDATOR = dedent("""\
    static int mtk_wdt_recovery_validate_owner(
    \tconst struct mtk_wdt_recovery_owner *owner,
    \tconst struct mtk_wdt_recovery_register_ops *ops, void *context,
    \tu64 identity, struct mtk_wdt_recovery_validation *validation)
    {
    \tu32 expected_length;

    \tif (!validation)
    \t\treturn -EINVAL;
    \t*validation = (struct mtk_wdt_recovery_validation){};
    \tif (!owner || !ops || !ops->read || !identity)
    \t\treturn -EINVAL;
    \tif (!owner->owned)
    \t\treturn -ENODATA;
    \tvalidation->identity = owner->identity;
    \tvalidation->owned = 1;
    \tif (identity != owner->identity)
    \t\treturn -EACCES;

    \tvalidation->mode = ops->read(context, WDT_MODE);
    \tvalidation->length = ops->read(context, WDT_LENGTH);
    \texpected_length = WDT_LENGTH_TIMEOUT(
    \t\tMTK_WDT_RECOVERY_TIMEOUT_SECONDS << 6);
    \tif ((validation->length & WDT_LENGTH_TIMEOUT_MASK) !=
    \t    expected_length ||
    \t    (validation->mode & WDT_MODE_RECOVERY_MASK) !=
    \t\t    (WDT_MODE_EN | WDT_MODE_AUTO_START))
    \t\treturn -EIO;

    \treturn 0;
    }

    """)


PUBLIC_VALIDATOR = dedent("""\

    int mtk_wdt_recovery_validate(
    \tstruct device *dev, u64 identity,
    \tstruct mtk_wdt_recovery_validation *validation)
    {
    \tstruct mtk_wdt_dev *mtk_wdt;
    \tunsigned long flags;
    \tint ret;

    \tif (!validation)
    \t\treturn -EINVAL;
    \t*validation = (struct mtk_wdt_recovery_validation){};
    \tif (!dev || !identity)
    \t\treturn -EINVAL;
    \tmtk_wdt = dev_get_drvdata(dev);
    \tif (!mtk_wdt)
    \t\treturn -ENODEV;
    \tif (!mtk_wdt->recovery_supported)
    \t\treturn -EOPNOTSUPP;

    \tspin_lock_irqsave(&mtk_wdt->recovery_lock, flags);
    \tret = mtk_wdt_recovery_validate_owner(
    \t\t&mtk_wdt->recovery, &mtk_wdt_recovery_ops, mtk_wdt,
    \t\tidentity, validation);
    \tspin_unlock_irqrestore(&mtk_wdt->recovery_lock, flags);

    \treturn ret;
    }
    EXPORT_SYMBOL_GPL(mtk_wdt_recovery_validate);
    """)


TESTS = dedent("""\

    static void mtk_wdt_recovery_validate_success_test(struct kunit *test)
    {
    \tstruct mtk_wdt_recovery_test_context state = {
    \t\t.mode = WDT_MODE_EXRST_EN | WDT_MODE_EN |
    \t\t\tWDT_MODE_AUTO_START,
    \t\t.length = WDT_LENGTH_TIMEOUT(
    \t\t\tMTK_WDT_RECOVERY_TIMEOUT_SECONDS << 6),
    \t};
    \tstruct mtk_wdt_recovery_validation validation;
    \tstruct mtk_wdt_recovery_owner owner = {
    \t\t.owned = true,
    \t\t.identity = 31,
    \t};
    \tint ret;

    \tret = mtk_wdt_recovery_validate_owner(
    \t\t&owner, &mtk_wdt_recovery_test_ops, &state, 31,
    \t\t&validation);
    \tKUNIT_ASSERT_EQ(test, 0, ret);
    \tKUNIT_EXPECT_EQ(test, 31ULL, validation.identity);
    \tKUNIT_EXPECT_EQ(test, 1U, validation.owned);
    \tKUNIT_EXPECT_EQ(test, 2U, state.reads);
    \tKUNIT_EXPECT_EQ(test, 0U, state.writes);
    }

    static void mtk_wdt_recovery_validate_rejections_test(struct kunit *test)
    {
    \tstruct mtk_wdt_recovery_test_context state = {
    \t\t.mode = WDT_MODE_EN | WDT_MODE_AUTO_START,
    \t\t.length = WDT_LENGTH_TIMEOUT(
    \t\t\tMTK_WDT_RECOVERY_TIMEOUT_SECONDS << 6),
    \t};
    \tstruct mtk_wdt_recovery_validation validation;
    \tstruct mtk_wdt_recovery_owner owner = {
    \t\t.owned = true,
    \t\t.identity = 37,
    \t};
    \tint ret;

    \tret = mtk_wdt_recovery_validate_owner(
    \t\t&owner, &mtk_wdt_recovery_test_ops, &state, 0,
    \t\t&validation);
    \tKUNIT_EXPECT_EQ(test, -EINVAL, ret);
    \tret = mtk_wdt_recovery_validate_owner(
    \t\t&owner, &mtk_wdt_recovery_test_ops, &state, 38,
    \t\t&validation);
    \tKUNIT_EXPECT_EQ(test, -EACCES, ret);
    \tKUNIT_EXPECT_EQ(test, 0U, state.reads);
    \towner.owned = false;
    \tret = mtk_wdt_recovery_validate_owner(
    \t\t&owner, &mtk_wdt_recovery_test_ops, &state, 37,
    \t\t&validation);
    \tKUNIT_EXPECT_EQ(test, -ENODATA, ret);
    \tKUNIT_EXPECT_EQ(test, 0U, state.reads);
    \towner.owned = true;
    \tstate.mode |= WDT_MODE_IRQ_EN;
    \tret = mtk_wdt_recovery_validate_owner(
    \t\t&owner, &mtk_wdt_recovery_test_ops, &state, 37,
    \t\t&validation);
    \tKUNIT_EXPECT_EQ(test, -EIO, ret);
    \tKUNIT_EXPECT_EQ(test, 2U, state.reads);
    \tstate.reads = 0;
    \tstate.mode &= ~WDT_MODE_IRQ_EN;
    \tstate.length ^= BIT(5);
    \tret = mtk_wdt_recovery_validate_owner(
    \t\t&owner, &mtk_wdt_recovery_test_ops, &state, 37,
    \t\t&validation);
    \tKUNIT_EXPECT_EQ(test, -EIO, ret);
    \tKUNIT_EXPECT_EQ(test, 2U, state.reads);
    \tKUNIT_EXPECT_EQ(test, 0U, state.writes);
    }
    """)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    header = root / "include/linux/mtk_wdt.h"
    source = root / "drivers/watchdog/mtk_wdt.c"

    replace_once(header, HEADER_OLD, HEADER_NEW)
    replace_once(
        source,
        "static u32 mtk_wdt_recovery_read(void *context, u32 offset)\n",
        VALIDATOR +
        "static u32 mtk_wdt_recovery_read(void *context, u32 offset)\n",
    )
    replace_once(
        source,
        "EXPORT_SYMBOL_GPL(mtk_wdt_recovery_takeover);\n#endif\n",
        "EXPORT_SYMBOL_GPL(mtk_wdt_recovery_takeover);\n" +
        PUBLIC_VALIDATOR + "\n#endif\n",
    )
    replace_once(
        source,
        "\tunsigned int writes;\n\tu64 identity;\n",
        "\tunsigned int writes;\n\tunsigned int reads;\n\tu64 identity;\n",
    )
    replace_once(
        source,
        "\tstruct mtk_wdt_recovery_test_context *state = context;\n\n"
        "\tif (offset == WDT_LENGTH)\n",
        "\tstruct mtk_wdt_recovery_test_context *state = context;\n\n"
        "\tstate->reads++;\n\tif (offset == WDT_LENGTH)\n",
    )
    replace_once(
        source,
        "static struct kunit_case mtk_wdt_recovery_cases[] = {\n",
        TESTS + "\nstatic struct kunit_case mtk_wdt_recovery_cases[] = {\n",
    )
    replace_once(
        source,
        "\tKUNIT_CASE(mtk_wdt_recovery_mode_fault_test),\n\t{}\n",
        "\tKUNIT_CASE(mtk_wdt_recovery_mode_fault_test),\n"
        "\tKUNIT_CASE(mtk_wdt_recovery_validate_success_test),\n"
        "\tKUNIT_CASE(mtk_wdt_recovery_validate_rejections_test),\n\t{}\n",
    )
    print("watchdog_validator_source_edits=pass")


if __name__ == "__main__":
    main()
