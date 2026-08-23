#!/usr/bin/env python3
"""Reject unsafe one-shot protected-clock live and recovery mutations."""

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


LIVE = load("protected_clock_live", SCRIPT_DIR / "validate-runtime.py")
RETAINED = load("protected_clock_retained", SCRIPT_DIR / "validate-retained.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def live_values() -> dict[str, str]:
    return {
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
        "protected_readback_devices": "1",
        "handoff_bound": "1",
        "i2c6_bound": "1",
        "clock_backend_bound": "1",
        "observer_bound": "1",
        "handoff_state": "ready",
        "i2c6_handoff_ready_count": "1",
        "cspm_range_count": "1",
        "cspm_handoff_owner_count": "1",
        "mcumixed_clock_owner_count": "1",
        "clock_prefix_count": "1",
        "clock_success_prefix_count": "1",
        "clock_shape_count": "1",
        "terminal_prefix_count": "1",
        "terminal_exact_count": "1",
        "bigidvfs_record_count": "0",
        "owner_exact_count": "1",
        "handoff_ebusy_count": "0",
        "block_mounts": "0",
        "pstore_files": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "same_value_action_request": "none",
        "observer_trigger": "automatic-probe-once",
        "protected_clock_caller_retries": "zero",
        "bigidvfs_calls": "zero",
        "mapped_clock_mmio_read_snapshots": "one",
        "clock_enable_disable_pairs": "one",
        "secure_calls": "zero",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }


def live_capture(values: dict[str, str] | None = None) -> str:
    values = live_values() if values is None else values
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
    for marker, header in (
        (RETAINED.MARKER_1, RETAINED.VALID_HEADER_1),
        (RETAINED.MARKER_2, RETAINED.VALID_HEADER_2),
    ):
        record = bytearray(b"\xff" * 4096)
        record[:12] = bytes.fromhex(header)
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
            b"dmesg-ramoops-0 121\ndmesg-ramoops-1 120\n" if pstore else b""
        ),
        "pstore_payload_b64": encoded(pstore),
        "record_1_size": "4096",
        "record_1_header": RETAINED.VALID_HEADER_1,
        "record_1_b64": encoded(records[0]),
        "record_2_size": "4096",
        "record_2_header": RETAINED.VALID_HEADER_2,
        "record_2_b64": encoded(records[1]),
        "ramoops_registration_lines": "1",
        "ramoops_dmesg_b64": encoded(b"ramoops: attached\n"),
        "ramoops_parameters_b64": encoded(b"record_size=4096\n"),
        "device_memory_writes": "none",
        "device_partition_writes": "none",
    }
    return "\n".join(f"{key}={value}" for key, value in values.items()) + "\n"


def retained_result(text: str) -> str:
    with tempfile.TemporaryDirectory(prefix="gemini-protected-clock-retained-test.") as raw:
        path = Path(raw) / "capture.txt"
        path.write_text(text, encoding="ascii")
        return RETAINED.classify(path)[0]


def main() -> None:
    valid_values = live_values()
    live = live_capture(valid_values)
    require(LIVE.classify_text(live)[0] == "protected-clock-first-dmesg-live-pass",
            "valid live result rejected")
    live_mutations = []
    for key, value in valid_values.items():
        if key in {"boot_id", "uptime_seconds", "cmdline", "pstore_files"}:
            continue
        changed = dict(valid_values)
        changed[key] = "wrong"
        live_mutations.append(live_capture(changed))
    for key, wrong in (
        ("boot_id", "malformed"),
        ("uptime_seconds", "nan"),
        ("cmdline", "console=ttyS0 maxcpus=9 rdinit=/init"),
        ("pstore_files", "many"),
    ):
        changed = dict(valid_values)
        changed[key] = wrong
        live_mutations.append(live_capture(changed))
    live_mutations.append(live.replace(LIVE.END, f"{LIVE.END}\n{LIVE.END}", 1))
    require(all(live_rejected(item) for item in live_mutations),
            "unsafe live mutation escaped")

    direct = retained_capture()
    pstore = retained_capture(RETAINED.RECORD_1 + RETAINED.RECORD_2)
    require(retained_result(direct) == "protected-clock-direct-retention-only",
            "direct-only result rejected")
    require(retained_result(pstore) == "protected-clock-cross-version-enumeration-pass",
            "pstore result rejected")
    retained_mutations = (
        direct.replace(RETAINED.CANDIDATE, "0" * 64, 1),
        direct.replace("active_root=/dev/mmcblk0p29", "active_root=/dev/mmcblk0p30", 1),
        direct.replace("pstore_mounted=yes", "pstore_mounted=no", 1),
        direct.replace("record_1_size=4096", "record_1_size=4095", 1),
        direct.replace("record_1_header=" + RETAINED.VALID_HEADER_1,
                       "record_1_header=444247430000000000000000", 1),
        direct.replace("record_1_b64=", "record_1_b64=***", 1),
        direct.replace("record_2_size=4096", "record_2_size=4095", 1),
        direct.replace("record_2_header=" + RETAINED.VALID_HEADER_2,
                       "record_2_header=444247430000000000000000", 1),
        direct.replace("record_2_b64=", "record_2_b64=***", 1),
        direct.replace("device_memory_writes=none", "device_memory_writes=one", 1),
        direct + "boot2_full_sha256=" + RETAINED.CANDIDATE + "\n",
        retained_capture(RETAINED.RECORD_1),
    )
    require(all(retained_result(item) == "rejected-attribution" for item in retained_mutations),
            "unsafe retained mutation escaped")

    probe = (SCRIPT_DIR / "remote-runtime-probe.sh").read_text(encoding="utf-8")
    for required in (
        "$BB dmesg", "clock_shape_count", "terminal_exact_count",
        "bigidvfs_record_count", "cspm_handoff_owner_count", "observer_bound",
    ):
        require(probe.count(required) >= 1, f"probe requirement changed: {required}")
    for forbidden in ("/dev/mem", "cpu_up", "cpu_down", "/bin/reboot", "writel"):
        require(forbidden not in probe, f"probe gained forbidden effect: {forbidden}")

    print("validation=protected-clock-first-dmesg-runtime-tools")
    print("live_results_accepted=1")
    print(f"live_unsafe_mutations_rejected={len(live_mutations)}")
    print("retained_recovery_forms_accepted=2")
    print(f"retained_unsafe_mutations_rejected={len(retained_mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
