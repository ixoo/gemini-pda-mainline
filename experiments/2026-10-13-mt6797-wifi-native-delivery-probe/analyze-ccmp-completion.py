#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Read the three frozen private logs; emit only whitelisted numeric metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import re

PINS = (
    ("CCMP3", "d93be0aff544d19ea24ee79db30be08c69eab4e73733170703424dff9ed8907a", 164195),
    ("CCMP4", "c9e01e4121ddfa9e3199dd86a922385d66d488e633ce4494d477771553d813c9", 164933),
    ("CCMP5", "6abbd402c844b113ee63104cdaf600c48a01af8536f6917f880c6d8c6039c72f", 160188),
)
# Fixed field names and numeric captures only. Never serialize a raw log line,
# path, address, SSID, packet, key, or an exception containing private content.
PATTERNS = {
    "data_start": r"data phase: budget_ms=(?P<budget_ms>\d+) teardown_margin_ms=(?P<margin_ms>\d+) inside_grant=1",
    "first_submit": r"data TX: first pid=(?P<pid>\d+) pages=(?P<pages>\d+) bytes=(?P<bytes>\d+)",
    "completion": r"TX done: pid=(?P<pid>\d+) status=(?P<status>\d+) advanced=(?P<advanced>\d+) count=(?P<count>\d+)",
    "credit": r"data credit: pages=(?P<pages>\d+) debt=(?P<debt>\d+) count=(?P<count>\d+)",
    "timeout": r"data TX timeout: pid=(?P<pid>\d+) debt=(?P<debt>\d+) credits=(?P<credits>\d+) elapsed_ms=(?P<elapsed_ms>\d+)",
    "stop": r"stopped: status=(?P<status>-?\d+) first=(?P<first>-?\d+) submitted=(?P<submitted>0x[0-9a-f]+) debt=(?P<debt>\d+) cleanup=(?P<cleanup>\d+) branch=(?P<branch>\d+)",
}


def analyze(path, label, digest, size):
    raw = path.read_bytes()
    if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(label + ": immutable log identity mismatch")
    sequence = []
    events = {name: [] for name in PATTERNS}
    refusals = 0
    for line in raw.decode("utf-8").splitlines():
        record = re.fullmatch(r"\d+,(\d+),(\d+),[^;]*;(.*)", line)
        if not record:  # /dev/kmsg continuation properties are not records.
            continue
        number, timestamp = int(record[1]), int(record[2])
        message = record[3]
        sequence.append(number)
        refusals += "one-shot WLAN native HIF refused:" in message
        marker = "one-shot WLAN join "
        if marker not in message:
            continue
        message = message.split(marker, 1)[1]
        for name, pattern in PATTERNS.items():
            match = re.fullmatch(pattern, message)
            if match:
                events[name].append({"sequence": number, "time_us": timestamp,
                                     **{key: int(value, 16 if value.startswith("0x") else 10)
                                        for key, value in match.groupdict().items()}})
    if sequence != list(range(len(sequence))):
        raise ValueError(label + ": discontinuous record sequence")
    if not all(len(events[name]) == 1 for name in ("data_start", "first_submit", "stop")):
        raise ValueError(label + ": missing or ambiguous required record")
    submit = events["first_submit"][0]
    done = [e for e in events["completion"] if e["pid"] == submit["pid"]]
    if len(done) != 1:
        raise ValueError(label + ": missing or ambiguous first completion")
    completion_count, credit_count = len(events["completion"]), len(events["credit"])
    pid6_done = any(e["pid"] == 6 for e in events["completion"])
    # Keep the decision-changing records, not a duplicate full chronology.
    events["completion"] = [e for e in events["completion"] if e["pid"] in (5, 6)]
    events["credit"] = events["credit"][:2]
    return {"run": label, "log_sha256": digest, "log_bytes": size,
            "records": len(sequence), "events": events,
            "recognized_completion_records": completion_count,
            "logged_credit_records": credit_count,
            "first_submit_to_completion_us": done[0]["time_us"] - submit["time_us"],
            "pid6_submit_time_observed": False,
            "pid6_completion_observed": pid6_done,
            "hif_refusal_records": refusals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logs", nargs=3, type=Path, metavar="LOG", help="C3, C4, C5 logs in order")
    args = parser.parse_args()
    try:
        runs = [analyze(path, *pin) for path, pin in zip(args.logs, PINS)]
    except (OSError, ValueError, UnicodeError, IndexError):
        parser.exit(1, "error: immutable log or record validation failed; no raw content emitted\n")
    print(json.dumps({"runs": runs, "limits": [
        "Recorded host handling times are not firmware/RF latency measurements",
        "No PID-6 submission timestamp was logged; none is reconstructed from timeout",
        "Missing recognized completion does not prove absence of a hardware event",
        "C5 ended before the C3/C4 comparison point; 0195 causality remains unresolved"
    ]}, indent=2))


if __name__ == "__main__":
    main()
