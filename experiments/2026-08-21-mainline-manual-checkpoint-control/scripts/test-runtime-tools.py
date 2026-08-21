#!/usr/bin/env python3
"""Reject unsafe live and retained-capture mutations offline."""

from __future__ import annotations

import base64
import importlib.util
from pathlib import Path
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


LIVE = load("manual_checkpoint_live", SCRIPT_DIR / "validate-runtime.py")
RETAINED = load("manual_checkpoint_retained", SCRIPT_DIR / "validate-retained.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def live_capture() -> str:
    values = {
        "installed_full_sha256": LIVE.CANDIDATE,
        "kernel_release": LIVE.RELEASE,
        "architecture": "aarch64",
        "boot_id": "12345678-1234-1234-1234-123456789abc",
        "uptime_seconds": "12.5",
        "cmdline": "console=ttyS0 maxcpus=8 rdinit=/init",
        "model": "MT6797X",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "udc_devices": "1",
        "keyboard_matrix_inputs": "1",
        "da921x_i2c_clients": "1",
        "same_value_write_attributes": "0",
        "clock_backend_devices": "0",
        "bigidvfs_backend_devices": "0",
        "protected_readback_devices": "0",
        "manual_live_prefix_count": "1",
        "manual_live_exact_count": "1",
        "block_mounts": "0",
        "pstore_files": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "same_value_action_request": "none",
        "protected_read_request": "none",
        "secure_call_request": "none",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    body = "\n".join(f"{key}={value}" for key, value in values.items())
    return f"noise\n{LIVE.BEGIN}\n{body}\n{LIVE.END}\n"


def retained_capture(slot_173: bytes, slot_174: bytes, pstore: bytes = b"") -> str:
    values = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "recovery_boot_id_sha256": "1" * 64,
        "active_root": "/dev/mmcblk0p29",
        "boot2_device": "/dev/mmcblk0p30",
        "boot2_full_sha256": RETAINED.CANDIDATE,
        "slot_173_size": "4096",
        "slot_174_size": "4096",
        "slot_173_header": slot_173[:12].hex(),
        "slot_174_header": slot_174[:12].hex(),
        "slot_173_b64": base64.b64encode(slot_173).decode(),
        "slot_174_b64": base64.b64encode(slot_174).decode(),
        "pstore_file_count": "0" if not pstore else "2",
        "pstore_payload_b64": base64.b64encode(pstore).decode(),
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def retained_result(text: str) -> str:
    with tempfile.TemporaryDirectory(prefix="gemini-manual-retained-test.") as raw:
        path = Path(raw) / "capture.txt"
        path.write_text(text, encoding="ascii")
        return RETAINED.classify(path)[0]


def main() -> None:
    live = live_capture()
    require(
        LIVE.classify_text(live)[0] == "manual-checkpoint-live-pass",
        "valid live capture rejected",
    )
    live_mutations = (
        live.replace(LIVE.CANDIDATE, "0" * 64, 1),
        live.replace(LIVE.RELEASE, "wrong-release", 1),
        live.replace("architecture=aarch64", "architecture=armv7l", 1),
        live.replace("model=MT6797X", "model=wrong", 1),
        live.replace("cpu_online=0-7", "cpu_online=0-8", 1),
        live.replace("cpu_offline=8-9", "cpu_offline=9", 1),
        live.replace("manual_live_prefix_count=1", "manual_live_prefix_count=0", 1),
        live.replace("manual_live_exact_count=1", "manual_live_exact_count=0", 1),
        live.replace("clock_backend_devices=0", "clock_backend_devices=1", 1),
        live.replace("protected_readback_devices=0", "protected_readback_devices=1", 1),
        live.replace("block_mounts=0", "block_mounts=1", 1),
        live.replace("device_storage_writes=none", "device_storage_writes=one", 1),
        live.replace("protected_read_request=none", "protected_read_request=one", 1),
        live.replace("secure_call_request=none", "secure_call_request=one", 1),
        live.replace("cpu_admission_request=none", "cpu_admission_request=one", 1),
        live.replace("reboot_request=none", "reboot_request=one", 1),
        live.replace("maxcpus=8", "maxcpus=9", 1),
        live.replace(LIVE.END, f"{LIVE.END}\n{LIVE.END}", 1),
        live.replace("boot_id=12345678-1234-1234-1234-123456789abc",
                     "boot_id=malformed", 1),
    )
    require(all(item != live for item in live_mutations), "live mutation was inert")
    require(
        all(LIVE.classify_text(item)[0] != "manual-checkpoint-live-pass"
            if not _raises_live(item) else True for item in live_mutations),
        "unsafe live mutation escaped",
    )

    empty = bytes.fromhex(RETAINED.EMPTY_HEADER) + b"\xff" * (4096 - 12)
    empty_text = retained_capture(empty, empty)
    require(retained_result(empty_text) == "live-pass-recovered-empty",
            "valid empty recovery rejected")
    first_slot = bytearray(empty)
    second_slot = bytearray(empty)
    first_slot[64:64 + len(RETAINED.FIRST)] = RETAINED.FIRST
    second_slot[64:64 + len(RETAINED.SECOND)] = RETAINED.SECOND
    records_text = retained_capture(bytes(first_slot), bytes(second_slot))
    require(retained_result(records_text) == "writer-and-recovery-pass",
            "valid retained records rejected")
    retained_mutations = (
        empty_text.replace(RETAINED.CANDIDATE, "0" * 64, 1),
        empty_text.replace("active_root=/dev/mmcblk0p29", "active_root=/dev/mmcblk0p30", 1),
        empty_text.replace("slot_173_size=4096", "slot_173_size=4095", 1),
        empty_text.replace(f"slot_173_header={RETAINED.EMPTY_HEADER}",
                           "slot_173_header=" + "0" * 24, 1),
        records_text.replace(base64.b64encode(bytes(second_slot)).decode(),
                             base64.b64encode(empty).decode(), 1),
        records_text.replace("slot_173_b64=", "slot_173_b64=***", 1),
        records_text.replace(
            base64.b64encode(bytes(first_slot)).decode(),
            "SWAP_SLOT_PAYLOAD",
            1,
        ).replace(
            base64.b64encode(bytes(second_slot)).decode(),
            base64.b64encode(bytes(first_slot)).decode(),
            1,
        ).replace("SWAP_SLOT_PAYLOAD", base64.b64encode(bytes(second_slot)).decode(), 1),
        records_text.replace("device_memory_writes=none", "device_memory_writes=one", 1),
        records_text + "boot2_full_sha256=" + RETAINED.CANDIDATE + "\n",
    )
    require(all(item not in (empty_text, records_text) for item in retained_mutations),
            "retained mutation was inert")
    require(all(retained_result(item) == "rejected-attribution"
                for item in retained_mutations), "unsafe retained mutation escaped")

    probe = (SCRIPT_DIR / "remote-runtime-probe.sh").read_text(encoding="utf-8")
    for required in ("$BB dmesg", "manual_live_prefix_count", "manual_live_exact_count"):
        require(probe.count(required) >= 1, f"probe requirement changed: {required}")
    for forbidden in ("/dev/mem", "cpu_up", "cpu_down", "/bin/reboot", "writel"):
        require(forbidden not in probe, f"probe gained forbidden effect: {forbidden}")

    print("validation=manual-checkpoint-runtime-tools")
    print(f"live_unsafe_mutations_rejected={len(live_mutations)}")
    print(f"retained_unsafe_mutations_rejected={len(retained_mutations)}")
    print("live_pass_oracle=two-local-full-readbacks")
    print("recovered_empty_distinguished=yes")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


def _raises_live(text: str) -> bool:
    try:
        LIVE.classify_text(text)
    except LIVE.Classification:
        return True
    return False


if __name__ == "__main__":
    main()
