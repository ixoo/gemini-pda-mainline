#!/usr/bin/env python3
"""Apply deterministic Gate-6 B2 production and KUnit source changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent, indent


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


def contract_header() -> str:
    return dedent("""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __I2C_MT65XX_GEMINI_WRITE_CONTRACT_H
    #define __I2C_MT65XX_GEMINI_WRITE_CONTRACT_H

    #include <linux/bits.h>
    #include <linux/i2c.h>
    #include <linux/types.h>

    #define MTK_I2C_IDVFS_IRQ_TRANSAC_COMP\tBIT(0)
    #define MTK_I2C_IDVFS_IRQ_ACKERR\t\tBIT(1)
    #define MTK_I2C_IDVFS_IRQ_HS_NACKERR\tBIT(2)
    #define MTK_I2C_IDVFS_IRQ_ARB_LOST\t\tBIT(3)
    #define MTK_I2C_IDVFS_SHORT_WRITE_BYTES\t2

    struct mtk_i2c_idvfs_short_write_plan {
    \tu16 slave_addr;
    \tu16 transfer_len;
    \tu16 transac_len;
    \tu8 fifo[MTK_I2C_IDVFS_SHORT_WRITE_BYTES];
    \tu8 fifo_count;
    \tbool use_dma;
    \tbool direction_change;
    };

    typedef void (*mtk_i2c_idvfs_fifo_write_fn)(void *context, u8 value);

    int mtk_i2c_idvfs_plan_short_write(
    \tconst struct i2c_msg *msgs, int num,
    \tstruct mtk_i2c_idvfs_short_write_plan *plan);
    void mtk_i2c_idvfs_emit_short_write(
    \tconst struct mtk_i2c_idvfs_short_write_plan *plan,
    \tmtk_i2c_idvfs_fifo_write_fn write, void *context);
    int mtk_i2c_idvfs_completion_result(unsigned long wait_result,
    \t\t\t\t\tu16 irq_stat);
    int mtk_i2c_idvfs_result_after_lease(int transport_result,
    \t\t\t\t\tint lease_result);
    int mtk_i2c_idvfs_transfer_once(struct i2c_adapter *adap,
\t\t\t\t    struct i2c_msg *msgs, int num);

    #endif /* __I2C_MT65XX_GEMINI_WRITE_CONTRACT_H */
    """)


def production_helpers() -> str:
    return dedent("""\
    int mtk_i2c_idvfs_plan_short_write(
    \tconst struct i2c_msg *msgs, int num,
    \tstruct mtk_i2c_idvfs_short_write_plan *plan)
    {
    \tif (!msgs || !plan || num != 1 || !msgs[0].buf ||
    \t    msgs[0].flags || msgs[0].addr > 0x7f ||
    \t    msgs[0].len != MTK_I2C_IDVFS_SHORT_WRITE_BYTES)
    \t\treturn -EINVAL;

    \tmemset(plan, 0, sizeof(*plan));
    \tplan->slave_addr = msgs[0].addr << 1;
    \tplan->transfer_len = MTK_I2C_IDVFS_SHORT_WRITE_BYTES;
    \tplan->transac_len = 1;
    \tplan->fifo_count = MTK_I2C_IDVFS_SHORT_WRITE_BYTES;
    \tmemcpy(plan->fifo, msgs[0].buf, sizeof(plan->fifo));
    \treturn 0;
    }

    void mtk_i2c_idvfs_emit_short_write(
    \tconst struct mtk_i2c_idvfs_short_write_plan *plan,
    \tmtk_i2c_idvfs_fifo_write_fn write, void *context)
    {
    \tunsigned int i;

    \tif (!plan || !write || plan->fifo_count != sizeof(plan->fifo))
    \t\treturn;

    \tfor (i = 0; i < plan->fifo_count; i++)
    \t\twrite(context, plan->fifo[i]);
    }

    int mtk_i2c_idvfs_completion_result(unsigned long wait_result,
    \t\t\t\t\tu16 irq_stat)
    {
    \tif (irq_stat & MTK_I2C_IDVFS_IRQ_ARB_LOST)
    \t\treturn -EAGAIN;
    \tif (!wait_result)
    \t\treturn -ETIMEDOUT;
    \tif (irq_stat & (MTK_I2C_IDVFS_IRQ_HS_NACKERR |
    \t\t\tMTK_I2C_IDVFS_IRQ_ACKERR))
    \t\treturn -ENXIO;
    \tif (irq_stat != MTK_I2C_IDVFS_IRQ_TRANSAC_COMP)
    \t\treturn -EIO;

    \treturn 0;
    }

    int mtk_i2c_idvfs_result_after_lease(int transport_result,
    \t\t\t\t\tint lease_result)
    {
    \tif (transport_result >= 0 && lease_result < 0)
    \t\treturn lease_result;

    \treturn transport_result;
    }

    int mtk_i2c_idvfs_transfer_once(struct i2c_adapter *adap,
\t\t\t\t    struct i2c_msg *msgs, int num)
    {
    \tunsigned int retries;
    \tint ret;

\tif (!adap || !msgs || num != 1 || !adap->lock_ops ||
\t    !adap->lock_ops->lock_bus || !adap->lock_ops->unlock_bus)
    \t\treturn -EINVAL;

\ti2c_lock_bus(adap, I2C_LOCK_ROOT_ADAPTER);
    \tretries = adap->retries;
    \tadap->retries = 0;
    \tret = __i2c_transfer(adap, msgs, num);
    \tadap->retries = retries;
\ti2c_unlock_bus(adap, I2C_LOCK_ROOT_ADAPTER);

    \treturn ret;
    }

    """)


def edit_production_driver(root: Path) -> None:
    path = root / "drivers/i2c/busses/i2c-mt65xx.c"
    replace_once(
        path,
        "#include <linux/uaccess.h>\n",
        "#include <linux/uaccess.h>\n\n"
        "#include \"i2c-mt65xx-gemini-write-contract.h\"\n",
    )

    helper_anchor = dedent("""\
    static bool mtk_i2c_should_use_dma(struct mtk_i2c *i2c,
    \t\t\t\t   const struct i2c_msg *msgs)
    {
    #ifdef CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC
    \tif (i2c->orion.mode == MTK_I2C_ORION_MODE_AUX_DMA ||
    \t    i2c->orion.mode == MTK_I2C_ORION_MODE_PACKED_DMA)
    \t\treturn true;
    \tif (i2c->orion.mode == MTK_I2C_ORION_MODE_PACKED_FIFO)
    \t\treturn false;
    #endif

    \tif (!i2c->dev_comp->fifo_size ||
    \t    msgs->len > i2c->dev_comp->fifo_size)
    \t\treturn true;

    \treturn i2c->op == I2C_MASTER_WRRD &&
    \t       (msgs + 1)->len > i2c->dev_comp->fifo_size;
    }

    """)
    replace_once(path, helper_anchor, helper_anchor + production_helpers())

    prepare_anchor = dedent("""\
    static void mtk_i2c_prepare_pio(struct mtk_i2c *i2c,
    \t\t\t\tconst struct i2c_msg *msgs)
    {
    \tint i;

    \tif (i2c->op == I2C_MASTER_RD)
    \t\treturn;

    \tfor (i = 0; i < msgs->len; i++)
    \t\twritel(msgs->buf[i],
    \t\t       i2c->base + i2c->dev_comp->regs[OFFSET_DATA_PORT]);
    }

    """)
    prepare_replacement = prepare_anchor + dedent("""\
    static void mtk_i2c_idvfs_write_data_port(void *context, u8 value)
    {
    \tstruct mtk_i2c *i2c = context;

    \twritel(value, i2c->base +
    \t       i2c->dev_comp->regs[OFFSET_DATA_PORT]);
    }

    """)
    replace_once(path, prepare_anchor, prepare_replacement)

    replace_once(
        path,
        "\tbool use_dma;\n\tint ret;\n\n"
        "\ti2c->irq_stat = 0;\n"
        "\tuse_dma = mtk_i2c_should_use_dma(i2c, msgs);\n",
        "\tstruct mtk_i2c_idvfs_short_write_plan short_write = { };\n"
        "\tbool idvfs_short_write;\n"
        "\tbool use_dma;\n\tint ret;\n\n"
        "\ti2c->irq_stat = 0;\n"
        "\tidvfs_short_write = i2c->dev_comp == &mt6797_idvfs_compat &&\n"
        "\t\ti2c->op == I2C_MASTER_WR && num == 1 && msgs->len == 2;\n"
        "\tif (idvfs_short_write) {\n"
        "\t\tret = mtk_i2c_idvfs_plan_short_write(msgs, num,\n"
        "\t\t\t\t\t\t&short_write);\n"
        "\t\tif (ret)\n\t\t\treturn ret;\n"
        "\t\tuse_dma = short_write.use_dma;\n"
        "\t} else {\n"
        "\t\tuse_dma = mtk_i2c_should_use_dma(i2c, msgs);\n"
        "\t}\n",
    )
    replace_once(
        path,
        "\taddr_reg = i2c_8bit_addr_from_msg(msgs);\n",
        "\taddr_reg = idvfs_short_write ? short_write.slave_addr :\n"
        "\t\ti2c_8bit_addr_from_msg(msgs);\n",
    )
    replace_once(
        path,
        "\t} else {\n"
        "\t\tmtk_i2c_writew(i2c, msgs->len, OFFSET_TRANSFER_LEN);\n"
        "\t\tmtk_i2c_writew(i2c, num, OFFSET_TRANSAC_LEN);\n"
        "\t}\n\n"
        "\tif (i2c->dev_comp->apdma_sync) {\n",
        "\t} else if (idvfs_short_write) {\n"
        "\t\tmtk_i2c_writew(i2c, short_write.transfer_len,\n"
        "\t\t\t\tOFFSET_TRANSFER_LEN);\n"
        "\t\tmtk_i2c_writew(i2c, short_write.transac_len,\n"
        "\t\t\t\tOFFSET_TRANSAC_LEN);\n"
        "\t} else {\n"
        "\t\tmtk_i2c_writew(i2c, msgs->len, OFFSET_TRANSFER_LEN);\n"
        "\t\tmtk_i2c_writew(i2c, num, OFFSET_TRANSAC_LEN);\n"
        "\t}\n\n"
        "\tif (i2c->dev_comp->apdma_sync) {\n",
    )
    replace_once(
        path,
        "\tif (!use_dma) {\n"
        "\t\tmtk_i2c_prepare_pio(i2c, msgs);\n"
        "\t} else if (i2c->op == I2C_MASTER_RD) {\n",
        "\tif (!use_dma) {\n"
        "\t\tif (idvfs_short_write)\n"
        "\t\t\tmtk_i2c_idvfs_emit_short_write(\n"
        "\t\t\t\t&short_write, mtk_i2c_idvfs_write_data_port,\n"
        "\t\t\t\ti2c);\n"
        "\t\telse\n"
        "\t\t\tmtk_i2c_prepare_pio(i2c, msgs);\n"
        "\t} else if (i2c->op == I2C_MASTER_RD) {\n",
    )

    result_anchor = indent(dedent("""\
    \tif (i2c->dev_comp == &mt6797_idvfs_compat &&
    \t    i2c->irq_stat & I2C_ARB_LOST) {
    \t\tdev_dbg(i2c->dev, "addr: %x, arbitration lost\\n", msgs->addr);
    \t\tmtk_i2c_init_hw(i2c);
    \t\treturn -EAGAIN;
    \t}

    \tif (ret == 0) {
    \t\tdev_dbg(i2c->dev, "addr: %x, transfer timeout\\n", msgs->addr);
    \t\ti2c_dump_register(i2c);
    \t\tmtk_i2c_init_hw(i2c);
    \t\treturn -ETIMEDOUT;
    \t}

    \tif (i2c->irq_stat & (I2C_HS_NACKERR | I2C_ACKERR)) {
    \t\tdev_dbg(i2c->dev, "addr: %x, transfer ACK error\\n", msgs->addr);
    \t\tmtk_i2c_init_hw(i2c);
    \t\treturn -ENXIO;
    \t}

    \tif (i2c->dev_comp == &mt6797_idvfs_compat &&
    \t    i2c->irq_stat != I2C_TRANSAC_COMP) {
    \t\tdev_dbg(i2c->dev, "addr: %x, incomplete transaction: 0x%x\\n",
    \t\t\tmsgs->addr, i2c->irq_stat);
    \t\tmtk_i2c_init_hw(i2c);
    \t\treturn -EIO;
    \t}

    """), "\t")
    result_replacement = indent(dedent("""\
    \tif (i2c->dev_comp == &mt6797_idvfs_compat) {
    \t\tint result = mtk_i2c_idvfs_completion_result(ret,
    \t\t\t\t\t\t\t      i2c->irq_stat);

    \t\tif (result) {
    \t\t\tdev_dbg(i2c->dev,
    \t\t\t\t"addr: %x, iDVFS transfer result %d irq 0x%x\\n",
    \t\t\t\tmsgs->addr, result, i2c->irq_stat);
    \t\t\tif (result == -ETIMEDOUT)
    \t\t\t\ti2c_dump_register(i2c);
    \t\t\tmtk_i2c_init_hw(i2c);
    \t\t\treturn result;
    \t\t}
    \t} else {
    \t\tif (ret == 0) {
    \t\t\tdev_dbg(i2c->dev, "addr: %x, transfer timeout\\n",
    \t\t\t\tmsgs->addr);
    \t\t\ti2c_dump_register(i2c);
    \t\t\tmtk_i2c_init_hw(i2c);
    \t\t\treturn -ETIMEDOUT;
    \t\t}

    \t\tif (i2c->irq_stat & (I2C_HS_NACKERR | I2C_ACKERR)) {
    \t\t\tdev_dbg(i2c->dev, "addr: %x, transfer ACK error\\n",
    \t\t\t\tmsgs->addr);
    \t\t\tmtk_i2c_init_hw(i2c);
    \t\t\treturn -ENXIO;
    \t\t}
    \t}

    """), "\t")
    replace_once(path, result_anchor, result_replacement)

    replace_once(
        path,
        "\t\tif (!ret && lease_ret)\n\t\t\tret = lease_ret;\n",
        "\t\tret = mtk_i2c_idvfs_result_after_lease(ret, lease_ret);\n",
    )


def edit_production(root: Path) -> None:
    write_new(
        root / "drivers/i2c/busses/i2c-mt65xx-gemini-write-contract.h",
        contract_header(),
    )
    edit_production_driver(root)


def kunit_source() -> str:
    return dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* Hardware-free coverage for the MT6797 iDVFS short-write contract. */

    #include <kunit/test.h>
    #include <linux/errno.h>
    #include <linux/i2c.h>
    #include <linux/kernel.h>
    #include <linux/module.h>
    #include <linux/string.h>

    #include "i2c-mt65xx-gemini-write-contract.h"

    #define MTK_I2C_TEST_ADDR\t0x2a
    #define MTK_I2C_TEST_BYTE0\t0xa5
    #define MTK_I2C_TEST_BYTE1\t0x5a

    struct mtk_i2c_idvfs_fifo_fake {
    \tu8 values[MTK_I2C_IDVFS_SHORT_WRITE_BYTES];
    \tunsigned int calls;
    };

    struct mtk_i2c_idvfs_transfer_fake {
    \tstruct i2c_adapter adap;
    \tstruct i2c_algorithm algo;
\tstruct i2c_lock_operations lock_ops;
    \tint result;
    \tunsigned int calls;
\tunsigned int lock_calls;
\tunsigned int unlock_calls;
\tunsigned int lock_flags;
\tunsigned int unlock_flags;
\tunsigned int retries_during;
\tbool locked;
\tbool locked_during;
    \tu16 address;
    \tu16 flags;
    \tu16 length;
    \tu8 payload[MTK_I2C_IDVFS_SHORT_WRITE_BYTES];
    };

    static struct i2c_msg mtk_i2c_idvfs_test_message(u8 payload[2])
    {
    \tstruct i2c_msg msg = {
    \t\t.addr = MTK_I2C_TEST_ADDR,
    \t\t.len = MTK_I2C_IDVFS_SHORT_WRITE_BYTES,
    \t\t.buf = payload,
    \t};

    \treturn msg;
    }

    static void mtk_i2c_idvfs_fifo_fake_write(void *context, u8 value)
    {
    \tstruct mtk_i2c_idvfs_fifo_fake *fake = context;

    \tif (fake->calls < ARRAY_SIZE(fake->values))
    \t\tfake->values[fake->calls] = value;
    \tfake->calls++;
    }

    static int mtk_i2c_idvfs_transfer_fake_xfer(struct i2c_adapter *adap,
    \t\t\t\t\t\t struct i2c_msg *msgs,
    \t\t\t\t\t\t int num)
    {
    \tstruct mtk_i2c_idvfs_transfer_fake *fake =
    \t\tcontainer_of(adap, struct mtk_i2c_idvfs_transfer_fake, adap);

    \tfake->calls++;
\tfake->retries_during = adap->retries;
\tfake->locked_during = fake->locked;
    \tif (num == 1 && msgs && msgs[0].buf && msgs[0].len == 2) {
    \t\tfake->address = msgs[0].addr;
    \t\tfake->flags = msgs[0].flags;
    \t\tfake->length = msgs[0].len;
    \t\tmemcpy(fake->payload, msgs[0].buf, sizeof(fake->payload));
    \t}

    \treturn fake->result;
    }

    static void mtk_i2c_idvfs_transfer_fake_lock(
\tstruct i2c_adapter *adap, unsigned int flags)
    {
\tstruct mtk_i2c_idvfs_transfer_fake *fake =
\t\tcontainer_of(adap, struct mtk_i2c_idvfs_transfer_fake, adap);

\tfake->lock_calls++;
\tfake->lock_flags = flags;
\tfake->locked = true;
    }

    static void mtk_i2c_idvfs_transfer_fake_unlock(
\tstruct i2c_adapter *adap, unsigned int flags)
    {
\tstruct mtk_i2c_idvfs_transfer_fake *fake =
\t\tcontainer_of(adap, struct mtk_i2c_idvfs_transfer_fake, adap);

\tfake->unlock_calls++;
\tfake->unlock_flags = flags;
\tfake->locked = false;
    }

    static void mtk_i2c_idvfs_transfer_fake_init(
    \tstruct mtk_i2c_idvfs_transfer_fake *fake, int result)
    {
    \tmemset(fake, 0, sizeof(*fake));
    \tfake->algo.master_xfer = mtk_i2c_idvfs_transfer_fake_xfer;
    \tfake->adap.algo = &fake->algo;
\tfake->lock_ops.lock_bus = mtk_i2c_idvfs_transfer_fake_lock;
\tfake->lock_ops.unlock_bus = mtk_i2c_idvfs_transfer_fake_unlock;
\tfake->adap.lock_ops = &fake->lock_ops;
    \tfake->adap.retries = 1;
    \tfake->result = result;
    }

    static void mtk_i2c_idvfs_exact_two_byte_fifo_plan(struct kunit *test)
    {
    \tu8 payload[2] = { MTK_I2C_TEST_BYTE0, MTK_I2C_TEST_BYTE1 };
    \tstruct i2c_msg msg = mtk_i2c_idvfs_test_message(payload);
    \tstruct mtk_i2c_idvfs_short_write_plan plan;
    \tstruct mtk_i2c_idvfs_fifo_fake fake = { };

    \tKUNIT_ASSERT_EQ(test,
    \t\tmtk_i2c_idvfs_plan_short_write(&msg, 1, &plan), 0);
    \tKUNIT_EXPECT_EQ(test, plan.slave_addr, (u16)0x54);
    \tKUNIT_EXPECT_EQ(test, plan.transfer_len, (u16)2);
    \tKUNIT_EXPECT_EQ(test, plan.transac_len, (u16)1);
    \tKUNIT_EXPECT_FALSE(test, plan.use_dma);
    \tKUNIT_EXPECT_FALSE(test, plan.direction_change);
    \tmtk_i2c_idvfs_emit_short_write(
    \t\t&plan, mtk_i2c_idvfs_fifo_fake_write, &fake);
    \tKUNIT_EXPECT_EQ(test, fake.calls, 2U);
    \tKUNIT_EXPECT_EQ(test, fake.values[0], (u8)MTK_I2C_TEST_BYTE0);
    \tKUNIT_EXPECT_EQ(test, fake.values[1], (u8)MTK_I2C_TEST_BYTE1);
    }

    static void mtk_i2c_idvfs_malformed_message_refusals(struct kunit *test)
    {
    \tu8 payload[3] = { MTK_I2C_TEST_BYTE0, MTK_I2C_TEST_BYTE1, 0 };
    \tstruct mtk_i2c_idvfs_short_write_plan plan;
    \tstruct i2c_msg msg = mtk_i2c_idvfs_test_message(payload);

    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_plan_short_write(NULL, 1, &plan), -EINVAL);
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_plan_short_write(&msg, 0, &plan), -EINVAL);
    \tmsg.buf = NULL;
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_plan_short_write(&msg, 1, &plan), -EINVAL);
    \tmsg.buf = payload;
    \tmsg.flags = I2C_M_RD;
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_plan_short_write(&msg, 1, &plan), -EINVAL);
    \tmsg.flags = 0;
    \tmsg.len = 1;
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_plan_short_write(&msg, 1, &plan), -EINVAL);
    \tmsg.len = 3;
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_plan_short_write(&msg, 1, &plan), -EINVAL);
    \tmsg.len = 2;
    \tmsg.addr = 0x80;
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_plan_short_write(&msg, 1, &plan), -EINVAL);
    }

    static void mtk_i2c_idvfs_exact_completion_success(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_completion_result(
    \t\t1, MTK_I2C_IDVFS_IRQ_TRANSAC_COMP), 0);
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_result_after_lease(1, 0), 1);
    }

    static void mtk_i2c_idvfs_timeout_classification(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_completion_result(0, 0), -ETIMEDOUT);
    }

    static void mtk_i2c_idvfs_nack_classification(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_completion_result(
    \t\t1, MTK_I2C_IDVFS_IRQ_ACKERR), -ENXIO);
    \tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_completion_result(
    \t\t1, MTK_I2C_IDVFS_IRQ_HS_NACKERR), -ENXIO);
    }

    static void mtk_i2c_idvfs_arbitration_loss_classification(
    \tstruct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_completion_result(
    \t\t0, MTK_I2C_IDVFS_IRQ_ARB_LOST), -EAGAIN);
    }

    static void mtk_i2c_idvfs_unexpected_irq_refusal(struct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_completion_result(1, 0), -EIO);
    \tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_completion_result(
    \t\t1, MTK_I2C_IDVFS_IRQ_TRANSAC_COMP |
    \t\t   MTK_I2C_IDVFS_IRQ_ACKERR), -ENXIO);
    \tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_completion_result(
    \t\t1, MTK_I2C_IDVFS_IRQ_TRANSAC_COMP |
    \t\t   MTK_I2C_IDVFS_IRQ_ARB_LOST), -EAGAIN);
    }

    static void mtk_i2c_idvfs_no_retry_eagain(struct kunit *test)
    {
    \tu8 payload[2] = { MTK_I2C_TEST_BYTE0, MTK_I2C_TEST_BYTE1 };
    \tstruct i2c_msg msg = mtk_i2c_idvfs_test_message(payload);
    \tstruct mtk_i2c_idvfs_transfer_fake fake;

    \tmtk_i2c_idvfs_transfer_fake_init(&fake, -EAGAIN);

\tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_transfer_once(
    \t\t&fake.adap, &msg, 1), -EAGAIN);
    \tKUNIT_EXPECT_EQ(test, fake.calls, 1U);
\tKUNIT_EXPECT_EQ(test, fake.lock_calls, 1U);
\tKUNIT_EXPECT_EQ(test, fake.unlock_calls, 1U);
\tKUNIT_EXPECT_EQ(test, fake.lock_flags,
\t\t\tI2C_LOCK_ROOT_ADAPTER);
\tKUNIT_EXPECT_EQ(test, fake.unlock_flags,
\t\t\tI2C_LOCK_ROOT_ADAPTER);
\tKUNIT_EXPECT_TRUE(test, fake.locked_during);
\tKUNIT_EXPECT_FALSE(test, fake.locked);
\tKUNIT_EXPECT_EQ(test, fake.retries_during, 0U);
    \tKUNIT_EXPECT_EQ(test, fake.adap.retries, 1U);
    \tKUNIT_EXPECT_EQ(test, fake.address, (u16)MTK_I2C_TEST_ADDR);
    \tKUNIT_EXPECT_EQ(test, fake.flags, (u16)0);
    \tKUNIT_EXPECT_EQ(test, fake.length, (u16)2);
    \tKUNIT_EXPECT_EQ(test, fake.payload[0], (u8)MTK_I2C_TEST_BYTE0);
    \tKUNIT_EXPECT_EQ(test, fake.payload[1], (u8)MTK_I2C_TEST_BYTE1);
    }

    static void mtk_i2c_idvfs_retry_restoration_success(struct kunit *test)
    {
    \tu8 payload[2] = { MTK_I2C_TEST_BYTE0, MTK_I2C_TEST_BYTE1 };
    \tstruct i2c_msg msg = mtk_i2c_idvfs_test_message(payload);
    \tstruct mtk_i2c_idvfs_transfer_fake fake;

    \tmtk_i2c_idvfs_transfer_fake_init(&fake, 1);

\tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_transfer_once(
    \t\t&fake.adap, &msg, 1), 1);
    \tKUNIT_EXPECT_EQ(test, fake.calls, 1U);
\tKUNIT_EXPECT_EQ(test, fake.lock_calls, 1U);
\tKUNIT_EXPECT_EQ(test, fake.unlock_calls, 1U);
\tKUNIT_EXPECT_TRUE(test, fake.locked_during);
\tKUNIT_EXPECT_FALSE(test, fake.locked);
\tKUNIT_EXPECT_EQ(test, fake.retries_during, 0U);
    \tKUNIT_EXPECT_EQ(test, fake.adap.retries, 1U);
    }

    static void mtk_i2c_idvfs_retry_restoration_failure(struct kunit *test)
    {
    \tu8 payload[2] = { MTK_I2C_TEST_BYTE0, MTK_I2C_TEST_BYTE1 };
    \tstruct i2c_msg msg = mtk_i2c_idvfs_test_message(payload);
    \tstruct mtk_i2c_idvfs_transfer_fake fake;

    \tmtk_i2c_idvfs_transfer_fake_init(&fake, -EIO);

\tKUNIT_EXPECT_EQ(test, mtk_i2c_idvfs_transfer_once(
    \t\t&fake.adap, &msg, 1), -EIO);
    \tKUNIT_EXPECT_EQ(test, fake.calls, 1U);
\tKUNIT_EXPECT_EQ(test, fake.lock_calls, 1U);
\tKUNIT_EXPECT_EQ(test, fake.unlock_calls, 1U);
\tKUNIT_EXPECT_TRUE(test, fake.locked_during);
\tKUNIT_EXPECT_FALSE(test, fake.locked);
\tKUNIT_EXPECT_EQ(test, fake.retries_during, 0U);
    \tKUNIT_EXPECT_EQ(test, fake.adap.retries, 1U);
    }

    static void mtk_i2c_idvfs_lease_failure_overrides_success(
    \tstruct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_result_after_lease(1, -EHOSTDOWN),
    \t\t-EHOSTDOWN);
    }

    static void mtk_i2c_idvfs_transport_failure_retains_precedence(
    \tstruct kunit *test)
    {
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_result_after_lease(-ENXIO, 0), -ENXIO);
    \tKUNIT_EXPECT_EQ(test,
    \t\tmtk_i2c_idvfs_result_after_lease(-ENXIO, -EHOSTDOWN),
    \t\t-ENXIO);
    }

    static struct kunit_case mtk_i2c_idvfs_write_contract_cases[] = {
    \tKUNIT_CASE(mtk_i2c_idvfs_exact_two_byte_fifo_plan),
    \tKUNIT_CASE(mtk_i2c_idvfs_malformed_message_refusals),
    \tKUNIT_CASE(mtk_i2c_idvfs_exact_completion_success),
    \tKUNIT_CASE(mtk_i2c_idvfs_timeout_classification),
    \tKUNIT_CASE(mtk_i2c_idvfs_nack_classification),
    \tKUNIT_CASE(mtk_i2c_idvfs_arbitration_loss_classification),
    \tKUNIT_CASE(mtk_i2c_idvfs_unexpected_irq_refusal),
    \tKUNIT_CASE(mtk_i2c_idvfs_no_retry_eagain),
    \tKUNIT_CASE(mtk_i2c_idvfs_retry_restoration_success),
    \tKUNIT_CASE(mtk_i2c_idvfs_retry_restoration_failure),
    \tKUNIT_CASE(mtk_i2c_idvfs_lease_failure_overrides_success),
    \tKUNIT_CASE(mtk_i2c_idvfs_transport_failure_retains_precedence),
    \t{ }
    };

    static struct kunit_suite mtk_i2c_idvfs_write_contract_suite = {
    \t.name = "mtk-i2c-idvfs-write-contract",
    \t.test_cases = mtk_i2c_idvfs_write_contract_cases,
    };

    kunit_test_suite(mtk_i2c_idvfs_write_contract_suite);

    MODULE_LICENSE("GPL");
    """)


def edit_kunit(root: Path) -> None:
    kconfig = root / "drivers/i2c/busses/Kconfig"
    anchor = dedent("""\
    \t  The ledger records no register-data byte, adds no retry, write, reset,
    \t  regulator consumer, or CPU action, and is intended only for the named
    \t  Gemini Gate-6 attribution experiment. Say N otherwise.

    config I2C_MT7621
    """)
    replacement = dedent("""\
    \t  The ledger records no register-data byte, adds no retry, write, reset,
    \t  regulator consumer, or CPU action, and is intended only for the named
    \t  Gemini Gate-6 attribution experiment. Say N otherwise.

    config I2C_MT65XX_GEMINI_WRITE_TRANSPORT_KUNIT_TEST
    \tbool "KUnit tests for the MT6797 I2C6 short-write contract"
    \tdepends on KUNIT=y
    \tdepends on I2C_MT65XX=y
    \thelp
    \t  Exercise the production-coupled MT6797 iDVFS one-message two-byte
    \t  FIFO plan, completion classes, no-retry wrapper, and transfer-lease
    \t  result precedence with an in-memory fake adapter.

    \t  The suite registers no adapter or client, maps no MMIO, writes no
    \t  START register, performs no physical transfer, and is only for the
    \t  hardware-free Gemini Gate-6 B2 experiment. Say N otherwise.

    config I2C_MT7621
    """)
    replace_once(kconfig, anchor, replacement)
    replace_once(
        root / "drivers/i2c/busses/Makefile",
        "obj-$(CONFIG_I2C_MT65XX)\t+= i2c-mt65xx.o\n",
        "obj-$(CONFIG_I2C_MT65XX)\t+= i2c-mt65xx.o\n"
        "obj-$(CONFIG_I2C_MT65XX_GEMINI_WRITE_TRANSPORT_KUNIT_TEST) += "
        "i2c-mt65xx-gemini-write-test.o\n",
    )
    write_new(
        root / "drivers/i2c/busses/i2c-mt65xx-gemini-write-test.c",
        kunit_source(),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("production", "kunit"), required=True)
    args = parser.parse_args()

    root = args.source_root.resolve()
    if not (root / "drivers/i2c/busses/i2c-mt65xx.c").is_file():
        raise SystemExit(f"not a prepared Linux source root: {root}")

    if args.phase == "production":
        edit_production(root)
    else:
        edit_kunit(root)

    print(f"source_edit_phase={args.phase}")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
