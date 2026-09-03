#!/usr/bin/env python3
"""Require unsafe hotplug-snapshot source mutations to fail closed."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile


MUTATIONS = (
    ("internal", "CLOCK_POWERON_WRITES 1U", "CLOCK_POWERON_WRITES 2U"),
    ("internal", "ACQUIRE_WRITES_MAX 200U", "ACQUIRE_WRITES_MAX 201U"),
    ("internal", "RELEASE_WRITES_MAX 200U", "RELEASE_WRITES_MAX 201U"),
    ("internal", "BIGIDVFS_READS 8U", "BIGIDVFS_READS 7U"),
    ("source", "trace->platform_calls++;", "trace->platform_calls += 2;"),
    ("source", "trace->provider_calls++;", "trace->provider_calls += 2;"),
    ("source", "trace->clock_calls++;", "trace->clock_calls += 2;"),
    ("source", "trace->bigidvfs_calls++;", "trace->bigidvfs_calls += 2;"),
    ("source", "!clock.sample_generation", "clock.sample_generation == 0xdead"),
    ("source", "!bigidvfs.sample_generation", "bigidvfs.sample_generation == 0xdead"),
    ("source", "provider->vbuckb_b <= 0xffU", "provider->vbuckb_b <= 0x1ffU"),
    ("source", "!provider->reserved", "provider->reserved == 1"),
    ("source", "platform_set_drvdata(pdev, source);", "platform_set_drvdata(pdev, NULL);"),
    ("source", '"mediatek,clock-backend"', '"mediatek,clock-backend-wrong"'),
    ("source", "return mt6797_a72_provider_snapshot(snapshot);", "return 0;"),
    ("source", "return mt6797_dvfsp_clock_backend_read(dev, snapshot);", "return 0;"),
    ("source", "return mt6797_bigidvfs_backend_read(dev, snapshot);", "return 0;"),
    ("test", "KUNIT_CASE(hotplug_snapshot_provider_width_test),", ""),
    (
        "kconfig",
        "config MTK_MT6797_A72_HOTPLUG_SNAPSHOT\n"
        "\tbool \"MediaTek MT6797 CPU9 hotplug snapshot adapter\"\n"
        "\tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR\n"
        "\tdepends on MTK_MT6797_A72_PLATFORM_STATE\n"
        "\tdepends on MTK_MT6797_DVFSP_CLOCK_BACKEND",
        "config MTK_MT6797_A72_HOTPLUG_SNAPSHOT\n"
        "\tbool \"MediaTek MT6797 CPU9 hotplug snapshot adapter\"\n"
        "\tdepends on MTK_MT6797_A72_HOTPLUG_EXECUTOR\n"
        "\tdepends on MTK_MT6797_A72_PLATFORM_STATE\n"
        "\tdepends on OF",
    ),
    ("makefile", "mt6797-a72-hotplug-snapshot-test.o", "mt6797-a72-hotplug-snapshot.o"),
)


FILES = {
    "internal": "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot-internal.h",
    "source": "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot.c",
    "test": "drivers/soc/mediatek/mt6797-a72-hotplug-snapshot-test.c",
    "kconfig": "drivers/soc/mediatek/Kconfig",
    "makefile": "drivers/soc/mediatek/Makefile",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = Path(__file__).resolve().parent / "validate_hotplug_snapshot_source.py"
    rejected = 0
    for index, (label, old, new) in enumerate(MUTATIONS, start=1):
        with tempfile.TemporaryDirectory(prefix=f"hotplug-snapshot-mutation-{index}-") as name:
            root = Path(name)
            for relative in FILES.values():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, target)
            path = root / FILES[label]
            text = path.read_text(encoding="utf-8")
            if text.count(old) != 1:
                raise SystemExit(f"mutation anchor changed: {old}")
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            completed = subprocess.run(
                ["python3", str(validator), "--source-root", str(root)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if completed.returncode == 0:
                raise SystemExit(f"unsafe mutation accepted: {index}:{label}")
            rejected += 1
    print("hotplug_snapshot_mutations=pass")
    print(f"unsafe_mutations_rejected={rejected}")


if __name__ == "__main__":
    main()
