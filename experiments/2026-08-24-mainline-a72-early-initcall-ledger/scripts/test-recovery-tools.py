#!/usr/bin/env python3
"""Reject unsafe A72 early-initcall retained-recovery mutations."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent


def load():
    path = SCRIPT_DIR / "classify-recovery.py"
    spec = importlib.util.spec_from_file_location("a72_early_initcall_recovery", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECOVERY = load()


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


def records(state_1: str, state_2: str) -> tuple[bytes, bytes]:
    record_1 = record(
        RECOVERY.MARKER_1 if state_1 == "pure" else None,
        RECOVERY.VALID_HEADER_1,
    )
    if state_2 == "core":
        record_2 = record(
            RECOVERY.MARKER_2_CORE, RECOVERY.VALID_HEADER_2_CORE
        )
    elif state_2 == "refusal":
        record_2 = record(
            RECOVERY.MARKER_2_REFUSAL, RECOVERY.VALID_HEADER_2_REFUSAL
        )
    else:
        record_2 = record(None, RECOVERY.EMPTY_HEADER)
    return record_1, record_2


def capture(state_1: str, state_2: str, pstore: bytes = b"") -> str:
    encoded = lambda payload: base64.b64encode(payload).decode()
    record_1, record_2 = records(state_1, state_2)
    values = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "recovery_boot_id": "12345678-1234-1234-1234-123456789abc",
        "active_root": "/dev/mmcblk0p29",
        "boot2_device": "/dev/mmcblk0p30",
        "boot2_full_sha256": RECOVERY.CANDIDATE,
        "pstore_mounted": "yes",
        "pstore_file_count": "1" if pstore else "0",
        "pstore_file_metadata_b64": encoded(b"dmesg-ramoops-0 249\n" if pstore else b""),
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
    with tempfile.TemporaryDirectory(prefix="gemini-a72-early-recovery-test.") as raw:
        path = Path(raw) / "capture.txt"
        path.write_text(text, encoding="ascii")
        return RECOVERY.classify(path)[0]


def replace_record(text: str, old: bytes, new: bytes) -> str:
    return text.replace(
        base64.b64encode(old).decode(),
        base64.b64encode(new).decode(),
        1,
    )


def main() -> None:
    neither = capture("empty", "empty")
    refusal_only = capture("empty", "refusal", RECOVERY.RECORD_2_REFUSAL)
    pure_only = capture("pure", "empty", RECOVERY.RECORD_1)
    pure_refusal = capture(
        "pure", "refusal", RECOVERY.RECORD_1 + RECOVERY.RECORD_2_REFUSAL
    )
    pure_core = capture(
        "pure", "core", RECOVERY.RECORD_1 + RECOVERY.RECORD_2_CORE
    )
    require(result(neither) == "before-pure-init-or-both-writers-refused",
            "neither branch rejected")
    require(result(refusal_only) == "pure-primary-refused-only",
            "refusal-only branch rejected")
    require(result(pure_only) == "pure-init-only", "pure-only branch rejected")
    require(result(pure_refusal) == "pure-plus-primary-refused",
            "pure-plus-refusal branch rejected")
    require(result(pure_core) == "pure-and-core-initcalls",
            "pure-plus-core branch rejected")

    valid_record_1, _ = records("pure", "empty")
    corrupt_payload_record = bytearray(valid_record_1)
    corrupt_payload_record[12 + len(RECOVERY.PREFIX)] ^= 1
    corrupt_payload = replace_record(
        pure_core, valid_record_1, bytes(corrupt_payload_record)
    )
    corrupt_tail_record = bytearray(valid_record_1)
    corrupt_tail_record[-1] = 0
    corrupt_tail = replace_record(
        pure_core, valid_record_1, bytes(corrupt_tail_record)
    )
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
        capture("empty", "core"),
        capture("empty", "empty", RECOVERY.RECORD_1),
        corrupt_payload,
        corrupt_tail,
        pure_core.replace(
            "record_1_header=" + RECOVERY.VALID_HEADER_1,
            "record_1_header=" + RECOVERY.EMPTY_HEADER,
            1,
        ),
        capture(
            "pure", "core", RECOVERY.RECORD_1 + RECOVERY.RECORD_1
        ),
        capture(
            "pure", "core", RECOVERY.RECORD_1 + RECOVERY.RECORD_2_REFUSAL
        ),
    )
    require(all(result(item) == "rejected-attribution" for item in mutations),
            "unsafe recovery mutation escaped")

    print("validation=a72-early-initcall-recovery-tools")
    print("valid_branches_accepted=5")
    print(f"unsafe_mutations_rejected={len(mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
