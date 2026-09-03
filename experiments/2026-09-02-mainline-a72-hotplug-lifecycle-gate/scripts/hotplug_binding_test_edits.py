#!/usr/bin/env python3
"""Add KUnit coverage for the private CPU9 device transition."""

from __future__ import annotations

import argparse
from pathlib import Path


TEST = r'''// SPDX-License-Identifier: GPL-2.0-only
/* KUnit tests for the private CPU9 device transition and route gate. */

#include <kunit/test.h>

#include <linux/device.h>
#include <linux/errno.h>
#include <linux/string.h>

#include "mt6797-a72-hotplug-binding-internal.h"

struct hotplug_binding_test_state {
	struct device device;
	u64 task_identity;
	u32 lock_calls;
	u32 unlock_calls;
	u32 device_calls;
	u32 online_calls;
	u32 task_calls;
	u32 offline_calls;
	int offline_ret;
	bool have_device;
	bool online;
	bool saw_private_gate;
};

static struct device *hotplug_binding_test_device(void *context,
						   unsigned int cpu)
{
	struct hotplug_binding_test_state *state = context;

	state->device_calls++;
	return state->have_device && cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 ?
		&state->device : NULL;
}

static void hotplug_binding_test_lock(void *context)
{
	struct hotplug_binding_test_state *state = context;

	state->lock_calls++;
}

static void hotplug_binding_test_unlock(void *context)
{
	struct hotplug_binding_test_state *state = context;

	state->unlock_calls++;
}

static bool hotplug_binding_test_online(void *context, unsigned int cpu)
{
	struct hotplug_binding_test_state *state = context;

	state->online_calls++;
	return cpu == MT6797_A72_HOTPLUG_BINDING_CPU9 && state->online;
}

static u64 hotplug_binding_test_task(void *context)
{
	struct hotplug_binding_test_state *state = context;

	state->task_calls++;
	return state->task_identity;
}

static int hotplug_binding_test_offline(void *context, struct device *dev)
{
	struct hotplug_binding_test_state *state = context;

	state->offline_calls++;
	state->saw_private_gate = !dev->offline_disabled;
	if (!state->offline_ret)
		dev->offline = true;
	return state->offline_ret;
}

static const struct mt6797_a72_hotplug_private_ops hotplug_binding_test_ops = {
	.cpu_device = hotplug_binding_test_device,
	.lock = hotplug_binding_test_lock,
	.unlock = hotplug_binding_test_unlock,
	.cpu_online = hotplug_binding_test_online,
	.task_identity = hotplug_binding_test_task,
	.offline = hotplug_binding_test_offline,
};

static void hotplug_binding_test_init(
	struct hotplug_binding_test_state *state)
{
	memset(state, 0, sizeof(*state));
	state->task_identity = 0x6797;
	state->have_device = true;
	state->online = true;
	state->device.offline_disabled = true;
}

static void hotplug_binding_success_test(struct kunit *test)
{
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_private_down_with_ops(
		&hotplug_binding_test_ops, state, 0x6797,
		MT6797_A72_HOTPLUG_BINDING_CPU9), 0);
	KUNIT_EXPECT_EQ(test, state->lock_calls, 1U);
	KUNIT_EXPECT_EQ(test, state->unlock_calls, 1U);
	KUNIT_EXPECT_EQ(test, state->offline_calls, 1U);
	KUNIT_EXPECT_TRUE(test, state->saw_private_gate);
	KUNIT_EXPECT_TRUE(test, state->device.offline_disabled);
	KUNIT_EXPECT_TRUE(test, state->device.offline);
}

static void hotplug_binding_wrong_task_test(struct kunit *test)
{
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_private_down_with_ops(
		&hotplug_binding_test_ops, state, 0x6798,
		MT6797_A72_HOTPLUG_BINDING_CPU9), -EPERM);
	KUNIT_EXPECT_EQ(test, state->offline_calls, 0U);
	KUNIT_EXPECT_TRUE(test, state->device.offline_disabled);
}

static void hotplug_binding_wrong_cpu_test(struct kunit *test)
{
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_private_down_with_ops(
		&hotplug_binding_test_ops, state, 0x6797, 8), -EINVAL);
	KUNIT_EXPECT_EQ(test, state->lock_calls, 0U);
	KUNIT_EXPECT_EQ(test, state->offline_calls, 0U);
}

static void hotplug_binding_missing_device_test(struct kunit *test)
{
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->have_device = false;
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_private_down_with_ops(
		&hotplug_binding_test_ops, state, 0x6797,
		MT6797_A72_HOTPLUG_BINDING_CPU9), -ENODEV);
	KUNIT_EXPECT_EQ(test, state->lock_calls, 1U);
	KUNIT_EXPECT_EQ(test, state->unlock_calls, 1U);
	KUNIT_EXPECT_EQ(test, state->offline_calls, 0U);
}

static void hotplug_binding_public_gate_test(struct kunit *test)
{
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->device.offline_disabled = false;
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_private_down_with_ops(
		&hotplug_binding_test_ops, state, 0x6797,
		MT6797_A72_HOTPLUG_BINDING_CPU9), -EPERM);
	KUNIT_EXPECT_EQ(test, state->offline_calls, 0U);
	KUNIT_EXPECT_FALSE(test, state->device.offline_disabled);
}

static void hotplug_binding_already_offline_test(struct kunit *test)
{
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->device.offline = true;
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_private_down_with_ops(
		&hotplug_binding_test_ops, state, 0x6797,
		MT6797_A72_HOTPLUG_BINDING_CPU9), -EPERM);
	KUNIT_EXPECT_EQ(test, state->offline_calls, 0U);
	KUNIT_EXPECT_TRUE(test, state->device.offline_disabled);
}

static void hotplug_binding_target_offline_test(struct kunit *test)
{
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->online = false;
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_private_down_with_ops(
		&hotplug_binding_test_ops, state, 0x6797,
		MT6797_A72_HOTPLUG_BINDING_CPU9), -EPERM);
	KUNIT_EXPECT_EQ(test, state->offline_calls, 0U);
	KUNIT_EXPECT_TRUE(test, state->device.offline_disabled);
}

static void hotplug_binding_failure_restores_gate_test(struct kunit *test)
{
	struct hotplug_binding_test_state *state;

	state = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
	KUNIT_ASSERT_NOT_NULL(test, state);
	hotplug_binding_test_init(state);
	state->offline_ret = -EIO;
	KUNIT_EXPECT_EQ(test, mt6797_a72_hotplug_private_down_with_ops(
		&hotplug_binding_test_ops, state, 0x6797,
		MT6797_A72_HOTPLUG_BINDING_CPU9), -EIO);
	KUNIT_EXPECT_EQ(test, state->offline_calls, 1U);
	KUNIT_EXPECT_TRUE(test, state->saw_private_gate);
	KUNIT_EXPECT_TRUE(test, state->device.offline_disabled);
	KUNIT_EXPECT_FALSE(test, state->device.offline);
}

static void hotplug_binding_route_test(struct kunit *test)
{
	KUNIT_EXPECT_TRUE(test, mt6797_a72_hotplug_binding_route_matches(
		MT6797_A72_HOTPLUG_BINDING_DOWN, 9,
		MT6797_A72_HOTPLUG_BINDING_DOWN));
	KUNIT_EXPECT_TRUE(test, mt6797_a72_hotplug_binding_route_matches(
		MT6797_A72_HOTPLUG_BINDING_RESTORE, 9,
		MT6797_A72_HOTPLUG_BINDING_RESTORE));
	KUNIT_EXPECT_FALSE(test, mt6797_a72_hotplug_binding_route_matches(
		MT6797_A72_HOTPLUG_BINDING_DOWN, 8,
		MT6797_A72_HOTPLUG_BINDING_DOWN));
	KUNIT_EXPECT_FALSE(test, mt6797_a72_hotplug_binding_route_matches(
		MT6797_A72_HOTPLUG_BINDING_IDLE, 9,
		MT6797_A72_HOTPLUG_BINDING_DOWN));
}

static struct kunit_case hotplug_binding_cases[] = {
	KUNIT_CASE(hotplug_binding_success_test),
	KUNIT_CASE(hotplug_binding_wrong_task_test),
	KUNIT_CASE(hotplug_binding_wrong_cpu_test),
	KUNIT_CASE(hotplug_binding_missing_device_test),
	KUNIT_CASE(hotplug_binding_public_gate_test),
	KUNIT_CASE(hotplug_binding_already_offline_test),
	KUNIT_CASE(hotplug_binding_target_offline_test),
	KUNIT_CASE(hotplug_binding_failure_restores_gate_test),
	KUNIT_CASE(hotplug_binding_route_test),
	{ }
};

static struct kunit_suite hotplug_binding_suite = {
	.name = "mt6797-a72-hotplug-binding",
	.test_cases = hotplug_binding_cases,
};

kunit_test_suite(hotplug_binding_suite);

MODULE_LICENSE("GPL");
'''


KCONFIG_BLOCK = '''config MTK_MT6797_A72_HOTPLUG_BINDING_KUNIT_TEST
\tbool "KUnit tests for the MT6797 CPU9 hotplug binding"
\tdepends on KUNIT=y
\tdepends on MTK_MT6797_A72_HOTPLUG_BINDING
\tdefault n
\thelp
\t  Exercise the private CPU9 device transition, exact task and CPU gate,
\t  lock scope, public-veto preservation, failure restoration, and route
\t  matching with injected memory-only operations.

\t  These tests issue no CPU request, PSCI call, MMIO, retained-memory,
\t  watchdog, IPI, network, storage, or device action. If unsure, say N.

'''


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"anchor count changed for {path}: {old[:60]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    test = root / "drivers/soc/mediatek/mt6797-a72-hotplug-binding-test.c"
    if test.exists():
        raise SystemExit(f"refusing to overwrite {test}")
    test.write_text(TEST, encoding="utf-8")

    kconfig = root / "drivers/soc/mediatek/Kconfig"
    anchor = "config MTK_MT6797_A72_CPU8_OBSERVER\n"
    replace_once(kconfig, anchor, KCONFIG_BLOCK + anchor)

    makefile = root / "drivers/soc/mediatek/Makefile"
    anchor = (
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING) += "
        "mt6797-a72-hotplug-binding.o\n"
    )
    replace_once(
        makefile, anchor,
        anchor +
        "obj-$(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING_KUNIT_TEST) += "
        "mt6797-a72-hotplug-binding-test.o\n",
    )
    print("hotplug_binding_test_edits=pass")


if __name__ == "__main__":
    main()
