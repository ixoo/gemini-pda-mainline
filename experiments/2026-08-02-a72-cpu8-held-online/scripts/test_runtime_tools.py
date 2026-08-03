#!/usr/bin/env python3
"""Validate held-online deployment and observation contracts."""

import hashlib
import re
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
INSTALLER = SCRIPT_DIR / "install-boot2.sh"
LIVE = SCRIPT_DIR / "capture-live-outcome.sh"
PLAN = EXPERIMENT / "results" / "runtime-decision-map-20260802.txt"
BASE_INSTALLER = (
    EXPERIMENT.parent
    / "2026-07-29-da921x-probe-isolation"
    / "scripts"
    / "install-boot2.sh"
)

PINNED = (
    "fc7368ef0bd56b5c17fea277f78bfeae362da5f685be9f85686f991cdc4fefda",
    "936b9256709514938ddf2f3ab13e63bd9c8d37e991fe40a568aa36a8f8818018",
    "93ad961f64bcdd54d5b94afc2ed23c18de329cdce55a30b6de350bbb1f4084bb",
    "gemian-a72-cpu8-held-online-53046cf314f7",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_installer_source(source: str) -> None:
    for token in PINNED:
        require(source.count(token) == 2, f"installer pin count changed: {token}")
    require(
        source.count(
            "SOURCE_INSTALLER_SHA256=0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7"
        )
        == 1,
        "base installer identity changed",
    )
    require(
        'repo_root="${GEMINI_REPO_ROOT_OVERRIDE:?missing}"' in source,
        "derived repository-root gate changed",
    )
    require("capacity >= 65" in source, "stable-power floor disappeared")


def main() -> int:
    installer = INSTALLER.read_text(encoding="utf-8")
    live = LIVE.read_text(encoding="utf-8")
    plan = PLAN.read_text(encoding="utf-8")
    base = BASE_INSTALLER.read_bytes()
    require(
        hashlib.sha256(base).hexdigest()
        == "0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7",
        "guarded base installer changed",
    )
    validate_installer_source(installer)
    for token in PINNED:
        mutated = installer.replace(token, "0" * len(token), 1)
        try:
            validate_installer_source(mutated)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"installer mutation survived: {token}")
    base_text = base.decode("utf-8")
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
    require(
        "Gemian A72 CPU8 held-online" in installer_help,
        "derived installer description changed",
    )
    require(
        "without creating a partition" in installer_help,
        "no-backup policy disappeared",
    )
    require(
        "shuts the device down cleanly" in installer_help,
        "post-success shutdown policy disappeared",
    )
    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    )
    require(
        "a72-held-attempt-N" in live_help.stderr,
        "live collector output contract changed",
    )
    device_program = live.split("<<'DEVICE'\n", 1)[1].split("\nDEVICE\n", 1)[0]
    for forbidden in (
        r"/dev/mmc",
        r"/dev/block",
        r"/sys/devices/system/cpu/cpu[89]/online\s*>",
        r"\b(?:dd|devmem|i2cset|mount|umount|reboot|poweroff|shutdown|kexec)\b",
    ):
        require(
            re.search(forbidden, device_program) is None,
            f"live device program gained forbidden operation: {forbidden}",
        )
    for token in (
        "cpu_online_writes=none",
        "device_storage_reads=none",
        "device_storage_writes=none",
        "runtime_stimulus=none",
        "gemini-a72-hold-v1 result=(pass|fault)",
        "__A72_HELD_LIVE_TERMINAL_CAPTURED__",
    ):
        require(token in live, f"live collector contract changed: {token}")
    for token in (
        "result=cpu8-online-held",
        "result=sample sample=1",
        "result=pass sample=2",
        "result=down-veto",
        "result=fault",
        "result=rejected-prestate",
        "result=rolled-back-preiso",
        "result=fault-retain-preiso",
        "result=fault-retain-postiso",
    ):
        require(token in plan, f"runtime decision missing class: {token}")
    require(
        "Automatic restart with no exact retained marker" in plan,
        "ambiguous restart rule changed",
    )
    require(
        "scripts/collect-device-pstore --wait-for-cycle" in plan,
        "changed-boot pstore collection rule changed",
    )
    print("validation=cpu8-held-online-runtime-tools")
    print("installer_mutations=4-rejected")
    print("live_collector=read-only")
    print("result_classes=complete")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
