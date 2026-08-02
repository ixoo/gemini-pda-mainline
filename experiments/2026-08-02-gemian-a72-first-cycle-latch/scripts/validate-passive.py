#!/usr/bin/env python3
"""Validate a passive two-read ABI-v2 first-cycle-latch capture."""

from __future__ import annotations

import argparse
import collections
import importlib.util
import pathlib
import re
import stat
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PARENT_ANALYZER = (
    ROOT.parent
    / "2026-08-02-gemian-a72-bounded-observer-boot"
    / "scripts"
    / "analyze-overwritten-ring.py"
)
HEADER = re.compile(
    r"^abi=mt6797-a72-transition-observer-v2 "
    r"state=(wait-up|capture-up|wait-down|capture-down|frozen-complete|"
    r"frozen-up-failed|frozen-down-failed|frozen-cpu9|frozen-protocol|"
    r"frozen-overflow) count=([0-9]+) overflow=([01]) "
    r"up_tx=([0-9]+) down_tx=([0-9]+)$"
)
BASE = re.compile(
    r"^seq=([0-9]+) ns=([0-9]+) tx=([0-9]+) "
    r"event=(lifecycle|da9214|spm|secure|clock|toprgu|dcm|mutation) "
    r"phase=([0-9]+) target=([0-9]+) actor=([0-9]+) "
    r"online=0x([0-9a-f]{8})(?: (.*))?$"
)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TERMINAL = {
    "frozen-complete",
    "frozen-up-failed",
    "frozen-down-failed",
    "frozen-cpu9",
    "frozen-protocol",
    "frozen-overflow",
}
EXPECTED = {
    "experiment": "gemian-a72-first-cycle-latch-passive",
    "kernel_release": "3.18.41+",
    "architecture": "aarch64",
    "build_identity": "#1 SMP PREEMPT Sun Aug 2 18:14:10 UTC 2026",
    "root": "/dev/mmcblk0p29",
    "possible": "0-9",
    "present": "0-9",
    "observer_path": "/proc/mt6797_a72_transition",
    "observer_mode": "400",
    "state_changing_writes": "none",
    "load_workers": "0",
    "cpu_online_writes": "none",
    "runtime_stimulus": "none",
    "boot_id_stable": "yes",
    "status": "completed",
}


class ValidationError(Exception):
    pass


def load_parent():
    import hashlib

    expected = "5f5ee7f04caad30e12674de69e86d38649a0ea10d4fb412c5f0a9c5ad29872dc"
    if hashlib.sha256(PARENT_ANALYZER.read_bytes()).hexdigest() != expected:
        raise ValidationError("pinned parent transition analyzer changed")
    spec = importlib.util.spec_from_file_location("bounded_transition_analyzer", PARENT_ANALYZER)
    if spec is None or spec.loader is None:
        raise ValidationError("cannot load pinned parent transition analyzer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def one(values: dict[str, list[str]], key: str) -> str:
    found = values.get(key, [])
    if len(found) != 1:
        raise ValidationError(f"{key} count is {len(found)}, expected one")
    return found[0]


def section(lines: list[str], label: str) -> list[str]:
    begin = f"__OBSERVER_{label}_BEGIN__"
    end = f"__OBSERVER_{label}_END__"
    if lines.count(begin) != 1 or lines.count(end) != 1:
        raise ValidationError(f"{label.lower()} observer delimiters changed")
    start, finish = lines.index(begin), lines.index(end)
    if finish <= start + 1:
        raise ValidationError(f"{label.lower()} observer section is empty")
    return lines[start + 1 : finish]


def parse_snapshot(lines: list[str], parent):
    match = HEADER.fullmatch(lines[0])
    if not match:
        raise ValidationError("observer ABI-v2 header changed")
    state, count_text, overflow_text, up_text, down_text = match.groups()
    count, overflow, up_tx, down_tx = map(
        int, (count_text, overflow_text, up_text, down_text)
    )
    if count > 256 or len(lines[1:]) != count:
        raise ValidationError("observer count exceeds capacity or line count")
    records = []
    for line in lines[1:]:
        record_match = BASE.fullmatch(line)
        if not record_match:
            raise ValidationError(f"malformed observer record: {line}")
        seq, ns, tx, event, phase, target, actor, online, payload = record_match.groups()
        records.append(
            parent.Record(
                sequence=int(seq),
                nanoseconds=int(ns),
                transaction=int(tx),
                event=event,
                phase=int(phase),
                target=int(target),
                actor=int(actor),
                online=int(online, 16),
                payload=parent.parse_payload(int(seq), payload),
            )
        )
    if [record.sequence for record in records] != list(range(1, count + 1)):
        raise ValidationError("latch sequence is not exact contiguous append order")
    if state == "wait-up" and (count or up_tx or down_tx or overflow):
        raise ValidationError("wait-up metadata is inconsistent")
    if state != "wait-up" and not up_tx:
        raise ValidationError("started latch lacks up transaction")
    if state in ("capture-down", "frozen-complete", "frozen-down-failed"):
        if not down_tx or down_tx == up_tx:
            raise ValidationError("down transaction is absent or aliases up")
    if state == "frozen-overflow" and overflow != 1:
        raise ValidationError("overflow state lacks overflow marker")
    if state != "frozen-overflow" and overflow:
        raise ValidationError("unexpected overflow marker")
    return state, count, overflow, up_tx, down_tx, records


def validate_complete(parsed, parent) -> None:
    state, _, overflow, up_tx, down_tx, records = parsed
    if state != "frozen-complete" or overflow:
        raise ValidationError("complete validator received non-complete state")
    if any(record.target != 8 for record in records):
        raise ValidationError("complete latch contains non-CPU8 record")
    grouped = collections.defaultdict(list)
    for record in records:
        parent.validate_payload(record)
        grouped[record.transaction].append(record)
    if set(grouped) != {up_tx, down_tx}:
        raise ValidationError("complete latch contains an unrelated transaction")
    if [record.transaction for record in records] != [up_tx] * len(grouped[up_tx]) + [
        down_tx
    ] * len(grouped[down_tx]):
        raise ValidationError("up/down transactions are not contiguous")
    parent.validate_up(up_tx, grouped[up_tx])
    parent.validate_down(down_tx, grouped[down_tx])


def validate(text: str) -> dict[str, str | int]:
    parent = load_parent()
    lines = text.splitlines()
    first_lines = section(lines, "FIRST")
    second_lines = section(lines, "SECOND")
    excluded = set(first_lines + second_lines)
    values: dict[str, list[str]] = {}
    inside = False
    for line in lines:
        if line.startswith("__OBSERVER_"):
            inside = line.endswith("_BEGIN__")
            continue
        if inside or line in excluded:
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            values.setdefault(key, []).append(value)
    for key, expected in EXPECTED.items():
        if one(values, key) != expected:
            raise ValidationError(f"{key} changed")
    before, after = one(values, "boot_id_before_sha256"), one(
        values, "boot_id_after_sha256"
    )
    if not HEX64.fullmatch(before) or after != before:
        raise ValidationError("boot ID hash is malformed or changed")
    first = parse_snapshot(first_lines, parent)
    second = parse_snapshot(second_lines, parent)
    identical = first_lines == second_lines
    reported_identical = one(values, "observer_snapshots_identical")
    if reported_identical != ("yes" if identical else "no"):
        raise ValidationError("reported snapshot stability disagrees")
    if int(one(values, "observer_first_lines")) != len(first_lines) or int(
        one(values, "observer_second_lines")
    ) != len(second_lines):
        raise ValidationError("reported observer line totals disagree")
    state = second[0]
    if state in TERMINAL and not identical:
        raise ValidationError("terminal latch changed across delayed reads")
    disposition = "preserve-incomplete-no-stimulus"
    owner_validation = "not-applicable"
    if state == "frozen-complete":
        validate_complete(second, parent)
        disposition = "accepted-first-natural-cpu8-pair"
        owner_validation = "passed"
    elif state.startswith("frozen-"):
        disposition = "preserve-terminal-failure-no-retry"
    return {
        "observer_state": state,
        "observer_count": second[1],
        "observer_overflow": second[2],
        "up_transaction": second[3],
        "down_transaction": second[4],
        "snapshots_identical": "yes" if identical else "no",
        "owner_transition_validation": owner_validation,
        "formal_disposition": disposition,
        "runtime_stimulus": "none",
        "next_action": "return-to-known-good-gemian-and-review",
    }


def read_regular(path: pathlib.Path) -> str:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValidationError("capture is missing, empty, or unsafe")
    return path.read_text()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = validate(read_regular(args.capture))
    except (OSError, UnicodeError, ValueError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=gemian-a72-first-cycle-latch-passive")
    for key, value in result.items():
        print(f"{key}={value}")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
