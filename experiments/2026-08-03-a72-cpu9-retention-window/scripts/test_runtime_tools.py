#!/usr/bin/env python3
"""Validate CPU9 retention-window deployment and observation contracts."""

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
HELD = EXPERIMENT.parent / "2026-08-02-a72-cpu8-held-online" / "scripts"
CPU9 = EXPERIMENT.parent / "2026-08-03-a72-cpu9-cluster-reuse" / "scripts"
HELD_INSTALLER = HELD / "install-boot2.sh"
HELD_LIVE = HELD / "capture-live-outcome.sh"
CPU9_LIVE = CPU9 / "capture-live-outcome.sh"
BASE_INSTALLER = (
    EXPERIMENT.parent
    / "2026-07-29-da921x-probe-isolation"
    / "scripts"
    / "install-boot2.sh"
)

PINS = (
    "b32bca348efc0fcaffe2b5909c6246d66a4d0fec4102cee091103c42db604d69",
    "6f1e5f45c8f75cdfde5a996f902f499d685566c3bec227efa6cdb56aaeffa115",
    "3a17f39db6d219a14533ca638dedc5763f455c360e74cd80f8d56f20a5e67567",
    "gemian-a72-cpu9-retention-window-140bed8c432d",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    installer = INSTALLER.read_text(encoding="utf-8")
    live = LIVE.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    held_installer = HELD_INSTALLER.read_bytes()
    held_live = HELD_LIVE.read_bytes()
    require(
        hashlib.sha256(held_installer).hexdigest()
        == "074464f4bea0062dab763d2cc3ce69fb3b827c6fcafaea98e7f7b9910a66f602",
        "held-online installer changed",
    )
    require(
        hashlib.sha256(held_live).hexdigest()
        == "0b316d4028df77a1ae03263ea185c9f34955dc35260e4bced5de395cb3078f16",
        "held-online live collector changed",
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
    for token in PINS:
        require(installer.count(token) == 2, f"installer pin count changed: {token}")
        mutated = installer.replace(token, "0" * len(token), 1)
        require(mutated.count(token) == 1, f"installer mutation failed: {token}")
    for token in (
        "source held-online installer changed",
        "GEMINI_CPU9_WINDOW_SCRIPT_DIR",
        "Gemian A72 CPU9 retention-window candidate",
        "2026-08-03-a72-cpu9-retention-window",
    ):
        require(token in installer, f"installer derivation lacks: {token}")

    base_text = BASE_INSTALLER.read_text(encoding="utf-8")
    for token in (
        "live GPT does not have exactly one boot2 row",
        "boot2 is mounted or not a block device",
        "fresh_predecessor_backup=no",
        "independent full readback checksum mismatch",
        "temporary_readback_removed=yes",
        "sudo -n systemctl poweroff",
        "shutdown=confirmed-unreachable",
    ):
        require(token in base_text, f"base installer safety gate changed: {token}")
    installer_help = subprocess.run(
        [str(INSTALLER), "--help"], check=True, capture_output=True, text=True
    ).stdout
    require("Gemian A72 CPU9 retention-window" in installer_help, "installer help changed")
    require("without creating a partition" in installer_help, "no-backup policy changed")
    require("shuts the device down cleanly" in installer_help, "shutdown policy changed")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    ).stderr
    require("a72-cpu9-window-attempt-N" in live_help, "live output changed")
    held_device_program = (
        held_live.decode("utf-8").split("<<'DEVICE'\n", 1)[1].split("\nDEVICE\n", 1)[0]
    )
    for forbidden in (
        r"/dev/mmc",
        r"/dev/block",
        r"/sys/devices/system/cpu/cpu[89]/online\s*>",
        r"\b(?:dd|devmem|i2cset|mount|umount|reboot|poweroff|shutdown|kexec)\b",
    ):
        require(
            re.search(forbidden, held_device_program) is None,
            f"inherited live device program has forbidden operation: {forbidden}",
        )
    for token in (
        "SOURCE_COLLECTOR_SHA256=30d3ac6fa33ac95e1909271ea50227f4e943cab29f61f692dfe5e66ec73ac51c",
        "gemini-a72-pair-v2 result=(pass|fault)",
        "result=(pass|fault) sample=[123]",
        "__A72_CPU9_WINDOW_LIVE_TERMINAL_CAPTURED__",
        "validation=a72-cpu9-window-live-outcome-pass",
    ):
        require(token in live, f"live derivation lacks: {token}")

    for token in (
        "result=hps-down-held-first cpu=9 error=-1",
        "gemini-a72-pair-v2 result=pass sample=3",
        "result=down-veto",
        "result=fault",
        "result=rejected-prestate",
        "result=fault-retain-psci",
        "result=fault-retain-secondary",
        "CPUHVFS `cluster1 off` text",
        "Automatic restart with no exact retained marker",
        "scripts/collect-device-pstore --target gemini@192.168.1.50",
        "do not repeat this exact candidate unchanged",
    ):
        require(token in plan, f"runtime decision missing: {token}")

    print("validation=cpu9-retention-window-runtime-tools")
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
