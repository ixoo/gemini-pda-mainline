#!/usr/bin/env python3
"""Add the bounded CPU9 restore-readiness observer and retained fields."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"edit anchor changed: {path}: {old.splitlines()[0]}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    public = root / "include/linux/gemini_a72_hotplug_ledger.h"
    replace_once(public,
        "#define GEMINI_A72_HOTPLUG_LEDGER_MEMBERS_MASK GENMASK(1, 0)\n",
        "#define GEMINI_A72_HOTPLUG_LEDGER_MEMBERS_MASK GENMASK(1, 0)\n"
        "#define GEMINI_A72_HOTPLUG_RESTORE_READINESS_ATTEMPTED BIT(0)\n"
        "#define GEMINI_A72_HOTPLUG_RESTORE_READINESS_READY BIT(1)\n"
        "#define GEMINI_A72_HOTPLUG_RESTORE_READINESS_FLAGS_MASK GENMASK(1, 0)\n"
        "#define GEMINI_A72_HOTPLUG_RESTORE_READINESS_SAMPLES_MAX 51U\n"
        "#define GEMINI_A72_HOTPLUG_RESTORE_READINESS_SLEEPS_MAX 50U\n")
    replace_once(public,
        "\tu32 readback_mismatch;\n\tu32 generation;\n",
        "\tu32 readback_mismatch;\n"
        "\tu32 restore_readiness_samples;\n"
        "\tu32 restore_readiness_sleeps;\n"
        "\ts32 restore_readiness_error;\n"
        "\tu32 restore_readiness_flags;\n"
        "\tu32 restore_first_status;\n"
        "\tu32 restore_first_status2;\n"
        "\tu32 restore_first_cpu9_pwr_con;\n"
        "\tu32 restore_last_status;\n"
        "\tu32 restore_last_status2;\n"
        "\tu32 restore_last_cpu9_pwr_con;\n"
        "\tu32 generation;\n")

    internal = root / "fs/pstore/gemini_a72_hotplug_ledger_internal.h"
    replace_once(internal,
        "#define GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD 0x00010001U\n"
        "#define GEMINI_A72_HOTPLUG_LEDGER_HEADER_WORDS 3U\n"
        "#define GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS 27U\n"
        "#define GEMINI_A72_HOTPLUG_LEDGER_COPIES 2U\n"
        "#define GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD 26U\n",
        "#define GEMINI_A72_HOTPLUG_LEDGER_VERSION_WORD 0x00010002U\n"
        "#define GEMINI_A72_HOTPLUG_LEDGER_HEADER_WORDS 3U\n"
        "#define GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS 37U\n"
        "#define GEMINI_A72_HOTPLUG_LEDGER_COPIES 2U\n"
        "#define GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD 36U\n")
    replace_once(internal,
        "#define GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD 28U\n",
        "#define GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD 38U\n")

    ledger = root / "fs/pstore/gemini_a72_hotplug_ledger.c"
    replace_once(ledger,
        "\t    record->members & ~GEMINI_A72_HOTPLUG_LEDGER_MEMBERS_MASK)\n"
        "\t\treturn false;\n",
        "\t    record->members & ~GEMINI_A72_HOTPLUG_LEDGER_MEMBERS_MASK ||\n"
        "\t    record->restore_readiness_samples >\n"
        "\t\t    GEMINI_A72_HOTPLUG_RESTORE_READINESS_SAMPLES_MAX ||\n"
        "\t    record->restore_readiness_sleeps >\n"
        "\t\t    GEMINI_A72_HOTPLUG_RESTORE_READINESS_SLEEPS_MAX ||\n"
        "\t    record->restore_readiness_flags &\n"
        "\t\t    ~GEMINI_A72_HOTPLUG_RESTORE_READINESS_FLAGS_MASK)\n"
        "\t\treturn false;\n"
        "\tif (record->stage < GEMINI_A72_HOTPLUG_CPU_ON_COMMITTED) {\n"
        "\t\tif (record->restore_readiness_samples ||\n"
        "\t\t    record->restore_readiness_sleeps ||\n"
        "\t\t    record->restore_readiness_error ||\n"
        "\t\t    record->restore_readiness_flags ||\n"
        "\t\t    record->restore_first_status ||\n"
        "\t\t    record->restore_first_status2 ||\n"
        "\t\t    record->restore_first_cpu9_pwr_con ||\n"
        "\t\t    record->restore_last_status ||\n"
        "\t\t    record->restore_last_status2 ||\n"
        "\t\t    record->restore_last_cpu9_pwr_con)\n"
        "\t\t\treturn false;\n"
        "\t} else {\n"
        "\t\tbool ready = record->restore_readiness_flags &\n"
        "\t\t\tGEMINI_A72_HOTPLUG_RESTORE_READINESS_READY;\n\n"
        "\t\tif (!record->restore_readiness_samples ||\n"
        "\t\t    record->restore_readiness_sleeps + 1 !=\n"
        "\t\t\t    record->restore_readiness_samples ||\n"
        "\t\t    !(record->restore_readiness_flags &\n"
        "\t\t      GEMINI_A72_HOTPLUG_RESTORE_READINESS_ATTEMPTED) ||\n"
        "\t\t    ready == !!record->restore_readiness_error)\n"
        "\t\t\treturn false;\n"
        "\t\tif (!ready && (record->terminal !=\n"
        "\t\t\t      GEMINI_A72_HOTPLUG_RESTORE_FAULT ||\n"
        "\t\t\t  record->stage !=\n"
        "\t\t\t      GEMINI_A72_HOTPLUG_CPU_ON_COMMITTED ||\n"
        "\t\t\t  record->cpu_on_calls))\n"
        "\t\t\treturn false;\n"
        "\t}\n")
    replace_once(ledger,
        "\trecord->readback_mismatch = le32_to_cpu(wire[25]);\n"
        "\treturn hotplug_record_shape_valid(record);\n",
        "\trecord->readback_mismatch = le32_to_cpu(wire[25]);\n"
        "\trecord->restore_readiness_samples = le32_to_cpu(wire[26]);\n"
        "\trecord->restore_readiness_sleeps = le32_to_cpu(wire[27]);\n"
        "\trecord->restore_readiness_error =\n"
        "\t\t(s32)le32_to_cpu(wire[28]);\n"
        "\trecord->restore_readiness_flags = le32_to_cpu(wire[29]);\n"
        "\trecord->restore_first_status = le32_to_cpu(wire[30]);\n"
        "\trecord->restore_first_status2 = le32_to_cpu(wire[31]);\n"
        "\trecord->restore_first_cpu9_pwr_con = le32_to_cpu(wire[32]);\n"
        "\trecord->restore_last_status = le32_to_cpu(wire[33]);\n"
        "\trecord->restore_last_status2 = le32_to_cpu(wire[34]);\n"
        "\trecord->restore_last_cpu9_pwr_con = le32_to_cpu(wire[35]);\n"
        "\treturn hotplug_record_shape_valid(record);\n")
    replace_once(ledger,
        "\twire[25] = cpu_to_le32(committed.readback_mismatch);\n"
        "\twire[26] = cpu_to_le32(hotplug_integrity(wire));\n",
        "\twire[25] = cpu_to_le32(committed.readback_mismatch);\n"
        "\twire[26] = cpu_to_le32(committed.restore_readiness_samples);\n"
        "\twire[27] = cpu_to_le32(committed.restore_readiness_sleeps);\n"
        "\twire[28] = cpu_to_le32((u32)committed.restore_readiness_error);\n"
        "\twire[29] = cpu_to_le32(committed.restore_readiness_flags);\n"
        "\twire[30] = cpu_to_le32(committed.restore_first_status);\n"
        "\twire[31] = cpu_to_le32(committed.restore_first_status2);\n"
        "\twire[32] = cpu_to_le32(committed.restore_first_cpu9_pwr_con);\n"
        "\twire[33] = cpu_to_le32(committed.restore_last_status);\n"
        "\twire[34] = cpu_to_le32(committed.restore_last_status2);\n"
        "\twire[35] = cpu_to_le32(committed.restore_last_cpu9_pwr_con);\n"
        "\twire[36] = cpu_to_le32(hotplug_integrity(wire));\n")

    binding_header = (
        root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-internal.h"
    )
    replace_once(binding_header,
        "#include <linux/device.h>\n",
        "#include <linux/bitops.h>\n#include <linux/device.h>\n")
    replace_once(binding_header,
        "#define MT6797_A72_HOTPLUG_BINDING_CPU9 9U\n",
        "#define MT6797_A72_HOTPLUG_BINDING_CPU9 9U\n"
        "#define MT6797_A72_RESTORE_READY_CPU8_STATUS BIT(7)\n"
        "#define MT6797_A72_RESTORE_READY_CPU9_STATUS BIT(6)\n"
        "#define MT6797_A72_RESTORE_READY_SAMPLES_MAX 51U\n")
    replace_once(binding_header,
        "struct mt6797_a72_hotplug_private_ops {\n",
        "struct mt6797_a72_restore_readiness_sample {\n"
        "\tu32 spm_cpu_pwr_status;\n"
        "\tu32 spm_cpu_pwr_status_2nd;\n"
        "\tu32 spm_mp2_cpu1_pwr_con;\n"
        "\tbool valid;\n"
        "};\n\n"
        "struct mt6797_a72_restore_readiness_result {\n"
        "\tstruct mt6797_a72_restore_readiness_sample first;\n"
        "\tstruct mt6797_a72_restore_readiness_sample last;\n"
        "\tu32 sample_calls;\n"
        "\tu32 sleep_calls;\n"
        "\ts32 error;\n"
        "\tbool attempted;\n"
        "\tbool ready;\n"
        "};\n\n"
        "struct mt6797_a72_restore_readiness_ops {\n"
        "\tint (*sample)(void *context,\n"
        "\t\t      struct mt6797_a72_restore_readiness_sample *sample);\n"
        "\tvoid (*sleep)(void *context);\n"
        "};\n\n"
        "struct mt6797_a72_hotplug_private_ops {\n")
    replace_once(binding_header,
        "bool mt6797_a72_hotplug_binding_route_matches(\n",
        "int mt6797_a72_hotplug_restore_readiness_with_ops(\n"
        "\tconst struct mt6797_a72_restore_readiness_ops *ops, void *context,\n"
        "\tstruct mt6797_a72_restore_readiness_result *result);\n"
        "bool mt6797_a72_hotplug_binding_route_matches(\n")

    binding = root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding.c"
    replace_once(binding,
        "#include <linux/device.h>\n",
        "#include <linux/delay.h>\n#include <linux/device.h>\n")
    replace_once(binding,
        "\tstruct mt6797_a72_cpu8_observer observer;\n",
        "\tstruct mt6797_a72_cpu8_observer observer;\n"
        "\tstruct mt6797_a72_restore_readiness_result readiness;\n")
    route_anchor = '''bool mt6797_a72_hotplug_binding_route_matches(
	enum mt6797_a72_hotplug_binding_route route, unsigned int cpu,
	enum mt6797_a72_hotplug_binding_route expected)
{
	return cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 && route == expected;
}
'''
    route_new = '''static bool mt6797_a72_restore_readiness_ops_valid(
	const struct mt6797_a72_restore_readiness_ops *ops)
{
	return ops && ops->sample && ops->sleep;
}

int mt6797_a72_hotplug_restore_readiness_with_ops(
	const struct mt6797_a72_restore_readiness_ops *ops, void *context,
	struct mt6797_a72_restore_readiness_result *result)
{
	u32 sample;
	int ret;

	if (!mt6797_a72_restore_readiness_ops_valid(ops) || !result)
		return -EINVAL;
	memset(result, 0, sizeof(*result));
	result->attempted = true;
	for (sample = 0; sample < MT6797_A72_RESTORE_READY_SAMPLES_MAX;
	     sample++) {
		result->sample_calls++;
		ret = ops->sample(context, &result->last);
		if (ret)
			goto fail;
		if (!result->last.valid) {
			ret = -ENODATA;
			goto fail;
		}
		if (!sample)
			result->first = result->last;
		if (!(result->last.spm_cpu_pwr_status &
		      MT6797_A72_RESTORE_READY_CPU8_STATUS) ||
		    !(result->last.spm_cpu_pwr_status_2nd &
		      MT6797_A72_RESTORE_READY_CPU8_STATUS)) {
			ret = -EPROTO;
			goto fail;
		}
		if (!((result->last.spm_cpu_pwr_status |
		       result->last.spm_cpu_pwr_status_2nd) &
		      MT6797_A72_RESTORE_READY_CPU9_STATUS)) {
			result->ready = true;
			return 0;
		}
		if (sample + 1 == MT6797_A72_RESTORE_READY_SAMPLES_MAX) {
			ret = -ETIMEDOUT;
			goto fail;
		}
		result->sleep_calls++;
		ops->sleep(context);
	}
	return -EIO;

fail:
	result->error = ret;
	return ret;
}

static int mt6797_a72_hotplug_restore_readiness_sample(
	void *context, struct mt6797_a72_restore_readiness_sample *sample)
{
	struct mt6797_a72_platform_state state = { };
	int ret;

	ret = mt6797_a72_platform_state_snapshot(context, &state);
	if (ret)
		return ret;
	*sample = (struct mt6797_a72_restore_readiness_sample) {
		.spm_cpu_pwr_status = state.spm_cpu_pwr_status,
		.spm_cpu_pwr_status_2nd = state.spm_cpu_pwr_status_2nd,
		.spm_mp2_cpu1_pwr_con = state.spm_mp2_cpu1_pwr_con,
		.valid = state.valid,
	};
	return 0;
}

static void mt6797_a72_hotplug_restore_readiness_sleep(void *context)
{
	(void)context;
	usleep_range(5000, 6000);
}

static const struct mt6797_a72_restore_readiness_ops
mt6797_a72_hotplug_restore_readiness_ops = {
	.sample = mt6797_a72_hotplug_restore_readiness_sample,
	.sleep = mt6797_a72_hotplug_restore_readiness_sleep,
};

bool mt6797_a72_hotplug_binding_route_matches(
	enum mt6797_a72_hotplug_binding_route route, unsigned int cpu,
	enum mt6797_a72_hotplug_binding_route expected)
{
	return cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 && route == expected;
}
'''
    replace_once(binding, route_anchor, route_new)
    replace_once(binding,
        "\t\t.readback_mismatch = binding->down_result.snapshots == 2 ?\n"
        "\t\t\tMT6797_A72_HOTPLUG_READBACK_BITMAP_V1 |\n"
        "\t\t\tmt6797_a72_hotplug_readback_mismatch(\n"
        "\t\t\t\t&binding->down_result.baseline,\n"
        "\t\t\t\t&binding->down_result.post_state) : 0,\n"
        "\t\t.stage = stage,\n",
        "\t\t.readback_mismatch = binding->down_result.snapshots == 2 ?\n"
        "\t\t\tMT6797_A72_HOTPLUG_READBACK_BITMAP_V1 |\n"
        "\t\t\tmt6797_a72_hotplug_readback_mismatch(\n"
        "\t\t\t\t&binding->down_result.baseline,\n"
        "\t\t\t\t&binding->down_result.post_state) : 0,\n"
        "\t\t.restore_readiness_samples = binding->readiness.sample_calls,\n"
        "\t\t.restore_readiness_sleeps = binding->readiness.sleep_calls,\n"
        "\t\t.restore_readiness_error = binding->readiness.error,\n"
        "\t\t.restore_readiness_flags =\n"
        "\t\t\t(binding->readiness.attempted ?\n"
        "\t\t\t GEMINI_A72_HOTPLUG_RESTORE_READINESS_ATTEMPTED : 0) |\n"
        "\t\t\t(binding->readiness.ready ?\n"
        "\t\t\t GEMINI_A72_HOTPLUG_RESTORE_READINESS_READY : 0),\n"
        "\t\t.restore_first_status =\n"
        "\t\t\tbinding->readiness.first.spm_cpu_pwr_status,\n"
        "\t\t.restore_first_status2 =\n"
        "\t\t\tbinding->readiness.first.spm_cpu_pwr_status_2nd,\n"
        "\t\t.restore_first_cpu9_pwr_con =\n"
        "\t\t\tbinding->readiness.first.spm_mp2_cpu1_pwr_con,\n"
        "\t\t.restore_last_status =\n"
        "\t\t\tbinding->readiness.last.spm_cpu_pwr_status,\n"
        "\t\t.restore_last_status2 =\n"
        "\t\t\tbinding->readiness.last.spm_cpu_pwr_status_2nd,\n"
        "\t\t.restore_last_cpu9_pwr_con =\n"
        "\t\t\tbinding->readiness.last.spm_mp2_cpu1_pwr_con,\n"
        "\t\t.stage = stage,\n")
    validate_old = '''static int mt6797_a72_hotplug_validate_restore_op(
	void *context,
	const struct mt6797_a72_restore_executor_request *request,
	const struct mt6797_a72_hotplug_transaction *restore)
{
	struct mt6797_a72_hotplug_snapshot snapshot = { };

	(void)context;
	mt6797_a72_hotplug_snapshot(&snapshot);
	return request->cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 &&
		snapshot.phase == MT6797_A72_HOTPLUG_RESTORE_FROZEN &&
		snapshot.members == BIT(0) && snapshot.controller_present == 1 &&
		snapshot.active.valid == 1 &&
		!memcmp(&snapshot.active.identity, &restore->identity,
			sizeof(restore->identity)) ? 0 : -EPROTO;
}
'''
    validate_new = '''static int mt6797_a72_hotplug_validate_restore_op(
	void *context,
	const struct mt6797_a72_restore_executor_request *request,
	const struct mt6797_a72_hotplug_transaction *restore)
{
	struct mt6797_a72_hotplug_binding *binding = context;
	struct mt6797_a72_hotplug_snapshot snapshot = { };

	mt6797_a72_hotplug_snapshot(&snapshot);
	if (request->cpu != MT6797_A72_HOTPLUG_BINDING_CPU9 ||
	    snapshot.phase != MT6797_A72_HOTPLUG_RESTORE_FROZEN ||
	    snapshot.members != BIT(0) || snapshot.controller_present != 1 ||
	    snapshot.active.valid != 1 ||
	    memcmp(&snapshot.active.identity, &restore->identity,
		   sizeof(restore->identity)))
		return -EPROTO;
	return mt6797_a72_hotplug_restore_readiness_with_ops(
		&mt6797_a72_hotplug_restore_readiness_ops,
		binding->source.platform, &binding->readiness);
}
'''
    replace_once(binding, validate_old, validate_new)

    test = root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c"
    replace_once(test,
        "\tbool saw_private_gate;\n};\n",
        "\tbool saw_private_gate;\n"
        "\tstruct mt6797_a72_restore_readiness_sample\n"
        "\t\treadiness[MT6797_A72_RESTORE_READY_SAMPLES_MAX];\n"
        "\tu32 readiness_count;\n"
        "\tu32 readiness_index;\n"
        "\tu32 readiness_sleep_calls;\n"
        "\tint readiness_ret;\n};\n")
    replace_once(test,
        "static const struct mt6797_a72_hotplug_private_ops hotplug_binding_test_ops = {\n",
        '''static int hotplug_binding_test_readiness_sample(
	void *context, struct mt6797_a72_restore_readiness_sample *sample)
{
	struct hotplug_binding_test_state *state = context;
	u32 index;

	if (state->readiness_ret)
		return state->readiness_ret;
	if (!state->readiness_count)
		return -ENODATA;
	index = state->readiness_index;
	if (index >= state->readiness_count)
		index = state->readiness_count - 1;
	*sample = state->readiness[index];
	state->readiness_index++;
	return 0;
}

static void hotplug_binding_test_readiness_sleep(void *context)
{
	struct hotplug_binding_test_state *state = context;

	state->readiness_sleep_calls++;
}

static const struct mt6797_a72_restore_readiness_ops
hotplug_binding_test_readiness_ops = {
	.sample = hotplug_binding_test_readiness_sample,
	.sleep = hotplug_binding_test_readiness_sleep,
};

static const struct mt6797_a72_hotplug_private_ops hotplug_binding_test_ops = {
''')
    replace_once(test,
        "\tstate->device.offline_disabled = true;\n}\n",
        "\tstate->device.offline_disabled = true;\n"
        "\tstate->readiness_count = 1;\n"
        "\tstate->readiness[0] =\n"
        "\t\t(struct mt6797_a72_restore_readiness_sample) {\n"
        "\t\t\t.spm_cpu_pwr_status = BIT(7),\n"
        "\t\t\t.spm_cpu_pwr_status_2nd = BIT(7),\n"
        "\t\t\t.spm_mp2_cpu1_pwr_con = 0x10,\n"
        "\t\t\t.valid = true,\n"
        "\t\t};\n}\n")
    tests_anchor = "static void hotplug_binding_success_test(struct kunit *test)\n"
    tests_new = '''static void hotplug_binding_readiness_immediate_test(struct kunit *test)
{
	struct mt6797_a72_restore_readiness_result result;
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_restore_readiness_with_ops(
		&hotplug_binding_test_readiness_ops, state, &result), 0);
	KUNIT_EXPECT_TRUE(test, result.attempted);
	KUNIT_EXPECT_TRUE(test, result.ready);
	KUNIT_EXPECT_EQ(test, result.sample_calls, 1U);
	KUNIT_EXPECT_EQ(test, result.sleep_calls, 0U);
	KUNIT_EXPECT_EQ(test, result.last.spm_mp2_cpu1_pwr_con, 0x10U);
}

static void hotplug_binding_readiness_settles_test(struct kunit *test)
{
	struct mt6797_a72_restore_readiness_result result;
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->readiness_count = 3;
	state->readiness[1] = state->readiness[0];
	state->readiness[2] = state->readiness[0];
	state->readiness[0].spm_cpu_pwr_status_2nd |= BIT(6);
	state->readiness[1].spm_cpu_pwr_status_2nd |= BIT(6);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_restore_readiness_with_ops(
		&hotplug_binding_test_readiness_ops, state, &result), 0);
	KUNIT_EXPECT_TRUE(test, result.ready);
	KUNIT_EXPECT_EQ(test, result.sample_calls, 3U);
	KUNIT_EXPECT_EQ(test, result.sleep_calls, 2U);
	KUNIT_EXPECT_EQ(test, state->readiness_sleep_calls, 2U);
	KUNIT_EXPECT_TRUE(test, result.first.spm_cpu_pwr_status_2nd & BIT(6));
	KUNIT_EXPECT_FALSE(test, result.last.spm_cpu_pwr_status_2nd & BIT(6));
}

static void hotplug_binding_readiness_timeout_test(struct kunit *test)
{
	struct mt6797_a72_restore_readiness_result result;
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->readiness[0].spm_cpu_pwr_status_2nd |= BIT(6);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_restore_readiness_with_ops(
		&hotplug_binding_test_readiness_ops, state, &result), -ETIMEDOUT);
	KUNIT_EXPECT_FALSE(test, result.ready);
	KUNIT_EXPECT_EQ(test, result.error, -ETIMEDOUT);
	KUNIT_EXPECT_EQ(test, result.sample_calls,
			MT6797_A72_RESTORE_READY_SAMPLES_MAX);
	KUNIT_EXPECT_EQ(test, result.sleep_calls,
			MT6797_A72_RESTORE_READY_SAMPLES_MAX - 1);
}

static void hotplug_binding_readiness_cpu8_guard_test(struct kunit *test)
{
	struct mt6797_a72_restore_readiness_result result;
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->readiness[0].spm_cpu_pwr_status_2nd &= ~BIT(7);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_restore_readiness_with_ops(
		&hotplug_binding_test_readiness_ops, state, &result), -EPROTO);
	KUNIT_EXPECT_EQ(test, result.sample_calls, 1U);
	KUNIT_EXPECT_EQ(test, result.sleep_calls, 0U);
}

static void hotplug_binding_success_test(struct kunit *test)
'''
    replace_once(test, tests_anchor, tests_new)
    replace_once(test,
        "static struct kunit_case hotplug_binding_cases[] = {\n"
        "\tKUNIT_CASE(hotplug_binding_success_test),\n",
        "static struct kunit_case hotplug_binding_cases[] = {\n"
        "\tKUNIT_CASE(hotplug_binding_readiness_immediate_test),\n"
        "\tKUNIT_CASE(hotplug_binding_readiness_settles_test),\n"
        "\tKUNIT_CASE(hotplug_binding_readiness_timeout_test),\n"
        "\tKUNIT_CASE(hotplug_binding_readiness_cpu8_guard_test),\n"
        "\tKUNIT_CASE(hotplug_binding_success_test),\n")

    ledger_test = root / "fs/pstore/gemini_a72_hotplug_ledger_test.c"
    replace_once(ledger_test,
        "\tif (stage >= GEMINI_A72_HOTPLUG_SECONDARY_COMPLETE)\n"
        "\t\trecord->cpu_on_calls = 1;\n",
        "\tif (stage >= GEMINI_A72_HOTPLUG_CPU_ON_COMMITTED) {\n"
        "\t\trecord->restore_readiness_samples = 3;\n"
        "\t\trecord->restore_readiness_sleeps = 2;\n"
        "\t\trecord->restore_readiness_flags =\n"
        "\t\t\tGEMINI_A72_HOTPLUG_RESTORE_READINESS_ATTEMPTED |\n"
        "\t\t\tGEMINI_A72_HOTPLUG_RESTORE_READINESS_READY;\n"
        "\t\trecord->restore_first_status = 0x00350cc8;\n"
        "\t\trecord->restore_first_status2 = 0x00350cff;\n"
        "\t\trecord->restore_first_cpu9_pwr_con = 0x12;\n"
        "\t\trecord->restore_last_status = 0x00350c88;\n"
        "\t\trecord->restore_last_status2 = 0x00350cbf;\n"
        "\t\trecord->restore_last_cpu9_pwr_con = 0x10;\n"
        "\t}\n"
        "\tif (stage >= GEMINI_A72_HOTPLUG_SECONDARY_COMPLETE)\n"
        "\t\trecord->cpu_on_calls = 1;\n")
    replace_once(ledger_test,
        "\tKUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS, 27U);\n"
        "\tKUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD, 26U);\n"
        "\tKUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD, 28U);\n",
        "\tKUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_COPY_WORDS, 37U);\n"
        "\tKUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_INTEGRITY_WORD, 36U);\n"
        "\tKUNIT_EXPECT_EQ(test, GEMINI_A72_HOTPLUG_LEDGER_WRITES_PER_RECORD, 38U);\n")
    replace_once(ledger_test,
        "\t\t\t0x00010001U);\n",
        "\t\t\t0x00010002U);\n")
    replace_once(ledger_test,
        "\tKUNIT_EXPECT_EQ(test, state.writes, 451U);\n",
        "\tKUNIT_EXPECT_EQ(test, state.writes, 611U);\n")
    replace_once(ledger_test,
        "\tKUNIT_EXPECT_EQ(test, latest.members, GENMASK(1, 0));\n",
        "\tKUNIT_EXPECT_EQ(test, latest.members, GENMASK(1, 0));\n"
        "\tKUNIT_EXPECT_EQ(test, latest.restore_readiness_samples, 3U);\n"
        "\tKUNIT_EXPECT_EQ(test, latest.restore_readiness_sleeps, 2U);\n"
        "\tKUNIT_EXPECT_EQ(test, latest.restore_last_status2, 0x00350cbfU);\n")
    replace_once(ledger_test,
        "\tKUNIT_EXPECT_EQ(test, state.writes, 30U);\n",
        "\tKUNIT_EXPECT_EQ(test, state.writes, 40U);\n")
    replace_once(ledger_test,
        "\trecord.cpu_off_calls = 0;\n"
        "\trecord.online_mask = BIT(10);\n",
        "\trecord.cpu_off_calls = 0;\n"
        "\trecord.restore_readiness_samples = 52;\n"
        "\tKUNIT_EXPECT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(\n"
        "\t\t&owner, &hotplug_test_ops, &state,\n"
        "\t\t0x1234567887654321ULL, &record), -EINVAL);\n"
        "\trecord.restore_readiness_samples = 0;\n"
        "\trecord.online_mask = BIT(10);\n")
    restore_test_anchor = "static struct kunit_case hotplug_ledger_cases[] = {\n"
    restore_test = '''static void hotplug_restore_readiness_timeout_test(struct kunit *test)
{
	static const u32 stages[] = { 1, 2, 3, 4, 5, 6, 7,
				      9, 10, 11, 12, 13, 14 };
	struct gemini_a72_hotplug_ledger_record latest;
	struct gemini_a72_hotplug_ledger_record record;
	struct gemini_a72_hotplug_ledger_owner owner = {};
	struct hotplug_test_state state;
	u32 copy = 0;
	unsigned int index;

	hotplug_test_raw(&state);
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_begin(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL), 0);
	for (index = 0; index < ARRAY_SIZE(stages); index++) {
		hotplug_test_fill(&record, stages[index], 0, 0);
		KUNIT_ASSERT_EQ(test,
				gemini_a72_hotplug_ledger_owner_checkpoint(
					&owner, &hotplug_test_ops, &state,
					0x1234567887654321ULL, &record), 0);
	}
	hotplug_test_fill(&record, GEMINI_A72_HOTPLUG_CPU_ON_COMMITTED,
			  GEMINI_A72_HOTPLUG_RESTORE_FAULT, -ETIMEDOUT);
	record.restore_readiness_samples = 51;
	record.restore_readiness_sleeps = 50;
	record.restore_readiness_error = -ETIMEDOUT;
	record.restore_readiness_flags =
		GEMINI_A72_HOTPLUG_RESTORE_READINESS_ATTEMPTED;
	KUNIT_ASSERT_EQ(test, gemini_a72_hotplug_ledger_owner_checkpoint(
		&owner, &hotplug_test_ops, &state,
		0x1234567887654321ULL, &record), 0);
	KUNIT_ASSERT_TRUE(test, gemini_a72_hotplug_ledger_read_latest(
		&hotplug_test_ops, &state, &latest, &copy));
	KUNIT_EXPECT_EQ(test, latest.restore_readiness_samples, 51U);
	KUNIT_EXPECT_EQ(test, latest.restore_readiness_sleeps, 50U);
	KUNIT_EXPECT_EQ(test, latest.restore_readiness_error, -ETIMEDOUT);
	KUNIT_EXPECT_EQ(test, latest.cpu_on_calls, 0U);
}

static struct kunit_case hotplug_ledger_cases[] = {
'''
    replace_once(ledger_test, restore_test_anchor, restore_test)
    replace_once(ledger_test,
        "\tKUNIT_CASE(hotplug_layout_test),\n",
        "\tKUNIT_CASE(hotplug_layout_test),\n"
        "\tKUNIT_CASE(hotplug_restore_readiness_timeout_test),\n")


if __name__ == "__main__":
    main()
