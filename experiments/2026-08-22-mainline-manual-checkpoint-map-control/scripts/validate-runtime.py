#!/usr/bin/env python3
"""Classify the exact manual-checkpoint mapping-model control probe."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


BEGIN = "__MANUAL_CHECKPOINT_MAP_RUNTIME_BEGIN__"
END = "__MANUAL_CHECKPOINT_MAP_RUNTIME_END__"
CANDIDATE = "dd513384c78ee8378e1e4bf515f89b99ca87ed6ed86c1d38ec37f8aadd693b5b"
RELEASE = "7.1.3-gemini-checkpoint-map"
EMPTY_SIGNATURE = "43474244"
UINT_MAX = 4_294_967_295
REASONS = (
    "ramoops-map-unavailable",
    "ramoops-empty-parallel-all-ones",
    "both-empty",
    "views-match-other",
    "views-differ",
)
LIVE_RE = re.compile(
    r"GEMINI_MANUAL_CHECKPOINT_CONTROL_LIVE_V1 first=([01]) second=([01]) "
    r"retained_writes=([0-2]) protected_calls=0 cpu_requests=0"
)
STAGE_RE = re.compile(
    r"GEMINI_MANUAL_CHECKPOINT_STAGE_V1 first=([01]) second=([01]) "
    r"stage=([a-z-]+) writes=([0-2]) protected=0 cpu=0"
)
MAP_RE = re.compile(
    r"GEMINI_MANUAL_CHECKPOINT_MAP_CONTROL_V1 r=(\d+) p=([0-9a-f]+) "
    r"why=([a-z-]+) rh=([0-9a-f]{8})/(\d+)/(\d+) "
    r"ph=([0-9a-f]{8})/(\d+)/(\d+) rr=(\d+) pr=(\d+) w=(\d+)"
)


class Classification(Exception):
    def __init__(self, result: str, reason: str) -> None:
        super().__init__(reason)
        self.result = result
        self.reason = reason


def reject(result: str, reason: str) -> None:
    raise Classification(result, reason)


def empty(header: tuple[str, int, int]) -> bool:
    return header == (EMPTY_SIGNATURE, 0, 0)


def classify_text(text: str) -> tuple[str, str]:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        reject("rejected-attribution", "non-unique-runtime-section")
    start = text.index(BEGIN) + len(BEGIN)
    finish = text.index(END, start)
    values: dict[str, str] = {}
    for raw in text[start:finish].replace("\r", "").splitlines():
        line = raw.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[a-z0-9_]+", key) or key in values:
            reject("rejected-attribution", "malformed-or-duplicate-key")
        values[key] = value

    expected = {
        "installed_full_sha256": CANDIDATE,
        "kernel_release": RELEASE,
        "architecture": "aarch64",
        "model": "MT6797X",
        "cpu_possible": "0-9",
        "cpu_present": "0-9",
        "cpu_online": "0-7",
        "cpu_offline": "8-9",
        "udc_devices": "1",
        "keyboard_matrix_inputs": "1",
        "da921x_i2c_clients": "1",
        "same_value_write_attributes": "0",
        "clock_backend_devices": "0",
        "bigidvfs_backend_devices": "0",
        "protected_readback_devices": "0",
        "manual_live_prefix_count": "1",
        "manual_stage_prefix_count": "1",
        "manual_prefix_prefix_count": "0",
        "manual_map_prefix_count": "1",
        "block_mounts": "0",
        "device_partition_reads": "none",
        "device_storage_writes": "none",
        "driver_binding_changes": "none",
        "same_value_action_request": "none",
        "protected_read_request": "none",
        "secure_call_request": "none",
        "owner_registration_request": "none",
        "cpu_admission_request": "none",
        "reboot_request": "none",
    }
    safety_keys = {
        "cpu_online", "cpu_offline", "same_value_write_attributes",
        "clock_backend_devices", "bigidvfs_backend_devices",
        "protected_readback_devices", "manual_live_prefix_count",
        "manual_stage_prefix_count", "manual_prefix_prefix_count",
        "manual_map_prefix_count", "block_mounts", "device_storage_writes",
        "same_value_action_request", "protected_read_request",
        "secure_call_request", "owner_registration_request",
        "cpu_admission_request", "reboot_request",
    }
    for key, required in expected.items():
        if values.get(key) != required:
            reject(
                "rejected-safety" if key in safety_keys else "rejected-attribution",
                f"{key}-mismatch",
            )
    if not re.fullmatch(
        r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}",
        values.get("boot_id", ""),
    ):
        reject("rejected-attribution", "malformed-boot-id")
    if not re.fullmatch(r"\d+(?:\.\d+)?", values.get("uptime_seconds", "")):
        reject("rejected-attribution", "malformed-uptime")
    if not re.fullmatch(r"\d+", values.get("pstore_files", "")):
        reject("rejected-attribution", "malformed-pstore-count")
    if "maxcpus=8" not in values.get("cmdline", "").split():
        reject("rejected-safety", "maxcpus-policy-missing")

    live = LIVE_RE.fullmatch(values.get("manual_live_record", ""))
    stage = STAGE_RE.fullmatch(values.get("manual_stage_record", ""))
    observed = MAP_RE.fullmatch(values.get("manual_map_record", ""))
    if live is None or stage is None or observed is None:
        reject("rejected-attribution", "malformed-live-stage-or-map-record")
    if tuple(map(int, live.groups())) != (0, 0, 0):
        reject("rejected-attribution", "historical-control-count-mismatch")
    if (int(stage.group(1)), int(stage.group(2)), stage.group(3), int(stage.group(4))) != (
        0, 0, "map-control-observed", 0
    ):
        reject("rejected-attribution", "fixed-stage-mismatch")

    record, physical = int(observed.group(1)), observed.group(2)
    why = observed.group(3)
    ramoops = (observed.group(4), int(observed.group(5)), int(observed.group(6)))
    parallel = (observed.group(7), int(observed.group(8)), int(observed.group(9)))
    ramoops_reads, parallel_reads, writes = map(int, observed.groups()[9:])
    if record != 171 or physical != "444bb000" or why not in REASONS:
        reject("rejected-attribution", "map-identity-or-reason-mismatch")
    if parallel_reads != 3 or writes != 0 or ramoops_reads not in (0, 3):
        reject("rejected-attribution", "map-read-write-count-mismatch")

    parallel_all_ones = parallel == ("ffffffff", UINT_MAX, UINT_MAX)
    consistent = {
        "ramoops-map-unavailable": (
            ramoops_reads == 0 and ramoops == ("00000000", 0, 0)
        ),
        "ramoops-empty-parallel-all-ones": (
            ramoops_reads == 3 and empty(ramoops) and parallel_all_ones
        ),
        "both-empty": ramoops_reads == 3 and empty(ramoops) and empty(parallel),
        "views-match-other": (
            ramoops_reads == 3 and ramoops == parallel and not empty(ramoops)
        ),
        "views-differ": (
            ramoops_reads == 3
            and ramoops != parallel
            and not (empty(ramoops) and parallel_all_ones)
        ),
    }[why]
    if not consistent:
        reject("rejected-attribution", "map-reason-header-mismatch")
    return "manual-checkpoint-map-pass", f"decision-map-{why}"


def classify(path: Path) -> tuple[str, str]:
    try:
        return classify_text(path.read_text(encoding="utf-8", errors="replace"))
    except Classification as result:
        return result.result, result.reason


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    result, reason = classify(args.capture)
    accepted = result == "manual-checkpoint-map-pass"
    print(f"runtime_classification={result}")
    print(f"runtime_reason={reason}")
    print(f"manual_checkpoint_map={'accepted' if accepted else 'not-accepted'}")
    print("retained_header_reads=parallel-3,ramoops-maximum-3")
    print("retained_writes=0")
    print("protected_calls=0")
    print("DA921x_register_data_writes=0")
    print("cpu8_cpu9_admission=closed")
    print("claim_scope=manual-checkpoint-mapping-model-and-serviceability-only")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
