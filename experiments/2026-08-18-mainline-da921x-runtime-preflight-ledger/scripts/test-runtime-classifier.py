#!/usr/bin/env python3
"""Exercise the two-stage runtime classifier and fail-closed boundaries."""

from __future__ import annotations

import base64
from pathlib import Path
import subprocess
import sys
import tempfile


PRE_SEQUENCE = (
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0x5D), (0x68, 0x5E), (0x68, 0xD7), (0x68, 0x5D),
    (0x68, 0xD9), (0x68, 0x5E),
)
TRIGGER_SEQUENCE = (
    (0x68, 0x56), (0x68, 0x51), (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0x56), (0x68, 0x51), (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
)
BOOT_HASH = "1" * 64
TOKEN = "run-readonly-preflight-20260818-a"


def status(sequence: tuple[tuple[int, int], ...]) -> list[str]:
    primary = sum(address == 0x68 for address, _ in sequence)
    page2 = sum(address == 0x69 for address, _ in sequence)
    lines = [
        f"handoff=ready transfer_attempts={len(sequence)} dma_starts=0 "
        f"nonzero_starts={len(sequence)} irq_count={len(sequence)}",
        f"oracle_combined_pointer_reads={len(sequence)}",
        f"oracle_primary_pointer_reads={primary}",
        f"oracle_page2_pointer_reads={page2}",
        "oracle_write_only_messages=0",
        "oracle_register_data_write_messages=0",
        "oracle_other_transfers=0",
        "oracle_other_address_transfers=0",
        f"entry_ledger=v1 count={len(sequence)} capacity=32 overflow=0",
    ]
    for index, (address, pointer) in enumerate(sequence):
        lines.append(
            f"entry{index} n=2 a0={address:02x} f0=0000 l0=1 "
            f"p0={pointer:02x} pv=1 a1={address:02x} f1=0001 l1=1 ret=2 done=1"
        )
    return lines


def provider_dmesg(*, passed: bool) -> str:
    lines = [
        "da921x-observer-v1 event=bound valid=1 identity_reads=14 providers=2 "
        "provider_read_attempts=4 provider_read_completed=4 register_data_writes=0 "
        "buck0_selector=70 buck0_uv=1000000 buck0_enabled=1 "
        "buck1_selector=70 buck1_uv=1000000 buck1_enabled=0",
        "input: keyboard-matrix as /devices/platform/keyboard-matrix/input/input0",
        "matrix-keypad keyboard-matrix: polling mode, interval 20 ms",
    ]
    if passed:
        lines.append(
            "da921x-preflight-v1 valid=1 passes=2 stable=1 registration_reads=2 "
            "observer_reads=4 preflight_reads=10 control_a=0x00 v_lock_clear=1 "
            "status_b=0x00 buckb_cont=0x00 vbuckb_a=0x46 vbuckb_b=0x46 "
            "safe_prestate=1 register_data_writes=0"
        )
    return "\n".join(lines) + "\n"


def encode(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def state(*, passed: bool) -> list[str]:
    if passed:
        return [
            "runtime_preflight=v1 state=passed attempts=1 last_error=0",
            f"trigger_token={TOKEN}",
            "valid=1 passes=2 stable=1 registration_reads=2 observer_reads=4 preflight_reads=10",
            "control_a=0x00 v_lock_clear=1 status_b=0x00 "
            "buckb_cont=0x00 vbuckb_a=0x46 vbuckb_b=0x46",
            "safe_prestate=1 register_data_writes=0",
        ]
    return [
        "runtime_preflight=v1 state=idle attempts=0 last_error=0",
        f"trigger_token={TOKEN}",
        "valid=0 passes=0 stable=0 registration_reads=2 observer_reads=4 preflight_reads=0",
        "control_a=0x00 v_lock_clear=0 status_b=0x00 "
        "buckb_cont=0x00 vbuckb_a=0x00 vbuckb_b=0x00",
        "safe_prestate=0 register_data_writes=0",
    ]


def pretrigger_fixture() -> str:
    return "\n".join((
        "__DA921X_RUNTIME_PRETRIGGER_BEGIN__",
        "kernel_release=7.1.3-gemini-da921x-preflight-rt",
        "architecture=aarch64",
        f"boot_id_sha256={BOOT_HASH}",
        "cmdline=console=ttyS0 maxcpus=8 rdinit=/init",
        "cpu_possible=0-9",
        "cpu_present=0-9",
        "cpu_online=0-7",
        "cpu_offline=8-9",
        "udc_devices=1",
        "keyboard_matrix_inputs=1",
        "da921x_i2c_clients=1",
        "block_mounts=0",
        "pstore_files=0",
        f"reboot_sha256={'2' * 64}",
        "__RUNTIME_PREFLIGHT_STATE_BEGIN__",
        *state(passed=False),
        "__RUNTIME_PREFLIGHT_STATE_END__",
        "__I2C6_STATUS_BEGIN__",
        *status(PRE_SEQUENCE),
        "__I2C6_STATUS_END__",
        "__DA921X_RUNTIME_DMESG_BASE64_BEGIN__",
        encode(provider_dmesg(passed=False)),
        "__DA921X_RUNTIME_DMESG_BASE64_END__",
        f"post_probe_boot_id_sha256={BOOT_HASH}",
        "__DA921X_RUNTIME_PRETRIGGER_END__",
        "",
    ))


def trigger_fixture() -> str:
    sequence = PRE_SEQUENCE + TRIGGER_SEQUENCE
    return "\n".join((
        "__DA921X_RUNTIME_TRIGGER_BEGIN__",
        "kernel_release=7.1.3-gemini-da921x-preflight-rt",
        "architecture=aarch64",
        f"boot_id_sha256={BOOT_HASH}",
        "__RUNTIME_PREFLIGHT_BEFORE_BEGIN__",
        *state(passed=False),
        "__RUNTIME_PREFLIGHT_BEFORE_END__",
        "trigger_command_started=yes",
        "trigger_command_status=0",
        "__RUNTIME_PREFLIGHT_AFTER_BEGIN__",
        *state(passed=True),
        "__RUNTIME_PREFLIGHT_AFTER_END__",
        "__I2C6_POSTTRIGGER_STATUS_BEGIN__",
        *status(sequence),
        "__I2C6_POSTTRIGGER_STATUS_END__",
        "__DA921X_RUNTIME_POSTTRIGGER_DMESG_BASE64_BEGIN__",
        encode(provider_dmesg(passed=True)),
        "__DA921X_RUNTIME_POSTTRIGGER_DMESG_BASE64_END__",
        f"post_trigger_boot_id_sha256={BOOT_HASH}",
        "__DA921X_RUNTIME_TRIGGER_END__",
        "",
    ))


def run(classifier: Path, pretrigger: Path, trigger: Path | None = None) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(classifier), "--pretrigger", str(pretrigger)]
    if trigger is not None:
        command.extend(("--trigger", str(trigger)))
    return subprocess.run(command, check=False, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"mutation anchor changed: {old}")
    return text.replace(old, new)


def main() -> None:
    classifier = Path(__file__).resolve().with_name("classify-runtime.py")
    pre = pretrigger_fixture()
    trigger = trigger_fixture()
    with tempfile.TemporaryDirectory(prefix="gemini-runtime-preflight-classifier-test.") as raw:
        root = Path(raw)
        pre_path = root / "pretrigger.txt"
        trigger_path = root / "trigger.txt"
        pre_path.write_text(pre, encoding="ascii")
        trigger_path.write_text(trigger, encoding="ascii")
        pre_result = run(classifier, pre_path)
        if pre_result.returncode != 0 or "trigger_permitted=once\n" not in pre_result.stdout:
            raise SystemExit(f"pretrigger baseline rejected:\n{pre_result.stderr}")
        result = run(classifier, pre_path, trigger_path)
        required = (
            "runtime_classification=success-runtime-preflight-ledger\n",
            "I2C6_pretrigger_sequence=exact-20-of-20\n",
            "I2C6_posttrigger_sequence=exact-30-of-30\n",
            "Gate6_B3=closed-by-exact-transfer-attribution\n",
            "Gate6_B4=closed-by-stable-safe-preflight\n",
            "result=pass\n",
        )
        if result.returncode != 0 or any(line not in result.stdout for line in required):
            raise SystemExit(f"posttrigger baseline rejected:\n{result.stderr}")

        mutations = (
            ("pre-count", "pre", "entry_ledger=v1 count=20", "entry_ledger=v1 count=19"),
            ("pre-write", "pre", "oracle_register_data_write_messages=0",
             "oracle_register_data_write_messages=1"),
            ("pre-state", "pre", "state=idle attempts=0", "state=passed attempts=0"),
            ("cpu8", "pre", "cpu_online=0-7\ncpu_offline=8-9", "cpu_online=0-8\ncpu_offline=9"),
            ("trigger-status", "trigger", "trigger_command_status=0", "trigger_command_status=1"),
            ("trigger-repeat", "trigger", "state=passed attempts=1", "state=passed attempts=2"),
            ("post-pointer", "trigger", "entry29 n=2 a0=68 f0=0000 l0=1 p0=da",
             "entry29 n=2 a0=68 f0=0000 l0=1 p0=db"),
            ("post-write", "trigger", "oracle_register_data_write_messages=0",
             "oracle_register_data_write_messages=1"),
            ("unsafe-prestate", "trigger", "safe_prestate=1 register_data_writes=0",
             "safe_prestate=0 register_data_writes=0"),
            ("changed-boot", "trigger", f"post_trigger_boot_id_sha256={BOOT_HASH}",
             f"post_trigger_boot_id_sha256={'3' * 64}"),
        )
        for name, location, old, new in mutations:
            pre_path.write_text(pre if location == "trigger" else replace_once(pre, old, new),
                                encoding="ascii")
            trigger_path.write_text(trigger if location == "pre" else replace_once(trigger, old, new),
                                    encoding="ascii")
            if run(classifier, pre_path, trigger_path).returncode == 0:
                raise SystemExit(f"unsafe mutation accepted: {name}")

        pre_path.write_text(pre, encoding="ascii")
        trigger_path.write_text(trigger.split("__RUNTIME_PREFLIGHT_AFTER_BEGIN__", 1)[0],
                                encoding="ascii")
        if run(classifier, pre_path, trigger_path).returncode == 0:
            raise SystemExit("truncated trigger capture accepted")

    print("validation=mainline-da921x-runtime-preflight-runtime-classifier")
    print(f"pretrigger_entries={len(PRE_SEQUENCE)}")
    print(f"posttrigger_entries={len(PRE_SEQUENCE + TRIGGER_SEQUENCE)}")
    print(f"unsafe_mutations_rejected={len(mutations) + 1}")
    print("trigger_retries=0")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
