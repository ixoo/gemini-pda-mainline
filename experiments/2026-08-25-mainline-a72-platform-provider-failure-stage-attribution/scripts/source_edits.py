#!/usr/bin/env python3
"""Apply deterministic failure-stage attribution edits to post-0377 sources."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one edit anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_count(path: Path, old: str, new: str, count: int) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != count:
        raise SystemExit(f"{path}: expected {count} edit anchors, found {text.count(old)}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def replace_first(path: Path, old: str, new: str, expected_count: int) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != expected_count:
        raise SystemExit(
            f"{path}: expected {expected_count} remaining edit anchors, "
            f"found {text.count(old)}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def production(root: Path) -> None:
    header = root / "drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer-internal.h"
    source = root / "drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer.c"
    replace_once(
        header,
        "struct device;\n\nstruct mt6797_a72_platform_provider_clock_snapshot {\n",
        dedent("""\
        struct device;

        enum mt6797_a72_ppc_failure_stage {
        \tMT6797_A72_PPC_FAILURE_NONE,
        \tMT6797_A72_PPC_FAILURE_DEPENDENCY,
        \tMT6797_A72_PPC_FAILURE_PLATFORM,
        \tMT6797_A72_PPC_FAILURE_PROVIDER,
        \tMT6797_A72_PPC_FAILURE_BEFORE_CLOCK,
        };

        struct mt6797_a72_platform_provider_clock_snapshot {
        """),
    )
    replace_once(
        header,
        "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot);\n",
        "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
        "\tenum mt6797_a72_ppc_failure_stage *failure_stage);\n",
    )
    old_capture = source.read_text(encoding="utf-8")
    start = old_capture.index("int mt6797_a72_ppc_capture(")
    end = old_capture.index("\nstatic struct device *mt6797_a72_ppc_get_platform", start)
    new_capture = old_capture[start:end]
    edits = (
        (
            "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot)\n",
            "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
            "\tenum mt6797_a72_ppc_failure_stage *failure_stage)\n",
        ),
        (
            "\tif (!snapshot)\n\t\treturn -EINVAL;\n"
            "\tmemset(snapshot, 0, sizeof(*snapshot));\n"
            "\tif (!platform || !provider || !clock)\n\t\treturn -EPROBE_DEFER;\n",
            "\tif (!snapshot || !failure_stage)\n\t\treturn -EINVAL;\n"
            "\t*failure_stage = MT6797_A72_PPC_FAILURE_NONE;\n"
            "\tmemset(snapshot, 0, sizeof(*snapshot));\n"
            "\tif (!platform || !provider || !clock) {\n"
            "\t\t*failure_stage = MT6797_A72_PPC_FAILURE_DEPENDENCY;\n"
            "\t\treturn -EPROBE_DEFER;\n\t}\n",
        ),
        (
            "\tret = ops->platform(context, platform, &snapshot->platform);\n"
            "\tif (ret)\n\t\tgoto out_clear;\n"
            "\tif (!snapshot->platform.valid) {\n\t\tret = -ENODATA;\n",
            "\tret = ops->platform(context, platform, &snapshot->platform);\n"
            "\tif (ret) {\n"
            "\t\t*failure_stage = MT6797_A72_PPC_FAILURE_PLATFORM;\n"
            "\t\tgoto out_clear;\n\t}\n"
            "\tif (!snapshot->platform.valid) {\n"
            "\t\t*failure_stage = MT6797_A72_PPC_FAILURE_PLATFORM;\n"
            "\t\tret = -ENODATA;\n",
        ),
        (
            "\tret = ops->provider(context, &snapshot->provider);\n"
            "\tif (ret)\n\t\tgoto out_clear;\n"
            "\tif (!snapshot->provider.valid) {\n\t\tret = -ENODATA;\n",
            "\tret = ops->provider(context, &snapshot->provider);\n"
            "\tif (ret) {\n"
            "\t\t*failure_stage = MT6797_A72_PPC_FAILURE_PROVIDER;\n"
            "\t\tgoto out_clear;\n\t}\n"
            "\tif (!snapshot->provider.valid) {\n"
            "\t\t*failure_stage = MT6797_A72_PPC_FAILURE_PROVIDER;\n"
            "\t\tret = -ENODATA;\n",
        ),
        (
            "\tif (!ops->checkpoint(context, 0)) {\n\t\tret = -EIO;\n",
            "\tif (!ops->checkpoint(context, 0)) {\n"
            "\t\t*failure_stage = MT6797_A72_PPC_FAILURE_BEFORE_CLOCK;\n"
            "\t\tret = -EIO;\n",
        ),
    )
    for old, new in edits:
        if new_capture.count(old) != 1:
            raise SystemExit(f"capture edit anchor changed: {old.splitlines()[0]}")
        new_capture = new_capture.replace(old, new, 1)
    source.write_text(old_capture[:start] + new_capture + old_capture[end:], encoding="utf-8")
    replace_once(
        source,
        "static void mt6797_a72_ppc_log(struct device *dev,\n",
        dedent("""\
        static const char *
        mt6797_a72_ppc_failure_stage_name(enum mt6797_a72_ppc_failure_stage stage)
        {
        \tswitch (stage) {
        \tcase MT6797_A72_PPC_FAILURE_NONE:
        \t\treturn "none";
        \tcase MT6797_A72_PPC_FAILURE_DEPENDENCY:
        \t\treturn "dependency";
        \tcase MT6797_A72_PPC_FAILURE_PLATFORM:
        \t\treturn "platform";
        \tcase MT6797_A72_PPC_FAILURE_PROVIDER:
        \t\treturn "provider";
        \tcase MT6797_A72_PPC_FAILURE_BEFORE_CLOCK:
        \t\treturn "before-clock";
        \tdefault:
        \t\treturn "invalid";
        \t}
        }

        static void mt6797_a72_ppc_log(struct device *dev,
        """),
    )
    replace_once(
        source,
        "\tstruct mt6797_a72_platform_provider_clock_snapshot snapshot;\n"
        "\tstruct device *platform;\n",
        "\tstruct mt6797_a72_platform_provider_clock_snapshot snapshot;\n"
        "\tenum mt6797_a72_ppc_failure_stage failure_stage;\n"
        "\tstruct device *platform;\n",
    )
    replace_once(
        source,
        "\tret = mt6797_a72_ppc_capture(platform, provider, clock,\n"
        "\t\t\t\t     &mt6797_a72_ppc_ops, NULL, &snapshot);\n"
        "\tif (ret)\n"
        "\t\tdev_err(dev, \"platform/provider/clock capture failed: %d\\n\", ret);\n",
        "\tret = mt6797_a72_ppc_capture(platform, provider, clock,\n"
        "\t\t\t\t     &mt6797_a72_ppc_ops, NULL, &snapshot,\n"
        "\t\t\t\t     &failure_stage);\n"
        "\tif (ret)\n"
        "\t\tdev_err(dev,\n"
        "\t\t\t\"platform/provider/clock capture failed: stage=%s ret=%d\\n\",\n"
        "\t\t\tmt6797_a72_ppc_failure_stage_name(failure_stage), ret);\n",
    )


def tests(root: Path) -> None:
    path = root / "drivers/soc/mediatek/mt6797-a72-platform-provider-clock-observer-test.c"
    replace_once(
        path,
        "static int mt6797_a72_ppc_run(struct mt6797_a72_ppc_test_state *state,\n"
        "\t\t\t      struct mt6797_a72_platform_provider_clock_snapshot *snapshot)\n",
        "static int mt6797_a72_ppc_run(struct mt6797_a72_ppc_test_state *state,\n"
        "\t\t\t      struct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
        "\t\t\t      enum mt6797_a72_ppc_failure_stage *failure_stage)\n",
    )
    replace_once(
        path,
        "\treturn mt6797_a72_ppc_capture(&platform, &provider, &clock, &test_ops,\n"
        "\t\t\t\t      state, snapshot);\n",
        "\treturn mt6797_a72_ppc_capture(&platform, &provider, &clock, &test_ops,\n"
        "\t\t\t\t      state, snapshot, failure_stage);\n",
    )
    replace_count(
        path,
        "\tstruct mt6797_a72_platform_provider_clock_snapshot snapshot;\n",
        "\tstruct mt6797_a72_platform_provider_clock_snapshot snapshot;\n"
        "\tenum mt6797_a72_ppc_failure_stage failure_stage;\n",
        8,
    )
    replace_count(
        path,
        "mt6797_a72_ppc_run(&state, &snapshot)",
        "mt6797_a72_ppc_run(&state, &snapshot, &failure_stage)",
        9,
    )
    replace_once(
        path,
        "\tret = mt6797_a72_ppc_capture(&device, &device, NULL, &test_ops,\n"
        "\t\t\t\t     &state, &snapshot);\n",
        "\tret = mt6797_a72_ppc_capture(&device, &device, NULL, &test_ops,\n"
        "\t\t\t\t     &state, &snapshot, &failure_stage);\n",
    )
    expectations = (
        ("\tKUNIT_EXPECT_EQ(test, ret, 0);\n\tKUNIT_EXPECT_TRUE(test, snapshot.valid);\n",
         "\tKUNIT_EXPECT_EQ(test, ret, 0);\n\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_NONE);\n\tKUNIT_EXPECT_TRUE(test, snapshot.valid);\n", 1),
        ("\tKUNIT_EXPECT_EQ(test, ret, -EPROBE_DEFER);\n",
         "\tKUNIT_EXPECT_EQ(test, ret, -EPROBE_DEFER);\n\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_DEPENDENCY);\n", 1),
        ("\tKUNIT_EXPECT_EQ(test, ret, -EAGAIN);\n",
         "\tKUNIT_EXPECT_EQ(test, ret, -EAGAIN);\n\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_PLATFORM);\n", 1),
        ("\tKUNIT_EXPECT_EQ(test, ret, -ENODATA);\n\tmt6797_a72_ppc_expect_zero(test, &snapshot);\n",
         "\tKUNIT_EXPECT_EQ(test, ret, -ENODATA);\n\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_PLATFORM);\n\tmt6797_a72_ppc_expect_zero(test, &snapshot);\n", 2),
        ("\tKUNIT_EXPECT_EQ(test, ret, -EIO);\n\tKUNIT_EXPECT_EQ(test, state.clock_calls, 0U);\n",
         "\tKUNIT_EXPECT_EQ(test, ret, -EIO);\n\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_PROVIDER);\n\tKUNIT_EXPECT_EQ(test, state.clock_calls, 0U);\n", 2),
        ("\tKUNIT_EXPECT_EQ(test, ret, -ENODATA);\n\tmt6797_a72_ppc_expect_zero(test, &snapshot);\n",
         "\tKUNIT_EXPECT_EQ(test, ret, -ENODATA);\n\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_PROVIDER);\n\tmt6797_a72_ppc_expect_zero(test, &snapshot);\n", 1),
        ("\tKUNIT_EXPECT_EQ(test, ret, -EIO);\n\tKUNIT_EXPECT_EQ(test, state.clock_calls, 0U);\n",
         "\tKUNIT_EXPECT_EQ(test, ret, -EIO);\n\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_BEFORE_CLOCK);\n\tKUNIT_EXPECT_EQ(test, state.clock_calls, 0U);\n", 1),
    )
    for old, new, count in expectations:
        replace_first(path, old, new, count)
    replace_count(
        path,
        "\tKUNIT_EXPECT_EQ(test, ret, 0);\n\tKUNIT_EXPECT_FALSE(test, snapshot.valid);\n",
        "\tKUNIT_EXPECT_EQ(test, ret, 0);\n"
        "\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_NONE);\n"
        "\tKUNIT_EXPECT_FALSE(test, snapshot.valid);\n",
        3,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    (production if args.phase == "production" else tests)(root)


if __name__ == "__main__":
    main()
