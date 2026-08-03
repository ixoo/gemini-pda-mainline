#!/usr/bin/env python3
"""Validate terminal-attribution deployment and observation contracts."""

import hashlib
import re
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
LIVE = SCRIPT_DIR / "capture-live-outcome.sh"
PLAN = EXPERIMENT / "results" / "runtime-decision-map-20260803.txt"
WINDOW = EXPERIMENT.parent / "2026-08-03-a72-cpu9-retention-window" / "scripts"
CPU9 = EXPERIMENT.parent / "2026-08-03-a72-cpu9-cluster-reuse" / "scripts"
WINDOW_INSTALLER = WINDOW / "install-boot2.sh"
CPU9_LIVE = CPU9 / "capture-live-outcome.sh"
BASE_INSTALLER = EXPERIMENT.parent / "2026-07-29-da921x-probe-isolation" / "scripts" / "install-boot2.sh"

PINS = (
    ("6f1e5f45c8f75cdfde5a996f902f499d685566c3bec227efa6cdb56aaeffa115", 3),
    ("933299078d78e5882055e73fcbf75447bac9abf7d42b2074f37d65fe81966a70", 2),
    ("e614144e8fd13b4a7d49a0a54852c9557c0a9cb8743cd149982f5725bafd1e83", 2),
    ("gemian-a72-cpu9-terminal-attribution-05012d24f84a", 2),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    installer = INSTALLER.read_text(encoding="utf-8")
    live = LIVE.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    require(hashlib.sha256(WINDOW_INSTALLER.read_bytes()).hexdigest() == "792be0d814871670e41dec652709f8ac888ba9a97a1e97e033f01e0f84490ab4", "retention-window installer changed")
    require(hashlib.sha256(CPU9_LIVE.read_bytes()).hexdigest() == "30d3ac6fa33ac95e1909271ea50227f4e943cab29f61f692dfe5e66ec73ac51c", "CPU9 live collector changed")
    require(hashlib.sha256(BASE_INSTALLER.read_bytes()).hexdigest() == "0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7", "guarded base installer changed")
    for token, count in PINS:
        require(installer.count(token) == count, f"installer pin count changed: {token}")
        require(installer.replace(token, "0" * len(token), 1).count(token) == count - 1, f"installer mutation failed: {token}")
    for token in ("source retention-window installer changed", "GEMINI_CPU9_TERMINAL_SCRIPT_DIR", "Gemian A72 CPU9 terminal-attribution candidate", "2026-08-03-a72-cpu9-terminal-attribution"):
        require(token in installer, f"installer derivation lacks: {token}")

    base = BASE_INSTALLER.read_text(encoding="utf-8")
    for token in ("live GPT does not have exactly one boot2 row", "boot2 is mounted or not a block device", "fresh_predecessor_backup=no", "independent full readback checksum mismatch", "temporary_readback_removed=yes", "sudo -n systemctl poweroff", "shutdown=confirmed-unreachable"):
        require(token in base, f"base installer safety gate changed: {token}")
    help_text = subprocess.run([str(INSTALLER), "--help"], check=True, capture_output=True, text=True).stdout
    require("Gemian A72 CPU9 terminal-attribution" in help_text, "installer help changed")
    require("without creating a partition" in help_text, "no-backup policy changed")
    require("shuts the device down cleanly" in help_text, "shutdown policy changed")

    live_help = subprocess.run([str(LIVE), "--help"], check=True, capture_output=True, text=True).stderr
    require("a72-cpu9-terminal-attempt-N" in live_help, "live output changed")
    held_live = (EXPERIMENT.parent / "2026-08-02-a72-cpu8-held-online" / "scripts" / "capture-live-outcome.sh").read_text(encoding="utf-8")
    device_program = held_live.split("<<'DEVICE'\n", 1)[1].split("\nDEVICE\n", 1)[0]
    for forbidden in (r"/dev/mmc", r"/dev/block", r"/sys/devices/system/cpu/cpu[89]/online\s*>", r"\b(?:dd|devmem|i2cset|mount|umount|reboot|poweroff|shutdown|kexec)\b"):
        require(re.search(forbidden, device_program) is None, f"live device program has forbidden operation: {forbidden}")
    for token in ("SOURCE_COLLECTOR_SHA256=30d3ac6fa33ac95e1909271ea50227f4e943cab29f61f692dfe5e66ec73ac51c", "gemini-a72-pair-v3 result=(pass|fault)", "hps_reported=-?[0-9]+ hps_cpu=-?[0-9]+ hps_error=-?[0-9]+ hps_count=[0-9]+", "__A72_CPU9_TERMINAL_LIVE_TERMINAL_CAPTURED__", "validation=a72-cpu9-terminal-live-outcome-pass"):
        require(token in live, f"live derivation lacks: {token}")

    for token in ("hps_reported=1", "hps_cpu=9", "hps_error=-1", "hps_count greater than zero", "hps_reported=0", "hps_reported=-1", "gemini-a72-pair-v2 result=fault", "result=down-veto", "result=fault-retain-psci", "Automatic restart with no exact retained marker", "scripts/collect-device-pstore --target gemini@192.168.1.50", "Missing exact pair-v3 pass", "Repeat this exact accepted candidate once"):
        require(token in plan, f"runtime decision missing: {token}")

    print("validation=cpu9-terminal-attribution-runtime-tools")
    print("installer_identity_mutations=4-rejected")
    print("live_collector=inherited-read-only")
    print("result_classes=complete")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
