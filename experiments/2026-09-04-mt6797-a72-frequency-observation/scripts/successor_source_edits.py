#!/usr/bin/env python3
"""Apply the two deterministic production-frequency successor edits."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise SystemExit(f"expected one edit anchor in {path}: {old[:60]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def bind_identity(source_root: Path) -> None:
    path = source_root / "arch/arm64/kernel/mt6797_psci.c"
    old = """#if IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING)
static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {
\t0x2e50cc09d2241006, 0xd819eeb0ed4151fb,
\t0xc6ed927e9e51b41e, 0x27c2dd7ce3cedd39,
};
#else
"""
    new = """#if IS_ENABLED(CONFIG_MTK_MT6797_A72_HOTPLUG_BINDING)
#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {
\t0x18ded825be6993a5, 0xa403f8cd526e3682,
\t0x199cc55afce876f3, 0x6b7f194faced0b25,
};
#else
static const u64 mt6797_a72_config_input_identity[ARM64_LATE_CPU_ID_WORDS] __initconst = {
\t0x2e50cc09d2241006, 0xd819eeb0ed4151fb,
\t0xc6ed927e9e51b41e, 0x27c2dd7ce3cedd39,
};
#endif
#else
"""
    replace_once(path, old, new)


def attach_observer(source_root: Path) -> None:
    soc = source_root / "drivers/soc/mediatek"
    header = soc / "mt6797-a72-frequency-observer-internal.h"
    observer = soc / "mt6797-a72-frequency-observer.c"
    admission = soc / "mt6797-a72-admission-controller.c"

    replace_once(
        header,
        """int mt6797_a72_frequency_observer_sample(
\tstruct mt6797_a72_frequency_observer_controller *controller,
\tconst struct mt6797_a72_hotplug_snapshot_source *source,
\tstruct mt6797_a72_frequency_observation *observation,
\tstruct mt6797_a72_frequency_observer_trace *trace);
int mt6797_a72_frequency_observer_register(struct device *dev);
""",
        """int mt6797_a72_frequency_observer_sample(
\tstruct mt6797_a72_frequency_observer_controller *controller,
\tconst struct mt6797_a72_hotplug_snapshot_source *source,
\tstruct mt6797_a72_frequency_observation *observation,
\tstruct mt6797_a72_frequency_observer_trace *trace);
ssize_t mt6797_a72_frequency_observer_render(
\tstruct device *dev,
\tstruct mt6797_a72_hotplug_snapshot_source *source, char *buf);
int mt6797_a72_frequency_observer_register(struct device *dev);
""",
    )
    replace_once(
        observer,
        """static ssize_t a72_frequency_observation_show(
\tstruct device *dev, struct device_attribute *attr, char *buf)
{
\tstruct mt6797_a72_hotplug_snapshot_source *source =
\t\tdev_get_drvdata(dev);
""",
        """ssize_t mt6797_a72_frequency_observer_render(
\tstruct device *dev,
\tstruct mt6797_a72_hotplug_snapshot_source *source, char *buf)
{
""",
    )
    replace_once(
        observer,
        """\treturn count;
}
static DEVICE_ATTR_RO(a72_frequency_observation);
""",
        """\treturn count;
}

static ssize_t a72_frequency_observation_show(
\tstruct device *dev, struct device_attribute *attr, char *buf)
{
\t(void)attr;
\treturn mt6797_a72_frequency_observer_render(
\t\tdev, dev_get_drvdata(dev), buf);
}
static DEVICE_ATTR_RO(a72_frequency_observation);
""",
    )

    replace_once(
        admission,
        """#include \"mt6797-a72-cpu9-admission-controller-internal.h\"
#include \"mt6797-a72-physical-source-observer-internal.h\"
""",
        """#include \"mt6797-a72-cpu9-admission-controller-internal.h\"
#include \"mt6797-a72-frequency-observer-internal.h\"
#include \"mt6797-a72-hotplug-snapshot-internal.h\"
#include \"mt6797-a72-physical-source-observer-internal.h\"
""",
    )
    replace_once(
        admission,
        """\tstruct mt6797_a72_physical_source_context source;
\tstruct mt6797_a72_admission_controller_state state;
""",
        """\tstruct mt6797_a72_physical_source_context source;
#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
\tstruct mt6797_a72_hotplug_snapshot_source frequency_source;
\tbool frequency_source_ready;
#endif
\tstruct mt6797_a72_admission_controller_state state;
""",
    )
    replace_once(
        admission,
        """\tstruct device *dev = controller->dev;
\tint ret;

\tret = mt6797_a72_admission_resolve(dev, \"mediatek,binder\",
""",
        """\tstruct device *dev = controller->dev;
\tint ret;

#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
\tif (controller->frequency_source_ready)
\t\treturn 0;
#endif
\tret = mt6797_a72_admission_resolve(dev, \"mediatek,binder\",
""",
    )
    replace_once(
        admission,
        """\tmt6797_a72_source_context_init(&controller->source, platform, clock,
\t\t\t\t       bigidvfs);
\treturn 0;
""",
        """\tmt6797_a72_source_context_init(&controller->source, platform, clock,
\t\t\t\t       bigidvfs);
#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
\tmt6797_a72_hotplug_snapshot_source_init(
\t\t&controller->frequency_source, platform, clock, bigidvfs);
\tcontroller->frequency_source_ready = true;
#endif
\treturn 0;
""",
    )
    replace_once(
        admission,
        """static DEVICE_ATTR_RO(status);
static DEVICE_ATTR_WO(trigger);
""",
        """#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
static ssize_t a72_frequency_observation_show(
\tstruct device *dev, struct device_attribute *attr, char *buf)
{
\tstruct mt6797_a72_admission_controller *controller =
\t\tdev_get_drvdata(dev);

\t(void)attr;
\treturn mt6797_a72_frequency_observer_render(
\t\tdev, &controller->frequency_source, buf);
}
static DEVICE_ATTR_RO(a72_frequency_observation);

static struct attribute *mt6797_a72_admission_frequency_attrs[] = {
\t&dev_attr_a72_frequency_observation.attr,
\tNULL,
};

static const struct attribute_group mt6797_a72_admission_frequency_group = {
\t.attrs = mt6797_a72_admission_frequency_attrs,
};
#endif

static DEVICE_ATTR_RO(status);
static DEVICE_ATTR_WO(trigger);
""",
    )
    replace_once(
        admission,
        """\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER)) {
\t\tret = devm_device_add_group(dev,
\t\t\t\t\t    &mt6797_a72_admission_live_group);
""",
        """\tif (IS_ENABLED(CONFIG_MTK_MT6797_A72_ADMISSION_LIVE_TRIGGER)) {
#if IS_ENABLED(CONFIG_MTK_MT6797_A72_FREQUENCY_OBSERVER)
\t\tret = mt6797_a72_admission_prepare(controller);
\t\tif (ret)
\t\t\treturn ret;
\t\tret = devm_device_add_group(
\t\t\tdev, &mt6797_a72_admission_frequency_group);
\t\tif (ret)
\t\t\treturn dev_err_probe(dev, ret,
\t\t\t\t\t     \"frequency observer unavailable\\n\");
#endif
\t\tret = devm_device_add_group(dev,
\t\t\t\t\t    &mt6797_a72_admission_live_group);
""",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--phase", choices=("identity", "observer"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    if args.phase == "identity":
        bind_identity(root)
    else:
        attach_observer(root)


if __name__ == "__main__":
    main()
