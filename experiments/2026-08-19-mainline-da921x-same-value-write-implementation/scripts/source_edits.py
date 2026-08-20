#!/usr/bin/env python3
"""Apply deterministic Gate-6 same-value-write source changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def public_ledger_header() -> str:
    return dedent("""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __LINUX_I2C_MT65XX_GEMINI_LEDGER_H
    #define __LINUX_I2C_MT65XX_GEMINI_LEDGER_H

    #include <linux/types.h>

    struct i2c_adapter;

    struct mtk_i2c_gemini_read_expectation {
    \tu16 address;
    \tu8 register_pointer;
    };

    int mtk_i2c_gemini_verify_read_ledger(struct i2c_adapter *adapter,
    \t\t\t\t      const struct mtk_i2c_gemini_read_expectation *expected,
    \tunsigned int count);

    #endif /* __LINUX_I2C_MT65XX_GEMINI_LEDGER_H */
    """)


def ledger_verifier_source() -> str:
    return dedent("""\
    int mtk_i2c_gemini_verify_read_ledger(struct i2c_adapter *adapter,
    \t\t\t\t      const struct mtk_i2c_gemini_read_expectation *expected,
    \tunsigned int count)
    {
    \tstruct mtk_i2c *i2c;
    \tunsigned long flags;
    \tunsigned int i;
    \tint ret = 0;

    \tif (!adapter || !expected || count > MTK_I2C_ENTRY_LEDGER_CAPACITY)
    \t\treturn -EINVAL;

    \tlockdep_assert_held(&adapter->bus_lock);
    \ti2c = i2c_get_adapdata(adapter);
    \tif (!i2c || &i2c->adap != adapter ||
    \t    i2c->dev_comp != &mt6797_idvfs_compat || !i2c->dvfsp_handoff)
    \t\treturn -ENODEV;

    \tspin_lock_irqsave(&i2c->entry_ledger_lock, flags);
    \tif (i2c->entry_ledger_count != count || i2c->entry_ledger_overflow) {
    \t\tret = -EPROTO;
    \t\tgoto out_unlock;
    \t}

    \tfor (i = 0; i < count; i++) {
    \t\tconst struct mtk_i2c_entry_record *record =
    \t\t\t&i2c->entry_ledger[i];

    \t\tif (record->num != 2 ||
    \t\t    record->addr[0] != expected[i].address ||
    \t\t    record->addr[1] != expected[i].address ||
    \t\t    record->flags[0] || record->flags[1] != I2C_M_RD ||
    \t\t    record->len[0] != 1 || record->len[1] != 1 ||
    \t\t    !record->first_byte_valid ||
    \t\t    record->first_byte != expected[i].register_pointer ||
    \t\t    record->second_byte_valid || !record->complete ||
    \t\t    record->result != 2) {
    \t\t\tret = -EPROTO;
    \t\t\tgoto out_unlock;
    \t\t}
    \t}

    out_unlock:
    \tspin_unlock_irqrestore(&i2c->entry_ledger_lock, flags);
    \treturn ret;
    }
    EXPORT_SYMBOL_GPL(mtk_i2c_gemini_verify_read_ledger);

    """)


def edit_ledger(root: Path) -> None:
    driver = root / "drivers/i2c/busses/i2c-mt65xx.c"
    kconfig = root / "drivers/i2c/busses/Kconfig"
    write_new(root / "include/linux/i2c-mt65xx-gemini-ledger.h",
              public_ledger_header())

    replace_once(
        driver,
        "#include <linux/i2c.h>\n",
        "#include <linux/i2c.h>\n"
        "#include <linux/i2c-mt65xx-gemini-ledger.h>\n",
    )
    replace_once(
        driver,
        "\tu8 first_byte;\n"
        "\tbool first_byte_valid;\n"
        "\tbool complete;\n",
        "\tu8 first_byte;\n"
        "\tu8 second_byte;\n"
        "\tbool first_byte_valid;\n"
        "\tbool second_byte_valid;\n"
        "\tbool complete;\n",
    )
    replace_once(
        driver,
        "\tif (num > 0 && msgs[0].buf && msgs[0].len) {\n"
        "\t\trecord->first_byte = msgs[0].buf[0];\n"
        "\t\trecord->first_byte_valid = true;\n"
        "\t}\n\n"
        "out_unlock:\n",
        "\tif (num > 0 && msgs[0].buf && msgs[0].len) {\n"
        "\t\trecord->first_byte = msgs[0].buf[0];\n"
        "\t\trecord->first_byte_valid = true;\n"
        "\t\tif (msgs[0].len == 2) {\n"
        "\t\t\trecord->second_byte = msgs[0].buf[1];\n"
        "\t\t\trecord->second_byte_valid = true;\n"
        "\t\t}\n"
        "\t}\n\n"
        "out_unlock:\n",
    )
    anchor = "#ifdef CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER\nstatic int mtk_i2c_entry_ledger_begin"
    replace_once(
        driver,
        anchor,
        "#ifdef CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER\n" +
        ledger_verifier_source() +
        "static int mtk_i2c_entry_ledger_begin",
    )
    replace_once(
        driver,
        '"entry_ledger=v1 count=%u capacity=%u overflow=%u\\n",',
        '"entry_ledger=v2 count=%u capacity=%u overflow=%u\\n",',
    )
    replace_once(
        driver,
        '"p0=%02x pv=%u a1=%02x f1=%04x l1=%u "\n'
        '\t\t\t\t"ret=%d done=%u\\n",\n'
        "\t\t\t\ti, record->num, record->addr[0],\n"
        "\t\t\t\trecord->flags[0], record->len[0],\n"
        "\t\t\t\trecord->first_byte,\n"
        "\t\t\t\t(unsigned int)record->first_byte_valid,\n"
        "\t\t\t\trecord->addr[1], record->flags[1],\n",
        '"p0=%02x pv=%u p1=%02x p1v=%u "\n'
        '\t\t\t\t"a1=%02x f1=%04x l1=%u ret=%d done=%u\\n",\n'
        "\t\t\t\ti, record->num, record->addr[0],\n"
        "\t\t\t\trecord->flags[0], record->len[0],\n"
        "\t\t\t\trecord->first_byte,\n"
        "\t\t\t\t(unsigned int)record->first_byte_valid,\n"
        "\t\t\t\trecord->second_byte,\n"
        "\t\t\t\t(unsigned int)record->second_byte_valid,\n"
        "\t\t\t\trecord->addr[1], record->flags[1],\n",
    )
    replace_once(
        driver,
        "\t\t\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t\t\"entry%u n=%u a0=%02x f0=%04x l0=%u \"\n"
        "\t\t\t\t\"p0=%02x pv=%u p1=%02x p1v=%u \"\n"
        "\t\t\t\t\"a1=%02x f1=%04x l1=%u ret=%d done=%u\\n\",\n"
        "\t\t\t\ti, record->num, record->addr[0],\n"
        "\t\t\t\trecord->flags[0], record->len[0],\n"
        "\t\t\t\trecord->first_byte,\n"
        "\t\t\t\t(unsigned int)record->first_byte_valid,\n"
        "\t\t\t\trecord->second_byte,\n"
        "\t\t\t\t(unsigned int)record->second_byte_valid,\n"
        "\t\t\t\trecord->addr[1], record->flags[1],\n"
        "\t\t\t\trecord->len[1], record->result,\n"
        "\t\t\t\t(unsigned int)record->complete);\n",
        "\t\t\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t\t\"entry%u n=%u a0=%02x f0=%04x l0=%u p0=%02x pv=%u \",\n"
        "\t\t\t\ti, record->num, record->addr[0],\n"
        "\t\t\t\trecord->flags[0], record->len[0],\n"
        "\t\t\t\trecord->first_byte,\n"
        "\t\t\t\t(unsigned int)record->first_byte_valid);\n"
        "\t\t\tlen += sysfs_emit_at(buf, len,\n"
        "\t\t\t\t\"p1=%02x p1v=%u a1=%02x f1=%04x l1=%u ret=%d done=%u\\n\",\n"
        "\t\t\t\trecord->second_byte,\n"
        "\t\t\t\t(unsigned int)record->second_byte_valid,\n"
        "\t\t\t\trecord->addr[1], record->flags[1],\n"
        "\t\t\t\trecord->len[1], record->result,\n"
        "\t\t\t\t(unsigned int)record->complete);\n",
    )

    replace_once(
        kconfig,
        dedent("""\
        config I2C_MT65XX_GEMINI_ENTRY_LEDGER
        \tbool "MT6797 I2C6 bounded transfer-entry ledger"
        \tdepends on I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE
        \thelp
        \t  Retain the first 32 message shapes submitted to the access-controlled
        \t  MT6797 iDVFS I2C instance. The read-only status includes message count,
        \t  address, flags, length, first pointer byte, and final adapter result.
        \t  Overflow is explicit and no transfer can be triggered through the ABI.

        \t  The ledger records no register-data byte, adds no retry, write, reset,
        \t  regulator consumer, or CPU action, and is intended only for the named
        \t  Gemini Gate-6 attribution experiment. Say N otherwise.

        """),
        dedent("""\
        config I2C_MT65XX_GEMINI_ENTRY_LEDGER
        \tbool "MT6797 I2C6 bounded transfer-entry ledger"
        \tdepends on I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE
        \thelp
        \t  Retain the first 32 message shapes submitted to the access-controlled
        \t  MT6797 iDVFS I2C instance. The v2 read-only status includes message
        \t  count, address, flags, length, the first byte, a bounded second byte
        \t  only for length-two writes, and the final adapter result.

        \t  A read-only verifier can match an exact completed pointer-read prefix
        \t  while its caller already holds the root-adapter lock. It cannot trigger
        \t  a transfer. This default-off Gate-6 ledger adds no retry, reset,
        \t  regulator consumer, or CPU action. Say N otherwise.

        """),
    )


def write_contract_header() -> str:
    return dedent("""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __DA9213_LEGACY_WRITE_CONTRACT_H
    #define __DA9213_LEGACY_WRITE_CONTRACT_H

    #include <linux/types.h>

    struct i2c_adapter;
    struct i2c_msg;

    #define DA9213_LEGACY_SAME_VALUE_PREFLIGHT_COUNT\t5
    #define DA9213_LEGACY_SAME_VALUE_POSTSTATE_COUNT\t4

    enum da9213_legacy_same_value_state {
    \tDA9213_LEGACY_SAME_VALUE_IDLE,
    \tDA9213_LEGACY_SAME_VALUE_RUNNING,
    \tDA9213_LEGACY_SAME_VALUE_PASSED,
    \tDA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE,
    \tDA9213_LEGACY_SAME_VALUE_FAULTED,
    };

    struct da9213_legacy_same_value_result {
    \tenum da9213_legacy_same_value_state state;
    \tunsigned int attempts;
    \tunsigned int action_transfers;
    \tunsigned int write_attempts;
    \tint error;
    \tu8 preflight[DA9213_LEGACY_SAME_VALUE_PREFLIGHT_COUNT];
    \tu8 immediate_readback;
    \tu8 delayed_readback;
    \tu8 poststate[DA9213_LEGACY_SAME_VALUE_POSTSTATE_COUNT];
    };

    struct da9213_legacy_same_value_ops {
    \tint (*verify_ledger)(struct i2c_adapter *adapter);
    \tint (*transfer)(struct i2c_adapter *adapter,
    \t\t\tstruct i2c_msg *messages, int count);
    \tvoid (*delay)(unsigned long minimum, unsigned long maximum);
    };

    const char *da9213_legacy_same_value_state_name(enum da9213_legacy_same_value_state state);
    int da9213_legacy_same_value_admit(struct da9213_legacy_same_value_result *result,
    \t\t\t\t   bool token_valid, bool preconditions_valid);
    int da9213_legacy_same_value_execute(struct i2c_adapter *adapter, u16 address,
    \t\t\t\t     const struct da9213_legacy_same_value_ops *ops,
    \t\t\t\t     struct da9213_legacy_same_value_result *result);

    #endif /* __DA9213_LEGACY_WRITE_CONTRACT_H */
    """)


def write_contract_source() -> str:
    return dedent("""\
    const char *da9213_legacy_same_value_state_name(enum da9213_legacy_same_value_state state)
    {
    \tswitch (state) {
    \tcase DA9213_LEGACY_SAME_VALUE_IDLE:
    \t\treturn "idle";
    \tcase DA9213_LEGACY_SAME_VALUE_RUNNING:
    \t\treturn "running";
    \tcase DA9213_LEGACY_SAME_VALUE_PASSED:
    \t\treturn "passed";
    \tcase DA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE:
    \t\treturn "failed-no-write";
    \tcase DA9213_LEGACY_SAME_VALUE_FAULTED:
    \t\treturn "faulted-no-further-i2c";
    \tdefault:
    \t\treturn "invalid";
    \t}
    }

    int da9213_legacy_same_value_admit(struct da9213_legacy_same_value_result *result,
    \t\t\t\t   bool token_valid, bool preconditions_valid)
    {
    \tif (!result || !token_valid)
    \t\treturn -EINVAL;
    \tif (result->state != DA9213_LEGACY_SAME_VALUE_IDLE)
    \t\treturn -EALREADY;

    \tresult->attempts = 1;
    \tif (!preconditions_valid) {
    \t\tresult->state = DA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE;
    \t\tresult->error = -EPROTO;
    \t\treturn -EPROTO;
    \t}

    \tresult->state = DA9213_LEGACY_SAME_VALUE_RUNNING;
    \treturn 0;
    }

    static int da9213_legacy_same_value_read(struct i2c_adapter *adapter,
    \t\t\t\t\t u16 address, u8 reg, u8 *value,
    \tconst struct da9213_legacy_same_value_ops *ops,
    \tstruct da9213_legacy_same_value_result *result)
    {
    \tstruct i2c_msg messages[2] = { };
    \tu8 data = 0;
    \tint ret;

    \tmessages[0].addr = address;
    \tmessages[0].len = 1;
    \tmessages[0].buf = &reg;
    \tmessages[1].addr = address;
    \tmessages[1].flags = I2C_M_RD;
    \tmessages[1].len = 1;
    \tmessages[1].buf = &data;

    \tret = ops->transfer(adapter, messages, ARRAY_SIZE(messages));
    \tresult->action_transfers++;
    \tif (ret < 0)
    \t\treturn ret;
    \tif (ret != ARRAY_SIZE(messages))
    \t\treturn -EIO;

    \t*value = data;
    \treturn 0;
    }

    static int da9213_legacy_same_value_write(struct i2c_adapter *adapter,
    \t\t\t\t\t  u16 address,
    \t\t\t\t     const struct da9213_legacy_same_value_ops *ops,
    \tstruct da9213_legacy_same_value_result *result)
    {
    \tu8 payload[2] = { 0xda, 0x46 };
    \tstruct i2c_msg message = {
    \t\t.addr = address,
    \t\t.len = ARRAY_SIZE(payload),
    \t\t.buf = payload,
    \t};
    \tint ret;

    \tresult->write_attempts = 1;
    \tret = ops->transfer(adapter, &message, 1);
    \tresult->action_transfers++;
    \tif (ret < 0)
    \t\treturn ret;
    \tif (ret != 1)
    \t\treturn -EIO;

    \treturn 0;
    }

    int da9213_legacy_same_value_execute(struct i2c_adapter *adapter, u16 address,
    \t\t\t\t     const struct da9213_legacy_same_value_ops *ops,
    \t\t\t\t     struct da9213_legacy_same_value_result *result)
    {
    \tstatic const u8 preflight_regs[] = { 0x56, 0x51, 0x5e, 0xd9, 0xda };
    \tstatic const u8 preflight_expected[] = { 0x7b, 0xc1, 0x00, 0x46, 0x46 };
    \tstatic const u8 poststate_regs[] = { 0x56, 0x51, 0x5e, 0xd9 };
    \tstatic const u8 poststate_expected[] = { 0x7b, 0xc1, 0x00, 0x46 };
    \tunsigned int saved_retries = 0;
    \tbool retries_saved = false;
    \tunsigned int i;
    \tint ret;

    \tif (!adapter || !ops || !ops->verify_ledger || !ops->transfer ||
    \t    !ops->delay || !result ||
    \t    result->state != DA9213_LEGACY_SAME_VALUE_RUNNING ||
    \t    !adapter->lock_ops || !adapter->lock_ops->lock_bus ||
    \t    !adapter->lock_ops->unlock_bus)
    \t\treturn -EINVAL;

    \ti2c_lock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);
    \tret = ops->verify_ledger(adapter);
    \tif (ret)
    \t\tgoto out_finish;

    \tsaved_retries = adapter->retries;
    \tretries_saved = true;
    \tadapter->retries = 0;

    \tfor (i = 0; i < ARRAY_SIZE(preflight_regs); i++) {
    \t\tret = da9213_legacy_same_value_read(adapter, address,
    \t\t\t\t\t\t    preflight_regs[i], &result->preflight[i],
    \t\t\t\t\t\t    ops, result);
    \t\tif (ret)
    \t\t\tgoto out_restore;
    \t\tif (result->preflight[i] != preflight_expected[i]) {
    \t\t\tret = -ERANGE;
    \t\t\tgoto out_restore;
    \t\t}
    \t}

    \tret = da9213_legacy_same_value_write(adapter, address, ops, result);
    \tif (ret)
    \t\tgoto out_restore;

    \tret = da9213_legacy_same_value_read(adapter, address, 0xda,
    \t\t\t\t\t    &result->immediate_readback, ops, result);
    \tif (ret)
    \t\tgoto out_restore;
    \tif (result->immediate_readback != 0x46) {
    \t\tret = -ERANGE;
    \t\tgoto out_restore;
    \t}

    \tops->delay(10000, 11000);
    \tret = da9213_legacy_same_value_read(adapter, address, 0xda,
    \t\t\t\t\t    &result->delayed_readback, ops, result);
    \tif (ret)
    \t\tgoto out_restore;
    \tif (result->delayed_readback != 0x46) {
    \t\tret = -ERANGE;
    \t\tgoto out_restore;
    \t}

    \tfor (i = 0; i < ARRAY_SIZE(poststate_regs); i++) {
    \t\tret = da9213_legacy_same_value_read(adapter, address,
    \t\t\t\t\t\t    poststate_regs[i], &result->poststate[i],
    \t\t\t\t\t\t    ops, result);
    \t\tif (ret)
    \t\t\tgoto out_restore;
    \t\tif (result->poststate[i] != poststate_expected[i]) {
    \t\t\tret = -ERANGE;
    \t\t\tgoto out_restore;
    \t\t}
    \t}

    \tret = 0;

    out_restore:
    \tadapter->retries = saved_retries;
    out_finish:
    \tif (retries_saved && adapter->retries != saved_retries)
    \t\tadapter->retries = saved_retries;
    \tresult->error = ret;
    \tif (!ret)
    \t\tresult->state = DA9213_LEGACY_SAME_VALUE_PASSED;
    \telse if (!result->write_attempts)
    \t\tresult->state = DA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE;
    \telse
    \t\tresult->state = DA9213_LEGACY_SAME_VALUE_FAULTED;
    \ti2c_unlock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);

    \treturn ret;
    }

    """)


def write_runtime_source() -> str:
    return dedent("""\
    #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE)
    #define DA9213_LEGACY_SAME_VALUE_TOKEN \\
    \t"run-same-value-write-20260819-a"

    static const struct mtk_i2c_gemini_read_expectation
    da9213_legacy_startup_ledger[] = {
    \t{ 0x69, 0x05 }, { 0x69, 0x06 }, { 0x69, 0x47 },
    \t{ 0x68, 0xd3 }, { 0x68, 0x5e }, { 0x68, 0xd9 }, { 0x68, 0xda },
    \t{ 0x69, 0x05 }, { 0x69, 0x06 }, { 0x69, 0x47 },
    \t{ 0x68, 0xd3 }, { 0x68, 0x5e }, { 0x68, 0xd9 }, { 0x68, 0xda },
    \t{ 0x68, 0xd7 }, { 0x68, 0xd9 },
    \t{ 0x68, 0xd7 }, { 0x68, 0x5d }, { 0x68, 0xd9 }, { 0x68, 0x5e },
    };

    static int da9213_legacy_verify_startup_ledger(struct i2c_adapter *adapter)
    {
    \treturn mtk_i2c_gemini_verify_read_ledger(adapter,
    \t\t\t\t\t da9213_legacy_startup_ledger,
    \t\tARRAY_SIZE(da9213_legacy_startup_ledger));
    }

    static const struct da9213_legacy_same_value_ops
    da9213_legacy_same_value_production_ops = {
    \t.verify_ledger = da9213_legacy_verify_startup_ledger,
    \t.transfer = __i2c_transfer,
    \t.delay = usleep_range,
    };

    static bool da9213_legacy_same_value_cpu_baseline(void)
    {
    \tunsigned int cpu;

    \tif (nr_cpu_ids <= 9)
    \t\treturn false;
    \tfor (cpu = 0; cpu < 8; cpu++)
    \t\tif (!cpu_online(cpu))
    \t\t\treturn false;

    \treturn !cpu_online(8) && !cpu_online(9) && num_online_cpus() == 8;
    }

    static bool da9213_legacy_same_value_preconditions(struct da9213_legacy *chip)
    {
    \treturn chip->observation.valid &&
    \t\tchip->observation.provider_count == DA9213_LEGACY_BUCK_COUNT &&
    \t\tchip->observation.provider_read_completed == 4 &&
    \t\t!chip->observation.register_data_writes &&
    \t\tchip->phase_reads[DA9213_LEGACY_READ_REGISTRATION] == 2 &&
    \t\tchip->phase_reads[DA9213_LEGACY_READ_OBSERVER] == 4 &&
    \t\t!chip->phase_reads[DA9213_LEGACY_READ_PREFLIGHT] &&
    \t\tda9213_legacy_same_value_cpu_baseline();
    }

    static ssize_t same_value_write_show(struct device *dev,
    \t\t\t\t     struct device_attribute *attr, char *buf)
    {
    \tstruct da9213_legacy *chip = dev_get_drvdata(dev);
    \tconst struct da9213_legacy_same_value_result *result =
    \t\t&chip->same_value_result;
    \tssize_t len;

    \tmutex_lock(&chip->runtime_preflight_lock);
    \tlen = sysfs_emit(buf,
    \t\t\t "same_value_write=v1 state=%s attempts=%u last_error=%d\\n",
    \t\t\t da9213_legacy_same_value_state_name(result->state),
    \t\t\t result->attempts, result->error);
    \tlen += sysfs_emit_at(buf, len,
    \t\t\t     "action_transfers=%u write_attempts=%u\\n",
    \t\t\t     result->action_transfers, result->write_attempts);
    \tlen += sysfs_emit_at(buf, len, "trigger_token=%s\\n",
    \t\t\t     DA9213_LEGACY_SAME_VALUE_TOKEN);
    \tlen += sysfs_emit_at(buf, len,
    \t\t\t     "preflight=%02x,%02x,%02x,%02x,%02x immediate=%02x ",
    \t\t\t     result->preflight[0], result->preflight[1],
    \t\t\t     result->preflight[2], result->preflight[3],
    \t\t\t     result->preflight[4], result->immediate_readback);
    \tlen += sysfs_emit_at(buf, len,
    \t\t\t     "delayed=%02x poststate=%02x,%02x,%02x,%02x\\n",
    \t\t\t     result->delayed_readback, result->poststate[0],
    \t\t\t     result->poststate[1], result->poststate[2],
    \t\t\t     result->poststate[3]);
    \tlen += sysfs_emit_at(buf, len,
    \t\t\t     "cpu_online=0-7 cpu_offline=8-9 page_con_accesses=0 ");
    \tlen += sysfs_emit_at(buf, len,
    \t\t\t     "consumer_requests=0 cpu_requests=0 second_writes=0\\n");
    \tmutex_unlock(&chip->runtime_preflight_lock);

    \treturn len;
    }

    static ssize_t same_value_write_store(struct device *dev,
    \t\t\t\t      struct device_attribute *attr,
    \t\t\t\t      const char *buf, size_t count)
    {
    \tstruct da9213_legacy *chip = dev_get_drvdata(dev);
    \tbool token_valid = sysfs_streq(buf, DA9213_LEGACY_SAME_VALUE_TOKEN);
    \tint ret;

    \tmutex_lock(&chip->runtime_preflight_lock);
    \tret = da9213_legacy_same_value_admit(&chip->same_value_result,
    \t\t\t\t\t     token_valid,
    \t\t\t\t\t     da9213_legacy_same_value_preconditions(chip));
    \tif (!ret)
    \t\tret = da9213_legacy_same_value_execute(chip->client->adapter,
    \t\t\t\t\t\t       chip->client->addr,
    \t\t\t\t\t\t       &da9213_legacy_same_value_production_ops,
    \t\t\t\t\t\t       &chip->same_value_result);
    \tif (!ret)
    \t\tdev_info(chip->dev,
    \t\t\t "same-value Gate-6 action passed with 12 transfers\\n");
    \tmutex_unlock(&chip->runtime_preflight_lock);

    \treturn ret ? ret : count;
    }

    static DEVICE_ATTR_RW(same_value_write);

    static struct attribute *da9213_legacy_same_value_attrs[] = {
    \t&dev_attr_same_value_write.attr,
    \tNULL,
    };

    static const struct attribute_group da9213_legacy_same_value_group = {
    \t.attrs = da9213_legacy_same_value_attrs,
    };
    #endif

    """)


def edit_write_implementation(root: Path) -> None:
    driver = root / "drivers/regulator/da9213-legacy-regulator.c"
    kconfig = root / "drivers/regulator/Kconfig"
    write_new(root / "drivers/regulator/da9213-legacy-write-contract.h",
              write_contract_header())

    replace_once(
        driver,
        "#include <linux/i2c.h>\n"
        "#include <linux/module.h>\n",
        "#include <linux/cpu.h>\n"
        "#include <linux/delay.h>\n"
        "#include <linux/i2c.h>\n"
        "#include <linux/i2c-mt65xx-gemini-ledger.h>\n"
        "#include <linux/module.h>\n",
    )
    replace_once(
        driver,
        '#include "da9213-legacy-observer.h"\n',
        '#include "da9213-legacy-observer.h"\n'
        '#include "da9213-legacy-write-contract.h"\n',
    )
    replace_once(
        driver,
        "\tint runtime_preflight_error;\n"
        "#endif\n"
        "#endif\n"
        "#endif\n"
        "};\n",
        "\tint runtime_preflight_error;\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE)\n"
        "\tstruct da9213_legacy_same_value_result same_value_result;\n"
        "#endif\n"
        "#endif\n"
        "#endif\n"
        "#endif\n"
        "};\n",
    )

    anchor = ("#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT)\n"
              "#define DA9213_LEGACY_RUNTIME_PREFLIGHT_TOKEN")
    replacement = (
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE)\n" +
        write_contract_source() +
        "#endif\n\n" +
        write_runtime_source() +
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT)\n"
        "#define DA9213_LEGACY_RUNTIME_PREFLIGHT_TOKEN"
    )
    replace_once(driver, anchor, replacement)

    replace_once(
        driver,
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT)\n"
        "\tchip->read_phase = DA9213_LEGACY_READ_PHASE_COUNT;\n"
        "\tret = devm_device_add_group(chip->dev,\n"
        "\t\t\t\t    &da9213_legacy_runtime_preflight_group);\n"
        "\tif (ret)\n"
        "\t\treturn dev_err_probe(&client->dev, ret,\n"
        "\t\t\t\t     \"failed to add read-only preflight trigger\\n\");\n"
        "#endif\n",
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT)\n"
        "\tchip->read_phase = DA9213_LEGACY_READ_PHASE_COUNT;\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE)\n"
        "\tret = devm_device_add_group(chip->dev,\n"
        "\t\t\t\t    &da9213_legacy_same_value_group);\n"
        "#else\n"
        "\tret = devm_device_add_group(chip->dev,\n"
        "\t\t\t\t    &da9213_legacy_runtime_preflight_group);\n"
        "#endif\n"
        "\tif (ret)\n"
        "\t\treturn dev_err_probe(&client->dev, ret,\n"
        "\t\t\t\t     \"failed to add Gate-6 runtime trigger\\n\");\n"
        "#endif\n",
    )

    replace_once(
        kconfig,
        "config REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST\n",
        dedent("""\
        config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE
        \tbool "Dialog legacy DA921x one-shot same-value write"
        \tdepends on REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT
        \tdepends on I2C_MT65XX_GEMINI_ENTRY_LEDGER
        \thelp
        \t  Replace the read-only runtime trigger with one exact-token Gate-6
        \t  action. Under one root-adapter lock it verifies the exact 20-entry
        \t  startup ledger, forces retries to zero, performs five exact preflight
        \t  reads, writes [0xda, 0x46] once, and performs six exact readbacks.

        \t  Every mismatch stops without retry, inverse write, PAGE_CON access,
        \t  regulator consumer, or CPU request. This option is only for the named
        \t  Gemini same-value-write experiment and must remain N otherwise.

        config REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST
        """),
    )


def kunit_source() -> str:
    return dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* Hardware-free coverage for the DA921x same-value-write sequence. */

    #include <kunit/test.h>
    #include <linux/errno.h>
    #include <linux/i2c.h>
    #include <linux/kernel.h>
    #include <linux/module.h>
    #include <linux/string.h>

    #include "da9213-legacy-write-contract.h"

    #define DA9213_TEST_ADDRESS\t0x2a
    #define DA9213_TEST_ACTIONS\t12

    struct da9213_test_fake {
    \tstruct i2c_adapter adapter;
    \tunsigned int lock_calls;
    \tunsigned int unlock_calls;
    \tunsigned int transfer_calls;
    \tunsigned int verify_calls;
    \tunsigned int delay_calls;
    \tunsigned int fail_ordinal;
    \tunsigned int mismatch_ordinal;
    \tint ledger_error;
    \tunsigned int retries_during[DA9213_TEST_ACTIONS];
    \tu8 registers[DA9213_TEST_ACTIONS];
    \tu8 write_payload[2];
    \tbool locked;
    \tbool verify_locked;
    \tbool unlocked_transfer;
    \tbool delay_locked;
    };

    static struct da9213_test_fake *active_fake;

    static const u8 da9213_test_registers[DA9213_TEST_ACTIONS] = {
    \t0x56, 0x51, 0x5e, 0xd9, 0xda, 0xda,
    \t0xda, 0xda, 0x56, 0x51, 0x5e, 0xd9,
    };

    static const u8 da9213_test_values[DA9213_TEST_ACTIONS] = {
    \t0x7b, 0xc1, 0x00, 0x46, 0x46, 0x46,
    \t0x46, 0x46, 0x7b, 0xc1, 0x00, 0x46,
    };

    static void da9213_test_lock(struct i2c_adapter *adapter, unsigned int flags)
    {
    \tstruct da9213_test_fake *fake = active_fake;

    \tfake->lock_calls++;
    \tfake->locked = true;
    }

    static int da9213_test_trylock(struct i2c_adapter *adapter, unsigned int flags)
    {
    \treturn 0;
    }

    static void da9213_test_unlock(struct i2c_adapter *adapter, unsigned int flags)
    {
    \tstruct da9213_test_fake *fake = active_fake;

    \tfake->unlock_calls++;
    \tfake->locked = false;
    }

    static const struct i2c_lock_operations da9213_test_lock_ops = {
    \t.lock_bus = da9213_test_lock,
    \t.trylock_bus = da9213_test_trylock,
    \t.unlock_bus = da9213_test_unlock,
    };

    static int da9213_test_verify(struct i2c_adapter *adapter)
    {
    \tstruct da9213_test_fake *fake = active_fake;

    \tfake->verify_calls++;
    \tfake->verify_locked = fake->locked;
    \treturn fake->ledger_error;
    }

    static int da9213_test_transfer(struct i2c_adapter *adapter,
    \t\t\t\tstruct i2c_msg *messages, int count)
    {
    \tstruct da9213_test_fake *fake = active_fake;
    \tunsigned int ordinal = ++fake->transfer_calls;
    \tu8 value;

    \tfake->unlocked_transfer |= !fake->locked;
    \tfake->retries_during[ordinal - 1] = adapter->retries;
    \tif (ordinal == fake->fail_ordinal)
    \t\treturn -EAGAIN;

    \tif (ordinal == 6) {
    \t\tif (count != 1 || messages[0].addr != DA9213_TEST_ADDRESS ||
    \t\t    messages[0].flags || messages[0].len != 2)
    \t\t\treturn -EPROTO;
    \t\tfake->registers[ordinal - 1] = messages[0].buf[0];
    \t\tmemcpy(fake->write_payload, messages[0].buf,
    \t\t       sizeof(fake->write_payload));
    \t\treturn 1;
    \t}

    \tif (count != 2 || messages[0].addr != DA9213_TEST_ADDRESS ||
    \t    messages[1].addr != DA9213_TEST_ADDRESS ||
    \t    messages[0].flags || messages[0].len != 1 ||
    \t    messages[1].len != 1 || messages[1].flags != I2C_M_RD)
    \t\treturn -EPROTO;
    \tfake->registers[ordinal - 1] = messages[0].buf[0];
    \tvalue = da9213_test_values[ordinal - 1];
    \tif (ordinal == fake->mismatch_ordinal)
    \t\tvalue ^= 1;
    \tmessages[1].buf[0] = value;
    \treturn 2;
    }

    static void da9213_test_delay(unsigned long minimum, unsigned long maximum)
    {
    \tstruct da9213_test_fake *fake = active_fake;

    \tif (minimum == 10000 && maximum == 11000)
    \t\tfake->delay_calls++;
    \tfake->delay_locked = fake->locked;
    }

    static const struct da9213_legacy_same_value_ops da9213_test_ops = {
    \t.verify_ledger = da9213_test_verify,
    \t.transfer = da9213_test_transfer,
    \t.delay = da9213_test_delay,
    };

    static void da9213_test_init_fake(struct da9213_test_fake *fake)
    {
    \tmemset(fake, 0, sizeof(*fake));
    \tfake->adapter.lock_ops = &da9213_test_lock_ops;
    \tfake->adapter.retries = 1;
    \tactive_fake = fake;
    }

    static void da9213_test_init_result(struct da9213_legacy_same_value_result *result)
    {
    \tmemset(result, 0, sizeof(*result));
    \tresult->attempts = 1;
    \tresult->state = DA9213_LEGACY_SAME_VALUE_RUNNING;
    }

    static void da9213_same_value_success(struct kunit *test)
    {
    \tstruct da9213_legacy_same_value_result result;
    \tstruct da9213_test_fake fake;
    \tunsigned int i;
    \tint ret;

    \tda9213_test_init_fake(&fake);
    \tda9213_test_init_result(&result);
    \tret = da9213_legacy_same_value_execute(&fake.adapter,
    \t\t\t\t\t       DA9213_TEST_ADDRESS, &da9213_test_ops, &result);

    \tKUNIT_EXPECT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_SAME_VALUE_PASSED);
    \tKUNIT_EXPECT_EQ(test, result.action_transfers, 12U);
    \tKUNIT_EXPECT_EQ(test, result.write_attempts, 1U);
    \tKUNIT_EXPECT_EQ(test, fake.lock_calls, 1U);
    \tKUNIT_EXPECT_EQ(test, fake.unlock_calls, 1U);
    \tKUNIT_EXPECT_TRUE(test, fake.verify_locked);
    \tKUNIT_EXPECT_FALSE(test, fake.unlocked_transfer);
    \tKUNIT_EXPECT_TRUE(test, fake.delay_locked);
    \tKUNIT_EXPECT_EQ(test, fake.delay_calls, 1U);
    \tKUNIT_EXPECT_EQ(test, fake.adapter.retries, 1);
    \tKUNIT_EXPECT_MEMEQ(test, fake.registers, da9213_test_registers, sizeof(fake.registers));
    \tKUNIT_EXPECT_EQ(test, fake.write_payload[0], (u8)0xda);
    \tKUNIT_EXPECT_EQ(test, fake.write_payload[1], (u8)0x46);
    \tfor (i = 0; i < DA9213_TEST_ACTIONS; i++)
    \t\tKUNIT_EXPECT_EQ(test, fake.retries_during[i], 0U);
    }

    static void da9213_same_value_admission(struct kunit *test)
    {
    \tstruct da9213_legacy_same_value_result result = { };
    \tint ret;

    \tret = da9213_legacy_same_value_admit(&result, false, true);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    \tKUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_SAME_VALUE_IDLE);
    \tret = da9213_legacy_same_value_admit(&result, true, false);
    \tKUNIT_EXPECT_EQ(test, ret, -EPROTO);
    \tKUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE);
    \tret = da9213_legacy_same_value_admit(&result, true, true);
    \tKUNIT_EXPECT_EQ(test, ret, -EALREADY);
    }

    static void da9213_same_value_ledger_refusal(struct kunit *test)
    {
    \tstruct da9213_legacy_same_value_result result;
    \tstruct da9213_test_fake fake;
    \tint ret;

    \tda9213_test_init_fake(&fake);
    \tda9213_test_init_result(&result);
    \tfake.ledger_error = -EPROTO;
    \tret = da9213_legacy_same_value_execute(&fake.adapter,
    \t\t\t\t\t       DA9213_TEST_ADDRESS, &da9213_test_ops, &result);
    \tKUNIT_EXPECT_EQ(test, ret, -EPROTO);
    \tKUNIT_EXPECT_EQ(test, result.state,
    \t\t\tDA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE);
    \tKUNIT_EXPECT_EQ(test, fake.verify_calls, 1U);
    \tKUNIT_EXPECT_TRUE(test, fake.verify_locked);
    \tKUNIT_EXPECT_EQ(test, fake.transfer_calls, 0U);
    \tKUNIT_EXPECT_EQ(test, fake.lock_calls, 1U);
    \tKUNIT_EXPECT_EQ(test, fake.unlock_calls, 1U);
    \tKUNIT_EXPECT_EQ(test, fake.adapter.retries, 1);
    }

    static void da9213_same_value_transfer_failures(struct kunit *test)
    {
    \tunsigned int ordinal;

    \tfor (ordinal = 1; ordinal <= DA9213_TEST_ACTIONS; ordinal++) {
    \t\tstruct da9213_legacy_same_value_result result;
    \t\tstruct da9213_test_fake fake;
    \t\tint ret;

    \t\tda9213_test_init_fake(&fake);
    \t\tda9213_test_init_result(&result);
    \t\tfake.fail_ordinal = ordinal;
    \t\tret = da9213_legacy_same_value_execute(&fake.adapter,
    \t\t\t\t\t\t       DA9213_TEST_ADDRESS,
    \t\t\t\t\t\t       &da9213_test_ops, &result);
    \t\tKUNIT_EXPECT_EQ_MSG(test, ret, -EAGAIN, "ordinal=%u", ordinal);
    \t\tKUNIT_EXPECT_EQ_MSG(test, result.action_transfers, ordinal,
    \t\t\t\t    "ordinal=%u", ordinal);
    \t\tKUNIT_EXPECT_EQ_MSG(test, fake.adapter.retries, 1,
    \t\t\t\t    "ordinal=%u", ordinal);
    \t\tKUNIT_EXPECT_EQ_MSG(test, fake.unlock_calls, 1U,
    \t\t\t\t    "ordinal=%u", ordinal);
    \t\tif (ordinal < 6) {
    \t\t\tKUNIT_EXPECT_EQ(test, result.write_attempts, 0U);
    \t\t\tKUNIT_EXPECT_EQ(test, result.state,
    \t\t\t\t\tDA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE);
    \t\t} else {
    \t\t\tKUNIT_EXPECT_EQ(test, result.write_attempts, 1U);
    \t\t\tKUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_SAME_VALUE_FAULTED);
    \t\t}
    \t}
    }

    static void da9213_same_value_mismatches(struct kunit *test)
    {
    \tunsigned int ordinal;

    \tfor (ordinal = 1; ordinal <= DA9213_TEST_ACTIONS; ordinal++) {
    \t\tstruct da9213_legacy_same_value_result result;
    \t\tstruct da9213_test_fake fake;
    \t\tint ret;

    \t\tif (ordinal == 6)
    \t\t\tcontinue;
    \t\tda9213_test_init_fake(&fake);
    \t\tda9213_test_init_result(&result);
    \t\tfake.mismatch_ordinal = ordinal;
    \t\tret = da9213_legacy_same_value_execute(&fake.adapter,
    \t\t\t\t\t\t       DA9213_TEST_ADDRESS,
    \t\t\t\t\t\t       &da9213_test_ops, &result);
    \t\tKUNIT_EXPECT_EQ_MSG(test, ret, -ERANGE, "ordinal=%u", ordinal);
    \t\tKUNIT_EXPECT_EQ_MSG(test, result.action_transfers, ordinal,
    \t\t\t\t    "ordinal=%u", ordinal);
    \t\tKUNIT_EXPECT_EQ_MSG(test, fake.adapter.retries, 1,
    \t\t\t\t    "ordinal=%u", ordinal);
    \t\tif (ordinal < 6)
    \t\t\tKUNIT_EXPECT_EQ(test, result.state,
    \t\t\t\t\tDA9213_LEGACY_SAME_VALUE_FAILED_NO_WRITE);
    \t\telse
    \t\t\tKUNIT_EXPECT_EQ(test, result.state, DA9213_LEGACY_SAME_VALUE_FAULTED);
    \t}
    }

    static void da9213_same_value_invalid_execute(struct kunit *test)
    {
    \tstruct da9213_legacy_same_value_result result = { };
    \tstruct da9213_test_fake fake;
    \tint ret;

    \tda9213_test_init_fake(&fake);
    \tret = da9213_legacy_same_value_execute(&fake.adapter,
    \t\t\t\t\t       DA9213_TEST_ADDRESS, &da9213_test_ops, &result);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    \tKUNIT_EXPECT_EQ(test, fake.lock_calls, 0U);
    \tKUNIT_EXPECT_EQ(test, fake.transfer_calls, 0U);
    }

    static struct kunit_case da9213_same_value_cases[] = {
    \tKUNIT_CASE(da9213_same_value_success),
    \tKUNIT_CASE(da9213_same_value_admission),
    \tKUNIT_CASE(da9213_same_value_ledger_refusal),
    \tKUNIT_CASE(da9213_same_value_transfer_failures),
    \tKUNIT_CASE(da9213_same_value_mismatches),
    \tKUNIT_CASE(da9213_same_value_invalid_execute),
    \t{ }
    };

    static struct kunit_suite da9213_same_value_suite = {
    \t.name = "da9213-legacy-same-value-write",
    \t.test_cases = da9213_same_value_cases,
    };

    kunit_test_suite(da9213_same_value_suite);

    MODULE_LICENSE("GPL");
    """)


def edit_kunit(root: Path) -> None:
    kconfig = root / "drivers/regulator/Kconfig"
    makefile = root / "drivers/regulator/Makefile"
    write_new(root / "drivers/regulator/da9213-legacy-write-test.c",
              kunit_source())

    replace_once(
        kconfig,
        "config REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST\n",
        dedent("""\
        config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST
        \tbool "KUnit tests for the legacy DA921x same-value write"
        \tdepends on KUNIT=y
        \tdepends on REGULATOR_DA9213_LEGACY=y
        \tdepends on REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE
        \thelp
        \t  Exercise the production sequence helper with an in-memory fake
        \t  adapter. Cover the exact 12 actions, both payload bytes, one lock,
        \t  zero retries, admission refusals, every transfer failure, every
        \t  readback mismatch, and restoration on every exit.

        \t  The suite registers no adapter or client, maps no MMIO, performs no
        \t  physical transfer, and exists only for the hardware-free Gate-6
        \t  implementation proof. Say N otherwise.

        config REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST) += da9213-legacy-observer-test.o\n",
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST) += da9213-legacy-observer-test.o\n"
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST) += da9213-legacy-write-test.o\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("ledger", "write", "kunit", "all"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if not (root / "drivers/i2c/busses/i2c-mt65xx.c").is_file():
        raise SystemExit("source root lacks the expected I2C driver")
    if not (root / "drivers/regulator/da9213-legacy-regulator.c").is_file():
        raise SystemExit("source root lacks the expected legacy regulator driver")

    if args.phase == "all":
        edit_ledger(root)
        edit_write_implementation(root)
        edit_kunit(root)
    elif args.phase == "ledger":
        edit_ledger(root)
    elif args.phase == "write":
        edit_write_implementation(root)
    else:
        edit_kunit(root)


if __name__ == "__main__":
    main()
