#!/usr/bin/env python3
"""Require the generic down-handoff source validator to fail closed."""

from __future__ import annotations

import argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile


FILES = (
    "include/linux/cpu.h",
    "kernel/cpu.c",
    "arch/arm64/include/asm/cpu_ops.h",
    "arch/arm64/kernel/smp.c",
    "arch/arm64/kernel/mt6797_psci.c",
)


def replace_once(path: pathlib.Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(old) != 1:
        raise RuntimeError(f"mutation anchor changed: {old}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def validate(validator: pathlib.Path,
             root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(validator), "--source-root", str(root)],
        check=False, capture_output=True, text=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    args = parser.parse_args()
    source = args.source_root.resolve()
    validator = pathlib.Path(__file__).resolve().parent / "validate_source.py"

    mutations = (
        ("preflight-removed", "kernel/cpu.c",
         "err = arch_cpu_down_preflight(cpu, target);",
         "err = 0;"),
        ("preflight-after-map-lock", "kernel/cpu.c",
         "\terr = arch_cpu_down_preflight(cpu, target);\n"
         "\tif (err)\n\t\treturn err;\n\n\tcpu_maps_update_begin();",
         "\tcpu_maps_update_begin();\n\terr = arch_cpu_down_preflight(cpu, target);\n"
         "\tif (err)\n\t\treturn err;"),
        ("validate-removed", "kernel/cpu.c",
         "ret = arch_cpu_down_validate(cpu, tasks_frozen, target);",
         "ret = 0;"),
        ("validate-after-write-lock", "kernel/cpu.c",
         "\tret = arch_cpu_down_validate(cpu, tasks_frozen, target);\n"
         "\tif (ret)\n\t\treturn ret;\n\n",
         ""),
        ("complete-removed", "kernel/cpu.c",
         "ret = arch_cpu_down_complete(cpu, target);", "ret = 0;"),
        ("complete-on-failure", "kernel/cpu.c",
         "\tif (!ret)\n\t\tret = arch_cpu_down_complete(cpu, target);",
         "\tret = arch_cpu_down_complete(cpu, target);"),
        ("failed-publication-removed", "kernel/cpu.c",
         "if (err && arch_cpu_down_failed(cpu, target, err))",
         "if (err)"),
        ("weak-default-effect", "kernel/cpu.c",
         "int __weak arch_cpu_down_preflight(unsigned int cpu,",
         "int __weak arch_cpu_down_preflight(unsigned int cpu,"),
        ("mt6797-callback-bound", "arch/arm64/kernel/mt6797_psci.c",
         "\t.cpu_can_disable = mt6797_psci_cpu_can_disable,",
         "\t.cpu_down_preflight = mt6797_psci_cpu_up_preflight,\n"
         "\t.cpu_can_disable = mt6797_psci_cpu_can_disable,"),
        ("disable-veto-opened", "arch/arm64/kernel/mt6797_psci.c",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn false;\n}",
         "static bool mt6797_psci_cpu_can_disable(unsigned int cpu)\n"
         "{\n\treturn true;\n}"),
    )

    positive = validate(validator, source)
    if positive.returncode:
        sys.stderr.write(positive.stdout + positive.stderr)
        return 1

    rejected = 0
    for name, relative, old, new in mutations:
        with tempfile.TemporaryDirectory(prefix="gemini-down-source-") as temp:
            root = pathlib.Path(temp)
            for item in FILES:
                target = root / item
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / item, target)
            if name == "validate-after-write-lock":
                replace_once(root / relative, old, new)
            elif name == "weak-default-effect":
                path = root / relative
                text = path.read_text(encoding="utf-8")
                marker = "int __weak arch_cpu_down_preflight(unsigned int cpu,"
                start = text.index(marker)
                body = text.index("\treturn 0;", start)
                text = text[:body] + "\treturn -EIO;" + text[body + len("\treturn 0;"):]
                path.write_text(text, encoding="utf-8")
            else:
                replace_once(root / relative, old, new)
            result = validate(validator, root)
            if result.returncode == 0:
                print(f"mutation={name} result=unexpected-pass", file=sys.stderr)
                return 1
            rejected += 1

    print(f"source_mutation_rejections={rejected}")
    print("source_validator_mutations=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
