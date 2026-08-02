#!/usr/bin/env python3
"""Validate and summarize the exact overwritten first-live observer ring."""

from __future__ import annotations

import argparse
import collections
import dataclasses
import hashlib
import pathlib
import re
import stat
import sys


CAPTURE_SHA256 = "c0a8081f809bfff51c1043e46ca9e242af0051e265b718728573fd3479cbdd48"
HEADER = re.compile(
    r"^abi=mt6797-a72-transition-observer-v1 count=([0-9]+) overwritten=([0-9]+)$"
)
BASE = re.compile(
    r"^seq=([0-9]+) ns=([0-9]+) tx=([0-9]+) "
    r"event=(lifecycle|da9214|spm|secure|clock|toprgu|dcm|mutation) "
    r"phase=([0-9]+) target=([0-9]+) actor=([0-9]+) "
    r"online=0x([0-9a-f]{8})(?: (.*))?$"
)

UP_TEMPLATE = [
    ("lifecycle", 1),
    ("lifecycle", 5),
    ("da9214", 6),
    ("spm", 6),
    ("secure", 6),
    ("clock", 6),
    ("dcm", 6),
    ("mutation", 7),
    ("lifecycle", 8),
    ("toprgu", 9),
    ("da9214", 10),
    ("da9214", 11),
    ("mutation", 12),
    ("toprgu", 13),
    ("lifecycle", 15),
    ("lifecycle", 16),
    ("lifecycle", 17),
    ("dcm", 18),
    ("lifecycle", 19),
    ("lifecycle", 20),
    ("da9214", 19),
    ("spm", 19),
    ("secure", 19),
    ("clock", 19),
    ("dcm", 19),
    ("lifecycle", 2),
]
DOWN_TEMPLATE = [
    ("lifecycle", 3),
    ("lifecycle", 21),
    ("lifecycle", 22),
    ("da9214", 22),
    ("spm", 22),
    ("secure", 22),
    ("clock", 22),
    ("dcm", 22),
    ("lifecycle", 23),
    ("dcm", 24),
    ("lifecycle", 25),
    ("da9214", 26),
    ("lifecycle", 27),
    ("lifecycle", 27),
    ("da9214", 27),
    ("spm", 27),
    ("secure", 27),
    ("clock", 27),
    ("dcm", 27),
    ("lifecycle", 4),
]


class ValidationError(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Record:
    sequence: int
    nanoseconds: int
    transaction: int
    event: str
    phase: int
    target: int
    actor: int
    online: int
    payload: dict[str, str]


def number(value: str, label: str) -> int:
    try:
        return int(value, 0)
    except ValueError as exc:
        raise ValidationError(f"{label} is not an integer: {value}") from exc


def field(record: Record, name: str) -> int:
    if name not in record.payload:
        raise ValidationError(
            f"sequence {record.sequence} {record.event} lacks payload field {name}"
        )
    return number(record.payload[name], f"sequence {record.sequence} {name}")


def parse_payload(sequence: int, text: str | None) -> dict[str, str]:
    payload: dict[str, str] = {}
    for token in (text or "").split():
        if "=" not in token:
            raise ValidationError(f"sequence {sequence} has an unkeyed payload token")
        key, value = token.split("=", 1)
        if not key or not value or key in payload:
            raise ValidationError(f"sequence {sequence} has a malformed payload")
        payload[key] = value
    return payload


def parse(text: str) -> tuple[int, list[Record]]:
    lines = text.splitlines()
    if not lines:
        raise ValidationError("capture is empty")
    header = HEADER.fullmatch(lines[0])
    if not header:
        raise ValidationError("observer ABI header changed")
    count, overwritten = map(int, header.groups())
    if count != 256 or overwritten != 3474 or len(lines[1:]) != count:
        raise ValidationError("exact ring count, overwrite total, or line count changed")
    records: list[Record] = []
    for line in lines[1:]:
        match = BASE.fullmatch(line)
        if not match:
            raise ValidationError(f"malformed observer record: {line}")
        sequence, ns, transaction, event, phase, target, actor, online, payload = (
            match.groups()
        )
        records.append(
            Record(
                sequence=int(sequence),
                nanoseconds=int(ns),
                transaction=int(transaction),
                event=event,
                phase=int(phase),
                target=int(target),
                actor=int(actor),
                online=int(online, 16),
                payload=parse_payload(int(sequence), payload),
            )
        )
    sequences = [record.sequence for record in records]
    if sequences != list(range(overwritten + 1, overwritten + count + 1)):
        raise ValidationError("ring sequences are not the exact contiguous retained tail")
    return overwritten, records


def validate_payload(record: Record) -> None:
    if record.target != 8 or not 0 <= record.actor <= 9 or not 0 <= record.phase <= 27:
        raise ValidationError(f"sequence {record.sequence} has an unexpected CPU identity")
    if record.event == "lifecycle":
        for name in ("result", "arg0", "arg1"):
            field(record, name)
    elif record.event == "da9214":
        for name in (
            "page_before",
            "page_selected",
            "buck_before",
            "buck_after",
            "vsel",
            "page_after",
            "status",
            "valid",
        ):
            field(record, name)
        if field(record, "status") != 0:
            raise ValidationError(f"sequence {record.sequence} has a DA9214 error")
        if any(
            field(record, name) != 0x80
            for name in ("page_before", "page_selected", "page_after")
        ):
            raise ValidationError(f"sequence {record.sequence} did not preserve PAGE_REVERT")
        expected_valid = 0x005F if record.phase in (10, 26) else 0x001F
        if field(record, "valid") != expected_valid:
            raise ValidationError(f"sequence {record.sequence} has incomplete DA9214 validity")
    elif record.event == "spm":
        if field(record, "valid") != 0x3F:
            raise ValidationError(f"sequence {record.sequence} has incomplete SPM validity")
        for index in range(6):
            field(record, f"r{index}")
    elif record.event == "secure":
        if field(record, "valid") != 0xFFF or field(record, "stable") != 1:
            raise ValidationError(f"sequence {record.sequence} has unstable secure evidence")
        sentinel = field(record, "sentinel_after")
        values = [field(record, f"r{index}") for index in range(12)]
        if sentinel != values[0]:
            raise ValidationError(f"sequence {record.sequence} secure sentinel changed")
    elif record.event == "clock":
        for name in ("pll_con1", "muxsel", "ckdiv"):
            field(record, name)
        if field(record, "status") != 0 or field(record, "semaphore") != 0x000F:
            raise ValidationError(f"sequence {record.sequence} has invalid clock evidence")
    elif record.event in ("toprgu", "mutation"):
        before = field(record, "before")
        requested = field(record, "requested")
        after = field(record, "after")
        mask = field(record, "mask")
        if record.event == "mutation":
            field(record, "address")
        if field(record, "status") != 0 or (after & mask) != (requested & mask):
            raise ValidationError(f"sequence {record.sequence} mutation readback mismatched")
        if before < 0:
            raise ValidationError(f"sequence {record.sequence} has invalid mutation pre-state")
    elif record.event == "dcm":
        for name in ("before", "toggle", "final", "mask", "on"):
            field(record, name)


def timestamp_template(records: list[Record]) -> list[tuple[str, int]]:
    return [
        (record.event, record.phase)
        for record in sorted(records, key=lambda item: (item.nanoseconds, item.sequence))
    ]


def lifecycle_results(records: list[Record], phase: int) -> list[int]:
    return [
        field(record, "result")
        for record in sorted(records, key=lambda item: (item.nanoseconds, item.sequence))
        if record.event == "lifecycle" and record.phase == phase
    ]


def validate_up(transaction: int, records: list[Record]) -> None:
    if timestamp_template(records) != UP_TEMPLATE:
        raise ValidationError(f"up transaction {transaction} ordering changed")
    if any(
        field(record, "result") != 0
        for record in records
        if record.event == "lifecycle"
    ):
        raise ValidationError(f"up transaction {transaction} has a failed lifecycle return")
    raw = next(record for record in records if record.event == "lifecycle" and record.phase == 16)
    mapped = next(
        record for record in records if record.event == "lifecycle" and record.phase == 17
    )
    if (field(raw, "arg0"), field(raw, "arg1")) != (
        field(mapped, "arg0"),
        field(mapped, "arg1"),
    ):
        raise ValidationError(f"up transaction {transaction} PSCI identities disagree")
    buck_enable = next(record for record in records if record.event == "da9214" and record.phase == 10)
    if field(buck_enable, "buck_before") != 0 or field(buck_enable, "buck_after") != 1:
        raise ValidationError(f"up transaction {transaction} lacks the buck-enable transition")


def validate_down(transaction: int, records: list[Record]) -> None:
    if timestamp_template(records) != DOWN_TEMPLATE:
        raise ValidationError(f"down transaction {transaction} ordering changed")
    for phase in (3, 21, 22, 23, 4):
        if lifecycle_results(records, phase) != [0]:
            raise ValidationError(f"down transaction {transaction} phase {phase} failed")
    if lifecycle_results(records, 25) != [1] or lifecycle_results(records, 27) != [0, 1]:
        raise ValidationError(f"down transaction {transaction} affinity/final return changed")
    buck_disable = next(
        record for record in records if record.event == "da9214" and record.phase == 26
    )
    if field(buck_disable, "buck_before") != 1 or field(buck_disable, "buck_after") != 0:
        raise ValidationError(f"down transaction {transaction} lacks the buck-disable transition")


def validate(text: str) -> dict[str, str | int]:
    overwritten, records = parse(text)
    for record in records:
        validate_payload(record)
    grouped: dict[int, list[Record]] = collections.defaultdict(list)
    for record in records:
        grouped[record.transaction].append(record)
    for transaction, group in grouped.items():
        indices = [records.index(record) for record in group]
        if indices != list(range(indices[0], indices[-1] + 1)):
            raise ValidationError(f"transaction {transaction} is not contiguous in the ring")

    up_transactions: list[int] = []
    down_transactions: list[int] = []
    partial_transactions: list[int] = []
    for transaction in sorted(grouped):
        template = collections.Counter(
            (record.event, record.phase) for record in grouped[transaction]
        )
        if template == collections.Counter(UP_TEMPLATE):
            validate_up(transaction, grouped[transaction])
            up_transactions.append(transaction)
        elif template == collections.Counter(DOWN_TEMPLATE):
            validate_down(transaction, grouped[transaction])
            down_transactions.append(transaction)
        else:
            partial_transactions.append(transaction)
    if up_transactions != [182, 184, 186, 188, 190]:
        raise ValidationError("exact complete CPU8-up transaction set changed")
    if down_transactions != [181, 183, 185, 187, 189, 191]:
        raise ValidationError("exact complete CPU8-down transaction set changed")
    if partial_transactions != [180]:
        raise ValidationError("exact partial transaction set changed")

    inversions = []
    for prior, current in zip(records, records[1:]):
        if current.nanoseconds < prior.nanoseconds:
            inversions.append((prior, current))
    if len(inversions) != 1 or inversions[0][0].sequence != 3703 or inversions[0][1].sequence != 3704:
        raise ValidationError("cross-CPU sequence/timestamp inversion changed")

    phase22_vsel = collections.Counter(
        field(record, "vsel")
        for record in records
        if record.event == "da9214" and record.phase == 22
    )
    if phase22_vsel != collections.Counter({0x32: 2, 0x3A: 4}):
        raise ValidationError("last-A72-offline VSEL distribution changed")
    return {
        "ring_count": len(records),
        "ring_overwritten": overwritten,
        "sequence_range": f"{records[0].sequence}-{records[-1].sequence}",
        "transaction_range": f"{min(grouped)}-{max(grouped)}",
        "complete_cpu8_up_transactions": ",".join(map(str, up_transactions)),
        "complete_cpu8_down_transactions": ",".join(map(str, down_transactions)),
        "partial_transactions": ",".join(map(str, partial_transactions)),
        "cpu9_records": 0,
        "da9214_status_and_page_restore": "passed",
        "secure_validity_and_stability": "passed",
        "clock_immediate_snapshot": "passed",
        "mutation_masked_readback": "passed",
        "psci_raw_mapped_identity": "passed",
        "timestamp_ordering": "passed",
        "sequence_timestamp_inversions": len(inversions),
        "phase22_vsel_counts": "0x32:2,0x3a:4",
        "retained_transition_validation": "passed",
        "formal_disposition": "inconclusive-overwritten-no-clean-initial-attribution",
        "pulse_permitted": "no",
    }


def read_exact(path: pathlib.Path) -> str:
    info = path.lstat()
    if path.is_symlink() or not stat.S_ISREG(info.st_mode) or not info.st_size:
        raise ValidationError("capture is missing, empty, or unsafe")
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != CAPTURE_SHA256:
        raise ValidationError("exact runtime capture SHA-256 changed")
    return payload.decode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=pathlib.Path)
    args = parser.parse_args()
    try:
        result = validate(read_exact(args.capture))
    except (OSError, UnicodeError, ValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=gemian-a72-overwritten-ring-v1")
    print(f"capture_sha256={CAPTURE_SHA256}")
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
