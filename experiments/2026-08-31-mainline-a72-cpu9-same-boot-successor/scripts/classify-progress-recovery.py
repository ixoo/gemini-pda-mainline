#!/usr/bin/env python3
"""Classify the exact CPU9 progress lane after changed-cycle recovery."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import struct
import sys


SOURCE_SHA256 = "c98379b6838d3f14b927a97cebc43af3bd02ce3cc9f3eed5693b39cd697c5673"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-recovery.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU8/CPU9 recovery classifier changed")


def load_source():
    spec = importlib.util.spec_from_file_location("cpu9_transition_recovery", SOURCE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_source()
PROGRESS_MAX_STAGE = 10
PROGRESS_STAGES = {
    1: "cpu8-proof",
    2: "ready-token",
    3: "derive",
    4: "publish",
    5: "prepare",
    6: "add-cpu-dispatch",
    7: "binder-entry",
    8: "ledger-begin-enter",
    9: "ledger-begin-return",
    10: "add-cpu-return",
}


def committed_header(data: bytes) -> bool:
    BASE.require(len(data) == BASE.HEADER_BYTES, "pstore-header-size-mismatch")
    signature, start, size = struct.unpack("<3I", data)
    return (
        signature == BASE.PSTORE_SIGNATURE
        and start == BASE.PAYLOAD_BYTES
        and size == BASE.PAYLOAD_BYTES
    )


def ordinal(record) -> int:
    BASE.require(record.phase in {1, 2}, "progress-phase-is-not-before-or-after")
    BASE.require(record.terminal == 0, "progress-terminal-is-not-zero")
    return (record.stage - 1) * 2 + record.phase


def progress_records(payload: bytes, cpu8_attempt_id: int):
    latest, records = BASE.latest_record(payload, PROGRESS_MAX_STAGE)
    BASE.require(
        all(record.attempt_id == cpu8_attempt_id for record in records),
        "progress-attempt-does-not-match-CPU8-terminal",
    )
    ordered = sorted(records, key=lambda record: record.generation)
    for before, after in zip(ordered, ordered[1:]):
        BASE.require(
            after.generation == before.generation + 1,
            "progress-generations-are-not-consecutive",
        )
        BASE.require(
            ordinal(after) == ordinal(before) + 1,
            "progress-commits-are-not-consecutive",
        )
    return latest, records


def classify(
    cpu8_payload: bytes,
    cpu9_payload: bytes | None,
    cpu9_header: bytes,
    progress_payload: bytes | None,
    progress_header: bytes,
    record3_header: bytes,
):
    base_result, cpu8_latest, cpu8_records, cpu9_latest = BASE.classify(
        cpu8_payload, cpu9_payload, cpu9_header, record3_header
    )
    if progress_payload is None:
        BASE.require(
            BASE.logical_empty_header(progress_header),
            "missing-progress-file-but-lane-not-empty",
        )
        BASE.require(cpu9_latest is None, "CPU9-ledger-present-before-progress-start")
        return (
            "cpu8-terminal-progress-not-started",
            base_result,
            cpu8_latest,
            cpu8_records,
            cpu9_latest,
            None,
            (),
        )

    BASE.require(committed_header(progress_header), "progress-header-is-not-committed")
    progress_latest, records = progress_records(
        progress_payload, cpu8_latest.attempt_id
    )
    progress_ordinal = ordinal(progress_latest)
    after_ledger_enter = (8 - 1) * 2 + 2
    before_ledger_return = (9 - 1) * 2 + 1
    if cpu9_latest is None:
        BASE.require(
            progress_ordinal < before_ledger_return,
            "progress-passed-ledger-begin-without-CPU9-ledger",
        )
    else:
        BASE.require(
            progress_ordinal >= after_ledger_enter,
            "CPU9-ledger-precedes-progress-ledger-begin-entry",
        )
    phase = "before" if progress_latest.phase == 1 else "after"
    result = f"cpu9-progress-{phase}-{PROGRESS_STAGES[progress_latest.stage]}"
    return (
        result,
        base_result,
        cpu8_latest,
        cpu8_records,
        cpu9_latest,
        progress_latest,
        records,
    )


def rejected(*args) -> None:
    try:
        classify(*args)
    except BASE.ClassificationError:
        return
    raise AssertionError("invalid progress recovery evidence was accepted")


def payload(*records: bytes) -> bytes:
    return b"".join(records).ljust(BASE.PAYLOAD_BYTES, b"\0")


def self_test() -> None:
    empty = struct.pack("<3I", BASE.PSTORE_SIGNATURE, 0, 0)
    committed = struct.pack(
        "<3I", BASE.PSTORE_SIGNATURE, BASE.PAYLOAD_BYTES, BASE.PAYLOAD_BYTES
    )
    cpu8 = payload(
        BASE.encode_record(
            attempt_id=7, generation=21, phase=3, stage=10, terminal=5
        ),
        BASE.encode_record(
            attempt_id=7, generation=20, phase=2, stage=10, terminal=0
        ),
    )
    progress6 = payload(
        BASE.encode_record(
            attempt_id=7, generation=12, phase=2, stage=6, terminal=0
        ),
        BASE.encode_record(
            attempt_id=7, generation=11, phase=1, stage=6, terminal=0
        ),
    )
    result = classify(cpu8, None, empty, progress6, committed, empty)
    assert result[0] == "cpu9-progress-after-add-cpu-dispatch"
    assert result[5].generation == 12 and len(result[6]) == 2

    result = classify(cpu8, None, empty, None, empty, empty)
    assert result[0] == "cpu8-terminal-progress-not-started"

    progress8 = payload(
        BASE.encode_record(
            attempt_id=7, generation=16, phase=2, stage=8, terminal=0
        ),
        BASE.encode_record(
            attempt_id=7, generation=15, phase=1, stage=8, terminal=0
        ),
    )
    result = classify(cpu8, None, empty, progress8, committed, empty)
    assert result[0] == "cpu9-progress-after-ledger-begin-enter"

    cpu9 = payload(
        BASE.encode_record(
            attempt_id=8, generation=2, phase=2, stage=1, terminal=0
        ),
        BASE.encode_record(
            attempt_id=8, generation=1, phase=1, stage=1, terminal=0
        ),
    )
    progress9 = payload(
        BASE.encode_record(
            attempt_id=7, generation=17, phase=1, stage=9, terminal=0
        ),
        BASE.encode_record(
            attempt_id=7, generation=16, phase=2, stage=8, terminal=0
        ),
    )
    result = classify(cpu8, cpu9, committed, progress9, committed, empty)
    assert result[0] == "cpu9-progress-before-ledger-begin-return"

    wrong_attempt = payload(
        BASE.encode_record(
            attempt_id=9, generation=12, phase=2, stage=6, terminal=0
        ),
        BASE.encode_record(
            attempt_id=9, generation=11, phase=1, stage=6, terminal=0
        ),
    )
    generation_gap = payload(
        BASE.encode_record(
            attempt_id=7, generation=14, phase=2, stage=6, terminal=0
        ),
        BASE.encode_record(
            attempt_id=7, generation=11, phase=1, stage=6, terminal=0
        ),
    )
    sequence_gap = payload(
        BASE.encode_record(
            attempt_id=7, generation=12, phase=1, stage=7, terminal=0
        ),
        BASE.encode_record(
            attempt_id=7, generation=11, phase=1, stage=6, terminal=0
        ),
    )
    for invalid in (
        (cpu8, None, empty, progress6, empty, empty),
        (cpu8, None, empty, None, committed, empty),
        (cpu8, cpu9, committed, progress6, committed, empty),
        (cpu8, None, empty, progress9, committed, empty),
        (cpu8, None, empty, wrong_attempt, committed, empty),
        (cpu8, None, empty, generation_gap, committed, empty),
        (cpu8, None, empty, sequence_gap, committed, empty),
        (cpu8, None, empty, progress6, committed, committed),
    ):
        rejected(*invalid)
    print("cpu9_progress_recovery_classifier_tests=12-of-12-pass")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu8-payload", type=Path)
    parser.add_argument("--cpu9-payload", type=Path)
    parser.add_argument("--cpu9-header-hex")
    parser.add_argument("--progress-payload", type=Path)
    parser.add_argument("--progress-header-hex")
    parser.add_argument("--record3-header-hex")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    BASE.require(args.cpu8_payload is not None, "--cpu8-payload-is-required")
    BASE.require(args.cpu9_header_hex is not None, "--cpu9-header-hex-is-required")
    BASE.require(
        args.progress_header_hex is not None,
        "--progress-header-hex-is-required",
    )
    BASE.require(
        args.record3_header_hex is not None,
        "--record3-header-hex-is-required",
    )
    try:
        result = classify(
            args.cpu8_payload.read_bytes(),
            args.cpu9_payload.read_bytes() if args.cpu9_payload else None,
            bytes.fromhex(args.cpu9_header_hex),
            args.progress_payload.read_bytes() if args.progress_payload else None,
            bytes.fromhex(args.progress_header_hex),
            bytes.fromhex(args.record3_header_hex),
        )
    except (BASE.ClassificationError, OSError, ValueError) as error:
        print("runtime_classification=rejected-attribution")
        print(f"runtime_reason={str(error).replace(' ', '-')}")
        return 3
    (
        classification,
        base_result,
        _,
        _,
        cpu9_latest,
        progress_latest,
        records,
    ) = result
    print(f"runtime_classification={classification}")
    print(f"transition_classification={base_result}")
    print("cpu9_lane=logical-empty" if cpu9_latest is None else "cpu9_lane=committed")
    if progress_latest is None:
        print("progress_lane=logical-empty")
    else:
        print("progress_lane=committed")
        print(f"progress_valid_copies={len(records)}")
        for record in sorted(records, key=lambda item: item.copy):
            print(
                f"progress_copy_{record.copy}=attempt:{record.attempt_id},"
                f"generation:{record.generation},phase:{record.phase},"
                f"stage:{record.stage},terminal:{record.terminal},crc:valid"
            )
        print(f"progress_latest_copy={progress_latest.copy}")
        print(f"progress_latest_attempt_id={progress_latest.attempt_id}")
        print(f"progress_latest_generation={progress_latest.generation}")
        print(f"progress_latest_phase={progress_latest.phase}")
        print(f"progress_latest_stage={progress_latest.stage}")
        print(f"progress_latest_stage_name={PROGRESS_STAGES[progress_latest.stage]}")
    print("record3_lane=logical-empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
