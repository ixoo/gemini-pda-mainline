#!/usr/bin/env python3
"""Accept the exact transaction fixture and reject unsafe mutations."""

from __future__ import annotations

import base64
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT = Path(__file__).with_name("classify-runtime.py")
BOOT_HASH = "a" * 64
SEQUENCE = (
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0xD7), (0x68, 0xD9), (0x68, 0xD7), (0x68, 0x5D),
    (0x68, 0xD9), (0x68, 0x5E),
)
PERMISSIONS = "00000000,00000000,00000000,00000000,00000000,00000000,00000000,00000000"
MASTERS = "00000000,00000000,00000000,00000000"


def fixture() -> str:
    dmesg = (
        "da921x-observer-v1 event=bound valid=1 identity_reads=14 providers=2 "
        "provider_read_attempts=4 provider_read_completed=4 register_data_writes=0 "
        "buck0_selector=70 buck0_uv=1000000 buck0_enabled=1 "
        "buck1_selector=70 buck1_uv=1000000 buck1_enabled=0\n"
        "input: keyboard-matrix as /devices/platform/keyboard-matrix/input/input0\n"
        "matrix-keypad keyboard-matrix: polling mode, interval 20 ms\n"
    )
    encoded = base64.b64encode(dmesg.encode()).decode()
    status = [
        "handoff=ready probe_attempts=1 init_attempts=1 init_successes=1 "
        "clock_ungated_checks=1 clock_gated_checks=1 clock_validation_failures=0 "
        "runtime_pm_link=1 clock_domains=i2c-appm,ap-dma transfer_attempts=20 "
        "dma_starts=0 nonzero_starts=20 irq_count=20 suspend_checks=0 "
        "resume_checks=0 resume_failures=0",
        "oracle_combined_pointer_reads=20",
        "oracle_primary_pointer_reads=14",
        "oracle_page2_pointer_reads=6",
        "oracle_write_only_messages=0",
        "oracle_register_data_write_messages=0",
        "oracle_other_transfers=0",
        "oracle_other_address_transfers=0",
        "entry_ledger=v1 count=20 capacity=32 overflow=0",
    ]
    for index, (address, pointer) in enumerate(SEQUENCE):
        status.append(
            f"entry{index} n=2 a0={address:02x} f0=0000 l0=1 "
            f"p0={pointer:02x} pv=1 a1={address:02x} f1=0001 l1=1 ret=2 done=1"
        )
    return "\n".join((
        "__I2C6_FWTXN_BEGIN__",
        "kernel_release=7.1.3-gemini-i2c6-fwtxn",
        "architecture=aarch64",
        f"boot_id_sha256={BOOT_HASH}",
        "cmdline=console=ttyS0 maxcpus=8 rdinit=/init",
        "cpu_possible=0-9", "cpu_present=0-9", "cpu_online=0-7", "cpu_offline=8-9",
        "udc_devices=1", "keyboard_matrix_inputs=1", "da921x_i2c_clients=1",
        "block_mounts=0", "attestation_readable=1",
        "__I2C6_FWTXN_ATTESTATION_BEGIN__",
        "enabled=1 transaction_window_enabled=1 captured=1 decision=passed "
        "probe_reset_decision=passed register_state_stable=1 "
        "sample_delay_us=10000..11000 register_writes=0 i2c6_attestation_transfers=0",
        f"sample=0 scp_reset_control=00000000 scp_debug_pc=fffffffe "
        f"devapc_i2c6_permission_raw={PERMISSIONS} master_domain_raw={MASTERS} devapc_control=00000001",
        f"sample=1 scp_reset_control=00000000 scp_debug_pc=fffffffe "
        f"devapc_i2c6_permission_raw={PERMISSIONS} master_domain_raw={MASTERS} devapc_control=00000001",
        "decoded_domain0=0 decoded_domain1=0 required_domain0=0 required_domain1=3",
        "transaction_entry_checks=20 transaction_exit_checks=20 "
        "transaction_last_entry_reset_control=00000000 "
        "transaction_last_exit_reset_control=00000000 transaction_reset_failures=0",
        "__I2C6_FWTXN_ATTESTATION_END__",
        "handoff_state=ready",
        "handoff_status=state=ready reason=late-validation-passed initial_gate=ungated "
        "supplier_bound=yes access_grant=ready transition_attempts=1 enable_successes=1 "
        "disable_count=1 late=passed late_checks=1 faults=0 i2c6_policy=requires-ready",
        "__I2C6_FWTXN_STATUS_BEGIN__", *status, "__I2C6_FWTXN_STATUS_END__",
        "__I2C6_FWTXN_DMESG_BASE64_BEGIN__", encoded,
        "__I2C6_FWTXN_DMESG_BASE64_END__",
        f"post_probe_boot_id_sha256={BOOT_HASH}",
        "__I2C6_FWTXN_END__", "",
    ))


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"mutation anchor changed: {old}")
    return text.replace(old, new)


def run(text: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="gemini-fwtxn-classifier-test.") as raw:
        path = Path(raw) / "capture.txt"
        path.write_text(text, encoding="ascii")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--capture", str(path)],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )


def main() -> None:
    baseline = fixture()
    result = run(baseline)
    if result.returncode or "roadmap_decision=close-B1-proceed-to-B2-design\n" not in result.stdout:
        raise SystemExit(f"baseline rejected:\n{result.stderr}")
    mutations = (
        ("release", "7.1.3-gemini-i2c6-fwtxn", "7.1.3-wrong"),
        ("cpu8", "cpu_online=0-7\ncpu_offline=8-9", "cpu_online=0-8\ncpu_offline=9"),
        ("probe-reset", "sample=1 scp_reset_control=00000000", "sample=1 scp_reset_control=00000001"),
        ("probe-decision", "probe_reset_decision=passed", "probe_reset_decision=failed"),
        ("entry-count", "transaction_entry_checks=20", "transaction_entry_checks=19"),
        ("exit-count", "transaction_exit_checks=20", "transaction_exit_checks=19"),
        ("exit-reset", "transaction_last_exit_reset_control=00000000", "transaction_last_exit_reset_control=00000001"),
        ("reset-failure", "transaction_reset_failures=0", "transaction_reset_failures=1"),
        ("handoff", "handoff_state=ready", "handoff_state=faulted"),
        ("ledger-count", "entry_ledger=v1 count=20", "entry_ledger=v1 count=19"),
        ("ledger-overflow", "capacity=32 overflow=0", "capacity=32 overflow=1"),
        ("write-shape", "oracle_register_data_write_messages=0", "oracle_register_data_write_messages=1"),
        ("pointer", "entry19 n=2 a0=68 f0=0000 l0=1 p0=5e", "entry19 n=2 a0=68 f0=0000 l0=1 p0=5f"),
        ("incomplete", "entry19 n=2 a0=68 f0=0000 l0=1 p0=5e pv=1 a1=68 f1=0001 l1=1 ret=2 done=1",
         "entry19 n=2 a0=68 f0=0000 l0=1 p0=5e pv=1 a1=68 f1=0001 l1=1 ret=-5 done=1"),
        ("changed-boot", f"post_probe_boot_id_sha256={BOOT_HASH}",
         f"post_probe_boot_id_sha256={'b' * 64}"),
    )
    for name, old, new in mutations:
        if run(replace_once(baseline, old, new)).returncode == 0:
            raise SystemExit(f"unsafe mutation accepted: {name}")
    if run(baseline.split("__I2C6_FWTXN_END__", 1)[0]).returncode == 0:
        raise SystemExit("truncated capture accepted")
    print("runtime_classifier_baseline=accepted")
    print(f"unsafe_runtime_mutations_rejected={len(mutations) + 1}")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
