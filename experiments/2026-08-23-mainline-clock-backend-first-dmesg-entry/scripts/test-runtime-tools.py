#!/usr/bin/env python3
"""Reject unsafe clock-entry live and retained-recovery mutations."""

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


LIVE = load("clock_entry_live", SCRIPT_DIR / "validate-runtime.py")
RETAINED = load("clock_entry_retained", SCRIPT_DIR / "validate-retained.py")


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
        "clock_backend_devices": "1",
        "bigidvfs_backend_devices": "0",
        "protected_readback_devices": "0",
        "clock_prefix_count": "3",
        "driver_init_exact_count": "1",
        "probe_enter_exact_count": "1",
        "probe_complete_exact_count": "1",
        "old_clock_prefix_count": "0",
        "first_dmesg_prefix_count": "0",
        "block_mounts": "0",
        "pstore_files": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "same_value_action_request": "none",
        "protected_read_request": "none",
        "secure_call_request": "none",
        "mapped_mmio_transaction": "none",
        "clock_enable_request": "none",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    body = "\n".join(f"{key}={value}" for key, value in values.items())
    return f"noise\n{LIVE.BEGIN}\n{body}\n{LIVE.END}\n"


def live_rejected(text: str) -> bool:
    try:
        LIVE.classify_text(text)
    except LIVE.Classification:
        return True
    return False


def retained_capture(pstore: bytes = b"") -> str:
    encoded = lambda payload: base64.b64encode(payload).decode()
    records = []
    for marker in (RETAINED.MARKER_1, RETAINED.MARKER_2):
        record = bytearray(b"\xff" * 4096)
        record[:12] = bytes.fromhex(RETAINED.VALID_HEADER)
        payload = RETAINED.PREFIX + marker
        record[12:12 + len(payload)] = payload
        records.append(bytes(record))
    values = {
        "recovery_kernel": "3.18.41+",
        "recovery_architecture": "aarch64",
        "recovery_boot_id_sha256": "1" * 64,
        "active_root": "/dev/mmcblk0p29",
        "boot2_device": "/dev/mmcblk0p30",
        "boot2_full_sha256": RETAINED.CANDIDATE,
        "pstore_mounted": "yes",
        "pstore_file_count": "2" if pstore else "0",
        "pstore_file_metadata_b64": encoded(
            b"dmesg-ramoops-0 118\ndmesg-ramoops-1 118\n" if pstore else b""
        ),
        "pstore_payload_b64": encoded(pstore),
        "record_1_size": "4096",
        "record_1_header": RETAINED.VALID_HEADER,
        "record_1_b64": encoded(records[0]),
        "record_2_size": "4096",
        "record_2_header": RETAINED.VALID_HEADER,
        "record_2_b64": encoded(records[1]),
        "ramoops_registration_lines": "1",
        "ramoops_dmesg_b64": encoded(b"ramoops: attached\n"),
        "ramoops_parameters_b64": encoded(b"record_size=4096\n"),
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def retained_result(text: str) -> str:
    with tempfile.TemporaryDirectory(prefix="gemini-clock-entry-retained-test.") as raw:
        path = Path(raw) / "capture.txt"
        path.write_text(text, encoding="ascii")
        return RETAINED.classify(path)[0]


def main() -> None:
    live = live_capture()
    require(LIVE.classify_text(live)[0] == "clock-backend-first-dmesg-live-pass",
            "valid live result rejected")
    live_mutations = (
        live.replace(LIVE.CANDIDATE, "0" * 64, 1),
        live.replace(LIVE.RELEASE, "wrong-release", 1),
        live.replace("architecture=aarch64", "architecture=armv7l", 1),
        live.replace("model=MT6797X", "model=wrong", 1),
        live.replace("cpu_online=0-7", "cpu_online=0-8", 1),
        live.replace("cpu_offline=8-9", "cpu_offline=9", 1),
        live.replace("clock_backend_devices=1", "clock_backend_devices=0", 1),
        live.replace("bigidvfs_backend_devices=0", "bigidvfs_backend_devices=1", 1),
        live.replace("protected_readback_devices=0", "protected_readback_devices=1", 1),
        live.replace("clock_prefix_count=3", "clock_prefix_count=2", 1),
        live.replace("driver_init_exact_count=1", "driver_init_exact_count=0", 1),
        live.replace("probe_enter_exact_count=1", "probe_enter_exact_count=0", 1),
        live.replace("probe_complete_exact_count=1", "probe_complete_exact_count=0", 1),
        live.replace("old_clock_prefix_count=0", "old_clock_prefix_count=1", 1),
        live.replace("first_dmesg_prefix_count=0", "first_dmesg_prefix_count=1", 1),
        live.replace("block_mounts=0", "block_mounts=1", 1),
        live.replace("device_storage_writes=none", "device_storage_writes=one", 1),
        live.replace("protected_read_request=none", "protected_read_request=one", 1),
        live.replace("mapped_mmio_transaction=none", "mapped_mmio_transaction=one", 1),
        live.replace("clock_enable_request=none", "clock_enable_request=one", 1),
        live.replace("cpu_admission_request=none", "cpu_admission_request=one", 1),
        live.replace("reboot_request=none", "reboot_request=one", 1),
        live.replace("maxcpus=8", "maxcpus=9", 1),
        live.replace(LIVE.END, f"{LIVE.END}\n{LIVE.END}", 1),
    )
    require(all(live_rejected(item) for item in live_mutations),
            "unsafe live mutation escaped")

    direct = retained_capture()
    pstore = retained_capture(RETAINED.RECORD_1 + RETAINED.RECORD_2)
    require(retained_result(direct) == "clock-entry-direct-retention-only",
            "direct-only result rejected")
    require(retained_result(pstore) == "clock-entry-cross-version-enumeration-pass",
            "pstore result rejected")
    retained_mutations = (
        direct.replace(RETAINED.CANDIDATE, "0" * 64, 1),
        direct.replace("active_root=/dev/mmcblk0p29", "active_root=/dev/mmcblk0p30", 1),
        direct.replace("pstore_mounted=yes", "pstore_mounted=no", 1),
        direct.replace("record_1_size=4096", "record_1_size=4095", 1),
        direct.replace("record_1_header=" + RETAINED.VALID_HEADER,
                       "record_1_header=444247430000000000000000", 1),
        direct.replace("record_1_b64=", "record_1_b64=***", 1),
        direct.replace("record_2_size=4096", "record_2_size=4095", 1),
        direct.replace("record_2_header=" + RETAINED.VALID_HEADER,
                       "record_2_header=444247430000000000000000", 1),
        direct.replace("record_2_b64=", "record_2_b64=***", 1),
        direct.replace("device_memory_writes=none", "device_memory_writes=one", 1),
        direct + "boot2_full_sha256=" + RETAINED.CANDIDATE + "\n",
        retained_capture(RETAINED.RECORD_1),
    )
    require(all(retained_result(item) == "rejected-attribution" for item in retained_mutations),
            "unsafe retained mutation escaped")

    probe = (SCRIPT_DIR / "remote-runtime-probe.sh").read_text(encoding="utf-8")
    for required in ("$BB dmesg", "probe_complete_exact_count", "clock_backend_devices"):
        require(probe.count(required) >= 1, f"probe requirement changed: {required}")
    for forbidden in ("/dev/mem", "cpu_up", "cpu_down", "/bin/reboot", "writel"):
        require(forbidden not in probe, f"probe gained forbidden effect: {forbidden}")

    print("validation=clock-backend-first-dmesg-runtime-tools")
    print("live_results_accepted=1")
    print(f"live_unsafe_mutations_rejected={len(live_mutations)}")
    print("retained_recovery_forms_accepted=2")
    print(f"retained_unsafe_mutations_rejected={len(retained_mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
