#!/usr/bin/env python3
"""Apply deterministic read-only DA921x provider-state export changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first_line = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one edit anchor beginning {first_line!r}, "
            f"found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply_registry(root: Path) -> None:
    header = root / "include/linux/mt6797-a72-provider.h"
    membership = root / "arch/arm64/kernel/mt6797_a72_membership.c"

    replace_once(
        header,
        "#define MT6797_A72_PROVIDER_CALL_BUCKB_VSEL\t0x46\n",
        "#define MT6797_A72_PROVIDER_CALL_BUCKB_VSEL\t0x46\n"
        "#define MT6797_A72_PROVIDER_STATE_ABI\t\t1\n",
    )
    replace_once(
        header,
        dedent("""\
        struct mt6797_a72_provider_ops {
        \tint (*acquire)(void *context,
        \t\t\tconst struct mt6797_a72_provider_request *request,
        \t\t\tstruct mt6797_a72_provider_response *response);
        \tint (*release)(void *context,
        \t\t\tconst struct mt6797_a72_provider_handle *handle,
        \t\t\tstruct mt6797_a72_provider_response *response);
        };
        """),
        dedent("""\
        struct mt6797_a72_provider_state {
        \tu32 abi;
        \tu32 valid;
        \tu32 control_a;
        \tu32 status_b;
        \tu32 buckb_cont;
        \tu32 vbuckb_a;
        \tu32 vbuckb_b;
        \tu32 reserved;
        };

        struct mt6797_a72_provider_ops {
        \tint (*acquire)(void *context,
        \t\t\tconst struct mt6797_a72_provider_request *request,
        \t\t\tstruct mt6797_a72_provider_response *response);
        \tint (*release)(void *context,
        \t\t\tconst struct mt6797_a72_provider_handle *handle,
        \t\t\tstruct mt6797_a72_provider_response *response);
        \tint (*snapshot)(void *context,
        \t\t\tstruct mt6797_a72_provider_state *state);
        };
        """),
    )
    replace_once(
        header,
        dedent("""\
        int mt6797_a72_provider_release(const struct mt6797_a72_provider_handle *handle,
        \t\t\t\t\tstruct mt6797_a72_provider_response *response);

        #endif /* __LINUX_MT6797_A72_PROVIDER_H */
        """),
        dedent("""\
        int mt6797_a72_provider_release(const struct mt6797_a72_provider_handle *handle,
        \t\t\t\t\tstruct mt6797_a72_provider_response *response);
        int mt6797_a72_provider_snapshot(struct mt6797_a72_provider_state *state);

        #endif /* __LINUX_MT6797_A72_PROVIDER_H */
        """),
    )

    release = dedent("""\
    EXPORT_SYMBOL_GPL(mt6797_a72_provider_release);

    struct mt6797_a72_owner_state {
    """)
    snapshot = dedent("""\
    EXPORT_SYMBOL_GPL(mt6797_a72_provider_release);

    int mt6797_a72_provider_snapshot(struct mt6797_a72_provider_state *state)
    {
    \tstruct mt6797_a72_provider_state observed = { };
    \tu32 raw;
    \tint ret;

    \tif (!state)
    \t\treturn -EINVAL;
    \tmemset(state, 0, sizeof(*state));

    \tmutex_lock(&a72_provider_registry_lock);
    \tif (!a72_provider_ops)
    \t\tret = -ENODEV;
    \telse if (!a72_provider_ops->snapshot)
    \t\tret = -EOPNOTSUPP;
    \telse
    \t\tret = a72_provider_ops->snapshot(a72_provider_context,
    \t\t\t\t\t\t &observed);
    \tif (!ret) {
    \t\traw = observed.control_a | observed.status_b |
    \t\t\tobserved.buckb_cont | observed.vbuckb_a |
    \t\t\tobserved.vbuckb_b;
    \t\tif (observed.abi != MT6797_A72_PROVIDER_STATE_ABI ||
    \t\t    observed.valid != 1 || observed.reserved ||
    \t\t    (raw & ~0xffU))
    \t\t\tret = -EPROTO;
    \t\telse
    \t\t\t*state = observed;
    \t}
    \tmutex_unlock(&a72_provider_registry_lock);

    \treturn ret;
    }
    EXPORT_SYMBOL_GPL(mt6797_a72_provider_snapshot);

    struct mt6797_a72_owner_state {
    """)
    replace_once(membership, release, snapshot)


def apply_provider(root: Path) -> None:
    driver = root / "drivers/regulator/da9213-legacy-regulator.c"

    replace_once(
        driver,
        "#include <linux/regulator/driver.h>\n",
        "#include <linux/regulator/driver.h>\n#include <linux/string.h>\n",
    )
    anchor = dedent("""\
    static const struct da9213_legacy_provider_transport_ops
    da9213_legacy_positive_provider_ops = {
    \t.transfer = __i2c_transfer,
    \t.delay = usleep_range,
    };
    """)
    implementation = dedent("""\
    static int
    da9213_legacy_provider_state_snapshot(void *context,
    \t\t\t\t\t struct mt6797_a72_provider_state *state)
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

    \t*state = (struct mt6797_a72_provider_state) {
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

    static const struct da9213_legacy_provider_transport_ops
    da9213_legacy_positive_provider_ops = {
    \t.transfer = __i2c_transfer,
    \t.delay = usleep_range,
    };
    """)
    replace_once(driver, anchor, implementation)
    replace_once(
        driver,
        dedent("""\
        static const struct mt6797_a72_provider_ops da9213_legacy_provider_ops = {
        \t.acquire = da9213_legacy_provider_acquire,
        \t.release = da9213_legacy_provider_release,
        };
        """),
        dedent("""\
        static const struct mt6797_a72_provider_ops da9213_legacy_provider_ops = {
        \t.acquire = da9213_legacy_provider_acquire,
        \t.release = da9213_legacy_provider_release,
        #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
        \t.snapshot = da9213_legacy_provider_state_snapshot,
        #endif
        };
        """),
    )


def apply_tests(root: Path) -> None:
    test = root / "drivers/regulator/da9213-legacy-membership-test.c"

    replace_once(
        test,
        "#define DA9213_MEMBERSHIP_P29_MUTATIONS\t9\n",
        "#define DA9213_MEMBERSHIP_P29_MUTATIONS\t9\n"
        "#define DA9213_PROVIDER_SNAPSHOT_ACTIONS\t10\n",
    )
    replace_once(
        test,
        "\tunsigned int write_count;\n",
        "\tunsigned int write_count;\n\tbool mutate_snapshot;\n",
    )
    replace_once(
        test,
        dedent("""\
        \t\treg = messages[0].buf[0];
        \t\tmessages[1].buf[0] = fake->registers[reg];
        \t\treturn 2;
        """),
        dedent("""\
        \t\treg = messages[0].buf[0];
        \t\tif (fake->mutate_snapshot && fake->operation_calls == 6)
        \t\t\tfake->registers[reg] ^= 1;
        \t\tmessages[1].buf[0] = fake->registers[reg];
        \t\treturn 2;
        """),
    )

    anchor = "static void da9213_membership_positive_abort_success(struct kunit *test)\n"
    tests = dedent("""\
    static void
    da9213_provider_snapshot_expect_zero(struct kunit *test,
    \t\t\t\t\tconst struct mt6797_a72_provider_state *state)
    {
    \tstruct mt6797_a72_provider_state zero = { };

    \tKUNIT_EXPECT_EQ(test, memcmp(state, &zero, sizeof(*state)), 0);
    }

    static void da9213_provider_snapshot_success(struct kunit *test)
    {
    \tstruct mt6797_a72_provider_state observed;
    \tstruct da9213_membership_test_state *state;
    \tint ret;

    \tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
    \tKUNIT_ASSERT_NOT_NULL(test, state);
    \tda9213_membership_fake_init(&state->fake);
    \tret = da9213_membership_register_state(state);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tmemset(&observed, 0xa5, sizeof(observed));
    \tret = mt6797_a72_provider_snapshot(&observed);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_EQ(test, observed.abi,
    \t\t\tMT6797_A72_PROVIDER_STATE_ABI);
    \tKUNIT_EXPECT_EQ(test, observed.valid, 1U);
    \tKUNIT_EXPECT_EQ(test, observed.control_a, 0x7bU);
    \tKUNIT_EXPECT_EQ(test, observed.status_b, 0xc1U);
    \tKUNIT_EXPECT_EQ(test, observed.buckb_cont, 0U);
    \tKUNIT_EXPECT_EQ(test, observed.vbuckb_a, 0x46U);
    \tKUNIT_EXPECT_EQ(test, observed.vbuckb_b, 0x46U);
    \tKUNIT_EXPECT_EQ(test, observed.reserved, 0U);
    \tKUNIT_EXPECT_EQ(test, state->fake.operation_calls,
    \t\t\tDA9213_PROVIDER_SNAPSHOT_ACTIONS);
    \tKUNIT_EXPECT_EQ(test, state->fake.total_calls,
    \t\t\tDA9213_PROVIDER_SNAPSHOT_ACTIONS);
    \tKUNIT_EXPECT_EQ(test, state->fake.lock_calls, 1U);
    \tKUNIT_EXPECT_EQ(test, state->fake.unlock_calls, 1U);
    \tKUNIT_EXPECT_EQ(test, state->fake.write_count, 0U);
    \tKUNIT_EXPECT_EQ(test, state->fake.delay_calls, 0U);
    \tKUNIT_EXPECT_FALSE(test, state->fake.transfer_unlocked);
    \tKUNIT_EXPECT_FALSE(test, state->fake.retry_nonzero);
    \tKUNIT_EXPECT_EQ(test, state->fake.adapter.retries,
    \t\t\tDA9213_MEMBERSHIP_TEST_RETRIES);
    \tKUNIT_EXPECT_EQ(test, state->endpoint.transaction.total_transfers, 0U);
    \tda9213_membership_unregister_endpoint();
    }

    static void da9213_provider_snapshot_transport_faults(struct kunit *test)
    {
    \tstruct da9213_membership_test_state *state;
    \tunsigned int mode;
    \tunsigned int ordinal;

    \tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
    \tKUNIT_ASSERT_NOT_NULL(test, state);
    \tfor (mode = 0; mode < 2; mode++) {
    \t\tfor (ordinal = 1; ordinal <= DA9213_PROVIDER_SNAPSHOT_ACTIONS;
    \t\t     ordinal++) {
    \t\t\tstruct mt6797_a72_provider_state observed;
    \t\t\tint ret;

    \t\t\tda9213_membership_fake_init(&state->fake);
    \t\t\tif (mode)
    \t\t\t\tstate->fake.short_ordinal = ordinal;
    \t\t\telse
    \t\t\t\tstate->fake.fail_ordinal = ordinal;
    \t\t\tret = da9213_membership_register_state(state);
    \t\t\tKUNIT_ASSERT_EQ(test, ret, 0);
    \t\t\tmemset(&observed, 0xa5, sizeof(observed));
    \t\t\tret = mt6797_a72_provider_snapshot(&observed);
    \t\t\tKUNIT_EXPECT_LT_MSG(test, ret, 0,
    \t\t\t\t\t    "mode=%u ordinal=%u", mode,
    \t\t\t\t\t    ordinal);
    \t\t\tda9213_provider_snapshot_expect_zero(test, &observed);
    \t\t\tKUNIT_EXPECT_EQ(test, state->fake.operation_calls,
    \t\t\t\t\tordinal);
    \t\t\tKUNIT_EXPECT_EQ(test, state->fake.lock_calls, 1U);
    \t\t\tKUNIT_EXPECT_EQ(test, state->fake.unlock_calls, 1U);
    \t\t\tKUNIT_EXPECT_EQ(test, state->fake.write_count, 0U);
    \t\t\tKUNIT_EXPECT_EQ(test, state->fake.delay_calls, 0U);
    \t\t\tKUNIT_EXPECT_FALSE(test, state->fake.transfer_unlocked);
    \t\t\tKUNIT_EXPECT_FALSE(test, state->fake.retry_nonzero);
    \t\t\tKUNIT_EXPECT_EQ(test, state->fake.adapter.retries,
    \t\t\t\t\tDA9213_MEMBERSHIP_TEST_RETRIES);
    \t\t\tda9213_membership_unregister_endpoint();
    \t\t}
    \t}
    }

    static void da9213_provider_snapshot_unstable(struct kunit *test)
    {
    \tstruct mt6797_a72_provider_state observed;
    \tstruct da9213_membership_test_state *state;
    \tint ret;

    \tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
    \tKUNIT_ASSERT_NOT_NULL(test, state);
    \tda9213_membership_fake_init(&state->fake);
    \tstate->fake.mutate_snapshot = true;
    \tret = da9213_membership_register_state(state);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tmemset(&observed, 0xa5, sizeof(observed));
    \tret = mt6797_a72_provider_snapshot(&observed);
    \tKUNIT_EXPECT_EQ(test, ret, -EAGAIN);
    \tda9213_provider_snapshot_expect_zero(test, &observed);
    \tKUNIT_EXPECT_EQ(test, state->fake.operation_calls,
    \t\t\tDA9213_PROVIDER_SNAPSHOT_ACTIONS);
    \tKUNIT_EXPECT_EQ(test, state->fake.lock_calls, 1U);
    \tKUNIT_EXPECT_EQ(test, state->fake.unlock_calls, 1U);
    \tKUNIT_EXPECT_EQ(test, state->fake.write_count, 0U);
    \tKUNIT_EXPECT_EQ(test, state->fake.delay_calls, 0U);
    \tda9213_membership_unregister_endpoint();
    }

    static void da9213_provider_snapshot_registry_guards(struct kunit *test)
    {
    \tstruct da9213_membership_test_state *state;
    \tstruct mt6797_a72_provider_state observed;
    \tint ret;

    \tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
    \tKUNIT_ASSERT_NOT_NULL(test, state);
    \tret = mt6797_a72_provider_snapshot(NULL);
    \tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
    \tmemset(&observed, 0xa5, sizeof(observed));
    \tret = mt6797_a72_provider_snapshot(&observed);
    \tKUNIT_EXPECT_EQ(test, ret, -ENODEV);
    \tda9213_provider_snapshot_expect_zero(test, &observed);

    \tret = da9213_membership_register_synthetic(&state->synthetic);
    \tKUNIT_ASSERT_EQ(test, ret, 0);
    \tmemset(&observed, 0xa5, sizeof(observed));
    \tret = mt6797_a72_provider_snapshot(&observed);
    \tKUNIT_EXPECT_EQ(test, ret, -EOPNOTSUPP);
    \tda9213_provider_snapshot_expect_zero(test, &observed);
    \tda9213_membership_unregister_synthetic();
    }

    static void da9213_membership_positive_abort_success(struct kunit *test)
    """)
    replace_once(test, anchor, tests)

    replace_once(
        test,
        dedent("""\
        static struct kunit_case da9213_membership_test_cases[] = {
        \tKUNIT_CASE(da9213_membership_positive_abort_success),
        """),
        dedent("""\
        static struct kunit_case da9213_membership_test_cases[] = {
        \tKUNIT_CASE(da9213_provider_snapshot_success),
        \tKUNIT_CASE(da9213_provider_snapshot_transport_faults),
        \tKUNIT_CASE(da9213_provider_snapshot_unstable),
        \tKUNIT_CASE(da9213_provider_snapshot_registry_guards),
        \tKUNIT_CASE(da9213_membership_positive_abort_success),
        """),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--step", choices=("registry", "provider", "tests"),
                        required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    if args.step == "registry":
        apply_registry(root)
    elif args.step == "provider":
        apply_provider(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
