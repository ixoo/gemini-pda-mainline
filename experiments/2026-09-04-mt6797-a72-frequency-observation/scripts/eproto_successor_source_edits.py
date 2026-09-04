#!/usr/bin/env python3
"""Apply deterministic MT6797 A72 frequency failure-stage diagnostics."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected one edit anchor in {path}: {old[:60]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def add_production_diagnostic(source_root: Path) -> None:
    soc = source_root / "drivers/soc/mediatek"
    header = soc / "mt6797-a72-frequency-observer-internal.h"
    observer = soc / "mt6797-a72-frequency-observer.c"

    replace_once(
        header,
        """struct mt6797_a72_frequency_observer_trace {
\tu32 attempt;
""",
        """enum mt6797_a72_frequency_observer_failure_stage {
\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_NONE = 0,
\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_CLOCK_TRANSPORT,
\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_CLOCK_SHAPE,
\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_BIGIDVFS_TRANSPORT,
\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_BIGIDVFS_SHAPE,
\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_DECODE,
};

struct mt6797_a72_frequency_observer_trace {
\tu32 attempt;
""",
    )
    replace_once(
        header,
        """\tu32 bigidvfs_reads;
\tu32 bigidvfs_sram_set_calls;
\tbool complete;
};
""",
        """\tu32 bigidvfs_reads;
\tu32 bigidvfs_sram_set_calls;
\tenum mt6797_a72_frequency_observer_failure_stage failure_stage;
\tu32 clock_abi;
\tu32 clock_reserved;
\tu64 clock_sample_generation;
\tu32 armplldiv_muxsel;
\tu32 armplldiv_ckdiv;
\tu32 pll_ll_con1;
\tu32 pll_l_con1;
\tu32 pll_cci_con1;
\tu32 big_abi;
\tu32 big_reserved;
\tu64 big_sample_generation;
\tu32 big_pll_pcw;
\tu32 big_pll_enable_posdiv;
\tbool complete;
};
""",
    )

    replace_once(
        observer,
        """static int mt6797_a72_frequency_observer_capture(
\tconst struct mt6797_a72_hotplug_snapshot_source *source,
\tstruct mt6797_a72_frequency_observation *observation,
\tstruct mt6797_a72_frequency_observer_trace *trace)
{
\tstruct mt6797_dvfsp_clock_readback clock = { };
\tstruct mt6797_bigidvfs_readback big = { };
\tint ret;

\ttrace->clock_calls++;
\tret = source->ops->clock(source->clock, &clock);
\tif (ret)
\t\treturn ret;
\tif (clock.abi != MT6797_DVFSP_CLOCK_BACKEND_ABI || clock.reserved ||
\t    !clock.sample_generation)
\t\treturn -EPROTO;

\ttrace->bigidvfs_calls++;
\tret = source->ops->bigidvfs(source->bigidvfs, &big);
\tif (ret)
\t\treturn ret;
\tif (big.abi != MT6797_BIGIDVFS_BACKEND_ABI || big.reserved ||
\t    !big.sample_generation)
\t\treturn -EPROTO;

\tret = mt6797_dvfsp_clock_state_decode(
\t\t&clock, &big, &observation->state);
\tif (ret)
\t\treturn ret;

\tobservation->abi = MT6797_A72_FREQUENCY_OBSERVER_ABI;
\tobservation->clock_sample_generation = clock.sample_generation;
\tobservation->big_sample_generation = big.sample_generation;
\tobservation->armplldiv_muxsel = clock.armplldiv_muxsel;
\tobservation->armplldiv_ckdiv = clock.armplldiv_ckdiv;
\tobservation->big_pll_pcw = big.pll_pcw;
\tobservation->big_pll_enable_posdiv = big.pll_enable_posdiv;
\ttrace->complete = true;
\treturn 0;
}
""",
        """static const char *mt6797_a72_frequency_observer_failure_name(
\tenum mt6797_a72_frequency_observer_failure_stage stage)
{
\tswitch (stage) {
\tcase MT6797_A72_FREQUENCY_OBSERVER_FAILURE_NONE:
\t\treturn "none";
\tcase MT6797_A72_FREQUENCY_OBSERVER_FAILURE_CLOCK_TRANSPORT:
\t\treturn "clock-transport";
\tcase MT6797_A72_FREQUENCY_OBSERVER_FAILURE_CLOCK_SHAPE:
\t\treturn "clock-shape";
\tcase MT6797_A72_FREQUENCY_OBSERVER_FAILURE_BIGIDVFS_TRANSPORT:
\t\treturn "bigidvfs-transport";
\tcase MT6797_A72_FREQUENCY_OBSERVER_FAILURE_BIGIDVFS_SHAPE:
\t\treturn "bigidvfs-shape";
\tcase MT6797_A72_FREQUENCY_OBSERVER_FAILURE_DECODE:
\t\treturn "decode";
\t}

\treturn "invalid";
}

static void mt6797_a72_frequency_observer_trace_clock(
\tstruct mt6797_a72_frequency_observer_trace *trace,
\tconst struct mt6797_dvfsp_clock_readback *clock)
{
\ttrace->clock_abi = clock->abi;
\ttrace->clock_reserved = clock->reserved;
\ttrace->clock_sample_generation = clock->sample_generation;
\ttrace->armplldiv_muxsel = clock->armplldiv_muxsel;
\ttrace->armplldiv_ckdiv = clock->armplldiv_ckdiv;
\ttrace->pll_ll_con1 = clock->pll_ll[1];
\ttrace->pll_l_con1 = clock->pll_l[1];
\ttrace->pll_cci_con1 = clock->pll_cci[1];
}

static void mt6797_a72_frequency_observer_trace_big(
\tstruct mt6797_a72_frequency_observer_trace *trace,
\tconst struct mt6797_bigidvfs_readback *big)
{
\ttrace->big_abi = big->abi;
\ttrace->big_reserved = big->reserved;
\ttrace->big_sample_generation = big->sample_generation;
\ttrace->big_pll_pcw = big->pll_pcw;
\ttrace->big_pll_enable_posdiv = big->pll_enable_posdiv;
}

static int mt6797_a72_frequency_observer_capture(
\tconst struct mt6797_a72_hotplug_snapshot_source *source,
\tstruct mt6797_a72_frequency_observation *observation,
\tstruct mt6797_a72_frequency_observer_trace *trace)
{
\tstruct mt6797_dvfsp_clock_readback clock = { };
\tstruct mt6797_bigidvfs_readback big = { };
\tint ret;

\ttrace->failure_stage =
\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_CLOCK_TRANSPORT;
\ttrace->clock_calls++;
\tret = source->ops->clock(source->clock, &clock);
\tif (ret)
\t\treturn ret;
\tmt6797_a72_frequency_observer_trace_clock(trace, &clock);
\ttrace->failure_stage = MT6797_A72_FREQUENCY_OBSERVER_FAILURE_CLOCK_SHAPE;
\tif (clock.abi != MT6797_DVFSP_CLOCK_BACKEND_ABI || clock.reserved ||
\t    !clock.sample_generation)
\t\treturn -EPROTO;

\ttrace->failure_stage =
\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_BIGIDVFS_TRANSPORT;
\ttrace->bigidvfs_calls++;
\tret = source->ops->bigidvfs(source->bigidvfs, &big);
\tif (ret)
\t\treturn ret;
\tmt6797_a72_frequency_observer_trace_big(trace, &big);
\ttrace->failure_stage =
\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_BIGIDVFS_SHAPE;
\tif (big.abi != MT6797_BIGIDVFS_BACKEND_ABI || big.reserved ||
\t    !big.sample_generation)
\t\treturn -EPROTO;

\ttrace->failure_stage = MT6797_A72_FREQUENCY_OBSERVER_FAILURE_DECODE;
\tret = mt6797_dvfsp_clock_state_decode(
\t\t&clock, &big, &observation->state);
\tif (ret)
\t\treturn ret;

\tobservation->abi = MT6797_A72_FREQUENCY_OBSERVER_ABI;
\tobservation->clock_sample_generation = clock.sample_generation;
\tobservation->big_sample_generation = big.sample_generation;
\tobservation->armplldiv_muxsel = clock.armplldiv_muxsel;
\tobservation->armplldiv_ckdiv = clock.armplldiv_ckdiv;
\tobservation->big_pll_pcw = big.pll_pcw;
\tobservation->big_pll_enable_posdiv = big.pll_enable_posdiv;
\ttrace->failure_stage = MT6797_A72_FREQUENCY_OBSERVER_FAILURE_NONE;
\ttrace->complete = true;
\treturn 0;
}
""",
    )
    replace_once(
        observer,
        """\tif (ret) {
\t\tdev_info(dev,
\t\t\t "GEMINI_A72_FREQUENCY_OBSERVATION_V1 attempt=%u/3 ret=%d\\n",
\t\t\t trace.attempt, ret);
\t\treturn ret;
\t}
""",
        """\tif (ret) {
\t\tdev_info(dev,
\t\t\t "GEMINI_A72_FREQUENCY_OBSERVATION_V1 attempt=%u/3 ret=%d stage=%s\\n",
\t\t\t trace.attempt, ret,
\t\t\t mt6797_a72_frequency_observer_failure_name(
\t\t\t\t trace.failure_stage));
\t\tdev_info(dev,
\t\t\t "GEMINI_A72_FREQ_CLOCK_SHAPE_V1 abi=%u reserved=%u generation=%llu\\n",
\t\t\t trace.clock_abi, trace.clock_reserved,
\t\t\t (unsigned long long)trace.clock_sample_generation);
\t\tdev_info(dev,
\t\t\t "GEMINI_A72_FREQ_CLOCK_DIV_V1 muxsel=0x%08x ckdiv=0x%08x\\n",
\t\t\t trace.armplldiv_muxsel, trace.armplldiv_ckdiv);
\t\tdev_info(dev,
\t\t\t "GEMINI_A72_FREQ_PLL_V1 ll=0x%08x l=0x%08x cci=0x%08x\\n",
\t\t\t trace.pll_ll_con1, trace.pll_l_con1,
\t\t\t trace.pll_cci_con1);
\t\tdev_info(dev,
\t\t\t "GEMINI_A72_FREQ_BIG_SHAPE_V1 abi=%u reserved=%u generation=%llu\\n",
\t\t\t trace.big_abi, trace.big_reserved,
\t\t\t (unsigned long long)trace.big_sample_generation);
\t\tdev_info(dev,
\t\t\t "GEMINI_A72_FREQ_BIG_PLL_V1 pcw=0x%08x enable_posdiv=0x%08x\\n",
\t\t\t trace.big_pll_pcw, trace.big_pll_enable_posdiv);
\t\treturn ret;
\t}
""",
    )


def add_failure_stage_tests(source_root: Path) -> None:
    test = (
        source_root
        / "drivers/soc/mediatek/mt6797-a72-frequency-observer-test.c"
    )

    replace_once(
        test,
        """\tKUNIT_EXPECT_EQ(test, trace.attempts_remaining, 2U);
\tKUNIT_EXPECT_TRUE(test, trace.complete);
""",
        """\tKUNIT_EXPECT_EQ(test, trace.attempts_remaining, 2U);
\tKUNIT_EXPECT_EQ(test, trace.failure_stage,
\t\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_NONE);
\tKUNIT_EXPECT_EQ(test, trace.clock_abi,
\t\t\tMT6797_DVFSP_CLOCK_BACKEND_ABI);
\tKUNIT_EXPECT_EQ(test, trace.clock_sample_generation, 11ULL);
\tKUNIT_EXPECT_EQ(test, trace.pll_ll_con1, 0xc1114000U);
\tKUNIT_EXPECT_EQ(test, trace.pll_l_con1, 0x400c4000U);
\tKUNIT_EXPECT_EQ(test, trace.pll_cci_con1, 0xc10c1d89U);
\tKUNIT_EXPECT_EQ(test, trace.big_abi, MT6797_BIGIDVFS_BACKEND_ABI);
\tKUNIT_EXPECT_EQ(test, trace.big_sample_generation, 13ULL);
\tKUNIT_EXPECT_EQ(test, trace.big_pll_pcw, 0xc1130000U);
\tKUNIT_EXPECT_TRUE(test, trace.complete);
""",
    )
    replace_once(
        test,
        """\tKUNIT_EXPECT_MEMEQ(test, &observation, &zero, sizeof(zero));
\tKUNIT_EXPECT_EQ(test, trace.attempt, 1U);
\tstate->clock_error = 0;
""",
        """\tKUNIT_EXPECT_MEMEQ(test, &observation, &zero, sizeof(zero));
\tKUNIT_EXPECT_EQ(test, trace.attempt, 1U);
\tKUNIT_EXPECT_EQ(test, trace.failure_stage,
\t\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_CLOCK_TRANSPORT);
\tstate->clock_error = 0;
""",
    )
    replace_once(
        test,
        """static void frequency_observer_shape_refusal_test(struct kunit *test)
{
\tstruct mt6797_a72_frequency_observer_controller controller;
\tstruct mt6797_a72_frequency_observer_trace trace;
\tstruct mt6797_a72_frequency_observation observation;
\tstruct mt6797_a72_frequency_observation zero = { };
\tstruct mt6797_a72_hotplug_snapshot_source source;
\tstruct frequency_observer_test_state *state;

\tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
\tKUNIT_ASSERT_NOT_NULL(test, state);
\tfrequency_observer_fill(state, &source, &controller);
\tstate->clock.sample_generation = 0;
\tKUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
\t\t&controller, &source, &observation, &trace), -EPROTO);
\tKUNIT_EXPECT_EQ(test, state->clock_calls, 1U);
\tKUNIT_EXPECT_EQ(test, state->big_calls, 0U);
\tKUNIT_EXPECT_MEMEQ(test, &observation, &zero, sizeof(zero));
}
""",
        """static void frequency_observer_failure_stages_test(struct kunit *test)
{
\tstruct mt6797_a72_frequency_observer_controller controller;
\tstruct mt6797_a72_frequency_observer_trace trace;
\tstruct mt6797_a72_frequency_observation observation;
\tstruct mt6797_a72_frequency_observation zero = { };
\tstruct mt6797_a72_hotplug_snapshot_source source;
\tstruct frequency_observer_test_state *state;

\tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
\tKUNIT_ASSERT_NOT_NULL(test, state);

\tfrequency_observer_fill(state, &source, &controller);
\tstate->clock.reserved = 1;
\tKUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
\t\t&controller, &source, &observation, &trace), -EPROTO);
\tKUNIT_EXPECT_EQ(test, trace.failure_stage,
\t\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_CLOCK_SHAPE);
\tKUNIT_EXPECT_EQ(test, trace.clock_reserved, 1U);
\tKUNIT_EXPECT_EQ(test, state->clock_calls, 1U);
\tKUNIT_EXPECT_EQ(test, state->big_calls, 0U);
\tKUNIT_EXPECT_MEMEQ(test, &observation, &zero, sizeof(zero));

\tfrequency_observer_fill(state, &source, &controller);
\tstate->big_error = -EIO;
\tKUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
\t\t&controller, &source, &observation, &trace), -EIO);
\tKUNIT_EXPECT_EQ(test, trace.failure_stage,
\t\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_BIGIDVFS_TRANSPORT);
\tKUNIT_EXPECT_EQ(test, state->clock_calls, 1U);
\tKUNIT_EXPECT_EQ(test, state->big_calls, 1U);

\tfrequency_observer_fill(state, &source, &controller);
\tstate->big.sample_generation = 0;
\tKUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
\t\t&controller, &source, &observation, &trace), -EPROTO);
\tKUNIT_EXPECT_EQ(test, trace.failure_stage,
\t\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_BIGIDVFS_SHAPE);
\tKUNIT_EXPECT_EQ(test, trace.big_abi, MT6797_BIGIDVFS_BACKEND_ABI);
\tKUNIT_EXPECT_EQ(test, trace.big_sample_generation, 0ULL);

\tfrequency_observer_fill(state, &source, &controller);
\tstate->clock.pll_ll[1] = 0;
\tKUNIT_EXPECT_EQ(test, mt6797_a72_frequency_observer_sample(
\t\t&controller, &source, &observation, &trace), -EPROTO);
\tKUNIT_EXPECT_EQ(test, trace.failure_stage,
\t\t\tMT6797_A72_FREQUENCY_OBSERVER_FAILURE_DECODE);
\tKUNIT_EXPECT_EQ(test, trace.pll_ll_con1, 0U);
\tKUNIT_EXPECT_EQ(test, trace.big_pll_pcw, 0xc1130000U);
\tKUNIT_EXPECT_EQ(test, state->clock_calls, 1U);
\tKUNIT_EXPECT_EQ(test, state->big_calls, 1U);
}
""",
    )
    replace_once(
        test,
        "KUNIT_CASE(frequency_observer_shape_refusal_test),",
        "KUNIT_CASE(frequency_observer_failure_stages_test),",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "production":
        add_production_diagnostic(root)
    else:
        add_failure_stage_tests(root)


if __name__ == "__main__":
    main()
