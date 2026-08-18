#!/usr/bin/env python3
"""Validate the checksum pins and one-shot ordering of the runtime collector."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    collector = script_dir / "collect-runtime.sh"
    text = collector.read_text(encoding="utf-8")
    pins = {
        "PRETRIGGER_PROBE_SHA256": script_dir / "remote-pretrigger-probe.sh",
        "TRIGGER_PROBE_SHA256": script_dir / "remote-trigger-probe.sh",
        "CLASSIFIER_SHA256": script_dir / "classify-runtime.py",
    }
    for name, path in pins.items():
        match = re.search(rf"^readonly {name}=([0-9a-f]{{64}})$", text, re.MULTILINE)
        require(match is not None, f"collector pin missing: {name}")
        require(match.group(1) == digest(path), f"collector pin changed: {name}")

    for name in ("remote-pretrigger-probe.sh", "remote-trigger-probe.sh"):
        probe = (script_dir / name).read_text(encoding="utf-8")
        require(probe.count("set -- /sys/bus/i2c/devices/*-0068") == 1,
                f"exact symlinked client resolver changed: {name}")
        require("find /sys/bus/i2c/devices -maxdepth 2 -name readonly_preflight" not in probe,
                f"non-symlink-following attribute lookup returned: {name}")
        require(probe.count("preflight=$1/readonly_preflight") == 1,
                f"exact runtime attribute path changed: {name}")
        begin = ("__DA921X_RUNTIME_PRETRIGGER_BEGIN__" if "pretrigger" in name
                 else "__DA921X_RUNTIME_TRIGGER_BEGIN__")
        require(probe.count(f"$BB printf '\\n%s\\n' {begin}") == 1,
                f"prompt-separated opening marker changed: {name}")

    trigger_probe = (script_dir / "remote-trigger-probe.sh").read_text(encoding="utf-8")
    mount_anchors = (
        'require_mount_option "$mount_options" ro || exit 1\n'
        "$BB printf '%s\\n' sysfs_mount_before=ro",
        '$BB mount -o remount,rw /sys',
        '$BB printf \'%s\\n\' "$TOKEN" >"$preflight"',
        'set +e\n$BB mount -o remount,ro /sys\nremount_ro_status=$?',
        '$BB printf \'%s\\n\' sysfs_mount_after=ro',
    )
    positions = []
    for anchor in mount_anchors:
        require(trigger_probe.count(anchor) == 1, f"trigger mount anchor changed: {anchor}")
        positions.append(trigger_probe.index(anchor))
    require(positions == sorted(positions), "trigger mount-window ordering changed")
    require(trigger_probe.count("trap restore_sysfs EXIT") == 1,
            "sysfs restore exit trap changed")
    require(trigger_probe.count("trap handle_signal HUP INT TERM") == 1,
            "sysfs restore signal traps changed")

    anchors = (
        'python3 "$classifier" --pretrigger "$pretrigger" >"$pretrigger_classification"',
        "printf 'pretrigger_durable_before_trigger=yes\\n'",
        'make_command "$trigger_probe"',
        'printf \'trigger_token_attempt_utc=%s\\ntrigger_retry_policy=none\\n\'',
        'python3 "$classifier" --pretrigger "$pretrigger" --trigger "$trigger_capture"',
        'printf \'/bin/reboot\\n\' >"$command_file"',
    )
    positions = []
    for anchor in anchors:
        require(text.count(anchor) == 1, f"collector anchor count changed: {anchor}")
        positions.append(text.index(anchor))
    require(positions == sorted(positions), "collector safety ordering changed")
    require(text.count('trigger_netcat_attempts=1') == 1, "trigger attempt count changed")
    require(text.count('trigger_retry_policy=none') == 1, "trigger retry closure changed")
    require(text.count('native_reboot_command_sent=no') == 2,
            "non-pass reboot closures changed")
    require('CANDIDATE_SHA256=af560eaad69b61239db7980995776b47b1194bb26fe5c8a24d8f1462008ab296'
            in text, "candidate identity changed")
    require('mainline-da921x-runtime-preflight-attempt-1e' in text,
            "private capture identity changed")

    print("validation=mainline-da921x-runtime-preflight-collector")
    print("pretrigger_durable_before_trigger=yes")
    print("trigger_attempts=1")
    print("trigger_retries=0")
    print("native_reboot_requires_posttrigger_pass=yes")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
