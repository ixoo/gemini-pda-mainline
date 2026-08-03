#!/usr/bin/env python3
"""Validate the generated late-hold patch and applied source."""

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


def read_source(source: Path) -> str:
    return (source / "arch/arm64/kernel/psci.c").read_text()


def validate_source(psci: str) -> None:
    work = psci[psci.index("static void mt6797_a72_hold_workfn") :]
    work = work[: work.index("static void mt6797_a72_one_way_marker")]
    once(work, "smp_call_function_single(8", "CPU8 synchronous IPI")
    once(work, "sample == 1 ? 5000 : 4000", "exact late timing")
    once(work, "sample < 3", "three-sample bound")
    once(work, "result=pass sample=3 cpu=8 cpu8=1 cpu9=0 hits=3", "terminal")
    ordered(
        work,
        (
            "smp_call_function_single(8",
            "observed_cpu != 8",
            "!cpu_online(8)",
            "cpu_online(9)",
            "atomic_inc(&mt6797_a72_hold_hits)",
            "sample < 3",
            "sample == 1 ? 5000 : 4000",
            "schedule_delayed_work",
            "result=pass sample=3 cpu=8 cpu8=1 cpu9=0 hits=3",
        ),
        "late sample state machine",
    )
    for token in (
        "gemini-a72-hold-v2 result=fault",
        "gemini-a72-hold-v2 result=sample",
        "gemini-a72-hold-v2 result=pass",
    ):
        if token not in work:
            raise ValidationError(f"missing versioned record: {token}")
    for forbidden in (
        "psci_ops.cpu_off",
        "cpu_down(8)",
        "cpu_down(9)",
        "mtk_wdt_restart",
        "mtk_wdt_set_time_out",
        "BigiDVFSSRAMLDODisable",
        "stress",
    ):
        if forbidden in work:
            raise ValidationError(f"late work gained forbidden action: {forbidden}")


def validate_inventory(patch_dir: Path) -> None:
    expected = "0001-diagnostic-retain-a-late-CPU8-IPI-sample.patch"
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
    validate_inventory(args.patch_dir)
    validate_source(read_source(args.source))
    print("validation=cpu8-late-hold-generated-source")
    print("late_ipi_contract=passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
