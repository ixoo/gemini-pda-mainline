#!/usr/bin/env python3
"""Static safety and source-pin tests for the power observer."""

from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
COLLECTOR = HERE / "collect-runtime.sh"
REMOTE = HERE / "remote-observe.sh"
CLASSIFIER = HERE / "classify-observation.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise SystemExit(reason)


def main() -> int:
    collector = COLLECTOR.read_text(encoding="utf-8")
    remote = REMOTE.read_text(encoding="utf-8")
    require(digest(REMOTE) in collector, "remote observer source pin changed")
    require(digest(CLASSIFIER) in collector, "classifier source pin changed")
    require(collector.count("nc -4 -b") == 1, "netcat session count changed")
    require("trigger_session=none" in collector, "trigger exclusion missing")
    require("load_session=none" in collector, "load exclusion missing")
    for forbidden in (
        "/dev/mmcblk", "mount ", "umount ", "reboot ", "poweroff ",
        "/sys/devices/system/cpu/cpu8/online", "/sys/devices/system/cpu/cpu9/online",
    ):
        require(forbidden not in remote, f"remote forbidden action: {forbidden}")
    require(remote.count('sha256sum "$ATAG"') == 1, "ATAG hash count changed")
    require("nvmem_binary_content_read=no" in remote, "NVMEM redaction missing")
    require("calibration_value_output=none" in remote, "calibration redaction missing")
    require("/sys/bus/nvmem/devices/mt6797-atag-calibration*" in remote,
            "NVMEM metadata-only inventory changed")
    subprocess.run([sys.executable, str(HERE / "test-classifier.py")], check=True)
    print("netcat_sessions=1")
    print("device_writes=none")
    print("cpu_or_load_triggers=none")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
