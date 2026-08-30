#!/usr/bin/env python3
"""Exercise the READY candidate's trace-aware pre-trigger classification."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "ready_pretrigger_test", SCRIPT_DIR / "validate-pretrigger.py"
)
assert spec is not None and spec.loader is not None
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def frame() -> str:
    return "\n".join((
        validator.BEGIN,
        f"installed_full_sha256={validator.CANDIDATE}",
        f"kernel_release={validator.RELEASE}",
        "architecture=aarch64",
        "boot_id=12345678-1234-1234-1234-123456789abc",
        "uptime_seconds=157.33",
        "model=MT6797X",
        "compatible=planet,gemini-pda,mediatek,mt6797,",
        "cpu_possible=0-9",
        "cpu_present=0-9",
        "cpu_online=0-7",
        "cpu_offline=8-9",
        "maxcpus8_tokens=1",
        "udc_devices=1",
        "block_mounts=0",
        "controller_devices=1",
        "controller_bound=1",
        "group_present=1",
        "status_mode=444",
        "status_uid=0",
        "trigger_mode=200",
        "trigger_uid=0",
        "sysfs_options=ro,nosuid,nodev,noexec,relatime",
        f"live_status={validator.ARMED}",
        "device_partition_reads=none",
        "device_storage_writes=none",
        "sysfs_write_request=none",
        "supplier_resolution_request=none",
        "cpu_admission_request=none",
        "cpu_off_request=none",
        "retry_request=none",
        "reboot_request=none",
        validator.END,
    ))


classification, boot_id = validator.classify(frame())
assert classification == "serviceable-armed-zero-execution"
assert boot_id == "12345678-1234-1234-1234-123456789abc"

mutations = (
    ("cpu_online=0-7", "cpu_online=0-8"),
    ("cpu_offline=8-9", "cpu_offline=9"),
    ("controller_bound=1", "controller_bound=0"),
    ("trigger_mode=200", "trigger_mode=644"),
    ("entry_trace_ret=0", "entry_trace_ret=-5"),
    ("terminal_trace_ret=0", "terminal_trace_ret=-5"),
    ("sysfs_options=ro,", "sysfs_options=rw,"),
    ("cpu_admission_request=none", "cpu_admission_request=cpu8"),
)
for old, new in mutations:
    try:
        validator.classify(frame().replace(old, new, 1))
    except validator.Classification:
        pass
    else:
        raise AssertionError(f"unsafe pre-trigger mutation accepted: {old}")

old_schema = frame().replace(
    " entry_trace_ret=0 terminal_trace_ret=0", "", 1
)
try:
    validator.classify(old_schema)
except validator.Classification:
    pass
else:
    raise AssertionError("trace-field omission was accepted")

print("pretrigger_accepted_branches=1")
print("pretrigger_mutations_rejected=9")
print("result=pass")
