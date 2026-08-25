#!/usr/bin/env python3
"""Apply deterministic provider-readiness repair edits."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        first = old.splitlines()[0] if old.splitlines() else "<empty>"
        raise SystemExit(
            f"{path}: expected one anchor beginning {first!r}, found {count}"
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def apply_dependency(root: Path) -> None:
    observer = (
        root
        / "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer.c"
    )
    internal = (
        root
        / "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer-internal.h"
    )

    replace_once(
        observer,
        "#include <linux/errno.h>\n#include <linux/module.h>\n",
        "#include <linux/errno.h>\n#include <linux/i2c.h>\n#include <linux/module.h>\n",
    )
    replace_once(
        observer,
        "int mt6797_a72_pp_capture(struct device *platform,\n"
        "\t\t\t  const struct mt6797_a72_platform_provider_observer_ops *ops,\n",
        "int mt6797_a72_pp_capture(struct device *platform,\n"
        "\t\t\t  struct device *provider,\n"
        "\t\t\t  const struct mt6797_a72_platform_provider_observer_ops *ops,\n",
    )
    replace_once(
        observer,
        "\tmemset(snapshot, 0, sizeof(*snapshot));\n"
        "\tif (!platform || !ops || !ops->platform || !ops->checkpoint ||\n",
        "\tmemset(snapshot, 0, sizeof(*snapshot));\n"
        "\tif (!provider)\n"
        "\t\treturn -EPROBE_DEFER;\n"
        "\tif (!platform || !ops || !ops->platform || !ops->checkpoint ||\n",
    )
    provider_helper = r'''static struct device *
mt6797_a72_platform_provider_get_provider(struct device *dev)
{
	struct i2c_client *provider;
	struct device_node *node;

	node = of_parse_phandle(dev->of_node, "mediatek,provider", 0);
	if (!node)
		return ERR_PTR(-EINVAL);
	if (!of_device_is_compatible(node, "dlg,da9214-legacy")) {
		of_node_put(node);
		return ERR_PTR(-EINVAL);
	}
	provider = of_find_i2c_device_by_node(node);
	of_node_put(node);
	if (!provider)
		return ERR_PTR(-EPROBE_DEFER);
	if (!device_is_bound(&provider->dev)) {
		put_device(&provider->dev);
		return ERR_PTR(-EPROBE_DEFER);
	}

	return &provider->dev;
}

'''
    replace_once(
        observer,
        "static void mt6797_a72_pp_log(struct device *dev,\n",
        provider_helper + "static void mt6797_a72_pp_log(struct device *dev,\n",
    )
    replace_once(
        observer,
        '" state=complete platform_calls=1 platform_samples=2"\n',
        '" state=complete provider_ready_gate=passed"\n'
        '\t\t " platform_calls=1 platform_samples=2"\n',
    )
    replace_once(
        observer,
        "\tstruct mt6797_a72_platform_provider_snapshot snapshot;\n"
        "\tstruct device *platform;\n"
        "\tstruct device *dev = &pdev->dev;\n",
        "\tstruct mt6797_a72_platform_provider_snapshot snapshot;\n"
        "\tstruct device *platform;\n"
        "\tstruct device *provider;\n"
        "\tstruct device *dev = &pdev->dev;\n",
    )
    replace_once(
        observer,
        "\tret = mt6797_a72_pp_capture(platform,\n"
        "\t\t\t\t    &mt6797_a72_platform_provider_ops,\n"
        "\t\t\t\t    NULL, &snapshot);\n"
        "\tif (ret)\n"
        "\t\tdev_err_probe(dev, ret, \"platform/provider snapshot failed\\n\");\n"
        "\telse\n"
        "\t\tmt6797_a72_pp_log(dev, &snapshot);\n"
        "\tput_device(platform);\n\n"
        "\treturn ret;\n",
        "\tprovider = mt6797_a72_platform_provider_get_provider(dev);\n"
        "\tif (IS_ERR(provider)) {\n"
        "\t\tret = dev_err_probe(dev, PTR_ERR(provider),\n"
        "\t\t\t\t    \"provider unavailable\\n\");\n"
        "\t\tgoto out_put_platform;\n"
        "\t}\n\n"
        "\tret = mt6797_a72_pp_capture(platform, provider,\n"
        "\t\t\t\t    &mt6797_a72_platform_provider_ops,\n"
        "\t\t\t\t    NULL, &snapshot);\n"
        "\tif (ret)\n"
        "\t\tdev_err_probe(dev, ret, \"platform/provider snapshot failed\\n\");\n"
        "\telse\n"
        "\t\tmt6797_a72_pp_log(dev, &snapshot);\n"
        "\tput_device(provider);\n"
        "out_put_platform:\n"
        "\tput_device(platform);\n\n"
        "\treturn ret;\n",
    )
    replace_once(
        internal,
        "int mt6797_a72_pp_capture(struct device *platform,\n"
        "\t\t\t  const struct mt6797_a72_platform_provider_observer_ops *ops,\n",
        "int mt6797_a72_pp_capture(struct device *platform,\n"
        "\t\t\t  struct device *provider,\n"
        "\t\t\t  const struct mt6797_a72_platform_provider_observer_ops *ops,\n",
    )


def apply_binding(root: Path) -> None:
    binding = (
        root
        / "Documentation/devicetree/bindings/soc/mediatek/mediatek,mt6797-a72-platform-provider-snapshot-observer.yaml"
    )
    replace_once(
        binding,
        "  mediatek,platform-state:\n"
        "    $ref: /schemas/types.yaml#/definitions/phandle\n"
        "    description: Phandle to the bound MT6797 A72 platform-state source.\n\n",
        "  mediatek,platform-state:\n"
        "    $ref: /schemas/types.yaml#/definitions/phandle\n"
        "    description: Phandle to the bound MT6797 A72 platform-state source.\n\n"
        "  mediatek,provider:\n"
        "    $ref: /schemas/types.yaml#/definitions/phandle\n"
        "    description: Phandle to the bound legacy DA9214 regulator endpoint.\n\n",
    )
    replace_once(
        binding,
        "  - mediatek,platform-state\n\n",
        "  - mediatek,platform-state\n"
        "  - mediatek,provider\n\n",
    )
    replace_once(
        binding,
        "        mediatek,platform-state = <&a72_platform_state>;\n",
        "        mediatek,platform-state = <&a72_platform_state>;\n"
        "        mediatek,provider = <&da9214>;\n",
    )


def apply_tests(root: Path) -> None:
    tests = (
        root
        / "drivers/soc/mediatek/mt6797-a72-platform-provider-snapshot-observer-test.c"
    )
    text = tests.read_text(encoding="utf-8")
    platform_declaration = "\tstruct device platform = { };\n"
    if text.count(platform_declaration) != 6:
        raise SystemExit("test source: expected six platform declarations")
    text = text.replace(
        platform_declaration,
        platform_declaration + "\tstruct device provider = { };\n",
    )
    calls = "mt6797_a72_pp_capture(&platform, &test_ops, &state, &snapshot)"
    if text.count(calls) != 7:
        raise SystemExit("test source: expected seven existing capture calls")
    text = text.replace(
        calls,
        "mt6797_a72_pp_capture(&platform, &provider, &test_ops, &state,\n"
        "\t\t\t\t    &snapshot)",
    )
    tests.write_text(text, encoding="utf-8")

    not_ready = r'''static void mt6797_platform_provider_not_ready_test(struct kunit *test)
{
	struct mt6797_a72_platform_provider_test_state state =
		mt6797_platform_provider_success_state();
	struct mt6797_a72_platform_provider_snapshot snapshot;
	struct device platform = { };
	int ret;

	memset(&snapshot, 0xff, sizeof(snapshot));
	ret = mt6797_a72_pp_capture(&platform, NULL, &test_ops, &state,
				    &snapshot);
	KUNIT_EXPECT_EQ(test, ret, -EPROBE_DEFER);
	KUNIT_EXPECT_EQ(test, state.platform_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.provider_calls, 0U);
	KUNIT_EXPECT_EQ(test, state.event_count, 0U);
	mt6797_pp_expect_zero(test, &snapshot);
}

'''
    replace_once(
        tests,
        "static void mt6797_platform_provider_success_test(struct kunit *test)\n",
        not_ready
        + "static void mt6797_platform_provider_success_test(struct kunit *test)\n",
    )
    replace_once(
        tests,
        "static struct kunit_case mt6797_a72_platform_provider_cases[] = {\n"
        "\tKUNIT_CASE(mt6797_platform_provider_success_test),\n",
        "static struct kunit_case mt6797_a72_platform_provider_cases[] = {\n"
        "\tKUNIT_CASE(mt6797_platform_provider_not_ready_test),\n"
        "\tKUNIT_CASE(mt6797_platform_provider_success_test),\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument(
        "--phase", choices=("dependency", "binding", "tests"), required=True
    )
    args = parser.parse_args()
    root = args.source_root.resolve()
    actions = {
        "dependency": lambda: apply_dependency(root),
        "binding": lambda: apply_binding(root),
        "tests": lambda: apply_tests(root),
    }
    actions[args.phase]()


if __name__ == "__main__":
    main()
