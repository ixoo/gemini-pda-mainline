#!/usr/bin/env python3
"""Validate bounded-coherency tooling and representative rejected mutations."""

from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEVICE = HERE / "device-bounded-ram-coherency.sh"
REMOTE = HERE / "remote-bounded-ram-coherency.sh"
CLASSIFIER = HERE / "classify-attempt.py"
EXECUTOR = HERE / "execute-attempt.sh"
COLLECTOR = HERE / "collect-pretrigger.sh"
RECOVERY = HERE / "collect-recovery.sh"
PARENT = HERE.parent.parent / "2026-08-31-mainline-a72-cpu9-same-boot-successor" / "scripts"
BOOT_ID = "11111111-2222-3333-4444-555555555555"
PAYLOAD = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def passing_capture() -> str:
    fields = {
        "boot_id": BOOT_ID,
        "kernel_release": "7.1.3-gemini-cpu9-progress",
        "cpu_online": "0-9",
        "cpu_offline": "",
        "root_entries": "1",
        "root_source": "rootfs",
        "root_fstype": "rootfs",
        "run_mount_entries": "0",
        "block_mounts": "0",
        "cpu8_core_id": "0",
        "cpu8_package_id": "2",
        "cpu8_core_siblings": "8-9",
        "cpu8_thread_siblings": "8",
        "cpu9_core_id": "1",
        "cpu9_package_id": "2",
        "cpu9_core_siblings": "8-9",
        "cpu9_thread_siblings": "9",
        "cpu8_affinity": "8",
        "cpu9_affinity": "9",
        "cpu8_processor": "8",
        "cpu9_processor": "9",
        "cpu8_stat_before": "cpu8 1 0 2 3 0 0 0 0 0 0",
        "cpu9_stat_before": "cpu9 1 0 2 3 0 0 0 0 0 0",
        "source_cpu8_sha256": PAYLOAD,
        "source_cpu9_sha256": PAYLOAD,
        "file8_size": "1914704",
        "file8_writer_cpu8_sha256": PAYLOAD,
        "file8_reader_cpu9_sha256": PAYLOAD,
        "file9_size": "1914704",
        "file9_writer_cpu9_sha256": PAYLOAD,
        "file9_reader_cpu8_sha256": PAYLOAD,
        "cpu8_stat_after": "cpu8 2 0 3 103 0 0 0 0 0 0",
        "cpu9_stat_after": "cpu9 2 0 3 103 0 0 0 0 0 0",
        "cleanup_file8": "absent",
        "cleanup_file9": "absent",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "cpu_off_request": "none",
        "retry_request": "none",
        "reboot_request": "none",
        "probe_result": "pass",
    }
    body = "\n".join(f"{key}={value}" for key, value in fields.items())
    return f"prompt {BEGIN}\n{body}\n{END}\nprompt\n"


BEGIN = "__GEMINI_A72_RAM_COHERENCY_BEGIN__"
END = "__GEMINI_A72_RAM_COHERENCY_END__"


def classify(text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="gemini-a72-coherency-test-") as name:
        capture = Path(name) / "capture.txt"
        capture.write_text(text, encoding="utf-8")
        return subprocess.run(
            [str(CLASSIFIER), "--capture", str(capture), "--boot-id", BOOT_ID],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


def mutate_field(text: str, key: str, value: str) -> str:
    pattern = re.compile(rf"(?m)^{re.escape(key)}=.*$")
    changed, count = pattern.subn(f"{key}={value}", text)
    require(count == 1, f"fixture field count changed: {key}")
    return changed


def main() -> int:
    device = DEVICE.read_text(encoding="utf-8")
    remote = REMOTE.read_text(encoding="utf-8")
    executor = EXECUTOR.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    recovery = RECOVERY.read_text(encoding="utf-8")
    require(
        f"readonly TEMPLATE_SHA256={digest(DEVICE)}" in remote,
        "remote template pin changed",
    )
    require(
        f"readonly REMOTE_WRAPPER_SHA256={digest(REMOTE)}" in executor,
        "executor remote-wrapper pin changed",
    )
    require(
        f"readonly CLASSIFIER_SHA256={digest(CLASSIFIER)}" in executor,
        "executor classifier pin changed",
    )
    source_pins = (
        (collector, PARENT / "collect-completion-lock-repair-pretrigger.sh"),
        (executor, PARENT / "execute-completion-lock-repair-trigger.sh"),
        (recovery, PARENT / "collect-completion-lock-repair-recovery.sh"),
    )
    for wrapper, source in source_pins:
        require(
            f"SOURCE_SHA256={digest(source)}" in wrapper
            or f"SOURCE_EXECUTOR_SHA256={digest(source)}" in wrapper,
            f"source pin changed: {source.name}",
        )
        require(
            'mktemp "$source_dir/' in wrapper,
            f"derived wrapper would lose source-relative dependencies: {source.name}",
        )
    require(
        collector.count("a72-dual-ram-coherency-attempt-1") == 2,
        "pre-trigger namespace contract changed",
    )
    require(
        recovery.count("a72-dual-ram-coherency-recovery-attempt-1") == 2,
        "recovery namespace contract changed",
    )
    materialized = subprocess.run(
        [str(REMOTE), "--boot-id", BOOT_ID],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout
    require(materialized.count(BOOT_ID) == 1, "materialized boot-ID count changed")
    require("__EXPECTED_BOOT_ID__" not in materialized, "boot-ID marker remained")
    require(materialized.count("taskset 100") >= 5, "CPU8 bounded work count weakened")
    require(materialized.count("taskset 200") >= 5, "CPU9 bounded work count weakened")
    require(device.index("block_mounts=") < device.index("of=\"$FILE8\""), "storage gate moved after write")
    for forbidden in (
        "/dev/mmcblk",
        "mount -o remount",
        "reboot -f",
        "poweroff",
        "/sys/devices/system/cpu/cpu8/online",
        "/sys/devices/system/cpu/cpu9/online",
    ):
        require(forbidden not in device, f"forbidden device action appeared: {forbidden}")

    baseline = passing_capture()
    accepted = classify(baseline)
    require(accepted.returncode == 0, f"passing fixture rejected: {accepted.stderr}")
    require(
        "runtime_classification=dual-a72-ram-integrity-pass" in accepted.stdout,
        "passing classification changed",
    )
    mutations = (
        mutate_field(baseline, "boot_id", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        mutate_field(baseline, "cpu_online", "0-8"),
        mutate_field(baseline, "root_source", "/dev/root"),
        mutate_field(baseline, "block_mounts", "1"),
        mutate_field(baseline, "cpu8_processor", "7"),
        mutate_field(baseline, "file8_reader_cpu9_sha256", "0" * 64),
        mutate_field(baseline, "cpu9_package_id", "3"),
        mutate_field(baseline, "cpu8_stat_after", "cpu8 1 0 2 3 0 0 0 0 0 0"),
        mutate_field(baseline, "cleanup_file9", "present"),
        mutate_field(baseline, "probe_result", "fail"),
        baseline.replace("cpu8_affinity=8\n", "cpu8_affinity=8\ncpu8_affinity=8\n"),
    )
    for index, mutation in enumerate(mutations, 1):
        rejected = classify(mutation)
        require(rejected.returncode != 0, f"mutation {index} was accepted")
    print("validation=dual-a72-bounded-ram-coherency-runtime-tools")
    print("positive_fixtures=1")
    print(f"mutations_rejected={len(mutations)}")
    print("device_storage_writes=none")
    print("cpu_off_requests=0")
    print("retries=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
