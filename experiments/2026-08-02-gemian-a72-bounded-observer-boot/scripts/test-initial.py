#!/usr/bin/env python3
"""Exercise initial-capture validation and read-only collector invariants."""

from __future__ import annotations

import importlib.util
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-initial.py"
REMOTE_PATH = ROOT / "scripts" / "remote-initial-probe.sh"
COLLECTOR_PATH = ROOT / "scripts" / "collect-initial.sh"
spec = importlib.util.spec_from_file_location("initial_validator", VALIDATOR_PATH)
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def capture(records: list[str], overwritten: int = 0, cpu8: str = "0", cpu9: str = "0") -> str:
    disposition = "blocked-cpu-state"
    if cpu8 == cpu9 == "0":
        if overwritten:
            disposition = "blocked-overwritten"
        elif records:
            disposition = "boot-records-present"
        else:
            disposition = "empty-offline"
    lines = [
        "experiment=gemian-a72-bounded-observer-initial",
        "kernel_release=3.18.41+",
        "architecture=aarch64",
        "build_identity=#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026",
        "root=/dev/mmcblk0p29",
        "possible=0-9",
        "present=0-9",
        "observer_path=/proc/mt6797_a72_transition",
        "observer_mode=400",
        "boot_id_before_sha256=" + "a" * 64,
        "power=usb:1|status:Full|capacity:100|health:Good",
        "state_changing_writes=none",
        "load_workers=0",
        "cpu_online_writes=none",
    ]
    for index in range(1, 6):
        lines.append(
            f"baseline_sample={index} cpu8={cpu8} cpu9={cpu9} online=0-7"
        )
    lines.extend(
        [
            "__OBSERVER_INITIAL_BEGIN__",
            f"abi=mt6797-a72-transition-observer-v1 count={len(records)} overwritten={overwritten}",
            *records,
            "__OBSERVER_INITIAL_END__",
            f"post_cpu8={cpu8}",
            f"post_cpu9={cpu9}",
            "post_online=0-7",
            "temperatures_millic=cpu:35000|ap:28000|pmic:27000|da9214:60000",
            "boot_id_after_sha256=" + "a" * 64,
            "boot_id_stable=yes",
            f"observer_count={len(records)}",
            f"observer_overwritten={overwritten}",
            f"initial_disposition={disposition}",
            "load_permitted_by_initial=no",
            "status=completed",
        ]
    )
    return "\n".join(lines) + "\n"


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
    empty = capture([])
    result = validator.validate(empty)
    assert result["initial_disposition"] == "empty-offline"
    assert result["next_action"] == "eligible-for-separate-second-prepulse-gate"

    record = (
        "seq=1 ns=100 tx=1 event=lifecycle phase=1 target=8 actor=0 "
        "online=0x000000ff result=0 arg0=0x0 arg1=0x0"
    )
    recorded = capture([record])
    result = validator.validate(recorded)
    assert result["initial_disposition"] == "boot-records-present"
    assert result["next_action"] == "preserve-and-review-no-load"
    assert validator.validate(capture([], overwritten=1))["initial_disposition"] == (
        "blocked-overwritten"
    )
    assert validator.validate(capture([], cpu8="1"))["initial_disposition"] == (
        "blocked-cpu-state"
    )

    reject(
        "load permission",
        replace_once(empty, "load_permitted_by_initial=no", "load_permitted_by_initial=yes"),
    )
    reject(
        "count mismatch",
        replace_once(empty, "count=0 overwritten=0", "count=1 overwritten=0"),
    )
    reject(
        "ABI drift",
        replace_once(empty, "observer-v1 count=0", "observer-v2 count=0"),
    )
    reject(
        "CPU9 record",
        replace_once(recorded, "target=8", "target=7"),
    )
    two = capture(
        [
            record,
            record.replace("ns=100", "ns=101").replace("phase=1", "phase=2"),
        ]
    )
    reject("non-increasing sequence", two)
    secure = capture(
        [
            "seq=1 ns=100 tx=1 event=secure phase=6 target=8 actor=0 "
            "online=0x000000ff valid=0x1fff sentinel_after=0x0"
        ]
    )
    reject("secure stability field", secure)

    remote = REMOTE_PATH.read_text()
    collector = COLLECTOR_PATH.read_text()
    for forbidden in (
        "yes >/dev/null",
        "/sys/devices/system/cpu/cpu8/online >",
        "/sys/devices/system/cpu/cpu9/online >",
        "i2cset",
        "devmem",
        "reboot",
        "poweroff",
    ):
        if forbidden in remote or forbidden in collector:
            raise AssertionError(f"collector contains forbidden action {forbidden!r}")
    for required in (
        "load_workers=0",
        "load_permitted_by_initial=no",
        "__OBSERVER_INITIAL_BEGIN__",
        "initial_disposition=",
    ):
        if required not in remote:
            raise AssertionError(f"remote probe lacks {required!r}")
    if "__REMOTE_SHA256__" in collector or "__VALIDATOR_SHA256__" in collector:
        raise AssertionError("collector retains an unresolved checksum placeholder")

    print("PASS: initial collector validation and 10 fail-closed checks")
    return 0


if __name__ == "__main__":
    sys.exit(main())
