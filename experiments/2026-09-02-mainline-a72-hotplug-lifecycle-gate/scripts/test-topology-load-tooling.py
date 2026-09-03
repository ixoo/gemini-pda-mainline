#!/usr/bin/env python3
"""Test topology/load materialization, freshness, and strict classification."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT = Path(__file__).resolve()
HERE = SCRIPT.parent
ROOT = SCRIPT.parents[3]
BUILDER = HERE / "build-topology-load-trigger.sh"
PRETRIGGER = HERE / "validate-topology-load-pretrigger.py"
SOURCE_PRETRIGGER = HERE / "validate-topology-repeat-pretrigger.py"
SOURCE_PRETRIGGER_TEST = HERE / "test-topology-repeat-pretrigger.py"
CLASSIFIER = HERE / "classify-topology-load-trigger.py"
SOURCE_LIFECYCLE = HERE / "classify-topology-repeat-trigger.py"
PROBE_BUILDER = ROOT / "experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/remote-bounded-topology-ram.sh"
PROBE_CLASSIFIER = ROOT / "experiments/2026-09-02-mainline-mt6797-cpu-map/scripts/classify-attempt.py"
BOOT_ID = "22222222-2222-4222-8222-222222222222"
PRIOR_BOOT_ID = "c1bd9a56-919f-4ba1-8404-1287148b334a"
DEPLOYMENT_BOOT_ID = "11111111-1111-4111-8111-111111111111"
PAYLOAD = "52151e7f322f926b64049cdaa1410dc3ea6485525e0624b05813791c219ae933"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load(path: Path, name: str):
    specification = importlib.util.spec_from_file_location(name, path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def lifecycle_fixture() -> str:
    module = load(SOURCE_LIFECYCLE, "topology_lifecycle_classifier")
    lines = [
        module.BEGIN,
        "kernel_release=7.1.3-gemini-a72-hotplug-physical",
        f"boot_id={BOOT_ID}",
        "cpu_online=0-7",
        "cpu_offline=8-9",
        "trigger_commit=yes",
        "token_sha256=dffc3cca86392738e4b247ac21bec30474ef4b909df9cb9d3f92a9118dfa5b8f",
        "trigger_write_status=0",
        "remount_ro_status=0",
        "post_status=state=terminal trigger_consumed=1 trigger_executions=1 operation_ret=0 core_consumed=1 cpu_requests=1 cpu9_requests=1 retries=0",
        "cpu_online=0-9",
        "cpu_offline=",
        module.SYSFS_BEGIN,
    ]
    clusters = {cpu: "0-3" for cpu in range(4)}
    clusters.update({cpu: "4-7" for cpu in range(4, 8)})
    clusters.update({8: "8-9", 9: "8-9"})
    core_ids = (0, 1, 2, 3, 0, 1, 2, 3, 0, 1)
    for cpu in range(10):
        lines.extend((
            f"cpu{cpu}_physical_package_id=0",
            f"cpu{cpu}_core_id={core_ids[cpu]}",
            f"cpu{cpu}_core_siblings=0-9",
            f"cpu{cpu}_cluster_cpus={clusters[cpu]}",
            f"cpu{cpu}_thread_siblings={cpu}",
        ))
    lines.extend((
        module.SYSFS_END,
        "CPU8: Booted secondary processor 0x0000000200 [0x410fd081]",
        "CPU9: Booted secondary processor 0x0000000201 [0x410fd081]",
        "CPU9: Booted secondary processor 0x0000000201 [0x410fd081]",
        module.BINDER,
        "device_storage_reads=none",
        "device_storage_writes=none",
        "load_probe=none",
        "retry_request=none",
        "reboot_request=none",
        module.END,
        "__A72_TOPOLOGY_LOAD_GATE_PASSED__",
    ))
    return "\n".join(lines) + "\n"


def ram_fixture() -> str:
    fields = {
        "boot_id": BOOT_ID,
        "kernel_release": "7.1.3-gemini-a72-hotplug-physical",
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
    return f"__GEMINI_A72_RAM_COHERENCY_BEGIN__\n{body}\n__GEMINI_A72_RAM_COHERENCY_END__\n"


def classify(text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="a72-topology-load-test-") as name:
        capture = Path(name) / "capture.txt"
        capture.write_text(text, encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(CLASSIFIER), str(capture), "--boot-id", BOOT_ID],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )


def main() -> int:
    builder = BUILDER.read_text(encoding="utf-8")
    require(digest(HERE / "build-topology-repeat-trigger.sh") in builder,
            "lifecycle trigger source pin changed")
    require(digest(PROBE_BUILDER) in builder, "RAM probe source pin changed")
    classifier = CLASSIFIER.read_text(encoding="utf-8")
    require(digest(SOURCE_LIFECYCLE) in classifier,
            "lifecycle classifier source pin changed")
    require(digest(PROBE_CLASSIFIER) in classifier,
            "RAM classifier source pin changed")
    pretrigger = PRETRIGGER.read_text(encoding="utf-8")
    require(digest(SOURCE_PRETRIGGER) in pretrigger,
            "pre-trigger validator source pin changed")

    subprocess.run([sys.executable, str(SOURCE_PRETRIGGER_TEST)], check=True)
    validator = load(SOURCE_PRETRIGGER, "topology_repeat_pretrigger")
    status = (
        "GEMINI_A72_ADMISSION_LIVE_V1 state=armed trigger_consumed=0 "
        "trigger_executions=0 operation_ret=-115 core_consumed=0 "
        "cpu_requests=0 cpu9_requests=0 cpu_off_requests=0 retries=0 "
        "binder_snapshot_ret=0 binder_abi=5 lifecycle=0 terminal=0 last_stage=0 "
        "attempted=0 watchdog_armed=0 cpu9_controller_consumed=0 "
        "cpu9_operation_ret=-115 cpu9_attempted=0 cpu9_membership_published=0 "
        "cpu9_cpu_requests=0 cpu9_cpu_off_requests=0 cpu9_retries=0"
    )
    values = {
        "kernel_release": validator.RELEASE,
        "architecture": "aarch64",
        "boot_id": BOOT_ID,
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "controller_bound": "1",
        "binder_bound": "1",
        "platform_state_bound": "1",
        "status_mode": "444",
        "trigger_mode": "200",
        "sysfs_options": "ro,nosuid,nodev,noexec,relatime",
        "record_identity": validator.RECORD_IDENTITY,
        "live_status": status,
    }
    lines = [validator.BEGIN]
    lines.extend(f"{key}={value}" for key, value in values.items())
    lines.extend((validator.LATE_BEGIN, f"[ 1.0] {validator.READY_LINE}", validator.LATE_END))
    for key in ("device_storage_reads", "device_storage_writes", "sysfs_write_request",
                "cpu_admission_request", "cpu_off_request", "retry_request", "reboot_request"):
        lines.append(f"{key}=none")
    lines.append(validator.END)
    good_pretrigger = "\n".join(lines) + "\n"
    deployment = (
        "target_logical_name=boot2\nroot=/dev/mmcblk0p29\n"
        f"candidate_sha256={validator.CANDIDATE}\nreadback_sha256={validator.CANDIDATE}\n"
        "fresh_predecessor_backup=no\ntemporary_readback_removed=yes\n"
        "post_shutdown_reachability=unreachable\nreboot=no\n"
        f"boot_id={DEPLOYMENT_BOOT_ID}\n"
    )
    with tempfile.TemporaryDirectory(prefix="a72-topology-load-pretrigger-") as name:
        root = Path(name)
        capture = root / "capture.txt"
        summary = root / "deployment.txt"
        capture.write_text(good_pretrigger, encoding="utf-8")
        summary.write_text(deployment, encoding="utf-8")
        accepted = subprocess.run(
            [sys.executable, str(PRETRIGGER), str(capture), "--deployment-summary", str(summary)],
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
        require(accepted.returncode == 0, "fresh pre-trigger fixture rejected")
        capture.write_text(good_pretrigger.replace(BOOT_ID, PRIOR_BOOT_ID, 1), encoding="utf-8")
        stale = subprocess.run(
            [sys.executable, str(PRETRIGGER), str(capture), "--deployment-summary", str(summary)],
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
        require(stale.returncode != 0 and "previous-runtime-boot-id" in stale.stdout,
                "previous runtime boot ID was accepted")

    materialized = subprocess.run(
        [str(BUILDER), "--boot-id", BOOT_ID],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    ).stdout
    require(materialized.count(BOOT_ID) == 2, "materialized boot-ID count changed")
    require("__EXPECTED_BOOT_ID__" not in materialized, "boot-ID marker remained")
    require(materialized.count("run-a72-admission-20260828-a") == 1,
            "lifecycle trigger count changed")
    require(materialized.index("__A72_TOPOLOGY_REPEAT_TRIGGER_END__") <
            materialized.index("__A72_TOPOLOGY_LOAD_GATE_PASSED__") <
            materialized.index("__GEMINI_A72_RAM_COHERENCY_BEGIN__"),
            "integrated execution order changed")
    require("for mapping in 0,0,0-3" in materialized and "9,1,8-9" in materialized,
            "device-side exact topology gate changed")
    require(materialized.count('of="$FILE8"') == 1 and materialized.count('of="$FILE9"') == 1,
            "bounded RAM write count changed")
    for forbidden in ("/dev/mmcblk", "reboot -f", "poweroff"):
        require(forbidden not in materialized, f"forbidden action appeared: {forbidden}")

    valid = lifecycle_fixture() + ram_fixture()
    accepted = classify(valid)
    require(accepted.returncode == 0, f"valid integrated fixture rejected: {accepted.stdout}")
    require("runtime_classification=stage18-topology-and-bounded-dual-a72-RAM-pass" in accepted.stdout,
            "integrated success classification changed")
    mutations = (
        valid.replace("operation_ret=0", "operation_ret=-5", 1),
        valid.replace("restore_completed=1 completed=1", "restore_completed=1 completed=0", 1),
        valid.replace("cpu9_cluster_cpus=8-9", "cpu9_cluster_cpus=9", 1),
        valid.replace("__A72_TOPOLOGY_LOAD_GATE_PASSED__", "__A72_TOPOLOGY_LOAD_GATE_REJECTED__"),
        valid.replace("kernel_release=7.1.3-gemini-a72-hotplug-physical",
                      "kernel_release=unexpected", 1),
        valid.replace(f"boot_id={BOOT_ID}", "boot_id=aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", 1),
        valid.replace("root_source=rootfs", "root_source=/dev/root", 1),
        valid.replace("cpu9_processor=9", "cpu9_processor=8", 1),
        valid.replace("file8_reader_cpu9_sha256=" + PAYLOAD,
                      "file8_reader_cpu9_sha256=" + "0" * 64, 1),
        valid.replace("cpu8_stat_after=cpu8 2 0 3 103 0 0 0 0 0 0",
                      "cpu8_stat_after=cpu8 1 0 2 3 0 0 0 0 0 0", 1),
        valid.replace("cleanup_file9=absent", "cleanup_file9=present", 1),
        valid.replace("__GEMINI_A72_RAM_COHERENCY_END__", "", 1),
    )
    rejected = sum(classify(mutation).returncode != 0 for mutation in mutations)
    require(rejected == len(mutations),
            f"integrated mutation rejection changed: {rejected}/{len(mutations)}")
    print("validation=a72-topology-load-tooling")
    print("pretrigger_source_mutations_rejected=8")
    print("prior_runtime_boot_ids_rejected=1")
    print("integrated_success_cases=1")
    print(f"integrated_mutations_rejected={rejected}")
    print("forbidden_actions=absent")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
