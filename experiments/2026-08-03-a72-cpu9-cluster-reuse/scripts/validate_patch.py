#!/usr/bin/env python3
"""Validate generated CPU9 cluster-reuse source and patch inventory."""

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    pass


def once(text: str, token: str, label: str) -> int:
    count = text.count(token)
    if count != 1:
        raise ValidationError(f"{label}: expected one {token!r}, found {count}")
    return text.index(token)


def ordered(text: str, tokens: tuple[str, ...], label: str) -> None:
    positions = [text.find(token) for token in tokens]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ValidationError(f"{label}: ordering failed")


def function(text: str, start: str, end: str) -> str:
    begin = text.index(start)
    finish = text.index(end, begin)
    return text[begin:finish]


def read_sources(source: Path) -> dict[str, str]:
    return {
        "psci": (source / "arch/arm64/kernel/psci.c").read_text(),
        "smp": (source / "arch/arm64/kernel/smp.c").read_text(),
        "kconfig": (source / "drivers/misc/mediatek/base/power/Kconfig").read_text(),
    }


def validate_source(sources: dict[str, str]) -> None:
    psci = sources["psci"]
    smp = sources["smp"]
    kconfig = sources["kconfig"]
    once(kconfig, "config MTK_A72_CPU9_CLUSTER_REUSE", "CPU9 Kconfig")
    once(kconfig, "depends on MTK_A72_ONE_WAY_CPU8", "exact parent dependency")

    boot = function(
        psci,
        "static int mt6797_a72_cpu9_boot(unsigned int cpu)",
        "#endif\n\nstatic int mt6797_a72_one_way_boot",
    )
    for token in (
        "if (cpu != 9)",
        "atomic_xchg(&mt6797_a72_cpu9_attempted, 1)",
        "READ_ONCE(mt6797_a72_one_way_psci_accepted)",
        "g_cl2_online & 1",
        "!cpu_online(8)",
        "cpu_online(9)",
        'mt6797_a72_cpu9_marker("rejected-prestate"',
        "psci_ops.cpu_on(cpu_logical_map(cpu), __pa(secondary_entry))",
        'mt6797_a72_cpu9_marker("fault-retain-psci"',
        "WRITE_ONCE(mt6797_a72_cpu9_psci_accepted, true)",
    ):
        once(boot, token, "CPU9 PSCI-only path")
    ordered(
        boot,
        (
            "if (cpu != 9)",
            "atomic_xchg(&mt6797_a72_cpu9_attempted, 1)",
            "READ_ONCE(mt6797_a72_one_way_psci_accepted)",
            "g_cl2_online & 1",
            "!cpu_online(8)",
            "cpu_online(9)",
            'mt6797_a72_cpu9_marker("rejected-prestate"',
            "psci_ops.cpu_on(cpu_logical_map(cpu), __pa(secondary_entry))",
            "mt6797_a72_obs_lifecycle",
            'mt6797_a72_cpu9_marker("fault-retain-psci"',
            "WRITE_ONCE(mt6797_a72_cpu9_psci_accepted, true)",
        ),
        "CPU9 entry and standard PSCI ordering",
    )
    for forbidden in (
        "da9214_a72_diag_compare_update",
        "mt6797_a72_diag_spm_compare_update",
        "mt6797_a72_diag_toprgu_compare_update",
        "mt6797_a72_one_way_sram_set_verify",
        "mt6797_a72_one_way_dcm_enable",
        "BigiDVFSSRAMLDOSet",
        "psci_ops.cpu_off",
        "cpu_down",
    ):
        if forbidden in boot:
            raise ValidationError(f"CPU9 path replays/uses forbidden action: {forbidden}")

    complete = function(
        psci,
        "int mt6797_a72_one_way_secondary_complete",
        "#endif\n\nstatic int cpu_power_on_buck",
    )
    for token in (
        "if (cpu == 9)",
        "READ_ONCE(mt6797_a72_cpu9_psci_accepted)",
        "!completed",
        "g_cl2_online & 1",
        "!cpu_online(8)",
        "!cpu_online(9)",
        'mt6797_a72_cpu9_marker("fault-retain-secondary"',
        'mt6797_a72_cpu9_marker("cpu9-online-held", "complete", 0)',
        "INIT_DELAYED_WORK(&mt6797_a72_hold_work",
        "msecs_to_jiffies(1000)",
    ):
        if token not in complete:
            raise ValidationError(f"CPU9 completion lacks: {token}")
    ordered(
        complete,
        (
            "if (cpu == 9)",
            "READ_ONCE(mt6797_a72_cpu9_psci_accepted)",
            "!completed",
            "g_cl2_online & 1",
            "!cpu_online(8)",
            "!cpu_online(9)",
            'mt6797_a72_cpu9_marker("fault-retain-secondary"',
            'mt6797_a72_cpu9_marker("cpu9-online-held", "complete", 0)',
            "INIT_DELAYED_WORK(&mt6797_a72_hold_work",
            "schedule_delayed_work",
        ),
        "CPU9 completion ordering",
    )

    work = function(
        psci,
        "static void mt6797_a72_hold_workfn",
        "static void mt6797_a72_one_way_marker",
    )
    pair = function(
        work,
        "#ifdef CONFIG_MTK_A72_CPU9_CLUSTER_REUSE",
        "#else\n\tint observed_cpu = -1;",
    )
    for token in (
        "smp_call_function_single(8",
        "smp_call_function_single(9",
        "observed_cpu8 != 8",
        "observed_cpu9 != 9",
        "!cpu_online(8)",
        "!cpu_online(9)",
        "hits8 != hits9",
        "atomic_inc(&mt6797_a72_hold_hits)",
        "atomic_inc(&mt6797_a72_cpu9_hits)",
        "sample < 3",
        "sample == 1 ? 5000 : 4000",
        "result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3",
    ):
        once(pair, token, "pair sampler")
    ordered(
        pair,
        (
            "hits8 = atomic_read",
            "hits9 = atomic_read",
            "hits8 == hits9",
            "smp_call_function_single(8",
            "smp_call_function_single(9",
            "observed_cpu8 != 8",
            "observed_cpu9 != 9",
            "!cpu_online(8)",
            "!cpu_online(9)",
            "hits8 != hits9",
            "atomic_inc(&mt6797_a72_hold_hits)",
            "atomic_inc(&mt6797_a72_cpu9_hits)",
            "sample < 3",
            "sample == 1 ? 5000 : 4000",
            "schedule_delayed_work",
            "result=pass sample=3 cpu8=8 cpu9=9 online8=1 online9=1 hits8=3 hits9=3",
        ),
        "pair sample state machine",
    )
    for forbidden in (
        "psci_ops.cpu_off",
        "cpu_down",
        "BigiDVFSSRAMLDODisable",
        "mtk_wdt_restart",
        "stress",
    ):
        if forbidden in pair:
            raise ValidationError(f"pair sampler gained forbidden action: {forbidden}")

    for token in (
        "CONFIG_MTK_A72_CPU9_CLUSTER_REUSE",
        "|| cpu == 9",
        "&& cpu != 9",
        "mt6797_a72_one_way_secondary_complete",
    ):
        if token not in smp:
            raise ValidationError(f"generic CPU9 completion guard lacks: {token}")
    if "if (cpu == 8 || cpu == 9)" not in psci:
        raise ValidationError("inherited platform CPU8/9 disable veto changed")
    if "if (cpu == 8 || cpu == 9)" not in sources.get("cpu", ""):
        # kernel/cpu.c is intentionally supplied by read_sources below.
        raise ValidationError("inherited public CPU8/9 down veto changed")


def validate_inventory(patch_dir: Path) -> None:
    expected = "0001-diagnostic-start-CPU9-by-reusing-the-prepared-cluster.patch"
    if (patch_dir / "series").read_text().splitlines() != [expected]:
        raise ValidationError("generated series changed")
    patch = (patch_dir / expected).read_text()
    if "Signed-off-by:" in patch:
        raise ValidationError("experiment patch has a synthetic sign-off")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--patch-dir", required=True, type=Path)
    args = parser.parse_args()
    sources = read_sources(args.source)
    sources["cpu"] = (args.source / "kernel/cpu.c").read_text()
    validate_inventory(args.patch_dir)
    validate_source(sources)
    print("validation=cpu9-cluster-reuse-generated-source")
    print("cpu9_path=one-shot-standard-psci-only")
    print("pair_samples=three-bounded-synchronous")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
