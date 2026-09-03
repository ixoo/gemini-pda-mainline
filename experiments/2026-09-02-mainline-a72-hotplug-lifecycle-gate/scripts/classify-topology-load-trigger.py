#!/usr/bin/env python3
"""Classify one integrated stage-18 topology and bounded RAM transaction."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile


LIFECYCLE_SHA256 = "d1b618adce29b853c02ee19d47fa41be1fc5ac32411c34c34552ceadebe4b81f"
PROBE_SHA256 = "2cd81b4ee24e5575fd22ec8330f351678c3b6f46a054c6fe0b481d4d192f7319"
LIFECYCLE_PASS = "stage18-repeat-and-mt6797-4+4+2-topology-pass"
PROBE_PASS = "mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass"
CURRENT_RELEASE = "7.1.3-gemini-a72-hotplug-physical"
PROBE_SOURCE_RELEASE = "7.1.3-gemini-cpu9-progress"
RAM_BEGIN = "__GEMINI_A72_RAM_COHERENCY_BEGIN__"
RAM_END = "__GEMINI_A72_RAM_COHERENCY_END__"
GATE_PASS = "__A72_TOPOLOGY_LOAD_GATE_PASSED__"
SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
LIFECYCLE = SCRIPT.with_name("classify-topology-repeat-trigger.py")
PROBE = ROOT / "experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/classify-attempt.py"


def reject(reason: str) -> int:
    print("runtime_classification=rejected")
    print(f"runtime_reason={reason}")
    print("trigger_attempts=unknown")
    print("load_probe_sessions=1")
    print("cpu_off_request_maximum=1")
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


def fields(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key):
            continue
        if key in parsed:
            raise ValueError(f"duplicate field: {key}")
        parsed[key] = value
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--boot-id", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", args.boot_id):
        return reject("expected-boot-id")
    if hashlib.sha256(LIFECYCLE.read_bytes()).hexdigest() != LIFECYCLE_SHA256:
        return reject("lifecycle-classifier-changed")
    if hashlib.sha256(PROBE.read_bytes()).hexdigest() != PROBE_SHA256:
        return reject("topology-RAM-classifier-changed")

    text = args.capture.read_text(encoding="utf-8", errors="replace").replace("\r", "")
    if text.count(RAM_BEGIN) != 1 or text.count(RAM_END) != 1:
        return reject("RAM-frame-boundary")
    if text.count(GATE_PASS) != 1:
        return reject("lifecycle-device-gate")
    lifecycle_end = text.find("__A72_TOPOLOGY_REPEAT_TRIGGER_END__")
    gate = text.find(GATE_PASS)
    ram_begin = text.find(RAM_BEGIN)
    if not (0 <= lifecycle_end < gate < ram_begin):
        return reject("integrated-frame-order")

    lifecycle = run(
        [sys.executable, str(LIFECYCLE), str(args.capture), "--boot-id", args.boot_id]
    )
    if lifecycle.returncode != 0:
        try:
            reason = fields(lifecycle.stdout).get("runtime_reason", "unknown")
        except ValueError as error:
            reason = str(error)
        return reject(f"lifecycle:{reason}")
    try:
        lifecycle_fields = fields(lifecycle.stdout)
    except ValueError as error:
        return reject(f"lifecycle:{error}")
    if lifecycle_fields.get("runtime_classification") != LIFECYCLE_PASS:
        return reject("lifecycle:classification-changed")

    ram_start = text.index(RAM_BEGIN) + len(RAM_BEGIN)
    ram_finish = text.index(RAM_END, ram_start)
    ram = text[ram_start:ram_finish]
    current = f"kernel_release={CURRENT_RELEASE}\n"
    if ram.count(current) != 1 or f"boot_id={args.boot_id}\n" not in ram:
        return reject("RAM-runtime-identity")
    retargeted = ram.replace(
        current,
        f"kernel_release={PROBE_SOURCE_RELEASE}\n",
        1,
    )
    with tempfile.TemporaryDirectory(prefix="a72-topology-load-classifier-") as name:
        capture = Path(name) / "retargeted-probe.txt"
        capture.write_text(f"{RAM_BEGIN}{retargeted}{RAM_END}\n", encoding="utf-8")
        probe = run(
            [
                sys.executable,
                str(PROBE),
                "--capture",
                str(capture),
                "--boot-id",
                args.boot_id,
            ]
        )
    if probe.returncode != 0:
        return reject("topology-RAM:strict-classifier-rejected")
    try:
        probe_fields = fields(probe.stdout)
    except ValueError as error:
        return reject(f"topology-RAM:{error}")
    if probe_fields.get("runtime_classification") != PROBE_PASS:
        return reject("topology-RAM:classification-changed")

    print("runtime_classification=stage18-topology-and-bounded-dual-a72-RAM-pass")
    print(f"boot_id={args.boot_id}")
    print("cpu_online=0-9")
    print("binder_ret=0")
    print("binder_completed=1")
    print("restore_stage=18")
    print("cpu_map=0-3,4-7,8-9")
    print("load_probe=bounded-bidirectional-volatile-RAM")
    print(f"cpu8_accounting_delta={probe_fields['cpu8_accounting_delta']}")
    print(f"cpu9_accounting_delta={probe_fields['cpu9_accounting_delta']}")
    print(f"payload_sha256={probe_fields['payload_sha256']}")
    print("bidirectional_cross_cpu_checksums=4-of-4")
    print("device_storage_writes=none")
    print("cpu_off_requests=1")
    print("trigger_attempts=1")
    print("load_probe_sessions=1")
    print("retries=0")
    print("native_reboot_requested=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
