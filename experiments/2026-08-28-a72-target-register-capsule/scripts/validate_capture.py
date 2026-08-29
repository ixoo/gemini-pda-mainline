#!/usr/bin/env python3
"""Validate one target-register capsule capture without extending evidence."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType


SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT = SCRIPT_DIR.parent
PARENT_VALIDATOR = (
    EXPERIMENT.parent
    / "2026-08-03-a72-scheduler-context/scripts/validate_phase_capture.py"
)
CAPSULE_PATCH = EXPERIMENT / "patches/0001-diagnostic-capture-A72-target-register-capsules.patch"
PARENT_VALIDATOR_SHA256 = (
    "3871817a60f6c8919eaf483d50e956a42bece2ada598b042474861f2e4b860a3"
)
CAPSULE_PATCH_SHA256 = (
    "f4070ea05b799744af2808e49d39582cdbd8cbd009613977c14efa9827a22c53"
)
SNAPSHOT_BEGIN = re.compile(
    r"capsule_trace_snapshot_begin sequence=([1-9][0-9]*) lines=([0-9]+)"
)
SNAPSHOT_END = re.compile(r"capsule_trace_snapshot_end sequence=([1-9][0-9]*)")
REGCAP_HEADER = re.compile(
    r"gemini-a72-regcap-v1 part=(core|aa64|a32isar|a32mm) "
    r"result=(pass|fault)(?: [^ \r\n]+)*$"
)
REGCAP_PARTS = ("core", "aa64", "a32isar", "a32mm")
REGCAP_SEQUENCE = REGCAP_PARTS + REGCAP_PARTS
REGCAP_FIELDS = {
    "core": (
        "cpu", "abi", "fields", "valid", "error", "complete", "identity",
        "mpidr", "midr", "revidr", "cntfrq", "ctr", "dczid", "clidr",
    ),
    "aa64": (
        "cpu", "identity", "dfr0", "isar0", "isar1", "mmfr0", "mmfr1",
        "pfr0", "pfr1",
    ),
    "a32isar": (
        "cpu", "identity", "isar0", "isar1", "isar2", "isar3", "isar4",
        "isar5",
    ),
    "a32mm": (
        "cpu", "identity", "mmfr0", "mmfr1", "mmfr2", "mmfr3", "pfr0",
        "pfr1",
    ),
}
HEX16_FIELDS = {
    "identity", "mpidr", "clidr", "dfr0", "isar0", "isar1", "mmfr0",
    "mmfr1", "pfr0", "pfr1",
}
CORE_HEX8_FIELDS = {"midr", "revidr", "cntfrq", "ctr", "dczid"}
DECIMAL = re.compile(r"-?[0-9]+")
HEX8 = re.compile(r"[0-9a-f]{8}")
HEX16 = re.compile(r"[0-9a-f]{16}")
HEX_VALUE = re.compile(r"(?:0|0x[0-9a-f]+)")
TERMINATOR = "__A72_REGCAP_TERMINAL_CAPTURED__"
HASH_INIT = 1469598103934665603
HASH_PRIME = 1099511628211
MASK64 = (1 << 64) - 1


class CaptureError(ValueError):
    """The retained record cannot safely support capsule inference."""


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CaptureError(message)


def load_parent() -> ModuleType:
    require(
        PARENT_VALIDATOR.is_file()
        and not PARENT_VALIDATOR.is_symlink()
        and digest(PARENT_VALIDATOR) == PARENT_VALIDATOR_SHA256,
        "pinned scheduler capture validator changed",
    )
    require(
        CAPSULE_PATCH.is_file()
        and not CAPSULE_PATCH.is_symlink()
        and digest(CAPSULE_PATCH) == CAPSULE_PATCH_SHA256,
        "pinned capsule source patch changed",
    )
    spec = importlib.util.spec_from_file_location("a72_scheduler_capture", PARENT_VALIDATOR)
    require(spec is not None and spec.loader is not None, "cannot load parent validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PARENT = load_parent()
CaptureError = PARENT.CaptureError
TASK_PHASES = ("task-capture-before", "task-capture-after", *PARENT.TASK_PHASES)
PARENT.TASK_PHASES = TASK_PHASES


def valid_complete_trace() -> list[tuple[int | None, str]]:
    records = list(PARENT.valid_complete_trace())
    for cpu in (8, 9):
        index = records.index((cpu, "task-ready-before"))
        records[index:index] = [
            (cpu, "task-capture-before"),
            (cpu, "task-capture-after"),
        ]
    return records


def validate_success_sequence(records: list[tuple[int | None, str]]) -> None:
    PARENT.validate_structural_sequence(records)
    require(len(records) == 43, "successful trace does not have 43 records")
    positions = {record: index for index, record in enumerate(records)}
    parent_phases = tuple(phase for cpu, phase in records if cpu is None)
    require(parent_phases == PARENT.PARENT_PHASES, "successful parent trace changed")
    for cpu in (8, 9):
        task = tuple(phase for record_cpu, phase in records if record_cpu == cpu)
        require(task == TASK_PHASES, f"successful CPU{cpu} task trace changed")
        causal_pairs = (
            ((None, f"unpark{cpu}-before"), (cpu, "task-capture-before")),
            ((cpu, "task-capture-before"), (cpu, "task-capture-after")),
            ((cpu, "task-capture-after"), (cpu, "task-ready-before")),
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


PARENT.validate_success_sequence = validate_success_sequence


def parse_regcap(line: str) -> dict[str, object]:
    stripped = line.rstrip("\r")
    require(
        stripped.count("gemini-a72-regcap-v1") == 1,
        "snapshot line does not contain exactly one capsule occurrence",
    )
    match = REGCAP_HEADER.search(stripped)
    require(match is not None, "snapshot contains a malformed capsule")
    part, result = match.groups()
    normalized = match.group(0)
    tokens = normalized.split()
    expected_names = REGCAP_FIELDS[part]
    require(
        len(tokens) == len(expected_names) + 3,
        f"{part} capsule field count changed",
    )
    values: dict[str, str] = {}
    for token, expected_name in zip(tokens[3:], expected_names):
        name, separator, value = token.partition("=")
        require(
            separator == "=" and name == expected_name and bool(value),
            f"{part} capsule field order changed at {expected_name}",
        )
        if name == "valid":
            valid = HEX_VALUE.fullmatch(value)
        elif name in CORE_HEX8_FIELDS or (
            part.startswith("a32") and name not in {"cpu", "identity"}
        ):
            valid = HEX8.fullmatch(value)
        elif name in HEX16_FIELDS:
            valid = HEX16.fullmatch(value)
        else:
            valid = DECIMAL.fullmatch(value)
        require(valid is not None, f"{part} capsule field malformed: {name}")
        values[name] = value
    cpu = int(values["cpu"])
    require(0 <= cpu <= 9, f"{part} capsule CPU is outside the device domain")
    return {
        "part": part,
        "result": result,
        "cpu": cpu,
        "identity": values["identity"],
        "normalized": normalized,
        "values": values,
    }


def number(value: str) -> int:
    if value.startswith("0x"):
        return int(value, 16)
    if re.fullmatch(r"[0-9a-f]{8}|[0-9a-f]{16}", value):
        return int(value, 16)
    return int(value, 10)


def mix(identity: int, value: int) -> int:
    return ((identity ^ (value & MASK64)) * HASH_PRIME) & MASK64


def capsule_identity(group: list[dict[str, object]]) -> int:
    by_part = {str(item["part"]): item["values"] for item in group}
    core = by_part["core"]
    aa64 = by_part["aa64"]
    a32isar = by_part["a32isar"]
    a32mm = by_part["a32mm"]
    assert isinstance(core, dict)
    assert isinstance(aa64, dict)
    assert isinstance(a32isar, dict)
    assert isinstance(a32mm, dict)
    valid = number(core["valid"])
    fields = (
        number(core["abi"]), number(core["fields"]), valid,
        number(core["error"]) & 0xFFFFFFFF, number(core["cpu"]),
        number(core["midr"]), number(core["revidr"]), number(core["cntfrq"]),
        number(core["ctr"]), number(core["dczid"]), int(bool(valid & 0x10)),
        number(core["mpidr"]), number(core["clidr"]), number(aa64["dfr0"]),
        number(aa64["isar0"]), number(aa64["isar1"]), number(aa64["mmfr0"]),
        number(aa64["mmfr1"]), number(aa64["pfr0"]), number(aa64["pfr1"]),
        number(a32isar["isar0"]), number(a32isar["isar1"]),
        number(a32isar["isar2"]), number(a32isar["isar3"]),
        number(a32isar["isar4"]), number(a32isar["isar5"]),
        number(a32mm["mmfr0"]), number(a32mm["mmfr1"]),
        number(a32mm["mmfr2"]), number(a32mm["mmfr3"]),
        number(a32mm["pfr0"]), number(a32mm["pfr1"]),
    )
    identity = HASH_INIT
    for value in fields:
        identity = mix(identity, value)
    return identity


def validate_capsule_prefix(capsules: list[dict[str, object]]) -> None:
    require(len(capsules) <= 8, "capsule history has more than eight records")
    parts = tuple(str(item["part"]) for item in capsules)
    require(parts == REGCAP_SEQUENCE[: len(parts)], "capsule part order changed")
    for start in (0, 4):
        group = capsules[start : min(start + 4, len(capsules))]
        if not group:
            continue
        require(
            len({int(item["cpu"]) for item in group}) == 1,
            "capsule slot has mixed CPU fields",
        )
        require(
            len({str(item["identity"]) for item in group}) == 1,
            "capsule slot has mixed identities",
        )
        require(
            len({str(item["result"]) for item in group}) == 1,
            "capsule slot has mixed result fields",
        )
        if len(group) != 4:
            continue
        core = group[0]["values"]
        assert isinstance(core, dict)
        computed_identity = capsule_identity(group)
        printed_identity = int(str(group[0]["identity"]), 16)
        require(computed_identity == printed_identity, "capsule identity mismatch")
        cpu = int(group[0]["cpu"])
        midr = number(core["midr"])
        expected_mpidr = 0x200 if cpu == 8 else 0x201
        computed_pass = (
            number(core["complete"]) == 1
            and number(core["abi"]) == 1
            and number(core["fields"]) == 32
            and number(core["valid"]) == 0x1F
            and number(core["error"]) == 0
            and cpu in (8, 9)
            and number(core["mpidr"]) == expected_mpidr
            and (midr >> 24) == 0x41
            and ((midr >> 4) & 0xFFF) == 0xD08
        )
        require(
            (str(group[0]["result"]) == "pass") == computed_pass,
            "capsule result disagrees with its exact field vector",
        )


def validate_capsule_terminal(
    capsules: list[dict[str, object]], pair_result: str
) -> None:
    require(len(capsules) == 8, "terminal lacks exactly eight capsule records")
    validate_capsule_prefix(capsules)
    if pair_result == "pass":
        require(
            [int(capsules[0]["cpu"]), int(capsules[4]["cpu"])] == [8, 9],
            "passing terminal lacks ordered CPU8/CPU9 slots",
        )
        require(
            all(str(item["result"]) == "pass" for item in capsules),
            "passing scheduler terminal has a fault capsule",
        )


def parse_snapshots(text: str) -> tuple[
    list[tuple[int | None, str]],
    list[tuple[int, str, str, dict[str, str]]],
    list[dict[str, object]],
    int,
    str,
]:
    snapshots: list[tuple[int, list[str]]] = []
    current: tuple[int, int, list[str]] | None = None
    transport_tail = "complete"
    for raw_line in text.splitlines():
        begin = SNAPSHOT_BEGIN.fullmatch(raw_line)
        end = SNAPSHOT_END.fullmatch(raw_line)
        if "capsule_trace_snapshot_begin" in raw_line:
            require(begin is not None, "malformed snapshot-begin control line")
            require(current is None, "nested snapshot-begin control line")
            sequence, declared = (int(value) for value in begin.groups())
            require(
                sequence == len(snapshots) + 1,
                "snapshot sequence is not contiguous from one",
            )
            current = (sequence, declared, [])
            continue
        if "capsule_trace_snapshot_end" in raw_line:
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
    latest_capsules: list[dict[str, object]] = []
    for _sequence, payload in snapshots:
        records: list[tuple[int | None, str]] = []
        pairs: list[tuple[int, str, str, dict[str, str]]] = []
        capsules: list[dict[str, object]] = []
        events: list[tuple[object, ...]] = []
        for line in payload:
            if "gemini-a72-sc-phase" in line:
                record = PARENT.parse_marker(line)
                records.append(record)
                events.append(("phase", *record))
            elif "gemini-a72-pair-v" in line:
                pair = PARENT.parse_pair(line)
                pairs.append(pair)
                events.append(("pair", pair[0], pair[1], pair[2]))
            elif "gemini-a72-regcap-v1" in line:
                capsule = parse_regcap(line)
                capsules.append(capsule)
                events.append(("capsule", capsule["normalized"]))
            else:
                raise CaptureError("snapshot contains an unknown payload line")
        if records:
            PARENT.validate_structural_sequence(records)
        validate_capsule_prefix(capsules)
        require(
            events[: len(previous_events)] == previous_events,
            "complete snapshots do not preserve one monotonic event history",
        )
        if pairs:
            require(
                len(pairs) == 2 and pairs[0][0] == 6 and pairs[1][0] == 7,
                "snapshot lacks one ordered pair-v6/pair-v7 terminal",
            )
            pair6_index = next(i for i, event in enumerate(events) if event[:2] == ("pair", 6))
            require(
                events[pair6_index + 1][:2] == ("pair", 7),
                "pair-v6/pair-v7 terminals are not adjacent",
            )
            require(
                pair6_index > 0
                and events[pair6_index - 1] == ("phase", None, "run-exit"),
                "pair terminal does not immediately follow run-exit",
            )
            require(
                all(event[0] == "capsule" for event in events[pair6_index + 2 :]),
                "non-capsule event follows pair-v7 terminal",
            )
        else:
            require(not capsules, "capsule appears without its pair terminal")
        previous_events = events
        latest_records = records
        latest_pairs = pairs
        latest_capsules = capsules
    return (
        latest_records,
        latest_pairs,
        latest_capsules,
        snapshots[-1][0],
        transport_tail,
    )


def analyze_capture_text(text: str, *, raw_log: bool = False) -> dict[str, str | int]:
    records, pairs, capsules, sequence, transport_tail = parse_snapshots(text)
    terminator_count = sum(line == TERMINATOR for line in text.splitlines())
    require(terminator_count <= 1, "terminal capture terminator is duplicated")
    pair6_metadata = [line for line in text.splitlines() if line.startswith("pair6_terminal_line=")]
    pair7_metadata = [line for line in text.splitlines() if line.startswith("pair7_terminal_line=")]
    capsule_metadata: dict[int, str] = {}
    for line in text.splitlines():
        match = re.fullmatch(r"regcap_terminal_line_([1-8])=(.*)", line)
        if match:
            index = int(match.group(1))
            require(index not in capsule_metadata, "duplicate capsule metadata index")
            capsule_metadata[index] = match.group(2)

    terminal_result = "absent"
    if pairs:
        terminal_result = PARENT.validate_terminal_semantics(records, pairs[0], pairs[1])
    if terminator_count == 1:
        require(len(pair6_metadata) == 1, "terminal lacks one pair-v6 metadata line")
        require(len(pair7_metadata) == 1, "terminal lacks one pair-v7 metadata line")
        require(
            set(capsule_metadata) == set(range(1, 9)),
            "terminal capsule metadata inventory changed",
        )
        metadata_pairs = (
            PARENT.parse_pair(pair6_metadata[0]),
            PARENT.parse_pair(pair7_metadata[0]),
        )
        require(
            len(pairs) == 2
            and [item[2] for item in metadata_pairs] == [item[2] for item in pairs],
            "pair metadata differs from the latest snapshot",
        )
        metadata_capsules = [parse_regcap(capsule_metadata[index]) for index in range(1, 9)]
        require(
            [item["normalized"] for item in metadata_capsules]
            == [item["normalized"] for item in capsules],
            "capsule metadata differs from the latest snapshot",
        )
        validate_capsule_terminal(capsules, terminal_result)
        capture_class = "terminal"
    else:
        require(
            not pair6_metadata and not pair7_metadata and not capsule_metadata,
            "terminal metadata lacks its capture terminator",
        )
        require(bool(records) or bool(pairs), "latest snapshot has no attributable marker")
        if len(capsules) == 8:
            validate_capsule_terminal(capsules, terminal_result)
            capture_class = "raw-terminal" if raw_log else "transport-truncated-valid-snapshot"
        elif pairs or capsules:
            capture_class = "capsule-prefix"
        elif transport_tail == "truncated":
            capture_class = "transport-truncated-valid-snapshot"
        else:
            capture_class = "valid-prefix"
    pass_slots = sum(
        1
        for start in (0, 4)
        if len(capsules[start : start + 4]) == 4
        and str(capsules[start]["result"]) == "pass"
    )
    return {
        "validation": "a72-target-register-capsule-structure-pass",
        "latest_sequence": sequence,
        "phase_records": len(records),
        "terminal_result": terminal_result,
        "capsule_records": len(capsules),
        "capsule_complete_slots": len(capsules) // 4,
        "capsule_pass_slots": pass_slots,
        "transport_tail": transport_tail,
        "capture_class": capture_class,
    }


def raw_capture(text: str) -> str:
    relevant = [
        line
        for line in text.splitlines()
        if any(
            token in line
            for token in (
                "gemini-a72-sc-phase",
                "gemini-a72-pair-v6",
                "gemini-a72-pair-v7",
                "gemini-a72-regcap-v1",
            )
        )
    ]
    return "\n".join(
        (
            f"capsule_trace_snapshot_begin sequence=1 lines={len(relevant)}",
            *relevant,
            "capsule_trace_snapshot_end sequence=1",
        )
    )


def synthetic_capsule(cpu: int) -> list[str]:
    require(cpu in (8, 9), "synthetic capsule CPU changed")
    mpidr = 0x200 if cpu == 8 else 0x201
    values: dict[str, dict[str, str]] = {
        "core": {
            "cpu": str(cpu), "abi": "1", "fields": "32", "valid": "0x1f",
            "error": "0", "complete": "1", "identity": "0" * 16,
            "mpidr": f"{mpidr:016x}", "midr": "410fd083", "revidr": "00000000",
            "cntfrq": "01a4e9c0", "ctr": "8444c004", "dczid": "00000004",
            "clidr": "0000000000000023",
        },
        "aa64": {
            "cpu": str(cpu), "identity": "0" * 16, "dfr0": "0000000010305106",
            "isar0": "0000000000011120", "isar1": "0000000000000000",
            "mmfr0": "0000000000001124", "mmfr1": "0000000000000000",
            "pfr0": "0000000000002222", "pfr1": "0000000000000000",
        },
        "a32isar": {
            "cpu": str(cpu), "identity": "0" * 16, "isar0": "02101110",
            "isar1": "13112111", "isar2": "21232042", "isar3": "01112131",
            "isar4": "00011142", "isar5": "00011121",
        },
        "a32mm": {
            "cpu": str(cpu), "identity": "0" * 16, "mmfr0": "10201105",
            "mmfr1": "40000000", "mmfr2": "01260000", "mmfr3": "02102211",
            "pfr0": "00000131", "pfr1": "00011011",
        },
    }
    group = [
        {
            "part": part,
            "result": "pass",
            "cpu": cpu,
            "identity": "0" * 16,
            "normalized": "",
            "values": values[part],
        }
        for part in REGCAP_PARTS
    ]
    identity = f"{capsule_identity(group):016x}"
    for part in REGCAP_PARTS:
        values[part]["identity"] = identity
    return [
        "gemini-a72-regcap-v1 "
        f"part={part} result=pass "
        + " ".join(f"{name}={values[part][name]}" for name in REGCAP_FIELDS[part])
        for part in REGCAP_PARTS
    ]


def render_terminal_capture() -> str:
    records = valid_complete_trace()
    pair6 = PARENT.synthetic_pair_line(6, "pass")
    pair7 = PARENT.synthetic_pair_line(7, "pass", parent_pass=1)
    capsules = synthetic_capsule(8) + synthetic_capsule(9)
    payload = [
        *(PARENT.marker_line(record, index + 1) for index, record in enumerate(records)),
        pair6,
        pair7,
        *capsules,
    ]
    metadata = [
        f"pair6_terminal_line={pair6}",
        f"pair7_terminal_line={pair7}",
        *(f"regcap_terminal_line_{index}={line}" for index, line in enumerate(capsules, 1)),
        TERMINATOR,
    ]
    return "\n".join(
        (
            f"capsule_trace_snapshot_begin sequence=1 lines={len(payload)}",
            *payload,
            "capsule_trace_snapshot_end sequence=1",
            *metadata,
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--capture", type=Path)
    source.add_argument("--raw-kernel-log", type=Path)
    args = parser.parse_args()
    if args.capture is not None:
        text = args.capture.read_text(encoding="utf-8")
        result = analyze_capture_text(text)
    else:
        text = args.raw_kernel_log.read_text(encoding="utf-8")
        result = analyze_capture_text(raw_capture(text), raw_log=True)
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CaptureError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
