#!/usr/bin/env python3
"""Require unsafe physical-executor source mutations to fail validation."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate_physical_executor_source.py"
FILES = (
    "arch/arm64/kernel/mt6797_psci.c",
    "drivers/soc/mediatek/Kconfig",
    "drivers/soc/mediatek/Makefile",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor-internal.h",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor.c",
    "drivers/soc/mediatek/mt6797-a72-hotplug-executor-test.c",
)


def run(root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--source-root", str(root),
         "--require-tests"],
        check=False, capture_output=True, text=True,
    )


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text()
    if text.count(old) != 1:
        raise ValueError(f"mutation anchor changed: {old}")
    path.write_text(text.replace(old, new, 1))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    mutations = (
        ("cpu8-status-bit", FILES[3], "CPU8_STATUS BIT(7)", "CPU8_STATUS BIT(6)"),
        ("cpu9-status-bit", FILES[3], "CPU9_STATUS BIT(6)", "CPU9_STATUS BIT(7)"),
        ("dcm-mask", FILES[3], "DCM_MASK GENMASK(6, 0)", "DCM_MASK GENMASK(5, 0)"),
        ("affinity-level", FILES[3], "AFFINITY_LEVEL0 0U", "AFFINITY_LEVEL0 1U"),
        ("affinity-state", FILES[3], "AFFINITY_OFF 1", "AFFINITY_OFF 0"),
        ("default-on", FILES[1],
         "config MTK_MT6797_A72_HOTPLUG_EXECUTOR\n"
         "\tbool \"MediaTek MT6797 CPU9 physical-hotplug executor\"\n"
         "\tdepends on ARM64 && ARCH_MEDIATEK\n\tdefault n\n",
         "config MTK_MT6797_A72_HOTPLUG_EXECUTOR\n"
         "\tbool \"MediaTek MT6797 CPU9 physical-hotplug executor\"\n"
         "\tdepends on ARM64 && ARCH_MEDIATEK\n\tdefault y\n"),
        ("physical-call", FILES[4], "#include <linux/string.h>",
         "#include <linux/string.h>\n/* psci_ops.cpu_off */"),
        ("cluster-gate", FILES[4],
         "baseline->spm_mp2_cpusys_pwr_con ==",
         "baseline->spm_pwr_status =="),
        ("cpu8-core-gate", FILES[4], "baseline->spm_mp2_cpu0_pwr_con ==",
         "baseline->spm_mp2_cpu1_pwr_con =="),
        ("isolation-mask", FILES[4], "MT6797_A72_HOTPLUG_EXT_ISO_MASK",
         "0"),
        ("provider-gate", FILES[4], "memcmp(baseline->provider",
         "memcmp(baseline->bigidvfs"),
        ("clock-gate", FILES[4], "memcmp(baseline->clock",
         "memcmp(baseline->provider"),
        ("commit-authorization", FILES[4],
         "result->cpu_off_authorizations = 1;",
         "result->cpu_off_authorizations = 2;"),
        ("second-affinity", FILES[4], "result->affinity_calls++;",
         "result->affinity_calls++;\n\tops->affinity_info(context, cpu, 0);"),
        ("missing-snapshot", FILES[4], "ret = ops->snapshot(context, &result->post_state);",
         "ret = 0;"),
        ("missing-cpu8", FILES[4],
         "ret = ops->cpu8_callback(context, MT6797_A72_HOTPLUG_CPU8);",
         "ret = 0;"),
        ("returned-success", FILES[4],
         "\treturn mt6797_a72_hotplug_fault(controller, ops, context, result,\n"
         "\t\t\t\t\terror ? error : -EIO);\n",
         "\treturn 0;\n"),
        ("open-veto", FILES[0],
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn false;\n}",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn true;\n}"),
    )

    with tempfile.TemporaryDirectory(prefix="gemini-hotplug-source-") as name:
        baseline = pathlib.Path(name) / "baseline"
        for relative in FILES:
            target = baseline / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
        positive = run(baseline)
        if positive.returncode:
            sys.stderr.write(positive.stderr)
            return 1
        for mutation, relative, old, new in mutations:
            candidate = pathlib.Path(name) / mutation
            shutil.copytree(baseline, candidate)
            try:
                replace_once(candidate / relative, old, new)
            except ValueError as exc:
                print(exc, file=sys.stderr)
                return 1
            result = run(candidate)
            if result.returncode == 0:
                print(f"mutation={mutation} result=unexpected-pass",
                      file=sys.stderr)
                return 1

    print(f"physical_executor_source_mutation_rejections={len(mutations)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
