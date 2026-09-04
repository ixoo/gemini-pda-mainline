#!/usr/bin/env python3
"""Test runtime materialization and strict observation classification."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUILDER = HERE / "build-production-runtime.sh"
CLASSIFIER = HERE / "classify-production-runtime.py"
LIFECYCLE_TEST = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/"
    "test-topology-load-tooling.py"
)
CONCURRENT_TEST = ROOT / (
    "experiments/2026-09-02-mainline-dual-a72-concurrent-multiline/scripts/"
    "test_runtime_tools.py"
)
BOOT_ID = "22222222-2222-4222-8222-222222222222"
CURRENT_RELEASE = "7.1.3-gemini-a72-frequency-thermal"
OBS_BEGIN = "__A72_FREQUENCY_THERMAL_BEGIN__"
OBS_END = "__A72_FREQUENCY_THERMAL_END__"
CONCURRENT_BEGIN = "__GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__"
CONCURRENT_END = "__GEMINI_A72_CONCURRENT_MULTILINE_END__"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load(path: Path, name: str):
    specification = importlib.util.spec_from_file_location(name, path)
    require(specification is not None and specification.loader is not None,
            f"cannot load test source: {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def sample(attempt: int) -> str:
    return " ".join((
        "abi=1",
        f"attempt={attempt}",
        "max_attempts=3",
        f"remaining={3 - attempt}",
        f"clock_generation={10 + attempt}",
        f"big_generation={12 + attempt}",
        "armplldiv_muxsel=0x00000055",
        "armplldiv_ckdiv=0x00042108",
        "big_pll_pcw=0xc1130000",
        "big_pll_enable_posdiv=0x07001000",
        "b_pcw=0x41130000",
        "b_posdiv=1",
        "b_mux=1",
        "b_divider=8",
        "ll_khz=897000",
        "l_khz=1274000",
        "b_khz=845000",
        "cci_khz=629500",
    ))


def passing_capture() -> str:
    lifecycle = load(LIFECYCLE_TEST, "topology_load_test")
    concurrent = load(CONCURRENT_TEST, "concurrent_runtime_test")
    lifecycle_text = lifecycle.lifecycle_fixture().replace(
        "kernel_release=7.1.3-gemini-a72-hotplug-physical",
        f"kernel_release={CURRENT_RELEASE}",
        1,
    )
    fields = concurrent.passing_fields()
    fields["boot_id"] = BOOT_ID
    fields["kernel_release"] = CURRENT_RELEASE
    before = sample(1)
    during = sample(2)
    after = sample(3)
    setup = (
        OBS_BEGIN,
        "frequency_observer_count=1",
        "frequency_observer_mode=444",
        "frequency_log_count_before=0",
        "thermal_zone_count=1",
        "thermal_zone_type=soc-thermal",
        f"frequency_before={before}",
        "thermal_before_millicelsius=36000",
        CONCURRENT_BEGIN,
    )
    concurrent_lines: list[str] = []
    for key, value in fields.items():
        concurrent_lines.append(f"{key}={value}")
        if key == "spin_limit":
            concurrent_lines.extend((
                "writer8_alive_before_observation=1",
                "writer9_alive_before_observation=1",
                f"frequency_during={during}",
                "thermal_during_millicelsius=37000",
                "writer8_alive_after_observation=1",
                "writer9_alive_after_observation=1",
                "writer_start_released=1",
            ))
        if key == "reader9_status":
            concurrent_lines.extend((
                f"frequency_after={after}",
                "thermal_after_millicelsius=36500",
            ))
        if key == "reboot_request":
            concurrent_lines.extend((
                "frequency_log_count=3",
                f"[ 10.0] snapshot: GEMINI_A72_FREQUENCY_OBSERVATION_V1 {before}",
                f"[ 10.1] snapshot: GEMINI_A72_FREQUENCY_OBSERVATION_V1 {during}",
                f"[ 10.2] snapshot: GEMINI_A72_FREQUENCY_OBSERVATION_V1 {after}",
            ))
    return "\n".join((
        lifecycle_text.rstrip("\n"), *setup, *concurrent_lines,
        CONCURRENT_END, OBS_END, "",
    ))


def classify(text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(
            prefix="a72-frequency-runtime-test-") as name:
        capture = Path(name) / "capture.txt"
        capture.write_text(text, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(CLASSIFIER), str(capture),
             "--boot-id", BOOT_ID],
            check=False, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


def main() -> int:
    materialized = subprocess.run(
        [str(BUILDER), "--boot-id", BOOT_ID], check=True, text=True,
        stdout=subprocess.PIPE,
    ).stdout
    require("__EXPECTED_BOOT_ID__" not in materialized,
            "boot-ID marker remained")
    require(materialized.count(BOOT_ID) == 2,
            "materialized boot-ID count changed")
    require(materialized.count(
        '[ "$($BB uname -r)" = 7.1.3-gemini-a72-frequency-thermal ] || '
        'reject_preflight kernel-identity') == 1,
        "production kernel identity was not materialized")
    require(materialized.count(
        "018de9150ffcf0b7b30fe7c45f3863555909c87e92ec4e868f30ef74a0e8cd2e"
    ) == 1, "production record identity was not materialized")
    for stale in (
        '[ "$($BB uname -r)" = 7.1.3-gemini-a72-hotplug-physical ]',
        "d4940602e7ad9cbc947376bfb9dc4222ef5a671faa15eb42a821df1852af9ba4",
    ):
        require(stale not in materialized,
                f"stale lifecycle identity remained: {stale}")
    require(materialized.count("frequency_observe before") == 1 and
            materialized.count("frequency_observe during") == 1 and
            materialized.count("frequency_observe after") == 1,
            "three-attempt observation boundary changed")
    require(materialized.count('cat "$FREQUENCY_OBSERVER"') == 1,
            "observer transport site count changed")
    require(materialized.count(
        "failure_additional_frequency_observation_request=none") == 1 and
        materialized.count(
            "grep -F 'GEMINI_A72_FREQUENCY_OBSERVATION_V1'") >= 2,
        "observer failure evidence path changed")
    require(materialized.index("frequency_observe before") <
            materialized.index('kill -0 "$pid8"') <
            materialized.index("frequency_observe during") <
            materialized.index('touch "$START_WRITE"') <
            materialized.index("frequency_observe after"),
            "materialized observation order changed")
    require(materialized.count("taskset 100") >= 2 and
            materialized.count("taskset 200") >= 2,
            "CPU8/CPU9 bounded workers weakened")
    require("ROUNDS=4" in materialized and "SPIN_LIMIT=1000000" in materialized,
            "finite workload limits changed")
    for forbidden in (
        "/dev/mmcblk", "reboot -f", "poweroff",
        "/sys/devices/system/cpu/cpu8/online",
        "/sys/devices/system/cpu/cpu9/online",
    ):
        require(forbidden not in materialized,
                f"forbidden action appeared: {forbidden}")

    valid = passing_capture()
    accepted = classify(valid)
    require(accepted.returncode == 0,
            f"valid runtime fixture rejected: {accepted.stdout}")
    require(
        "runtime_classification=stage18-thermal-frequency-bounded-load-pass"
        in accepted.stdout,
        "success classification changed",
    )
    failed = classify(
        valid + "__A72_FREQUENCY_THERMAL_REJECTED__ reason=frequency-before\n"
        "GEMINI_A72_FREQUENCY_OBSERVATION_V1 attempt=1/3 ret=-11\n"
    )
    require(failed.returncode == 3,
            "observer failure fixture was not rejected")
    require("frequency_observer_attempts=1-of-3" in failed.stdout and
            "frequency_observer_kernel_callbacks=1" in failed.stdout and
            "frequency_observer_errno=-11" in failed.stdout,
            "observer failure identity was not preserved")
    retried_failure = classify(
        valid + "__A72_FREQUENCY_THERMAL_REJECTED__ reason=frequency-before\n"
        "GEMINI_A72_FREQUENCY_OBSERVATION_V1 attempt=1/3 ret=-71\n"
        "GEMINI_A72_FREQUENCY_OBSERVATION_V1 attempt=2/3 ret=-71\n"
    )
    require(retried_failure.returncode == 3,
            "two-callback observer failure fixture was not rejected")
    require("frequency_observer_attempts=1-2-of-3" in retried_failure.stdout and
            "frequency_observer_kernel_callbacks=2" in retried_failure.stdout and
            "frequency_observer_errno=-71" in retried_failure.stdout,
            "two-callback observer failure identity was not preserved")
    mutations = (
        valid.replace("attempt=2", "attempt=1", 1),
        valid.replace("remaining=0", "remaining=1", 1),
        valid.replace("clock_generation=12", "clock_generation=11", 1),
        valid.replace("b_pcw=0x41130000", "b_pcw=0x41130001", 1),
        valid.replace("b_khz=845000", "b_khz=846000", 1),
        valid.replace("thermal_during_millicelsius=37000",
                      "thermal_during_millicelsius=130000", 1),
        valid.replace("frequency_observer_mode=444",
                      "frequency_observer_mode=644", 1),
        valid.replace("frequency_log_count_before=0",
                      "frequency_log_count_before=1", 1),
        valid.replace("writer8_alive_before_observation=1",
                      "writer8_alive_before_observation=0", 1),
        valid.replace("writer9_alive_after_observation=1",
                      "writer9_alive_after_observation=0", 1),
        valid.replace("writer_start_released=1", "writer_start_released=0", 1),
        valid.replace("frequency_log_count=3", "frequency_log_count=2", 1),
        valid.replace("GEMINI_A72_FREQUENCY_OBSERVATION_V1 abi=1 attempt=2",
                      "GEMINI_A72_FREQUENCY_OBSERVATION_V1 abi=1 attempt=1", 1),
        valid.replace("writer8_rounds_completed=4",
                      "writer8_rounds_completed=3", 1),
        valid.replace("cpu9_stat_after=cpu9 2 0 3 103 0 0 0 0 0 0",
                      "cpu9_stat_after=cpu9 1 0 2 3 0 0 0 0 0 0", 1),
        valid.replace("restore_last_stage=18", "restore_last_stage=17", 1),
        valid.replace(CONCURRENT_END, "", 1),
        valid.replace(OBS_END, "", 1),
    )
    rejected = sum(classify(text).returncode != 0 for text in mutations)
    require(rejected == len(mutations),
            f"runtime mutation rejection changed: {rejected}/{len(mutations)}")
    print("validation=mt6797-a72-frequency-production-runtime-tools")
    print("success_cases=1")
    print(f"mutations_rejected={rejected}")
    print("frequency_attempts=3-exact")
    print("worker_liveness=both-sides-of-during-observation")
    print("concurrent_rounds=4")
    print("forbidden_actions=absent")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
