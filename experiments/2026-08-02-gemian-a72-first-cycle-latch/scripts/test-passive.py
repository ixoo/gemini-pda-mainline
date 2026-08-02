#!/usr/bin/env python3
"""Exercise ABI-v2 passive-capture validation and no-stimulus invariants."""

from __future__ import annotations

import importlib.util
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-passive.py"
REMOTE_PATH = ROOT / "scripts" / "remote-passive-capture.sh"
RUNTIME = (
    ROOT.parent
    / "2026-08-02-gemian-a72-bounded-observer-boot"
    / "results"
    / "runtime-attempt-1-overwritten-ring-20260802.txt"
)
spec = importlib.util.spec_from_file_location("passive_validator", VALIDATOR_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def envelope(first: list[str], second: list[str], identical: str) -> str:
    lines = [
        "experiment=gemian-a72-first-cycle-latch-passive",
        "kernel_release=3.18.41+",
        "architecture=aarch64",
        "build_identity=#1 SMP PREEMPT Sun Aug 2 18:14:10 UTC 2026",
        "root=/dev/mmcblk0p29",
        "possible=0-9",
        "present=0-9",
        "observer_path=/proc/mt6797_a72_transition",
        "observer_mode=400",
        "boot_id_before_sha256=" + "a" * 64,
        "state_changing_writes=none",
        "load_workers=0",
        "cpu_online_writes=none",
        "__OBSERVER_FIRST_BEGIN__",
        *first,
        "__OBSERVER_FIRST_END__",
        "__OBSERVER_SECOND_BEGIN__",
        *second,
        "__OBSERVER_SECOND_END__",
        f"observer_first_lines={len(first)}",
        f"observer_second_lines={len(second)}",
        f"observer_snapshots_identical={identical}",
        "cpu8=0",
        "cpu9=0",
        "online=0-7",
        "power=usb:0|status:Discharging|capacity:99|health:Good",
        "boot_id_after_sha256=" + "a" * 64,
        "boot_id_stable=yes",
        "runtime_stimulus=none",
        "status=completed",
    ]
    return "\n".join(lines) + "\n"


def complete_snapshot() -> list[str]:
    selected = []
    for line in RUNTIME.read_text().splitlines():
        if " tx=182 " in line or " tx=183 " in line:
            selected.append(line)
    assert len(selected) == 46
    rewritten = [
        re.sub(r"^seq=[0-9]+", f"seq={index}", line)
        for index, line in enumerate(selected, 1)
    ]
    return [
        "abi=mt6797-a72-transition-observer-v2 state=frozen-complete "
        "count=46 overflow=0 up_tx=182 down_tx=183",
        *rewritten,
    ]


def reject(label: str, text: str) -> None:
    try:
        validator.validate(text)
    except validator.ValidationError:
        return
    raise AssertionError(f"{label} mutation was accepted")


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"mutation target count changed for {old!r}")
    return text.replace(old, new, 1)


def main() -> int:
    wait = [
        "abi=mt6797-a72-transition-observer-v2 state=wait-up "
        "count=0 overflow=0 up_tx=0 down_tx=0"
    ]
    waiting = envelope(wait, wait, "yes")
    result = validator.validate(waiting)
    assert result["formal_disposition"] == "preserve-incomplete-no-stimulus"

    complete = complete_snapshot()
    accepted = envelope(complete, complete, "yes")
    result = validator.validate(accepted)
    assert result["formal_disposition"] == "accepted-first-natural-cpu8-pair"
    assert result["owner_transition_validation"] == "passed"

    reject("ABI drift", accepted.replace("observer-v2", "observer-v1", 1))
    unstable = complete.copy()
    unstable[-1] = unstable[-1].replace("arg1=0x0", "arg1=0x1")
    reject("terminal instability", envelope(complete, unstable, "no"))
    reject("synthetic load", replace_once(accepted, "load_workers=0", "load_workers=2"))
    reject(
        "CPU9 complete record",
        accepted.replace("target=8", "target=9", 1),
    )
    reject(
        "overflow",
        accepted.replace("overflow=0 up_tx=182", "overflow=1 up_tx=182", 1),
    )
    reject("transaction alias", accepted.replace("down_tx=183", "down_tx=182"))
    reject(
        "sequence gap",
        accepted.replace("seq=2 ", "seq=99 ", 1),
    )
    reject(
        "failed boundary",
        accepted.replace(
            "event=lifecycle phase=2 target=8 actor=8 online=0x000001f0 result=0",
            "event=lifecycle phase=2 target=8 actor=8 online=0x000001f0 result=-1",
            1,
        ),
    )
    reject(
        "reported stability",
        replace_once(accepted, "observer_snapshots_identical=yes", "observer_snapshots_identical=no"),
    )
    reject(
        "boot identity",
        replace_once(accepted, "Sun Aug 2 18:14:10", "Sun Aug 2 18:14:11"),
    )

    remote = REMOTE_PATH.read_text()
    for forbidden in (
        "yes >/dev/null",
        "/sys/devices/system/cpu/cpu8/online >",
        "/sys/devices/system/cpu/cpu9/online >",
        "i2cset",
        "devmem",
        "reboot",
        "poweroff",
        "stress",
    ):
        if forbidden in remote:
            raise AssertionError(f"remote capture contains forbidden action {forbidden!r}")
    first_copy = remote.index('cat "$observer" >"$first"')
    optional_power = remote.index("optional_read /sys/class/power_supply/usb/online")
    if first_copy >= optional_power:
        raise AssertionError("observer is not copied before optional power reporting")
    print("PASS: passive latch validation and 12 fail-closed/no-stimulus checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
