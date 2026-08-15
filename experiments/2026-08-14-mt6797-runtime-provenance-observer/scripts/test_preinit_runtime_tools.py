#!/usr/bin/env python3
"""Offline positive and mutation tests for the pre-init runtime toolchain."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent
RUNTIME_VALIDATOR = SCRIPT_DIR / "validate-preinit-runtime.py"
CYCLE_CLASSIFIER = SCRIPT_DIR / "classify-preinit-cycle.py"
PROBE = SCRIPT_DIR / "remote-preinit-runtime-probe.sh"
COLLECTOR = SCRIPT_DIR / "collect-preinit-runtime.sh"
INSTALLER = SCRIPT_DIR / "install-preinit-boot2.sh"
PSTORE_COLLECTOR = SCRIPT_DIR.parents[2] / "scripts" / "collect-device-pstore"
CANDIDATE = "99414cdecc4e031b12b93114b355fb3d44366d6e7b5092cb4f5f9132755d61c7"
MARKER = "GEMINI_DVFSP_PROVENANCE_PREINIT_RECOVERY_20260815"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runtime_validator = load("preinit_runtime_validator_test", RUNTIME_VALIDATOR)
cycle_classifier = load("preinit_cycle_classifier_test", CYCLE_CLASSIFIER)


def snapshot(**changes: str) -> list[str]:
    values = {
        "abi": "1",
        "state": "available",
        "observation_complete": "1",
        "variant_id": "273",
        "observer_generation": "9",
        "table_epoch": "1",
        "calibration_handle": "2",
        "ppm_expected_cluster_count": "3",
        "ppm_cluster_mask": "0x00000007",
        "eem_required_bank_mask": "0x0000003b",
        "eem_calibration_bank_mask": "0x0000003b",
        "table_commit_count": "3",
        "calibration_bank_publish_count": "5",
        "calibration_publish_count": "1",
        "calibration_invalidate_count": "0",
        "owner_handle": "0",
        "transition_handle": "0",
        "coherent_transition_owner": "0",
        "provider": "none",
        "hardware_write": "none",
        "cpu8_cpu9_admission": "closed",
    }
    values.update(changes)
    return [f"{key}={value}" for key, value in values.items()]


def runtime_capture(
    first: list[str] | None = None,
    second: list[str] | None = None,
    **outer_changes: str,
) -> str:
    outer = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": "3.18.79-gemini-provenance-preinit+",
        "architecture": "aarch64",
        "boot_id": "11111111-2222-3333-4444-555555555555",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "state_path": "/sys/kernel/debug/gemini_dvfsp_provenance/state",
        "state_access": "readable",
        "state_mode": "444",
    }
    outer.update(outer_changes)
    first = snapshot() if first is None else first
    second = list(first) if second is None else second
    lines = [runtime_validator.BEGIN]
    lines.extend(f"{key}={value}" for key, value in outer.items())
    lines.append("__GEMINI_PROVENANCE_SNAPSHOT_1_BEGIN__")
    lines.extend(first)
    lines.append("__GEMINI_PROVENANCE_SNAPSHOT_1_END__")
    lines.append("__GEMINI_PROVENANCE_SNAPSHOT_2_BEGIN__")
    lines.extend(second)
    lines.append("__GEMINI_PROVENANCE_SNAPSHOT_2_END__")
    lines.extend(
        (
            "device_partition_reads=none",
            "device_storage_writes=none",
            "hardware_write=none",
            "reboot_request=none",
            runtime_validator.END,
        )
    )
    return "\n".join(lines) + "\n"


def runtime_outcome(text: str) -> tuple[str, str]:
    with tempfile.TemporaryDirectory() as root:
        path = Path(root) / "runtime.txt"
        path.write_text(text)
        try:
            return runtime_validator.classify(path)
        except runtime_validator.Classification as result:
            return result.result, result.reason


def make_pstore_capture(root: Path, console: str, **cycle_changes: str) -> Path:
    capture = root / "capture"
    pstore = capture / "pstore"
    pstore.mkdir(parents=True)
    cycle = {
        "wait_for_cycle": "yes",
        "boot_id_changed": "yes",
        "capture_kernel": "3.18.41+",
        "capture_arch": "aarch64",
        "expected_kernel": "3.18.41+",
    }
    cycle.update(cycle_changes)
    (capture / "cycle.txt").write_text(
        "\n".join(f"{key}={value}" for key, value in cycle.items()) + "\n"
    )
    (capture / "metadata.txt").write_text(
        "kernel=3.18.41+\narchitecture=aarch64\npstore_directory=present\n"
    )
    (pstore / "console-ramoops").write_text(console)
    return capture


def good_console() -> str:
    return (
        "Linux version 3.18.79-gemini-provenance-preinit+\n"
        f"{MARKER} checkpoint=pre-init recovery=armed deadline_seconds=120 "
        "pstore_console=required storage_access=none dvfsp_hardware_write=none "
        "cpu8_cpu9_admission=closed\n"
        f"{MARKER} recovery=executing reset=emergency-restart "
        "storage_access=none dvfsp_hardware_write=none "
        "cpu8_cpu9_admission=closed\n"
    )


def cycle_outcome(console: str, runtime: str | None = None, **cycle_changes: str):
    with tempfile.TemporaryDirectory() as root:
        root_path = Path(root)
        capture = make_pstore_capture(root_path, console, **cycle_changes)
        runtime_path = None
        if runtime is not None:
            runtime_path = root_path / "runtime.txt"
            runtime_path.write_text(runtime)
        try:
            result = cycle_classifier.classify(capture, runtime_path)
            return result["runtime_classification"], result["runtime_reason"]
        except cycle_classifier.Classification as outcome:
            return outcome.result, outcome.reason


def test_runtime_classifier() -> None:
    assert runtime_outcome(runtime_capture())[0] == "success"
    cases = (
        (runtime_capture(kernel_release="wrong"), "rejected-attribution"),
        (runtime_capture(state_access="absent-or-unreadable"), "service-failure"),
        (runtime_capture(first=snapshot(observation_complete="0", state="unavailable")), "inconclusive"),
        (runtime_capture(second=snapshot(observer_generation="10")), "inconclusive"),
        (runtime_capture(first=snapshot(owner_handle="1")), "rejected-safety"),
        (runtime_capture(first=snapshot(state="fault", observation_complete="0")), "rejected-safety"),
        (runtime_capture(cpu_online="0-9"), "rejected-safety"),
    )
    for text, expected in cases:
        assert runtime_outcome(text)[0] == expected


def test_cycle_classifier() -> None:
    assert cycle_outcome(good_console())[0] == "success-preinit-recovery"
    assert cycle_outcome(good_console(), runtime_capture())[0] == "success-runtime-publication"
    checkpoint = good_console().splitlines()[1] + "\n"
    execution = good_console().splitlines()[2] + "\n"
    cases = (
        ("unrelated retained log\n", {}, "service-failure"),
        (good_console().splitlines()[0] + "\n" + checkpoint, {}, "inconclusive"),
        (execution, {}, "rejected-attribution"),
        (good_console().replace("storage_access=none", "storage_access=write", 1), {}, "rejected-safety"),
        (good_console() + checkpoint, {}, "rejected-attribution"),
        (good_console(), {"boot_id_changed": "no"}, "rejected-attribution"),
        (good_console().replace("3.18.79-gemini-provenance-preinit+", "3.18.79-gemini-provenance-wrong+"), {}, "rejected-attribution"),
    )
    for console, changes, expected in cases:
        assert cycle_outcome(console, **changes)[0] == expected


def test_tool_contracts() -> None:
    probe = PROBE.read_text()
    collector = COLLECTOR.read_text()
    installer = INSTALLER.read_text()
    pstore_collector = PSTORE_COLLECTOR.read_text()
    classifier = CYCLE_CLASSIFIER.read_text()
    for text in (probe, collector, installer):
        assert CANDIDATE in text
    assert probe.count('cat "$STATE"') == 2
    for forbidden in ("/dev/mmc", "systemctl", "/sbin/reboot", "poweroff", "shutdown"):
        assert forbidden not in probe
    assert "WAIT_SECONDS=240" in collector
    assert "nc -4 -b" in collector
    assert "device_partition_reads=none" in collector
    assert "runtime_probe_transport=stdin-pipe-no-device-file" in collector
    assert MARKER in classifier and "deadline_seconds=120" in classifier
    assert "--wait-for-cycle" in pstore_collector
    assert "tar -C /sys/fs/pstore -cf - ." in pstore_collector
    for required in (
        "PARTLABEL,TYPE,SIZE,RO,MOUNTPOINT",
        "/dev/disk/by-partlabel/boot2",
        "/dev/mmcblk0p29",
        "blockdev --flushbufs",
        "full-partition checksum mismatch",
        "independent readback byte mismatch",
        "systemctl poweroff",
        "shutdown=confirmed-unreachable",
        "fresh_predecessor_backup=no",
    ):
        assert required in installer, f"installer lacks gate: {required}"
    assert "EXPECTED_PREDECESSOR_SHA256" not in installer
    assert "backup-device-mmc" not in installer
    assert "provenance-preinit-deployment-*" in installer


def main() -> None:
    test_runtime_classifier()
    test_cycle_classifier()
    test_tool_contracts()
    print("validation=preinit-runtime-tools-offline")
    print("direct_runtime_positive=pass")
    print("direct_runtime_mutations_distinguished=7")
    print("retained_cycle_positive_paths=2")
    print("retained_cycle_mutations_distinguished=7")
    print("installer_static_contract=pass")
    print("cpu8_cpu9_admission=closed")


if __name__ == "__main__":
    main()
