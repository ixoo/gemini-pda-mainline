#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Classify one private, receipt-bound targeted keyboard observation."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
PROTOCOL = json.loads((ROOT / "protocol.json").read_text())
SHA = re.compile(r"[0-9a-f]{64}")
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
HASH_INPUTS = (
    "candidate_sha256", "image_sha256", "dtb_sha256", "config_sha256",
    "initramfs_sha256", "helper_sha256", "launcher_sha256", "protocol_sha256",
    "input_capabilities_sha256", "baseline_first_boot_result_sha256",
    "baseline_recovery_result_sha256",
)
SCANS = {2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6,
         9: 48, 10: 49, 11: 54, 125: 35, 42: 30, 54: 43,
         105: 41, 103: 44, 108: 42, 106: 45, 30: 21,
         29: 38, 56: 33, 35: 22, 18: 12, 38: 46, 25: 51, 28: 53}


class Refusal(ValueError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise Refusal(message)


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate-json-field")
        result[key] = value
    return result


def read_json(path):
    require(path.is_file() and not path.is_symlink(), "json-not-regular")
    require(path.stat().st_size <= 65536, "json-byte-budget")
    return json.loads(path.read_bytes(), object_pairs_hook=no_duplicates)


def bind(expected, receipt, data):
    require(expected.get("schema_version") == 1 and
            expected.get("state") in ("conditional", "ready"), "contract-unfrozen")
    for key in HASH_INPUTS:
        value = expected.get(key)
        require(isinstance(value, str) and SHA.fullmatch(value), "missing-contract-" + key)
        require(receipt.get(key) == value, "mismatched-" + key)
    require(expected["protocol_sha256"] == sha((ROOT / "protocol.json").read_bytes()),
            "changed-protocol")
    for key in ("kernel_release", "input_sysfs_realpath"):
        require(isinstance(expected.get(key), str) and expected[key] and
                receipt.get(key) == expected[key], "mismatched-" + key)
    require(re.fullmatch(r"/sys/devices/platform/[^\s]+/input/input[0-9]+",
                         expected["input_sysfs_realpath"]), "unresolved-input-path")
    require(receipt.get("schema_version") == 1, "receipt-version")
    for key in ("deployment_receipt_sha256", "recovery_reference_sha256"):
        require(isinstance(receipt.get(key), str) and SHA.fullmatch(receipt[key]),
                "missing-" + key)
    for key in ("boot_id_before", "boot_id_after", "known_good_boot_id"):
        require(isinstance(receipt.get(key), str) and UUID.fullmatch(receipt[key]),
                "missing-" + key)
    require(receipt["boot_id_before"] == receipt["boot_id_after"] !=
            receipt["known_good_boot_id"], "lost-boot-attribution")
    require(receipt.get("cpu_online_before") == "0-7" and
            receipt.get("cpu_online_after") == "0-7", "cpu-policy")
    require(receipt.get("map_sha256") == PROTOCOL["map_sha256"], "map-identity")
    for key in ("map_verify_before", "map_verify_after", "baseline_dependencies_verified",
                "console_logs_separated", "tty1_exclusive", "owner_sequence_complete",
                "owner_screen_readable", "post_capture_usb_pass", "budget_claimed_once"):
        require(receipt.get(key) is True, "missing-witness-" + key)
    require(receipt.get("capture_exit_status") == 0, "capture-exit")
    require(receipt.get("capture_sha256") == sha(data), "capture-checksum")
    require(re.fullmatch(r"event[0-9]+", str(receipt.get("event"))), "event-identity")
    require(type(receipt.get("event_minor")) is int and 0 <= receipt["event_minor"] <= 1048575,
            "event-minor")


def parse(data, receipt):
    require(len(data) <= 262144, "capture-byte-budget")
    try:
        lines = iter(data.decode("ascii").splitlines())
    except UnicodeDecodeError as exc:
        raise Refusal("capture-not-ascii") from exc

    def exact(wanted):
        require(next(lines, None) == wanted, "incomplete-or-unexpected-frame")

    exact("keyboard-observe version=1")
    exact(f"device event={receipt['event']} major=13 minor={receipt['event_minor']} name=keyboard-matrix")
    exact("window events=0 bytes=0 held=0")
    exact("preflight state=pass vt=1 unicode=1 held=0 functions=exact")
    cases = []
    for step in PROTOCOL["steps"]:
        exact(f"step begin index={step['index']}")
        edges, scans, vt = [], [], bytearray()
        event_count = 0
        pending_scan = None
        frame_dirty = False
        while True:
            line = next(lines, None)
            require(line is not None, "truncated-step")
            end = re.fullmatch(r"window events=([0-9]+) bytes=([0-9]+) held=0", line)
            if end:
                require(pending_scan is None and not frame_dirty, "unfinished-event-frame")
                require([int(end[1]), int(end[2])] == [event_count, len(vt)], "counter-mismatch")
                break
            event = re.fullmatch(r"event type=([0-9]+) code=([0-9]+) value=(-?[0-9]+)", line)
            tty = re.fullmatch(r"tty hex=([0-9a-f]+)", line)
            if event:
                event_count += 1
                require(event_count <= PROTOCOL["max_events_per_step"], "event-budget")
                kind, code, value = map(int, event.groups())
                if kind == 0:
                    require(code == 0 and value == 0 and pending_scan is None,
                            "dropped-or-malformed-sync")
                    frame_dirty = False
                elif kind == 4:
                    require(code == 4 and 0 <= value <= 63 and pending_scan is None,
                            "malformed-scan")
                    pending_scan = value
                    frame_dirty = True
                elif kind == 1:
                    require(value in (0, 1), "repeat-or-malformed-key")
                    require(pending_scan is not None, "key-without-scan")
                    edges.append([code, value])
                    scans.append(pending_scan)
                    pending_scan = None
                    frame_dirty = True
                else:
                    raise Refusal("unexpected-event-type")
            elif tty:
                require(len(tty[1]) % 2 == 0, "malformed-tty-hex")
                vt.extend(bytes.fromhex(tty[1]))
                require(len(vt) <= PROTOCOL["max_tty_bytes_per_step"], "tty-byte-budget")
            else:
                raise Refusal("unrecognized-capture-record")
        exact(f"step end index={step['index']}")
        cases.append((edges, scans, vt.hex()))
    exact("complete steps=20 restored=1")
    require(next(lines, None) is None, "trailing-capture-record")
    return cases


def classify(expected, receipt, data):
    try:
        bind(expected, receipt, data)
        cases = parse(data, receipt)
    except (Refusal, KeyError, TypeError, ValueError) as exc:
        return {"classification": "inconclusive", "reason": str(exc), "hardware_claim": False}
    results = []
    for step, (edges, scans, vt) in zip(PROTOCOL["steps"], cases):
        expected_scans = [SCANS[code] for code, _value in step["key_edges"]]
        if edges != step["key_edges"] or scans != expected_scans:
            result = "input-sequence-mismatch"
        elif vt != step["vt_hex"]:
            result = "vt-byte-mismatch"
        else:
            result = "pass"
        results.append({"step": step["index"], "result": result})
    return {"classification": "pass" if all(c["result"] == "pass" for c in results)
            else "mismatch-requires-owner-trace-review", "cases": results,
            "scope": "targeted-function-navigation-modifier-sequence-once",
            "release_reliability_gate": "separate",
            "hardware_claim": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--capture", required=True, type=Path)
    args = parser.parse_args()
    try:
        require(args.capture.is_file() and not args.capture.is_symlink(), "capture-not-regular")
        require(args.capture.stat().st_size <= 262144, "capture-byte-budget")
        result = classify(read_json(args.contract), read_json(args.receipt), args.capture.read_bytes())
    except (OSError, ValueError) as exc:
        result = {"classification": "inconclusive", "reason": str(exc), "hardware_claim": False}
    print(json.dumps(result, indent=2))
    return 0 if result["classification"] == "pass" else 2


if __name__ == "__main__":
    sys.exit(main())
