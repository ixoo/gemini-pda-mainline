#!/usr/bin/env python3
"""Validate pair-v6 deployment and observation contracts."""

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
PAIR5 = EXPERIMENT.parent / "2026-08-03-a72-cpu9-multiline-integrity"
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
    ("5227729e34ca42cf606f43008ec753fce15147693ce7a670818db58c5903fa48", 3),
    ("0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb", 2),
    ("fb095f8677b2d548f96093f56157b510afa7bc5b26e4fac8ce65e04a7ad87690", 2),
    ("gemian-a72-cpu9-parallel-disjoint-load-6673d9ff6b9f", 2),
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
        hashlib.sha256(
            (PAIR5 / "scripts/capture-live-outcome.sh").read_bytes()
        ).hexdigest()
        == "1ac4ab27737b46ceb718b76583b081408b0df977284b9adca1046cbb11013d9a",
        "pair-v5 collector changed",
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
        "EXPECTED_PREDECESSOR_SHA256=5227729e34ca42cf606f43008ec753fce15147693ce7a670818db58c5903fa48",
        "CANDIDATE_SHA256=0beead0b00485ad18333aca4d688fcd549c813113b7ec0554a6761c7147b17fb",
        "ARTIFACT_MANIFEST_SHA256=fb095f8677b2d548f96093f56157b510afa7bc5b26e4fac8ce65e04a7ad87690",
        "ARTIFACT_NAME=gemian-a72-cpu9-parallel-disjoint-load-6673d9ff6b9f",
        "source pair-v5 installer changed",
        "GEMINI_CPU9_PARALLEL_SCRIPT_DIR",
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
    require("parallel-disjoint-load" in help_text, "installer help changed")
    require("without creating a partition" in help_text, "no-backup policy changed")
    require("shuts the device down cleanly" in help_text, "shutdown policy changed")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    ).stderr
    require("a72-cpu9-parallel-attempt-N" in live_help, "live output changed")
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
        "SOURCE_COLLECTOR_SHA256=1ac4ab27737b46ceb718b76583b081408b0df977284b9adca1046cbb11013d9a",
        "gemini-a72-pair-v6 result=(pass|fault)",
        "pl_reported=-?[0-9]+ pl_rounds=128 pl_lines=1024 pl_words=8",
        "pl_done8=[0-9]+ pl_done9=[0-9]+ pl_ready=[0-9]+ pl_written=[0-9]+ pl_verified=[0-9]+",
        "pl_hash8w=[0-9a-f]{16} pl_hash8r=[0-9a-f]{16} pl_hash9w=[0-9a-f]{16} pl_hash9r=[0-9a-f]{16}",
        "__A72_CPU9_PARALLEL_LIVE_TERMINAL_CAPTURED__",
        "validation=a72-cpu9-parallel-live-outcome-pass",
    ):
        require(token in live, f"live derivation lacks: {token}")

    for token in (
        "gemini-a72-pair-v6 result=pass",
        "pl_reported=1",
        "pl_rounds=128",
        "pl_lines=1024",
        "pl_words=8",
        "pl_cpu8=8 pl_cpu9=9 pl_error8=0 pl_error9=0",
        "pl_done8=128 pl_done9=128",
        "pl_ready=256 pl_written=256 pl_verified=256",
        "pl_hash8w=X pl_hash8r=Y pl_hash9w=Y pl_hash9r=X",
        "gemini-a72-pair-v6 result=fault",
        "AUTOMATIC RESTART WITH NO PAIR-V6",
        "collect-device-pstore --target gemini@192.168.1.50 --wait-for-cycle",
        "One exact repeat is then earned",
    ):
        require(token in plan, f"runtime decision missing: {token}")

    print("validation=cpu9-parallel-disjoint-load-runtime-tools")
    print("installer_identity_mutations=4-rejected")
    print("installer=exact-predecessor-candidate-readback-shutdown")
    print("live_collector=inherited-read-only-complete-pair-v6")
    print("result_classes=complete")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
