#!/usr/bin/env python3
"""Validate a passive two-read ABI-v3 pre-isolation rollback capture."""

from __future__ import annotations

import argparse
import hashlib
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
    r"^abi=mt6797-a72-transition-observer-v3 "
    r"state=(wait-up|capture-up|rolled-back|fault-retain|rejected-prestate|"
    r"frozen-complete|frozen-up-failed|frozen-down-failed|frozen-cpu9|"
    r"frozen-protocol|frozen-overflow) count=([0-9]+) overflow=([01]) "
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
    "rolled-back",
    "fault-retain",
    "rejected-prestate",
    "frozen-complete",
    "frozen-up-failed",
    "frozen-down-failed",
    "frozen-cpu9",
    "frozen-protocol",
    "frozen-overflow",
}
FORBIDDEN_PHASES = set(range(17, 33))
ROLLED_TEMPLATE = [
    ("lifecycle", 1),
    ("clock", 6),
    ("secure", 6),
    ("dcm", 6),
    ("da9214", 6),
    ("mutation", 6),
    ("mutation", 6),
    ("toprgu", 6),
    ("mutation", 7),
    ("toprgu", 9),
    ("da9214", 10),
    ("da9214", 11),
    ("lifecycle", 12),
    ("da9214", 13),
    ("mutation", 14),
    ("mutation", 14),
    ("toprgu", 15),
    ("da9214", 16),
    ("mutation", 16),
    ("mutation", 16),
    ("toprgu", 16),
    ("secure", 16),
    ("dcm", 16),
    ("clock", 16),
    ("da9214", 16),
    ("spm", 16),
    ("secure", 16),
    ("clock", 16),
    ("dcm", 16),
    ("lifecycle", 16),
]
REJECTED_TEMPLATE = [
    ("lifecycle", 1),
    ("clock", 6),
    ("secure", 6),
    ("dcm", 6),
    ("da9214", 6),
    ("mutation", 6),
    ("mutation", 6),
    ("toprgu", 6),
    ("da9214", 16),
    ("spm", 16),
    ("secure", 16),
    ("clock", 16),
    ("dcm", 16),
    ("lifecycle", 16),
]
EXPECTED = {
    "experiment": "gemian-a72-preiso-rollback-passive",
    "kernel_release": "3.18.41+",
    "architecture": "aarch64",
    "build_identity": "#1 SMP PREEMPT Sun Aug 2 21:22:32 UTC 2026",
    "root": "/dev/mmcblk0p29",
    "possible": "0-9",
    "present": "0-9",
    "observer_path": "/proc/mt6797_a72_transition",
    "observer_mode": "400",
    "state_changing_writes": "none",
    "load_workers": "0",
    "cpu_online_writes": "none",
    "cpu8": "0",
    "cpu9": "0",
    "online": "0-7",
    "runtime_stimulus": "none",
    "boot_id_stable": "yes",
    "status": "completed",
}


class ValidationError(Exception):
    pass


def load_parent():
    expected = "5f5ee7f04caad30e12674de69e86d38649a0ea10d4fb412c5f0a9c5ad29872dc"
    if hashlib.sha256(PARENT_ANALYZER.read_bytes()).hexdigest() != expected:
        raise ValidationError("pinned parent transition analyzer changed")
    spec = importlib.util.spec_from_file_location(
        "bounded_transition_analyzer", PARENT_ANALYZER
    )
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
    if finish <= start:
        raise ValidationError(f"{label.lower()} observer section is malformed")
    return lines[start + 1 : finish]


def parse_snapshot(lines: list[str], parent):
    if not lines:
        raise ValidationError("observer snapshot is empty")
    match = HEADER.fullmatch(lines[0])
    if not match:
        raise ValidationError("observer ABI-v3 header changed")
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
        seq, ns, tx, event, phase, target, actor, online, payload = (
            record_match.groups()
        )
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
    if down_tx:
        raise ValidationError("pre-isolation capture contains a down transaction")
    if state == "frozen-overflow" and overflow != 1:
        raise ValidationError("overflow state lacks overflow marker")
    if state != "frozen-overflow" and overflow:
        raise ValidationError("unexpected overflow marker")
    for record in records:
        if record.target != 8 or not 0 <= record.actor <= 9:
            raise ValidationError("capture contains a non-CPU8 target or invalid actor")
        if record.transaction != up_tx:
            raise ValidationError("capture contains an unrelated transaction")
        if record.online & 0x300:
            raise ValidationError("capture observed CPU8 or CPU9 online")
        if record.phase in FORBIDDEN_PHASES or not 1 <= record.phase <= 32:
            raise ValidationError("capture crossed a forbidden A72 phase")
        validate_payload_shape(record, parent)
    return state, count, overflow, up_tx, down_tx, records


def validate_payload_shape(record, parent) -> None:
    if record.event == "lifecycle":
        names = ("result", "arg0", "arg1")
    elif record.event == "da9214":
        names = (
            "page_before", "page_selected", "buck_before", "buck_after",
            "vsel", "page_after", "status", "valid",
        )
    elif record.event == "spm":
        names = ("valid", *(f"r{index}" for index in range(6)))
    elif record.event == "secure":
        names = (
            "valid", "stable", "sentinel_after",
            *(f"r{index}" for index in range(12)),
        )
    elif record.event == "clock":
        names = ("pll_con1", "muxsel", "ckdiv", "status", "semaphore")
    elif record.event == "toprgu":
        names = ("before", "requested", "after", "mask", "status")
    elif record.event == "mutation":
        names = ("address", "before", "requested", "after", "mask", "status")
    elif record.event == "dcm":
        names = ("before", "toggle", "final", "mask", "on")
    else:
        raise ValidationError("unknown event")
    for name in names:
        parent.field(record, name)


def exact_template(records) -> list[tuple[str, int]]:
    return [(record.event, record.phase) for record in records]


def require(record, parent, **fields: int) -> None:
    for name, expected in fields.items():
        if parent.field(record, name) != expected:
            raise ValidationError(
                f"sequence {record.sequence} {name} changed from {expected:#x}"
            )


def validate_zero_secure(record, parent) -> None:
    require(record, parent, valid=0xFFF, stable=1, sentinel_after=0)
    for index in range(12):
        require(record, parent, **{f"r{index}": 0})


def validate_zero_dcm(record, parent) -> None:
    require(record, parent, before=0, toggle=0, final=0, mask=0x7F)


def validate_da(record, parent, before: int, after: int, validity: int) -> None:
    require(
        record,
        parent,
        page_before=0x80,
        page_selected=0x80,
        buck_before=before,
        buck_after=after,
        vsel=0x46,
        page_after=0x80,
        status=0,
        valid=validity,
    )


def validate_mutation(
    record, parent, address: int, before: int, requested: int, after: int
) -> None:
    require(
        record,
        parent,
        address=address,
        before=before,
        requested=requested,
        after=after,
        mask=0xFFFFFFFF,
        status=0,
    )


def validate_toprgu(record, parent, before_set: bool, after_set: bool) -> None:
    before = parent.field(record, "before")
    after = parent.field(record, "after")
    requested = parent.field(record, "requested")
    require(record, parent, mask=0x800, status=0)
    if bool(before & 0x800) != before_set or bool(after & 0x800) != after_set:
        raise ValidationError("TOPRGU ownership transition changed")
    if bool(requested & 0x800) != after_set:
        raise ValidationError("TOPRGU requested bit disagrees with result")


def validate_clock(record, parent) -> tuple[int, int, int]:
    require(record, parent, status=0, semaphore=0xF)
    return tuple(parent.field(record, name) for name in ("pll_con1", "muxsel", "ckdiv"))


def validate_rolled_back(parsed, parent) -> None:
    state, count, overflow, _, _, records = parsed
    if state != "rolled-back" or count != 30 or overflow:
        raise ValidationError("rolled-back header changed")
    if exact_template(records) != ROLLED_TEMPLATE:
        raise ValidationError("rolled-back event ordering changed")
    require(records[0], parent, result=0)
    entry_clock = validate_clock(records[1], parent)
    validate_zero_secure(records[2], parent)
    validate_zero_dcm(records[3], parent)
    validate_da(records[4], parent, 0, 0, 0x5F)
    validate_mutation(records[5], parent, 0x10006218, 0x10132, 0x10132, 0x10132)
    validate_mutation(records[6], parent, 0x10006290, 0x2, 0x2, 0x2)
    validate_toprgu(records[7], parent, False, False)
    validate_mutation(records[8], parent, 0x10006218, 0x10132, 0x10133, 0x10133)
    validate_toprgu(records[9], parent, False, True)
    validate_da(records[10], parent, 0, 1, 0x5F)
    validate_da(records[11], parent, 1, 1, 0x5F)
    require(records[12], parent, result=0)
    validate_da(records[13], parent, 1, 0, 0x5F)
    validate_mutation(records[14], parent, 0x10006290, 0x2, 0x2, 0x2)
    validate_mutation(records[15], parent, 0x10006218, 0x10133, 0x10132, 0x10132)
    validate_toprgu(records[16], parent, True, False)
    validate_da(records[17], parent, 0, 0, 0x5F)
    validate_mutation(records[18], parent, 0x10006218, 0x10132, 0x10132, 0x10132)
    validate_mutation(records[19], parent, 0x10006290, 0x2, 0x2, 0x2)
    validate_toprgu(records[20], parent, False, False)
    validate_zero_secure(records[21], parent)
    validate_zero_dcm(records[22], parent)
    final_clock = validate_clock(records[23], parent)
    validate_da(records[24], parent, 0, 0, 0x1F)
    require(records[25], parent, valid=0x3F, r4=0x10132, r5=0x2)
    validate_zero_secure(records[26], parent)
    fixed_clock = validate_clock(records[27], parent)
    validate_zero_dcm(records[28], parent)
    require(records[29], parent, result=1)
    if entry_clock != final_clock or final_clock != fixed_clock:
        raise ValidationError("entry/final clock state changed")


def validate_rejected(parsed, parent) -> None:
    state, count, overflow, _, _, records = parsed
    if state != "rejected-prestate" or count != 14 or overflow:
        raise ValidationError("rejected-prestate header changed")
    if exact_template(records) != REJECTED_TEMPLATE:
        raise ValidationError("rejected-prestate event ordering changed")
    require(records[-1], parent, result=3)
    for record in records:
        if record.event in ("mutation", "toprgu"):
            if parent.field(record, "before") != parent.field(record, "after"):
                raise ValidationError("pre-state rejection contains a hardware change")
    entry_da = records[4]
    if parent.field(entry_da, "valid") & 0xC:
        if parent.field(entry_da, "buck_before") != parent.field(entry_da, "buck_after"):
            raise ValidationError("pre-state rejection changed BUCKB")


def validate_fault(parsed, parent) -> None:
    state, count, overflow, _, _, records = parsed
    if state != "fault-retain" or not 15 <= count <= 30 or overflow:
        raise ValidationError("fault-retain bounds changed")
    if exact_template(records[:8]) != ROLLED_TEMPLATE[:8]:
        raise ValidationError("fault-retain lacks the complete entry gate")
    terminal = records[-1]
    if terminal.event != "lifecycle" or terminal.phase != 16:
        raise ValidationError("fault-retain terminal record changed")
    require(terminal, parent, result=2)


def validate(text: str) -> dict[str, str | int]:
    parent = load_parent()
    lines = text.splitlines()
    first_lines = section(lines, "FIRST")
    second_lines = section(lines, "SECOND")
    values: dict[str, list[str]] = {}
    inside = False
    for line in lines:
        if line.startswith("__OBSERVER_"):
            inside = line.endswith("_BEGIN__")
            continue
        if inside:
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            values.setdefault(key, []).append(value)
    for key, expected in EXPECTED.items():
        if one(values, key) != expected:
            raise ValidationError(f"{key} changed")
    before = one(values, "boot_id_before_sha256")
    after = one(values, "boot_id_after_sha256")
    if not HEX64.fullmatch(before) or after != before:
        raise ValidationError("boot ID hash is malformed or changed")
    first = parse_snapshot(first_lines, parent)
    second = parse_snapshot(second_lines, parent)
    identical = first_lines == second_lines
    if one(values, "observer_snapshots_identical") != ("yes" if identical else "no"):
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
    if state == "rolled-back":
        validate_rolled_back(second, parent)
        disposition = "accepted-pre-isolation-rollback"
        owner_validation = "passed"
    elif state == "rejected-prestate":
        validate_rejected(second, parent)
        disposition = "preserve-prestate-rejection-no-retry"
        owner_validation = "passed-no-write"
    elif state == "fault-retain":
        validate_fault(second, parent)
        disposition = "preserve-fault-retain-reset-recovery"
        owner_validation = "failed-closed"
    elif state.startswith("frozen-"):
        disposition = "reject-boundary-violation-no-retry"
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
    print("validation=gemian-a72-preiso-rollback-passive")
    for key, value in result.items():
        print(f"{key}={value}")
    print("hardware_write=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
