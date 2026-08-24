#!/usr/bin/env python3
"""Exercise accepted and rejected live-control classifications."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("validate_runtime", SCRIPT_DIR / "validate-runtime.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def capture(markers: tuple[str, ...] = ()) -> str:
    return "\n".join(
        (
            MODULE.BEGIN,
            f"installed_full_sha256={MODULE.CANDIDATE}",
            f"kernel_release={MODULE.RELEASE}",
            "architecture=aarch64",
            "boot_id=12345678-1234-1234-1234-123456789abc",
            "uptime_seconds=55.25",
            "model=MT6797X",
            "compatible=planet,gemini-pda,mediatek,mt6797,",
            "cpu_possible=0-9",
            "cpu_present=0-9",
            "cpu_online=0-7",
            "cpu_offline=8-9",
            "maxcpus8_tokens=1",
            "udc_devices=1",
            "block_mounts=0",
            "pstore_files=0",
            MODULE.MARKERS_BEGIN,
            *markers,
            MODULE.MARKERS_END,
            "device_partition_reads=none",
            "device_storage_writes=none",
            "driver_binding_changes=none",
            "regulator_action_request=none",
            "clock_action_request=none",
            "secure_call_request=none",
            "owner_registration_request=none",
            "cpu_admission_request=none",
            "reboot_request=none",
            MODULE.END,
        )
    )


def accepted(markers: tuple[str, ...], expected: str) -> None:
    result, _, ledger, _ = MODULE.classify_text(capture(markers))
    assert result == "serviceable-stage27-control-pass"
    assert ledger == expected


def rejected(text: str, expected: str) -> None:
    try:
        MODULE.classify_text(text)
    except MODULE.Classification as result:
        assert result.result == expected
    else:
        raise AssertionError("unsafe capture was accepted")


accepted((), "no-early-record-exposed-live")
accepted((MODULE.PURE,), "pure-only-live")
accepted((MODULE.PURE, MODULE.CORE), "pure-plus-core-live")
accepted((MODULE.REFUSAL,), "primary-refusal-only-live")
accepted((MODULE.PURE, MODULE.REFUSAL), "pure-plus-primary-refusal-live")
rejected(capture((MODULE.CORE,)), "rejected-ledger")
rejected(capture((MODULE.PURE, MODULE.CORE, MODULE.REFUSAL)), "rejected-ledger")
rejected(capture().replace(MODULE.RELEASE, "7.1.3-wrong", 1), "rejected-attribution")
rejected(capture().replace("maxcpus8_tokens=1", "maxcpus8_tokens=0", 1), "rejected-safety")
rejected(capture() + "\n" + capture(), "rejected-attribution")
print("runtime_classifier_accepted_branches=5")
print("runtime_classifier_rejected_mutations=5")
print("result=pass")
