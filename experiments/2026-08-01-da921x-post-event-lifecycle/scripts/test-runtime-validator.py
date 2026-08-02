#!/usr/bin/env python3
"""Fail-closed tests for the Stage 27 lifecycle classifier."""

from __future__ import annotations

import importlib.util
import subprocess
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).with_name("validate-runtime.py")
SPEC = importlib.util.spec_from_file_location("validate_runtime", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load runtime validator")
validate_runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validate_runtime)


def passing() -> dict[str, str]:
    values = dict(validate_runtime.EXPECTED)
    for phase, (combined, primary, page2) in validate_runtime.PHASE_COUNTS.items():
        for key in (
            "transfer_attempts",
            "nonzero_starts",
            "irq_count",
            "oracle_combined_pointer_reads",
        ):
            values[f"{phase}_{key}"] = str(combined)
        values[f"{phase}_dma_starts"] = "0"
        values[f"{phase}_oracle_primary_pointer_reads"] = str(primary)
        values[f"{phase}_oracle_page2_pointer_reads"] = str(page2)
        for key in validate_runtime.ZERO_COUNTERS:
            values[f"{phase}_{key}"] = "0"
    return values


def run(values: dict[str, str]) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temporary:
        record = Path(temporary) / "runtime.txt"
        record.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
        return subprocess.run(
            [str(SCRIPT), str(record)], check=False, capture_output=True, text=True
        )


valid = run(passing())
if valid.returncode != 0:
    raise SystemExit(f"passing lifecycle record rejected: {valid.stderr}")

mutations = {
    "unbind-transaction": ("post_unbind_transfer_attempts", "15"),
    "rebind-short": ("post_rebind_oracle_combined_pointer_reads", "27"),
    "register-write": ("post_rebind_oracle_register_data_write_messages", "1"),
    "dma-start": ("post_rebind_dma_starts", "1"),
    "sysfs-left-rw": ("sysfs", "read-write"),
    "a72-online": ("cpu_offline", "9"),
}
for name, (key, value) in mutations.items():
    candidate = passing()
    candidate[key] = value
    result = run(candidate)
    if result.returncode == 0:
        raise SystemExit(f"unsafe mutation passed: {name}")

print("validation=da921x-post-event-lifecycle-runtime-mutations")
print(f"mutations_rejected={len(mutations)}")
