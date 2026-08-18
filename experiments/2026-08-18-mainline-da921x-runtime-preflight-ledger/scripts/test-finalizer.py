#!/usr/bin/env python3
"""Validate finalizer pins, no-retrigger closure, and reboot ordering."""

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
    finalizer = script_dir / "finalize-runtime.sh"
    text = finalizer.read_text(encoding="utf-8")
    pins = {
        "RUNTIME_CLASSIFIER_SHA256": script_dir / "classify-runtime.py",
        "CONFIRM_PROBE_SHA256": script_dir / "remote-posttrigger-confirm.sh",
        "FINALIZATION_CLASSIFIER_SHA256": script_dir / "classify-finalization.py",
    }
    for name, path in pins.items():
        match = re.search(rf"^readonly {name}=([0-9a-f]{{64}})$", text, re.MULTILINE)
        require(match is not None, f"finalizer pin missing: {name}")
        require(match.group(1) == digest(path), f"finalizer pin changed: {name}")

    require("run-readonly-preflight-20260818-a" not in text,
            "finalizer must not contain the runtime trigger token")
    require("remote-trigger-probe.sh" not in text,
            "finalizer must not reference the trigger probe")
    require("mount -o remount,rw" not in text,
            "finalizer must not create another writable sysfs window")
    require("SOURCE_MANIFEST_SHA256=e55c548836444b115ecf8bfc39462c3212c8b5fc38a74f7635b6aa25099add5a"
            in text, "attempt-1e capture identity changed")
    require("mainline-da921x-runtime-preflight-attempt-1e-finalize" in text,
            "finalization output identity changed")

    anchors = (
        'python3 "$runtime_classifier" --pretrigger "$source/pretrigger.txt"',
        "printf 'retained_classification_sha256=%s\\n'",
        'python3 "$finalization_classifier"',
        "printf 'second_trigger_requests=0\\nnative_reboot_gate=passed\\n'",
        "printf '/bin/reboot\\n' >\"$command_file\"",
        "printf 'changed_gemian_return_utc=%s\\n'",
    )
    positions = []
    for anchor in anchors:
        require(text.count(anchor) == 1, f"finalizer anchor count changed: {anchor}")
        positions.append(text.index(anchor))
    require(positions == sorted(positions), "finalizer safety ordering changed")
    require(text.count("native_reboot_command_sent=yes") == 1,
            "native reboot attempt count changed")

    print("validation=mainline-da921x-runtime-preflight-finalizer")
    print("retained_capture_pinned=yes")
    print("second_trigger_requests=0")
    print("live_confirmation_before_reboot=yes")
    print("native_reboot_attempts=1")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
