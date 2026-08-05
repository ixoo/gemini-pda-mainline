#!/usr/bin/env python3
"""Validate phase-marker structure in one read-only USB/netcat capture."""

import argparse
import re
import sys
from pathlib import Path


PARENT_PHASES = (
    "create8-before",
    "create8-after",
    "create9-before",
    "create9-after",
    "unpark8-before",
    "unpark8-after",
    "unpark9-before",
    "unpark9-after",
    "ready8-wait-before",
    "ready8-wait-after",
    "ready9-wait-before",
    "ready9-wait-after",
    "release-before",
    "release-after",
    "done8-wait-before",
    "done8-wait-after",
    "done9-wait-before",
    "done9-wait-after",
    "stop8-before",
    "stop8-after",
    "stop9-before",
    "stop9-after",
    "run-exit",
)
TASK_PHASES = (
    "task-ready-before",
    "task-ready-after",
    "task-start-wait-before",
    "task-start-wait-after",
    "task-work-before",
    "task-work-after",
    "task-done-before",
    "task-done-after",
)
PARENT_INDEX = {phase: index for index, phase in enumerate(PARENT_PHASES)}
CREATE_PREFIX = PARENT_PHASES[:4]
PARENT_PATHS = (
    PARENT_PHASES,
    CREATE_PREFIX + ("run-exit",),
    CREATE_PREFIX + ("stop8-before", "stop8-after", "run-exit"),
    CREATE_PREFIX + ("stop9-before", "stop9-after", "run-exit"),
)
SNAPSHOT_BEGIN = re.compile(
    r"phase_trace_snapshot_begin sequence=([1-9][0-9]*) lines=([0-9]+)"
)
SNAPSHOT_END = re.compile(r"phase_trace_snapshot_end sequence=([1-9][0-9]*)")
MARKER = re.compile(
    r"gemini-a72-sc-phase(?: cpu=([0-9]+))? phase=([a-z0-9-]+)$"
)
PAIR_HEADER = re.compile(
    r"gemini-a72-pair-v([67]) result=(pass|fault)(?: [^ \r\n]+)*$"
)
DECIMAL = re.compile(r"-?[0-9]+")
HEX16 = re.compile(r"[0-9a-f]{16}")
PAIR6_FIELDS = (
    "sample", "cpu8", "cpu9", "online8", "online9", "hits8", "hits9",
    "hps_reported", "hps_cpu", "hps_error", "hps_count", "coh_reported",
    "coh_rounds", "coh_cpu8", "coh_cpu9", "coh_error8", "coh_error9",
    "coh_seq8", "coh_seq9", "ml_reported", "ml_rounds", "ml_lines",
    "ml_words", "ml_cpu8", "ml_cpu9", "ml_error8", "ml_error9",
    "ml_done8", "ml_done9", "ml_hash8w", "ml_hash8r", "ml_hash9w",
    "ml_hash9r", "ml_bad_round", "ml_bad_line", "ml_bad_word",
    "ml_expected", "ml_actual", "pl_reported", "pl_rounds", "pl_lines",
    "pl_words", "pl_cpu8", "pl_cpu9", "pl_error8", "pl_error9",
    "pl_done8", "pl_done9", "pl_ready", "pl_written", "pl_verified",
    "pl_hash8w", "pl_hash8r", "pl_hash9w", "pl_hash9r", "pl_bad_round",
    "pl_bad_line", "pl_bad_word", "pl_expected", "pl_actual",
)
PAIR7_FIELDS = (
    "parent_pass", "sc_reported", "sc_iterations", "sc_rescheds",
    "sc_expected8", "sc_start8", "sc_end8", "sc_expected9", "sc_start9",
    "sc_end9", "sc_task8", "sc_task9", "sc_create8", "sc_create9",
    "sc_unpark8", "sc_unpark9", "sc_readywait8", "sc_readywait9",
    "sc_startwait8", "sc_startwait9", "sc_wait8", "sc_wait9",
    "sc_error8", "sc_error9", "sc_stop8", "sc_stop9", "sc_done8",
    "sc_done9", "sc_ready", "sc_finished", "sc_hash8", "sc_hash9",
)
PAIR_FIELDS = {6: PAIR6_FIELDS, 7: PAIR7_FIELDS}
PAIR_EXACT = {
    6: {
        "sample": "3", "cpu8": "8", "cpu9": "9", "online8": "1",
        "online9": "1", "hits8": "3", "hits9": "3",
        "ml_rounds": "64", "ml_lines": "256", "ml_words": "8",
        "pl_rounds": "128", "pl_lines": "1024", "pl_words": "8",
    },
    7: {"sc_iterations": "262144", "sc_rescheds": "64"},
}
PAIR_HEX = {
    6: {
        "ml_hash8w", "ml_hash8r", "ml_hash9w", "ml_hash9r",
        "ml_expected", "ml_actual", "pl_hash8w", "pl_hash8r",
        "pl_hash9w", "pl_hash9r", "pl_expected", "pl_actual",
    },
    7: {"sc_hash8", "sc_hash9"},
}
PAIR6_PASS_EXACT = {
    "sample": "3", "cpu8": "8", "cpu9": "9", "online8": "1",
    "online9": "1", "hits8": "3", "hits9": "3", "hps_reported": "1",
    "hps_cpu": "9", "hps_error": "-1", "coh_reported": "1",
    "coh_rounds": "1024", "coh_cpu8": "8", "coh_cpu9": "9",
    "coh_error8": "0", "coh_error9": "0", "coh_seq8": "1024",
    "coh_seq9": "1024", "ml_reported": "1", "ml_rounds": "64",
    "ml_lines": "256", "ml_words": "8", "ml_cpu8": "8", "ml_cpu9": "9",
    "ml_error8": "0", "ml_error9": "0", "ml_done8": "64", "ml_done9": "64",
    "ml_hash8w": "34e574e95cbe0383", "ml_hash8r": "432574e95cbe0383",
    "ml_hash9w": "432574e95cbe0383", "ml_hash9r": "34e574e95cbe0383",
    "ml_bad_round": "0", "ml_bad_line": "0", "ml_bad_word": "0",
    "ml_expected": "0000000000000000", "ml_actual": "0000000000000000",
    "pl_reported": "1", "pl_rounds": "128", "pl_lines": "1024",
    "pl_words": "8", "pl_cpu8": "8", "pl_cpu9": "9", "pl_error8": "0",
    "pl_error9": "0", "pl_done8": "128", "pl_done9": "128",
    "pl_ready": "256", "pl_written": "256", "pl_verified": "256",
    "pl_hash8w": "d7bbe01c2e3d0383", "pl_hash8r": "f5e6a0ebae7d0383",
    "pl_hash9w": "f5e6a0ebae7d0383", "pl_hash9r": "d7bbe01c2e3d0383",
    "pl_bad_round": "0", "pl_bad_line": "0", "pl_bad_word": "0",
    "pl_expected": "0000000000000000", "pl_actual": "0000000000000000",
}
PAIR7_PASS_EXACT = {
    "parent_pass": "1", "sc_reported": "1", "sc_iterations": "262144",
    "sc_rescheds": "64", "sc_expected8": "8", "sc_start8": "8",
    "sc_end8": "8", "sc_expected9": "9", "sc_start9": "9", "sc_end9": "9",
    "sc_task8": "1", "sc_task9": "1", "sc_create8": "0", "sc_create9": "0",
    "sc_unpark8": "1", "sc_unpark9": "1",
    "sc_readywait8": "1", "sc_readywait9": "1", "sc_startwait8": "1",
    "sc_startwait9": "1", "sc_wait8": "1", "sc_wait9": "1",
    "sc_error8": "0", "sc_error9": "0", "sc_stop8": "0", "sc_stop9": "0",
    "sc_done8": "262144", "sc_done9": "262144", "sc_ready": "2",
    "sc_finished": "2", "sc_hash8": "f678147669874ecd",
    "sc_hash9": "c2274327e9c8104c",
}
TERMINATOR = "__A72_SCHEDULER_UNPARK_TERMINAL_CAPTURED__"


class CaptureError(ValueError):
    """The transport record cannot safely support phase inference."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(message)


def marker_line(record: tuple[int | None, str], timestamp: int = 1) -> str:
    """Return a representative dmesg line for static parser tests."""
    cpu, phase = record
    cpu_field = "" if cpu is None else f" cpu={cpu}"
    return f"[{timestamp:6d}.000000] gemini-a72-sc-phase{cpu_field} phase={phase}"


def valid_complete_trace() -> list[tuple[int | None, str]]:
    """Return one legal successful interleaving of all 39 runtime records."""
    return [
        (None, "create8-before"),
        (None, "create8-after"),
        (None, "create9-before"),
        (None, "create9-after"),
        (None, "unpark8-before"),
        (None, "unpark8-after"),
        (8, "task-ready-before"),
        (8, "task-ready-after"),
        (8, "task-start-wait-before"),
        (None, "unpark9-before"),
        (None, "unpark9-after"),
        (9, "task-ready-before"),
        (9, "task-ready-after"),
        (9, "task-start-wait-before"),
        (None, "ready8-wait-before"),
        (None, "ready8-wait-after"),
        (None, "ready9-wait-before"),
        (None, "ready9-wait-after"),
        (None, "release-before"),
        (None, "release-after"),
        (None, "done8-wait-before"),
        (8, "task-start-wait-after"),
        (8, "task-work-before"),
        (8, "task-work-after"),
        (8, "task-done-before"),
        (8, "task-done-after"),
        (None, "done8-wait-after"),
        (None, "done9-wait-before"),
        (9, "task-start-wait-after"),
        (9, "task-work-before"),
        (9, "task-work-after"),
        (9, "task-done-before"),
        (9, "task-done-after"),
        (None, "done9-wait-after"),
        (None, "stop8-before"),
        (None, "stop8-after"),
        (None, "stop9-before"),
        (None, "stop9-after"),
        (None, "run-exit"),
    ]


def parse_marker(line: str) -> tuple[int | None, str]:
    stripped = line.rstrip("\r")
    require(
        stripped.count("gemini-a72-sc-phase") == 1,
        "snapshot line does not contain exactly one phase-marker occurrence",
    )
    match = MARKER.search(stripped)
    require(match is not None, "snapshot contains a malformed phase marker")
    cpu_text, phase = match.groups()
    cpu = None if cpu_text is None else int(cpu_text)
    if phase in PARENT_INDEX:
        require(cpu is None, f"parent phase has a CPU field: {phase}")
    elif phase in TASK_PHASES:
        require(cpu in (8, 9), f"task phase has an invalid CPU field: {phase}")
    else:
        raise CaptureError(f"snapshot contains an unknown phase: {phase}")
    return cpu, phase


def parse_pair(line: str) -> tuple[int, str, str, dict[str, str]]:
    """Parse one complete pair terminal and retain its exact normalized text."""
    stripped = line.rstrip("\r")
    require(
        stripped.count("gemini-a72-pair-v") == 1,
        "snapshot line does not contain exactly one pair-terminal occurrence",
    )
    match = PAIR_HEADER.search(stripped)
    require(match is not None, "snapshot contains a malformed pair terminal")
    version = int(match.group(1))
    result = match.group(2)
    normalized = match.group(0)
    tokens = normalized.split()
    expected_names = PAIR_FIELDS[version]
    require(
        len(tokens) == len(expected_names) + 2,
        f"pair-v{version} terminal field count changed",
    )
    values = {}
    for token, expected_name in zip(tokens[2:], expected_names):
        name, separator, value = token.partition("=")
        require(
            separator == "=" and name == expected_name and bool(value),
            f"pair-v{version} terminal field order changed at {expected_name}",
        )
        exact = PAIR_EXACT[version].get(name)
        if exact is not None:
            require(value == exact, f"pair-v{version} fixed field changed: {name}")
        elif name in PAIR_HEX[version]:
            require(
                HEX16.fullmatch(value) is not None,
                f"pair-v{version} hexadecimal field malformed: {name}",
            )
        else:
            require(
                DECIMAL.fullmatch(value) is not None,
                f"pair-v{version} decimal field malformed: {name}",
            )
        values[name] = value
    return version, result, normalized, values


def validate_pair6_pass(values: dict[str, str]) -> None:
    for name, expected in PAIR6_PASS_EXACT.items():
        require(values[name] == expected, f"pair-v6 pass field changed: {name}")
    require(int(values["hps_count"]) > 0, "pair-v6 pass hps_count is not positive")


def validate_pair7_pass(values: dict[str, str]) -> None:
    for name, expected in PAIR7_PASS_EXACT.items():
        require(values[name] == expected, f"pair-v7 pass field changed: {name}")


def validate_fault_field_causality(
    records: list[tuple[int | None, str]], values: dict[str, str]
) -> None:
    """Apply causal edges independently claimed by successful fault fields."""
    positions = {record: index for index, record in enumerate(records)}

    def require_edge(
        field: str,
        first: tuple[int | None, str],
        second: tuple[int | None, str],
    ) -> None:
        if values[field] != "1":
            return
        require(first in positions, f"{field}=1 lacks causal marker: {first}")
        require(second in positions, f"{field}=1 lacks causal marker: {second}")
        require(
            positions[first] < positions[second],
            f"{field}=1 contradicts causal marker order",
        )

    for cpu in (8, 9):
        unpark_field = f"sc_unpark{cpu}"
        unpark_before = (None, f"unpark{cpu}-before")
        unpark_after = (None, f"unpark{cpu}-after")
        require(
            values[unpark_field] in ("0", "1"),
            f"{unpark_field} is outside the source domain",
        )
        require_edge(
            unpark_field,
            unpark_before,
            unpark_after,
        )
        require(
            unpark_after not in positions or values[unpark_field] == "1",
            f"{unpark_field}=0 contradicts its after marker",
        )
        ready = f"sc_readywait{cpu}"
        require_edge(
            ready,
            (cpu, "task-ready-before"),
            (None, f"ready{cpu}-wait-after"),
        )
        require_edge(
            ready,
            (cpu, "task-ready-before"),
            (None, "release-before"),
        )
        require_edge(
            f"sc_startwait{cpu}",
            (None, "release-before"),
            (cpu, "task-start-wait-after"),
        )
        require_edge(
            f"sc_wait{cpu}",
            (cpu, "task-done-before"),
            (None, f"done{cpu}-wait-after"),
        )


def synthetic_pair_line(
    version: int, result: str, parent_pass: int | None = None
) -> str:
    """Return one complete representative terminal for parser tests."""
    require(version in PAIR_FIELDS, "synthetic pair version is invalid")
    require(result in ("pass", "fault"), "synthetic pair result is invalid")
    semantic_values = {}
    if result == "pass" and version == 6:
        semantic_values = {**PAIR6_PASS_EXACT, "hps_count": "1"}
    elif result == "pass" and version == 7:
        semantic_values = PAIR7_PASS_EXACT
    fields = []
    for name in PAIR_FIELDS[version]:
        if name in semantic_values:
            value = semantic_values[name]
        elif name in PAIR_EXACT[version]:
            value = PAIR_EXACT[version][name]
        elif name in PAIR_HEX[version]:
            value = "0" * 16
        elif name == "parent_pass":
            value = str(
                parent_pass if parent_pass is not None else int(result == "pass")
            )
        else:
            value = "0"
        fields.append(f"{name}={value}")
    return f"gemini-a72-pair-v{version} result={result} {' '.join(fields)}"


def validate_structural_sequence(records: list[tuple[int | None, str]]) -> None:
    """Validate source-invariant order without imposing PASS-only causality."""
    require(bool(records), "latest complete snapshot has no phase marker")
    for cpu, phase in records:
        if phase in PARENT_INDEX:
            require(cpu is None, f"parent phase has a CPU field: {phase}")
        elif phase in TASK_PHASES:
            require(cpu in (8, 9), f"task phase has an invalid CPU field: {phase}")
        else:
            raise CaptureError(f"phase history contains an unknown phase: {phase}")
    require(
        records[0] == (None, "create8-before"),
        "phase history does not begin at create8-before",
    )
    require(len(records) == len(set(records)), "phase history has a duplicate record")

    positions = {record: index for index, record in enumerate(records)}
    parent = tuple(phase for cpu, phase in records if cpu is None)
    require(
        any(parent == path[: len(parent)] for path in PARENT_PATHS),
        "parent phase history is not a prefix of a reachable source path",
    )

    for cpu in (8, 9):
        task = [phase for record_cpu, phase in records if record_cpu == cpu]
        require(
            tuple(task) == TASK_PHASES[: len(task)],
            f"CPU{cpu} task phases are not an exact source-order prefix",
        )
        if task:
            create_after = (None, f"create{cpu}-after")
            require(create_after in positions, f"CPU{cpu} task lacks create-after")
            require(
                positions[create_after] < positions[(cpu, task[0])],
                f"CPU{cpu} task precedes create-after",
            )
            unpark_before = (None, f"unpark{cpu}-before")
            require(unpark_before in positions, f"CPU{cpu} task lacks unpark-before")
            require(
                positions[unpark_before] < positions[(cpu, task[0])],
                f"CPU{cpu} task precedes unpark-before",
            )
        task_done_after = (cpu, "task-done-after")
        stop_after = (None, f"stop{cpu}-after")
        if task_done_after in positions and stop_after in positions:
            require(
                positions[task_done_after] < positions[stop_after],
                f"CPU{cpu} stop returned before task-done-after",
            )

    run_exit = (None, "run-exit")
    if run_exit in positions:
        for cpu in (8, 9):
            if any(record_cpu == cpu for record_cpu, _phase in records):
                stop_after = (None, f"stop{cpu}-after")
                require(stop_after in positions, f"run-exit lacks CPU{cpu} stop-after")
                require(
                    positions[stop_after] < positions[run_exit],
                    f"run-exit precedes CPU{cpu} stop-after",
                )


def validate_success_sequence(records: list[tuple[int | None, str]]) -> None:
    """Validate the complete PASS-only order and cross-causal contract."""
    validate_structural_sequence(records)
    require(len(records) == 39, "successful trace does not have 39 records")
    positions = {record: index for index, record in enumerate(records)}
    parent = tuple(phase for cpu, phase in records if cpu is None)
    require(parent == PARENT_PHASES, "successful parent trace changed")
    for cpu in (8, 9):
        task = tuple(phase for record_cpu, phase in records if record_cpu == cpu)
        require(task == TASK_PHASES, f"successful CPU{cpu} task trace changed")
        causal_pairs = (
            ((None, f"unpark{cpu}-before"), (cpu, "task-ready-before")),
            ((cpu, "task-ready-before"), (None, f"ready{cpu}-wait-after")),
            ((cpu, "task-ready-before"), (None, "release-before")),
            ((None, "release-before"), (cpu, "task-start-wait-after")),
            ((cpu, "task-done-before"), (None, f"done{cpu}-wait-after")),
            ((cpu, "task-done-after"), (None, f"stop{cpu}-after")),
            ((None, f"stop{cpu}-after"), (None, "run-exit")),
        )
        for first, second in causal_pairs:
            require(
                positions[first] < positions[second],
                f"successful causal order changed: {first} -> {second}",
            )


def validate_terminal_semantics(
    records: list[tuple[int | None, str]],
    pair6: tuple[int, str, str, dict[str, str]],
    pair7: tuple[int, str, str, dict[str, str]],
) -> str:
    """Validate source and decision semantics for one complete terminal pair."""
    require(pair6[0] == 6, "terminal pair-v6 has the wrong version")
    require(pair7[0] == 7, "terminal pair-v7 has the wrong version")
    terminal_result = pair7[1]
    if terminal_result == "pass":
        require(pair6[1] == "pass", "pair-v7 pass lacks a pair-v6 pass")
        validate_pair6_pass(pair6[3])
        validate_pair7_pass(pair7[3])
        validate_success_sequence(records)
    elif records:
        require(pair6[1] == "pass", "scheduler fault lacks a pair-v6 pass")
        validate_pair6_pass(pair6[3])
        require(
            (None, "run-exit") in records,
            "pair-v7 fault terminal precedes run-exit",
        )
        require(
            pair7[3]["parent_pass"] == "1",
            "scheduler fault trace lacks parent_pass=1",
        )
        validate_fault_field_causality(records, pair7[3])
    else:
        validate_fault_field_causality(records, pair7[3])
        require(
            pair6[1] == "fault" and pair7[3]["parent_pass"] == "0",
            "marker-free pair-v7 fault lacks parent_pass=0",
        )
    return terminal_result


def render_snapshot(
    sequence: int,
    records: list[tuple[int | None, str]],
    pair_result: str | None = None,
    pair6_result: str = "pass",
) -> str:
    """Render the real numbered-snapshot format for static parser tests."""
    payload = [marker_line(record, index + 1) for index, record in enumerate(records)]
    if pair_result is not None:
        payload.append(f"[999998.000000] {synthetic_pair_line(6, pair6_result)}")
        payload.append(
            f"[999999.000000] "
            f"{synthetic_pair_line(7, pair_result, parent_pass=int(bool(records)))}"
        )
    lines = [
        f"phase_trace_snapshot_begin sequence={sequence} lines={len(payload)}",
        *payload,
        f"phase_trace_snapshot_end sequence={sequence}",
    ]
    return "\n".join(lines)


def analyze_capture_text(text: str) -> dict[str, str | int]:
    """Analyze complete snapshots and return a conservative capture class."""
    snapshots: list[tuple[int, list[str]]] = []
    current: tuple[int, int, list[str]] | None = None
    transport_tail = "complete"

    for raw_line in text.splitlines():
        begin = SNAPSHOT_BEGIN.fullmatch(raw_line)
        end = SNAPSHOT_END.fullmatch(raw_line)
        if "phase_trace_snapshot_begin" in raw_line:
            require(begin is not None, "malformed snapshot-begin control line")
            require(current is None, "nested snapshot-begin control line")
            sequence, declared = (int(value) for value in begin.groups())
            require(
                sequence == len(snapshots) + 1,
                "snapshot sequence is not contiguous from one",
            )
            current = (sequence, declared, [])
            continue
        if "phase_trace_snapshot_end" in raw_line:
            require(end is not None, "malformed snapshot-end control line")
            require(current is not None, "snapshot-end lacks a begin")
            sequence = int(end.group(1))
            open_sequence, declared, payload = current
            require(sequence == open_sequence, "snapshot control sequence mismatch")
            require(len(payload) == declared, "snapshot payload line count changed")
            snapshots.append((sequence, payload))
            current = None
            continue
        if current is not None:
            current[2].append(raw_line)

    if current is not None:
        transport_tail = "truncated"
    require(bool(snapshots), "capture has no complete numbered snapshot")

    previous_events: list[tuple[object, ...]] = []
    latest_records: list[tuple[int | None, str]] = []
    latest_pairs: list[tuple[int, str, str, dict[str, str]]] = []
    for snapshot_index, (_sequence, payload) in enumerate(snapshots):
        records = []
        pairs = []
        events: list[tuple[object, ...]] = []
        for line in payload:
            if "gemini-a72-sc-phase" in line:
                record = parse_marker(line)
                records.append(record)
                events.append(("phase", *record))
                continue
            pair = parse_pair(line)
            pairs.append(pair)
            events.append(("pair", pair[0], pair[1], pair[2]))
        if records:
            validate_structural_sequence(records)
        require(
            events[: len(previous_events)] == previous_events,
            "complete snapshots do not preserve one monotonic event history",
        )
        if pairs:
            require(
                snapshot_index == len(snapshots) - 1,
                "pair terminal appears before the final complete snapshot",
            )
            require(
                len(pairs) == 2 and pairs[0][0] == 6 and pairs[1][0] == 7,
                "snapshot lacks one ordered pair-v6/pair-v7 terminal",
            )
            require(
                len(events) >= 2
                and events[-2][0:2] == ("pair", 6)
                and events[-1][0:2] == ("pair", 7),
                "pair-v6/pair-v7 terminals are not the adjacent final events",
            )
            if records:
                require(
                    len(events) >= 3
                    and events[-3] == ("phase", None, "run-exit"),
                    "pair terminal does not immediately follow run-exit",
                )
        previous_events = events
        latest_records = records
        latest_pairs = pairs

    terminator_count = sum(line == TERMINATOR for line in text.splitlines())
    require(terminator_count <= 1, "terminal capture terminator is duplicated")
    pair6_metadata = [
        line
        for line in text.splitlines()
        if line.startswith("pair6_terminal_line=")
    ]
    pair7_metadata = [
        line
        for line in text.splitlines()
        if line.startswith("pair7_terminal_line=")
    ]
    if terminator_count == 1:
        require(len(pair6_metadata) == 1, "terminal capture lacks one pair-v6 line")
        require(len(pair7_metadata) == 1, "terminal capture lacks one pair-v7 line")
        pair6 = parse_pair(pair6_metadata[0])
        pair7 = parse_pair(pair7_metadata[0])
        require(pair6[0] == 6, "pair-v6 metadata has the wrong version")
        require(pair7[0] == 7, "pair-v7 metadata has the wrong version")
        require(
            len(latest_pairs) == 2
            and latest_pairs[0][2] == pair6[2]
            and latest_pairs[1][2] == pair7[2],
            "terminal metadata differs from the latest complete snapshot",
        )
        terminal_result = validate_terminal_semantics(
            latest_records, latest_pairs[0], latest_pairs[1]
        )
        capture_class = "terminal"
    else:
        require(
            bool(latest_records) or bool(latest_pairs),
            "latest complete snapshot has no phase marker",
        )
        require(
            not pair6_metadata and not pair7_metadata,
            "pair metadata lacks its capture terminator",
        )
        require(
            not latest_pairs
            or (len(latest_pairs) == 2 and latest_pairs[0][0] == 6),
            "latest snapshot has a partial or duplicated pair terminal",
        )
        if latest_pairs:
            terminal_result = validate_terminal_semantics(
                latest_records, latest_pairs[0], latest_pairs[1]
            )
            capture_class = "transport-truncated-valid-snapshot"
        elif transport_tail == "truncated":
            terminal_result = "absent"
            capture_class = "transport-truncated-valid-snapshot"
        else:
            terminal_result = "absent"
            capture_class = "valid-prefix"

    return {
        "validation": "a72-scheduler-unpark-capture-structure-pass",
        "snapshot_count": len(snapshots),
        "latest_sequence": snapshots[-1][0],
        "phase_records": len(latest_records),
        "terminal_result": terminal_result,
        "transport_tail": transport_tail,
        "capture_class": capture_class,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True, type=Path)
    args = parser.parse_args()
    result = analyze_capture_text(args.capture.read_text(encoding="utf-8"))
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CaptureError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
