#!/usr/bin/env python3
"""Apply deterministic platform-movement attribution edits to post-0379 sources."""

from __future__ import annotations

import argparse
from pathlib import Path
from textwrap import dedent


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: expected one anchor: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_count(path: Path, old: str, new: str, count: int) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != count:
        raise SystemExit(f"{path}: expected {count} anchors, found {text.count(old)}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def production(root: Path) -> None:
    soc = root / "drivers/soc/mediatek"
    include = root / "include/linux/soc/mediatek"
    platform = soc / "mt6797-a72-platform-state.c"
    header = include / "mt6797-a72-platform-state.h"
    internal = soc / "mt6797-a72-platform-state-internal.h"
    observer = soc / "mt6797-a72-platform-provider-clock-observer.c"
    observer_internal = soc / "mt6797-a72-platform-provider-clock-observer-internal.h"

    internal.write_text(dedent("""\
        /* SPDX-License-Identifier: GPL-2.0-only */
        #ifndef __MT6797_A72_PLATFORM_STATE_INTERNAL_H
        #define __MT6797_A72_PLATFORM_STATE_INTERNAL_H

        #include <linux/soc/mediatek/mt6797-a72-platform-state.h>

        struct mt6797_state_capture_ops {
        \tint (*read_once)(void *context,
        \t\t\t struct mt6797_a72_platform_state *sample);
        };

        int mt6797_a72_platform_state_capture(const struct mt6797_state_capture_ops *ops,
        \t\t\t\t      void *context,
        \t\t\t\t      struct mt6797_a72_platform_state *snapshot,
        \t\t\t\t      struct mt6797_a72_platform_state_failure *failure);

        #endif /* __MT6797_A72_PLATFORM_STATE_INTERNAL_H */
        """), encoding="utf-8")

    replace_once(
        header,
        "#include <linux/errno.h>\n",
        "#include <linux/bitops.h>\n#include <linux/errno.h>\n",
    )
    replace_once(
        header,
        "#if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_STATE)\n",
        dedent("""\
        enum mt6797_a72_platform_state_movement {
        \tMT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS = BIT(0),
        \tMT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND = BIT(1),
        \tMT6797_A72_PLATFORM_MOVED_MP2_CPUSYS_PWR_CON = BIT(2),
        \tMT6797_A72_PLATFORM_MOVED_MP2_CPU0_PWR_CON = BIT(3),
        \tMT6797_A72_PLATFORM_MOVED_MP2_CPU1_PWR_CON = BIT(4),
        \tMT6797_A72_PLATFORM_MOVED_CPU_EXT_BUCK_ISO = BIT(5),
        \tMT6797_A72_PLATFORM_MOVED_MP2_SYNC_DCM = BIT(6),
        \tMT6797_A72_PLATFORM_MOVED_CCI_MP2_PORT = BIT(7),
        \tMT6797_A72_PLATFORM_MOVED_PWRAP_RESET = BIT(8),
        \tMT6797_A72_PLATFORM_MOVED_ALL = GENMASK(8, 0),
        };

        /**
         * struct mt6797_a72_platform_state_failure - completed refused pair
         * @first: first completed raw sample
         * @second: second completed raw sample
         * @movement_mask: fields that differ under the stable-snapshot contract
         * @samples_valid: both samples completed before refusal
         *
         * This is out-of-band failure evidence. It never authorizes a transition
         * and is zero for read errors and successful stable snapshots.
         */
        struct mt6797_a72_platform_state_failure {
        \tstruct mt6797_a72_platform_state first;
        \tstruct mt6797_a72_platform_state second;
        \tu32 movement_mask;
        \tbool samples_valid;
        };

        #if IS_ENABLED(CONFIG_MTK_MT6797_A72_PLATFORM_STATE)
        int mt6797_a72_platform_state_snapshot_detailed(struct device *dev,
        \t\t\t\t\t\tstruct mt6797_a72_platform_state *snapshot,
        \t\t\t\t\t\tstruct mt6797_a72_platform_state_failure *failure);
        """),
    )
    replace_once(
        header,
        "static inline int mt6797_a72_platform_state_snapshot(struct device *dev,\n",
        dedent("""\
        static inline int
        mt6797_a72_platform_state_snapshot_detailed(struct device *dev,
        \t\t\t\t\t    struct mt6797_a72_platform_state *snapshot,
        \t\t\t\t\t    struct mt6797_a72_platform_state_failure *failure)
        {
        \t(void)dev;
        \tif (snapshot)
        \t\t*snapshot = (struct mt6797_a72_platform_state){};
        \tif (failure)
        \t\t*failure = (struct mt6797_a72_platform_state_failure){};
        \treturn -EOPNOTSUPP;
        }

        static inline int mt6797_a72_platform_state_snapshot(struct device *dev,
        """),
    )

    replace_once(
        platform,
        "#include <linux/soc/mediatek/mt6797-a72-platform-state.h>\n",
        "#include <linux/soc/mediatek/mt6797-a72-platform-state.h>\n\n"
        "#include \"mt6797-a72-platform-state-internal.h\"\n",
    )
    old_start = platform.read_text(encoding="utf-8")
    start = old_start.index("static bool mt6797_state_moved(")
    end = old_start.index("\nstatic int mt6797_a72_platform_state_probe", start)
    replacement = dedent("""\
        static u32
        mt6797_state_movement_mask(const struct mt6797_a72_platform_state *first,
        \t\t\t   const struct mt6797_a72_platform_state *second)
        {
        \tu32 movement = 0;

        \tif (first->spm_cpu_pwr_status != second->spm_cpu_pwr_status)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS;
        \tif (first->spm_cpu_pwr_status_2nd != second->spm_cpu_pwr_status_2nd)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND;
        \tif (first->spm_mp2_cpusys_pwr_con != second->spm_mp2_cpusys_pwr_con)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_MP2_CPUSYS_PWR_CON;
        \tif (first->spm_mp2_cpu0_pwr_con != second->spm_mp2_cpu0_pwr_con)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_MP2_CPU0_PWR_CON;
        \tif (first->spm_mp2_cpu1_pwr_con != second->spm_mp2_cpu1_pwr_con)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_MP2_CPU1_PWR_CON;
        \tif (first->spm_cpu_ext_buck_iso != second->spm_cpu_ext_buck_iso)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_CPU_EXT_BUCK_ISO;
        \tif ((first->mp2_sync_dcm ^ second->mp2_sync_dcm) &
        \t    MT6797_MCUCFG_MP2_SYNC_DCM_MASK)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_MP2_SYNC_DCM;
        \tif ((first->cci_mp2_port_control ^ second->cci_mp2_port_control) &
        \t    MT6797_CCI_MP2_REQUEST_MASK)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_CCI_MP2_PORT;
        \tif (first->pwrap_reset_asserted != second->pwrap_reset_asserted)
        \t\tmovement |= MT6797_A72_PLATFORM_MOVED_PWRAP_RESET;

        \treturn movement;
        }

        static bool mt6797_state_cci_busy(const struct mt6797_a72_platform_state *sample)
        {
        \treturn (sample->cci_status_before | sample->cci_status_after) &
        \t\tMT6797_CCI_CHANGE_PENDING;
        }

        int mt6797_a72_platform_state_capture(const struct mt6797_state_capture_ops *ops,
        \t\t\t\t      void *context,
        \t\t\t\t      struct mt6797_a72_platform_state *snapshot,
        \t\t\t\t      struct mt6797_a72_platform_state_failure *failure)
        {
        \tstruct mt6797_a72_platform_state first;
        \tstruct mt6797_a72_platform_state second;
        \tu32 movement;
        \tint ret;

        \tif (!snapshot || !failure)
        \t\treturn -EINVAL;
        \t*snapshot = (struct mt6797_a72_platform_state){};
        \t*failure = (struct mt6797_a72_platform_state_failure){};
        \tif (!ops || !ops->read_once)
        \t\treturn -EINVAL;

        \tret = ops->read_once(context, &first);
        \tif (ret)
        \t\treturn ret;
        \tret = ops->read_once(context, &second);
        \tif (ret)
        \t\treturn ret;

        \tmovement = mt6797_state_movement_mask(&first, &second);
        \tif (mt6797_state_cci_busy(&first) ||
        \t    mt6797_state_cci_busy(&second) || movement) {
        \t\tfailure->first = first;
        \t\tfailure->second = second;
        \t\tfailure->movement_mask = movement;
        \t\tfailure->samples_valid = true;
        \t}
        \tif (mt6797_state_cci_busy(&first) || mt6797_state_cci_busy(&second))
        \t\treturn -EBUSY;
        \tif (movement)
        \t\treturn -EAGAIN;

        \t*snapshot = second;
        \tsnapshot->valid = true;
        \treturn 0;
        }

        static int mt6797_state_read_source(void *context,
        \t\t\t\t    struct mt6797_a72_platform_state *sample)
        {
        \treturn mt6797_state_read_once(context, sample);
        }

        static const struct mt6797_state_capture_ops
        mt6797_state_capture_ops = {
        \t.read_once = mt6797_state_read_source,
        };

        int mt6797_a72_platform_state_snapshot_detailed(struct device *dev,
        \t\t\t\t\t\tstruct mt6797_a72_platform_state *snapshot,
        \t\t\t\t\t\tstruct mt6797_a72_platform_state_failure *failure)
        {
        \tstruct mt6797_a72_platform_state_source *source;
        \tint ret;

        \tif (!snapshot || !failure)
        \t\treturn -EINVAL;
        \t*snapshot = (struct mt6797_a72_platform_state){};
        \t*failure = (struct mt6797_a72_platform_state_failure){};
        \tif (!dev)
        \t\treturn -EINVAL;

        \tsource = dev_get_drvdata(dev);
        \tif (!source)
        \t\treturn -ENODEV;

        \tmutex_lock(&source->lock);
        \tret = mt6797_a72_platform_state_capture(&mt6797_state_capture_ops,
        \t\t\t\t\t\tsource, snapshot, failure);
        \tmutex_unlock(&source->lock);

        \treturn ret;
        }
        EXPORT_SYMBOL_GPL(mt6797_a72_platform_state_snapshot_detailed);

        int mt6797_a72_platform_state_snapshot(struct device *dev,
        \t\t\t\t       struct mt6797_a72_platform_state *snapshot)
        {
        \tstruct mt6797_a72_platform_state_failure failure;

        \treturn mt6797_a72_platform_state_snapshot_detailed(dev, snapshot,
        \t\t\t\t\t\t     &failure);
        }
        EXPORT_SYMBOL_GPL(mt6797_a72_platform_state_snapshot);
        """)
    platform.write_text(old_start[:start] + replacement + old_start[end:], encoding="utf-8")

    replace_once(
        observer_internal,
        "\tint (*platform)(void *context, struct device *dev,\n"
        "\t\t\tstruct mt6797_a72_platform_state *snapshot);\n",
        "\tint (*platform)(void *context, struct device *dev,\n"
        "\t\t\tstruct mt6797_a72_platform_state *snapshot,\n"
        "\t\t\tstruct mt6797_a72_platform_state_failure *failure);\n",
    )
    replace_once(
        observer_internal,
        "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
        "\tenum mt6797_a72_ppc_failure_stage *failure_stage);\n",
        "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
        "\tenum mt6797_a72_ppc_failure_stage *failure_stage,\n"
        "\tstruct mt6797_a72_platform_state_failure *platform_failure);\n",
    )
    replace_once(
        observer,
        "static int mt6797_a72_ppc_platform(void *context, struct device *dev,\n"
        "\t\t\t\t   struct mt6797_a72_platform_state *snapshot)\n"
        "{\n\treturn mt6797_a72_platform_state_snapshot(dev, snapshot);\n}\n",
        "static int mt6797_a72_ppc_platform(void *context, struct device *dev,\n"
        "\tstruct mt6797_a72_platform_state *snapshot,\n"
        "\tstruct mt6797_a72_platform_state_failure *failure)\n"
        "{\n\treturn mt6797_a72_platform_state_snapshot_detailed(dev, snapshot, failure);\n}\n",
    )
    replace_once(
        observer,
        "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
        "\tenum mt6797_a72_ppc_failure_stage *failure_stage)\n",
        "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
        "\tenum mt6797_a72_ppc_failure_stage *failure_stage,\n"
        "\tstruct mt6797_a72_platform_state_failure *platform_failure)\n",
    )
    replace_once(
        observer,
        "\tif (!snapshot || !failure_stage)\n\t\treturn -EINVAL;\n"
        "\t*failure_stage = MT6797_A72_PPC_FAILURE_NONE;\n"
        "\tmemset(snapshot, 0, sizeof(*snapshot));\n",
        "\tif (!snapshot || !failure_stage || !platform_failure)\n\t\treturn -EINVAL;\n"
        "\t*failure_stage = MT6797_A72_PPC_FAILURE_NONE;\n"
        "\tmemset(snapshot, 0, sizeof(*snapshot));\n"
        "\tmemset(platform_failure, 0, sizeof(*platform_failure));\n",
    )
    replace_once(
        observer,
        "\tret = ops->platform(context, platform, &snapshot->platform);\n",
        "\tret = ops->platform(context, platform, &snapshot->platform,\n"
        "\t\t\t    platform_failure);\n",
    )
    replace_once(
        observer,
        "static void mt6797_a72_ppc_log(struct device *dev,\n",
        dedent("""\
        static void
        mt6797_a72_ppc_log_failure(struct device *dev,
        \t\t\t   enum mt6797_a72_ppc_failure_stage stage, int ret,
        \t\t\t   const struct mt6797_a72_platform_state_failure *failure)
        {
        \tconst struct mt6797_a72_platform_state *first = &failure->first;
        \tconst struct mt6797_a72_platform_state *second = &failure->second;

        \tif (stage == MT6797_A72_PPC_FAILURE_PLATFORM && ret == -EAGAIN &&
        \t    failure->samples_valid) {
        \t\tdev_err(dev,
        \t\t\t"platform/provider/clock capture failed: stage=platform ret=-11"
        \t\t\t" movement=%03x cpu=%08x/%08x cpu2=%08x/%08x"
        \t\t\t" cpusys=%08x/%08x cpu0=%08x/%08x cpu1=%08x/%08x"
        \t\t\t" iso=%08x/%08x dcm=%08x/%08x cci-port=%08x/%08x"
        \t\t\t" pwrap=%u/%u\\n",
        \t\t\tfailure->movement_mask,
        \t\t\tfirst->spm_cpu_pwr_status, second->spm_cpu_pwr_status,
        \t\t\tfirst->spm_cpu_pwr_status_2nd,
        \t\t\tsecond->spm_cpu_pwr_status_2nd,
        \t\t\tfirst->spm_mp2_cpusys_pwr_con,
        \t\t\tsecond->spm_mp2_cpusys_pwr_con,
        \t\t\tfirst->spm_mp2_cpu0_pwr_con,
        \t\t\tsecond->spm_mp2_cpu0_pwr_con,
        \t\t\tfirst->spm_mp2_cpu1_pwr_con,
        \t\t\tsecond->spm_mp2_cpu1_pwr_con,
        \t\t\tfirst->spm_cpu_ext_buck_iso,
        \t\t\tsecond->spm_cpu_ext_buck_iso,
        \t\t\tfirst->mp2_sync_dcm, second->mp2_sync_dcm,
        \t\t\tfirst->cci_mp2_port_control,
        \t\t\tsecond->cci_mp2_port_control,
        \t\t\tfirst->pwrap_reset_asserted,
        \t\t\tsecond->pwrap_reset_asserted);
        \t\treturn;
        \t}

        \tdev_err(dev,
        \t\t"platform/provider/clock capture failed: stage=%s ret=%d\\n",
        \t\tmt6797_a72_ppc_failure_stage_name(stage), ret);
        }

        static void mt6797_a72_ppc_log(struct device *dev,
        """),
    )
    replace_once(
        observer,
        "\tstruct mt6797_a72_platform_provider_clock_snapshot snapshot;\n"
        "\tenum mt6797_a72_ppc_failure_stage failure_stage;\n",
        "\tstruct mt6797_a72_platform_provider_clock_snapshot snapshot;\n"
        "\tstruct mt6797_a72_platform_state_failure platform_failure;\n"
        "\tenum mt6797_a72_ppc_failure_stage failure_stage;\n",
    )
    replace_once(
        observer,
        "\tret = mt6797_a72_ppc_capture(platform, provider, clock,\n"
        "\t\t\t\t     &mt6797_a72_ppc_ops, NULL, &snapshot,\n"
        "\t\t\t\t     &failure_stage);\n"
        "\tif (ret)\n"
        "\t\tdev_err(dev,\n"
        "\t\t\t\"platform/provider/clock capture failed: stage=%s ret=%d\\n\",\n"
        "\t\t\tmt6797_a72_ppc_failure_stage_name(failure_stage), ret);\n",
        "\tret = mt6797_a72_ppc_capture(platform, provider, clock,\n"
        "\t\t\t\t     &mt6797_a72_ppc_ops, NULL, &snapshot,\n"
        "\t\t\t\t     &failure_stage, &platform_failure);\n"
        "\tif (ret)\n"
        "\t\tmt6797_a72_ppc_log_failure(dev, failure_stage, ret,\n"
        "\t\t\t\t\t   &platform_failure);\n",
    )


def tests(root: Path) -> None:
    soc = root / "drivers/soc/mediatek"
    kconfig = soc / "Kconfig"
    makefile = soc / "Makefile"
    observer_test = soc / "mt6797-a72-platform-provider-clock-observer-test.c"
    platform_test = soc / "mt6797-a72-platform-state-test.c"

    replace_once(
        kconfig,
        "config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST\n",
        dedent("""\
        config MTK_MT6797_A72_PLATFORM_STATE_KUNIT_TEST
        \tbool "KUnit tests for MT6797 A72 platform-state movement"
        \tdepends on KUNIT=y
        \tdepends on MTK_MT6797_A72_PLATFORM_STATE
        \tdefault n
        \thelp
        \t  Exercise the exact two-sample transaction, read-error bounds, CCI-busy
        \t  precedence, all nine movement bits, and masked-noise exclusion with
        \t  injected memory only. No physical hardware access occurs, and no
        \t  retained write, provider action, clock call, or CPU request is made.

        config MTK_MT6797_A72_PLATFORM_PROVIDER_CLOCK_KUNIT_TEST
        """),
    )
    replace_once(
        makefile,
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE) += mt6797-a72-platform-state.o\n",
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE) += mt6797-a72-platform-state.o\n"
        "obj-$(CONFIG_MTK_MT6797_A72_PLATFORM_STATE_KUNIT_TEST) += mt6797-a72-platform-state-test.o\n",
    )

    replace_once(
        observer_test,
        "\tint clock_ret;\n};\n",
        "\tint clock_ret;\n"
        "\tu32 platform_movement_mask;\n"
        "\tbool platform_samples_valid;\n};\n",
    )
    replace_once(
        observer_test,
        "static int mt6797_a72_ppc_test_platform(void *context, struct device *dev,\n"
        "\t\t\t\t\tstruct mt6797_a72_platform_state *snapshot)\n"
        "{\n\tstruct mt6797_a72_ppc_test_state *state = context;\n\n",
        "static int mt6797_a72_ppc_test_platform(void *context, struct device *dev,\n"
        "\tstruct mt6797_a72_platform_state *snapshot,\n"
        "\tstruct mt6797_a72_platform_state_failure *failure)\n"
        "{\n\tstruct mt6797_a72_ppc_test_state *state = context;\n\n"
        "\t*failure = (struct mt6797_a72_platform_state_failure){};\n"
        "\tif (state->platform_samples_valid) {\n"
        "\t\tfailure->first.spm_cpu_pwr_status = 0x11111111;\n"
        "\t\tfailure->second.spm_cpu_pwr_status = 0x22222222;\n"
        "\t\tfailure->movement_mask = state->platform_movement_mask;\n"
        "\t\tfailure->samples_valid = true;\n"
        "\t}\n",
    )
    replace_once(
        observer_test,
        "static int mt6797_a72_ppc_run(struct mt6797_a72_ppc_test_state *state,\n"
        "\t\t\t      struct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
        "\t\t\t      enum mt6797_a72_ppc_failure_stage *failure_stage)\n",
        "static int mt6797_a72_ppc_run(struct mt6797_a72_ppc_test_state *state,\n"
        "\tstruct mt6797_a72_platform_provider_clock_snapshot *snapshot,\n"
        "\tenum mt6797_a72_ppc_failure_stage *failure_stage,\n"
        "\tstruct mt6797_a72_platform_state_failure *platform_failure)\n",
    )
    replace_once(
        observer_test,
        "\treturn mt6797_a72_ppc_capture(&platform, &provider, &clock, &test_ops,\n"
        "\t\t\t\t      state, snapshot, failure_stage);\n",
        "\treturn mt6797_a72_ppc_capture(&platform, &provider, &clock, &test_ops,\n"
        "\t\t\t\t      state, snapshot, failure_stage,\n"
        "\t\t\t\t      platform_failure);\n",
    )
    replace_count(
        observer_test,
        "\tstruct mt6797_a72_platform_provider_clock_snapshot snapshot;\n"
        "\tenum mt6797_a72_ppc_failure_stage failure_stage;\n",
        "\tstruct mt6797_a72_platform_provider_clock_snapshot snapshot;\n"
        "\tstruct mt6797_a72_platform_state_failure platform_failure;\n"
        "\tenum mt6797_a72_ppc_failure_stage failure_stage;\n",
        8,
    )
    replace_count(
        observer_test,
        "mt6797_a72_ppc_run(&state, &snapshot, &failure_stage)",
        "mt6797_a72_ppc_run(&state, &snapshot, &failure_stage, &platform_failure)",
        9,
    )
    replace_once(
        observer_test,
        "\tret = mt6797_a72_ppc_capture(&device, &device, NULL, &test_ops,\n"
        "\t\t\t\t     &state, &snapshot, &failure_stage);\n",
        "\tret = mt6797_a72_ppc_capture(&device, &device, NULL, &test_ops,\n"
        "\t\t\t\t     &state, &snapshot, &failure_stage,\n"
        "\t\t\t\t     &platform_failure);\n",
    )
    replace_once(
        observer_test,
        "\tstate.platform_ret = -EAGAIN;\n"
        "\tret = mt6797_a72_ppc_run(&state, &snapshot, &failure_stage, &platform_failure);\n",
        "\tstate.platform_ret = -EAGAIN;\n"
        "\tstate.platform_samples_valid = true;\n"
        "\tstate.platform_movement_mask =\n"
        "\t\tMT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS;\n"
        "\tret = mt6797_a72_ppc_run(&state, &snapshot, &failure_stage, &platform_failure);\n",
    )
    replace_once(
        observer_test,
        "\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_PLATFORM);\n"
        "\tKUNIT_EXPECT_EQ(test, state.provider_calls, 0U);\n",
        "\tKUNIT_EXPECT_EQ(test, failure_stage, MT6797_A72_PPC_FAILURE_PLATFORM);\n"
        "\tKUNIT_EXPECT_TRUE(test, platform_failure.samples_valid);\n"
        "\tKUNIT_EXPECT_EQ(test, platform_failure.movement_mask,\n"
        "\t\t\tMT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS);\n"
        "\tKUNIT_EXPECT_EQ(test, state.provider_calls, 0U);\n",
    )

    platform_test.write_text(dedent("""\
        // SPDX-License-Identifier: GPL-2.0-only
        /* Injected tests for MT6797 A72 platform-state movement attribution. */

        #include <kunit/test.h>
        #include <linux/bitops.h>
        #include <linux/errno.h>
        #include <linux/module.h>
        #include <linux/string.h>

        #include "mt6797-a72-platform-state-internal.h"

        struct mt6797_state_test_context {
        \tstruct mt6797_a72_platform_state samples[2];
        \tint returns[2];
        \tunsigned int calls;
        };

        static int mt6797_state_test_read_once(void *context,
        \t\t\t\t       struct mt6797_a72_platform_state *sample)
        {
        \tstruct mt6797_state_test_context *state = context;
        \tunsigned int call = state->calls++;

        \tif (call >= ARRAY_SIZE(state->samples))
        \t\treturn -EOVERFLOW;
        \tif (state->returns[call])
        \t\treturn state->returns[call];
        \t*sample = state->samples[call];
        \treturn 0;
        }

        static const struct mt6797_state_capture_ops test_ops = {
        \t.read_once = mt6797_state_test_read_once,
        };

        static void mt6797_state_expect_zero(struct kunit *test, const void *actual,
        \t\t\t\t     size_t size)
        {
        \tu8 zero[sizeof(struct mt6797_a72_platform_state_failure)] = { };

        \tKUNIT_ASSERT_LE(test, size, sizeof(zero));
        \tKUNIT_EXPECT_MEMEQ(test, actual, zero, size);
        }

        static void mt6797_state_stable_test(struct kunit *test)
        {
        \tstruct mt6797_state_test_context state = { };
        \tstruct mt6797_a72_platform_state_failure failure;
        \tstruct mt6797_a72_platform_state snapshot;
        \tint ret;

        \tstate.samples[0].spm_cpu_pwr_status = 0x12345678;
        \tstate.samples[1] = state.samples[0];
        \tret = mt6797_a72_platform_state_capture(&test_ops, &state, &snapshot,
        \t\t\t\t\t\t&failure);
        \tKUNIT_EXPECT_EQ(test, ret, 0);
        \tKUNIT_EXPECT_EQ(test, state.calls, 2U);
        \tKUNIT_EXPECT_TRUE(test, snapshot.valid);
        \tKUNIT_EXPECT_EQ(test, snapshot.spm_cpu_pwr_status, (u32)0x12345678);
        \tmt6797_state_expect_zero(test, &failure, sizeof(failure));
        }

        static void mt6797_state_read_errors_test(struct kunit *test)
        {
        \tstruct mt6797_state_test_context state = { .returns = { -EIO, 0 } };
        \tstruct mt6797_a72_platform_state_failure failure;
        \tstruct mt6797_a72_platform_state snapshot;
        \tint ret;

        \tret = mt6797_a72_platform_state_capture(&test_ops, &state, &snapshot,
        \t\t\t\t\t\t&failure);
        \tKUNIT_EXPECT_EQ(test, ret, -EIO);
        \tKUNIT_EXPECT_EQ(test, state.calls, 1U);
        \tmt6797_state_expect_zero(test, &snapshot, sizeof(snapshot));
        \tmt6797_state_expect_zero(test, &failure, sizeof(failure));

        \tstate = (struct mt6797_state_test_context){ .returns = { 0, -ENODATA } };
        \tret = mt6797_a72_platform_state_capture(&test_ops, &state, &snapshot,
        \t\t\t\t\t\t&failure);
        \tKUNIT_EXPECT_EQ(test, ret, -ENODATA);
        \tKUNIT_EXPECT_EQ(test, state.calls, 2U);
        \tmt6797_state_expect_zero(test, &snapshot, sizeof(snapshot));
        \tmt6797_state_expect_zero(test, &failure, sizeof(failure));
        }

        static void mt6797_state_cci_busy_precedence_test(struct kunit *test)
        {
        \tstruct mt6797_state_test_context state = { };
        \tstruct mt6797_a72_platform_state_failure failure;
        \tstruct mt6797_a72_platform_state snapshot;
        \tint ret;

        \tstate.samples[0].cci_status_before = BIT(0);
        \tstate.samples[1].spm_cpu_pwr_status = 1;
        \tret = mt6797_a72_platform_state_capture(&test_ops, &state, &snapshot,
        \t\t\t\t\t\t&failure);
        \tKUNIT_EXPECT_EQ(test, ret, -EBUSY);
        \tKUNIT_EXPECT_EQ(test, state.calls, 2U);
        \tKUNIT_EXPECT_TRUE(test, failure.samples_valid);
        \tKUNIT_EXPECT_EQ(test, failure.movement_mask,
        \t\t\tMT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS);
        \tmt6797_state_expect_zero(test, &snapshot, sizeof(snapshot));
        }

        static void mt6797_state_set_movement(struct mt6797_a72_platform_state *sample,
        \t\t\t\t      u32 movement)
        {
        \tswitch (movement) {
        \tcase MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS:
        \t\tsample->spm_cpu_pwr_status = 1;
        \t\tbreak;
        \tcase MT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND:
        \t\tsample->spm_cpu_pwr_status_2nd = 1;
        \t\tbreak;
        \tcase MT6797_A72_PLATFORM_MOVED_MP2_CPUSYS_PWR_CON:
        \t\tsample->spm_mp2_cpusys_pwr_con = 1;
        \t\tbreak;
        \tcase MT6797_A72_PLATFORM_MOVED_MP2_CPU0_PWR_CON:
        \t\tsample->spm_mp2_cpu0_pwr_con = 1;
        \t\tbreak;
        \tcase MT6797_A72_PLATFORM_MOVED_MP2_CPU1_PWR_CON:
        \t\tsample->spm_mp2_cpu1_pwr_con = 1;
        \t\tbreak;
        \tcase MT6797_A72_PLATFORM_MOVED_CPU_EXT_BUCK_ISO:
        \t\tsample->spm_cpu_ext_buck_iso = 1;
        \t\tbreak;
        \tcase MT6797_A72_PLATFORM_MOVED_MP2_SYNC_DCM:
        \t\tsample->mp2_sync_dcm = BIT(0);
        \t\tbreak;
        \tcase MT6797_A72_PLATFORM_MOVED_CCI_MP2_PORT:
        \t\tsample->cci_mp2_port_control = BIT(0);
        \t\tbreak;
        \tcase MT6797_A72_PLATFORM_MOVED_PWRAP_RESET:
        \t\tsample->pwrap_reset_asserted = true;
        \t\tbreak;
        \t}
        }

        static void mt6797_state_each_movement_test(struct kunit *test)
        {
        \tstatic const u32 movements[] = {
        \t\tMT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS,
        \t\tMT6797_A72_PLATFORM_MOVED_SPM_CPU_PWR_STATUS_2ND,
        \t\tMT6797_A72_PLATFORM_MOVED_MP2_CPUSYS_PWR_CON,
        \t\tMT6797_A72_PLATFORM_MOVED_MP2_CPU0_PWR_CON,
        \t\tMT6797_A72_PLATFORM_MOVED_MP2_CPU1_PWR_CON,
        \t\tMT6797_A72_PLATFORM_MOVED_CPU_EXT_BUCK_ISO,
        \t\tMT6797_A72_PLATFORM_MOVED_MP2_SYNC_DCM,
        \t\tMT6797_A72_PLATFORM_MOVED_CCI_MP2_PORT,
        \t\tMT6797_A72_PLATFORM_MOVED_PWRAP_RESET,
        \t};
        \tunsigned int i;

        \tfor (i = 0; i < ARRAY_SIZE(movements); i++) {
        \t\tstruct mt6797_state_test_context state = { };
        \t\tstruct mt6797_a72_platform_state_failure failure;
        \t\tstruct mt6797_a72_platform_state snapshot;
        \t\tint ret;

        \t\tmt6797_state_set_movement(&state.samples[1], movements[i]);
        \t\tret = mt6797_a72_platform_state_capture(&test_ops, &state,
        \t\t\t\t\t\t\t&snapshot, &failure);
        \t\tKUNIT_EXPECT_EQ_MSG(test, ret, -EAGAIN, "movement=%x", movements[i]);
        \t\tKUNIT_EXPECT_EQ_MSG(test, state.calls, 2U, "movement=%x", movements[i]);
        \t\tKUNIT_EXPECT_TRUE(test, failure.samples_valid);
        \t\tKUNIT_EXPECT_EQ_MSG(test, failure.movement_mask, movements[i],
        \t\t\t\t    "movement=%x", movements[i]);
        \t\tKUNIT_EXPECT_MEMEQ(test, &failure.first, &state.samples[0],
        \t\t\t\t   sizeof(failure.first));
        \t\tKUNIT_EXPECT_MEMEQ(test, &failure.second, &state.samples[1],
        \t\t\t\t   sizeof(failure.second));
        \t\tmt6797_state_expect_zero(test, &snapshot, sizeof(snapshot));
        \t}
        }

        static void mt6797_state_masked_noise_test(struct kunit *test)
        {
        \tstruct mt6797_state_test_context state = { };
        \tstruct mt6797_a72_platform_state_failure failure;
        \tstruct mt6797_a72_platform_state snapshot;
        \tint ret;

        \tstate.samples[1].spm_pwr_status = 1;
        \tstate.samples[1].spm_pwr_status_2nd = 1;
        \tstate.samples[1].mp2_sync_dcm = BIT(7);
        \tstate.samples[1].cci_mp2_port_control = BIT(2);
        \tret = mt6797_a72_platform_state_capture(&test_ops, &state, &snapshot,
        \t\t\t\t\t\t&failure);
        \tKUNIT_EXPECT_EQ(test, ret, 0);
        \tKUNIT_EXPECT_EQ(test, state.calls, 2U);
        \tKUNIT_EXPECT_TRUE(test, snapshot.valid);
        \tmt6797_state_expect_zero(test, &failure, sizeof(failure));
        }

        static struct kunit_case mt6797_state_cases[] = {
        \tKUNIT_CASE(mt6797_state_stable_test),
        \tKUNIT_CASE(mt6797_state_read_errors_test),
        \tKUNIT_CASE(mt6797_state_cci_busy_precedence_test),
        \tKUNIT_CASE(mt6797_state_each_movement_test),
        \tKUNIT_CASE(mt6797_state_masked_noise_test),
        \t{ }
        };

        static struct kunit_suite mt6797_state_suite = {
        \t.name = "mt6797-a72-platform-state-movement",
        \t.test_cases = mt6797_state_cases,
        };

        kunit_test_suite(mt6797_state_suite);

        MODULE_LICENSE("GPL");
        """), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    (production if args.phase == "production" else tests)(root)


if __name__ == "__main__":
    main()
