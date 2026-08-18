#!/usr/bin/env python3
"""Exercise the retained-capture finalization classifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load fixture module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"mutation anchor changed: {old}")
    return text.replace(old, new)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    runtime_path = script_dir / "classify-runtime.py"
    final_path = script_dir / "classify-finalization.py"
    fixtures = load(script_dir / "test-runtime-classifier.py", "runtime_fixtures")
    boot_hash = fixtures.BOOT_HASH
    confirm = "\n".join((
        "__DA921X_RUNTIME_POSTTRIGGER_CONFIRM_BEGIN__",
        "kernel_release=7.1.3-gemini-da921x-preflight-rt",
        "architecture=aarch64",
        f"boot_id_sha256={boot_hash}",
        "cpu_possible=0-9",
        "cpu_present=0-9",
        "cpu_online=0-7",
        "cpu_offline=8-9",
        "block_mounts=0",
        "sysfs_mount=ro",
        "__RUNTIME_PREFLIGHT_CONFIRM_STATE_BEGIN__",
        *fixtures.state(passed=True),
        "__RUNTIME_PREFLIGHT_CONFIRM_STATE_END__",
        "__I2C6_CONFIRM_STATUS_BEGIN__",
        *fixtures.status(fixtures.PRE_SEQUENCE + fixtures.TRIGGER_SEQUENCE),
        "__I2C6_CONFIRM_STATUS_END__",
        f"post_confirm_boot_id_sha256={boot_hash}",
        "__DA921X_RUNTIME_POSTTRIGGER_CONFIRM_END__",
        "",
    ))

    with tempfile.TemporaryDirectory(prefix="gemini-runtime-finalization-test.") as raw:
        root = Path(raw)
        pre = root / "pretrigger.txt"
        trigger = root / "trigger.txt"
        retained = root / "retained-classification.txt"
        confirm_path = root / "confirm.txt"
        pre.write_text(fixtures.pretrigger_fixture(), encoding="ascii")
        trigger.write_text(fixtures.trigger_fixture(), encoding="ascii")
        runtime = subprocess.run(
            [sys.executable, str(runtime_path), "--pretrigger", str(pre),
             "--trigger", str(trigger)],
            check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        if runtime.returncode != 0:
            raise SystemExit(f"runtime fixture rejected:\n{runtime.stderr}")
        retained.write_text(runtime.stdout, encoding="ascii")

        command = [
            sys.executable, str(final_path),
            "--runtime-classifier", str(runtime_path),
            "--trigger", str(trigger),
            "--retained-classification", str(retained),
            "--confirm", str(confirm_path),
        ]

        def run(value: str) -> subprocess.CompletedProcess[str]:
            confirm_path.write_text(value, encoding="ascii")
            return subprocess.run(command, check=False, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        result = run(confirm)
        if result.returncode != 0 or any(line not in result.stdout for line in (
            "finalization_classification=posttrigger-live-confirmed\n",
            "I2C6_ledger_count=30\n",
            "sysfs_mount=ro\n",
            "native_reboot_permitted=once\n",
            "result=pass\n",
        )):
            raise SystemExit(f"finalization baseline rejected:\n{result.stderr}")

        mutations = (
            ("changed-boot", f"boot_id_sha256={boot_hash}\ncpu_possible=0-9",
             f"boot_id_sha256={'3' * 64}\ncpu_possible=0-9"),
            ("sysfs-rw", "sysfs_mount=ro", "sysfs_mount=rw"),
            ("cpu8-online", "cpu_online=0-7\ncpu_offline=8-9",
             "cpu_online=0-8\ncpu_offline=9"),
            ("state-not-passed", "state=passed attempts=1", "state=idle attempts=1"),
            ("ledger-count", "entry_ledger=v1 count=30", "entry_ledger=v1 count=29"),
            ("register-write", "oracle_register_data_write_messages=0",
             "oracle_register_data_write_messages=1"),
        )
        for name, old, new in mutations:
            if run(replace_once(confirm, old, new)).returncode == 0:
                raise SystemExit(f"unsafe finalization mutation accepted: {name}")
        if run(confirm.split("__I2C6_CONFIRM_STATUS_END__", 1)[0]).returncode == 0:
            raise SystemExit("truncated finalization capture accepted")

    print("validation=mainline-da921x-runtime-preflight-finalization")
    print(f"unsafe_mutations_rejected={len(mutations) + 1}")
    print("second_trigger_requests=0")
    print("native_reboot_requires_live_confirmation=yes")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
