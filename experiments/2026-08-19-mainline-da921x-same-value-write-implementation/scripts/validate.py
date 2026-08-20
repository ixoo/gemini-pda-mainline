#!/usr/bin/env python3
"""Validate the bounded implementation plan without touching hardware."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract.json"
REVIEW = ROOT.parent / "2026-08-19-mainline-da921x-same-value-write-preflight-review" / "contract.json"


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate(contract: dict, review_sha256: str) -> None:
    require(contract["schema"] == "gemini-da921x-same-value-write-implementation-v1",
            "schema changed")
    require(contract["status"] == "canonical-patches-admitted-build-pending",
            "status changed")
    parent = contract["review_parent"]
    require(parent["repository_commit"] ==
            "ca3caa3e3c814da61a0ca113c69fc87e3bc1140e", "parent changed")
    require(parent["contract_sha256"] == review_sha256, "review checksum changed")
    require([item["number"] for item in contract["patch_plan"]] ==
            ["0290", "0291", "0292"], "patch order changed")
    require([item["scope"] for item in contract["patch_plan"]] == [
        "ledger-v2-and-read-only-locked-prefix-verifier",
        "one-shot-production-sequence",
        "hardware-free-kunit",
    ], "logical patch scopes changed")

    production = contract["production"]
    require(production["token"] == "run-same-value-write-20260819-a",
            "token changed")
    require(production["pretrigger_entries"] == 20 and
            production["ledger_capacity"] == 32 and
            production["action_transfers"] == 12, "ledger accounting changed")
    require(production["write_ordinal"] == 6 and
            production["write_address"] == "0x68" and
            production["write_payload"] == ["0xda", "0x46"], "write changed")
    require(production["root_lock_calls"] == production["root_unlock_calls"] == 1,
            "root lock changed")
    require(production["retries_during"] == 0 and
            production["delay_us"] == {"minimum": 10000, "maximum": 11000},
            "retry or delay changed")
    require(production["automatic_retry"] is False and
            production["second_or_inverse_write"] is False,
            "repeat or inverse admitted")
    require(production["page_con_accesses"] == 0 and
            production["consumer_requests"] == 0 and
            production["cpu_requests"] == 0, "forbidden action admitted")

    tests = contract["hardware_free_tests"]
    require(tests["registered_adapters"] == tests["registered_clients"] == 0 and
            tests["physical_mmio"] is False and tests["physical_transfers"] == 0,
            "tests must remain hardware-free")
    require(tests["success_path"] and tests["admission_refusals"] and
            tests["ledger_refusal"], "required test family missing")
    require(tests["transfer_failure_ordinals"] == 12 and
            tests["value_mismatch_ordinals"] == 11 and
            tests["retry_restoration_every_exit"] and
            tests["payload_bytes_checked"] == 2, "failure coverage changed")

    workflow = contract["workflow"]
    require(workflow["patch_generation_backend"] == "buildbox" and
            workflow["kernel_build_backend"] == "buildbox" and
            workflow["native_vm_build"] is False and
            workflow["clean_pushed_commit_required"] is True and
            workflow["canonical_series_audit"] is True and
            workflow["all_profiles_audit"] is True, "workflow boundary changed")

    decision = contract["decision"]
    require(decision["implementation_in_progress"] is True and
            decision["boot_candidate_exists"] is False and
            decision["physical_da921x_write_authorized"] is False and
            decision["device_action"] == "none", "premature hardware decision")
    require(decision["cpu8_cpu9_admission"] == "closed", "CPU admission changed")
    require(decision["next_success_gate"] ==
            "focused-buildbox-kunit-build-and-network-free-qemu-pass",
            "next success gate changed")


def mutate(candidate: dict, path: tuple, value: object) -> None:
    node = candidate
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


def test_mutations(contract: dict, review_sha256: str) -> int:
    mutations = [
        (("patch_plan", 0, "number"), "0291"),
        (("production", "action_transfers"), 13),
        (("production", "write_ordinal"), 5),
        (("production", "write_address"), "0x69"),
        (("production", "write_payload", 1), "0x45"),
        (("production", "root_lock_calls"), 12),
        (("production", "retries_during"), 1),
        (("production", "automatic_retry"), True),
        (("production", "second_or_inverse_write"), True),
        (("production", "cpu_requests"), 1),
        (("hardware_free_tests", "physical_transfers"), 1),
        (("hardware_free_tests", "transfer_failure_ordinals"), 11),
        (("workflow", "kernel_build_backend"), "vm"),
        (("decision", "boot_candidate_exists"), True),
        (("decision", "physical_da921x_write_authorized"), True),
        (("decision", "cpu8_cpu9_admission"), "open"),
    ]
    rejected = 0
    for path, value in mutations:
        candidate = copy.deepcopy(contract)
        mutate(candidate, path, value)
        try:
            validate(candidate, review_sha256)
        except ValidationError:
            rejected += 1
        else:
            raise ValidationError(f"unsafe mutation accepted: {path}")
    return rejected


def main() -> None:
    review_sha256 = hashlib.sha256(REVIEW.read_bytes()).hexdigest()
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    require(contract["review_parent"]["contract_sha256"] != "pending",
            "review checksum has not been frozen")
    validate(contract, review_sha256)
    rejected = test_mutations(contract, review_sha256)
    print("contract_schema=gemini-da921x-same-value-write-implementation-v1")
    print("patches_planned=3")
    print("action_transfers=12")
    print("write_attempts=1")
    print("hardware_action=none")
    print("boot_candidate=false")
    print("cpu8_cpu9_admission=closed")
    print(f"unsafe_mutations_rejected={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
