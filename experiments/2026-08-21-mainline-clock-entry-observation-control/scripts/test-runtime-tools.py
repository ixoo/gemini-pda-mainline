#!/usr/bin/env python3
"""Exercise positive, refusal, attribution, and safety control outcomes."""

from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile


SCRIPT_DIR = Path(__file__).resolve().parent


GOOD = """__CLOCK_ENTRY_CONTROL_RUNTIME_BEGIN__
installed_full_sha256=fc2a9a1a53de1373cf75d14f163a5b9921219996882f58e0b5395595872230bf
kernel_release=7.1.3-gemini-clock-backend-entry-ledger
architecture=aarch64
boot_id=12345678-1234-1234-1234-123456789abc
uptime_seconds=1.25
cpu_possible=0-9
cpu_present=0-9
cpu_online=0-7
cpu_offline=8-9
cmdline=console=ttyS0 maxcpus=8
model=MT6797X
clock_node_status=disabled
driver_registered=yes
clock_platform_device_present=no
ioremap_ram_warning_count=0
device_partition_reads=none
device_storage_writes=none
driver_binding_changes=none
protected_read_request=none
secure_call_request=none
owner_registration_request=none
cpu_admission_request=none
reboot_request=none
__CLOCK_ENTRY_CONTROL_RUNTIME_END__
"""


def run(capture: Path, text: str) -> subprocess.CompletedProcess[str]:
    capture.write_text(text, encoding="utf-8")
    return subprocess.run(
        ["python3", str(SCRIPT_DIR / "validate-runtime.py"), str(capture)],
        check=False,
        text=True,
        capture_output=True,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        capture = Path(temporary) / "runtime.txt"
        passed = run(capture, GOOD)
        assert passed.returncode == 0
        assert "runtime_classification=serviceable-driver-init-control-pass" in passed.stdout

        refused = run(capture, GOOD.replace("driver_registered=yes", "driver_registered=no"))
        assert refused.returncode == 0
        assert "runtime_classification=serviceable-shared-checkpoint-refused" in refused.stdout

        stale_model = run(capture, GOOD.replace("model=MT6797X", "model=Planet Computers Gemini PDA"))
        assert stale_model.returncode == 3
        assert "runtime_classification=rejected-attribution" in stale_model.stdout

        unsafe_cpu = run(capture, GOOD.replace("cpu_online=0-7", "cpu_online=0-8"))
        assert unsafe_cpu.returncode == 3
        assert "runtime_classification=rejected-safety" in unsafe_cpu.stdout

    print("validation=clock-entry-observation-control-runtime-tools")
    print("serviceable_positive_cases=2")
    print("attribution_mutations_rejected=1")
    print("safety_mutations_rejected=1")
    print("device_access=none")
    print("hardware_write=none")


if __name__ == "__main__":
    main()
