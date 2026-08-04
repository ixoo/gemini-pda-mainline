#!/usr/bin/env python3
"""Validate corrected pair-v7 deployment and observation contracts."""

import hashlib
import re
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
LIVE = SCRIPT_DIR / "capture-live-outcome.sh"
PLAN = EXPERIMENT / "results" / "runtime-decision-map-start-gate-20260804.txt"
PAIR5 = EXPERIMENT.parent / "2026-08-03-a72-cpu9-multiline-integrity"
BASE_INSTALLER = (
    EXPERIMENT.parent
    / "2026-07-29-da921x-probe-isolation"
    / "scripts"
    / "install-boot2.sh"
)
PINS = (
    ("d34b2de509021d5fbbfcca62e3676202fe88b449786daf62b4eb466667fae093", 2),
    ("2e8c611b1dbe5b79b13f2dec9cf9d77d9b7973a732f63702a6228600bef464b3", 2),
    ("1383686ddfed408190fdbbe59bf512d3ba3a52a49e6aa2ff30dfed3e01f379b7", 2),
    ("gemian-a72-scheduler-context-78dd52721a76", 2),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    installer = INSTALLER.read_text(encoding="utf-8")
    live = LIVE.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    require(
        hashlib.sha256((PAIR5 / "scripts/install-boot2.sh").read_bytes()).hexdigest()
        == "a2a3f292f0bb857be0251c7bacabecfa9157b2034d3a7ecc1ccd6b5541b672c9",
        "pair-v5 installer changed",
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
            f"installer identity mutation was not rejected: {token}",
        )
    for token in (
        "EXPECTED_PREDECESSOR_SHA256=d34b2de509021d5fbbfcca62e3676202fe88b449786daf62b4eb466667fae093",
        "CANDIDATE_SHA256=2e8c611b1dbe5b79b13f2dec9cf9d77d9b7973a732f63702a6228600bef464b3",
        "ARTIFACT_MANIFEST_SHA256=1383686ddfed408190fdbbe59bf512d3ba3a52a49e6aa2ff30dfed3e01f379b7",
        "ARTIFACT_NAME=gemian-a72-scheduler-context-78dd52721a76",
        "source pair-v5 installer changed",
        "GEMINI_A72_SCHEDULER_SCRIPT_DIR",
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
    require("blocked-start-gate scheduler" in help_text, "installer help changed")
    require("without creating a partition" in help_text, "no-backup policy changed")
    require("shuts the device down cleanly" in help_text, "shutdown policy changed")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    ).stderr
    require("a72-scheduler-attempt-N" in live_help, "live output changed")
    device_program = live.split("<<'DEVICE'\n", 1)[1].split("\nDEVICE\n", 1)[0]
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
        "gemini-a72-pair-v6 result=(pass|fault)",
        "gemini-a72-pair-v7 result=(pass|fault)",
        "sc_iterations=262144 sc_rescheds=64",
        "sc_task8=-?[0-9]+ sc_task9=-?[0-9]+",
        "sc_readywait8=-?[0-9]+ sc_readywait9=-?[0-9]+",
        "sc_startwait8=-?[0-9]+ sc_startwait9=-?[0-9]+",
        "sc_done8=[0-9]+ sc_done9=[0-9]+ sc_ready=[0-9]+ sc_finished=[0-9]+",
        "sc_hash8=[0-9a-f]{16} sc_hash9=[0-9a-f]{16}",
        "__A72_SCHEDULER_LIVE_TERMINAL_CAPTURED__",
        "validation=a72-scheduler-live-outcome-pass",
    ):
        require(token in live, f"live collector lacks: {token}")

    for token in (
        "adjacent complete pair-v6 pass",
        "gemini-a72-pair-v7 result=pass parent_pass=1",
        "sc_reported=1 sc_iterations=262144 sc_rescheds=64",
        "sc_expected8=8 sc_start8=8 sc_end8=8",
        "sc_expected9=9 sc_start9=9 sc_end9=9",
        "sc_task8=1 sc_task9=1 sc_create8=0 sc_create9=0",
        "sc_wake8 and sc_wake9 must each be 0 or 1",
        "sc_readywait8=1 sc_readywait9=1",
        "sc_startwait8=1 sc_startwait9=1",
        "sc_wait8=1 sc_wait9=1",
        "sc_error8=0 sc_error9=0 sc_stop8=0 sc_stop9=0",
        "sc_done8=262144 sc_done9=262144 sc_ready=2 sc_finished=2",
        "sc_hash8=f678147669874ecd sc_hash9=c2274327e9c8104c",
        "AUTOMATIC RESTART WITH NO PAIR-V7",
        "collect-device-pstore --target gemini@192.168.1.50 --wait-for-cycle",
        "One exact repeat is then earned",
    ):
        require(token in plan, f"runtime decision missing: {token}")

    print("validation=a72-scheduler-context-runtime-tools")
    print("installer_identity_mutations=4-rejected")
    print("installer=exact-predecessor-candidate-readback-shutdown")
    print("live_collector=read-only-adjacent-pair-v6-v7")
    print("result_classes=complete")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
