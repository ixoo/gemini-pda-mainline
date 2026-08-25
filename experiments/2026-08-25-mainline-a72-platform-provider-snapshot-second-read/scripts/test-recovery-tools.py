#!/usr/bin/env python3
"""Reject unsafe platform/provider retained-recovery mutations."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("platform_provider_recovery", SCRIPT_DIR / "classify-recovery.py")
assert SPEC is not None and SPEC.loader is not None
RECOVERY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RECOVERY)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def record(marker: bytes | None, header: str) -> bytes:
    value = bytearray(b"\xff" * 4096)
    if marker is None:
        value[:12] = bytes.fromhex(RECOVERY.EMPTY_HEADER)
    else:
        value[:12] = bytes.fromhex(header)
        payload = RECOVERY.PREFIX + marker
        value[12:12 + len(payload)] = payload
    return bytes(value)


def capture(state_1: str, state_2: str) -> str:
    encoded = lambda payload: base64.b64encode(payload).decode()
    record_1 = record(
        RECOVERY.MARKER_1 if state_1 == "valid" else None,
        RECOVERY.VALID_HEADER_1,
    )
    record_2 = record(
        RECOVERY.MARKER_2 if state_2 == "valid" else None,
        RECOVERY.VALID_HEADER_2,
    )
    values = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "deployment_boot_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "recovery_boot_id": "12345678-1234-1234-1234-123456789abc",
        "active_root": "/dev/mmcblk0p29",
        "boot2_device": "/dev/mmcblk0p30",
        "boot2_full_sha256": RECOVERY.CANDIDATE,
        "record_1_size": "4096",
        "record_1_header": record_1[:12].hex(),
        "record_1_b64": encoded(record_1),
        "record_2_size": "4096",
        "record_2_header": record_2[:12].hex(),
        "record_2_b64": encoded(record_2),
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def result(text: str) -> str:
    with tempfile.TemporaryDirectory(prefix="gemini-platform-provider-recovery-test.") as raw:
        path = Path(raw) / "capture.txt"
        path.write_text(text, encoding="ascii")
        return RECOVERY.classify(path)[0]


neither = capture("empty", "empty")
before = capture("valid", "empty")
both = capture("valid", "valid")
require(result(neither) == "before-provider-boundary-or-writer-refused", "neither branch rejected")
require(result(before) == "before-provider-only", "before-provider branch rejected")
require(result(both) == "provider-returned", "both branch rejected")

valid_record_1 = record(RECOVERY.MARKER_1, RECOVERY.VALID_HEADER_1)
corrupt_record_1 = bytearray(valid_record_1)
corrupt_record_1[12 + len(RECOVERY.PREFIX)] ^= 1
corrupt_payload = before.replace(
    base64.b64encode(valid_record_1).decode(),
    base64.b64encode(corrupt_record_1).decode(),
    1,
)
mutations = (
    neither.replace(RECOVERY.CANDIDATE, "0" * 64, 1),
    neither.replace("recovery_kernel=3.18.41+", "recovery_kernel=wrong", 1),
    neither.replace("active_root=/dev/mmcblk0p29", "active_root=/dev/mmcblk0p30", 1),
    neither.replace("boot2_device=/dev/mmcblk0p30", "boot2_device=wrong", 1),
    neither.replace("device_memory_writes=none", "device_memory_writes=one", 1),
    neither.replace("device_partition_writes=none", "device_partition_writes=one", 1),
    neither.replace("record_1_size=4096", "record_1_size=4095", 1),
    neither.replace("record_1_b64=", "record_1_b64=***", 1),
    neither.replace("record_2_b64=", "record_2_b64=***", 1),
    neither + "boot2_full_sha256=" + RECOVERY.CANDIDATE + "\n",
    neither.replace(
        "recovery_boot_id=12345678-1234-1234-1234-123456789abc",
        "recovery_boot_id=aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        1,
    ),
    capture("empty", "valid"),
    corrupt_payload,
    before.replace(
        "record_1_header=" + RECOVERY.VALID_HEADER_1,
        "record_1_header=" + RECOVERY.EMPTY_HEADER,
        1,
    ),
    both.replace(
        base64.b64encode(record(RECOVERY.MARKER_2, RECOVERY.VALID_HEADER_2)).decode(),
        base64.b64encode(record(RECOVERY.MARKER_2, RECOVERY.VALID_HEADER_1)).decode(),
        1,
    ),
)
require(all(result(item) == "rejected-attribution" for item in mutations),
        "unsafe recovery mutation escaped")
print("validation=a72-platform-provider-recovery-tools")
print("valid_branches_accepted=3")
print(f"unsafe_mutations_rejected={len(mutations)}")
print("device_access=none")
print("hardware_write=none")
print("result=pass")
