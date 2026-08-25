#!/usr/bin/env python3
"""Classify the exact platform/provider/protected-clock live capture."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
from pathlib import Path
import re


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_PATH = REPO_ROOT / "experiments/2026-08-25-mainline-a72-platform-provider-deferred-bind-repair/scripts/validate-runtime.py"
SOURCE_SHA256 = "8b88d26718faf70e98960e784d781e66041c37bbe45cd177bd4648fb5677db91"
CANDIDATE = "1f7bd9600e11846af352abbec660db816c378094664f81d861b9fbd1f1f16aa2"
RELEASE = "7.1.3-gemini-a72-clock-third"
TAG = "GEMINI_A72_PLATFORM_PROVIDER_CLOCK_SNAPSHOT_V1"
PLATFORM = re.compile(
    rf"{TAG} platform valid=1 spm=(?:[0-9a-f]{{8}}/){{3}}[0-9a-f]{{8}} "
    r"mp2=(?:[0-9a-f]{8}/){2}[0-9a-f]{8} iso=[0-9a-f]{8} "
    r"dcm=[0-9a-f]{8} cci=(?:[0-9a-f]{8}/){2}[0-9a-f]{8} pwrap=[01]"
)
PROVIDER = re.compile(
    rf"{TAG} provider abi=1 valid=1 raw=(?:[0-9a-f]{{2}}/){{4}}[0-9a-f]{{2}}"
)
CLOCK = re.compile(
    rf"{TAG} clock ret=(-?[0-9]+) abi=([0-9]+) generation=([0-9]+) "
    r"muxsel=[0-9a-f]{8} ckdiv=[0-9a-f]{8} "
    r"pll_ll=(?:[0-9a-f]{8}/){2}[0-9a-f]{8} "
    r"pll_l=(?:[0-9a-f]{8}/){2}[0-9a-f]{8} "
    r"pll_cci=(?:[0-9a-f]{8}/){2}[0-9a-f]{8} "
    r"cspm_swctrl=(?:[0-9a-f]{8}/){2}[0-9a-f]{8} "
    r"cspm_hwsta=(?:[0-9a-f]{8}/){3}[0-9a-f]{8}"
)
COMPLETE = re.compile(
    rf"{TAG} state=complete provider_ready_gate=passed clock_ready_gate=passed "
    r"valid=([01]) clock_returned=([01]) after_checkpoint=([01]) "
    r"platform_calls=1 platform_samples=2 platform_register_observations=26 "
    r"provider_snapshots=1 provider_samples=2 provider_i2c_reads=10 "
    r"provider_i2c_writes=0 retained_write_attempts=2 protected_clock_calls=1 "
    r"protected_clock_ret=(-?[0-9]+) protected_clock_abi=([0-9]+) "
    r"protected_clock_generation=([0-9]+) clock_gate_pairs=1 "
    r"explicit_mmio_writes_maximum=401 explicit_mmio_reads_maximum=419 "
    r"observer_retries=0 bigidvfs_reads=0 secure_calls=0 provider_acquires=0 "
    r"provider_releases=0 publisher_calls=0 owner_mutations=0 cpu_requests=0"
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(SOURCE_PATH) != SOURCE_SHA256:
    raise SystemExit("source runtime validator changed")
SPEC = importlib.util.spec_from_file_location("provider_ready_runtime_source", SOURCE_PATH)
assert SPEC is not None and SPEC.loader is not None
SOURCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SOURCE)
BASE = SOURCE.BASE
BASE.CANDIDATE = CANDIDATE
BASE.RELEASE = RELEASE


def scalar_values(text: str) -> dict[str, str]:
    start = text.index(BASE.BEGIN) + len(BASE.BEGIN)
    finish = text.index(BASE.END, start)
    section = text[start:finish].replace("\r", "")
    marker_start = section.index(BASE.MARKERS_BEGIN)
    marker_finish = section.index(BASE.MARKERS_END) + len(BASE.MARKERS_END)
    section = section[:marker_start] + section[marker_finish:]
    values: dict[str, str] = {}
    for raw in section.splitlines():
        line = raw.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in values:
            raise BASE.Classification("rejected-platform-provider-clock", "duplicate-scalar")
        values[key] = value
    return values


def classify(text: str) -> tuple[str, str, str, dict[str, int], str, tuple[int, int, int, int, int, int]]:
    clock_action = (
        "clock_action_request="
        "one-balanced-gate-pair-and-bounded-cspm-snapshot"
    )
    if text.count(clock_action) != 1:
        raise BASE.Classification(
            "rejected-platform-provider-clock", "clock-action-request-mismatch"
        )
    inherited_text = text.replace(clock_action, "clock_action_request=none", 1)
    result, _, ledger, counts = BASE.classify_text(inherited_text)
    if result != "serviceable-stage27-control-pass":
        raise AssertionError("base serviceability classification changed")
    values = scalar_values(text)
    expected = {
        "platform_state_devices": "1",
        "platform_state_bound": "1",
        "clock_backend_devices": "1",
        "clock_backend_bound": "1",
        "bigidvfs_backend_devices": "1",
        "bigidvfs_backend_bound": "1",
        "composed_observer_devices": "1",
        "composed_observer_bound": "1",
        "provider_only_observer_devices": "0",
        "platform_only_observer_devices": "0",
        "physical_observer_devices": "0",
        "provider_i2c_devices": "1",
        "provider_i2c_bound": "1",
        "usb_controller_status": "okay",
        "tphy_status": "okay",
        "i2c5_status": "okay",
        "keyboard_status": "okay",
        "snapshot_log_lines": "4",
        "snapshot_failure_lines": "0",
        "platform_snapshot_request": "boot-observer-one-shot",
        "platform_snapshot_calls_expected": "1",
        "platform_samples_expected": "2",
        "platform_register_observations_expected": "26",
        "provider_readiness_request": "explicit-phandle-bound-device",
        "provider_snapshot_request": "one-stable-read-only",
        "provider_snapshots_expected": "1",
        "provider_samples_expected": "2",
        "provider_i2c_reads_expected": "10",
        "provider_i2c_writes_expected": "0",
        "clock_backend_read_request": "one-handoff-owned-snapshot",
        "protected_clock_calls_expected": "1",
        "protected_clock_abi_expected": "2",
        "protected_clock_generation_expected": "1",
        "clock_gate_pairs_expected": "1",
        "explicit_mmio_writes_maximum": "401",
        "explicit_mmio_reads_maximum": "419",
        "bigidvfs_backend_read_request": "none",
        "clock_action_request": "one-balanced-gate-pair-and-bounded-cspm-snapshot",
        "secure_call_request": "none",
        "provider_acquire_release_request": "none",
        "observer_registration_request": "dt-probe-only",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    for key, value in expected.items():
        if values.get(key) != value:
            raise BASE.Classification("rejected-platform-provider-clock", f"{key}-mismatch")
    try:
        raw_log = base64.b64decode(values.get("snapshot_log_b64", ""), validate=True)
        log = raw_log.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise BASE.Classification("rejected-platform-provider-clock", "snapshot-log-malformed") from error
    tagged = [line[line.index(TAG):].strip() for line in log.splitlines() if TAG in line]
    if len(tagged) != 4 or not PLATFORM.fullmatch(tagged[0]) or not PROVIDER.fullmatch(tagged[1]):
        raise BASE.Classification("rejected-platform-provider-clock", "prefix-log-contract-mismatch")
    clock = CLOCK.fullmatch(tagged[2])
    complete = COMPLETE.fullmatch(tagged[3])
    if not clock or not complete:
        raise BASE.Classification("rejected-platform-provider-clock", "clock-log-contract-mismatch")
    clock_ret, clock_abi, clock_generation = map(int, clock.groups())
    valid, returned, after, terminal_ret, terminal_abi, terminal_generation = map(
        int, complete.groups()
    )
    if (clock_ret, clock_abi, clock_generation) != (
        terminal_ret, terminal_abi, terminal_generation
    ) or returned != 1:
        raise BASE.Classification("rejected-platform-provider-clock", "terminal-log-disagreement")
    if (valid, after, clock_ret, clock_abi, clock_generation) == (1, 1, 0, 2, 1):
        classification = "serviceable-platform-provider-clock-complete"
        reason = "exact-live-three-reader-success"
    elif after == 0 and valid == 0:
        classification = "serviceable-platform-provider-clock-after-checkpoint-failed"
        reason = "clock-returned-but-after-checkpoint-refused"
    elif clock_ret != 0 and after == 1 and valid == 0:
        classification = "serviceable-platform-provider-clock-terminal-error"
        reason = "clock-call-returned-error-with-no-retry"
    elif after == 1 and valid == 0:
        classification = "serviceable-platform-provider-clock-invalid-identity"
        reason = "clock-returned-with-nonqualifying-abi-or-generation"
    else:
        raise BASE.Classification("rejected-platform-provider-clock", "terminal-state-invalid")
    state = (valid, returned, after, clock_ret, clock_abi, clock_generation)
    return classification, reason, ledger, counts, hashlib.sha256(raw_log).hexdigest(), state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        result, reason, ledger, counts, log_sha256, state = classify(
            args.capture.read_text(encoding="utf-8", errors="replace")
        )
    except BASE.Classification as error:
        result, reason, ledger, counts, log_sha256, state = (
            error.result, error.reason, "not-classified", {}, "not-classified",
            (0, 0, 0, 0, 0, 0),
        )
    accepted = result.startswith("serviceable-platform-provider-clock-")
    valid, returned, after, clock_ret, clock_abi, clock_generation = state
    print("runtime_gate=serviceable-platform-provider-clock-decision" if accepted else "runtime_gate=rejected")
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"snapshot_log_sha256={log_sha256}")
    print(f"live_ledger_classification={ledger}")
    print(f"pure_marker_matches={counts.get('pure', 0)}")
    print(f"core_marker_matches={counts.get('core', 0)}")
    print(f"refusal_marker_matches={counts.get('refusal', 0)}")
    print("provider_ready_gate=passed" if accepted else "provider_ready_gate=unknown")
    print("clock_ready_gate=passed" if accepted else "clock_ready_gate=unknown")
    print(f"snapshot_valid={valid}")
    print(f"clock_returned={returned}")
    print(f"after_checkpoint={after}")
    print("platform_snapshot_calls=1" if accepted else "platform_snapshot_calls=unknown")
    print("platform_samples=2" if accepted else "platform_samples=unknown")
    print("platform_register_observations=26" if accepted else "platform_register_observations=unknown")
    print("provider_snapshots=1" if accepted else "provider_snapshots=unknown")
    print("provider_samples=2" if accepted else "provider_samples=unknown")
    print("provider_i2c_reads=10" if accepted else "provider_i2c_reads=unknown")
    print("provider_i2c_writes=0")
    print("protected_clock_calls=1" if accepted else "protected_clock_calls=unknown")
    print(f"protected_clock_ret={clock_ret}")
    print(f"protected_clock_abi={clock_abi}")
    print(f"protected_clock_generation={clock_generation}")
    print("clock_gate_pairs=1" if accepted else "clock_gate_pairs=unknown")
    print("explicit_mmio_writes_maximum=401")
    print("explicit_mmio_reads_maximum=419")
    print("bigidvfs_reads=0")
    print("secure_calls=0")
    print("provider_acquires=0")
    print("provider_releases=0")
    print("publisher_calls=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
