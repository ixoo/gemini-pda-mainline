#!/usr/bin/env python3
"""Test the exact attempt-1 pre-clock failure classifier."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SOURCE_TEST = SCRIPT_DIR / "test-runtime.py"
SOURCE_TEST_SHA256 = "b29b6ec9d7dbd5859e529cf37a2cbcdd3cb005ebd055c9a10cf35d8138e6ecdd"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if hashlib.sha256(SOURCE_TEST.read_bytes()).hexdigest() != SOURCE_TEST_SHA256:
    raise SystemExit("preboot runtime fixture changed")
with contextlib.redirect_stdout(io.StringIO()):
    FIXTURE = load("third_reader_preboot_fixture", SOURCE_TEST)
MODULE = load("third_reader_attempt_1_runtime", SCRIPT_DIR / "validate-runtime-attempt-1.py")
BASE = MODULE.BASE


def capture() -> str:
    text = FIXTURE.capture()
    replacements = (
        ("boot_id=12345678-1234-1234-1234-123456789abc", f"boot_id={MODULE.BOOT_ID}"),
        ("composed_observer_bound=1", "composed_observer_bound=0"),
        (f"snapshot_log_b64={FIXTURE.encoded_log()}", "snapshot_log_b64=Cg=="),
        ("snapshot_log_lines=4", "snapshot_log_lines=0"),
        ("snapshot_failure_lines=0", "snapshot_failure_lines=1"),
    )
    for old, new in replacements:
        if text.count(old) != 1:
            raise AssertionError(f"fixture anchor changed: {old}")
        text = text.replace(old, new, 1)
    return text


def error_evidence() -> str:
    return "\n".join((
        "validation=a72-platform-provider-clock-runtime-attempt-1-dmesg",
        f"candidate_sha256={MODULE.CANDIDATE}", f"kernel_release={MODULE.RELEASE}",
        f"boot_id={MODULE.BOOT_ID}",
        "collection=bounded-read-only-usb-netcat-dmesg-filter", "dmesg_excerpt_begin",
        "[   46.168257] mt6797-a72-platform-provider-clock-observer a72-platform-provider-clock-observer: platform/provider/clock capture failed: -11",
        "[   46.168268] mt6797-a72-platform-provider-clock-observer a72-platform-provider-clock-observer: probe with driver mt6797-a72-platform-provider-clock-observer failed with error -11",
        "[   46.176044] probe of a72-platform-provider-clock-observer returned 11 after 7948 usecs",
        "dmesg_excerpt_end", "failure_stage=ambiguous-platform-or-provider-snapshot",
        "retained_write_attempts=0", "protected_clock_calls=0",
        "native_reboot_requested=no", "result=decision-bearing-pre-clock-failure", "",
    ))


assert MODULE.classify(capture(), error_evidence())[0] == (
    "serviceable-platform-provider-clock-pre-clock-failure"
)

capture_mutations = (
    ("installed_full_sha256=1f7bd960", "installed_full_sha256=0f7bd960"),
    ("kernel_release=7.1.3-gemini-a72-clock-third", "kernel_release=wrong"),
    ("composed_observer_bound=0", "composed_observer_bound=1"),
    ("platform_state_bound=1", "platform_state_bound=0"),
    ("provider_i2c_bound=1", "provider_i2c_bound=0"),
    ("clock_backend_bound=1", "clock_backend_bound=0"),
    ("snapshot_log_b64=Cg==", "snapshot_log_b64=AA=="),
    ("snapshot_log_lines=0", "snapshot_log_lines=1"),
    ("snapshot_failure_lines=1", "snapshot_failure_lines=0"),
    ("clock_action_request=one-balanced-gate-pair-and-bounded-cspm-snapshot", "clock_action_request=none"),
    ("cpu_admission_request=none", "cpu_admission_request=cpu8"),
    ("device_storage_writes=none", "device_storage_writes=boot2"),
)
rejected = 0
for old, new in capture_mutations:
    try:
        MODULE.classify(capture().replace(old, new, 1), error_evidence())
    except BASE.Classification:
        rejected += 1
    else:
        raise AssertionError(f"unsafe attempt-1 capture mutation accepted: {old}")

error_mutations = (
    ("capture failed: -11", "capture failed: -5"),
    ("failure_stage=ambiguous-platform-or-provider-snapshot", "failure_stage=clock"),
    ("protected_clock_calls=0", "protected_clock_calls=1"),
)
for old, new in error_mutations:
    try:
        MODULE.classify(capture(), error_evidence().replace(old, new, 1))
    except BASE.Classification:
        rejected += 1
    else:
        raise AssertionError(f"unsafe attempt-1 error mutation accepted: {old}")

print("attempt_1_accepted_branches=1")
print(f"attempt_1_rejected_mutations={rejected}")
print("result=pass")
