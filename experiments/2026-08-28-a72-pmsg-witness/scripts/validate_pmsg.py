#!/usr/bin/env python3
"""Classify one changed-cycle Gemian pmsg capture without trusting other bytes."""

from __future__ import annotations

import argparse
import hashlib
import re
import stat
import sys
from pathlib import Path


PREFIX = b"gemini-a72-pmsg-"
ENTRY = b"gemini-a72-pmsg-v1 stage=entry parent=register-capsule\n"
PRE_SCHEDULER = b"gemini-a72-pmsg-v1 stage=pre-scheduler parent=pair-v6-pass\n"
TERMINAL_PASS = b"gemini-a72-pmsg-v1 stage=pre-capsule result=pass\n"
TERMINAL_FAULT = b"gemini-a72-pmsg-v1 stage=pre-capsule result=fault\n"
KNOWN_RECORDS = (ENTRY, PRE_SCHEDULER, TERMINAL_PASS, TERMINAL_FAULT)
VALID_SEQUENCES = {
    (): "no-pmsg-witness",
    (ENTRY,): "before-pre-scheduler",
    (ENTRY, PRE_SCHEDULER): "before-pre-capsule",
    (ENTRY, PRE_SCHEDULER, TERMINAL_PASS): "pre-capsule-pass-await-capsules",
    (ENTRY, PRE_SCHEDULER, TERMINAL_FAULT): "scheduler-capsule-fault",
}
SHA256 = re.compile(r"[0-9a-f]{64}")
KERNEL_RELEASE = re.compile(r"[A-Za-z0-9._+-]+")
MAX_PMSG_BYTES = 1_048_576


class EvidenceError(ValueError):
    """The capture cannot safely support a pmsg classification."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def parse_records(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r"([a-z0-9_]+)=([^\r\n]+)", line)
        require(match is not None, f"malformed cycle record: {line!r}")
        key, value = match.groups()
        require(key not in result, f"duplicate cycle record: {key}")
        result[key] = value
    return result


def validate_cycle(cycle: Path) -> dict[str, str]:
    require(cycle.is_file() and not cycle.is_symlink(), "unsafe cycle file")
    records = parse_records(cycle)
    required = {
        "wait_for_cycle",
        "initial_boot_id_sha256",
        "final_boot_id_sha256",
        "boot_id_changed",
        "capture_kernel",
        "capture_arch",
        "expected_kernel",
        "archive_pre_boot_id_sha256",
        "archive_post_boot_id_sha256",
    }
    require(required <= records.keys(), "cycle record inventory is incomplete")
    require(records["wait_for_cycle"] == "yes", "capture did not wait for a cycle")
    require(records["boot_id_changed"] == "yes", "capture boot ID did not change")
    initial = records["initial_boot_id_sha256"]
    final = records["final_boot_id_sha256"]
    require(SHA256.fullmatch(initial) is not None, "initial boot-ID hash malformed")
    require(SHA256.fullmatch(final) is not None, "final boot-ID hash malformed")
    require(initial != final, "boot-ID hashes did not change")
    require(
        records["archive_pre_boot_id_sha256"] == final
        and records["archive_post_boot_id_sha256"] == final,
        "pstore archive is not bound to the final boot ID",
    )
    require(records["capture_arch"] == "aarch64", "recovery architecture changed")
    require(
        KERNEL_RELEASE.fullmatch(records["capture_kernel"]) is not None,
        "recovery kernel release malformed",
    )
    require(
        records["capture_kernel"] == records["expected_kernel"],
        "recovery kernel does not match the cycle contract",
    )
    return records


def extract_witnesses(raw: bytes) -> list[bytes]:
    records: list[bytes] = []
    offset = 0
    while True:
        start = raw.find(PREFIX, offset)
        if start < 0:
            break
        end = raw.find(b"\n", start)
        require(end >= 0, "unterminated pmsg witness-family record")
        record = raw[start : end + 1]
        require(len(record) <= 256, "oversized pmsg witness-family record")
        require(record in KNOWN_RECORDS, "malformed pmsg witness-family record")
        records.append(record)
        offset = start + len(PREFIX)
    return records


def classify_capture(capture: Path) -> dict[str, str]:
    require(capture.is_dir() and not capture.is_symlink(), "unsafe capture root")
    cycle = validate_cycle(capture / "cycle.txt")
    pstore = capture / "pstore"
    require(pstore.is_dir() and not pstore.is_symlink(), "unsafe pstore directory")
    pmsg_files = sorted(
        path.name
        for path in pstore.iterdir()
        if path.name.startswith("pmsg-ramoops")
    )
    require(
        pmsg_files in ([], ["pmsg-ramoops-0"]),
        "unexpected pmsg file inventory",
    )
    pmsg = pstore / "pmsg-ramoops-0"
    if not pmsg_files:
        raw = b""
        pmsg_state = "absent"
    else:
        info = pmsg.stat()
        require(
            pmsg.is_file() and not pmsg.is_symlink() and info.st_nlink == 1,
            "unsafe pmsg file",
        )
        require(
            stat.S_IMODE(info.st_mode) == 0o600,
            "unsafe pmsg file mode",
        )
        require(0 < info.st_size <= MAX_PMSG_BYTES, "unsafe pmsg file size")
        raw = pmsg.read_bytes()
        pmsg_state = "present"
    witnesses = extract_witnesses(raw)
    sequence = tuple(witnesses)
    require(sequence in VALID_SEQUENCES, "duplicate, mixed, or out-of-order pmsg witnesses")
    counts = {record: witnesses.count(record) for record in KNOWN_RECORDS}
    return {
        "validation": "a72-pmsg-changed-cycle",
        "capture_kernel": cycle["capture_kernel"],
        "boot_id_changed": "yes",
        "pmsg_file": pmsg_state,
        "pmsg_sha256": hashlib.sha256(raw).hexdigest() if raw else "none",
        "pmsg_size": str(len(raw)),
        "entry_records": str(counts[ENTRY]),
        "pre_scheduler_records": str(counts[PRE_SCHEDULER]),
        "terminal_pass_records": str(counts[TERMINAL_PASS]),
        "terminal_fault_records": str(counts[TERMINAL_FAULT]),
        "classification": VALID_SEQUENCES[sequence],
        "capsule_result": (
            "required"
            if sequence == (ENTRY, PRE_SCHEDULER, TERMINAL_PASS)
            else "not-applicable"
        ),
        "screen_evidence": "non-classifying",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, required=True)
    args = parser.parse_args()
    result = classify_capture(args.capture.resolve())
    for key, value in result.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvidenceError, OSError, UnicodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1) from error
