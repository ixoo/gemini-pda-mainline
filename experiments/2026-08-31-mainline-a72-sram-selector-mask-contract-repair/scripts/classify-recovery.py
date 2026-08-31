#!/usr/bin/env python3
"""Classify exact retained records after the selector-mask runtime."""

from __future__ import annotations

import argparse
import importlib.util
import struct
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
VALIDATOR_DIR = (
    REPO_ROOT
    / "experiments/2026-08-28-mainline-a72-admission-durable-candidate/scripts"
)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TRACE = load("selector_mask_recovery_trace", VALIDATOR_DIR / "validate-admission-trace.py")
LEDGER = load("selector_mask_recovery_ledger", VALIDATOR_DIR / "validate-transition-ledger.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def classify(entry: bytes, terminal: bytes, ledger: bytes) -> tuple[str, dict]:
    trace_state, detail = TRACE.classify(entry, terminal)
    ledger_state, latest, copy = LEDGER.classify(ledger)
    require(ledger_state != "raw-header", "transition ledger has raw header")

    if ledger_state == "logical-empty":
        if trace_state == "empty":
            result = "pre-controller-or-retention-failure"
        elif trace_state == "entry-only":
            result = "entry-prerequisite-deferral-or-interruption"
        else:
            result = f"zero-request-{detail}"
    elif trace_state == "empty":
        result = "request-ledger-with-missing-admission-entry"
    elif trace_state == "entry-only":
        result = "request-reached-binder"
    else:
        raise ValueError("zero-request terminal conflicts with request-bearing ledger")

    return result, {
        "trace_state": trace_state,
        "trace_detail": detail,
        "ledger_state": ledger_state,
        "ledger_latest": latest,
        "ledger_copy": copy,
    }


def ledger(*, phase: int = 3, stage: int = 7, terminal: int = 4) -> bytes:
    record = LEDGER.encode_record(
        attempt=0x1122334455667788,
        generation=1,
        phase=phase,
        stage=stage,
        terminal=terminal,
    )
    return (
        struct.pack("<3I", LEDGER.SIGNATURE, LEDGER.PAYLOAD_SIZE, LEDGER.PAYLOAD_SIZE)
        + record
        + bytes(LEDGER.COPY_BYTES)
    )


def rejected(entry: bytes, terminal: bytes, retained: bytes) -> None:
    try:
        classify(entry, terminal, retained)
    except ValueError:
        return
    raise AssertionError("conflicting retained records were accepted")


def self_test() -> None:
    empty_trace = TRACE.make_slot(None)
    entry = TRACE.make_slot(TRACE.ENTRY)
    empty_ledger = (
        struct.pack("<3I", LEDGER.SIGNATURE, 0, 0) + bytes(LEDGER.PAYLOAD_SIZE)
    )
    assert classify(empty_trace, empty_trace, empty_ledger)[0] == (
        "pre-controller-or-retention-failure"
    )
    assert classify(entry, empty_trace, empty_ledger)[0] == (
        "entry-prerequisite-deferral-or-interruption"
    )
    for name, payload in TRACE.TERMINALS.items():
        assert classify(entry, TRACE.make_slot(payload), empty_ledger)[0] == (
            f"zero-request-{name}"
        )
    assert classify(empty_trace, empty_trace, ledger())[0] == (
        "request-ledger-with-missing-admission-entry"
    )
    result, details = classify(entry, empty_trace, ledger())
    assert result == "request-reached-binder"
    assert details["ledger_latest"]["stage"] == 7
    for payload in TRACE.TERMINALS.values():
        rejected(entry, TRACE.make_slot(payload), ledger())
    print("selector_mask_recovery_decision_map_tests=10-of-10-pass")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entry-hex")
    parser.add_argument("--terminal-hex")
    parser.add_argument("--ledger-hex")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    require(
        all((args.entry_hex, args.terminal_hex, args.ledger_hex)),
        "all three retained hex inputs are required",
    )
    try:
        result, details = classify(
            bytes.fromhex(args.entry_hex),
            bytes.fromhex(args.terminal_hex),
            bytes.fromhex(args.ledger_hex),
        )
    except (ValueError, struct.error) as error:
        print("runtime_classification=rejected-attribution")
        print(f"runtime_reason={str(error).replace(' ', '-')}")
        return 3
    print(f"runtime_classification={result}")
    print(f"admission_trace_state={details['trace_state']}")
    print(f"admission_trace_detail={details['trace_detail']}")
    print(f"transition_ledger_state={details['ledger_state']}")
    latest = details["ledger_latest"]
    if latest is None:
        print("transition_ledger_latest_copy=none")
    else:
        print(f"transition_ledger_latest_copy={details['ledger_copy']}")
        for key in ("attempt_id", "generation", "phase", "stage", "terminal"):
            print(f"transition_ledger_latest_{key}={latest[key]}")
    print("result=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
