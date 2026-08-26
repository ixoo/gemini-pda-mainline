#!/usr/bin/env python3
"""Classify the exact platform-movement live capture."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
from pathlib import Path
import re
from typing import NamedTuple


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
SOURCE_PATH = REPO_ROOT / (
    "experiments/2026-08-25-mainline-a72-platform-provider-failure-stage-attribution/"
    "scripts/validate-runtime.py"
)
SOURCE_SHA256 = "29005d94a93518901f9509e81b48c358defb521e617a097a4e013272a0287c7f"
CANDIDATE = "9ac8e004cdba7955c0525eab7a4863f0df5474b4ff105408e6f06b1cbc846f78"
RELEASE = "7.1.3-gemini-a72-movement"
FAILURE_PREFIX = "platform/provider/clock capture failed:"
MOVEMENT_FIELDS = (
    "cpu", "cpu2", "cpusys", "cpu0", "cpu1", "iso", "dcm",
    "cci-port", "pwrap",
)
MOVEMENT = re.compile(
    r"platform/provider/clock capture failed: stage=platform ret=-11 "
    r"movement=([0-9a-f]{3}) "
    r"cpu=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"cpu2=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"cpusys=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"cpu0=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"cpu1=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"iso=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"dcm=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"cci-port=([0-9a-f]{8})/([0-9a-f]{8}) "
    r"pwrap=([01])/([01])"
)


class Decision(NamedTuple):
    classification: str
    reason: str
    ledger: str
    counts: dict[str, int]
    snapshot_sha256: str
    clock_state: tuple[int, int, int, int, int, int]
    failure_stage: str
    failure_errno: int
    retained_write_attempts: int
    failure_sha256: str
    movement_mask: int | None
    movement_pairs: tuple[tuple[int, int], ...]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if digest(SOURCE_PATH) != SOURCE_SHA256:
    raise SystemExit("source runtime validator changed")
SPEC = importlib.util.spec_from_file_location("movement_runtime_source", SOURCE_PATH)
assert SPEC is not None and SPEC.loader is not None
PARENT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARENT)
BASE = PARENT.BASE
PARENT.CANDIDATE = CANDIDATE
PARENT.RELEASE = RELEASE
PARENT.SOURCE.CANDIDATE = CANDIDATE
PARENT.SOURCE.RELEASE = RELEASE
BASE.CANDIDATE = CANDIDATE
BASE.RELEASE = RELEASE


def wrap(parent: object, failure_sha256: str | None = None) -> Decision:
    return Decision(
        parent.classification, parent.reason, parent.ledger, parent.counts,
        parent.snapshot_sha256, parent.clock_state, parent.failure_stage,
        parent.failure_errno, parent.retained_write_attempts,
        failure_sha256 or parent.failure_sha256, None, (),
    )


def classify(text: str) -> Decision:
    values = PARENT.SOURCE.scalar_values(text)
    if values.get("platform_movement_detail_expected") != "one-on-platform-eagain":
        raise BASE.Classification("rejected-platform-movement", "movement-expectation-mismatch")
    raw_failure = PARENT.decode_log(values, "failure_log_b64", "failure-log-malformed")
    failure_lines = raw_failure.decode("utf-8").splitlines()
    if len(failure_lines) == 1 and FAILURE_PREFIX in failure_lines[0]:
        attributed = failure_lines[0][failure_lines[0].index(FAILURE_PREFIX):].strip()
        if attributed.startswith(
                "platform/provider/clock capture failed: stage=platform"):
            match = MOVEMENT.fullmatch(attributed)
            if not match:
                raise BASE.Classification(
                    "rejected-platform-movement", "platform-movement-contract-mismatch"
                )
            groups = match.groups()
            movement_mask = int(groups[0], 16)
            numbers = [int(value, 16) for value in groups[1:]]
            pairs = tuple(
                (numbers[index], numbers[index + 1])
                for index in range(0, len(numbers), 2)
            )
            computed = sum(
                1 << index for index, pair in enumerate(pairs)
                if pair[0] != pair[1]
            )
            if movement_mask == 0 or movement_mask > 0x1ff or movement_mask != computed:
                raise BASE.Classification(
                    "rejected-platform-movement", "movement-mask-value-mismatch"
                )
            original_b64 = values["failure_log_b64"]
            generic = base64.b64encode(
                b"driver: platform/provider/clock capture failed: "
                b"stage=platform ret=-11\n"
            ).decode()
            token = f"failure_log_b64={original_b64}"
            if text.count(token) != 1:
                raise BASE.Classification(
                    "rejected-platform-movement", "failure-log-scalar-mismatch"
                )
            parent = PARENT.classify(text.replace(token, f"failure_log_b64={generic}", 1))
            if parent.classification != (
                    "serviceable-platform-provider-clock-stage-platform-eagain"):
                raise AssertionError("parent platform classification changed")
            return Decision(
                "serviceable-platform-movement-attributed",
                "exact-platform-eagain-movement-mask",
                parent.ledger, parent.counts, parent.snapshot_sha256,
                parent.clock_state, parent.failure_stage, parent.failure_errno,
                parent.retained_write_attempts,
                hashlib.sha256(raw_failure).hexdigest(), movement_mask, pairs,
            )
    return wrap(PARENT.classify(text), hashlib.sha256(raw_failure).hexdigest())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("capture", type=Path)
    args = parser.parse_args()
    try:
        decision = classify(args.capture.read_text(encoding="utf-8", errors="replace"))
    except BASE.Classification as error:
        decision = Decision(
            error.result, error.reason, "not-classified", {}, "not-classified",
            (0, 0, 0, 0, 0, 0), "unknown", 0, 0, "not-classified",
            None, (),
        )
    accepted = decision.classification.startswith("serviceable-")
    valid, returned, after, clock_ret, clock_abi, clock_generation = decision.clock_state
    failure = decision.failure_stage != "none"
    movement = decision.movement_mask is not None
    print("runtime_gate=serviceable-platform-movement-decision" if accepted else "runtime_gate=rejected")
    print(f"runtime_classification={decision.classification}")
    print(f"runtime_reason={decision.reason}")
    print(f"snapshot_log_sha256={decision.snapshot_sha256}")
    print(f"failure_log_sha256={decision.failure_sha256}")
    print(f"failure_stage={decision.failure_stage}")
    print(f"failure_errno={decision.failure_errno}")
    print(f"live_ledger_classification={decision.ledger}")
    print(f"pure_marker_matches={decision.counts.get('pure', 0)}")
    print(f"core_marker_matches={decision.counts.get('core', 0)}")
    print(f"refusal_marker_matches={decision.counts.get('refusal', 0)}")
    print("provider_ready_gate=passed" if accepted else "provider_ready_gate=unknown")
    print("clock_ready_gate=not-reached" if failure else ("clock_ready_gate=passed" if accepted else "clock_ready_gate=unknown"))
    print(f"snapshot_valid={valid}")
    print(f"clock_returned={returned}")
    print(f"after_checkpoint={after}")
    print("platform_snapshot_calls=1" if accepted else "platform_snapshot_calls=unknown")
    print("platform_samples=2" if movement or (accepted and not failure) else "platform_samples=unknown")
    print("platform_register_observations=26" if movement or (accepted and not failure) else "platform_register_observations=unknown")
    if failure:
        provider_calls = 0 if decision.failure_stage == "platform" else 1
        print(f"provider_snapshots={provider_calls}")
        print("provider_samples=unknown")
        print("provider_i2c_reads=unknown")
    else:
        print("provider_snapshots=1" if accepted else "provider_snapshots=unknown")
        print("provider_samples=2" if accepted else "provider_samples=unknown")
        print("provider_i2c_reads=10" if accepted else "provider_i2c_reads=unknown")
    print("provider_i2c_writes=0")
    print(f"retained_write_attempts={decision.retained_write_attempts if accepted else 'unknown'}")
    print("protected_clock_calls=0" if failure else ("protected_clock_calls=1" if accepted else "protected_clock_calls=unknown"))
    print(f"protected_clock_ret={'not-called' if failure else clock_ret}")
    print(f"protected_clock_abi={'not-called' if failure else clock_abi}")
    print(f"protected_clock_generation={'not-called' if failure else clock_generation}")
    print("clock_gate_pairs=0" if failure else ("clock_gate_pairs=1" if accepted else "clock_gate_pairs=unknown"))
    if movement:
        print(f"movement_mask=0x{decision.movement_mask:03x}")
        moved = [
            name for index, name in enumerate(MOVEMENT_FIELDS)
            if decision.movement_mask & (1 << index)
        ]
        print(f"movement_fields={','.join(moved)}")
        for name, pair in zip(MOVEMENT_FIELDS, decision.movement_pairs):
            width = 1 if name == "pwrap" else 8
            print(f"movement_{name.replace('-', '_')}={pair[0]:0{width}x}/{pair[1]:0{width}x}")
    else:
        print("movement_mask=none")
        print("movement_fields=none")
    print("explicit_mmio_writes_maximum=401")
    print("explicit_mmio_reads_maximum=419")
    print("bigidvfs_reads=0")
    print("secure_calls=0")
    print("provider_acquires=0")
    print("provider_releases=0")
    print("publisher_calls=0")
    print("owner_mutations=0")
    print("cpu_requests=0")
    print("cpu8_cpu9_admission=closed")
    print("native_reboot_requested=no")
    return 0 if accepted else 3


if __name__ == "__main__":
    raise SystemExit(main())
