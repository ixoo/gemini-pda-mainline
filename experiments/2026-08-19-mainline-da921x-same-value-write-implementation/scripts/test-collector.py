#!/usr/bin/env python3
"""Validate the pins and one-shot ordering of the Gate-6 collector."""

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
        require(match is not None and match.group(1) == digest(path),
                f"collector pin changed: {name}")

    pretrigger = (script_dir / "remote-pretrigger-probe.sh").read_text(encoding="utf-8")
    trigger = (script_dir / "remote-trigger-probe.sh").read_text(encoding="utf-8")
    for probe in (pretrigger, trigger):
        require(probe.count("set -- /sys/bus/i2c/devices/*-0068") == 1,
                "exact DA921x resolver changed")
        require(probe.count("action=$1/same_value_write") == 1,
                "same-value attribute path changed")
    require(pretrigger.count(">\"$action\"") == 0, "pretrigger probe gained a write")
    require(trigger.count("TOKEN=run-same-value-write-20260819-a") == 1,
            "token identity changed")
    require(trigger.count("$BB printf '%s\\n' \"$TOKEN\" >\"$action\"") == 1,
            "token write count changed")
    require(trigger.index('sysfs_mount_during=rw') <
            trigger.index('[ -w "$action" ]') <
            trigger.index("trigger_command_started=yes"),
            "attribute writability check escaped the bounded sysfs window")
    require(trigger.count("trap restore_sysfs EXIT") == 1,
            "sysfs restore exit trap changed")

    anchors = (
        'python3 "$classifier" --pretrigger "$pretrigger" >"$pretrigger_classification"',
        "printf 'pretrigger_durable_before_trigger=yes\\n'",
        'make_command "$trigger_probe"',
        "printf 'trigger_token_attempt_utc=%s\\ntrigger_retry_policy=none\\n'",
        'python3 "$classifier" --pretrigger "$pretrigger" --trigger "$trigger_capture"',
        "printf '/bin/reboot\\n' >\"$command_file\"",
    )
    positions = []
    for anchor in anchors:
        require(text.count(anchor) == 1, f"collector anchor changed: {anchor}")
        positions.append(text.index(anchor))
    require(positions == sorted(positions), "collector ordering changed")
    require(text.count("trigger_netcat_attempts=1") == 1, "trigger attempts changed")
    require(text.count("trigger_retry_policy=none") == 2, "retry closure changed")
    require(text.count("second_write_policy=forbidden") == 1,
            "second-write closure changed")
    require("ask-sudo-password" not in text and "1password" not in text.lower(),
            "interactive credential path leaked")
    require("IdentitiesOnly=yes" in text and "IdentityAgent=none" in text,
            "Gemian SSH key isolation changed")
    require("CANDIDATE_SHA256=b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22"
            in text, "candidate identity changed")

    print("validation=mainline-da921x-same-value-write-collector")
    print("pretrigger_durable_before_trigger=yes")
    print("trigger_attempts=1")
    print("trigger_retries=0")
    print("second_writes=0")
    print("native_reboot_requires_terminal_classification=yes")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
