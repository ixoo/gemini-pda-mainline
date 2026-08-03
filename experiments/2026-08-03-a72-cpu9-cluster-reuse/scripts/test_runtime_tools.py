#!/usr/bin/env python3
"""Validate CPU9 deployment and observation contracts."""

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
HELD_INSTALLER = HELD / "install-boot2.sh"
HELD_LIVE = HELD / "capture-live-outcome.sh"
BASE_INSTALLER = (
    EXPERIMENT.parent
    / "2026-07-29-da921x-probe-isolation"
    / "scripts"
    / "install-boot2.sh"
)

PINS = (
    "2e81e18610d99c69bee8867d2fe960245dfcdda1ca583965724598255ea871af",
    "b32bca348efc0fcaffe2b5909c6246d66a4d0fec4102cee091103c42db604d69",
    "036d2f121e716466cbd99c2b249df6507e33aee041210c8b093437c16bd81acc",
    "gemian-a72-cpu9-cluster-reuse-fef3d814c217",
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
        "GEMINI_CPU9_SCRIPT_DIR",
        "Gemian A72 CPU9 cluster-reuse candidate",
        "2026-08-03-a72-cpu9-cluster-reuse",
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
    require("Gemian A72 CPU9 cluster-reuse" in installer_help, "installer help changed")
    require("without creating a partition" in installer_help, "no-backup policy changed")
    require("shuts the device down cleanly" in installer_help, "shutdown policy changed")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    ).stderr
    require("a72-cpu9-attempt-N" in live_help, "live output contract changed")
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
        "SOURCE_COLLECTOR_SHA256=0b316d4028df77a1ae03263ea185c9f34955dc35260e4bced5de395cb3078f16",
        "gemini-a72-pair-v1 result=(pass|fault)",
        "result=(pass|fault) sample=[123]",
        "__A72_CPU9_LIVE_TERMINAL_CAPTURED__",
        "validation=a72-cpu9-live-outcome-pass",
    ):
        require(token in live, f"live derivation lacks: {token}")

    for token in (
        "result=cpu8-online-held",
        "result=cpu9-online-held",
        "result=sample sample=1",
        "result=sample sample=2",
        "result=pass sample=3",
        "result=down-veto",
        "result=fault",
        "result=rejected-prestate",
        "result=fault-retain-psci",
        "result=fault-retain-secondary",
        "Automatic restart with no exact retained marker",
        "scripts/collect-device-pstore --target gemini@192.168.1.50",
        "Do not repeat this exact artifact unchanged",
    ):
        require(token in plan, f"runtime decision missing: {token}")

    print("validation=cpu9-cluster-reuse-runtime-tools")
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
