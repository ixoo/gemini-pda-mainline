#!/usr/bin/env python3
"""Apply the frozen DA921x read-only snapshot separation."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_DIR = SCRIPT_DIR.parent / "source"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply_core(root: Path) -> None:
    header = root / "drivers/regulator/da9213-legacy-provider-contract.h"
    driver = root / "drivers/regulator/da9213-legacy-regulator.c"

    replace_once(
        header,
        "#include <linux/mt6797-a72-provider.h>\n",
        "#include <linux/kconfig.h>\n"
        "#include <linux/mt6797-a72-provider.h>\n",
    )
    replace_once(
        header,
        "struct i2c_adapter;\nstruct i2c_msg;\n",
        "struct device;\nstruct i2c_adapter;\nstruct i2c_msg;\n\n"
        "typedef int (*da9213_provider_read_transfer_t)(struct i2c_adapter *adapter,\n"
        "\t\t\t\t\t struct i2c_msg *messages, int count);\n",
    )
    replace_once(
        header,
        dedent(
            """\
            struct da9213_legacy_provider_endpoint {
            \tstruct i2c_adapter *adapter;
            \tu16 address;
            \tconst struct da9213_legacy_provider_transport_ops *ops;
            \tstruct mutex lock; /* Serializes one endpoint lifecycle. */
            \tstruct da9213_legacy_provider_result transaction;
            };

            struct da9213_legacy_provider_transport_ops {
            \tint (*transfer)(struct i2c_adapter *adapter,
            \t\t\tstruct i2c_msg *messages, int count);
            \tvoid (*delay)(unsigned long minimum, unsigned long maximum);
            };
            """
        ),
        dedent(
            """\
            struct da9213_legacy_provider_transport_ops {
            \tint (*transfer)(struct i2c_adapter *adapter,
            \t\t\tstruct i2c_msg *messages, int count);
            \tvoid (*delay)(unsigned long minimum, unsigned long maximum);
            };

            struct da9213_legacy_provider_endpoint {
            \tstruct device *dev;
            \tstruct i2c_adapter *adapter;
            \tu16 address;
            \tda9213_provider_read_transfer_t read_transfer;
            \tstruct mutex lock; /* Serializes one endpoint lifecycle. */
            #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
            \tconst struct da9213_legacy_provider_transport_ops *ops;
            \tstruct da9213_legacy_provider_result transaction;
            #endif
            };
            """
        ),
    )
    replace_once(
        header,
        dedent(
            """\
            void
            da9213_legacy_provider_test_unregister(struct da9213_legacy_provider_endpoint *endpoint);
            int da9213_legacy_provider_transaction_release(struct i2c_adapter *adapter,
            """
        ),
        dedent(
            """\
            void
            da9213_legacy_provider_test_unregister(struct da9213_legacy_provider_endpoint *endpoint);
            int
            da9213_provider_snapshot_test_register(struct da9213_legacy_provider_endpoint
            \t\t\t\t\t       *endpoint,
            \tstruct i2c_adapter *adapter, u16 address,
            \tda9213_provider_read_transfer_t read_transfer);
            void
            da9213_provider_snapshot_test_unregister(struct da9213_legacy_provider_endpoint
            \t\t\t\t\t\t *endpoint);
            int da9213_legacy_provider_transaction_release(struct i2c_adapter *adapter,
            """
        ),
    )

    replace_once(
        driver,
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        '#include "da9213-legacy-provider-contract.h"\n'
        "#endif\n"
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n",
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n"
        '#include "da9213-legacy-provider-contract.h"\n'
        "#endif\n"
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n",
    )
    replace_once(
        driver,
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tstruct da9213_legacy_provider_endpoint provider_endpoint;\n"
        "#endif\n",
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n"
        "\tstruct da9213_legacy_provider_endpoint provider_endpoint;\n"
        "#endif\n",
    )

    readonly = dedent(
        """\
        static const u8 da9213_legacy_provider_snapshot_regs[] = {
        \t0x56, 0x51, 0x5e, 0xd9, 0xda,
        };

        static bool
        da9213_provider_read_transport_valid(const struct da9213_legacy_provider_endpoint
        \t\t\t\t     *endpoint)
        {
        \treturn endpoint && endpoint->adapter && endpoint->read_transfer &&
        \t\tendpoint->adapter->lock_ops &&
        \t\tendpoint->adapter->lock_ops->lock_bus &&
        \t\tendpoint->adapter->lock_ops->unlock_bus;
        }

        static int
        da9213_provider_snapshot_read(struct da9213_legacy_provider_endpoint *endpoint,
        \t\t\t      u8 reg, u8 *value)
        {
        \tstruct i2c_msg messages[2] = { };
        \tu8 data = 0;
        \tint ret;

        \tmessages[0].addr = endpoint->address;
        \tmessages[0].len = 1;
        \tmessages[0].buf = &reg;
        \tmessages[1].addr = endpoint->address;
        \tmessages[1].flags = I2C_M_RD;
        \tmessages[1].len = 1;
        \tmessages[1].buf = &data;

        \tret = endpoint->read_transfer(endpoint->adapter, messages,
        \t\t\t\t      ARRAY_SIZE(messages));
        \tif (ret < 0)
        \t\treturn ret;
        \tif (ret != ARRAY_SIZE(messages))
        \t\treturn -EIO;

        \t*value = data;
        \treturn 0;
        }

        static int
        da9213_provider_snapshot_sample(struct da9213_legacy_provider_endpoint *endpoint,
        \t\t\t\tstruct da9213_legacy_provider_snapshot *snapshot)
        {
        \tu8 *values = (u8 *)snapshot;
        \tunsigned int i;
        \tint ret;

        \tBUILD_BUG_ON(sizeof(*snapshot) !=
        \t\t     ARRAY_SIZE(da9213_legacy_provider_snapshot_regs));
        \tfor (i = 0; i < ARRAY_SIZE(da9213_legacy_provider_snapshot_regs);
        \t     i++) {
        \t\tret = da9213_provider_snapshot_read(endpoint,
        \t\t\t\t\t\t    da9213_legacy_provider_snapshot_regs[i],
        \t\t\t\t\t\t    &values[i]);
        \t\tif (ret)
        \t\t\treturn ret;
        \t}

        \treturn 0;
        }

        static int
        da9213_provider_snapshot(void *context,
        \t\t\t struct mt6797_a72_provider_snapshot *state)
        {
        \tstruct da9213_legacy_provider_endpoint *endpoint = context;
        \tstruct da9213_legacy_provider_snapshot first = { };
        \tstruct da9213_legacy_provider_snapshot second = { };
        \tunsigned int saved_retries;
        \tint ret;

        \tif (!state)
        \t\treturn -EINVAL;
        \tmemset(state, 0, sizeof(*state));
        \tif (!da9213_provider_read_transport_valid(endpoint))
        \t\treturn -EINVAL;

        \tmutex_lock(&endpoint->lock);
        \ti2c_lock_bus(endpoint->adapter, I2C_LOCK_ROOT_ADAPTER);
        \tsaved_retries = endpoint->adapter->retries;
        \tendpoint->adapter->retries = 0;

        \tret = da9213_provider_snapshot_sample(endpoint, &first);
        \tif (ret)
        \t\tgoto out;
        \tret = da9213_provider_snapshot_sample(endpoint, &second);
        \tif (ret)
        \t\tgoto out;
        \tif (memcmp(&first, &second, sizeof(first))) {
        \t\tret = -EAGAIN;
        \t\tgoto out;
        \t}

        \t*state = (struct mt6797_a72_provider_snapshot) {
        \t\t.abi = MT6797_A72_PROVIDER_STATE_ABI,
        \t\t.valid = 1,
        \t\t.control_a = second.control_a,
        \t\t.status_b = second.status_b,
        \t\t.buckb_cont = second.buckb_cont,
        \t\t.vbuckb_a = second.vbuckb_a,
        \t\t.vbuckb_b = second.vbuckb_b,
        \t};
        \tret = 0;

        out:
        \tendpoint->adapter->retries = saved_retries;
        \ti2c_unlock_bus(endpoint->adapter, I2C_LOCK_ROOT_ADAPTER);
        \tmutex_unlock(&endpoint->lock);
        \treturn ret;
        }

        """
    )
    replace_once(
        driver,
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n\n"
        "static const u8 da9213_legacy_provider_snapshot_regs[] = {\n"
        "\t0x56, 0x51, 0x5e, 0xd9, 0xda,\n"
        "};\n\n",
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n\n"
        + readonly
        + "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n\n",
    )

    old_snapshot = dedent(
        """\
        static int
        da9213_provider_snapshot(void *context,
        \t\t\t struct mt6797_a72_provider_snapshot *state)
        {
        \tstruct da9213_legacy_provider_endpoint *endpoint = context;
        \tstruct da9213_legacy_provider_snapshot first = { };
        \tstruct da9213_legacy_provider_snapshot second = { };
        \tstruct da9213_legacy_provider_result result = { };
        \tunsigned int saved_retries;
        \tint ret;

        \tif (!state)
        \t\treturn -EINVAL;
        \tmemset(state, 0, sizeof(*state));
        \tif (!endpoint ||
        \t    !da9213_provider_transport_valid(endpoint->adapter, endpoint->ops))
        \t\treturn -EINVAL;

        \tmutex_lock(&endpoint->lock);
        \ti2c_lock_bus(endpoint->adapter, I2C_LOCK_ROOT_ADAPTER);
        \tsaved_retries = endpoint->adapter->retries;
        \tendpoint->adapter->retries = 0;

        \tret = da9213_legacy_provider_snapshot(endpoint->adapter,
        \t\t\t\t\t      endpoint->address, endpoint->ops,
        \t\t\t\t\t      &result, &first);
        \tif (ret)
        \t\tgoto out;
        \tret = da9213_legacy_provider_snapshot(endpoint->adapter,
        \t\t\t\t\t      endpoint->address, endpoint->ops,
        \t\t\t\t\t      &result, &second);
        \tif (ret)
        \t\tgoto out;
        \tif (memcmp(&first, &second, sizeof(first))) {
        \t\tret = -EAGAIN;
        \t\tgoto out;
        \t}

        \t*state = (struct mt6797_a72_provider_snapshot) {
        \t\t.abi = MT6797_A72_PROVIDER_STATE_ABI,
        \t\t.valid = 1,
        \t\t.control_a = second.control_a,
        \t\t.status_b = second.status_b,
        \t\t.buckb_cont = second.buckb_cont,
        \t\t.vbuckb_a = second.vbuckb_a,
        \t\t.vbuckb_b = second.vbuckb_b,
        \t};
        \tret = 0;

        out:
        \tda9213_provider_restore_retries(endpoint->adapter, saved_retries);
        \ti2c_unlock_bus(endpoint->adapter, I2C_LOCK_ROOT_ADAPTER);
        \tmutex_unlock(&endpoint->lock);
        \treturn ret;
        }

        """
    )
    replace_once(driver, old_snapshot, "")

    replace_once(
        driver,
        dedent(
            """\
            static int da9213_legacy_provider_acquire(void *context,
            \tconst struct mt6797_a72_provider_request *request,
            \tstruct mt6797_a72_provider_response *response)
            {
            #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
            \tstruct da9213_legacy_provider_endpoint *endpoint = context;
            \tint ret;
            #else
            \tstruct da9213_legacy *chip = context;
            #endif
            """
        ),
        dedent(
            """\
            static int da9213_legacy_provider_acquire(void *context,
            \tconst struct mt6797_a72_provider_request *request,
            \tstruct mt6797_a72_provider_response *response)
            {
            \tstruct da9213_legacy_provider_endpoint *endpoint = context;
            #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
            \tint ret;
            #endif
            """
        ),
    )
    replace_once(
        driver,
        "\tdev_dbg(chip->dev,\n"
        '\t\t"provider-owner acquire refused: read-only resource boundary\\n");\n',
        "\tif (endpoint->dev)\n"
        "\t\tdev_dbg(endpoint->dev,\n"
        '\t\t\t"provider-owner acquire refused: read-only resource boundary\\n");\n',
    )
    replace_once(
        driver,
        dedent(
            """\
            static int da9213_legacy_provider_release(void *context,
            \tconst struct mt6797_a72_provider_handle *handle,
            \tstruct mt6797_a72_provider_response *response)
            {
            #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
            \tstruct da9213_legacy_provider_endpoint *endpoint = context;
            \tint ret;
            #else
            \tstruct da9213_legacy *chip = context;
            #endif
            """
        ),
        dedent(
            """\
            static int da9213_legacy_provider_release(void *context,
            \tconst struct mt6797_a72_provider_handle *handle,
            \tstruct mt6797_a72_provider_response *response)
            {
            \tstruct da9213_legacy_provider_endpoint *endpoint = context;
            #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
            \tint ret;
            #endif
            """
        ),
    )
    replace_once(
        driver,
        "\tdev_dbg(chip->dev,\n"
        '\t\t"provider-owner release refused: no rollback owner\\n");\n',
        "\tif (endpoint->dev)\n"
        "\t\tdev_dbg(endpoint->dev,\n"
        '\t\t\t"provider-owner release refused: no rollback owner\\n");\n',
    )
    replace_once(
        driver,
        "\t.release = da9213_legacy_provider_release,\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\t.snapshot = da9213_provider_snapshot,\n"
        "#endif\n",
        "\t.release = da9213_legacy_provider_release,\n"
        "\t.snapshot = da9213_provider_snapshot,\n",
    )
    replace_once(
        driver,
        "\tmemset(endpoint, 0, sizeof(*endpoint));\n"
        "\tendpoint->adapter = adapter;\n"
        "\tendpoint->address = address;\n"
        "\tendpoint->ops = ops;\n",
        "\tmemset(endpoint, 0, sizeof(*endpoint));\n"
        "\tendpoint->adapter = adapter;\n"
        "\tendpoint->address = address;\n"
        "\tendpoint->read_transfer = ops->transfer;\n"
        "\tendpoint->ops = ops;\n",
    )

    test_seam = dedent(
        """\
        #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER_SNAPSHOT_KUNIT_TEST)
        int
        da9213_provider_snapshot_test_register(struct da9213_legacy_provider_endpoint
        \t\t\t\t\t       *endpoint,
        \tstruct i2c_adapter *adapter, u16 address,
        \tda9213_provider_read_transfer_t read_transfer)
        {
        \tif (!endpoint || !adapter || !read_transfer)
        \t\treturn -EINVAL;

        \tmemset(endpoint, 0, sizeof(*endpoint));
        \tendpoint->adapter = adapter;
        \tendpoint->address = address;
        \tendpoint->read_transfer = read_transfer;
        \tmutex_init(&endpoint->lock);
        \treturn mt6797_a72_provider_register(&da9213_legacy_provider_ops,
        \t\t\t\t\t    endpoint);
        }

        void
        da9213_provider_snapshot_test_unregister(struct da9213_legacy_provider_endpoint
        \t\t\t\t\t\t *endpoint)
        {
        \tmt6797_a72_provider_unregister(&da9213_legacy_provider_ops, endpoint);
        }
        #endif

        """
    )
    replace_once(
        driver,
        "static void da9213_legacy_provider_unregister(void *context)\n",
        test_seam + "static void da9213_legacy_provider_unregister(void *context)\n",
    )
    replace_once(
        driver,
        dedent(
            """\
            static int da9213_legacy_register_owner(struct da9213_legacy *chip)
            {
            \tvoid *context = chip;
            \tint ret;

            #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
            \tchip->provider_endpoint.adapter = chip->client->adapter;
            \tchip->provider_endpoint.address = chip->client->addr;
            \tchip->provider_endpoint.ops = &da9213_legacy_positive_provider_ops;
            \tmutex_init(&chip->provider_endpoint.lock);
            \tcontext = &chip->provider_endpoint;
            #endif
            \tret = mt6797_a72_provider_register(&da9213_legacy_provider_ops,
            \t\t\t\t\t   context);
            """
        ),
        dedent(
            """\
            static int da9213_legacy_register_owner(struct da9213_legacy *chip)
            {
            \tvoid *context = &chip->provider_endpoint;
            \tint ret;

            \tchip->provider_endpoint.dev = chip->dev;
            \tchip->provider_endpoint.adapter = chip->client->adapter;
            \tchip->provider_endpoint.address = chip->client->addr;
            \tchip->provider_endpoint.read_transfer = __i2c_transfer;
            \tmutex_init(&chip->provider_endpoint.lock);
            #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
            \tchip->provider_endpoint.ops = &da9213_legacy_positive_provider_ops;
            #endif
            \tret = mt6797_a72_provider_register(&da9213_legacy_provider_ops,
            \t\t\t\t\t   context);
            """
        ),
    )


def apply_tests(root: Path) -> None:
    kconfig = root / "drivers/regulator/Kconfig"
    makefile = root / "drivers/regulator/Makefile"
    test = root / "drivers/regulator/da9213-legacy-provider-snapshot-test.c"

    entry = dedent(
        """\
        config REGULATOR_DA9213_LEGACY_PROVIDER_SNAPSHOT_KUNIT_TEST
        \tbool "KUnit tests for the read-only legacy DA921x provider snapshot"
        \tdepends on KUNIT=y
        \tdepends on REGULATOR_DA9213_LEGACY=y
        \tdepends on ARM64_MT6797_A72_PROVIDER_OWNER
        \tdepends on !REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION
        \tdepends on !MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW
        \thelp
        \t  Exercise the production stable provider snapshot with an
        \t  unregistered in-memory adapter. Cover exact two-sample success,
        \t  every negative and short transfer at all ten read ordinals, every
        \t  second-sample byte mismatch, exact registry lifetime, and read-only
        \t  acquire/release refusal.

        \t  This selection compiles no positive provider transaction or
        \t  firmware-writer transaction window. It performs no physical I2C,
        \t  register write, MMIO, firmware call, CPU request, or device action.

        """
    )
    replace_once(
        kconfig,
        "config REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST\n",
        entry + "config REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST\n",
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST) += da9213-legacy-provider-test.o\n",
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST) += da9213-legacy-provider-test.o\n"
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER_SNAPSHOT_KUNIT_TEST) += \\\n"
        "\tda9213-legacy-provider-snapshot-test.o\n",
    )
    if test.exists():
        raise SystemExit(f"{test}: refusing to overwrite existing test")
    test.write_text(
        (SOURCE_DIR / "da9213-legacy-provider-snapshot-test.c").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("core", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    if args.phase == "core":
        apply_core(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
