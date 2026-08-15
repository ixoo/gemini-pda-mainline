#!/usr/bin/env python3
"""Apply the deterministic DA921x read-only observer source change."""

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one edit anchor, found {count}")
    path.write_text(text.replace(old, new, 1))


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def edit_kconfig(root: Path) -> None:
    path = root / "drivers/regulator/Kconfig"
    anchor = dedent("""\
    \t  This is an offline/provider-boundary experiment. It does not establish
    \t  rail ownership, constraints, rollback, suspend/resume, or CPU bring-up.

    config REGULATOR_DBX500_PRCMU
    """)
    replacement = dedent("""\
    \t  This is an offline/provider-boundary experiment. It does not establish
    \t  rail ownership, constraints, rollback, suspend/resume, or CPU bring-up.

    config REGULATOR_DA9213_LEGACY_OBSERVER
    \tbool "Dialog legacy DA921x read-only provider observer"
    \tdepends on REGULATOR_DA9213_LEGACY_PROVIDER
    \thelp
    \t  Emit one attributable record after the fixed identity transcript and
    \t  both read-only regulator descriptors are registered. The observation
    \t  samples only selector, linear voltage, and enable state and fails probe
    \t  rather than publishing a partial result.

    \t  This default-off diagnostic adds no writable regulator operation,
    \t  consumer, register-data write, transition owner, or CPU action.

    config REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST
    \tbool "KUnit tests for the legacy DA921x read-only observer"
    \tdepends on KUNIT=y
    \tdepends on REGULATOR_DA9213_LEGACY_OBSERVER
    \thelp
    \t  Exercise the hardware-free observer success, bounded failure, semantic
    \t  validation, and cleanup contracts with a fake read callback.

    config REGULATOR_DBX500_PRCMU
    """)
    replace_once(path, anchor, replacement)


def edit_makefile(root: Path) -> None:
    path = root / "drivers/regulator/Makefile"
    replace_once(
        path,
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY) += da9213-legacy-regulator.o\n",
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY) += da9213-legacy-regulator.o\n"
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER_KUNIT_TEST) += "
        "da9213-legacy-observer-test.o\n",
    )


def observer_header() -> str:
    return dedent("""\
    /* SPDX-License-Identifier: GPL-2.0-only */
    #ifndef __DA9213_LEGACY_OBSERVER_H
    #define __DA9213_LEGACY_OBSERVER_H

    #include <linux/types.h>

    #define DA9213_LEGACY_BUCK_COUNT\t2
    #define DA9213_LEGACY_MIN_UV\t\t300000
    #define DA9213_LEGACY_MAX_UV\t\t1570000
    #define DA9213_LEGACY_STEP_UV\t\t10000
    #define DA9213_LEGACY_VSEL_MASK\t0x7f
    #define DA9213_LEGACY_ENABLE_MASK\t0x01

    enum da9213_legacy_observer_field {
    \tDA9213_LEGACY_OBSERVER_SELECTOR,
    \tDA9213_LEGACY_OBSERVER_ENABLED,
    };

    struct da9213_legacy_observer_buck {
    \tunsigned int selector;
    \tunsigned int microvolts;
    \tunsigned int enabled;
    };

    struct da9213_legacy_observation {
    \tbool valid;
    \tunsigned int identity_reads;
    \tunsigned int provider_count;
    \tunsigned int provider_read_attempts;
    \tunsigned int provider_read_completed;
    \tunsigned int register_data_writes;
    \tstruct da9213_legacy_observer_buck buck[DA9213_LEGACY_BUCK_COUNT];
    };

    typedef int (*da9213_legacy_observer_read_fn)(
    \tvoid *context, unsigned int buck,
    \tenum da9213_legacy_observer_field field, unsigned int *value);

    int da9213_legacy_observer_collect(
    \tda9213_legacy_observer_read_fn read, void *context,
    \tunsigned int identity_reads, unsigned int provider_count,
    \tstruct da9213_legacy_observation *observation);
    void da9213_legacy_observer_cleanup_state(
    \tstruct da9213_legacy_observation *observation);

    #endif /* __DA9213_LEGACY_OBSERVER_H */
    """)


def observer_test() -> str:
    return dedent("""\
    // SPDX-License-Identifier: GPL-2.0-only
    /* Hardware-free tests for the legacy DA921x read-only observer. */

    #include <kunit/test.h>
    #include <linux/errno.h>
    #include <linux/module.h>

    #include "da9213-legacy-observer.h"

    struct da9213_legacy_observer_fake {
    \tint fail_at;
    \tunsigned int calls;
    \tunsigned int values[4];
    };

    static int da9213_legacy_observer_fake_read(
    \tvoid *context, unsigned int buck,
    \tenum da9213_legacy_observer_field field, unsigned int *value)
    {
    \tstruct da9213_legacy_observer_fake *fake = context;
    \tunsigned int expected_buck = fake->calls / 2;
    \tenum da9213_legacy_observer_field expected_field =
    \t\tfake->calls % 2 ? DA9213_LEGACY_OBSERVER_ENABLED :
    \t\t\t\t  DA9213_LEGACY_OBSERVER_SELECTOR;
    \tunsigned int call = fake->calls++;

    \tif (buck != expected_buck || field != expected_field)
    \t\treturn -EINVAL;
    \tif (call == fake->fail_at)
    \t\treturn -EIO;

    \t*value = fake->values[call];
    \treturn 0;
    }

    static struct da9213_legacy_observer_fake
    da9213_legacy_observer_valid_fake(void)
    {
    \tstruct da9213_legacy_observer_fake fake = {
    \t\t.fail_at = -1,
    \t\t.values = { 42, 1, 70, 0 },
    \t};

    \treturn fake;
    }

    static void da9213_legacy_observer_records_both_bucks(struct kunit *test)
    {
    \tstruct da9213_legacy_observer_fake fake =
    \t\tda9213_legacy_observer_valid_fake();
    \tstruct da9213_legacy_observation observation;
    \tint ret;

    \tret = da9213_legacy_observer_collect(
    \t\tda9213_legacy_observer_fake_read, &fake, 14, 2,
    \t\t&observation);

    \tKUNIT_EXPECT_EQ(test, ret, 0);
    \tKUNIT_EXPECT_TRUE(test, observation.valid);
    \tKUNIT_EXPECT_EQ(test, observation.identity_reads, 14U);
    \tKUNIT_EXPECT_EQ(test, observation.provider_count, 2U);
    \tKUNIT_EXPECT_EQ(test, observation.provider_read_attempts, 4U);
    \tKUNIT_EXPECT_EQ(test, observation.provider_read_completed, 4U);
    \tKUNIT_EXPECT_EQ(test, observation.register_data_writes, 0U);
    \tKUNIT_EXPECT_EQ(test, observation.buck[0].selector, 42U);
    \tKUNIT_EXPECT_EQ(test, observation.buck[0].microvolts, 720000U);
    \tKUNIT_EXPECT_EQ(test, observation.buck[0].enabled, 1U);
    \tKUNIT_EXPECT_EQ(test, observation.buck[1].selector, 70U);
    \tKUNIT_EXPECT_EQ(test, observation.buck[1].microvolts, 1000000U);
    \tKUNIT_EXPECT_EQ(test, observation.buck[1].enabled, 0U);
    }

    static void da9213_legacy_observer_bounds_read_failures(struct kunit *test)
    {
    \tunsigned int fail_at;

    \tfor (fail_at = 0; fail_at < 4; fail_at++) {
    \t\tstruct da9213_legacy_observer_fake fake =
    \t\t\tda9213_legacy_observer_valid_fake();
    \t\tstruct da9213_legacy_observation observation;
    \t\tint ret;

    \t\tfake.fail_at = fail_at;
    \t\tret = da9213_legacy_observer_collect(
    \t\t\tda9213_legacy_observer_fake_read, &fake, 14, 2,
    \t\t\t&observation);

    \t\tKUNIT_EXPECT_EQ(test, ret, -EIO);
    \t\tKUNIT_EXPECT_FALSE(test, observation.valid);
    \t\tKUNIT_EXPECT_EQ(test, observation.provider_read_attempts,
    \t\t\t\tfail_at + 1);
    \t\tKUNIT_EXPECT_EQ(test, observation.provider_read_completed,
    \t\t\t\tfail_at);
    \t\tKUNIT_EXPECT_EQ(test, observation.register_data_writes, 0U);
    \t}
    }

    static void da9213_legacy_observer_rejects_incomplete_state(
    \tstruct kunit *test)
    {
    \tstruct da9213_legacy_observer_fake fake =
    \t\tda9213_legacy_observer_valid_fake();
    \tstruct da9213_legacy_observation observation;

    \tKUNIT_EXPECT_EQ(test, da9213_legacy_observer_collect(
    \t\tda9213_legacy_observer_fake_read, &fake, 13, 2,
    \t\t&observation), -EINVAL);
    \tKUNIT_EXPECT_EQ(test, fake.calls, 0U);
    \tKUNIT_EXPECT_FALSE(test, observation.valid);

    \tKUNIT_EXPECT_EQ(test, da9213_legacy_observer_collect(
    \t\tda9213_legacy_observer_fake_read, &fake, 14, 1,
    \t\t&observation), -EINVAL);
    \tKUNIT_EXPECT_EQ(test, fake.calls, 0U);
    \tKUNIT_EXPECT_FALSE(test, observation.valid);
    }

    static void da9213_legacy_observer_rejects_invalid_values(
    \tstruct kunit *test)
    {
    \tstruct da9213_legacy_observer_fake fake =
    \t\tda9213_legacy_observer_valid_fake();
    \tstruct da9213_legacy_observation observation;

    \tfake.values[0] = DA9213_LEGACY_VSEL_MASK + 1;
    \tKUNIT_EXPECT_EQ(test, da9213_legacy_observer_collect(
    \t\tda9213_legacy_observer_fake_read, &fake, 14, 2,
    \t\t&observation), -ERANGE);
    \tKUNIT_EXPECT_FALSE(test, observation.valid);
    \tKUNIT_EXPECT_EQ(test, observation.provider_read_attempts, 1U);
    \tKUNIT_EXPECT_EQ(test, observation.provider_read_completed, 1U);

    \tfake = da9213_legacy_observer_valid_fake();
    \tfake.values[1] = 2;
    \tKUNIT_EXPECT_EQ(test, da9213_legacy_observer_collect(
    \t\tda9213_legacy_observer_fake_read, &fake, 14, 2,
    \t\t&observation), -ERANGE);
    \tKUNIT_EXPECT_FALSE(test, observation.valid);
    \tKUNIT_EXPECT_EQ(test, observation.provider_read_attempts, 2U);
    \tKUNIT_EXPECT_EQ(test, observation.provider_read_completed, 2U);
    \tKUNIT_EXPECT_EQ(test, observation.register_data_writes, 0U);
    }

    static void da9213_legacy_observer_invalidates_on_cleanup(
    \tstruct kunit *test)
    {
    \tstruct da9213_legacy_observer_fake fake =
    \t\tda9213_legacy_observer_valid_fake();
    \tstruct da9213_legacy_observation observation;

    \tKUNIT_ASSERT_EQ(test, da9213_legacy_observer_collect(
    \t\tda9213_legacy_observer_fake_read, &fake, 14, 2,
    \t\t&observation), 0);
    \tda9213_legacy_observer_cleanup_state(&observation);
    \tKUNIT_EXPECT_FALSE(test, observation.valid);
    \tKUNIT_EXPECT_EQ(test, observation.provider_count, 0U);
    \tKUNIT_EXPECT_EQ(test, observation.register_data_writes, 0U);
    }

    static struct kunit_case da9213_legacy_observer_test_cases[] = {
    \tKUNIT_CASE(da9213_legacy_observer_records_both_bucks),
    \tKUNIT_CASE(da9213_legacy_observer_bounds_read_failures),
    \tKUNIT_CASE(da9213_legacy_observer_rejects_incomplete_state),
    \tKUNIT_CASE(da9213_legacy_observer_rejects_invalid_values),
    \tKUNIT_CASE(da9213_legacy_observer_invalidates_on_cleanup),
    \t{ }
    };

    static struct kunit_suite da9213_legacy_observer_test_suite = {
    \t.name = "da9213-legacy-observer",
    \t.test_cases = da9213_legacy_observer_test_cases,
    };

    kunit_test_suite(da9213_legacy_observer_test_suite);

    MODULE_LICENSE("GPL");
    """)


def edit_driver(root: Path) -> None:
    path = root / "drivers/regulator/da9213-legacy-regulator.c"

    replace_once(
        path,
        "#include <linux/regulator/driver.h>\n",
        "#include <linux/regulator/driver.h>\n\n"
        "#include \"da9213-legacy-observer.h\"\n",
    )
    replace_once(
        path,
        "#define DA9213_LEGACY_BUCK_COUNT\t2\n"
        "#define DA9213_LEGACY_MIN_UV\t\t300000\n"
        "#define DA9213_LEGACY_MAX_UV\t\t1570000\n"
        "#define DA9213_LEGACY_STEP_UV\t\t10000\n"
        "#define DA9213_LEGACY_VSEL_MASK\t\t0x7f\n"
        "#define DA9213_LEGACY_ENABLE_MASK\t0x01\n\n",
        "",
    )
    replace_once(
        path,
        "\tstruct regulator_dev *rdev[2];\n#endif\n};\n",
        "\tstruct regulator_dev *rdev[2];\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER)\n"
        "\tunsigned int provider_count;\n"
        "\tbool observer_bound;\n"
        "\tstruct da9213_legacy_observation observation;\n"
        "#endif\n#endif\n};\n",
    )
    replace_once(
        path,
        "\t\tif (IS_ERR(chip->rdev[i]))\n"
        "\t\t\treturn PTR_ERR(chip->rdev[i]);\n"
        "\t}\n\n\treturn 0;\n}\n\n",
        "\t\tif (IS_ERR(chip->rdev[i]))\n"
        "\t\t\treturn PTR_ERR(chip->rdev[i]);\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER)\n"
        "\t\tchip->provider_count++;\n"
        "#endif\n"
        "\t}\n\n\treturn 0;\n}\n\n",
    )

    observer_code = dedent("""\
    #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER)

    int da9213_legacy_observer_collect(
    \tda9213_legacy_observer_read_fn read, void *context,
    \tunsigned int identity_reads, unsigned int provider_count,
    \tstruct da9213_legacy_observation *observation)
    {
    \tunsigned int buck;

    \tif (!observation)
    \t\treturn -EINVAL;

    \tmemset(observation, 0, sizeof(*observation));
    \tobservation->identity_reads = identity_reads;
    \tobservation->provider_count = provider_count;
    \tif (!read || identity_reads != DA9213_LEGACY_PASSES *
    \t\t\t\t\t ARRAY_SIZE(da9213_legacy_samples) ||
    \t    provider_count != DA9213_LEGACY_BUCK_COUNT)
    \t\treturn -EINVAL;

    \tfor (buck = 0; buck < DA9213_LEGACY_BUCK_COUNT; buck++) {
    \t\tunsigned int value;
    \t\tint ret;

    \t\tobservation->provider_read_attempts++;
    \t\tret = read(context, buck, DA9213_LEGACY_OBSERVER_SELECTOR,
    \t\t\t   &value);
    \t\tif (ret)
    \t\t\treturn ret;
    \t\tobservation->provider_read_completed++;
    \t\tif (value > DA9213_LEGACY_VSEL_MASK)
    \t\t\treturn -ERANGE;
    \t\tobservation->buck[buck].selector = value;
    \t\tobservation->buck[buck].microvolts =
    \t\t\tDA9213_LEGACY_MIN_UV + value * DA9213_LEGACY_STEP_UV;
    \t\tif (observation->buck[buck].microvolts >
    \t\t    DA9213_LEGACY_MAX_UV)
    \t\t\treturn -ERANGE;

    \t\tobservation->provider_read_attempts++;
    \t\tret = read(context, buck, DA9213_LEGACY_OBSERVER_ENABLED,
    \t\t\t   &value);
    \t\tif (ret)
    \t\t\treturn ret;
    \t\tobservation->provider_read_completed++;
    \t\tif (value > 1)
    \t\t\treturn -ERANGE;
    \t\tobservation->buck[buck].enabled = value;
    \t}

    \tobservation->valid = true;
    \treturn 0;
    }

    void da9213_legacy_observer_cleanup_state(
    \tstruct da9213_legacy_observation *observation)
    {
    \tif (!observation)
    \t\treturn;

    \tobservation->valid = false;
    \tobservation->provider_count = 0;
    }

    static int da9213_legacy_observer_read(
    \tvoid *context, unsigned int buck,
    \tenum da9213_legacy_observer_field field, unsigned int *value)
    {
    \tstruct da9213_legacy *chip = context;
    \tint ret;

    \tif (!chip || !value || buck >= chip->provider_count)
    \t\treturn -EINVAL;

    \tswitch (field) {
    \tcase DA9213_LEGACY_OBSERVER_SELECTOR:
    \t\tret = da9213_legacy_get_voltage_sel(chip->rdev[buck]);
    \t\tbreak;
    \tcase DA9213_LEGACY_OBSERVER_ENABLED:
    \t\tret = da9213_legacy_is_enabled(chip->rdev[buck]);
    \t\tbreak;
    \tdefault:
    \t\treturn -EINVAL;
    \t}
    \tif (ret < 0)
    \t\treturn ret;

    \t*value = ret;
    \treturn 0;
    }

    static void da9213_legacy_observer_cleanup(void *context)
    {
    \tstruct da9213_legacy *chip = context;
    \tunsigned int providers = chip->observation.provider_count;

    \tda9213_legacy_observer_cleanup_state(&chip->observation);
    \tdev_info(chip->dev,
    \t\t "da921x-observer-v1 event=%s providers_released=%u "
    \t\t "register_data_writes=%u\\n",
    \t\t chip->observer_bound ? "unbind" : "failed-probe",
    \t\t providers, chip->observation.register_data_writes);
    }

    static int da9213_legacy_observer_prepare(struct da9213_legacy *chip)
    {
    \treturn devm_add_action(chip->dev, da9213_legacy_observer_cleanup,
    \t\t\t       chip);
    }

    static int da9213_legacy_observer_sample(struct da9213_legacy *chip,
    \t\t\t\t     unsigned int identity_reads)
    {
    \treturn da9213_legacy_observer_collect(
    \t\tda9213_legacy_observer_read, chip, identity_reads,
    \t\tchip->provider_count, &chip->observation);
    }

    static void da9213_legacy_observer_publish(struct da9213_legacy *chip)
    {
    \tconst struct da9213_legacy_observation *observation =
    \t\t&chip->observation;

    \tchip->observer_bound = true;
    \tdev_info(chip->dev,
    \t\t "da921x-observer-v1 event=bound valid=%u identity_reads=%u "
    \t\t "providers=%u provider_read_attempts=%u "
    \t\t "provider_read_completed=%u register_data_writes=%u "
    \t\t "buck0_selector=%u buck0_uv=%u buck0_enabled=%u "
    \t\t "buck1_selector=%u buck1_uv=%u buck1_enabled=%u\\n",
    \t\t observation->valid, observation->identity_reads,
    \t\t observation->provider_count,
    \t\t observation->provider_read_attempts,
    \t\t observation->provider_read_completed,
    \t\t observation->register_data_writes,
    \t\t observation->buck[0].selector,
    \t\t observation->buck[0].microvolts,
    \t\t observation->buck[0].enabled,
    \t\t observation->buck[1].selector,
    \t\t observation->buck[1].microvolts,
    \t\t observation->buck[1].enabled);
    }

    #endif

    """)
    replace_once(
        path,
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n\n"
        "static int da9213_legacy_provider_acquire",
        observer_code
        + "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n\n"
        "static int da9213_legacy_provider_acquire",
    )

    replace_once(
        path,
        "\tunsigned int sample;\n\tint ret = 0;\n",
        "\tunsigned int sample;\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER)\n"
        "\tunsigned int identity_reads = 0;\n"
        "#endif\n"
        "\tint ret = 0;\n",
    )
    replace_once(
        path,
        "\t\t\tif (ret)\n\t\t\t\tgoto out_unlock;\n\t\t}\n",
        "\t\t\tif (ret)\n\t\t\t\tgoto out_unlock;\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER)\n"
        "\t\t\tidentity_reads++;\n"
        "#endif\n"
        "\t\t}\n",
    )
    replace_once(
        path,
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER)\n"
        "\tret = da9213_legacy_register_provider(chip);\n",
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_PROVIDER)\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER)\n"
        "\tret = da9213_legacy_observer_prepare(chip);\n"
        "\tif (ret)\n"
        "\t\treturn dev_err_probe(&client->dev, ret,\n"
        "\t\t\t\t     \"failed to prepare read-only observer\\n\");\n"
        "#endif\n"
        "\tret = da9213_legacy_register_provider(chip);\n",
    )
    replace_once(
        path,
        "\tif (ret)\n"
        "\t\treturn dev_err_probe(&client->dev, ret,\n"
        "\t\t\t\t     \"failed to register read-only provider\\n\");\n"
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n",
        "\tif (ret)\n"
        "\t\treturn dev_err_probe(&client->dev, ret,\n"
        "\t\t\t\t     \"failed to register read-only provider\\n\");\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER)\n"
        "\tret = da9213_legacy_observer_sample(chip, identity_reads);\n"
        "\tif (ret)\n"
        "\t\treturn dev_err_probe(&client->dev, ret,\n"
        "\t\t\t\t     \"read-only provider observation failed\\n\");\n"
        "#endif\n"
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n",
    )
    replace_once(
        path,
        "#endif\n#endif\n\n\tdev_info(&client->dev,\n",
        "#endif\n#endif\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_OBSERVER)\n"
        "\tda9213_legacy_observer_publish(chip);\n"
        "#endif\n\n"
        "\tdev_info(&client->dev,\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_root", type=Path)
    args = parser.parse_args()
    root = args.source_root.resolve()

    edit_kconfig(root)
    edit_makefile(root)
    write_new(root / "drivers/regulator/da9213-legacy-observer.h",
              observer_header())
    write_new(root / "drivers/regulator/da9213-legacy-observer-test.c",
              observer_test())
    edit_driver(root)

    print("source_edit=da921x-readonly-observer")
    print("changed_paths=5")
    print("hardware_write=none")
    print("cpu8_cpu9_admission=closed")


if __name__ == "__main__":
    main()
