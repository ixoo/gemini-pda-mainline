#!/usr/bin/env python3
"""Exercise exact retained and serviceability classifier outcomes offline."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent


def load_retained():
    spec = importlib.util.spec_from_file_location(
        "clock_entry_retained", SCRIPT_DIR / "classify-retained.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    retained = load_retained()
    assert retained.classify_payload(b"")[:2] == (
        "neither",
        "clock-driver-init-not-reached-or-shared-checkpoint-refused",
    )
    assert retained.classify_payload(retained.DRIVER_INIT)[:2] == (
        "driver-init-only",
        "registration-matching-or-probe-entry-not-established",
    )
    assert retained.classify_payload(retained.DRIVER_INIT + retained.PROBE_ENTER)[:2] == (
        "driver-init-and-probe-enter",
        "clock-probe-entered-failure-at-or-after-first-operation",
    )
    assert retained.classify_payload(retained.PROBE_ENTER)[0] == "rejected-attribution"
    assert retained.classify_payload(retained.DRIVER_INIT * 2)[0] == "rejected-attribution"
    assert retained.classify_payload(retained.PREFIX + b"foreign\n")[0] == (
        "rejected-attribution"
    )

    good = """__CLOCK_BACKEND_ENTRY_RUNTIME_BEGIN__
installed_full_sha256=444ffc4a3631e75d05e567f6304fdd1607695adbd1f3c8b5654714633e6278de
kernel_release=7.1.3-gemini-clock-backend-entry-ledger
architecture=aarch64
boot_id=12345678-1234-1234-1234-123456789abc
uptime_seconds=1.25
cpu_possible=0-9
cpu_present=0-9
cpu_online=0-7
cpu_offline=8-9
cmdline=console=ttyS0 maxcpus=8
model=Planet Computers Gemini PDA (clock backend entry ledger)
device_partition_reads=none
device_storage_writes=none
driver_binding_changes=none
protected_read_request=none
secure_call_request=none
owner_registration_request=none
cpu_admission_request=none
reboot_request=none
__CLOCK_BACKEND_ENTRY_RUNTIME_END__
"""
    with tempfile.TemporaryDirectory() as temporary:
        capture = Path(temporary) / "runtime.txt"
        capture.write_text(good, encoding="utf-8")
        result = subprocess.run(
            ["python3", str(SCRIPT_DIR / "validate-runtime.py"), str(capture)],
            check=True,
            text=True,
            capture_output=True,
        )
        assert "runtime_classification=serviceable-clock-entry-runtime" in result.stdout
        capture.write_text(good.replace("cpu_online=0-7", "cpu_online=0-8"), encoding="utf-8")
        rejected = subprocess.run(
            ["python3", str(SCRIPT_DIR / "validate-runtime.py"), str(capture)],
            check=False,
            text=True,
            capture_output=True,
        )
        assert rejected.returncode == 3
        assert "runtime_classification=rejected-safety" in rejected.stdout

    print("validation=clock-backend-entry-runtime-tools")
    print("retained_positive_outcomes=3")
    print("retained_malformed_outcomes_rejected=3")
    print("serviceability_positive_cases=1")
    print("serviceability_safety_mutations_rejected=1")
    print("device_access=none")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
