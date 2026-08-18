#!/usr/bin/env python3
"""Validate retained success plus a read-only live post-trigger confirmation."""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import re


EXPECTED_RELEASE = "7.1.3-gemini-da921x-preflight-rt"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_runtime_classifier(path: Path):
    spec = importlib.util.spec_from_file_location("da921x_runtime_classifier", path)
    require(spec is not None and spec.loader is not None, "runtime classifier load failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-classifier", type=Path, required=True)
    parser.add_argument("--trigger", type=Path, required=True)
    parser.add_argument("--retained-classification", type=Path, required=True)
    parser.add_argument("--confirm", type=Path, required=True)
    args = parser.parse_args()

    runtime = load_runtime_classifier(args.runtime_classifier)
    retained = args.retained_classification.read_text(encoding="ascii").splitlines()
    for exact in (
        "runtime_classification=success-runtime-preflight-ledger",
        "I2C6_pretrigger_sequence=exact-20-of-20",
        "I2C6_posttrigger_sequence=exact-30-of-30",
        "DA921x_register_data_writes=0",
        "runtime_preflight_state=passed",
        "Gate6_B3=closed-by-exact-transfer-attribution",
        "Gate6_B4=closed-by-stable-safe-preflight",
        "Gate6_B1=blocking",
        "Gate6_B2=blocking",
        "result=pass",
    ):
        require(retained.count(exact) == 1, f"retained classification changed: {exact}")

    trigger_lines = args.trigger.read_text(encoding="ascii").splitlines()
    trigger_boot = runtime.exact_field(trigger_lines, "boot_id_sha256")
    confirm = args.confirm.read_text(encoding="ascii").splitlines()
    require(confirm.count("__DA921X_RUNTIME_POSTTRIGGER_CONFIRM_BEGIN__") == 1,
            "confirmation begin changed")
    require(confirm.count("__DA921X_RUNTIME_POSTTRIGGER_CONFIRM_END__") == 1,
            "confirmation end changed")
    require(runtime.exact_field(confirm, "kernel_release") == EXPECTED_RELEASE,
            "confirmation kernel changed")
    require(runtime.exact_field(confirm, "architecture") == "aarch64",
            "confirmation architecture changed")
    require(runtime.exact_field(confirm, "boot_id_sha256") == trigger_boot,
            "live boot differs from retained trigger")
    require(runtime.exact_field(confirm, "post_confirm_boot_id_sha256") == trigger_boot,
            "boot changed during confirmation")
    require(runtime.exact_field(confirm, "cpu_possible") == "0-9", "possible CPUs changed")
    require(runtime.exact_field(confirm, "cpu_present") == "0-9", "present CPUs changed")
    require(runtime.exact_field(confirm, "cpu_online") == "0-7", "online CPUs changed")
    require(runtime.exact_field(confirm, "cpu_offline") == "8-9", "offline CPUs changed")
    require(runtime.exact_field(confirm, "block_mounts") == "0", "block mount appeared")
    require(runtime.exact_field(confirm, "sysfs_mount") == "ro", "sysfs is not read-only")
    runtime.validate_state(runtime.block(
        confirm,
        "__RUNTIME_PREFLIGHT_CONFIRM_STATE_BEGIN__",
        "__RUNTIME_PREFLIGHT_CONFIRM_STATE_END__",
    ), passed=True)
    runtime.validate_status(runtime.block(
        confirm,
        "__I2C6_CONFIRM_STATUS_BEGIN__",
        "__I2C6_CONFIRM_STATUS_END__",
    ), runtime.PRE_SEQUENCE + runtime.TRIGGER_SEQUENCE)
    require(re.fullmatch(r"[0-9a-f]{64}", trigger_boot) is not None, "boot hash malformed")

    print("finalization_classification=posttrigger-live-confirmed")
    print(f"kernel_release={EXPECTED_RELEASE}")
    print("runtime_preflight_state=passed")
    print("runtime_preflight_attempts=1")
    print("I2C6_ledger_count=30")
    print("DA921x_register_data_writes=0")
    print("sysfs_mount=ro")
    print("CPU8_CPU9_admission=closed")
    print("native_reboot_permitted=once")
    print("result=pass")


if __name__ == "__main__":
    main()
