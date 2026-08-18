#!/usr/bin/env python3
"""Exercise the preflight/ledger classifier and its fail-closed boundaries."""

from __future__ import annotations

import base64
from pathlib import Path
import subprocess
import sys
import tempfile


SEQUENCE = (
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x69, 0x05), (0x69, 0x06), (0x69, 0x47), (0x68, 0xD3),
    (0x68, 0x5E), (0x68, 0xD9), (0x68, 0xDA),
    (0x68, 0x5D), (0x68, 0x5E),
    (0x68, 0xD7), (0x68, 0x5D), (0x68, 0xD9), (0x68, 0x5E),
    (0x68, 0x56), (0x68, 0x51), (0x68, 0x5E), (0x68, 0xD9),
    (0x68, 0xDA), (0x68, 0x56), (0x68, 0x51), (0x68, 0x5E),
    (0x68, 0xD9), (0x68, 0xDA),
)


def fixture() -> str:
    status = [
        "handoff=ready transfer_attempts=30 dma_starts=0 nonzero_starts=30 irq_count=30",
        "oracle_combined_pointer_reads=30",
        "oracle_primary_pointer_reads=24",
        "oracle_page2_pointer_reads=6",
        "oracle_write_only_messages=0",
        "oracle_register_data_write_messages=0",
        "oracle_other_transfers=0",
        "oracle_other_address_transfers=0",
        "entry_ledger=v1 count=30 capacity=32 overflow=0",
    ]
    for index, (address, pointer) in enumerate(SEQUENCE):
        status.append(
            f"entry{index} n=2 a0={address:02x} f0=0000 l0=1 "
            f"p0={pointer:02x} pv=1 a1={address:02x} f1=0001 l1=1 ret=2 done=1"
        )
    dmesg = "\n".join((
        "da921x-observer-v1 event=bound valid=1 identity_reads=14 providers=2 "
        "provider_read_attempts=4 provider_read_completed=4 register_data_writes=0 "
        "buck0_selector=70 buck0_uv=1000000 buck0_enabled=1 "
        "buck1_selector=70 buck1_uv=1000000 buck1_enabled=0",
        "da921x-preflight-v1 valid=1 passes=2 stable=1 registration_reads=2 "
        "observer_reads=4 preflight_reads=10 control_a=0x00 v_lock_clear=1 "
        "status_b=0x00 buckb_cont=0x00 vbuckb_a=0x46 vbuckb_b=0x46 "
        "safe_prestate=1 register_data_writes=0",
        "input: keyboard-matrix as /devices/platform/keyboard-matrix/input/input0",
        "matrix-keypad keyboard-matrix: polling mode, interval 20 ms",
        "matrix_platform_device=keyboard-matrix driver=matrix-keypad",
        "matrix_input_name=keyboard-matrix event_node=/dev/input/event0",
    )) + "\n"
    encoded = base64.b64encode(dmesg.encode("utf-8")).decode("ascii")
    return "\n".join((
        "usb-shell# __DA921X_PREFLIGHT_BEGIN__",
        "kernel_release=7.1.3-gemini-da921x-preflight",
        "architecture=aarch64",
        f"boot_id_sha256={'1' * 64}",
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
        "__I2C6_STATUS_BEGIN__",
        *status,
        "__I2C6_STATUS_END__",
        "__DA921X_PREFLIGHT_DMESG_BASE64_BEGIN__",
        encoded,
        "__DA921X_PREFLIGHT_DMESG_BASE64_END__",
        f"post_probe_boot_id_sha256={'1' * 64}",
        "__DA921X_PREFLIGHT_END__",
        "",
    ))


def run(classifier: Path, capture: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(classifier), "--capture", str(capture)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def replace_dmesg(capture: str, old: str, new: str) -> str:
    lines = capture.splitlines()
    begin = lines.index("__DA921X_PREFLIGHT_DMESG_BASE64_BEGIN__")
    end = lines.index("__DA921X_PREFLIGHT_DMESG_BASE64_END__")
    decoded = base64.b64decode("".join(lines[begin + 1:end])).decode("utf-8")
    if decoded.count(old) != 1:
        raise SystemExit(f"dmesg mutation anchor changed: {old}")
    encoded = base64.b64encode(decoded.replace(old, new).encode("utf-8")).decode("ascii")
    lines[begin + 1:end] = [encoded]
    return "\n".join(lines) + "\n"


def main() -> None:
    classifier = Path(__file__).resolve().with_name("classify-runtime.py")
    baseline = fixture()
    mutations = {
        "ledger-pointer": ("capture", "entry29 n=2 a0=68 f0=0000 l0=1 p0=da",
                           "entry29 n=2 a0=68 f0=0000 l0=1 p0=db"),
        "ledger-overflow": ("capture", "capacity=32 overflow=0", "capacity=32 overflow=1"),
        "write-counter": ("capture", "oracle_register_data_write_messages=0",
                          "oracle_register_data_write_messages=1"),
        "v-lock": ("dmesg", "control_a=0x00 v_lock_clear=1",
                   "control_a=0x80 v_lock_clear=0"),
        "phase-count": ("dmesg", "stable=1 registration_reads=2",
                       "stable=1 registration_reads=3"),
        "cpu8-online": ("capture", "cpu_online=0-7\ncpu_offline=8-9",
                        "cpu_online=0-8\ncpu_offline=9"),
        "transfer-result": ("capture",
                            "entry20 n=2 a0=68 f0=0000 l0=1 p0=56 pv=1 a1=68 f1=0001 l1=1 ret=2",
                            "entry20 n=2 a0=68 f0=0000 l0=1 p0=56 pv=1 a1=68 f1=0001 l1=1 ret=-5"),
        "kernel-identity": ("capture", "7.1.3-gemini-da921x-preflight",
                            "7.1.3-gemini-da921x-wrong"),
    }
    with tempfile.TemporaryDirectory(prefix="gemini-preflight-classifier-test.") as raw:
        root = Path(raw)
        capture = root / "capture.txt"
        capture.write_text(baseline, encoding="ascii")
        result = run(classifier, capture)
        if result.returncode != 0:
            raise SystemExit(f"baseline rejected:\n{result.stderr}")
        required = (
            "runtime_classification=success-readonly-preflight-ledger\n",
            "I2C6_sequence=exact-30-of-30\n",
            "Gate6_B3=closed-by-exact-transfer-attribution\n",
            "Gate6_B4=closed-by-stable-safe-preflight\n",
            "result=pass\n",
        )
        if any(line not in result.stdout for line in required):
            raise SystemExit("baseline output lost a required decision field")
        for name, (location, old, new) in mutations.items():
            if location == "capture":
                if baseline.count(old) != 1:
                    raise SystemExit(f"mutation anchor changed: {name}")
                mutated = baseline.replace(old, new)
            else:
                mutated = replace_dmesg(baseline, old, new)
            capture.write_text(mutated, encoding="ascii")
            if run(classifier, capture).returncode == 0:
                raise SystemExit(f"unsafe mutation accepted: {name}")

    print("validation=mainline-da921x-readonly-preflight-runtime-classifier")
    print(f"ledger_entries={len(SEQUENCE)}")
    print(f"unsafe_mutations_rejected={len(mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
