#!/usr/bin/env python3
"""Require representative unsafe attestation/READY mutations to fail."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("attestation_validate", SCRIPT_DIR / "validate.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def paths() -> tuple[Path, Path]:
    experiment = SCRIPT_DIR.parent
    repository = experiment.parents[1]
    return (
        experiment / "schema" / "attestation-ledger-v1.json",
        repository
        / "experiments/2026-08-28-a72-pmsg-witness/results/"
        / "runtime-attempt-1-complete-pass-20260829.txt",
    )


def target(document: dict[str, Any], cpu: int) -> dict[str, Any]:
    return next(item for item in document["reference_capture"]["targets"] if item["cpu"] == cpu)


def stage(document: dict[str, Any], stage_id: str) -> dict[str, Any]:
    return next(item for item in document["architecture_contract"]["stages"] if item["id"] == stage_id)


def mutations() -> list[tuple[str, Callable[[dict[str, Any]], None]]]:
    return [
        ("wrong-target-cpu", lambda d: target(d, 8).__setitem__("cpu", 7)),
        ("wrong-cpu8-mpidr", lambda d: target(d, 8).__setitem__("mpidr", "0000000000000201")),
        ("wrong-cpu9-midr", lambda d: target(d, 9)["registers"].__setitem__("midr", "410fd080")),
        ("remove-observed-field", lambda d: d["reference_capture"]["register_image_observed_fields"].pop()),
        ("overlap-observed-unmeasured", lambda d: d["reference_capture"]["register_image_unmeasured_fields"].append("ctr")),
        ("invent-unmeasured-zero", lambda d: target(d, 8)["registers"].__setitem__("aidr", "0000000000000000")),
        ("promote-reference-role", lambda d: d["reference_capture"].__setitem__("role", "current-mainline-runtime")),
        ("allow-runtime-copy", lambda d: d["reference_capture"].__setitem__("may_populate_current_runtime_observation", True)),
        ("promote-partial-id-registers", lambda d: d["abi7_mapping"]["target_cap_groups"]["ID_REGS"].__setitem__("reference", "complete")),
        ("invent-current-gic", lambda d: d["abi7_mapping"]["target_cap_groups"]["GIC"].__setitem__("current_mainline", "complete")),
        ("borrow-gemian-policy", lambda d: d["abi7_mapping"]["current_boot_only_fields"]["target_policy"].__setitem__("owner", "gemian-reference-capture")),
        ("permit-observed-midr-copy", lambda d: d["architecture_contract"]["forbidden_copy_destinations"].remove("observed_target_midr")),
        ("validate-after-online", lambda d: d["architecture_contract"]["entry_validation_sources"]["new_order"].append(d["architecture_contract"]["entry_validation_sources"]["new_order"].pop(2))),
        ("reorder-commit", lambda d: stage(d, "commit-architecture-effects").__setitem__("order", 7)),
        ("remove-commit", lambda d: d["architecture_contract"]["stages"].pop(5)),
        ("platform-owned-commit", lambda d: stage(d, "commit-architecture-effects").__setitem__("owner", "mt6797-profile")),
        ("request-before-ready", lambda d: d["architecture_contract"]["physical_actions"].__setitem__("cpu_request_before_ready", True)),
        ("request-cpu9", lambda d: d["architecture_contract"]["physical_actions"].__setitem__("cpu9_request", True)),
        ("allow-cpu-off", lambda d: d["architecture_contract"]["physical_actions"].__setitem__("cpu_off", True)),
        ("allow-retry", lambda d: d["architecture_contract"]["physical_actions"].__setitem__("retry_count_max", 1)),
        ("continue-after-entry-mismatch", lambda d: d["architecture_contract"]["physical_actions"].__setitem__("entry_mismatch", "continue-secondary-startup")),
    ]


def main() -> int:
    ledger_path, capture_path = paths()
    original = json.loads(ledger_path.read_text())
    capture = capture_path.read_text()
    VALIDATOR.validate_document(original, capture)

    rejected = 0
    for name, mutate in mutations():
        candidate = copy.deepcopy(original)
        mutate(candidate)
        try:
            VALIDATOR.validate_document(candidate, capture)
        except VALIDATOR.ValidationError:
            rejected += 1
        else:
            raise AssertionError(f"unsafe mutation accepted: {name}")

    print("validation=mainline-a72-attestation-mutations-pass")
    print("positive_cases=1")
    print(f"unsafe_mutations_rejected={rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
