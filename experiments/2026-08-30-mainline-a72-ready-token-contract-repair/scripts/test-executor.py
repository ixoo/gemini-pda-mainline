#!/usr/bin/env python3
"""Audit the host executor's exact-once and source-integrity invariants."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess


SCRIPT_DIR = Path(__file__).resolve().parent
EXECUTOR = SCRIPT_DIR / "execute-trigger.sh"
text = EXECUTOR.read_text(encoding="utf-8")

sources = {
    "TRIGGER_WRAPPER_SHA256": SCRIPT_DIR / "remote-trigger.sh",
    "CLASSIFIER_SHA256": SCRIPT_DIR / "classify-attempt.py",
    "VALIDATOR_SHA256": SCRIPT_DIR / "validate-pretrigger.py",
}
for variable, path in sources.items():
    match = re.search(rf"^readonly {variable}=([0-9a-f]{{64}})$", text, re.MULTILINE)
    assert match is not None, variable
    assert match.group(1) == hashlib.sha256(path.read_bytes()).hexdigest(), path

assert text.count('nc -4 -b "$interface" -s "$HOST_ADDRESS"') == 1
assert text.count('phase=executing-trigger-once') == 1
assert text.count('trigger_nc_sessions=1') == 1
assert text.count('trigger_retry=forbidden') == 1
assert 'trigger_retried=no' in text
assert 'cpu9_requests=0' in text
assert 'cpu_off_requests=0' in text
assert 'reboot_requested=no' in text
assert 'sudo ' not in text
assert 'ifconfig "$interface" alias' not in text

trigger_section = text.split("phase=executing-trigger-once", 1)[1].split(
    'if [[ "$attempt_result" == trigger-boundary-transport-loss ]]', 1
)[0]
assert not re.search(r"^(?:for|while)\b", trigger_section, re.MULTILINE)

help_result = subprocess.run(
    [str(EXECUTOR), "--help"], text=True, capture_output=True, check=False
)
assert help_result.returncode == 0
assert "opens exactly one boot-bound CPU8 trigger session" not in help_result.stdout
assert "exactly one netcat session" in help_result.stdout

missing = subprocess.run([str(EXECUTOR)], text=True, capture_output=True, check=False)
assert missing.returncode == 2
malformed = subprocess.run(
    [
        str(EXECUTOR),
        "--pretrigger-dir",
        "artifacts/runtime-captures/a72-ready-token-contract-repair-pretrigger-attempt-1",
        "--deployment-boot-id",
        "malformed",
    ],
    text=True,
    capture_output=True,
    check=False,
)
assert malformed.returncode == 2

print("trigger_netcat_call_sites=1")
print("trigger_retry_loops=0")
print("executor_source_pins=3")
print("address_configuration_paths=0")
print("result=pass")
