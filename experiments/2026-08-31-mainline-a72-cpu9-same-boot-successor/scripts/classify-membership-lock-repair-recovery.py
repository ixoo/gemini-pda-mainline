#!/usr/bin/env python3
"""Classify retained patch-0480 CPU9 membership-lock repair evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
from pathlib import Path
import sys


SOURCE_SHA256 = "c98379b6838d3f14b927a97cebc43af3bd02ce3cc9f3eed5693b39cd697c5673"
SCRIPT = Path(__file__).resolve()
SOURCE = SCRIPT.with_name("classify-recovery.py")
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
    raise SystemExit("source CPU8/CPU9 recovery decoder changed")

spec = importlib.util.spec_from_file_location("cpu9_recovery_base", SOURCE)
assert spec is not None and spec.loader is not None
BASE = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = BASE
spec.loader.exec_module(BASE)

CPU8_ONLINE = (3, 10, 5)
CPU9_ONLINE = (3, 5, 5)
CPU9_TERMINALS = {
    (1, 1): "prestate-failure",
    (2, 2): "cpu-on-failure",
    (3, 3): "online-wait-failure",
    (4, 4): "ipi-failure",
    (5, 4): "membership-failure",
    (5, 5): "cpu9-online-proof",
}
CPU9_STAGES = {
    1: "prestate",
    2: "cpu-on",
    3: "online-wait",
    4: "ipi",
    5: "membership",
}
CPU_ON_STAGES = {
    1: "p30e-prepare",
    2: "membership-begin",
    3: "p30e-arm",
    4: "generic-cpu-boot",
}
CPU_ON_CLASSIFICATIONS = {
    1: ("cpu-on-progress-before-p30e-prepare", "p30e-prepare"),
    2: ("cpu-on-progress-after-p30e-prepare", "membership-begin-entry-checkpoint"),
    3: ("cpu-on-progress-before-membership-begin", "membership-begin"),
    4: ("cpu-on-progress-after-membership-begin", "p30e-arm-entry-checkpoint"),
    5: ("cpu-on-progress-before-p30e-arm", "p30e-arm"),
    6: ("cpu-on-progress-after-p30e-arm", "generic-cpu-boot-entry-checkpoint"),
    7: ("cpu-on-progress-before-generic-cpu-boot", "generic-cpu-boot"),
    8: ("cpu-on-progress-after-generic-cpu-boot", "cpu9-after-cpu-on-checkpoint"),
}
CPU9_NONTERMINAL_CLASSIFICATIONS = {
    4: ("cpu9-cpu-on-returned", "online-wait"),
    5: ("cpu9-before-online-wait", "online-wait"),
    6: ("cpu9-after-online-wait", "ipi"),
    7: ("cpu9-before-ipi", "ipi"),
    8: ("cpu9-after-ipi", "membership-publish"),
    9: ("cpu9-before-membership-publish", "membership-publish"),
    10: ("cpu9-after-membership-publish", "online-proof-terminal"),
}


@dataclass(frozen=True)
class Result:
    classification: str
    next_branch: str
    cpu8_latest: BASE.Record
    cpu8_records: tuple[BASE.Record, ...]
    cpu9_latest: BASE.Record
    cpu9_records: tuple[BASE.Record, ...]
    controller_latest: BASE.Record
    controller_records: tuple[BASE.Record, ...]
    cpu_on_latest: BASE.Record
    cpu_on_records: tuple[BASE.Record, ...]


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise BASE.ClassificationError(reason)


def nonterminal_rank(record: BASE.Record) -> int:
    require(record.phase in (1, 2) and record.terminal == 0,
            "record-is-not-a-nonterminal-checkpoint")
    return (record.stage - 1) * 2 + record.phase


def validate_copies(name: str, latest: BASE.Record,
                    records: tuple[BASE.Record, ...]) -> None:
    require(all(record.attempt_id == latest.attempt_id for record in records),
            f"{name}-valid-copies-have-different-attempts")
    if len(records) == 2:
        ordered = sorted(records, key=lambda record: record.generation)
        require(ordered[1].generation == ordered[0].generation + 1,
                f"{name}-valid-generations-are-not-consecutive")


def validate_cpu_on_order(records: tuple[BASE.Record, ...]) -> None:
    for record in records:
        require(record.phase in (1, 2) and record.terminal == 0,
                "CPU-ON-progress-has-terminal-or-invalid-phase")
    if len(records) == 2:
        ordered = sorted(records, key=lambda record: record.generation)
        require(nonterminal_rank(ordered[1]) == nonterminal_rank(ordered[0]) + 1,
                "CPU-ON-progress-checkpoints-are-not-adjacent")


def substage_status(latest: BASE.Record, stage: int) -> str:
    rank = nonterminal_rank(latest)
    before = (stage - 1) * 2 + 1
    if rank < before:
        return "not-reached"
    if rank == before:
        return "entered-not-returned"
    return "returned"


def classify(payloads: tuple[bytes, bytes, bytes, bytes]) -> Result:
    cpu8_latest, cpu8_records = BASE.latest_record(payloads[0], 10)
    cpu9_latest, cpu9_records = BASE.latest_record(payloads[1], 5)
    controller_latest, controller_records = BASE.latest_record(payloads[2], 10)
    cpu_on_latest, cpu_on_records = BASE.latest_record(payloads[3], 4)

    for name, latest, records in (
        ("CPU8", cpu8_latest, cpu8_records),
        ("CPU9", cpu9_latest, cpu9_records),
        ("controller", controller_latest, controller_records),
        ("CPU-ON-progress", cpu_on_latest, cpu_on_records),
    ):
        validate_copies(name, latest, records)

    require((cpu8_latest.phase, cpu8_latest.stage, cpu8_latest.terminal) == CPU8_ONLINE,
            "CPU8-terminal-online-proof-missing")
    require(cpu9_latest.attempt_id != cpu8_latest.attempt_id,
            "CPU8-and-CPU9-attempt-identities-collide")
    require(controller_latest.attempt_id == cpu8_latest.attempt_id,
            "controller-attempt-does-not-match-CPU8")
    require(controller_latest.phase in (1, 2) and controller_latest.terminal == 0,
            "controller-latest-is-not-a-progress-checkpoint")
    require(controller_latest.stage >= 9,
            "controller-did-not-return-from-ledger-begin")
    require(cpu_on_latest.attempt_id == cpu9_latest.attempt_id,
            "CPU-ON-progress-attempt-does-not-match-CPU9")
    validate_cpu_on_order(cpu_on_records)
    cpu_on_rank = nonterminal_rank(cpu_on_latest)

    if cpu9_latest.phase == 3:
        terminal_name = CPU9_TERMINALS.get(
            (cpu9_latest.stage, cpu9_latest.terminal)
        )
        require(terminal_name is not None, "CPU9-terminal-stage-value-pair-is-invalid")
        require(cpu9_latest.stage >= 2,
                "CPU-ON-progress-exists-before-CPU9-CPU-ON-stage")
        if cpu9_latest.stage >= 3 or cpu9_latest.terminal == 5:
            require(cpu_on_rank == 8,
                    "CPU9-later-terminal-lacks-CPU-boot-return-proof")
        if terminal_name == "cpu9-online-proof":
            classification = "cpu9-terminal-online-proof"
            next_branch = "repeatability-and-cluster-validation"
        else:
            classification = f"cpu9-terminal-{terminal_name}"
            if terminal_name == "cpu-on-failure":
                next_branch = CPU_ON_STAGES[cpu_on_latest.stage]
            else:
                next_branch = CPU9_STAGES[cpu9_latest.stage]
    else:
        require(cpu9_latest.phase in (1, 2) and cpu9_latest.terminal == 0,
                "CPU9-latest-is-neither-checkpoint-nor-terminal")
        cpu9_rank = nonterminal_rank(cpu9_latest)
        require(cpu9_rank >= 3,
                "CPU-ON-progress-exists-before-CPU9-before-CPU-ON")
        if cpu9_rank > 3:
            require(cpu_on_rank == 8,
                    "CPU9-past-CPU-ON-lacks-CPU-boot-return-proof")
        if controller_latest.stage == 10:
            require(False, "controller-recorded-add-CPU-return-before-CPU9-terminal")
        if cpu9_rank == 3:
            classification, next_branch = CPU_ON_CLASSIFICATIONS[cpu_on_rank]
        else:
            require(cpu9_rank in CPU9_NONTERMINAL_CLASSIFICATIONS,
                    "CPU9-nonterminal-state-is-outside-decision-map")
            classification, next_branch = CPU9_NONTERMINAL_CLASSIFICATIONS[cpu9_rank]

    return Result(
        classification,
        next_branch,
        cpu8_latest,
        cpu8_records,
        cpu9_latest,
        cpu9_records,
        controller_latest,
        controller_records,
        cpu_on_latest,
        cpu_on_records,
    )


def payload(*records: bytes) -> bytes:
    return b"".join(records).ljust(BASE.PAYLOAD_BYTES, b"\0")


def lane(attempt: int, latest: tuple[int, int, int],
         previous: tuple[int, int, int] | None, *, latest_generation: int = 21,
         previous_attempt: int | None = None,
         previous_generation: int | None = None) -> bytes:
    encoded = [
        BASE.encode_record(
            attempt_id=attempt,
            generation=latest_generation,
            phase=latest[0],
            stage=latest[1],
            terminal=latest[2],
        )
    ]
    if previous is not None:
        encoded.append(
            BASE.encode_record(
                attempt_id=previous_attempt or attempt,
                generation=(
                    latest_generation - 1
                    if previous_generation is None
                    else previous_generation
                ),
                phase=previous[0],
                stage=previous[1],
                terminal=previous[2],
            )
        )
    return payload(*encoded)


def previous_checkpoint(state: tuple[int, int, int]) -> tuple[int, int, int]:
    phase, stage, terminal = state
    if phase == 3:
        return (2, stage, 0) if terminal == 5 else (1, stage, 0)
    if phase == 2:
        return (1, stage, 0)
    require(stage > 1, "synthetic-state-has-no-predecessor")
    return (2, stage - 1, 0)


def fixture(
    *,
    cpu9: tuple[int, int, int] = (1, 2, 0),
    cpu_on: tuple[int, int, int] = (1, 2, 0),
    controller: tuple[int, int, int] = (2, 9, 0),
    cpu8_attempt: int = 1,
    cpu9_attempt: int = 2,
    controller_attempt: int | None = None,
    cpu_on_attempt: int | None = None,
) -> tuple[bytes, bytes, bytes, bytes]:
    cpu8_payload = lane(cpu8_attempt, CPU8_ONLINE, (2, 10, 0))
    cpu9_payload = lane(cpu9_attempt, cpu9, previous_checkpoint(cpu9))
    controller_payload = lane(
        controller_attempt or cpu8_attempt,
        controller,
        previous_checkpoint(controller),
    )
    cpu_on_previous = None if cpu_on == (1, 1, 0) else previous_checkpoint(cpu_on)
    cpu_on_payload = lane(
        cpu_on_attempt or cpu9_attempt,
        cpu_on,
        cpu_on_previous,
    )
    return cpu8_payload, cpu9_payload, controller_payload, cpu_on_payload


def rejected(payloads: tuple[bytes, bytes, bytes, bytes]) -> None:
    try:
        classify(payloads)
    except BASE.ClassificationError:
        return
    raise AssertionError("invalid membership-lock recovery evidence was accepted")


def self_test() -> None:
    valid = (
        ((1, 2, 0), (1, 1, 0), "cpu-on-progress-before-p30e-prepare"),
        ((1, 2, 0), (1, 2, 0), "cpu-on-progress-before-membership-begin"),
        ((1, 2, 0), (2, 2, 0), "cpu-on-progress-after-membership-begin"),
        ((1, 2, 0), (1, 3, 0), "cpu-on-progress-before-p30e-arm"),
        ((1, 2, 0), (1, 4, 0), "cpu-on-progress-before-generic-cpu-boot"),
        ((1, 2, 0), (2, 4, 0), "cpu-on-progress-after-generic-cpu-boot"),
        ((2, 2, 0), (2, 4, 0), "cpu9-cpu-on-returned"),
        ((1, 3, 0), (2, 4, 0), "cpu9-before-online-wait"),
        ((3, 2, 2), (1, 4, 0), "cpu9-terminal-cpu-on-failure"),
        ((3, 3, 3), (2, 4, 0), "cpu9-terminal-online-wait-failure"),
        ((3, 4, 4), (2, 4, 0), "cpu9-terminal-ipi-failure"),
        ((3, 5, 4), (2, 4, 0), "cpu9-terminal-membership-failure"),
        ((3, 5, 5), (2, 4, 0), "cpu9-terminal-online-proof"),
    )
    for cpu9, cpu_on, expected in valid:
        result = classify(fixture(cpu9=cpu9, cpu_on=cpu_on))
        assert result.classification == expected

    invalid = [
        (bytes(BASE.PAYLOAD_BYTES),) + fixture()[1:],
        fixture(cpu8_attempt=2, cpu9_attempt=2),
        fixture(controller_attempt=3),
        fixture(controller=(2, 8, 0)),
        fixture(cpu_on_attempt=3),
        fixture(cpu9=(2, 2, 0), cpu_on=(1, 4, 0)),
        fixture(cpu9=(3, 2, 3), cpu_on=(1, 4, 0)),
        fixture(cpu9=(3, 5, 5), cpu_on=(1, 4, 0)),
        fixture(cpu9=(2, 2, 0), cpu_on=(2, 4, 0), controller=(2, 10, 0)),
    ]
    bad_progress = list(fixture())
    bad_progress[3] = lane(
        2,
        (1, 3, 0),
        (2, 1, 0),
    )
    invalid.append(tuple(bad_progress))
    bad_generation = list(fixture())
    bad_generation[3] = lane(
        2,
        (1, 2, 0),
        (2, 1, 0),
        previous_generation=18,
    )
    invalid.append(tuple(bad_generation))
    bad_attempt = list(fixture())
    bad_attempt[3] = lane(
        2,
        (1, 2, 0),
        (2, 1, 0),
        previous_attempt=3,
    )
    invalid.append(tuple(bad_attempt))
    for mutation in invalid:
        rejected(mutation)
    total = len(valid) + len(invalid)
    print(f"membership_lock_repair_recovery_classifier_tests={total}-of-{total}-pass")


def emit_records(name: str, latest: BASE.Record,
                 records: tuple[BASE.Record, ...]) -> None:
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
    for name, latest, records in (
        ("cpu8", result.cpu8_latest, result.cpu8_records),
        ("cpu9", result.cpu9_latest, result.cpu9_records),
        ("controller", result.controller_latest, result.controller_records),
        ("cpu_on_progress", result.cpu_on_latest, result.cpu_on_records),
    ):
        emit_records(name, latest, records)
    print(f"runtime_classification={result.classification}")
    print(f"cpu9_latest_stage_name={CPU9_STAGES[result.cpu9_latest.stage]}")
    print(
        "cpu_on_progress_latest_stage_name="
        f"{CPU_ON_STAGES[result.cpu_on_latest.stage]}"
    )
    for stage, name in CPU_ON_STAGES.items():
        print(f"{name.replace('-', '_')}={substage_status(result.cpu_on_latest, stage)}")
    print(
        "cpu9_online="
        f"{'retained-proof' if result.classification == 'cpu9-terminal-online-proof' else 'no'}"
    )
    print(f"next_selected_branch={result.next_branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
