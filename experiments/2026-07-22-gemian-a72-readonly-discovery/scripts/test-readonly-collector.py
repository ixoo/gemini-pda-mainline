#!/usr/bin/env python3

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time


SCRIPT_DIR = Path(__file__).resolve().parent
REMOTE = SCRIPT_DIR / "remote-probe.sh"
COLLECT = SCRIPT_DIR / "collect.sh"
BOUNDED_EXEC = SCRIPT_DIR / "bounded-exec.pl"

METADATA_ONLY_PATHS = (
    "/proc/idvfs/dvt_test",
    "/sys/devices/platform/da9214-user/da9214_access",
    "/sys/bus/platform/devices/da9214-user/da9214_access",
    "/sys/kernel/debug/cpuhvfs/dbg_repo",
    "/sys/power/dcm_state",
    "/proc/clkmgr/armbpll_fsel",
    "/proc/clkmgr/armccipll_fsel",
    "/proc/cpufreq/MT_CPU_DVFS_B/cpufreq_volt",
)

TRIPWIRES = {
    "/proc/idvfs/dvt_test": "DVT_TEST_CONTENT_MUST_NOT_BE_READ",
    "/sys/devices/platform/da9214-user/da9214_access": "DA9214_CACHE_MUST_NOT_BE_READ",
    "/sys/bus/platform/devices/da9214-user/da9214_access": "DA9214_BUS_CACHE_MUST_NOT_BE_READ",
    "/sys/kernel/debug/cpuhvfs/dbg_repo": "DBG_REPO_CONTENT_MUST_NOT_BE_READ",
    "/sys/power/dcm_state": "INCOMPLETE_DCM_CONTENT_MUST_NOT_BE_READ",
    "/proc/clkmgr/armbpll_fsel": "B_FSEL_CONTENT_MUST_NOT_BE_READ",
    "/proc/clkmgr/armccipll_fsel": "CCI_FSEL_CONTENT_MUST_NOT_BE_READ",
    "/proc/cpufreq/MT_CPU_DVFS_B/cpufreq_volt": "B_VOLT_SMC_PATH_MUST_NOT_BE_READ",
}


def write_fixture(root: Path, logical_path: str, contents: str) -> None:
    path = root / logical_path.lstrip("/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def assert_static_contract() -> None:
    remote_text = REMOTE.read_text(encoding="utf-8")
    collect_text = COLLECT.read_text(encoding="utf-8")

    subprocess.run(["sh", "-n", str(REMOTE)], check=True)
    subprocess.run(["bash", "-n", str(COLLECT)], check=True)
    subprocess.run(["perl", "-c", str(BOUNDED_EXEC)], check=True, capture_output=True)

    forbidden_tokens = (
        "/dev/mem",
        "/dev/i2c-",
        "devmem",
        "i2cget",
        "i2cset",
        "modprobe",
        "insmod",
        "rmmod",
        "trace_marker",
        "/sys/devices/system/cpu/cpu8/online",
        "/sys/devices/system/cpu/cpu9/online",
    )
    for token in forbidden_tokens:
        assert token not in remote_text, f"forbidden remote token present: {token}"

    for logical_path in METADATA_ONLY_PATHS:
        matching = [line.strip() for line in remote_text.splitlines() if logical_path in line]
        assert matching == [f'metadata_only "{logical_path}"'], matching

    assert "sudo -n env" in collect_text
    assert "GEMINI_OBSERVER_TEST_ROOT" not in collect_text
    assert "BatchMode=yes" in collect_text
    assert "ServerAliveInterval=5" in collect_text
    assert "ServerAliveCountMax=3" in collect_text
    assert "StrictHostKeyChecking=yes" in collect_text
    assert "WarnWeakCrypto=no" in collect_text
    assert "LogLevel=ERROR" in collect_text
    assert "gemini@192.168.1.50" in collect_text
    assert "artifacts/credentials/gemini_ed25519" in collect_text
    assert "artifacts/runtime-captures" in collect_text
    assert "preserving partial evidence" in collect_text
    assert "output must be a new path" in collect_text
    assert "WALL_CLOCK_GRACE_SECONDS=60" in collect_text
    assert "sampling_sleep_seconds=$(((samples - 1) * interval))" in collect_text
    assert 'perl "$bounded_exec" "$wall_timeout_seconds" -- ssh' in collect_text
    assert "b_volt=$(read_flat" not in remote_text
    assert "collector_smc_calls=none" in remote_text


def build_fixture(root: Path, selector: str = "0xd9") -> None:
    fixtures = {
        "/test/uname-r": "3.18.41+\n",
        "/test/uname-m": "aarch64\n",
        "/test/findmnt-root-source": "/dev/mmcblk0p29\n",
        "/proc/sys/kernel/random/boot_id": "11111111-2222-3333-4444-555555555555\n",
        "/proc/cmdline": (
            "console=tty0 androidboot.serialno=SERIAL_TRIPWIRE "
            "androidboot.uniqueno=UNIQUE_TRIPWIRE maxcpus=5\n"
        ),
        "/proc/mounts": "rootfs / rootfs rw 0 0\n",
        "/proc/uptime": "12.34 56.78\n",
        "/sys/devices/system/cpu/possible": "0-9\n",
        "/sys/devices/system/cpu/present": "0-9\n",
        "/sys/devices/system/cpu/online": "0-9\n",
        "/sys/devices/system/cpu/offline": "\n",
        "/sys/class/power_supply/ac/online": "0\n",
        "/sys/class/power_supply/usb/online": "1\n",
        "/sys/class/power_supply/battery/present": "1\n",
        "/sys/class/power_supply/battery/status": "Full\n",
        "/sys/class/power_supply/battery/capacity": "100\n",
        "/sys/class/power_supply/battery/health": "Good\n",
        "/proc/idvfs/idvfs_debug": (
            f"IDVFS debug (log level) = 0. I2C_reg[{selector}] = 0x42.\n"
        ),
        "/proc/cpufreq/MT_CPU_DVFS_B/cpufreq_freq": "845000 KHz\n",
        "/proc/cpufreq/MT_CPU_DVFS_CCI/cpufreq_freq": "533000 KHz\n",
        "/sys/kernel/debug/cpuhvfs/dvfsp_reg": "PCM_TIMER  : 00000001\nSW_RSV0    : 0x2\n",
        "/test/dmesg": "[  10.0] CPU8: Booted secondary processor\n",
    }
    for logical_path, contents in fixtures.items():
        write_fixture(root, logical_path, contents)
    for logical_path, tripwire in TRIPWIRES.items():
        write_fixture(root, logical_path, tripwire + "\n")


def run_fixture(
    root: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GEMINI_OBSERVER_TEST_ROOT": str(root),
            "GEMINI_OBSERVER_SAMPLES": "2",
            "GEMINI_OBSERVER_INTERVAL": "0",
        }
    )
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        ["sh", str(REMOTE)],
        env=env,
        text=True,
        capture_output=True,
        check=True,
    )


def assert_fixture_contract() -> None:
    with tempfile.TemporaryDirectory(prefix="gemian-a72-observer-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        mock_bin = root / "test-bin"
        mock_bin.mkdir()
        findmnt_tripwire = root / "findmnt-was-invoked"
        make_executable(
            mock_bin / "findmnt",
            "#!/bin/sh\n: >\"$FINDMNT_TRIPWIRE\"\nexit 99\n",
        )
        result = run_fixture(
            root,
            {
                "PATH": f"{mock_bin}:{os.environ['PATH']}",
                "FINDMNT_TRIPWIRE": str(findmnt_tripwire),
            },
        )
        output = result.stdout

        assert not findmnt_tripwire.exists(), "fixture invoked host/mock findmnt"
        assert "format=gemian-a72-readonly-discovery-v2" in output
        assert "root_findmnt_source=/dev/mmcblk0p29" in output
        assert "root_proc_mounts_source=rootfs" in output
        assert "SERIAL_TRIPWIRE" not in output
        assert "UNIQUE_TRIPWIRE" not in output
        assert "androidboot.serialno=REDACTED" in output
        assert "androidboot.uniqueno=REDACTED" in output
        assert output.count("sample_begin=") == 2
        assert output.count("mask_bracket=stable-nonatomic") == 2
        assert output.count("da9214_selector=reported-0xd9") == 2
        assert "I2C_reg[0xd9] = 0x42" in output
        assert "b_freq=845000 KHz" in output
        assert "cci_freq=533000 KHz" in output
        assert "PCM_TIMER  : 00000001" in output
        assert "CPU8: Booted secondary processor" in output
        assert "identity_gate=pass" in output
        assert "power_gate=pass" in output
        assert "boot_id_stable_through_capture=yes" in output
        assert "state_changing_writes=none" in output
        assert "da9214_bus_operation=driver-serialized-register-address-read" in output
        assert "collector_smc_calls=none" in output
        assert "cpufreq_volt_content_read=no" in output
        assert "capture_scope=partial-existing-surfaces-only" in output
        for logical_path, tripwire in TRIPWIRES.items():
            assert logical_path in output
            assert tripwire not in output

        write_fixture(
            root,
            "/proc/idvfs/idvfs_debug",
            "IDVFS debug (log level) = 0. I2C_reg[0x5e] = 0x1.\n",
        )
        changed_selector = run_fixture(root).stdout
        assert changed_selector.count("da9214_selector=not-confirmed") == 2
        assert "da9214_selector=reported-0xd9" not in changed_selector


def assert_identity_power_gates() -> None:
    bad_values = (
        ("/test/uname-r", "7.1.3\n"),
        ("/test/uname-m", "arm64\n"),
        ("/test/findmnt-root-source", "/dev/mmcblk0p30\n"),
        ("/proc/mounts", "/dev/mmcblk0p30 / ext4 rw 0 0\n"),
        ("/sys/devices/system/cpu/possible", "0-7\n"),
        ("/sys/devices/system/cpu/present", "0-7\n"),
        ("/proc/sys/kernel/random/boot_id", "malformed\n"),
        ("/sys/class/power_supply/usb/online", "0\n"),
        ("/sys/class/power_supply/battery/present", "0\n"),
        ("/sys/class/power_supply/battery/status", "Discharging\n"),
        ("/sys/class/power_supply/battery/capacity", "99\n"),
        ("/sys/class/power_supply/battery/health", "Unknown\n"),
    )
    for logical_path, bad_value in bad_values:
        with tempfile.TemporaryDirectory(prefix="gemian-a72-gate-") as temp_dir:
            root = Path(temp_dir)
            build_fixture(root)
            write_fixture(root, logical_path, bad_value)
            env = os.environ.copy()
            env.update(
                {
                    "GEMINI_OBSERVER_TEST_ROOT": str(root),
                    "GEMINI_OBSERVER_SAMPLES": "1",
                    "GEMINI_OBSERVER_INTERVAL": "0",
                }
            )
            result = subprocess.run(
                ["sh", str(REMOTE)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode == 3, (logical_path, result)
            assert result.stdout.startswith("failure=gate-"), (
                logical_path,
                result.stdout,
            )
            assert "SERIAL_TRIPWIRE" not in result.stdout
            assert "pre-sample Gemian gate failed" in result.stderr
            expected_root_failure = {
                "/test/findmnt-root-source": "gate-root-findmnt-mismatch",
                "/proc/mounts": "gate-root-proc-mounts-mismatch",
            }.get(logical_path)
            if expected_root_failure:
                assert result.stdout == f"failure={expected_root_failure}\n"

    unavailable_roots = (
        ("/test/findmnt-root-source", "missing", "gate-root-findmnt-unavailable"),
        ("/test/findmnt-root-source", "read-failed", "gate-root-findmnt-unavailable"),
        ("/proc/mounts", "missing", "gate-root-proc-mounts-unavailable"),
        ("/proc/mounts", "read-failed", "gate-root-proc-mounts-unavailable"),
    )
    for logical_path, failure_mode, failure_code in unavailable_roots:
        with tempfile.TemporaryDirectory(prefix="gemian-a72-root-unavailable-") as temp_dir:
            root = Path(temp_dir)
            build_fixture(root)
            fixture_path = root / logical_path.lstrip("/")
            fixture_path.unlink()
            if failure_mode == "read-failed":
                if logical_path == "/test/findmnt-root-source":
                    fixture_path.write_text("read-failed\n", encoding="utf-8")
                else:
                    fixture_path.mkdir()
            env = os.environ.copy()
            env.update(
                {
                    "GEMINI_OBSERVER_TEST_ROOT": str(root),
                    "GEMINI_OBSERVER_SAMPLES": "1",
                    "GEMINI_OBSERVER_INTERVAL": "0",
                }
            )
            result = subprocess.run(
                ["sh", str(REMOTE)],
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode == 3, (logical_path, result)
            assert result.stdout == f"failure={failure_code}\n"
            assert failure_code in result.stderr
            assert "__GEMIAN_A72_IDENTITY__" not in result.stdout

    with tempfile.TemporaryDirectory(prefix="gemian-a72-missing-power-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        (root / "sys/class/power_supply/ac/online").unlink()
        env = os.environ.copy()
        env.update(
            {
                "GEMINI_OBSERVER_TEST_ROOT": str(root),
                "GEMINI_OBSERVER_SAMPLES": "1",
                "GEMINI_OBSERVER_INTERVAL": "0",
            }
        )
        missing_power = subprocess.run(
            ["sh", str(REMOTE)], env=env, text=True, capture_output=True, check=False
        )
        assert missing_power.returncode == 3
        assert missing_power.stdout == "failure=gate-power-unobservable\n"
        assert "gate-power-unobservable" in missing_power.stderr

    with tempfile.TemporaryDirectory(prefix="gemian-a72-stability-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        write_fixture(root, "/test/boot-id-second", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n")
        env = os.environ.copy()
        env.update(
            {
                "GEMINI_OBSERVER_TEST_ROOT": str(root),
                "GEMINI_OBSERVER_SAMPLES": "1",
                "GEMINI_OBSERVER_INTERVAL": "0",
            }
        )
        changed_boot = subprocess.run(
            ["sh", str(REMOTE)], env=env, text=True, capture_output=True, check=False
        )
        assert changed_boot.returncode == 3
        assert changed_boot.stdout == "failure=gate-boot-id-changed\n"
        assert "gate-boot-id-changed" in changed_boot.stderr

        (root / "test/boot-id-second").unlink()
        write_fixture(
            root,
            "/test/power-second",
            "ac=0;usb=0;battery_present=1;battery_status=Full;battery_capacity=100;battery_health=Good\n",
        )
        changed_power = subprocess.run(
            ["sh", str(REMOTE)], env=env, text=True, capture_output=True, check=False
        )
        assert changed_power.returncode == 3
        assert changed_power.stdout == "failure=gate-power-state-changed\n"
        assert "gate-power-state-changed" in changed_power.stderr

        (root / "test/power-second").unlink()
        write_fixture(root, "/test/boot-id-final", "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee\n")
        changed_final = subprocess.run(
            ["sh", str(REMOTE)], env=env, text=True, capture_output=True, check=False
        )
        assert changed_final.returncode == 4
        assert "failure=boot-id-changed-during-capture" in changed_final.stdout
        assert "boot-id-changed-during-capture" in changed_final.stderr


def run_mid_sample_fixture(
    root: Path, *, samples: int = 3
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GEMINI_OBSERVER_TEST_ROOT": str(root),
            "GEMINI_OBSERVER_SAMPLES": str(samples),
            "GEMINI_OBSERVER_INTERVAL": "0",
        }
    )
    return subprocess.run(
        ["sh", str(REMOTE)], env=env, text=True, capture_output=True, check=False
    )


def assert_mid_sample_fail_stop() -> None:
    healthy = (
        "ac=0;usb=1;battery_present=1;battery_status=Full;"
        "battery_capacity=100;battery_health=Good\n"
    )

    with tempfile.TemporaryDirectory(prefix="gemian-a72-mid-power-before-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        write_fixture(
            root,
            "/test/sample-2-power-before",
            healthy.replace("ac=0;usb=1", "ac=1;usb=0"),
        )
        result = run_mid_sample_fixture(root)
        assert result.returncode == 4, result
        assert result.stdout.count("sample_end=") == 1
        assert "failure=sample-2-power-before-state-changed" in result.stdout
        assert "sample-2-power-before-state-changed" in result.stderr
        assert "__GEMIAN_A72_COMPLETE__" not in result.stdout

    with tempfile.TemporaryDirectory(prefix="gemian-a72-mid-power-after-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        write_fixture(
            root,
            "/test/sample-1-power-after",
            healthy.replace("usb=1", "usb=0"),
        )
        result = run_mid_sample_fixture(root)
        assert result.returncode == 4, result
        assert result.stdout.count("sample_end=") == 0
        assert "failure=sample-1-power-after-external-power-unhealthy" in result.stdout
        assert "sample-1-power-after-external-power-unhealthy" in result.stderr
        assert "__GEMIAN_A72_COMPLETE__" not in result.stdout

    with tempfile.TemporaryDirectory(prefix="gemian-a72-mid-read-failed-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        write_fixture(
            root,
            "/test/sample-2-read-failed",
            "/proc/cpufreq/MT_CPU_DVFS_B/cpufreq_freq\n",
        )
        result = run_mid_sample_fixture(root)
        assert result.returncode == 4, result
        assert result.stdout.count("sample_end=") == 1
        assert "failure=read-failed-b_freq" in result.stdout
        assert "read-failed-b_freq" in result.stderr
        assert "sample_end=2" not in result.stdout
        assert "__GEMIAN_A72_COMPLETE__" not in result.stdout

    with tempfile.TemporaryDirectory(prefix="gemian-a72-mid-power-absent-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        write_fixture(
            root,
            "/test/sample-2-power-before",
            healthy.replace("ac=0", "ac=absent-or-unreadable"),
        )
        result = run_mid_sample_fixture(root)
        assert result.returncode == 4, result
        assert result.stdout.count("sample_end=") == 1
        assert "failure=sample-2-power-before-unobservable" in result.stdout
        assert "sample-2-power-before-unobservable" in result.stderr
        assert "__GEMIAN_A72_COMPLETE__" not in result.stdout

    with tempfile.TemporaryDirectory(prefix="gemian-a72-mid-required-absent-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        (root / "proc/uptime").unlink()
        result = run_mid_sample_fixture(root)
        assert result.returncode == 4, result
        assert "failure=required-read-unavailable-uptime_before" in result.stdout
        assert "__GEMIAN_A72_COMPLETE__" not in result.stdout

    with tempfile.TemporaryDirectory(prefix="gemian-a72-context-read-failed-") as temp_dir:
        root = Path(temp_dir)
        build_fixture(root)
        write_fixture(
            root,
            "/test/dump-safe-read-failed",
            "/sys/kernel/debug/cpuhvfs/dvfsp_reg\n",
        )
        result = run_mid_sample_fixture(root)
        assert result.returncode == 4, result
        assert "failure=read-failed-safe-context" in result.stdout
        assert "read-failed-safe-context" in result.stderr
        assert "__GEMIAN_A72_NATURAL_SAMPLES__" not in result.stdout


def make_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def assert_host_wrapper() -> None:
    with tempfile.TemporaryDirectory(prefix="gemian-a72-host-") as temp_dir:
        temp_root = Path(temp_dir).resolve()
        repo = temp_root / "repo"
        scripts = repo / "experiments/2026-07-22-gemian-a72-readonly-discovery/scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(COLLECT, scripts / "collect.sh")
        shutil.copy2(REMOTE, scripts / "remote-probe.sh")
        shutil.copy2(BOUNDED_EXEC, scripts / "bounded-exec.pl")

        (repo / ".gitignore").write_text("/artifacts/\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        identity = repo / "artifacts/credentials/gemini_ed25519"
        identity.parent.mkdir(parents=True)
        identity.write_text("private-test-key\n", encoding="utf-8")
        identity.chmod(0o600)
        private_root = repo / "artifacts/runtime-captures"
        private_root.mkdir(parents=True)
        private_root.chmod(0o700)

        test_home = temp_root / "home"
        known_hosts = test_home / ".ssh/known_hosts"
        known_hosts.parent.mkdir(parents=True)
        known_hosts.write_text("test known host\n", encoding="utf-8")
        known_hosts.chmod(0o600)

        mock_bin = temp_root / "bin"
        mock_bin.mkdir()
        mock_ssh = mock_bin / "ssh"
        make_executable(
            mock_ssh,
            """#!/bin/sh
printf '%s\n' "$*" >"$MOCK_SSH_LOG"
if [ "${MOCK_SSH_BLOCK:-0}" = 1 ]; then
    exec /usr/bin/perl -e '$|=1; print qq(timeout-partial\\n); sleep 30'
fi
while IFS= read -r ignored; do :; done
printf '%s\n' "${MOCK_SSH_OUTPUT:-mock-capture}"
exit "${MOCK_SSH_STATUS:-0}"
""",
        )

        env = os.environ.copy()
        env.update(
            {
                "HOME": str(test_home),
                "PATH": f"{mock_bin}:{env['PATH']}",
                "MOCK_SSH_LOG": str(temp_root / "ssh.log"),
            }
        )
        success = private_root / "gemian-a72-readonly-success.txt"
        result = subprocess.run(
            [
                "bash",
                str(scripts / "collect.sh"),
                "--output",
                str(success),
                "--samples",
                "1",
                "--interval",
                "1",
            ],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert success.read_text(encoding="utf-8") == "mock-capture\n"
        assert success.stat().st_mode & 0o777 == 0o600
        ssh_args = (temp_root / "ssh.log").read_text(encoding="utf-8")
        for required in (
            "-F /dev/null",
            "ServerAliveInterval=5",
            "ServerAliveCountMax=3",
            "StrictHostKeyChecking=yes",
            "WarnWeakCrypto=no",
            "LogLevel=ERROR",
            f"-i {identity}",
            "gemini@192.168.1.50",
        ):
            assert required in ssh_args, required
        assert "state_changing_device_writes=none" in result.stdout
        assert "sampling_sleep_seconds=0" in result.stdout
        assert "wall_timeout_seconds=60" in result.stdout

        target_override = subprocess.run(
            [
                "bash",
                str(scripts / "collect.sh"),
                "--target",
                "other@example.test",
                "--output",
                str(private_root / "gemian-a72-readonly-override.txt"),
            ],
            cwd=repo,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        assert target_override.returncode == 2
        assert "unknown option: --target" in target_override.stderr

        failure = private_root / "gemian-a72-readonly-failure.txt"
        failure_env = env.copy()
        failure_env.update({"MOCK_SSH_STATUS": "42", "MOCK_SSH_OUTPUT": "partial-evidence"})
        failed = subprocess.run(
            ["bash", str(scripts / "collect.sh"), "--output", str(failure)],
            cwd=repo,
            env=failure_env,
            text=True,
            capture_output=True,
            check=False,
        )
        partial = Path(str(failure) + ".partial")
        assert failed.returncode == 42
        assert not failure.exists()
        assert partial.read_text(encoding="utf-8") == "partial-evidence\n"
        assert partial.stat().st_mode & 0o777 == 0o600
        assert "preserving partial evidence" in failed.stderr

        # Test the wrapper/helper/SSH composition without waiting for the
        # production 60-second grace: mutate only the private fixture copy.
        fixture_collect = scripts / "collect.sh"
        fixture_text = fixture_collect.read_text(encoding="utf-8")
        fixture_collect.write_text(
            fixture_text.replace(
                "readonly WALL_CLOCK_GRACE_SECONDS=60",
                "readonly WALL_CLOCK_GRACE_SECONDS=1",
            ),
            encoding="utf-8",
        )
        timeout_output = private_root / "gemian-a72-readonly-timeout.txt"
        timeout_env = env.copy()
        timeout_env["MOCK_SSH_BLOCK"] = "1"
        started = time.monotonic()
        timed = subprocess.run(
            [
                "bash",
                str(fixture_collect),
                "--output",
                str(timeout_output),
                "--samples",
                "1",
                "--interval",
                "1",
            ],
            cwd=repo,
            env=timeout_env,
            text=True,
            capture_output=True,
            check=False,
        )
        elapsed = time.monotonic() - started
        timeout_partial = Path(str(timeout_output) + ".partial")
        assert timed.returncode == 124, timed
        assert elapsed >= 0.9, elapsed
        assert elapsed < 2.5, elapsed
        assert not timeout_output.exists()
        assert timeout_partial.read_text(encoding="utf-8") == "timeout-partial\n"
        assert timeout_partial.stat().st_mode & 0o777 == 0o600
        assert "preserving partial evidence" in timed.stderr


def assert_bounded_exec() -> None:
    status = subprocess.run(
        ["perl", str(BOUNDED_EXEC), "2", "--", "/usr/bin/perl", "-e", "exit 42"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert status.returncode == 42, status
    assert status.stderr == "", status.stderr

    signaled = subprocess.run(
        [
            "perl",
            str(BOUNDED_EXEC),
            "2",
            "--",
            "/usr/bin/perl",
            "-e",
            "kill 15, $$",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert signaled.returncode == 143, signaled
    assert signaled.stderr == "", signaled.stderr

    sentinel = subprocess.Popen(["/bin/sleep", "5"])
    started = time.monotonic()
    try:
        timed = subprocess.run(
            [
                "perl",
                str(BOUNDED_EXEC),
                "1",
                "--",
                "/usr/bin/perl",
                "-e",
                "$|=1; print qq(partial-evidence\\n); sleep 30",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        elapsed = time.monotonic() - started
        assert timed.returncode == 124, timed
        assert timed.stdout == "partial-evidence\n"
        assert timed.stderr == ""
        assert elapsed >= 0.9, elapsed
        assert elapsed < 2.5, elapsed
        assert sentinel.poll() is None, "bounded helper killed an unrelated process"
    finally:
        sentinel.terminate()
        sentinel.wait(timeout=2)


def assert_bounds() -> None:
    with tempfile.TemporaryDirectory(prefix="gemian-a72-observer-bounds-") as temp_dir:
        env = os.environ.copy()
        env.update(
            {
                "GEMINI_OBSERVER_TEST_ROOT": temp_dir,
                "GEMINI_OBSERVER_SAMPLES": "0",
                "GEMINI_OBSERVER_INTERVAL": "0",
            }
        )
        result = subprocess.run(
            ["sh", str(REMOTE)], env=env, text=True, capture_output=True, check=False
        )
        assert result.returncode == 2
        assert "between 1 and 900" in result.stderr

        env["GEMINI_OBSERVER_SAMPLES"] = "900"
        env["GEMINI_OBSERVER_INTERVAL"] = "2"
        duration = subprocess.run(
            ["sh", str(REMOTE)], env=env, text=True, capture_output=True, check=False
        )
        assert duration.returncode == 2
        assert "duration exceeds 900 seconds" in duration.stderr


def main() -> None:
    assert_static_contract()
    assert_fixture_contract()
    assert_identity_power_gates()
    assert_mid_sample_fail_stop()
    assert_host_wrapper()
    assert_bounded_exec()
    assert_bounds()
    print("readonly collector tests: PASS")


if __name__ == "__main__":
    main()
