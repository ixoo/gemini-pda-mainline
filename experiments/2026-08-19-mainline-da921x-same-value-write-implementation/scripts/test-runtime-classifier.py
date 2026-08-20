#!/usr/bin/env python3
"""Exercise the same-value runtime classifier and fail-closed mutations."""

from __future__ import annotations

import base64
from pathlib import Path
import subprocess
import sys
import tempfile


RELEASE = "7.1.3-gemini-da921x-same-write"
BOOT = "a" * 64
PRE = (
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0xD7), (0x68, 0xD9), (0x68, 0xD7), (0x68, 0x5D),
    (0x68, 0xD9), (0x68, 0x5E),
)
ACTIONS = (
    ("read", 0x56), ("read", 0x51), ("read", 0x5E), ("read", 0xD9),
    ("read", 0xDA), ("write", 0xDA), ("read", 0xDA), ("read", 0xDA),
    ("read", 0x56), ("read", 0x51), ("read", 0x5E), ("read", 0xD9),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def entry(index: int, kind: str, pointer: int, address: int = 0x68) -> str:
    if kind == "read":
        return (f"entry{index} n=2 a0={address:02x} f0=0000 l0=1 p0={pointer:02x} "
                f"pv=1 p1=00 p1v=0 a1={address:02x} f1=0001 l1=1 ret=2 done=1")
    return (f"entry{index} n=1 a0=68 f0=0000 l0=2 p0=da pv=1 p1=46 p1v=1 "
            "a1=00 f1=0000 l1=0 ret=1 done=1")


def status(action_count: int) -> str:
    reads = sum(kind == "read" for kind, _ in ACTIONS[:action_count])
    writes = int(action_count >= 6)
    total = 20 + action_count
    lines = [
        (f"handoff=ready oracle_combined_pointer_reads={20 + reads} "
         f"oracle_primary_pointer_reads={14 + reads} oracle_page2_pointer_reads=6 "
         f"oracle_write_only_messages={writes} oracle_register_data_write_messages={writes} "
         "oracle_other_transfers=0 oracle_other_address_transfers=0"),
        (f"transaction_entry_checks={total} transaction_exit_checks={total} "
         "transaction_last_entry_reset_control=00000000 "
         "transaction_last_exit_reset_control=00000000 transaction_reset_failures=0"),
        f"entry_ledger=v2 count={total} capacity=32 overflow=0",
    ]
    lines.extend(entry(index, "read", pointer, address)
                 for index, (address, pointer) in enumerate(PRE))
    lines.extend(entry(20 + offset, kind, pointer)
                 for offset, (kind, pointer) in enumerate(ACTIONS[:action_count]))
    return "\n".join(lines)


def state(name: str, actions: int, writes: int, error: int) -> str:
    attempts = int(name != "idle")
    values = (
        "preflight=00,00,00,00,00 immediate=00 delayed=00 poststate=00,00,00,00"
        if name == "idle" else
        "preflight=7b,c1,00,46,46 immediate=46 delayed=46 poststate=7b,c1,00,46"
    )
    return "\n".join((
        f"same_value_write=v1 state={name} attempts={attempts} last_error={error}",
        f"action_transfers={actions} write_attempts={writes}",
        "trigger_token=run-same-value-write-20260819-a",
        values,
        "cpu_online=0-7 cpu_offline=8-9 page_con_accesses=0 consumer_requests=0 "
        "cpu_requests=0 second_writes=0",
    ))


def encoded_dmesg(passed: bool) -> str:
    lines = [
        "da9213 6-0068: da921x-observer-v1 event=bound valid=1 identity_reads=14 "
        "providers=2 provider_read_attempts=4 provider_read_completed=4 register_data_writes=0",
        "input: keyboard-matrix as /devices/platform/keyboard/input/input0",
    ]
    if passed:
        lines.append("da9213 6-0068: same-value Gate-6 action passed with 12 transfers")
    return base64.b64encode(("\n".join(lines) + "\n").encode()).decode()


def pretrigger() -> str:
    return "\n".join((
        "__DA921X_SAME_VALUE_PRETRIGGER_BEGIN__", f"kernel_release={RELEASE}",
        "architecture=aarch64", f"boot_id_sha256={BOOT}",
        "cmdline=console=ttyS0 maxcpus=8", "cpu_possible=0-9", "cpu_present=0-9",
        "cpu_online=0-7", "cpu_offline=8-9", "udc_devices=1",
        "keyboard_matrix_inputs=1", "da921x_i2c_clients=1", "block_mounts=0",
        "pstore_files=0", "__SAME_VALUE_STATE_BEGIN__", state("idle", 0, 0, 0),
        "__SAME_VALUE_STATE_END__", "__I2C6_STATUS_BEGIN__", status(0),
        "__I2C6_STATUS_END__", "__DA921X_SAME_VALUE_DMESG_BASE64_BEGIN__",
        encoded_dmesg(False), "__DA921X_SAME_VALUE_DMESG_BASE64_END__",
        f"post_probe_boot_id_sha256={BOOT}", "__DA921X_SAME_VALUE_PRETRIGGER_END__", "",
    ))


def trigger(name: str, actions: int, writes: int, error: int) -> str:
    passed = name == "passed"
    return "\n".join((
        "__DA921X_SAME_VALUE_TRIGGER_BEGIN__", f"kernel_release={RELEASE}",
        "architecture=aarch64", f"boot_id_sha256={BOOT}",
        "__SAME_VALUE_BEFORE_BEGIN__", state("idle", 0, 0, 0),
        "__SAME_VALUE_BEFORE_END__", "sysfs_mount_before=ro",
        "sysfs_remount_rw_status=0", "sysfs_mount_during=rw",
        "same_value_write_writable=1",
        "trigger_command_started=yes", f"trigger_command_status={0 if passed else 1}",
        "sysfs_remount_ro_status=0", "sysfs_mount_after=ro",
        "__SAME_VALUE_AFTER_BEGIN__", state(name, actions, writes, error),
        "__SAME_VALUE_AFTER_END__", "__I2C6_POSTTRIGGER_STATUS_BEGIN__", status(actions),
        "__I2C6_POSTTRIGGER_STATUS_END__",
        "__DA921X_SAME_VALUE_POSTTRIGGER_DMESG_BASE64_BEGIN__", encoded_dmesg(passed),
        "__DA921X_SAME_VALUE_POSTTRIGGER_DMESG_BASE64_END__",
        f"post_trigger_boot_id_sha256={BOOT}", "__DA921X_SAME_VALUE_TRIGGER_END__", "",
    ))


def run(classifier: Path, pre: Path, capture: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(classifier), "--pretrigger", str(pre)]
    if capture is not None:
        command.extend(("--trigger", str(capture)))
    return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          check=False)


def main() -> None:
    classifier = Path(__file__).with_name("classify-runtime.py")
    with tempfile.TemporaryDirectory(prefix="same-value-runtime-classifier.") as raw:
        root = Path(raw)
        pre = root / "pretrigger.txt"
        success = root / "success.txt"
        pre.write_text(pretrigger(), encoding="ascii")
        success_text = trigger("passed", 12, 1, 0)
        success.write_text(success_text, encoding="ascii")
        result = run(classifier, pre)
        require(result.returncode == 0 and
                "runtime_classification=pretrigger-exact-20\n" in result.stdout,
                f"pretrigger fixture rejected: {result.stderr}")
        result = run(classifier, pre, success)
        require(result.returncode == 0 and
                "runtime_classification=success-same-value-write\n" in result.stdout,
                f"success fixture rejected: {result.stderr}")

        failed = root / "failed.txt"
        failed.write_text(trigger("failed-no-write", 3, 0, -34), encoding="ascii")
        result = run(classifier, pre, failed)
        require(result.returncode == 0 and
                "runtime_classification=terminal-failed-no-write\n" in result.stdout,
                "pre-write terminal fixture rejected")
        faulted = root / "faulted.txt"
        faulted.write_text(trigger("faulted-no-further-i2c", 6, 1, -5), encoding="ascii")
        result = run(classifier, pre, faulted)
        require(result.returncode == 0 and
                "runtime_classification=terminal-faulted-no-further-i2c\n" in result.stdout,
                "post-write terminal fixture rejected")

        mutations = (
            ("payload-byte", "p1=46 p1v=1", "p1=45 p1v=1"),
            ("payload-valid", "p1=46 p1v=1", "p1=46 p1v=0"),
            ("write-count", "write_attempts=1", "write_attempts=0"),
            ("action-count", "action_transfers=12", "action_transfers=11"),
            ("ledger-count", "entry_ledger=v2 count=32", "entry_ledger=v2 count=31"),
            ("cpu-online", "cpu_online=0-7", "cpu_online=0-8"),
            ("token", "run-same-value-write-20260819-a", "wrong-token"),
            ("sysfs-restore", "sysfs_mount_after=ro", "sysfs_mount_after=rw"),
            ("attribute-writable", "same_value_write_writable=1",
             "same_value_write_writable=0"),
            ("second-write", "second_writes=0", "second_writes=1"),
            ("transaction-entry", "transaction_entry_checks=32", "transaction_entry_checks=31"),
            ("transaction-exit", "transaction_exit_checks=32", "transaction_exit_checks=31"),
            ("reset-failure", "transaction_reset_failures=0", "transaction_reset_failures=1"),
        )
        for name, old, new in mutations:
            require(success_text.count(old) >= 1, f"mutation anchor absent: {name}")
            changed = root / f"mutation-{name}.txt"
            changed.write_text(success_text.replace(old, new, 1), encoding="ascii")
            require(run(classifier, pre, changed).returncode != 0,
                    f"runtime mutation escaped: {name}")

    print("validation=mainline-da921x-same-value-runtime-classifier")
    print("pretrigger_fixture=passed")
    print("success_fixture=passed")
    print("prewrite_terminal_fixture=passed")
    print("postwrite_terminal_fixture=passed")
    print(f"mutations_rejected={len(mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
