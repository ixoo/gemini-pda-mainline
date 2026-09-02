#!/usr/bin/env python3
"""Classify one same-session dual-A72 trigger and topology/RAM attempt."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys


PARENT_SHA256 = "c41d58cf60e0f5c769f195b28933b1349963f3523e86248fa197b59b718f58b1"
PROBE_SHA256 = "2cd81b4ee24e5575fd22ec8330f351678c3b6f46a054c6fe0b481d4d192f7319"
PASS = "mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass"
SCRIPT = Path(__file__).resolve()
PARENT = SCRIPT.with_name("classify-parent-trigger.py")
PROBE = SCRIPT.with_name("classify-attempt.py")


def fields(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in result:
            raise ValueError(f"duplicate classifier field: {key}")
        result[key] = value
    return result


def reject(reason: str) -> int:
    print("runtime_classification=rejected")
    print(f"runtime_reason={reason}")
    print("trigger_attempts=unknown")
    print("probe_sessions=1")
    print("cpu8_request_maximum=1")
    print("cpu9_request_maximum=1")
    print("cpu_off_requests=0")
    print("retries=0")
    print("native_reboot_requested=no")
    return 3


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrigger", required=True, type=Path)
    parser.add_argument("--trigger", required=True, type=Path)
    args = parser.parse_args()
    if hashlib.sha256(PARENT.read_bytes()).hexdigest() != PARENT_SHA256:
        return reject("parent-classifier-changed")
    if hashlib.sha256(PROBE.read_bytes()).hexdigest() != PROBE_SHA256:
        return reject("topology-ram-classifier-changed")

    parent = run(
        [
            sys.executable,
            str(PARENT),
            "--pretrigger",
            str(args.pretrigger),
            "--trigger",
            str(args.trigger),
        ]
    )
    if parent.returncode != 0:
        try:
            reason = fields(parent.stdout).get("runtime_reason", "unknown")
        except ValueError as error:
            reason = str(error)
        sys.stderr.write(parent.stderr)
        return reject(f"parent-trigger:{reason}")
    try:
        parent_fields = fields(parent.stdout)
    except ValueError as error:
        return reject(f"parent-trigger:{error}")
    if parent_fields.get("runtime_classification") != "cpu8-cpu9-online-accounting-advanced":
        return reject("parent-trigger:classification-changed")

    # The parent classifier deliberately does not repeat the boot ID in its
    # output, so recover the one exact pre-trigger ID without weakening either
    # underlying classifier.
    boot_ids = [
        line.split("=", 1)[1]
        for line in args.pretrigger.read_text(encoding="utf-8").splitlines()
        if line.startswith("boot_id=")
    ]
    if len(boot_ids) != 1:
        return reject("pretrigger-boot-id-count-changed")
    probe = run(
        [
            sys.executable,
            str(PROBE),
            "--capture",
            str(args.trigger),
            "--boot-id",
            boot_ids[0],
        ]
    )
    if probe.returncode != 0:
        sys.stderr.write(probe.stderr)
        return reject("topology-ram:strict-classifier-rejected")
    try:
        probe_fields = fields(probe.stdout)
    except ValueError as error:
        return reject(f"topology-ram:{error}")
    if probe_fields.get("runtime_classification") != PASS:
        return reject("topology-ram:classification-changed")

    sys.stdout.write(probe.stdout)
    print("parent_runtime_classification=cpu8-cpu9-online-accounting-advanced")
    print("trigger_attempts=1")
    print("probe_sessions=1")
    print("native_reboot_requested=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
