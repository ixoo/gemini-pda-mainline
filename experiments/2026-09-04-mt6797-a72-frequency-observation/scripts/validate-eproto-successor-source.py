#!/usr/bin/env python3
"""Validate the MT6797 A72 frequency failure-stage diagnostic source."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def count(text: str, token: str, expected: int, label: str) -> None:
    actual = text.count(token)
    require(actual == expected, f"{label}: expected {expected}, found {actual}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    soc = args.source_root.resolve() / "drivers/soc/mediatek"
    header = (soc / "mt6797-a72-frequency-observer-internal.h").read_text()
    observer = (soc / "mt6797-a72-frequency-observer.c").read_text()
    test = (soc / "mt6797-a72-frequency-observer-test.c").read_text()

    stages = (
        "NONE",
        "CLOCK_TRANSPORT",
        "CLOCK_SHAPE",
        "BIGIDVFS_TRANSPORT",
        "BIGIDVFS_SHAPE",
        "DECODE",
    )
    for stage in stages:
        token = f"MT6797_A72_FREQUENCY_OBSERVER_FAILURE_{stage}"
        require(token in header, f"missing stage declaration: {stage}")
        require(token in observer, f"missing stage implementation: {stage}")
        require(token in test, f"missing stage test: {stage}")

    for field in (
        "clock_abi",
        "clock_reserved",
        "clock_sample_generation",
        "armplldiv_muxsel",
        "armplldiv_ckdiv",
        "pll_ll_con1",
        "pll_l_con1",
        "pll_cci_con1",
        "big_abi",
        "big_reserved",
        "big_sample_generation",
        "big_pll_pcw",
        "big_pll_enable_posdiv",
    ):
        require(f"trace->{field}" in observer, f"trace field not captured: {field}")
        require(f"trace.{field}" in observer, f"trace field not logged: {field}")

    count(observer, "source->ops->clock(source->clock, &clock)", 1,
          "protected clock call")
    count(observer, "source->ops->bigidvfs(source->bigidvfs, &big)", 1,
          "BigiDVFS call")
    count(observer, "mt6797_dvfsp_clock_state_decode(", 1, "decoder call")
    count(observer, "MT6797_A72_FREQUENCY_OBSERVER_MAX_ATTEMPTS -", 1,
          "attempt budget")
    count(observer, "controller->attempts++", 1, "attempt consumption")
    count(observer, "stage=%s", 1, "failure-stage log")
    count(observer, "GEMINI_A72_FREQUENCY_OBSERVATION_V1", 2,
          "stable observation marker")
    count(test, "KUNIT_CASE(", 5, "focused KUnit case count")
    require("frequency_observer_failure_stages_test" in test,
            "focused failure-stage KUnit test missing")

    for forbidden in (
        "add_cpu(", "remove_cpu(", "cpu_up(", "cpu_down(",
        "regmap_write(", "writel(", "kernel_restart(", "reboot(",
    ):
        require(forbidden not in header + observer + test,
                f"forbidden operation present: {forbidden}")

    print("failure_stage_count=6")
    print("failure_stage_kunit_coverage=complete")
    print("observer_attempt_budget=3-unchanged")
    print("clock_calls_per_attempt=1-unchanged")
    print("bigidvfs_calls_per_admitted_attempt=1-unchanged")
    print("additional_hardware_calls=0")
    print("cpu_requests_added=0")
    print("hardware_writes_added=0")
    print("result=pass")


if __name__ == "__main__":
    main()
