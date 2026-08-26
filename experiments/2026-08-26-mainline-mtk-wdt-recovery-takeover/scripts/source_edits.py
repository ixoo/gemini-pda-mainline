#!/usr/bin/env python3
"""Apply deterministic MT6797 watchdog recovery-takeover edits."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


PRODUCTION_KCONFIG = dedent("""\
    config MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER
    \tbool "MediaTek MT6797 one-shot recovery watchdog takeover"
    \tdepends on ARM64 && ARCH_MEDIATEK
    \tdepends on OF
    \tdepends on WATCHDOG=y && MEDIATEK_WATCHDOG=y
    \tdefault n
    \thelp
    \t  Add a private MT6797-only API that irreversibly takes ownership of
    \t  the TOPRGU watchdog for one exact 15-second reset deadline. After
    \t  takeover, ordinary ping, timeout, pretimeout, start, and stop calls
    \t  are rejected before MMIO so no kicker can extend the deadline.

    \t  This option adds no caller, trigger, CPU operation, retained-memory
    \t  write, or boot policy. If unsure, say N.

    """)

TEST_KCONFIG = dedent("""\
    config MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER_KUNIT_TEST
    \tbool "KUnit tests for MediaTek watchdog recovery takeover"
    \tdepends on KUNIT=y
    \tdepends on MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER=y
    \tdefault n
    \thelp
    \t  Test exact write order, invalid-input refusal, one-shot ownership,
    \t  and retained ownership after length or mode readback mismatch with an
    \t  in-memory register transport. No watchdog MMIO or timer is used.

    \t  If unsure, say N.

    """)

HEADER_BLOCK = dedent("""\
    #define MTK_WDT_RECOVERY_TIMEOUT_MS 15000U

    struct mtk_wdt_recovery_result {
    \tu64 identity;
    \tu32 mode_before;
    \tu32 mode_after;
    \tu32 length_after;
    \tu32 owned;
    };

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

RECOVERY_TYPES = dedent("""\
    #if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER)
    struct mtk_wdt_recovery_owner {
    \tbool owned;
    \tu64 identity;
    };

    struct mtk_wdt_recovery_register_ops {
    \tu32 (*read)(void *context, u32 offset);
    \tvoid (*write)(void *context, u32 offset, u32 value);
    \tu64 (*next_identity)(void *context);
    };

    static atomic64_t mtk_wdt_recovery_identity = ATOMIC64_INIT(0);
    #endif

    """)

RECOVERY_IMPLEMENTATION = dedent("""\
    #if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER)
    static int
    mtk_wdt_recovery_execute(struct mtk_wdt_recovery_owner *owner,
    \t\t\t const struct mtk_wdt_recovery_register_ops *ops,
    \t\t\t void *context, unsigned int timeout_ms,
    \t\t\t struct mtk_wdt_recovery_result *result)
    {
    \tu32 length;
    \tu32 mode;

    \tif (!result)
    \t\treturn -EINVAL;
    \t*result = (struct mtk_wdt_recovery_result){};
    \tif (!owner || !ops || !ops->read || !ops->write ||
    \t    !ops->next_identity || timeout_ms != MTK_WDT_RECOVERY_TIMEOUT_MS)
    \t\treturn -EINVAL;
    \tif (owner->owned) {
    \t\tresult->identity = owner->identity;
    \t\tresult->owned = 1;
    \t\treturn -EALREADY;
    \t}

    \tresult->mode_before = ops->read(context, WDT_MODE);
    \towner->identity = ops->next_identity(context);
    \tif (!owner->identity)
    \t\treturn -EOVERFLOW;

    \towner->owned = true;
    \tresult->identity = owner->identity;
    \tresult->owned = 1;
    \tlength = WDT_LENGTH_TIMEOUT(MTK_WDT_RECOVERY_TIMEOUT_SECONDS << 6);
    \tmode = result->mode_before & ~(WDT_MODE_IRQ_EN | WDT_MODE_DUAL_EN);
    \tmode |= WDT_MODE_EN | WDT_MODE_AUTO_START;
    \tops->write(context, WDT_LENGTH, length | WDT_LENGTH_KEY);
    \tops->write(context, WDT_MODE, mode | WDT_MODE_KEY);
    \tops->write(context, WDT_RST, WDT_RST_RELOAD);
    \tresult->length_after = ops->read(context, WDT_LENGTH);
    \tresult->mode_after = ops->read(context, WDT_MODE);

    \tif ((result->length_after & WDT_LENGTH_TIMEOUT_MASK) != length ||
    \t    (result->mode_after & WDT_MODE_RECOVERY_MASK) !=
    \t\t    (WDT_MODE_EN | WDT_MODE_AUTO_START))
    \t\treturn -EIO;

    \treturn 0;
    }

    static u32 mtk_wdt_recovery_read(void *context, u32 offset)
    {
    \tstruct mtk_wdt_dev *mtk_wdt = context;

    \treturn ioread32(mtk_wdt->wdt_base + offset);
    }

    static void mtk_wdt_recovery_write(void *context, u32 offset, u32 value)
    {
    \tstruct mtk_wdt_dev *mtk_wdt = context;

    \tiowrite32(value, mtk_wdt->wdt_base + offset);
    }

    static u64 mtk_wdt_recovery_next_identity(void *context)
    {
    \tu64 identity;

    \t(void)context;
    \tidentity = (u64)atomic64_inc_return(&mtk_wdt_recovery_identity);
    \tif (!identity)
    \t\tidentity = (u64)atomic64_inc_return(&mtk_wdt_recovery_identity);
    \treturn identity;
    }

    static const struct mtk_wdt_recovery_register_ops
    mtk_wdt_recovery_ops = {
    \t.read = mtk_wdt_recovery_read,
    \t.write = mtk_wdt_recovery_write,
    \t.next_identity = mtk_wdt_recovery_next_identity,
    };

    int mtk_wdt_recovery_takeover(struct device *dev, unsigned int timeout_ms,
    \t\t\t      struct mtk_wdt_recovery_result *result)
    {
    \tstruct mtk_wdt_dev *mtk_wdt;
    \tunsigned long flags;
    \tint ret;

    \tif (!result)
    \t\treturn -EINVAL;
    \t*result = (struct mtk_wdt_recovery_result){};
    \tif (!dev)
    \t\treturn -EINVAL;
    \tmtk_wdt = dev_get_drvdata(dev);
    \tif (!mtk_wdt)
    \t\treturn -ENODEV;
    \tif (!mtk_wdt->recovery_supported)
    \t\treturn -EOPNOTSUPP;

    \tspin_lock_irqsave(&mtk_wdt->recovery_lock, flags);
    \tret = mtk_wdt_recovery_execute(&mtk_wdt->recovery,
    \t\t\t\t       &mtk_wdt_recovery_ops, mtk_wdt,
    \t\t\t\t       timeout_ms, result);
    \tif (result->owned) {
    \t\tmtk_wdt->wdt_dev.timeout = MTK_WDT_RECOVERY_TIMEOUT_SECONDS;
    \t\tmtk_wdt->wdt_dev.pretimeout = 0;
    \t\tset_bit(WDOG_HW_RUNNING, &mtk_wdt->wdt_dev.status);
    \t}
    \tspin_unlock_irqrestore(&mtk_wdt->recovery_lock, flags);

    \treturn ret;
    }
    EXPORT_SYMBOL_GPL(mtk_wdt_recovery_takeover);
    #endif

    static int mtk_wdt_mutation_begin(struct mtk_wdt_dev *mtk_wdt,
    \t\t\t\t  unsigned long *flags)
    {
    #if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER)
    \tspin_lock_irqsave(&mtk_wdt->recovery_lock, *flags);
    \tif (mtk_wdt->recovery.owned) {
    \t\tspin_unlock_irqrestore(&mtk_wdt->recovery_lock, *flags);
    \t\treturn -EBUSY;
    \t}
    #else
    \t(void)mtk_wdt;
    \t*flags = 0;
    #endif
    \treturn 0;
    }

    static void mtk_wdt_mutation_end(struct mtk_wdt_dev *mtk_wdt,
    \t\t\t\t unsigned long flags)
    {
    #if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER)
    \tspin_unlock_irqrestore(&mtk_wdt->recovery_lock, flags);
    #else
    \t(void)mtk_wdt;
    \t(void)flags;
    #endif
    }

    """)

WATCHDOG_OPS = dedent("""\
    static void mtk_wdt_ping_unlocked(struct mtk_wdt_dev *mtk_wdt)
    {
    \tiowrite32(WDT_RST_RELOAD, mtk_wdt->wdt_base + WDT_RST);
    }

    static int mtk_wdt_ping(struct watchdog_device *wdt_dev)
    {
    \tstruct mtk_wdt_dev *mtk_wdt = watchdog_get_drvdata(wdt_dev);
    \tunsigned long flags;
    \tint ret;

    \tret = mtk_wdt_mutation_begin(mtk_wdt, &flags);
    \tif (ret)
    \t\treturn ret;
    \tmtk_wdt_ping_unlocked(mtk_wdt);
    \tmtk_wdt_mutation_end(mtk_wdt, flags);
    \treturn 0;
    }

    static void mtk_wdt_set_timeout_unlocked(struct watchdog_device *wdt_dev,
    \t\t\t\t\t unsigned int timeout)
    {
    \tstruct mtk_wdt_dev *mtk_wdt = watchdog_get_drvdata(wdt_dev);
    \tu32 reg;

    \twdt_dev->timeout = timeout;
    \t/*
    \t * In dual mode, irq will be triggered at timeout / 2
    \t * the real timeout occurs at timeout
    \t */
    \tif (wdt_dev->pretimeout)
    \t\twdt_dev->pretimeout = timeout / 2;

    \t/*
    \t * One bit is the value of 512 ticks
    \t * The clock has 32 KHz
    \t */
    \treg = WDT_LENGTH_TIMEOUT((timeout - wdt_dev->pretimeout) << 6)
    \t\t\t| WDT_LENGTH_KEY;
    \tiowrite32(reg, mtk_wdt->wdt_base + WDT_LENGTH);
    \tmtk_wdt_ping_unlocked(mtk_wdt);
    }

    static int mtk_wdt_set_timeout(struct watchdog_device *wdt_dev,
    \t\t\t       unsigned int timeout)
    {
    \tstruct mtk_wdt_dev *mtk_wdt = watchdog_get_drvdata(wdt_dev);
    \tunsigned long flags;
    \tint ret;

    \tret = mtk_wdt_mutation_begin(mtk_wdt, &flags);
    \tif (ret)
    \t\treturn ret;
    \tmtk_wdt_set_timeout_unlocked(wdt_dev, timeout);
    \tmtk_wdt_mutation_end(mtk_wdt, flags);
    \treturn 0;
    }

    """)

STOP_START_PRETIMEOUT = dedent("""\
    static int mtk_wdt_stop(struct watchdog_device *wdt_dev)
    {
    \tstruct mtk_wdt_dev *mtk_wdt = watchdog_get_drvdata(wdt_dev);
    \tunsigned long flags;
    \tu32 reg;
    \tint ret;

    \tret = mtk_wdt_mutation_begin(mtk_wdt, &flags);
    \tif (ret)
    \t\treturn ret;
    \treg = readl(mtk_wdt->wdt_base + WDT_MODE);
    \treg &= ~WDT_MODE_EN;
    \treg |= WDT_MODE_KEY;
    \tiowrite32(reg, mtk_wdt->wdt_base + WDT_MODE);
    \tmtk_wdt_mutation_end(mtk_wdt, flags);
    \treturn 0;
    }

    static int mtk_wdt_start(struct watchdog_device *wdt_dev)
    {
    \tstruct mtk_wdt_dev *mtk_wdt = watchdog_get_drvdata(wdt_dev);
    \tunsigned long flags;
    \tu32 reg;
    \tint ret;

    \tret = mtk_wdt_mutation_begin(mtk_wdt, &flags);
    \tif (ret)
    \t\treturn ret;
    \tmtk_wdt_set_timeout_unlocked(wdt_dev, wdt_dev->timeout);
    \treg = ioread32(mtk_wdt->wdt_base + WDT_MODE);
    \tif (wdt_dev->pretimeout)
    \t\treg |= WDT_MODE_IRQ_EN | WDT_MODE_DUAL_EN;
    \telse
    \t\treg &= ~(WDT_MODE_IRQ_EN | WDT_MODE_DUAL_EN);
    \tif (mtk_wdt->disable_wdt_extrst)
    \t\treg &= ~WDT_MODE_EXRST_EN;
    \tif (mtk_wdt->reset_by_toprgu)
    \t\treg |= WDT_MODE_CNT_SEL;
    \tif (mtk_wdt->use_auto_restart)
    \t\treg |= WDT_MODE_AUTO_START;
    \treg |= WDT_MODE_EN | WDT_MODE_KEY;
    \tiowrite32(reg, mtk_wdt->wdt_base + WDT_MODE);
    \tmtk_wdt_mutation_end(mtk_wdt, flags);
    \treturn 0;
    }

    static int mtk_wdt_set_pretimeout(struct watchdog_device *wdd,
    \t\t\t\t  unsigned int timeout)
    {
    \tstruct mtk_wdt_dev *mtk_wdt = watchdog_get_drvdata(wdd);
    \tunsigned long flags;
    \tu32 reg;
    \tint ret;

    \tret = mtk_wdt_mutation_begin(mtk_wdt, &flags);
    \tif (ret)
    \t\treturn ret;
    \treg = ioread32(mtk_wdt->wdt_base + WDT_MODE);
    \tif (timeout && !wdd->pretimeout) {
    \t\twdd->pretimeout = wdd->timeout / 2;
    \t\treg |= WDT_MODE_IRQ_EN | WDT_MODE_DUAL_EN;
    \t} else if (!timeout && wdd->pretimeout) {
    \t\twdd->pretimeout = 0;
    \t\treg &= ~(WDT_MODE_IRQ_EN | WDT_MODE_DUAL_EN);
    \t} else {
    \t\tmtk_wdt_mutation_end(mtk_wdt, flags);
    \t\treturn 0;
    \t}

    \treg |= WDT_MODE_KEY;
    \tiowrite32(reg, mtk_wdt->wdt_base + WDT_MODE);
    \tmtk_wdt_set_timeout_unlocked(wdd, wdd->timeout);
    \tmtk_wdt_mutation_end(mtk_wdt, flags);
    \treturn 0;
    }

    """)

TEST_SOURCE = dedent("""\
    #if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER_KUNIT_TEST)
    #define MTK_WDT_RECOVERY_TEST_WRITES 3

    struct mtk_wdt_recovery_test_context {
    \tu32 mode;
    \tu32 length;
    \tu32 write_offset[MTK_WDT_RECOVERY_TEST_WRITES];
    \tu32 write_value[MTK_WDT_RECOVERY_TEST_WRITES];
    \tunsigned int writes;
    \tu64 identity;
    \tbool corrupt_length;
    \tbool corrupt_mode;
    };

    static u32 mtk_wdt_recovery_test_read(void *context, u32 offset)
    {
    \tstruct mtk_wdt_recovery_test_context *state = context;

    \tif (offset == WDT_LENGTH)
    \t\treturn state->length ^
    \t\t\t(state->corrupt_length && state->writes ? BIT(5) : 0);
    \tif (offset == WDT_MODE)
    \t\treturn state->mode ^
    \t\t\t(state->corrupt_mode && state->writes ? WDT_MODE_IRQ_EN : 0);
    \treturn 0;
    }

    static void mtk_wdt_recovery_test_write(void *context, u32 offset, u32 value)
    {
    \tstruct mtk_wdt_recovery_test_context *state = context;

    \tif (state->writes < MTK_WDT_RECOVERY_TEST_WRITES) {
    \t\tstate->write_offset[state->writes] = offset;
    \t\tstate->write_value[state->writes] = value;
    \t}
    \tstate->writes++;
    \tif (offset == WDT_LENGTH)
    \t\tstate->length = value & ~WDT_LENGTH_KEY;
    \telse if (offset == WDT_MODE)
    \t\tstate->mode = value & ~WDT_MODE_KEY;
    }

    static u64 mtk_wdt_recovery_test_identity(void *context)
    {
    \tstruct mtk_wdt_recovery_test_context *state = context;

    \treturn state->identity;
    }

    static const struct mtk_wdt_recovery_register_ops
    mtk_wdt_recovery_test_ops = {
    \t.read = mtk_wdt_recovery_test_read,
    \t.write = mtk_wdt_recovery_test_write,
    \t.next_identity = mtk_wdt_recovery_test_identity,
    };

    static void mtk_wdt_recovery_success_test(struct kunit *test)
    {
    \tstruct mtk_wdt_recovery_test_context state = {
    \t\t.mode = WDT_MODE_IRQ_EN | WDT_MODE_DUAL_EN |
    \t\t\tWDT_MODE_EXRST_EN | WDT_MODE_CNT_SEL,
    \t\t.identity = 41,
    \t};
    \tstruct mtk_wdt_recovery_result result;
    \tstruct mtk_wdt_recovery_owner owner = {};
    \tu32 expected_length;

    \tKUNIT_ASSERT_EQ(test, 0,
    \t\tmtk_wdt_recovery_execute(&owner, &mtk_wdt_recovery_test_ops,
    \t\t\t\t\t &state,
    \t\t\t\t\t MTK_WDT_RECOVERY_TIMEOUT_MS,
    \t\t\t\t\t &result));
    \texpected_length = WDT_LENGTH_TIMEOUT(
    \t\tMTK_WDT_RECOVERY_TIMEOUT_SECONDS << 6);
    \tKUNIT_EXPECT_TRUE(test, owner.owned);
    \tKUNIT_EXPECT_EQ(test, 41ULL, owner.identity);
    \tKUNIT_EXPECT_EQ(test, 1U, result.owned);
    \tKUNIT_EXPECT_EQ(test, 41ULL, result.identity);
    \tKUNIT_EXPECT_EQ(test, 3U, state.writes);
    \tKUNIT_EXPECT_EQ(test, (u32)WDT_LENGTH, state.write_offset[0]);
    \tKUNIT_EXPECT_EQ(test, (u32)WDT_MODE, state.write_offset[1]);
    \tKUNIT_EXPECT_EQ(test, (u32)WDT_RST, state.write_offset[2]);
    \tKUNIT_EXPECT_EQ(test, expected_length,
    \t\t\tstate.write_value[0] & WDT_LENGTH_TIMEOUT_MASK);
    \tKUNIT_EXPECT_EQ(test, (u32)WDT_RST_RELOAD, state.write_value[2]);
    \tKUNIT_EXPECT_EQ(test, WDT_MODE_EXRST_EN | WDT_MODE_CNT_SEL |
    \t\t\tWDT_MODE_EN | WDT_MODE_AUTO_START,
    \t\t\tresult.mode_after);
    }

    static void mtk_wdt_recovery_rejections_test(struct kunit *test)
    {
    \tstruct mtk_wdt_recovery_test_context state = { .identity = 7 };
    \tstruct mtk_wdt_recovery_result result;
    \tstruct mtk_wdt_recovery_owner owner = {};

    \tKUNIT_EXPECT_EQ(test, -EINVAL,
    \t\tmtk_wdt_recovery_execute(&owner, &mtk_wdt_recovery_test_ops,
    \t\t\t\t\t &state,
    \t\t\t\t\t MTK_WDT_RECOVERY_TIMEOUT_MS - 1,
    \t\t\t\t\t &result));
    \tKUNIT_EXPECT_EQ(test, 0U, state.writes);
    \tstate.identity = 0;
    \tKUNIT_EXPECT_EQ(test, -EOVERFLOW,
    \t\tmtk_wdt_recovery_execute(&owner, &mtk_wdt_recovery_test_ops,
    \t\t\t\t\t &state,
    \t\t\t\t\t MTK_WDT_RECOVERY_TIMEOUT_MS,
    \t\t\t\t\t &result));
    \tKUNIT_EXPECT_FALSE(test, owner.owned);
    \tKUNIT_EXPECT_EQ(test, 0U, state.writes);
    }

    static void mtk_wdt_recovery_one_shot_test(struct kunit *test)
    {
    \tstruct mtk_wdt_recovery_test_context state = { .identity = 9 };
    \tstruct mtk_wdt_recovery_result result;
    \tstruct mtk_wdt_recovery_owner owner = {};

    \tKUNIT_ASSERT_EQ(test, 0,
    \t\tmtk_wdt_recovery_execute(&owner, &mtk_wdt_recovery_test_ops,
    \t\t\t\t\t &state,
    \t\t\t\t\t MTK_WDT_RECOVERY_TIMEOUT_MS,
    \t\t\t\t\t &result));
    \tKUNIT_EXPECT_EQ(test, -EALREADY,
    \t\tmtk_wdt_recovery_execute(&owner, &mtk_wdt_recovery_test_ops,
    \t\t\t\t\t &state,
    \t\t\t\t\t MTK_WDT_RECOVERY_TIMEOUT_MS,
    \t\t\t\t\t &result));
    \tKUNIT_EXPECT_EQ(test, 3U, state.writes);
    \tKUNIT_EXPECT_EQ(test, 1U, result.owned);
    \tKUNIT_EXPECT_EQ(test, 9ULL, result.identity);
    }

    static void mtk_wdt_recovery_length_fault_test(struct kunit *test)
    {
    \tstruct mtk_wdt_recovery_test_context state = {
    \t\t.identity = 11,
    \t\t.corrupt_length = true,
    \t};
    \tstruct mtk_wdt_recovery_result result;
    \tstruct mtk_wdt_recovery_owner owner = {};

    \tKUNIT_EXPECT_EQ(test, -EIO,
    \t\tmtk_wdt_recovery_execute(&owner, &mtk_wdt_recovery_test_ops,
    \t\t\t\t\t &state,
    \t\t\t\t\t MTK_WDT_RECOVERY_TIMEOUT_MS,
    \t\t\t\t\t &result));
    \tKUNIT_EXPECT_TRUE(test, owner.owned);
    \tKUNIT_EXPECT_EQ(test, 1U, result.owned);
    \tKUNIT_EXPECT_EQ(test, 3U, state.writes);
    }

    static void mtk_wdt_recovery_mode_fault_test(struct kunit *test)
    {
    \tstruct mtk_wdt_recovery_test_context state = {
    \t\t.identity = 13,
    \t\t.corrupt_mode = true,
    \t};
    \tstruct mtk_wdt_recovery_result result;
    \tstruct mtk_wdt_recovery_owner owner = {};

    \tKUNIT_EXPECT_EQ(test, -EIO,
    \t\tmtk_wdt_recovery_execute(&owner, &mtk_wdt_recovery_test_ops,
    \t\t\t\t\t &state,
    \t\t\t\t\t MTK_WDT_RECOVERY_TIMEOUT_MS,
    \t\t\t\t\t &result));
    \tKUNIT_EXPECT_TRUE(test, owner.owned);
    \tKUNIT_EXPECT_EQ(test, 1U, result.owned);
    \tKUNIT_EXPECT_EQ(test, 3U, state.writes);
    }

    static struct kunit_case mtk_wdt_recovery_cases[] = {
    \tKUNIT_CASE(mtk_wdt_recovery_success_test),
    \tKUNIT_CASE(mtk_wdt_recovery_rejections_test),
    \tKUNIT_CASE(mtk_wdt_recovery_one_shot_test),
    \tKUNIT_CASE(mtk_wdt_recovery_length_fault_test),
    \tKUNIT_CASE(mtk_wdt_recovery_mode_fault_test),
    \t{}
    };

    static struct kunit_suite mtk_wdt_recovery_suite = {
    \t.name = "mtk-wdt-recovery-takeover",
    \t.test_cases = mtk_wdt_recovery_cases,
    };

    kunit_test_suite(mtk_wdt_recovery_suite);
    #endif

    """)


def apply_production(root: Path) -> None:
    kconfig = root / "drivers/watchdog/Kconfig"
    driver = root / "drivers/watchdog/mtk_wdt.c"
    header = root / "include/linux/mtk_wdt.h"

    replace_once(kconfig, "config MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE\n",
                 PRODUCTION_KCONFIG +
                 "config MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE\n")
    replace_once(header, "#endif\n\n#endif\n",
                 "#endif\n\n" + HEADER_BLOCK + "#endif\n")
    replace_once(driver, "#include <linux/delay.h>\n",
                 "#include <linux/atomic.h>\n#include <linux/bitops.h>\n"
                 "#include <linux/delay.h>\n")
    replace_once(
        driver,
        "#if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_KUNIT_TEST)\n"
        "#include <kunit/test.h>\n#endif\n",
        "#if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_KUNIT_TEST) || \\\n+    IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER_KUNIT_TEST)\n"
        "#include <kunit/test.h>\n#endif\n",
    )
    replace_once(driver, "#define WDT_LENGTH_TIMEOUT(n)\t((n) << 5)\n",
                 "#define WDT_LENGTH_TIMEOUT(n)\t((n) << 5)\n"
                 "#define WDT_LENGTH_TIMEOUT_MASK\tGENMASK(15, 5)\n")
    replace_once(driver, "#define WDT_MODE_KEY\t\t0x22000000\n",
                 "#define WDT_MODE_KEY\t\t0x22000000\n"
                 "#define WDT_MODE_RECOVERY_MASK \\\n+    \t(WDT_MODE_EN | WDT_MODE_IRQ_EN | WDT_MODE_AUTO_START | \\\n+    \t WDT_MODE_DUAL_EN)\n"
                 "#define MTK_WDT_RECOVERY_TIMEOUT_SECONDS\t15U\n")
    replace_once(driver, "static unsigned int timeout;\n\n",
                 "static unsigned int timeout;\n\n" + RECOVERY_TYPES)
    replace_once(
        driver,
        "\tbool use_auto_restart;\n#ifdef CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE\n",
        "\tbool use_auto_restart;\n"
        "#if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER)\n"
        "\tspinlock_t recovery_lock; /* guards recovery ownership */\n"
        "\tstruct mtk_wdt_recovery_owner recovery;\n"
        "\tbool recovery_supported;\n"
        "#endif\n"
        "#ifdef CONFIG_MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE\n",
    )
    replace_once(driver, "\tbool has_boot_status;\n\tunsigned int restart_priority;\n",
                 "\tbool has_boot_status;\n"
                 "\tbool recovery_takeover;\n"
                 "\tunsigned int restart_priority;\n")
    replace_once(driver, "\t.has_boot_status = true,\n\t.use_auto_restart = true,\n",
                 "\t.has_boot_status = true,\n"
                 "\t.recovery_takeover = true,\n"
                 "\t.use_auto_restart = true,\n")
    replace_once(driver, "static int mtk_wdt_restart(struct watchdog_device *wdt_dev,\n",
                 RECOVERY_IMPLEMENTATION +
                 "static int mtk_wdt_restart(struct watchdog_device *wdt_dev,\n")
    old_ops = driver.read_text(encoding="utf-8")
    start = old_ops.index("static int mtk_wdt_ping(struct watchdog_device *wdt_dev)\n")
    end = old_ops.index("static void mtk_wdt_init(struct watchdog_device *wdt_dev)\n")
    driver.write_text(old_ops[:start] + WATCHDOG_OPS + old_ops[end:],
                      encoding="utf-8")
    old_ops = driver.read_text(encoding="utf-8")
    start = old_ops.index("static int mtk_wdt_stop(struct watchdog_device *wdt_dev)\n")
    end = old_ops.index("static irqreturn_t mtk_wdt_isr(int irq, void *arg)\n")
    driver.write_text(old_ops[:start] + STOP_START_PRETIMEOUT + old_ops[end:],
                      encoding="utf-8")
    replace_once(driver, "\tplatform_set_drvdata(pdev, mtk_wdt);\n\n"
                 "\twdt_data = of_device_get_match_data(dev);\n",
                 "#if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER)\n"
                 "\tspin_lock_init(&mtk_wdt->recovery_lock);\n"
                 "#endif\n"
                 "\tplatform_set_drvdata(pdev, mtk_wdt);\n\n"
                 "\twdt_data = of_device_get_match_data(dev);\n")
    replace_once(driver, "\tif (wdt_data)\n"
                 "\t\tmtk_wdt->use_auto_restart = wdt_data->use_auto_restart;\n",
                 "\tif (wdt_data) {\n"
                 "\t\tmtk_wdt->use_auto_restart = wdt_data->use_auto_restart;\n"
                 "#if IS_ENABLED(CONFIG_MEDIATEK_WATCHDOG_RECOVERY_TAKEOVER)\n"
                 "\t\tmtk_wdt->recovery_supported = wdt_data->recovery_takeover;\n"
                 "#endif\n"
                 "\t}\n")


def apply_tests(root: Path) -> None:
    kconfig = root / "drivers/watchdog/Kconfig"
    driver = root / "drivers/watchdog/mtk_wdt.c"
    replace_once(kconfig, "config MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE\n",
                 TEST_KCONFIG +
                 "config MEDIATEK_WATCHDOG_BOOT_STATUS_CAPTURE\n")
    replace_once(driver, "module_param(timeout, uint, 0);\n",
                 TEST_SOURCE + "module_param(timeout, uint, 0);\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "production":
        apply_production(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
