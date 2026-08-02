#!/usr/bin/env python3
"""Validate a private initial bounded-observer capture without changing it."""

from __future__ import annotations

import argparse
import pathlib
import re
import stat
import sys


HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEADER = re.compile(
    r"^abi=mt6797-a72-transition-observer-v1 count=([0-9]+) overwritten=([0-9]+)$"
)
RECORD = re.compile(
    r"^seq=([0-9]+) ns=([0-9]+) tx=([0-9]+) "
    r"event=(lifecycle|da9214|spm|secure|clock|toprgu|dcm|mutation) "
    r"phase=([0-9]+) target=([0-9]+) actor=([0-9]+) "
    r"online=0x([0-9a-f]{8})(?: .+)?$"
)
EXPECTED_SCALARS = {
    "experiment": "gemian-a72-bounded-observer-initial",
    "kernel_release": "3.18.41+",
    "architecture": "aarch64",
    "build_identity": "#1 SMP PREEMPT Sun Aug 2 14:14:43 UTC 2026",
    "root": "/dev/mmcblk0p29",
    "possible": "0-9",
    "present": "0-9",
    "observer_path": "/proc/mt6797_a72_transition",
    "observer_mode": "400",
    "power": "usb:1|status:Full|capacity:100|health:Good",
    "state_changing_writes": "none",
    "load_workers": "0",
    "cpu_online_writes": "none",
    "boot_id_stable": "yes",
    "load_permitted_by_initial": "no",
    "status": "completed",
}


class ValidationError(Exception):
    pass


def read_regular(path: pathlib.Path) -> str:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValidationError("capture is missing, empty, or unsafe")
    return path.read_text()


def one(values: dict[str, list[str]], key: str) -> str:
    found = values.get(key, [])
    if len(found) != 1:
        raise ValidationError(f"{key} count is {len(found)}, expected one")
    return found[0]


def validate(text: str) -> dict[str, str | int]:
    lines = text.splitlines()
    if lines.count("__OBSERVER_INITIAL_BEGIN__") != 1 or lines.count(
        "__OBSERVER_INITIAL_END__"
    ) != 1:
        raise ValidationError("observer delimiters are absent or duplicated")
    begin = lines.index("__OBSERVER_INITIAL_BEGIN__")
    end = lines.index("__OBSERVER_INITIAL_END__")
    if end <= begin + 1:
        raise ValidationError("observer section is empty or reversed")

    values: dict[str, list[str]] = {}
    for line in lines[:begin] + lines[end + 1 :]:
        if "=" in line:
            key, value = line.split("=", 1)
            values.setdefault(key, []).append(value)
    for key, expected in EXPECTED_SCALARS.items():
        if one(values, key) != expected:
            raise ValidationError(f"{key} changed")

    before = one(values, "boot_id_before_sha256")
    after = one(values, "boot_id_after_sha256")
    if not HEX64.fullmatch(before) or after != before:
        raise ValidationError("boot ID hash is malformed or changed")

    baseline = [line for line in lines[:begin] if line.startswith("baseline_sample=")]
    if len(baseline) != 5:
        raise ValidationError("baseline sample count changed")
    for index, line in enumerate(baseline, 1):
        match = re.fullmatch(
            r"baseline_sample=([1-5]) cpu8=([01]) cpu9=([01]) online=([0-9,-]+)",
            line,
        )
        if not match or int(match.group(1)) != index:
            raise ValidationError("baseline sample is malformed or unordered")

    observer = lines[begin + 1 : end]
    header = HEADER.fullmatch(observer[0])
    if not header:
        raise ValidationError("observer ABI header changed")
    count, overwritten = map(int, header.groups())
    if count > 256 or len(observer[1:]) != count:
        raise ValidationError("observer count exceeds the ring or line count")
    previous_sequence = -1
    for line in observer[1:]:
        match = RECORD.fullmatch(line)
        if not match:
            raise ValidationError(f"malformed observer record: {line}")
        sequence, _, _, event, phase, target, actor, _ = match.groups()
        sequence_value = int(sequence)
        if sequence_value <= previous_sequence:
            raise ValidationError("observer sequence is not strictly increasing")
        previous_sequence = sequence_value
        if int(phase) > 26 or int(target) not in (8, 9) or int(actor) > 9:
            raise ValidationError("observer phase or CPU identity is out of range")
        required_payload = {
            "lifecycle": (" result=", " arg0=0x", " arg1=0x"),
            "da9214": (" status=", " valid=0x"),
            "secure": (" stable=", " sentinel_after=0x"),
            "clock": (" status=", " semaphore=0x"),
            "mutation": (" requested=0x", " after=0x", " status="),
        }.get(event, ())
        if any(token not in line for token in required_payload):
            raise ValidationError(f"{event} payload is incomplete")

    reported_count = int(one(values, "observer_count"))
    reported_overwritten = int(one(values, "observer_overwritten"))
    if (reported_count, reported_overwritten) != (count, overwritten):
        raise ValidationError("reported observer totals disagree with the snapshot")

    post_cpu8 = one(values, "post_cpu8")
    post_cpu9 = one(values, "post_cpu9")
    if post_cpu8 not in ("0", "1") or post_cpu9 not in ("0", "1"):
        raise ValidationError("post CPU state is malformed")
    all_offline = all(" cpu8=0 cpu9=0 " in line for line in baseline)
    all_offline = all_offline and post_cpu8 == post_cpu9 == "0"
    disposition = one(values, "initial_disposition")
    expected_disposition = "blocked-cpu-state"
    if all_offline:
        if overwritten:
            expected_disposition = "blocked-overwritten"
        elif count:
            expected_disposition = "boot-records-present"
        else:
            expected_disposition = "empty-offline"
    if disposition != expected_disposition:
        raise ValidationError("initial disposition does not match captured state")

    return {
        "observer_count": count,
        "observer_overwritten": overwritten,
        "initial_disposition": disposition,
        "next_action": (
            "preserve-and-review-no-load"
            if disposition != "empty-offline"
            else "eligible-for-separate-second-prepulse-gate"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = validate(read_regular(args.capture))
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=gemian-a72-bounded-observer-initial")
    for key, value in result.items():
        print(f"{key}={value}")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
