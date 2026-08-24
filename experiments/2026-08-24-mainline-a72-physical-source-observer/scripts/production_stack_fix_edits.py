#!/usr/bin/env python3
"""Move the production physical-source result off the kernel stack."""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one production probe, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = (
        args.source_root.resolve()
        / "drivers/soc/mediatek/mt6797-a72-physical-source-observer.c"
    )

    replace_once(
        path,
        "#include <linux/pstore_ram.h>\n#include <linux/string.h>\n",
        "#include <linux/pstore_ram.h>\n#include <linux/slab.h>\n"
        "#include <linux/string.h>\n",
    )
    replace_once(
        path,
        """static int
mt6797_a72_physical_source_probe(struct platform_device *pdev)
{
	struct mt6797_a72_physical_source_context context = {
		.readers = &mt6797_a72_physical_source_readers,
	};
	struct mt6797_a72_direct_state_snapshot snapshot;
	struct device *dev = &pdev->dev;
	int ret;

	context.platform = mt6797_a72_physical_source_get_device(dev, "mediatek,platform-state");
	if (IS_ERR(context.platform))
		return dev_err_probe(dev, PTR_ERR(context.platform),
				     "platform-state source unavailable\\n");
	context.clock = mt6797_a72_physical_source_get_device(dev, "mediatek,clock-backend");
	if (IS_ERR(context.clock)) {
		ret = dev_err_probe(dev, PTR_ERR(context.clock),
				    "clock source unavailable\\n");
		goto put_platform;
	}
	context.bigidvfs = mt6797_a72_physical_source_get_device(dev, "mediatek,bigidvfs-backend");
	if (IS_ERR(context.bigidvfs)) {
		ret = dev_err_probe(dev, PTR_ERR(context.bigidvfs),
				    "BigiDVFS source unavailable\\n");
		goto put_clock;
	}

	ret = mt6797_a72_physical_source_run(&context, &mt6797_physical_runtime,
					     &snapshot);
	if (ret)
		dev_err_probe(dev, ret, "direct physical snapshot failed\\n");
	else
		mt6797_a72_physical_source_log(dev, &snapshot);

	put_device(context.bigidvfs);
put_clock:
	put_device(context.clock);
put_platform:
	put_device(context.platform);
	return ret;
}
""",
        """static int
mt6797_a72_physical_source_probe(struct platform_device *pdev)
{
	struct mt6797_a72_physical_source_context context = {
		.readers = &mt6797_a72_physical_source_readers,
	};
	struct mt6797_a72_direct_state_snapshot *snapshot;
	struct device *dev = &pdev->dev;
	int ret;

	snapshot = kvzalloc_obj(*snapshot);
	if (!snapshot)
		return -ENOMEM;
	context.platform = mt6797_a72_physical_source_get_device(dev, "mediatek,platform-state");
	if (IS_ERR(context.platform)) {
		ret = dev_err_probe(dev, PTR_ERR(context.platform),
				    "platform-state source unavailable\\n");
		goto free_snapshot;
	}
	context.clock = mt6797_a72_physical_source_get_device(dev, "mediatek,clock-backend");
	if (IS_ERR(context.clock)) {
		ret = dev_err_probe(dev, PTR_ERR(context.clock),
				    "clock source unavailable\\n");
		goto put_platform;
	}
	context.bigidvfs = mt6797_a72_physical_source_get_device(dev, "mediatek,bigidvfs-backend");
	if (IS_ERR(context.bigidvfs)) {
		ret = dev_err_probe(dev, PTR_ERR(context.bigidvfs),
				    "BigiDVFS source unavailable\\n");
		goto put_clock;
	}

	ret = mt6797_a72_physical_source_run(&context, &mt6797_physical_runtime,
					     snapshot);
	if (ret)
		dev_err_probe(dev, ret, "direct physical snapshot failed\\n");
	else
		mt6797_a72_physical_source_log(dev, snapshot);

	put_device(context.bigidvfs);
put_clock:
	put_device(context.clock);
put_platform:
	put_device(context.platform);
free_snapshot:
	kvfree(snapshot);
	return ret;
}
""",
    )


if __name__ == "__main__":
    main()
