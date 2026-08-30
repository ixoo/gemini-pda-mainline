#!/usr/bin/env python3
"""Audit the repaired read-only probe composition and bounded transport."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess


SCRIPT_DIR = Path(__file__).resolve().parent
COLLECTOR = SCRIPT_DIR / "collect-pretrigger.sh"
WRAPPER = SCRIPT_DIR / "remote-pretrigger.sh"
VALIDATOR = SCRIPT_DIR / "validate-pretrigger.py"

collector = COLLECTOR.read_text(encoding="utf-8")
wrapper = WRAPPER.read_text(encoding="utf-8")
probe = subprocess.run(
    [str(WRAPPER)], text=True, capture_output=True, check=True
).stdout

for variable, expected in {
    "WRAPPER_SHA256": hashlib.sha256(WRAPPER.read_bytes()).hexdigest(),
    "PROBE_SHA256": hashlib.sha256(probe.encode()).hexdigest(),
    "VALIDATOR_SHA256": hashlib.sha256(VALIDATOR.read_bytes()).hexdigest(),
}.items():
    match = re.search(rf"^readonly {variable}=([0-9a-f]{{64}})$", collector, re.MULTILINE)
    assert match is not None, variable
    assert match.group(1) == expected, (variable, match.group(1), expected)

assert probe.startswith("#!/bin/sh\n")
assert probe.count("__GEMINI_A72_LIVE_PRETRIGGER_BEGIN__") == 1
assert probe.count("__GEMINI_A72_LIVE_PRETRIGGER_END__") == 1
assert probe.count("installed_full_sha256=a7ce2c2d58bccce6c1f41814d0ae584b") == 1
for field in (
    "provenance_node=", "runtime_identity_verified_count=",
    "ready_plan_diag_count=", "ready_plan_values_count=",
    "proof_mask_24000_count=", "live_status=",
):
    assert probe.count(field) == 1, field

assert collector.count('nc -4 -b "$interface" -s "$HOST_ADDRESS"') == 1
assert "transport=bounded-heredoc" in collector
assert "/bin/busybox sh <<'%s'" in collector
assert "base64" not in collector
assert "run-a72-admission-20260828-a" not in collector
assert 'remote-trigger.sh' not in collector
assert '>"$TRIGGER"' not in probe
assert "device_partition_reads" in probe
assert "device_storage_writes" in probe

missing = subprocess.run([str(COLLECTOR)], text=True, capture_output=True, check=False)
assert missing.returncode == 2

print("materialized_device_probe=yes")
print("required_ready_fields=6")
print("pretrigger_netcat_call_sites=1")
print("pretrigger_trigger_paths=0")
print("result=pass")
