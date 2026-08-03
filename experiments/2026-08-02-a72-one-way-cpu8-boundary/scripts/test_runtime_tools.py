#!/usr/bin/env python3
"""Validate the guarded deployment and one-way CPU8 observation contract."""

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
    "4830a0d0e1a3cb82a13e7c34248fb95f736d9ba3c71ba8ecb82ab210389bde6d",
    "fc7368ef0bd56b5c17fea277f78bfeae362da5f685be9f85686f991cdc4fefda",
    "a58e950b6004b4591b4bec17691bbc179ba089adc382ce454b7d23eace2e9f64",
    "gemian-a72-one-way-cpu8-aae1a0f9a3d9",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_installer_source(source: str) -> None:
    for token in PINNED:
        require(source.count(token) == 2, f"installer pin count changed: {token}")
    require(
        source.count("SOURCE_INSTALLER_SHA256=0c669ab85063015fa83b7e28a506e1bcf8cdafc4994726009becf92151fda7e7")
        == 1,
        "base installer identity changed",
    )
    require("repo_root=\"${GEMINI_REPO_ROOT_OVERRIDE:?missing}\"" in source,
            "derived repository-root gate changed")
    require("owner-battery-override" not in source,
            "installer gained a battery override")


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
    require("Gemian A72 one-way CPU8" in installer_help,
            "derived installer description changed")
    require("without creating a partition" in installer_help,
            "no-backup policy disappeared")
    require("shuts the device down cleanly" in installer_help,
            "post-success shutdown policy disappeared")

    live_help = subprocess.run(
        [str(LIVE), "--help"], check=True, capture_output=True, text=True
    )
    require("a72-one-way-attempt-N" in live_help.stderr,
            "live collector output contract changed")
    device_program = live.split("<<'DEVICE'\n", 1)[1].split("\nDEVICE\n", 1)[0]
    for forbidden in (
        r"/dev/mmc",
        r"/dev/block",
        r"/sys/devices/system/cpu/cpu[89]/online\s*>",
        r"\b(?:dd|devmem|i2cset|mount|umount|reboot|poweroff|shutdown|kexec)\b",
    ):
        require(re.search(forbidden, device_program) is None,
                f"live device program gained forbidden operation: {forbidden}")
    for token in (
        "cpu_online_writes=none",
        "device_storage_reads=none",
        "device_storage_writes=none",
        "runtime_stimulus=none",
        "gemini-a72-oneway-v1 result=",
        "__A72_ONE_WAY_LIVE_TERMINAL_CAPTURED__",
    ):
        require(token in live, f"live collector contract changed: {token}")

    for result in (
        "cpu8-online-held",
        "rejected-prestate",
        "rolled-back-preiso",
        "fault-retain-preiso",
        "fault-retain-postiso",
    ):
        require(f"`result={result}" in plan,
                f"runtime decision missing terminal class: {result}")
    require("Automatic restart with no exact marker" in plan,
            "ambiguous restart rule changed")
    require("scripts/collect-device-pstore" in plan and "--wait-for-cycle" in plan,
            "changed-boot pstore collection rule changed")

    print("validation=one-way-cpu8-runtime-tools")
    print("installer_mutations=4-rejected")
    print("live_collector=read-only")
    print("terminal_classes=5-complete")
    print("result=pass")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
