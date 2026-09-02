#!/usr/bin/env python3
"""Validate no-op-by-default generic CPU-down lifecycle handoffs."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"source_validation=fail reason={message}")


def collapse(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def braced(source: str, start: str, label: str) -> str:
    first = source.find(start)
    require(first >= 0, f"{label}: start missing")
    opening = source.find("{", first)
    require(opening >= 0, f"{label}: opening brace missing")
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[first:index + 1]
    raise SystemExit(f"source_validation=fail reason={label}: unterminated")


def ordered(source: str, tokens: tuple[str, ...], label: str) -> None:
    cursor = 0
    for token in tokens:
        position = source.find(token, cursor)
        require(position >= 0, f"{label}: missing/out-of-order {token}")
        cursor = position + len(token)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()

    cpu_h = (root / "include/linux/cpu.h").read_text(encoding="utf-8")
    cpu_c = (root / "kernel/cpu.c").read_text(encoding="utf-8")
    cpu_ops = (root / "arch/arm64/include/asm/cpu_ops.h").read_text(
        encoding="utf-8")
    smp = (root / "arch/arm64/kernel/smp.c").read_text(encoding="utf-8")
    mt_psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text(
        encoding="utf-8")
    normalized = collapse(cpu_c)

    names = (
        "arch_cpu_down_preflight",
        "arch_cpu_down_validate",
        "arch_cpu_down_complete",
        "arch_cpu_down_failed",
    )
    for name in names:
        require(cpu_h.count(f"int {name}(") == 1,
                f"one declaration for {name}")
        require(cpu_c.count(f"int __weak {name}(") == 1,
                f"one no-op default for {name}")
        require(smp.count(f"int {name}(") == 1,
                f"one arm64 dispatcher for {name}")
        field = name.removeprefix("arch_")
        require(cpu_ops.count(f"(*{field})(") == 1,
                f"one operation field for {field}")
        dispatcher = braced(smp, f"int {name}(", f"{name} dispatcher")
        require(f"ops->{field}" in dispatcher,
                f"{name} dispatches the matching operation")
        require("return 0;" in dispatcher,
                f"{name} has an unset no-op path")
        default = braced(cpu_c, f"int __weak {name}(", f"{name} default")
        require(collapse(default).endswith("{ return 0; }"),
                f"{name} weak default is effect-free")

    preflight = braced(normalized, "static int cpu_down(", "cpu_down")
    ordered(preflight, (
        "err = arch_cpu_down_preflight(cpu, target);",
        "if (err) return err;",
        "cpu_maps_update_begin();",
        "err = cpu_down_maps_locked(cpu, target);",
        "cpu_maps_update_done();",
        "if (err && arch_cpu_down_failed(cpu, target, err))",
    ), "preflight placement")

    down = braced(normalized, "static int __ref _cpu_down(", "_cpu_down")
    ordered(down, (
        "ret = arch_cpu_down_validate(cpu, tasks_frozen, target);",
        "if (ret) return ret;",
        "if (num_online_cpus() == 1)",
        "if (!cpu_present(cpu))",
        "cpus_write_lock();",
        "ret = cpuhp_down_callbacks(cpu, st, target);",
        "if (!ret) ret = arch_cpu_down_complete(cpu, target);",
        "cpus_write_unlock();",
    ), "validate/complete placement")
    require(down.count("arch_cpu_down_validate(") == 1,
            "one down validation call")
    require(down.count("arch_cpu_down_complete(") == 1,
            "one down completion call")

    for field in ("cpu_down_preflight", "cpu_down_validate",
                  "cpu_down_complete", "cpu_down_failed"):
        require(f".{field}" not in mt_psci,
                f"MT6797 production callback remains unset: {field}")
    can_disable = braced(mt_psci,
                         "static bool mt6797_psci_cpu_can_disable(",
                         "MT6797 disable veto")
    require(collapse(can_disable).endswith("{ return false; }"),
            "MT6797 disable veto changed")

    patch_scope = cpu_h + cpu_c + cpu_ops + smp
    for forbidden in (
        "psci_ops.cpu_off", "psci_ops.affinity_info", "arm_smccc_smc",
        "cpu_down(9", "cpu_up(9", "readl(", "writel(", "regmap_",
        "watchdog", "ramoops", "pstore",
    ):
        require(forbidden not in patch_scope,
                f"generic handoff slice gained physical behavior: {forbidden}")

    print("source_phase=generic-down-handoffs")
    print("preflight=before-cpu-map-lock")
    print("validate=after-cpu-map-lock-before-cpu-hotplug-write-lock")
    print("complete=after-full-down-before-cpu-hotplug-write-unlock")
    print("failed=after-cpu-map-lock-release-on-nonzero-result")
    print("weak_defaults=no-op")
    print("mt6797_callbacks=unset")
    print("mt6797_cpu_can_disable=false")
    print("physical_effect_calls=0")
    print("boot_candidate=false")
    print("device_action=false")
    print("source_validation=pass")


if __name__ == "__main__":
    main()
