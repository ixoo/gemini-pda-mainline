#!/usr/bin/env python3
"""Validate the concurrent multiline runtime tools and rejection oracle."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CPU_MAP = ROOT / "experiments/2026-09-02-mainline-mt6797-cpu-map/scripts"
DEVICE = HERE / "device-concurrent-multiline.sh"
REMOTE = HERE / "remote-integrated-concurrent-multiline.sh"
CLASSIFIER = HERE / "classify-attempt.py"
EXECUTOR = HERE / "execute-attempt.sh"
COLLECTOR = HERE / "collect-pretrigger.sh"
RECOVERY = HERE / "collect-recovery.sh"
BOOT_ID = "11111111-2222-3333-4444-555555555555"
PAYLOAD = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
BEGIN = "__GEMINI_A72_CONCURRENT_MULTILINE_BEGIN__"
END = "__GEMINI_A72_CONCURRENT_MULTILINE_END__"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load_classifier():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("concurrent_classifier", CLASSIFIER)
    require(spec is not None and spec.loader is not None, "classifier import spec failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def passing_fields() -> dict[str, str]:
    return {
        "boot_id": BOOT_ID,
        "kernel_release": "7.1.3-gemini-cpu9-progress",
        "cpu_online": "0-9",
        "cpu_offline": "",
        "root_entries": "1",
        "root_source": "rootfs",
        "root_fstype": "rootfs",
        "run_mount_entries": "0",
        "block_mounts": "0",
        "rounds": "4",
        "payload_size": "1914704",
        "payload_sha256": PAYLOAD,
        "writer_start_barrier": "bounded-file-publication",
        "reader_start_barrier": "bounded-file-publication",
        "spin_limit": "1000000",
        "cpu8_stat_before": "cpu8 1 0 2 3 0 0 0 0 0 0",
        "cpu9_stat_before": "cpu9 1 0 2 3 0 0 0 0 0 0",
        "writer8_affinity": "8",
        "writer8_processor": "8",
        "writer8_rounds_completed": "4",
        "writer8_size": "1914704",
        "writer8_sha256": PAYLOAD,
        "writer9_affinity": "9",
        "writer9_processor": "9",
        "writer9_rounds_completed": "4",
        "writer9_size": "1914704",
        "writer9_sha256": PAYLOAD,
        "writer8_status": "0",
        "writer9_status": "0",
        "reader8_affinity": "8",
        "reader8_processor": "8",
        "reader8_rounds_completed": "4",
        "reader8_peer_sha256": PAYLOAD,
        "reader9_affinity": "9",
        "reader9_processor": "9",
        "reader9_rounds_completed": "4",
        "reader9_peer_sha256": PAYLOAD,
        "reader8_status": "0",
        "reader9_status": "0",
        "cpu8_stat_after": "cpu8 2 0 3 103 0 0 0 0 0 0",
        "cpu9_stat_after": "cpu9 2 0 3 103 0 0 0 0 0 0",
        "cleanup_file8": "absent",
        "cleanup_file9": "absent",
        "cleanup_auxiliary": "absent",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "cpu_off_request": "none",
        "retry_request": "none",
        "reboot_request": "none",
        "concurrent_result": "pass",
    }


def rejected(module, fields: dict[str, str]) -> bool:
    try:
        module.validate_fields(fields, BOOT_ID)
    except module.Classification:
        return True
    return False


def main() -> int:
    remote = REMOTE.read_text(encoding="utf-8")
    executor = EXECUTOR.read_text(encoding="utf-8")
    classifier_text = CLASSIFIER.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    recovery = RECOVERY.read_text(encoding="utf-8")
    require(digest(CPU_MAP / "remote-integrated-topology-ram.sh") in remote,
            "integrated topology/RAM parent pin changed")
    require(digest(DEVICE) in remote, "concurrent device workload pin changed")
    require(digest(CPU_MAP / "classify-integrated-attempt.py") in classifier_text,
            "parent classifier pin changed")
    require(digest(CPU_MAP / "execute-integrated-attempt.sh") in executor,
            "parent executor pin changed")
    require(digest(REMOTE) in executor and digest(CLASSIFIER) in executor,
            "concurrent executor pins changed")
    require(digest(CPU_MAP / "collect-integrated-pretrigger.sh") in collector,
            "pre-trigger collector pin changed")
    require(digest(CPU_MAP / "collect-integrated-recovery.sh") in recovery,
            "recovery collector pin changed")

    materialized = subprocess.run(
        [str(REMOTE), "--boot-id", BOOT_ID],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout
    require(materialized.count(BOOT_ID) == 3, "materialized boot-ID count changed")
    require("__EXPECTED_BOOT_ID__" not in materialized, "boot-ID marker remained")
    trigger = materialized.index("__GEMINI_A72_LIVE_TRIGGER_BEGIN__")
    ram = materialized.index("__GEMINI_A72_RAM_COHERENCY_BEGIN__")
    topology = materialized.index("topology=/sys/devices/system/cpu/cpu${cpu}/topology")
    concurrent = materialized.index(BEGIN)
    require(trigger < ram < topology < concurrent, "integrated execution order changed")
    require(materialized.count(BEGIN) == 1 and materialized.count(END) == 2,
            "concurrent boundaries changed")
    require(materialized.count("taskset 100") >= 7,
            "CPU8 bounded work weakened")
    require(materialized.count("taskset 200") >= 7,
            "CPU9 bounded work weakened")
    require(materialized.index("block_mounts=") < materialized.index('of="$FILE8"'),
            "storage gate moved after concurrent write")
    require(materialized.count("mount -o remount,rw /sys") == 1 and
            materialized.count("mount -o remount,ro /sys") == 1,
            "inherited one-shot sysfs trigger remount contract changed")
    require("mount -o remount" not in DEVICE.read_text(encoding="utf-8"),
            "concurrent child gained a remount action")
    for forbidden in (
        "/dev/mmcblk",
        "reboot -f",
        "poweroff",
        "/sys/devices/system/cpu/cpu8/online",
        "/sys/devices/system/cpu/cpu9/online",
    ):
        require(forbidden not in materialized, f"forbidden action appeared: {forbidden}")

    module = load_classifier()
    baseline = passing_fields()
    deltas = module.validate_fields(baseline, BOOT_ID)
    require(deltas == {8: 102, 9: 102}, "positive accounting result changed")
    body = "\n".join(f"{key}={value}" for key, value in baseline.items())
    capture = f"prompt\n{BEGIN}\n{body}\n{END}\nprompt\n"
    with tempfile.TemporaryDirectory(prefix="gemini-a72-concurrent-parser-") as name:
        capture_path = Path(name) / "capture.txt"
        capture_path.write_text(capture, encoding="utf-8")
        parsed = module.fields_from_capture(capture_path)
        require(parsed == baseline, "capture parser changed")

    mutations = (
        ("boot_id", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        ("cpu_online", "0-8"),
        ("block_mounts", "1"),
        ("rounds", "3"),
        ("writer8_processor", "7"),
        ("writer9_affinity", "8"),
        ("writer8_sha256", "0" * 64),
        ("reader9_peer_sha256", "0" * 64),
        ("writer8_status", "11"),
        ("reader9_status", "21"),
        ("cpu8_stat_after", "cpu8 1 0 2 3 0 0 0 0 0 0"),
        ("cleanup_file9", "present"),
        ("device_storage_writes", "present"),
        ("cpu_off_request", "cpu8"),
        ("retry_request", "requested"),
        ("reboot_request", "requested"),
        ("concurrent_result", "fail"),
    )
    for index, (key, value) in enumerate(mutations, 1):
        candidate = dict(baseline)
        candidate[key] = value
        require(rejected(module, candidate), f"mutation {index} was accepted: {key}")

    print("validation=dual-a72-concurrent-multiline-runtime-tools")
    print("positive_fixtures=1")
    print(f"rejected_mutations={len(mutations)}")
    print("execution_order=trigger-topology-ram-concurrent")
    print("device_storage_writes=none")
    print("cpu_off_requests=0")
    print("retries=0")
    print("reboot_requests=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
