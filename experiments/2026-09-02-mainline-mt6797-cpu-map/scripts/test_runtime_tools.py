#!/usr/bin/env python3
"""Validate CPU-map runtime tooling and representative rejected mutations."""

from __future__ import annotations

import hashlib
import re
import subprocess
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
REMOTE = HERE / "remote-bounded-topology-ram.sh"
CLASSIFIER = HERE / "classify-attempt.py"
EXECUTOR = HERE / "execute-attempt.sh"
PARENT_EXECUTOR = HERE / "execute-parent-trigger.sh"
PARENT_CLASSIFIER = HERE / "classify-parent-trigger.py"
COLLECTOR = HERE / "collect-pretrigger.sh"
RECOVERY = HERE / "collect-recovery.sh"
VALIDATOR = HERE / "validate-pretrigger.py"
UPSTREAM_RUNTIME = HERE.parent.parent / "2026-09-02-mainline-dual-a72-ram-coherency" / "scripts"
UPSTREAM_PARENT = HERE.parent.parent / "2026-08-31-mainline-a72-cpu9-same-boot-successor" / "scripts"
BOOT_ID = "11111111-2222-3333-4444-555555555555"
PAYLOAD = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"
BEGIN = "__GEMINI_A72_RAM_COHERENCY_BEGIN__"
END = "__GEMINI_A72_RAM_COHERENCY_END__"


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
    }
    for cpu in range(10):
        if cpu < 4:
            cluster, core = "0-3", str(cpu)
        elif cpu < 8:
            cluster, core = "4-7", str(cpu - 4)
        else:
            cluster, core = "8-9", str(cpu - 8)
        fields.update({
            f"cpu{cpu}_core_id": core,
            f"cpu{cpu}_package_id": "0",
            f"cpu{cpu}_core_siblings": "0-9",
            f"cpu{cpu}_cluster_cpus": cluster,
            f"cpu{cpu}_thread_siblings": str(cpu),
        })
    fields.update({
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
    })
    body = "\n".join(f"{key}={value}" for key, value in fields.items())
    return f"prompt {BEGIN}\n{body}\n{END}\nprompt\n"


def classify(text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="gemini-mt6797-cpu-map-test-") as name:
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
    remote = REMOTE.read_text(encoding="utf-8")
    executor = EXECUTOR.read_text(encoding="utf-8")
    parent_executor = PARENT_EXECUTOR.read_text(encoding="utf-8")
    collector = COLLECTOR.read_text(encoding="utf-8")
    require(
        f"readonly SOURCE_SHA256={digest(UPSTREAM_RUNTIME / 'device-bounded-ram-coherency.sh')}" in remote,
        "remote source-probe pin changed",
    )
    require(
        digest(REMOTE) in executor and digest(CLASSIFIER) in executor,
        "attempt-executor tooling pin changed",
    )
    require(
        digest(PARENT_EXECUTOR) in executor,
        "attempt-executor parent pin changed",
    )
    require(
        f"readonly SOURCE_SHA256={digest(UPSTREAM_RUNTIME / 'execute-attempt.sh')}" in executor,
        "attempt-executor source pin changed",
    )
    require(
        f"readonly SOURCE_SHA256={digest(UPSTREAM_PARENT / 'execute-completion-lock-repair-trigger.sh')}" in parent_executor,
        "parent-executor source pin changed",
    )
    require(digest(VALIDATOR) in parent_executor, "parent validator pin changed")
    require(digest(PARENT_CLASSIFIER) in parent_executor, "parent classifier pin changed")
    require(
        (
            f'("{digest(UPSTREAM_PARENT / "classify-completion-lock-repair-attempt.py")}",\n'
            f'     "{digest(PARENT_CLASSIFIER)}", 1)'
        )
        in parent_executor,
        "parent classifier replacement pair changed",
    )
    require(
        f'SOURCE_SHA256 = "{digest(UPSTREAM_PARENT / "classify-completion-lock-repair-attempt.py")}"'
        in PARENT_CLASSIFIER.read_text(encoding="utf-8"),
        "parent classifier source pin changed",
    )

    with tempfile.TemporaryDirectory(prefix="gemini-mt6797-parent-classifier-") as name:
        temporary = Path(name)
        pretrigger = temporary / "pretrigger.txt"
        trigger = temporary / "trigger.txt"
        pretrigger.write_text(
            "installed_full_sha256="
            "68ec1b7815cab7abae99cbdecabb2f0ba0dd1ddbf26943d652fcedf4d2b4e393\n",
            encoding="utf-8",
        )
        trigger.write_text("", encoding="utf-8")
        retargeted = subprocess.run(
            [
                str(PARENT_CLASSIFIER),
                "--pretrigger",
                str(pretrigger),
                "--trigger",
                str(trigger),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        require(
            "installed-full-candidate-mismatch" not in retargeted.stdout,
            "parent classifier did not retarget the exact CPU-map identity",
        )
        pretrigger.write_text(
            "installed_full_sha256="
            "370ae4d0ab2b7d3ed4d6f935198abbbb76a674698509053d8f0a1e0464774f3e\n",
            encoding="utf-8",
        )
        stale = subprocess.run(
            [
                str(PARENT_CLASSIFIER),
                "--pretrigger",
                str(pretrigger),
                "--trigger",
                str(trigger),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        require(stale.returncode != 0, "parent classifier accepted the retired identity")
        require(
            "runtime_reason=installed-full-candidate-mismatch" in stale.stdout,
            "parent classifier stale-identity rejection changed",
        )
    require(
        f"readonly SOURCE_SHA256={digest(HERE.parent.parent / '2026-08-30-mainline-a72-ready-token-contract-repair/scripts/collect-pretrigger.sh')}" in collector,
        "pre-trigger collector source pin changed",
    )
    recovery = RECOVERY.read_text(encoding="utf-8")
    require(
        f"readonly SOURCE_SHA256={digest(UPSTREAM_PARENT / 'collect-completion-lock-repair-recovery.sh')}" in recovery,
        "recovery collector source pin changed",
    )
    require('mktemp "$source_dir/' in recovery, "recovery derivation lost source-relative dependencies")

    materialized = subprocess.run(
        [str(REMOTE), "--boot-id", BOOT_ID],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout
    require(materialized.count(BOOT_ID) == 1, "materialized boot-ID count changed")
    require("__EXPECTED_BOOT_ID__" not in materialized, "boot-ID marker remained")
    require(
        materialized.count("cluster_cpus_list") == 1
        and "for cpu in 0 1 2 3 4 5 6 7 8 9" in materialized,
        "all-CPU topology collection changed",
    )
    require(materialized.count("taskset 100") >= 5, "CPU8 bounded work weakened")
    require(materialized.count("taskset 200") >= 5, "CPU9 bounded work weakened")
    require(materialized.index("block_mounts=") < materialized.index('of="$FILE8"'), "storage gate moved after write")
    for forbidden in (
        "/dev/mmcblk",
        "mount -o remount",
        "reboot -f",
        "poweroff",
        "/sys/devices/system/cpu/cpu8/online",
        "/sys/devices/system/cpu/cpu9/online",
    ):
        require(forbidden not in materialized, f"forbidden action appeared: {forbidden}")

    baseline = passing_capture()
    accepted = classify(baseline)
    require(accepted.returncode == 0, f"passing fixture rejected: {accepted.stderr}")
    require(
        "runtime_classification=mt6797-4+4+2-topology-and-dual-a72-ram-integrity-pass"
        in accepted.stdout,
        "passing classification changed",
    )
    mutations = (
        mutate_field(baseline, "boot_id", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
        mutate_field(baseline, "cpu_online", "0-8"),
        mutate_field(baseline, "root_source", "/dev/root"),
        mutate_field(baseline, "block_mounts", "1"),
        mutate_field(baseline, "cpu0_cluster_cpus", "0-9"),
        mutate_field(baseline, "cpu4_cluster_cpus", "0-7"),
        mutate_field(baseline, "cpu8_cluster_cpus", "0-9"),
        mutate_field(baseline, "cpu9_core_siblings", "8-9"),
        mutate_field(baseline, "cpu8_core_id", "8"),
        mutate_field(baseline, "cpu9_package_id", "2"),
        mutate_field(baseline, "cpu8_processor", "7"),
        mutate_field(baseline, "file8_reader_cpu9_sha256", "0" * 64),
        mutate_field(baseline, "cpu8_stat_after", "cpu8 1 0 2 3 0 0 0 0 0 0"),
        mutate_field(baseline, "cleanup_file9", "present"),
        mutate_field(baseline, "probe_result", "fail"),
        baseline.replace("cpu8_affinity=8\n", "cpu8_affinity=8\ncpu8_affinity=8\n"),
    )
    for index, mutation in enumerate(mutations, 1):
        rejected = classify(mutation)
        require(rejected.returncode != 0, f"mutation {index} was accepted")
    print("validation=mt6797-cpu-map-runtime-tools")
    print("positive_fixtures=1")
    print(f"mutations_rejected={len(mutations)}")
    print("device_storage_writes=none")
    print("cpu_off_requests=0")
    print("retries=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
