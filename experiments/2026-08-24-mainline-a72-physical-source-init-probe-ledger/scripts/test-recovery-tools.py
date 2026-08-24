#!/usr/bin/env python3
"""Reject unsafe A72 init/probe retained-recovery mutations."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent


def load():
    path = SCRIPT_DIR / "classify-recovery.py"
    spec = importlib.util.spec_from_file_location("a72_init_probe_recovery", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECOVERY = load()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def record(marker: bytes | None) -> bytes:
    value = bytearray(b"\xff" * 4096)
    if marker is None:
        value[:12] = bytes.fromhex(RECOVERY.EMPTY_HEADER)
    else:
        value[:12] = bytes.fromhex(RECOVERY.VALID_HEADER)
        payload = RECOVERY.PREFIX + marker
        value[12:12 + len(payload)] = payload
    return bytes(value)


def capture(state_1: str, state_2: str, pstore: bytes = b"") -> str:
    encoded = lambda payload: base64.b64encode(payload).decode()
    record_1 = record(RECOVERY.MARKER_1 if state_1 == "valid" else None)
    record_2 = record(RECOVERY.MARKER_2 if state_2 == "valid" else None)
    values = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "recovery_boot_id": "12345678-1234-1234-1234-123456789abc",
        "active_root": "/dev/mmcblk0p29",
        "boot2_device": "/dev/mmcblk0p30",
        "boot2_full_sha256": RECOVERY.CANDIDATE,
        "pstore_mounted": "yes",
        "pstore_file_count": "1" if pstore else "0",
        "pstore_file_metadata_b64": encoded(b"dmesg-ramoops-0 107\n" if pstore else b""),
        "pstore_payload_b64": encoded(pstore),
        "record_1_size": "4096",
        "record_1_header": record_1[:12].hex(),
        "record_1_b64": encoded(record_1),
        "record_2_size": "4096",
        "record_2_header": record_2[:12].hex(),
        "record_2_b64": encoded(record_2),
        "ramoops_registration_lines": "1",
        "ramoops_dmesg_b64": encoded(b"ramoops: attached\n"),
        "ramoops_parameters_b64": encoded(b"record_size=4096\n"),
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def result(text: str) -> str:
    with tempfile.TemporaryDirectory(prefix="gemini-a72-init-probe-recovery-test.") as raw:
        path = Path(raw) / "capture.txt"
        path.write_text(text, encoding="ascii")
        return RECOVERY.classify(path)[0]


def main() -> None:
    neither = capture("empty", "empty")
    init_only = capture("valid", "empty", RECOVERY.RECORD_1)
    both = capture("valid", "valid", RECOVERY.RECORD_1 + RECOVERY.RECORD_2)
    valid_record_1 = record(RECOVERY.MARKER_1)
    corrupt_record_1 = bytearray(valid_record_1)
    corrupt_record_1[12 + len(RECOVERY.PREFIX)] ^= 1
    corrupt_payload = both.replace(
        base64.b64encode(valid_record_1).decode(),
        base64.b64encode(corrupt_record_1).decode(),
        1,
    )
    require(result(neither) == "before-driver-init-or-writer-refused",
            "neither branch rejected")
    require(result(init_only) == "driver-init-only", "init-only branch rejected")
    require(result(both) == "driver-init-and-probe-enter", "both branch rejected")

    mutations = (
        neither.replace(RECOVERY.CANDIDATE, "0" * 64, 1),
        neither.replace("recovery_kernel=3.18.41+", "recovery_kernel=wrong", 1),
        neither.replace("active_root=/dev/mmcblk0p29", "active_root=/dev/mmcblk0p30", 1),
        neither.replace("pstore_mounted=yes", "pstore_mounted=no", 1),
        neither.replace("device_memory_writes=none", "device_memory_writes=one", 1),
        neither.replace("device_partition_writes=none", "device_partition_writes=one", 1),
        neither.replace("record_1_size=4096", "record_1_size=4095", 1),
        neither.replace("record_1_b64=", "record_1_b64=***", 1),
        neither.replace("record_2_b64=", "record_2_b64=***", 1),
        neither + "boot2_full_sha256=" + RECOVERY.CANDIDATE + "\n",
        neither.replace(
            "recovery_boot_id=12345678-1234-1234-1234-123456789abc",
            "recovery_boot_id=" + RECOVERY.DEPLOYMENT_BOOT_ID,
            1,
        ),
        capture("empty", "valid"),
        capture("empty", "empty", RECOVERY.RECORD_1),
        corrupt_payload,
        both.replace("record_1_header=" + RECOVERY.VALID_HEADER,
                     "record_1_header=" + RECOVERY.EMPTY_HEADER, 1),
        capture("valid", "valid", RECOVERY.RECORD_1 + RECOVERY.RECORD_1),
    )
    require(all(result(item) == "rejected-attribution" for item in mutations),
            "unsafe recovery mutation escaped")

    print("validation=a72-init-probe-recovery-tools")
    print("valid_branches_accepted=3")
    print(f"unsafe_mutations_rejected={len(mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
