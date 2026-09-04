#!/usr/bin/env python3
"""Classify one stage-18 thermal/frequency observation and finite workload."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import subprocess
import sys
import tempfile


CURRENT_RELEASE = "7.1.3-gemini-a72-frequency-thermal"
LIFECYCLE_RELEASE = "7.1.3-gemini-a72-hotplug-physical"
CONCURRENT_RELEASE = "7.1.3-gemini-cpu9-progress"
LIFECYCLE_SHA256 = "d1b618adce29b853c02ee19d47fa41be1fc5ac32411c34c34552ceadebe4b81f"
CONCURRENT_SHA256 = "1f6c8f3ac1663db5aa796e529984dfb5a9acc3d5e1f60391336bedf34efb8d79"
LIFECYCLE_PASS = "stage18-repeat-and-mt6797-4+4+2-topology-pass"
OBS_BEGIN = "__A72_FREQUENCY_THERMAL_BEGIN__"
OBS_END = "__A72_FREQUENCY_THERMAL_END__"
CONCURRENT_BEGIN = "__GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__"
CONCURRENT_END = "__GEMINI_A72_CONCURRENT_MULTILINE_END__"
LIFECYCLE_BEGIN = "__A72_TOPOLOGY_REPEAT_TRIGGER_BEGIN__"
LIFECYCLE_END = "__A72_TOPOLOGY_REPEAT_TRIGGER_END__"
LOG_MARKER = "GEMINI_A72_FREQUENCY_OBSERVATION_V1 "
OBSERVATION_FIELDS = {
    "abi", "attempt", "max_attempts", "remaining", "clock_generation",
    "big_generation", "armplldiv_muxsel", "armplldiv_ckdiv",
    "big_pll_pcw", "big_pll_enable_posdiv", "b_pcw", "b_posdiv",
    "b_mux", "b_divider", "ll_khz", "l_khz", "b_khz", "cci_khz",
}
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
LIFECYCLE = ROOT / (
    "experiments/2026-09-02-mainline-a72-hotplug-lifecycle-gate/scripts/"
    "classify-topology-repeat-trigger.py"
)
CONCURRENT = ROOT / (
    "experiments/2026-09-02-mainline-dual-a72-concurrent-multiline/scripts/"
    "classify-attempt.py"
)


class Rejected(ValueError):
    """A strict runtime predicate failed."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Rejected(reason)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bounded(text: str, begin: str, end: str) -> str:
    require(text.count(begin) == 1 and text.count(end) == 1,
            f"boundary-count:{begin}")
    start = text.index(begin) + len(begin)
    finish = text.index(end, start)
    require(start < finish, f"boundary-order:{begin}")
    return text[start:finish]


def strict_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if not re.fullmatch(r"[a-z0-9_]+=[^\n]*", line):
            continue
        key, value = line.split("=", 1)
        require(key not in fields, f"duplicate-field:{key}")
        fields[key] = value
    return fields


def observation(value: str, attempt: int) -> dict[str, int | str]:
    parsed: dict[str, str] = {}
    for item in value.split():
        require(item.count("=") == 1, f"observation-token-shape:{attempt}")
        key, field = item.split("=", 1)
        require(key not in parsed, f"observation-duplicate:{attempt}:{key}")
        parsed[key] = field
    require(set(parsed) == OBSERVATION_FIELDS,
            f"observation-field-set:{attempt}")
    numeric: dict[str, int | str] = {}
    for key, field in parsed.items():
        if key in {
                "armplldiv_muxsel", "armplldiv_ckdiv", "big_pll_pcw",
                "big_pll_enable_posdiv", "b_pcw"}:
            require(bool(re.fullmatch(r"0x[0-9a-f]{8}", field)),
                    f"observation-hex:{attempt}:{key}")
            numeric[key] = int(field, 16)
        else:
            require(bool(re.fullmatch(r"[0-9]+", field)),
                    f"observation-integer:{attempt}:{key}")
            numeric[key] = int(field)
    require(numeric["abi"] == 1, f"observation-abi:{attempt}")
    require(numeric["attempt"] == attempt,
            f"observation-attempt:{attempt}")
    require(numeric["max_attempts"] == 3,
            f"observation-limit:{attempt}")
    require(numeric["remaining"] == 3 - attempt,
            f"observation-remaining:{attempt}")
    require(int(numeric["clock_generation"]) > 0 and
            int(numeric["big_generation"]) > 0,
            f"observation-generation:{attempt}")
    require(numeric["b_pcw"] ==
            (int(numeric["big_pll_pcw"]) & 0x7FFFFFFF),
            f"observation-big-pcw:{attempt}")
    require(numeric["b_posdiv"] ==
            ((int(numeric["big_pll_enable_posdiv"]) >> 12) & 0x7),
            f"observation-big-posdiv:{attempt}")
    mhz = (26 * int(numeric["b_pcw"])) >> 24
    expected_b_khz = (mhz >> int(numeric["b_posdiv"])) * 1000
    require(numeric["b_khz"] == expected_b_khz and expected_b_khz > 0,
            f"observation-big-frequency:{attempt}")
    for key in ("ll_khz", "l_khz", "b_khz", "cci_khz"):
        require(26_000 <= int(numeric[key]) <= 3_000_000,
                f"observation-frequency-range:{attempt}:{key}")
    require(0 <= int(numeric["b_mux"]) <= 3 and
            0 <= int(numeric["b_divider"]) <= 31,
            f"observation-selector-range:{attempt}")
    numeric["raw"] = value
    return numeric


def load_concurrent():
    require(digest(CONCURRENT) == CONCURRENT_SHA256,
            "concurrent-classifier-changed")
    specification = importlib.util.spec_from_file_location(
        "a72_concurrent_classifier", CONCURRENT
    )
    require(specification is not None and specification.loader is not None,
            "concurrent-classifier-load")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def classify_lifecycle(text: str, boot_id: str, root: Path) -> None:
    require(digest(LIFECYCLE) == LIFECYCLE_SHA256,
            "lifecycle-classifier-changed")
    frame = f"{LIFECYCLE_BEGIN}{bounded(text, LIFECYCLE_BEGIN, LIFECYCLE_END)}{LIFECYCLE_END}\n"
    current = f"kernel_release={CURRENT_RELEASE}\n"
    require(frame.count(current) == 1, "lifecycle-release-count")
    path = root / "lifecycle.txt"
    path.write_text(frame.replace(
        current, f"kernel_release={LIFECYCLE_RELEASE}\n", 1
    ), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(LIFECYCLE), str(path), "--boot-id", boot_id],
        check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    require(result.returncode == 0, "lifecycle-classifier-rejected")
    require(f"runtime_classification={LIFECYCLE_PASS}\n" in result.stdout,
            "lifecycle-classification-changed")


def classify_concurrent(text: str, boot_id: str, root: Path) -> dict[int, int]:
    module = load_concurrent()
    frame = f"{CONCURRENT_BEGIN}{bounded(text, CONCURRENT_BEGIN, CONCURRENT_END)}{CONCURRENT_END}\n"
    current = f"kernel_release={CURRENT_RELEASE}\n"
    require(frame.count(current) == 1, "concurrent-release-count")
    path = root / "concurrent.txt"
    path.write_text(frame.replace(
        current, f"kernel_release={CONCURRENT_RELEASE}\n", 1
    ), encoding="utf-8")
    try:
        fields = module.fields_from_capture(path)
        return module.validate_fields(fields, boot_id)
    except module.Classification as error:
        raise Rejected(f"concurrent:{error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--boot-id", required=True)
    args = parser.parse_args()
    try:
        require(bool(re.fullmatch(
            r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
            args.boot_id,
        )), "expected-boot-id")
        text = args.capture.read_text(
            encoding="utf-8", errors="replace"
        ).replace("\r", "")
        require("__A72_FREQUENCY_THERMAL_REJECTED__" not in text,
                "device-frequency-gate-rejected")
        require("concurrent_result=fail" not in text,
                "device-concurrent-gate-rejected")
        obs_frame = bounded(text, OBS_BEGIN, OBS_END)
        lifecycle_finish = text.index(LIFECYCLE_END)
        obs_start = text.index(OBS_BEGIN)
        concurrent_start = text.index(CONCURRENT_BEGIN)
        during = text.index("frequency_during=")
        release = text.index("writer_start_released=1")
        after = text.index("frequency_after=")
        concurrent_finish = text.index(CONCURRENT_END)
        obs_finish = text.index(OBS_END)
        require(lifecycle_finish < obs_start < concurrent_start < during <
                release < after < concurrent_finish < obs_finish,
                "integrated-frame-order")
        fields = strict_fields(obs_frame)
        exact = {
            "frequency_observer_count": "1",
            "frequency_observer_mode": "444",
            "frequency_log_count_before": "0",
            "thermal_zone_count": "1",
            "thermal_zone_type": "soc-thermal",
            "writer8_alive_before_observation": "1",
            "writer9_alive_before_observation": "1",
            "writer8_alive_after_observation": "1",
            "writer9_alive_after_observation": "1",
            "writer_start_released": "1",
            "frequency_log_count": "3",
        }
        for key, expected in exact.items():
            require(fields.get(key) == expected, f"field:{key}")
        observations = [
            observation(fields[f"frequency_{label}"], attempt)
            for attempt, label in enumerate(("before", "during", "after"), 1)
        ]
        for key in ("clock_generation", "big_generation"):
            values = [int(item[key]) for item in observations]
            require(values[0] < values[1] < values[2],
                    f"observation-generation-order:{key}")
        temperatures: list[int] = []
        for label in ("before", "during", "after"):
            value = fields.get(f"thermal_{label}_millicelsius", "")
            require(bool(re.fullmatch(r"-?[0-9]+", value)),
                    f"temperature-shape:{label}")
            temperature = int(value)
            require(0 <= temperature <= 120_000,
                    f"temperature-range:{label}")
            temperatures.append(temperature)
        require(max(temperatures) - min(temperatures) <= 60_000,
                "temperature-spread")

        logs = re.findall(
            r"GEMINI_A72_FREQUENCY_OBSERVATION_V1 (abi=[^\n]+)", text
        )
        require(len(logs) == 3, "frequency-log-record-count")
        require(logs == [str(item["raw"]) for item in observations],
                "frequency-log-record-mismatch")
        with tempfile.TemporaryDirectory(
                prefix="a72-frequency-runtime-classifier-") as name:
            root = Path(name)
            classify_lifecycle(text, args.boot_id, root)
            deltas = classify_concurrent(text, args.boot_id, root)
    except (OSError, Rejected, UnicodeError) as error:
        print("runtime_classification=rejected")
        print(f"runtime_reason={error}")
        print("frequency_observer_attempts=unknown")
        print("cpu_off_request_maximum=1")
        print("retries=0")
        print("native_reboot_requested=no")
        return 3

    print("runtime_classification=stage18-thermal-frequency-bounded-load-pass")
    print(f"boot_id={args.boot_id}")
    print("cpu_online=0-9")
    print("cpu_map=0-3,4-7,8-9")
    print("binder_completed=1")
    print("restore_stage=18")
    print("frequency_observer_attempts=3-of-3")
    print("frequency_log_records=3-of-3")
    for label, sample, temperature in zip(
            ("before", "during", "after"), observations, temperatures):
        print(f"{label}_b_khz={sample['b_khz']}")
        print(f"{label}_ll_khz={sample['ll_khz']}")
        print(f"{label}_l_khz={sample['l_khz']}")
        print(f"{label}_cci_khz={sample['cci_khz']}")
        print(f"{label}_temperature_millicelsius={temperature}")
    print(f"cpu8_accounting_delta={deltas[8]}")
    print(f"cpu9_accounting_delta={deltas[9]}")
    print("concurrent_rounds=4")
    print("writer_checksums=8-of-8")
    print("peer_reader_checksums=8-of-8")
    print("worker_liveness_during_observation=both-before-and-after")
    print("device_storage_writes=none")
    print("cpu_off_requests=1")
    print("trigger_attempts=1")
    print("retries=0")
    print("native_reboot_requested=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
