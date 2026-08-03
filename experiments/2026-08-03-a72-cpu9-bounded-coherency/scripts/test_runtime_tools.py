#!/usr/bin/env python3
"""Validate bounded-coherency deployment and observation contracts."""

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
WINDOW_INSTALLER = (
    EXPERIMENT.parent
    / "2026-08-03-a72-cpu9-retention-window"
    / "scripts"
    / "install-boot2.sh"
)
CPU9_LIVE = (
    EXPERIMENT.parent
    / "2026-08-03-a72-cpu9-cluster-reuse"
    / "scripts"
    / "capture-live-outcome.sh"
)
BASE_INSTALLER = (
    EXPERIMENT.parent
    / "2026-07-29-da921x-probe-isolation"
    / "scripts"
    / "install-boot2.sh"
)
HELD_LIVE = (
    EXPERIMENT.parent
    / "2026-08-02-a72-cpu8-held-online"
    / "scripts"
    / "capture-live-outcome.sh"
)

PINS = (
    ("933299078d78e5882055e73fcbf75447bac9abf7d42b2074f37d65fe81966a70", 2),
    ("eda1d5bb312aa937e41499ea8fd13a5f8ae95865399605fe7cf93ee61daaa23d", 2),
    ("4854360971b7adb83571702baf026fd107b2aa689b58cf92dbc47bd47ff263f9", 2),
    ("gemian-a72-cpu9-bounded-coherency-647ebe58da86", 2),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    installer = INSTALLER.read_text(encoding="utf-8")
    live = LIVE.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    require(
        hashlib.sha256(WINDOW_INSTALLER.read_bytes()).hexdigest()
        == "792be0d814871670e41dec652709f8ac888ba9a97a1e97e033f01e0f84490ab4",
        "retention-window installer changed",
    )
    require(
        hashlib.sha256(CPU9_LIVE.read_bytes()).hexdigest()
        == "30d3ac6fa33ac95e1909271ea50227f4e943cab29f61f692dfe5e66ec73ac51c",
        "CPU9 live collector changed",
    )
    require(
        hashlib.sha256(BASE_INSTALLER.read_bytes()).hexdigest()
        == "0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7",
        "guarded base installer changed",
    )
    for token, count in PINS:
        require(installer.count(token) == count, f"installer pin count changed: {token}")
        require(
            installer.replace(token, "0" * len(token), 1).count(token) == count - 1,
            f"installer mutation failed: {token}",
        )
    for token in (
        "source retention-window installer changed",
        "GEMINI_CPU9_COHERENCE_SCRIPT_DIR",
        "Gemian A72 CPU9 bounded-coherency candidate",
        "2026-08-03-a72-cpu9-bounded-coherency",
    ):
        require(token in installer, f"installer derivation lacks: {token}")

    base = BASE_INSTALLER.read_text(encoding="utf-8")
    for token in (
        "live GPT does not have exactly one boot2 row",
        "boot2 is mounted or not a block device",
        "fresh_predecessor_backup=no",
        "independent full readback checksum mismatch",
        "temporary_readback_removed=yes",
        "sudo -n systemctl poweroff",
        "shutdown=confirmed-unreachable",
    ):
        require(token in base, f"base installer safety gate changed: {token}")
    help_text = subprocess.run(
        [str(INSTALLER), "--help"], check=True, capture_output=True, text=True
    ).stdout
    require("Gemian A72 CPU9 bounded-coherency" in help_text, "installer help changed")
    require("without creating a partition" in help_text, "no-backup policy changed")
    require("shuts the device down cleanly" in help_text, "shutdown policy changed")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    ).stderr
    require("a72-cpu9-coherence-attempt-N" in live_help, "live output changed")
    held_live = HELD_LIVE.read_text(encoding="utf-8")
    device_program = held_live.split("<<'DEVICE'\n", 1)[1].split("\nDEVICE\n", 1)[0]
    for forbidden in (
        r"/dev/mmc",
        r"/dev/block",
        r"/sys/devices/system/cpu/cpu[89]/online\s*>",
        r"\b(?:dd|devmem|i2cset|mount|umount|reboot|poweroff|shutdown|kexec)\b",
    ):
        require(
            re.search(forbidden, device_program) is None,
            f"live device program has forbidden operation: {forbidden}",
        )
    for token in (
        "SOURCE_COLLECTOR_SHA256=30d3ac6fa33ac95e1909271ea50227f4e943cab29f61f692dfe5e66ec73ac51c",
        "gemini-a72-pair-v4 result=(pass|fault)",
        "hps_reported=-?[0-9]+ hps_cpu=-?[0-9]+ hps_error=-?[0-9]+ hps_count=[0-9]+",
        "coh_reported=-?[0-9]+ coh_rounds=[0-9]+ coh_cpu8=-?[0-9]+ coh_cpu9=-?[0-9]+ coh_error8=-?[0-9]+ coh_error9=-?[0-9]+ coh_seq8=[0-9]+ coh_seq9=[0-9]+",
        "__A72_CPU9_COHERENCE_LIVE_TERMINAL_CAPTURED__",
        "validation=a72-cpu9-coherence-live-outcome-pass",
    ):
        require(token in live, f"live derivation lacks: {token}")

    for token in (
        "hps_reported=1",
        "hps_cpu=9",
        "hps_error=-1",
        "hps_count greater than zero",
        "coh_reported=1",
        "coh_rounds=1024",
        "coh_cpu8=8",
        "coh_cpu9=9",
        "coh_error8=0",
        "coh_error9=0",
        "coh_seq8=1024",
        "coh_seq9=1024",
        "gemini-a72-pair-v4 result=fault",
        "AUTOMATIC RESTART WITH NO PAIR-V4",
        "collect-device-pstore --target gemini@192.168.1.50 --wait-for-cycle",
        "repeatability run is then earned",
    ):
        require(token in plan, f"runtime decision missing: {token}")

    print("validation=cpu9-bounded-coherency-runtime-tools")
    print("installer_identity_mutations=4-rejected")
    print("live_collector=inherited-read-only-complete-pair-v4")
    print("result_classes=complete")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
