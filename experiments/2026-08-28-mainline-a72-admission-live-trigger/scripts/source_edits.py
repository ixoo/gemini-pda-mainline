#!/usr/bin/env python3
"""Apply deterministic serviceability-first admission-trigger edits."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


PARENT_HASHES = {
    "drivers/soc/mediatek/Kconfig":
        "864c7a0745a1460ea0e9456ec81d727e98d0f65eb8ed8ca5423fbe32917273bb",
    "drivers/soc/mediatek/mt6797-a72-admission-controller.c":
        "ee66b07cb75455d438c42032fe88249f0550e0f6cb6955e7cb232fda25027fae",
    "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h":
        "24d47e11a0d7ae43d77292f05333292390a36775440ea1abb9e33cf76f3fabca",
    "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c":
        "5777a74faf8c2f48388aaf5f9624f7f7d77cb801b2853d1d6421fda5207b9f7f",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_file(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"source path is not an exact file: {relative}")
    return path


def validate_hashes(root: Path, relatives: tuple[str, ...]) -> None:
    for relative in relatives:
        path = require_file(root, relative)
        actual = sha256(path)
        if actual != PARENT_HASHES[relative]:
            raise SystemExit(
                f"source hash changed: {relative}: "
                f"{actual} != {PARENT_HASHES[relative]}"
            )


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"source anchor count changed in {path}: {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate_stage_parent(root: Path, stage: str) -> None:
    if stage == "production":
        validate_hashes(root, tuple(PARENT_HASHES))
        return

    validate_hashes(
        root,
        ("drivers/soc/mediatek/mt6797-a72-admission-controller-test.c",),
    )
    source = require_file(
        root, "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    ).read_text(encoding="utf-8")
    header = require_file(
        root,
        "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h",
    ).read_text(encoding="utf-8")
    kconfig = require_file(
        root, "drivers/soc/mediatek/Kconfig"
    ).read_text(encoding="utf-8")
    for token in (
        "CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER",
        "mt6797_a72_admission_trigger_run(",
        "static DEVICE_ATTR_WO(trigger);",
    ):
        if token not in source and token not in header and token not in kconfig:
            raise SystemExit(f"staged production token absent: {token}")


def apply_production(root: Path) -> None:
    kconfig = root / "drivers/soc/mediatek/Kconfig"
    anchor = "config MTK_MT6797_A72_PHYSICAL_SOURCE_KUNIT_TEST\n"
    block = """config MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER
\tbool "MediaTek MT6797 serviceability-first CPU8 admission trigger"
\tdepends on MTK_MT6797_A72_ADMISSION_CONTROLLER
\tdepends on SYSFS
\tdefault n
\thelp
\t  Keep the candidate controller dormant at probe and expose one exact,
\t  root-only sysfs token. The first valid token is consumed before any
\t  supplier resolution and synchronously invokes the existing admission
\t  core at most once. Invalid and repeated tokens perform no action.

\t  This mode exists so USB/netcat can prove the exact kernel and CPU0-7
\t  baseline before any physical source, publication, or CPU8 request.
\t  CPU9, CPU_OFF, retry, reboot, and storage operations remain absent.
\t  If unsure, say N.

"""
    replace_once(kconfig, anchor, block + anchor)

    header = (
        root
        / "drivers/soc/mediatek/mt6797-a72-admission-controller-internal.h"
    )
    anchor = "struct mt6797_a72_admission_controller_state {\n"
    block = """#define MT6797_A72_ADMISSION_TRIGGER_TOKEN \\
\t"run-a72-admission-20260828-a\\n"

struct mt6797_a72_admission_trigger_ops {
\tint (*execute)(void *context);
};

struct mt6797_a72_admission_trigger_state {
\tatomic_t consumed;
\tbool complete;
\tu32 executions;
\tint operation_ret;
};

"""
    replace_once(header, anchor, block + anchor)
    anchor = "void\nmt6797_a72_admission_state_init("
    block = """void
mt6797_a72_admission_trigger_state_init(
\t\t\tstruct mt6797_a72_admission_trigger_state *state);
int
mt6797_a72_admission_trigger_run(
\t\t\tstruct mt6797_a72_admission_trigger_state *state,
\t\t\tconst struct mt6797_a72_admission_trigger_ops *ops,
\t\t\tvoid *context, const char *buf, size_t count);

"""
    replace_once(header, anchor, block + anchor)

    source = root / "drivers/soc/mediatek/mt6797-a72-admission-controller.c"
    replace_once(
        source,
        "#include <linux/cpu.h>\n#include <linux/device.h>\n",
        "#include <linux/compiler.h>\n#include <linux/cpu.h>\n"
        "#include <linux/device.h>\n",
    )
    replace_once(
        source,
        "#include <linux/string.h>\n",
        "#include <linux/string.h>\n#include <linux/sysfs.h>\n",
    )
    replace_once(
        source,
        '#define MT6797_A72_ADMISSION_TAG "GEMINI_A72_ADMISSION_V1"\n',
        '#define MT6797_A72_ADMISSION_TAG "GEMINI_A72_ADMISSION_V1"\n'
        '#define MT6797_A72_ADMISSION_LIVE_TAG '
        '"GEMINI_A72_ADMISSION_LIVE_V1"\n',
    )
    replace_once(
        source,
        "struct mt6797_a72_admission_controller {\n"
        "\tstruct device *binder;\n"
        "\tstruct mt6797_a72_physical_source_context source;\n"
        "\tstruct mt6797_a72_admission_controller_state state;\n"
        "};\n",
        "struct mt6797_a72_admission_controller {\n"
        "\tstruct device *dev;\n"
        "\tstruct device *binder;\n"
        "\tstruct mt6797_a72_physical_source_context source;\n"
        "\tstruct mt6797_a72_admission_controller_state state;\n"
        "\tstruct mt6797_a72_admission_trigger_state trigger;\n"
        "};\n",
    )
    anchor = "int\nmt6797_a72_admission_run("
    block = """void
mt6797_a72_admission_trigger_state_init(
\t\t\tstruct mt6797_a72_admission_trigger_state *state)
{
\tmemset(state, 0, sizeof(*state));
\tatomic_set(&state->consumed, 0);
\tstate->operation_ret = -EINPROGRESS;
}

int
mt6797_a72_admission_trigger_run(
\t\t\tstruct mt6797_a72_admission_trigger_state *state,
\t\t\tconst struct mt6797_a72_admission_trigger_ops *ops,
\t\t\tvoid *context, const char *buf, size_t count)
{
\tint ret;

\tif (!state || !ops || !ops->execute || !buf)
\t\treturn -EINVAL;
\tif (count != sizeof(MT6797_A72_ADMISSION_TRIGGER_TOKEN) - 1 ||
\t    memcmp(buf, MT6797_A72_ADMISSION_TRIGGER_TOKEN, count))
\t\treturn -EINVAL;
\tif (atomic_cmpxchg(&state->consumed, 0, 1))
\t\treturn -EALREADY;

\tWRITE_ONCE(state->executions, 1);
\tret = ops->execute(context);
\tWRITE_ONCE(state->operation_ret, ret);
\tsmp_store_release(&state->complete, true);
\treturn 0;
}

"""
    replace_once(source, anchor, block + anchor)

    old_probe = """static int mt6797_a72_admission_probe(struct platform_device *pdev)
{
\tstruct mt6797_a72_admission_controller *controller;
\tstruct device *bigidvfs;
\tstruct device *platform;
\tstruct device *clock;
\tstruct device *dev = &pdev->dev;
\tint ret;

\tcontroller = devm_kzalloc(dev, sizeof(*controller), GFP_KERNEL);
\tif (!controller)
\t\treturn -ENOMEM;
\tmt6797_a72_admission_state_init(&controller->state);
\tret = mt6797_a72_admission_resolve(dev, "mediatek,binder",
\t\t\t\t\t   &controller->binder);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "binder unavailable\\n");
\tret = mt6797_a72_admission_resolve(dev, "mediatek,platform-state",
\t\t\t\t\t   &platform);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "platform-state unavailable\\n");
\tret = mt6797_a72_admission_resolve(dev, "mediatek,clock-backend",
\t\t\t\t\t   &clock);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "clock backend unavailable\\n");
\tret = mt6797_a72_admission_resolve(dev, "mediatek,bigidvfs-backend",
\t\t\t\t\t   &bigidvfs);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "BigiDVFS backend unavailable\\n");
\tmt6797_a72_source_context_init(&controller->source, platform, clock,
\t\t\t\t       bigidvfs);
\tret = mt6797_a72_admission_run(&controller->state,
\t\t\t\t       &mt6797_a72_admission_production_ops,
\t\t\t\t       controller);
\tif (!atomic_read(&controller->state.consumed))
\t\treturn dev_err_probe(dev, ret, "admission prerequisite unavailable\\n");

\tplatform_set_drvdata(pdev, controller);
\tdev_info(dev, MT6797_A72_ADMISSION_TAG
\t\t " state=terminal ret=%d consumed=1 requests=%u/0/0 retries=0\\n",
\t\t ret, controller->state.cpu_requests);
\treturn 0;
}
"""
    new_probe = """static int
mt6797_a72_admission_prepare(
\t\t\tstruct mt6797_a72_admission_controller *controller)
{
\tstruct device *bigidvfs;
\tstruct device *platform;
\tstruct device *clock;
\tstruct device *dev = controller->dev;
\tint ret;

\tret = mt6797_a72_admission_resolve(dev, "mediatek,binder",
\t\t\t\t\t   &controller->binder);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "binder unavailable\\n");
\tret = mt6797_a72_admission_resolve(dev, "mediatek,platform-state",
\t\t\t\t\t   &platform);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "platform-state unavailable\\n");
\tret = mt6797_a72_admission_resolve(dev, "mediatek,clock-backend",
\t\t\t\t\t   &clock);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "clock backend unavailable\\n");
\tret = mt6797_a72_admission_resolve(dev, "mediatek,bigidvfs-backend",
\t\t\t\t\t   &bigidvfs);
\tif (ret)
\t\treturn dev_err_probe(dev, ret, "BigiDVFS backend unavailable\\n");
\tmt6797_a72_source_context_init(&controller->source, platform, clock,
\t\t\t\t       bigidvfs);
\treturn 0;
}

static int mt6797_a72_admission_execute(void *context)
{
\tstruct mt6797_a72_admission_controller *controller = context;
\tint ret;

\tret = mt6797_a72_admission_prepare(controller);
\tif (ret)
\t\treturn ret;
\treturn mt6797_a72_admission_run(
\t\t&controller->state, &mt6797_a72_admission_production_ops,
\t\tcontroller);
}

static const struct mt6797_a72_admission_trigger_ops
mt6797_a72_admission_trigger_production_ops = {
\t.execute = mt6797_a72_admission_execute,
};

static ssize_t status_show(struct device *dev, struct device_attribute *attr,
\t\t\t   char *buf)
{
\tstruct mt6797_a72_admission_controller *controller = dev_get_drvdata(dev);
\tbool complete = smp_load_acquire(&controller->trigger.complete);
\tbool consumed = atomic_read(&controller->trigger.consumed);
\tconst char *trigger_state;
\tssize_t len;

\t(void)attr;
\tif (!consumed)
\t\ttrigger_state = "armed";
\telse if (!complete)
\t\ttrigger_state = "running";
\telse
\t\ttrigger_state = "terminal";
\tlen = sysfs_emit(buf, "%s state=%s ",
\t\t\t MT6797_A72_ADMISSION_LIVE_TAG, trigger_state);
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "trigger_consumed=%u trigger_executions=%u ",
\t\t\t     consumed, READ_ONCE(controller->trigger.executions));
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "operation_ret=%d core_consumed=%d ",
\t\t\t     READ_ONCE(controller->trigger.operation_ret),
\t\t\t     atomic_read(&controller->state.consumed));
\tlen += sysfs_emit_at(buf, len,
\t\t\t     "cpu_requests=%u cpu9_requests=0 ",
\t\t\t     READ_ONCE(controller->state.cpu_requests));
\treturn len + sysfs_emit_at(buf, len,
\t\t\t\t   "cpu_off_requests=0 retries=0\\n");
}

static ssize_t trigger_store(struct device *dev,
\t\t\t     struct device_attribute *attr,
\t\t\t     const char *buf, size_t count)
{
\tstruct mt6797_a72_admission_controller *controller = dev_get_drvdata(dev);
\tint ret;

\t(void)attr;
\tret = mt6797_a72_admission_trigger_run(
\t\t&controller->trigger,
\t\t&mt6797_a72_admission_trigger_production_ops,
\t\tcontroller, buf, count);
\tif (ret)
\t\treturn ret;
\tdev_info(dev, MT6797_A72_ADMISSION_LIVE_TAG
\t\t " state=terminal ret=%d core_consumed=%d requests=%u/0/0 "
\t\t "retries=0\\n",
\t\t READ_ONCE(controller->trigger.operation_ret),
\t\t atomic_read(&controller->state.consumed),
\t\t READ_ONCE(controller->state.cpu_requests));
\treturn count;
}

static DEVICE_ATTR_RO(status);
static DEVICE_ATTR_WO(trigger);

static struct attribute *mt6797_a72_admission_live_attrs[] = {
\t&dev_attr_status.attr,
\t&dev_attr_trigger.attr,
\tNULL,
};

static const struct attribute_group mt6797_a72_admission_live_group = {
\t.name = "gemini_admission",
\t.attrs = mt6797_a72_admission_live_attrs,
};

static int mt6797_a72_admission_probe(struct platform_device *pdev)
{
\tstruct mt6797_a72_admission_controller *controller;
\tstruct device *dev = &pdev->dev;
\tint ret;

\tcontroller = devm_kzalloc(dev, sizeof(*controller), GFP_KERNEL);
\tif (!controller)
\t\treturn -ENOMEM;
\tcontroller->dev = dev;
\tmt6797_a72_admission_state_init(&controller->state);
\tmt6797_a72_admission_trigger_state_init(&controller->trigger);
\tplatform_set_drvdata(pdev, controller);

\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER)) {
\t\tret = devm_device_add_group(dev,
\t\t\t\t    &mt6797_a72_admission_live_group);
\t\tif (ret)
\t\t\treturn dev_err_probe(dev, ret,
\t\t\t\t\t     "live trigger unavailable\\n");
\t\tdev_info(dev, MT6797_A72_ADMISSION_LIVE_TAG
\t\t\t " state=armed trigger_consumed=0 trigger_executions=0 "
\t\t\t "core_consumed=0 requests=0/0/0 retries=0\\n");
\t\treturn 0;
\t}

\tret = mt6797_a72_admission_execute(controller);
\tif (!atomic_read(&controller->state.consumed))
\t\treturn dev_err_probe(dev, ret, "admission prerequisite unavailable\\n");
\tdev_info(dev, MT6797_A72_ADMISSION_TAG
\t\t " state=terminal ret=%d consumed=1 requests=%u/0/0 retries=0\\n",
\t\t ret, controller->state.cpu_requests);
\treturn 0;
}
"""
    replace_once(source, old_probe, new_probe)


def apply_tests(root: Path) -> None:
    test = (
        root
        / "drivers/soc/mediatek/mt6797-a72-admission-controller-test.c"
    )
    replace_once(
        test,
        "\tbool trace_zero_fails;\n};\n",
        "\tbool trace_zero_fails;\n"
        "\tunsigned int trigger_execute_calls;\n"
        "\tint trigger_execute_ret;\n"
        "};\n",
    )
    anchor = "static struct mt6797_a72_admission_test_context *\n"
    block = """static int mt6797_a72_admission_test_trigger_execute(void *data)
{
\tstruct mt6797_a72_admission_test_context *context = data;

\tcontext->trigger_execute_calls++;
\treturn context->trigger_execute_ret;
}

static const struct mt6797_a72_admission_trigger_ops test_trigger_ops = {
\t.execute = mt6797_a72_admission_test_trigger_execute,
};

"""
    replace_once(test, anchor, block + anchor)
    anchor = "static struct kunit_case mt6797_a72_admission_controller_cases[] = {\n"
    block = """static void mt6797_a72_admission_trigger_invalid_test(struct kunit *test)
{
\tstruct mt6797_a72_admission_test_context context = { };
\tstruct mt6797_a72_admission_trigger_state trigger;
\tint ret;

\tmt6797_a72_admission_trigger_state_init(&trigger);
\tret = mt6797_a72_admission_trigger_run(
\t\t&trigger, &test_trigger_ops, &context,
\t\tMT6797_A72_ADMISSION_TRIGGER_TOKEN,
\t\tsizeof(MT6797_A72_ADMISSION_TRIGGER_TOKEN) - 2);
\tKUNIT_EXPECT_EQ(test, ret, -EINVAL);
\tKUNIT_EXPECT_EQ(test, atomic_read(&trigger.consumed), 0);
\tKUNIT_EXPECT_FALSE(test, trigger.complete);
\tKUNIT_EXPECT_EQ(test, trigger.executions, (u32)0);
\tKUNIT_EXPECT_EQ(test, context.trigger_execute_calls, 0U);
}

static void mt6797_a72_admission_trigger_terminal_test(struct kunit *test)
{
\tstruct mt6797_a72_admission_test_context context = { };
\tstruct mt6797_a72_admission_trigger_state trigger;
\tint ret;

\tmt6797_a72_admission_trigger_state_init(&trigger);
\tcontext.trigger_execute_ret = -EIO;
\tret = mt6797_a72_admission_trigger_run(
\t\t&trigger, &test_trigger_ops, &context,
\t\tMT6797_A72_ADMISSION_TRIGGER_TOKEN,
\t\tsizeof(MT6797_A72_ADMISSION_TRIGGER_TOKEN) - 1);
\tKUNIT_EXPECT_EQ(test, ret, 0);
\tKUNIT_EXPECT_EQ(test, atomic_read(&trigger.consumed), 1);
\tKUNIT_EXPECT_TRUE(test, trigger.complete);
\tKUNIT_EXPECT_EQ(test, trigger.executions, (u32)1);
\tKUNIT_EXPECT_EQ(test, trigger.operation_ret, -EIO);
\tKUNIT_EXPECT_EQ(test, context.trigger_execute_calls, 1U);
}

static void mt6797_a72_admission_trigger_repeat_closed_test(struct kunit *test)
{
\tstruct mt6797_a72_admission_test_context context = { };
\tstruct mt6797_a72_admission_trigger_state trigger;
\tint ret;

\tmt6797_a72_admission_trigger_state_init(&trigger);
\tret = mt6797_a72_admission_trigger_run(
\t\t&trigger, &test_trigger_ops, &context,
\t\tMT6797_A72_ADMISSION_TRIGGER_TOKEN,
\t\tsizeof(MT6797_A72_ADMISSION_TRIGGER_TOKEN) - 1);
\tKUNIT_ASSERT_EQ(test, ret, 0);
\tret = mt6797_a72_admission_trigger_run(
\t\t&trigger, &test_trigger_ops, &context,
\t\tMT6797_A72_ADMISSION_TRIGGER_TOKEN,
\t\tsizeof(MT6797_A72_ADMISSION_TRIGGER_TOKEN) - 1);
\tKUNIT_EXPECT_EQ(test, ret, -EALREADY);
\tKUNIT_EXPECT_EQ(test, trigger.executions, (u32)1);
\tKUNIT_EXPECT_EQ(test, context.trigger_execute_calls, 1U);
}

"""
    cases = """static struct kunit_case mt6797_a72_admission_controller_cases[] = {
\tKUNIT_CASE(mt6797_a72_admission_trigger_invalid_test),
\tKUNIT_CASE(mt6797_a72_admission_trigger_terminal_test),
\tKUNIT_CASE(mt6797_a72_admission_trigger_repeat_closed_test),
"""
    replace_once(test, anchor, block + cases)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--stage", choices=("production", "tests"), required=True
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_stage_parent(root, args.stage)
    if args.stage == "production":
        apply_production(root)
    else:
        apply_tests(root)


if __name__ == "__main__":
    main()
