#!/usr/bin/env python3
"""Validate the generated held-online patches and applied source."""

import argparse
from pathlib import Path


class ValidationError(RuntimeError):
    pass


PATHS = {
    "cpu": "kernel/cpu.c",
    "hps": "drivers/misc/mediatek/base/power/mt6797/mt_hotplug_strategy_algo.c",
    "psci": "arch/arm64/kernel/psci.c",
}


def once(text: str, token: str, label: str) -> int:
    count = text.count(token)
    if count != 1:
        raise ValidationError(f"{label}: expected one {token!r}, found {count}")
    return text.index(token)


def ordered(text: str, tokens: tuple[str, ...], label: str) -> None:
    positions = [text.find(token) for token in tokens]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ValidationError(f"{label}: ordering failed")


def validate_files(files: dict[str, str]) -> None:
    cpu, hps, psci = files["cpu"], files["hps"], files["psci"]
    down = cpu[cpu.index("int __ref cpu_down(unsigned int cpu)") :]
    down = down[: down.index("EXPORT_SYMBOL(cpu_down)")]
    once(down, "if (cpu == 8 || cpu == 9)", "generic CPU8/9 veto")
    ordered(
        down,
        (
            "if (cpu == 8 || cpu == 9)",
            "return -EPERM",
            "aee_rr_rec_cpu_caller",
            "cpu_maps_update_begin()",
            "_cpu_down",
        ),
        "pre-notifier generic veto",
    )
    if "__cpu_notify" in down[: down.index("return -EPERM")]:
        raise ValidationError("notifier precedes generic veto")

    action = hps[hps.index("static int hps_algo_do_cluster_action") :]
    action = action[: action.index("unsigned int hps_get_cluster_cpus")]
    once(action, "cpu_id_min == 8 && cpu_id_max == 9", "exact HPS cluster")
    ordered(
        action,
        (
            "cpu_id_min == 8 && cpu_id_max == 9",
            "cpu_online(8) && target_cores < 1",
            "target_cores = 1",
            "if (target_cores > online_cores)",
            "cpu_down(cpu)",
        ),
        "HPS floor dominance",
    )

    once(psci, "static void mt6797_a72_hold_ipi", "IPI callback")
    once(psci, "static void mt6797_a72_hold_workfn", "hold work")
    work = psci[psci.index("static void mt6797_a72_hold_workfn") :]
    work = work[: work.index("static void mt6797_a72_one_way_marker")]
    once(
        work,
        "ret || observed_cpu != 8 || !cpu_online(8) || cpu_online(9)",
        "exact IPI/accounting failure predicate",
    )
    ordered(
        work,
        (
            "smp_call_function_single(8",
            "observed_cpu != 8",
            "!cpu_online(8)",
            "cpu_online(9)",
            "atomic_inc(&mt6797_a72_hold_hits)",
            "sample == 1",
            "msecs_to_jiffies(5000)",
            "result=pass sample=2 cpu=8 cpu8=1 cpu9=0",
        ),
        "bounded IPI samples",
    )
    complete = psci[psci.index("int mt6797_a72_one_way_secondary_complete") :]
    complete = complete[: complete.index("static int cpu_power_on_buck")]
    ordered(
        complete,
        (
            '"cpu8-online-held"',
            "INIT_DELAYED_WORK",
            "msecs_to_jiffies(1000)",
            '"hold-schedule"',
        ),
        "hold scheduling after startup success",
    )
    for forbidden in (
        "psci_ops.cpu_off",
        "cpu_down(8)",
        "cpu_down(9)",
        "BigiDVFSSRAMLDODisable",
        "stress",
    ):
        if forbidden in work:
            raise ValidationError(f"hold work gained forbidden action: {forbidden}")
    if "mtk_wdt_restart" in work or "mtk_wdt_set_time_out" in work:
        raise ValidationError("hold work refreshes or changes watchdog")


def read_source(source: Path) -> dict[str, str]:
    return {name: (source / path).read_text() for name, path in PATHS.items()}


def validate_inventory(patch_dir: Path) -> None:
    expected = (
        "0001-hotplug-reject-one-way-CPU8-down-before-notifiers.patch",
        "0002-power-hold-one-CPU-in-the-one-way-A72-cluster.patch",
        "0003-diagnostic-sample-held-CPU8-with-two-IPIs.patch",
    )
    if tuple((patch_dir / "series").read_text().splitlines()) != expected:
        raise ValidationError("generated series changed")
    for name in expected:
        text = (patch_dir / name).read_text()
        if "Signed-off-by:" in text:
            raise ValidationError(f"experiment patch has synthetic sign-off: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--patch-dir", required=True, type=Path)
    args = parser.parse_args()
    validate_inventory(args.patch_dir)
    validate_files(read_source(args.source))
    print("validation=cpu8-held-online-generated-source")
    print("veto_order=passed")
    print("ipi_hold_contract=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
