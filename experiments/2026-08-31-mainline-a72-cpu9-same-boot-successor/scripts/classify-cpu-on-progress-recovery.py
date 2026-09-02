#!/usr/bin/env python3
"""Classify retained CPU9 CPU_ON substage evidence after recovery."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys


SOURCE_SHA256 = "c98379b6838d3f14b927a97cebc43af3bd02ce3cc9f3eed5693b39cd697c5673"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-recovery.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU8/CPU9 recovery classifier changed")

spec = importlib.util.spec_from_file_location("cpu9_recovery_base", SOURCE)
assert spec is not None and spec.loader is not None
BASE = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = BASE
spec.loader.exec_module(BASE)

CPU_ON_STAGES = {
    1: "p30e-prepare",
    2: "membership-begin",
    3: "p30e-arm",
    4: "generic-cpu-boot",
}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise BASE.ClassificationError(reason)


def classify(payloads: tuple[bytes, bytes, bytes, bytes]):
    cpu8_latest, cpu8_records = BASE.latest_record(payloads[0], 10)
    cpu9_latest, cpu9_records = BASE.latest_record(payloads[1], 5)
    controller_latest, controller_records = BASE.latest_record(payloads[2], 10)
    cpu_on_latest, cpu_on_records = BASE.latest_record(payloads[3], 4)

    require(
        (cpu8_latest.phase, cpu8_latest.stage, cpu8_latest.terminal) == (3, 10, 5),
        "CPU8-terminal-proof-missing",
    )
    require(cpu9_latest.attempt_id != cpu8_latest.attempt_id,
            "CPU8-and-CPU9-attempt-identities-collide")
    require(
        (cpu9_latest.phase, cpu9_latest.stage, cpu9_latest.terminal) == (1, 2, 0),
        "CPU9-transition-is-not-before-CPU-ON",
    )
    require(controller_latest.attempt_id == cpu8_latest.attempt_id,
            "controller-attempt-does-not-match-CPU8")
    require(
        (controller_latest.phase, controller_latest.stage,
         controller_latest.terminal) == (2, 9, 0),
        "controller-did-not-return-from-ledger-begin",
    )
    require(cpu_on_latest.attempt_id == cpu9_latest.attempt_id,
            "CPU-ON-progress-attempt-does-not-match-CPU9")
    ordered = sorted(cpu_on_records, key=lambda record: record.generation)
    require(len(ordered) == 2, "CPU-ON-progress-does-not-have-two-valid-copies")
    require(ordered[1].generation == ordered[0].generation + 1,
            "CPU-ON-progress-generations-are-not-consecutive")
    require(
        (ordered[0].phase, ordered[0].stage, ordered[0].terminal) == (2, 1, 0),
        "CPU-ON-progress-did-not-return-from-P30E-prepare",
    )
    require(
        (ordered[1].phase, ordered[1].stage, ordered[1].terminal) == (1, 2, 0),
        "CPU-ON-progress-latest-is-not-before-membership-begin",
    )
    return (
        cpu8_latest, cpu8_records, cpu9_latest, cpu9_records,
        controller_latest, controller_records, cpu_on_latest, cpu_on_records,
    )


def payload(*records: bytes) -> bytes:
    return b"".join(records).ljust(BASE.PAYLOAD_BYTES, b"\0")


def self_test() -> None:
    cpu8 = payload(
        BASE.encode_record(attempt_id=1, generation=21, phase=3, stage=10,
                           terminal=5),
        BASE.encode_record(attempt_id=1, generation=20, phase=2, stage=10,
                           terminal=0),
    )
    cpu9 = payload(
        BASE.encode_record(attempt_id=2, generation=3, phase=1, stage=2,
                           terminal=0),
        BASE.encode_record(attempt_id=2, generation=2, phase=2, stage=1,
                           terminal=0),
    )
    controller = payload(
        BASE.encode_record(attempt_id=1, generation=17, phase=1, stage=9,
                           terminal=0),
        BASE.encode_record(attempt_id=1, generation=18, phase=2, stage=9,
                           terminal=0),
    )
    classify((cpu8, cpu9, controller, cpu9))
    mutations = []
    for index in range(4):
        damaged = [cpu8, cpu9, controller, cpu9]
        damaged[index] = bytes(len(damaged[index]))
        mutations.append(tuple(damaged))
    wrong_latest = payload(
        BASE.encode_record(attempt_id=2, generation=3, phase=1, stage=3,
                           terminal=0),
        BASE.encode_record(attempt_id=2, generation=2, phase=2, stage=1,
                           terminal=0),
    )
    mutations.append((cpu8, cpu9, controller, wrong_latest))
    for mutation in mutations:
        try:
            classify(mutation)
        except BASE.ClassificationError:
            continue
        raise AssertionError("invalid CPU_ON recovery evidence was accepted")
    print("cpu_on_progress_recovery_classifier_tests=6-of-6-pass")


def emit_records(name: str, latest, records) -> None:
    print(f"{name}_valid_copies={len(records)}")
    for record in sorted(records, key=lambda item: item.copy):
        print(
            f"{name}_copy_{record.copy}=attempt:{record.attempt_id},"
            f"generation:{record.generation},phase:{record.phase},"
            f"stage:{record.stage},terminal:{record.terminal},crc:valid"
        )
    print(f"{name}_latest_copy={latest.copy}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pstore-dir", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    require(args.pstore_dir is not None, "--pstore-dir-is-required")
    try:
        payloads = tuple(
            (args.pstore_dir / f"dmesg-ramoops-{index}").read_bytes()
            for index in range(4)
        )
        result = classify(payloads)
    except (BASE.ClassificationError, OSError) as error:
        print("runtime_classification=rejected-attribution")
        print(f"runtime_reason={str(error).replace(' ', '-')}")
        return 3
    names = ("cpu8", "cpu9", "controller", "cpu_on_progress")
    for index, name in enumerate(names):
        emit_records(name, result[index * 2], result[index * 2 + 1])
    latest = result[6]
    print("runtime_classification=cpu-on-progress-before-membership-begin")
    print(f"cpu_on_progress_latest_stage_name={CPU_ON_STAGES[latest.stage]}")
    print("p30e_prepare=returned")
    print("membership_begin=entered-not-returned")
    print("p30e_arm=not-reached")
    print("generic_cpu_boot=not-reached")
    print("cpu9_online=no")
    print("next_selected_branch=CPUHP-lock-held-membership-begin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
