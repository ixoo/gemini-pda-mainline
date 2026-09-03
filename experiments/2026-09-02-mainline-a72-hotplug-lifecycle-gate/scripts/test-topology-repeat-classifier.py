#!/usr/bin/env python3
"""Exercise the topology-repeat classifier's success and rejection paths."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile


CLASSIFIER_SHA256 = "d1b618adce29b853c02ee19d47fa41be1fc5ac32411c34c34552ceadebe4b81f"
SCRIPT = Path(__file__).resolve()
CLASSIFIER = SCRIPT.with_name("classify-topology-repeat-trigger.py")
BOOT_ID = "11111111-2222-3333-4444-555555555555"


def classify(path: Path) -> int:
    return subprocess.run(
        [sys.executable, str(CLASSIFIER), str(path), "--boot-id", BOOT_ID],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode


def main() -> int:
    if hashlib.sha256(CLASSIFIER.read_bytes()).hexdigest() != CLASSIFIER_SHA256:
        raise SystemExit("topology-repeat classifier changed")
    specification = importlib.util.spec_from_file_location("topology_classifier", CLASSIFIER)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)

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
        "",
    ))
    valid = "\n".join(lines)
    mutations = (
        ("operation-ret", "operation_ret=0", "operation_ret=-71"),
        ("online-mask", "cpu_online=0-9", "cpu_online=0-8"),
        ("cluster2", "cpu9_cluster_cpus=8-9", "cpu9_cluster_cpus=9"),
        ("cpu9-entry", "CPU9: Booted secondary processor 0x0000000201 [0x410fd081]\n", "", 1),
        ("binder-completed", "restore_completed=1 completed=1", "restore_completed=1 completed=0"),
        ("load-probe", "load_probe=none", "load_probe=unexpected"),
        ("boot-id", f"boot_id={BOOT_ID}", "boot_id=aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"),
    )
    with tempfile.TemporaryDirectory(prefix="a72-topology-repeat-classifier-") as directory:
        root = Path(directory)
        base = root / "valid.txt"
        base.write_text(valid, encoding="utf-8")
        if classify(base) != 0:
            raise SystemExit("valid topology-repeat fixture was rejected")
        rejected = 0
        for mutation in mutations:
            name, old, new, *limit = mutation
            changed = valid.replace(old, new, limit[0] if limit else -1)
            path = root / f"{name}.txt"
            path.write_text(changed, encoding="utf-8")
            if classify(path) != 0:
                rejected += 1
    if rejected != len(mutations):
        raise SystemExit(
            f"classifier mutation rejection failed: {rejected}/{len(mutations)}"
        )
    print("validation=a72-topology-repeat-classifier-tests")
    print("success_cases=1")
    print(f"mutations_rejected={rejected}")
    print("mutations_accepted=0")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
