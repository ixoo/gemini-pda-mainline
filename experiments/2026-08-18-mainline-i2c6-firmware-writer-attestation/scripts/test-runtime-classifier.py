#!/usr/bin/env python3
"""Exercise both attestation decisions and reject unsafe capture mutations."""

from __future__ import annotations

import base64
from pathlib import Path
import subprocess
import sys
import tempfile


SCRIPT = Path(__file__).with_name("classify-runtime.py")
BOOT_HASH = "a" * 64
PERMISSIONS = "00000000,00000030,11111111,22222222,33333333,44444444,55555555,66666666"
MASTERS = "01234567,89abcdef,0f0f0f0f,f0f0f0f0"
DMESG = (
    "da921x-observer-v1 event=bound valid=1 identity_reads=14 providers=2 "
    "provider_read_attempts=4 provider_read_completed=4 register_data_writes=0 "
    "buck0_selector=12 buck0_uv=420000 buck0_enabled=1 "
    "buck1_selector=13 buck1_uv=430000 buck1_enabled=1\n"
)


def capture(*, decision: str = "passed", stable: int = 1,
            reset1: str = "00000000", permissions1: str = PERMISSIONS,
            clients: int = 1, dmesg: str = DMESG) -> str:
    encoded = base64.b64encode(dmesg.encode()).decode()
    return f"""__I2C6_FWATT_BEGIN__
kernel_release=7.1.3-gemini-i2c6-fwatt
architecture=aarch64
boot_id_sha256={BOOT_HASH}
cmdline=bootopt=64S3,32N2,64N2 maxcpus=8
cpu_possible=0-9
cpu_present=0-9
cpu_online=0-7
cpu_offline=8-9
udc_devices=1
keyboard_matrix_inputs=1
da921x_i2c_clients={clients}
block_mounts=0
attestation_readable=1
__I2C6_FWATT_SYSFS_BEGIN__
enabled=1 captured=1 decision={decision} register_state_stable={stable} sample_delay_us=10000..11000 register_writes=0 i2c6_transfers=0
sample=0 scp_reset_control=00000000 scp_debug_pc=00000000 devapc_i2c6_permission_raw={PERMISSIONS} master_domain_raw={MASTERS} devapc_control=00000001
sample=1 scp_reset_control={reset1} scp_debug_pc=00000000 devapc_i2c6_permission_raw={permissions1} master_domain_raw={MASTERS} devapc_control=00000001
decoded_domain0=0 decoded_domain1=3 required_domain0=0 required_domain1=3
__I2C6_FWATT_SYSFS_END__
handoff_state=ready
handoff_status=okay
__I2C6_FWATT_DMESG_BASE64_BEGIN__
{encoded}
__I2C6_FWATT_DMESG_BASE64_END__
post_probe_boot_id_sha256={BOOT_HASH}
__I2C6_FWATT_END__
"""


def run(value: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="gemini-fwatt-classifier-test.") as raw:
        path = Path(raw) / "capture.txt"
        path.write_text(value, encoding="ascii")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--capture", str(path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    passed = run(capture())
    require(passed.returncode == 0, passed.stderr)
    require("attestation_decision=passed\n" in passed.stdout,
            "pass decision missing")
    require("roadmap_decision=close-B1-proceed-to-B2\n" in passed.stdout,
            "pass roadmap branch missing")

    failed = run(capture(decision="failed", reset1="00000001",
                         clients=0, dmesg="firmware discriminator failed\n"))
    require(failed.returncode == 0, failed.stderr)
    require("attestation_decision=failed\n" in failed.stdout,
            "failure decision missing")
    require("roadmap_decision=keep-B1-open\n" in failed.stdout,
            "failure roadmap branch missing")

    mutations = (
        capture(decision="passed", reset1="00000001"),
        capture(stable=1, permissions1=PERMISSIONS.replace(
            "66666666", "66666667")),
        capture().replace("register_writes=0", "register_writes=1", 1),
        capture().replace("i2c6_transfers=0", "i2c6_transfers=1", 1),
        capture().replace("decoded_domain1=3", "decoded_domain1=0", 1),
        capture().replace("7.1.3-gemini-i2c6-fwatt", "7.1.3-wrong", 1),
    )
    for index, mutation in enumerate(mutations):
        require(run(mutation).returncode != 0,
                f"unsafe mutation accepted: {index}")

    print("runtime_classifier_pass_fixture=accepted")
    print("runtime_classifier_failure_fixture=accepted-and-B1-kept-open")
    print(f"unsafe_runtime_mutations_rejected={len(mutations)}")
    print("result=pass")


if __name__ == "__main__":
    main()
