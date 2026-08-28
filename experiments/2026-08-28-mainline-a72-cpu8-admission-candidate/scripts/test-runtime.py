#!/usr/bin/env python3
"""Exercise the exact CPU8 admission runtime decision map."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import struct


SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATOR = SCRIPT_DIR / "validate-runtime.py"
spec = importlib.util.spec_from_file_location("admission_runtime", VALIDATOR)
assert spec is not None and spec.loader is not None
RUNTIME = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RUNTIME)


def ledger(*, phase: int, stage: int, terminal: int) -> str:
    record = RUNTIME.LEDGER.encode_record(
        attempt=0x1122334455667788,
        generation=1,
        phase=phase,
        stage=stage,
        terminal=terminal,
    )
    data = struct.pack(
        "<3I", RUNTIME.LEDGER.SIGNATURE,
        RUNTIME.LEDGER.PAYLOAD_SIZE, RUNTIME.LEDGER.PAYLOAD_SIZE,
    ) + record + bytes(RUNTIME.LEDGER.COPY_BYTES)
    return data.hex()


def empty_ledger() -> str:
    return (struct.pack("<3I", RUNTIME.LEDGER.SIGNATURE, 0, 0) +
            bytes(RUNTIME.LEDGER.PAYLOAD_SIZE)).hex()


def capture(*, ret: int, requests: int, online: str, offline: str,
            ledger_hex: str) -> str:
    return f"""
{RUNTIME.BEGIN}
installed_full_sha256={RUNTIME.CANDIDATE}
kernel_release={RUNTIME.RELEASE}
architecture=aarch64
boot_id=01234567-89ab-cdef-0123-456789abcdef
uptime_seconds=42.5
model=MT6797X
compatible=planet,gemini-pda,mediatek,mt6797,
cpu_possible=0-9
cpu_present=0-9
cpu_online={online}
cpu_offline={offline}
maxcpus8_tokens=1
udc_devices=1
block_mounts=0
pstore_files=0
transition_ledger_hex={ledger_hex}
{RUNTIME.MARKERS_BEGIN}
driver: GEMINI_A72_ADMISSION_V1 state=terminal ret={ret} consumed=1 requests={requests}/0/0 retries=0
{RUNTIME.MARKERS_END}
device_partition_reads=none
device_storage_writes=none
driver_binding_changes=none
userspace_regulator_request=none
userspace_clock_request=none
userspace_secure_call_request=none
userspace_cpu_request=none
reboot_request=none
{RUNTIME.END}
"""


def main() -> None:
    success = RUNTIME.classify_text(capture(
        ret=0, requests=1, online="0-8", offline="9",
        ledger_hex=ledger(phase=3, stage=9, terminal=5),
    ))
    assert success[0] == "serviceable-cpu8-online-proof"
    rejected = RUNTIME.classify_text(capture(
        ret=-11, requests=0, online="0-7", offline="8-9",
        ledger_hex=empty_ledger(),
    ))
    assert rejected[0] == "serviceable-pre-request-rejection"
    failed = RUNTIME.classify_text(capture(
        ret=-5, requests=1, online="0-7", offline="8-9",
        ledger_hex=ledger(phase=3, stage=5, terminal=4),
    ))
    assert failed[0] == "serviceable-cpu8-transition-failure"
    try:
        RUNTIME.classify_text(capture(
            ret=0, requests=1, online="0-9", offline="",
            ledger_hex=ledger(phase=3, stage=9, terminal=5),
        ))
    except RUNTIME.Classification as error:
        assert error.result == "rejected-decision"
    else:
        raise AssertionError("CPU9-online capture was accepted")
    print("runtime_decision_map_tests=4-of-4-pass")
    print("device_access=none")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
