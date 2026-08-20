#!/usr/bin/env python3
"""Apply deterministic Gate-7 positive-provider source changes."""

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


def replace_region_once(path: Path, start: str, end: str, replacement: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(start) != 1 or text.count(end) != 1:
        raise SystemExit(f"{path}: source region boundary changed")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    path.write_text(before + replacement + end + after, encoding="utf-8")


def write_new(path: Path, source: Path) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite existing path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def repair_release_registration(root: Path) -> None:
    driver = root / "drivers/regulator/da9213-legacy-regulator.c"
    replace_once(
        driver,
        "static const struct mt6797_a72_provider_ops da9213_legacy_provider_ops = {\n"
        "\t.acquire = da9213_legacy_provider_acquire,\n"
        "};\n",
        "static const struct mt6797_a72_provider_ops da9213_legacy_provider_ops = {\n"
        "\t.acquire = da9213_legacy_provider_acquire,\n"
        "\t.release = da9213_legacy_provider_release,\n"
        "};\n",
    )


def positive_callbacks() -> str:
    return dedent("""\
    static int da9213_legacy_provider_acquire(void *context,
    \tconst struct mt6797_a72_provider_request *request,
    \tstruct mt6797_a72_provider_response *response)
    {
    \tstruct da9213_legacy *chip = context;
    #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
    \tint ret;
    #endif

    \tif (!chip || !request || !response)
    \t\treturn -EINVAL;

    #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
    \tmutex_lock(&chip->provider_transaction_lock);
    \tret = da9213_legacy_provider_transaction_acquire(
    \t\tchip->client->adapter, chip->client->addr,
    \t\t&da9213_legacy_positive_provider_ops, request,
    \t\t&chip->provider_transaction, response);
    \tmutex_unlock(&chip->provider_transaction_lock);
    \treturn ret;
    #else
    \tmemset(response, 0, sizeof(*response));
    \tresponse->abi = MT6797_A72_PROVIDER_CALL_ABI;
    \tresponse->returned = 1;
    \tif (request->abi != MT6797_A72_PROVIDER_CALL_ABI ||
    \t    request->operation != MT6797_A72_PROVIDER_OPERATION_CPU8_UP ||
    \t    request->settle_us != MT6797_A72_PROVIDER_CALL_SETTLE_US ||
    \t    request->da921x_page != MT6797_A72_PROVIDER_CALL_DA921X_PAGE ||
    \t    request->buckb_vsel != MT6797_A72_PROVIDER_CALL_BUCKB_VSEL ||
    \t    request->reserved)
    \t\treturn -EINVAL;

    \tdev_dbg(chip->dev,
    \t\t"provider-owner acquire refused: read-only resource boundary\\n");
    \treturn -EOPNOTSUPP;
    #endif
    }

    static int da9213_legacy_provider_release(void *context,
    \tconst struct mt6797_a72_provider_handle *handle,
    \tstruct mt6797_a72_provider_response *response)
    {
    \tstruct da9213_legacy *chip = context;
    #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
    \tint ret;
    #endif

    \tif (!chip || !handle || !response)
    \t\treturn -EINVAL;

    #if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)
    \tmutex_lock(&chip->provider_transaction_lock);
    \tret = da9213_legacy_provider_transaction_release(
    \t\tchip->client->adapter, chip->client->addr,
    \t\t&da9213_legacy_positive_provider_ops, handle,
    \t\t&chip->provider_transaction, response);
    \tmutex_unlock(&chip->provider_transaction_lock);
    \treturn ret;
    #else
    \tmemset(response, 0, sizeof(*response));
    \tresponse->abi = MT6797_A72_PROVIDER_CALL_ABI;
    \tresponse->returned = 1;
    \tresponse->origin = 1;

    \tdev_dbg(chip->dev,
    \t\t"provider-owner release refused: no rollback owner\\n");
    \treturn -EOPNOTSUPP;
    #endif
    }

    """)


def add_positive_transaction(root: Path, source_dir: Path) -> None:
    driver = root / "drivers/regulator/da9213-legacy-regulator.c"
    regulator_kconfig = root / "drivers/regulator/Kconfig"
    arm64_kconfig = root / "arch/arm64/Kconfig"

    write_new(
        root / "drivers/regulator/da9213-legacy-provider-contract.h",
        source_dir / "da9213-legacy-provider-contract.h",
    )
    replace_once(
        driver,
        '#include "da9213-legacy-write-contract.h"\n'
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n",
        '#include "da9213-legacy-write-contract.h"\n'
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        '#include "da9213-legacy-provider-contract.h"\n'
        "#endif\n"
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n",
    )
    replace_once(
        driver,
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE)\n"
        "\tstruct da9213_legacy_same_value_result same_value_result;\n"
        "#endif\n"
        "#endif\n"
        "#endif\n"
        "#endif\n"
        "};\n",
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE)\n"
        "\tstruct da9213_legacy_same_value_result same_value_result;\n"
        "#endif\n"
        "#endif\n"
        "#endif\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tstruct mutex provider_transaction_lock;\n"
        "\tstruct da9213_legacy_provider_result provider_transaction;\n"
        "#endif\n"
        "#endif\n"
        "};\n",
    )
    implementation = (
        source_dir / "da9213-legacy-positive-provider.c.inc"
    ).read_text(encoding="utf-8")
    replace_once(
        driver,
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n\n"
        "static int da9213_legacy_provider_acquire",
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_PROVIDER_OWNER)\n\n"
        + implementation
        + "\nstatic int da9213_legacy_provider_acquire",
    )
    replace_region_once(
        driver,
        "static int da9213_legacy_provider_acquire",
        "static const struct mt6797_a72_provider_ops da9213_legacy_provider_ops",
        positive_callbacks(),
    )
    replace_once(
        driver,
        "static int da9213_legacy_register_owner(struct da9213_legacy *chip)\n"
        "{\n"
        "\tint ret;\n\n"
        "\tret = mt6797_a72_provider_register(&da9213_legacy_provider_ops, chip);\n",
        "static int da9213_legacy_register_owner(struct da9213_legacy *chip)\n"
        "{\n"
        "\tint ret;\n\n"
        "#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION)\n"
        "\tmutex_init(&chip->provider_transaction_lock);\n"
        "#endif\n"
        "\tret = mt6797_a72_provider_register(&da9213_legacy_provider_ops, chip);\n",
    )
    replace_once(
        driver,
        "\tdev_info(&client->dev,\n"
        "\t\t \"%s legacy direct-address identity matched; provider is read-only\\n\",\n"
        "\t\t variant->name);\n",
        "\tif (IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION))\n"
        "\t\tdev_info(&client->dev,\n"
        "\t\t\t \"%s positive provider armed; CPU admission remains closed\\n\",\n"
        "\t\t\t variant->name);\n"
        "\telse\n"
        "\t\tdev_info(&client->dev,\n"
        "\t\t\t \"%s legacy direct-address identity matched; provider is read-only\\n\",\n"
        "\t\t\t variant->name);\n",
    )

    replace_once(
        regulator_kconfig,
        "config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST\n",
        dedent("""\
        config REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION
        \tbool "Dialog legacy DA921x positive Buck-B provider transaction"
        \tdepends on ARM64_MT6797_A72_PROVIDER_OWNER
        \tdepends on MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW
        \thelp
        \t  Enable one default-off, one-shot positive Buck-B provider state
        \t  machine behind the private MT6797 A72 owner seam. Acquire and
        \t  release each use one complete root-adapter lock, zero retries,
        \t  exact full-byte state checks, and a generation-bound handle.

        \t  The only writes are BUCKB_CONT 0x00 to 0x01 and its exactly owned
        \t  inverse. Any incomplete ownership proof is terminal and receives
        \t  no retry or speculative rollback. This option exposes no consumer,
        \t  PAGE_CON or selector write, P28 effect, CPU_ON, or CPU_OFF. Say N
        \t  outside the named Gemini Gate-7 experiment.

        config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST
        """),
    )
    replace_once(
        arm64_kconfig,
        "\t  dormant MT6797 A72 transaction. The current legacy provider is\n"
        "\t  read-only and therefore returns a clean pre-vote refusal; this option\n"
        "\t  does not connect CPU_ON or authorize regulator writes.\n",
        "\t  dormant MT6797 A72 transaction. Without the separately default-off\n"
        "\t  positive provider transaction, the legacy provider returns a clean\n"
        "\t  pre-vote refusal. This option alone does not connect CPU_ON or\n"
        "\t  authorize regulator writes.\n",
    )


def add_kunit(root: Path, source_dir: Path) -> None:
    kconfig = root / "drivers/regulator/Kconfig"
    makefile = root / "drivers/regulator/Makefile"
    write_new(
        root / "drivers/regulator/da9213-legacy-provider-test.c",
        source_dir / "da9213-legacy-provider-test.c",
    )
    replace_once(
        kconfig,
        "config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST\n",
        dedent("""\
        config REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST
        \tbool "KUnit tests for the positive legacy DA921x provider transaction"
        \tdepends on KUNIT=y
        \tdepends on REGULATOR_DA9213_LEGACY=y
        \tdepends on REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_TRANSACTION
        \thelp
        \t  Exercise acquire, exact-handle release, one-shot admission, every
        \t  negative and short transfer result at all eleven ordinals in both
        \t  operations, every owned-value mismatch, and record-only STATUS_B.

        \t  The suite uses address 0x2a on an unregistered in-memory adapter.
        \t  It registers no device or client, maps no MMIO, and performs no
        \t  physical I2C, regulator, firmware, or CPU action.

        config REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST) += da9213-legacy-write-test.o\n",
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE_KUNIT_TEST) += da9213-legacy-write-test.o\n"
        "obj-$(CONFIG_REGULATOR_DA9213_LEGACY_POSITIVE_PROVIDER_KUNIT_TEST) += da9213-legacy-provider-test.o\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("repair", "transaction", "kunit"), required=True
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    source_dir = Path(__file__).resolve().parent.parent / "source"
    if args.phase == "repair":
        repair_release_registration(root)
    elif args.phase == "transaction":
        add_positive_transaction(root, source_dir)
    else:
        add_kunit(root, source_dir)


if __name__ == "__main__":
    main()
