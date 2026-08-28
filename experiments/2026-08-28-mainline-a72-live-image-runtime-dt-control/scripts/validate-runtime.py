#!/usr/bin/env python3
"""Classify one exact current-Image/runtime-DT control frame."""

from __future__ import annotations
import argparse
from pathlib import Path
import re

BEGIN = "__A72_RUNTIME_DT_CONTROL_BEGIN__"
END = "__A72_RUNTIME_DT_CONTROL_END__"
EXPECTED = {
    "installed_full_sha256": "c2b85cad08f77d641a07e68eda09617959ad1db6b36b60b20eb8f53733c6baab",
    "kernel_release": "7.1.3-gemini-a72-admission-live", "architecture": "aarch64",
    "model": "MT6797X", "compatible": "planet,gemini-pda,mediatek,mt6797,",
    "cpu_possible": "0-9", "cpu_present": "0-9", "cpu_online": "0-7", "cpu_offline": "8-9",
    "maxcpus8_tokens": "1", "udc_devices": "1", "block_mounts": "0",
    "controller_nodes": "0", "binder_nodes": "0", "platform_state_nodes": "1", "composed_observer_nodes": "1",
    "device_partition_reads": "none", "device_storage_writes": "none", "retained_ram_writes": "none",
    "regulator_action_request": "none", "clock_action_request": "none", "secure_call_request": "none",
    "owner_mutation_request": "none", "cpu_admission_request": "none", "reboot_request": "none",
}
NODE_AUDIT_BEGIN = "__A72_NODE_AUDIT_BEGIN__"
NODE_AUDIT_END = "__A72_NODE_AUDIT_END__"
PLATFORM_PATH = "platform_state=/sys/firmware/devicetree/base/a72-platform-state@10222000/compatible"
OBSERVER_PATH = "composed_observer=/sys/firmware/devicetree/base/a72-platform-provider-clock-observer/compatible"


def validate_node_audit(text: str) -> bool:
    if text.count(NODE_AUDIT_BEGIN) != 1 or text.count(NODE_AUDIT_END) != 1:
        return False
    section = text[text.index(NODE_AUDIT_BEGIN) + len(NODE_AUDIT_BEGIN):text.index(NODE_AUDIT_END)]
    lines = [line.strip() for line in section.replace("\r", "").splitlines() if line.strip()]
    return lines == [PLATFORM_PATH, OBSERVER_PATH]

def classify(text: str, node_audit: str | None = None) -> tuple[str, str]:
    if text.count(BEGIN) != 1 or text.count(END) != 1: return "rejected-attribution", "non-unique-frame"
    section = text[text.index(BEGIN) + len(BEGIN):text.index(END)].replace("\r", "")
    values: dict[str, str] = {}
    for raw in section.splitlines():
        line = raw.strip()
        if not line or "=" not in line: continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in values: return "rejected-attribution", "malformed-or-duplicate-key"
        values[key] = value
    audit_required = values.get("platform_state_nodes") == "0" and values.get("composed_observer_nodes") == "0"
    for key, value in EXPECTED.items():
        if audit_required and key in {"platform_state_nodes", "composed_observer_nodes"}: continue
        if values.get(key) != value: return "rejected-control", f"{key}-mismatch"
    if audit_required and (node_audit is None or not validate_node_audit(node_audit)):
        return "rejected-control", "shallow-node-counters-without-exact-recursive-audit"
    if set(values) != set(EXPECTED) | {"boot_id", "uptime_seconds"}: return "rejected-attribution", "unexpected-key-set"
    if not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", values["boot_id"]): return "rejected-attribution", "malformed-boot-id"
    if not re.fullmatch(r"\d+(?:\.\d+)?", values["uptime_seconds"]): return "rejected-attribution", "malformed-uptime"
    return "serviceable-current-image-runtime-dt-control", "exact-current-image-reached-usb-with-runtime-proven-dt"

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("capture", type=Path); parser.add_argument("--node-audit", type=Path); args = parser.parse_args()
    audit = args.node_audit.read_text(encoding="utf-8", errors="replace") if args.node_audit else None
    result, reason = classify(args.capture.read_text(encoding="utf-8", errors="replace"), audit)
    print(f"runtime_classification={result}"); print(f"runtime_reason={reason}")
    print("cpu8_cpu9_admission=closed"); print("native_reboot_requested=no")
    return 0 if result == "serviceable-current-image-runtime-dt-control" else 3

if __name__ == "__main__": raise SystemExit(main())
