#!/usr/bin/env python3

from __future__ import annotations

import pathlib
import re
import signal
import subprocess
import tempfile
import time


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
REMOTE = SCRIPT_DIR / "remote-load-probe.sh"
HOST = SCRIPT_DIR / "collect.sh"
BOUNDED = SCRIPT_DIR / "bounded-exec.pl"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"error: {message}")


for shell, path in (("sh", REMOTE), ("bash", HOST)):
    subprocess.run([shell, "-n", str(path)], check=True)
subprocess.run(["perl", "-c", str(BOUNDED)], check=True, capture_output=True)

remote = REMOTE.read_text(encoding="utf-8")
host = HOST.read_text(encoding="utf-8")

required_remote = (
    "for stage in 1 2 4 8 10",
    "baseline_samples=5",
    "sample_interval=0.2",
    "cooldown_samples=75",
    "readonly_cpu_limit=50000",
    "readonly_ap_limit=50000",
    "readonly_pmic_limit=60000",
    "readonly_da9214_limit=80000",
    "timeout --signal=TERM --kill-after=1s 3s yes >/dev/null &",
    "kill \"$pid\"",
    "wait \"$pid\"",
    "trap cleanup_all EXIT",
    "trap handle_signal HUP INT PIPE TERM",
    "trap defer_signal HUP INT PIPE TERM",
    "require_hps up_threshold 95",
    "require_hps rush_boost_threshold 98",
    "require_hps num_limit_thermal 0",
    "current_stage=\"preload-$stage\"",
    "preload_gate_sample=1",
    "a72_bracket=stable-off",
    "trigger_attribution=not-run-preexisting-a72",
    "trigger_attribution=\"delayed-after-load-$stage\"",
    "workers_alive_before=%s",
    "workers_alive_after=%s",
    "load_escalation=stopped-after-a72-observation",
    "cpu_online_writes=none",
    "policy_writes=none",
    "partition_access=none",
)
for token in required_remote:
    require(token in remote, f"remote policy token missing: {token}")

for forbidden in (
    "/dev/mem",
    "/dev/i2c",
    "taskset",
    "renice",
    "/proc/ppm/",
    "/proc/cpufreq/",
    "/sys/devices/system/cpu/cpu8/online >",
    "/sys/devices/system/cpu/cpu9/online >",
    "REG_WRITE",
    "reboot",
    "/dev/watchdog",
):
    require(forbidden not in remote, f"forbidden remote token present: {forbidden}")

write_redirection = re.compile(
    r"(?:/proc/hps/|/proc/ppm/|/proc/cpufreq/|/sys/|/dev/mmcblk)[^\n]*[>]"
)
require(write_redirection.search(remote) is None, "state path write redirection present")

required_host = (
    "readonly TARGET=gemini@192.168.1.50",
    "-o IdentitiesOnly=yes",
    "-o IdentityAgent=none",
    "-o StrictHostKeyChecking=yes",
    "GEMINI_OBSERVER_INTERVAL=1 timeout --signal=TERM",
    "timeout --signal=TERM --kill-after=1s ${LOAD_REMOTE_TIMEOUT}s sh -s",
    "perl \"$bounded_exec\" \"$LOAD_HOST_TIMEOUT\" -- ssh",
    "trap host_cleanup EXIT",
    "trap host_signal HUP INT PIPE TERM",
    "trap defer_host_signal HUP INT PIPE TERM",
    "sample_end=1",
    "read-only observer did not span the full load probe",
    "observer_synchronized_before_load=yes",
    "observer_spanned_load_and_cooldown=yes",
    "observer_near_a72_sample=",
    "EXPECTED_OBSERVER_REMOTE_SHA256=",
    "EXPECTED_LOAD_REMOTE_SHA256=",
    "EXPECTED_BOUNDED_EXEC_SHA256=",
)
for token in required_host:
    require(token in host, f"host policy token missing: {token}")

hash_inputs = {
    "EXPECTED_OBSERVER_REMOTE_SHA256": (
        SCRIPT_DIR.parent.parent
        / "2026-07-22-gemian-a72-readonly-discovery"
        / "scripts"
        / "remote-probe.sh"
    ),
    "EXPECTED_LOAD_REMOTE_SHA256": REMOTE,
    "EXPECTED_BOUNDED_EXEC_SHA256": BOUNDED,
}
for variable, path in hash_inputs.items():
    match = re.search(rf"^readonly {variable}=([0-9a-f]{{64}})$", host, re.MULTILINE)
    require(match is not None, f"missing pinned checksum: {variable}")
    actual = subprocess.run(
        ["shasum", "-a", "256", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()[0]
    require(match.group(1) == actual, f"stale pinned checksum: {variable}")

child_program = (
    'trap \'printf terminated >"$1"; exit 0\' TERM; '
    "while :; do sleep 0.1; done"
)
with tempfile.TemporaryDirectory(prefix="gemini-bounded-exec-test-") as temp_dir:
    marker = pathlib.Path(temp_dir) / "timeout-marker"
    completed = subprocess.run(
        [
            "perl",
            str(BOUNDED),
            "1",
            "--",
            "/bin/sh",
            "-c",
            child_program,
            "bounded-child",
            str(marker),
        ],
        timeout=6,
        check=False,
    )
    require(completed.returncode == 124, "bounded helper timeout status is not 124")
    require(marker.read_text(encoding="utf-8") == "terminated", "timeout did not terminate exact child")

    signal_marker = pathlib.Path(temp_dir) / "signal-marker"
    process = subprocess.Popen(
        [
            "perl",
            str(BOUNDED),
            "30",
            "--",
            "/bin/sh",
            "-c",
            child_program,
            "bounded-child",
            str(signal_marker),
        ]
    )
    time.sleep(0.2)
    process.send_signal(signal.SIGTERM)
    signal_status = process.wait(timeout=6)
    require(signal_status == 143, "bounded helper signal status is not 143")
    require(
        signal_marker.read_text(encoding="utf-8") == "terminated",
        "host signal did not terminate exact child",
    )

print("validation=gemian-a72-load-assisted-static")
print("remote_shell_syntax=passed")
print("host_shell_syntax=passed")
print("stages=0,1,2,4,8,10")
print("per-worker-active-deadline_seconds=3-plus-1-kill-grace")
print("load_cleanup=kill-and-wait-exact-child-pids")
print("independent_worker_deadline=3-plus-1-seconds")
print("remote_script_deadline=55-plus-1-seconds")
print("host_children=signal-aware-exact-child-bounds")
print("observer_start_and_span=runtime-gated")
print("collector_inputs=sha256-pinned")
print("bounded_exec_dynamic_timeout=passed")
print("bounded_exec_dynamic_signal=passed")
print("thermal_abort=cpu-50C,ap-50C,pmic-60C,da9214-80C")
print("forbidden_interfaces=absent")
print("device_access=none")
