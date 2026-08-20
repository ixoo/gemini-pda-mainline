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
    require(contract["status"] ==
            "predeployment-tools-pass-evidence-publication-pending",
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

    package = contract["production_package"]
    require(package["repository_commit"] ==
            "7c012d736f78898be08bfd8430a25c8708a62e1d" and
            package["profile"] == "da921x-same-value-write" and
            package["kernel_release"] == "7.1.3-gemini-da921x-same-write",
            "production package identity changed")
    require(package["config_sha256"] ==
            "61590965540ad27624b64c8906a58f87d36ed15821e769f5ec93871f39695614" and
            package["image_sha256"] ==
            "595056ac4cee9ff0a5b79287dca18bdc24f48374ffa7a3ef2647a0255cf1773c" and
            package["repository_dirty"] is False and
            package["target_architecture"] == "arm64" and
            package["kunit_enabled"] is False, "production package boundary changed")

    candidate = contract["boot_candidate"]
    require(candidate["raw_size"] == 6895616 and candidate["raw_sha256"] ==
            "b84f3ba8d86ea9f1b34234794e71be786853da7d1942ce755b175f6c7289509d",
            "raw candidate identity changed")
    require(candidate["padded_size"] == 16777216 and candidate["padded_sha256"] ==
            "b81813d13acc970c7b9203b89ec034921ef6f7e1017539a0c228754619af7b22",
            "padded candidate identity changed")
    require(candidate["lk_gates"] == 32 and
            candidate["independent_assemblies_identical"] is True and
            candidate["independent_padding_identical"] is True and
            candidate["negative_dtb_mutations_rejected"] == 8 and
            candidate["device_access"] == candidate["hardware_write"] == "none",
            "candidate validation boundary changed")

    tooling = contract["runtime_tooling"]
    require(tooling["pretrigger_capture_before_token"] is True and
            tooling["pretrigger_required_count"] == 20 and
            tooling["trigger_attempts"] == 1 and tooling["trigger_retries"] == 0 and
            tooling["second_writes"] == 0, "runtime one-shot boundary changed")
    require(tooling["terminal_states"] == [
        "passed", "failed-no-write", "faulted-no-further-i2c"
    ] and tooling["native_reboot_requires_terminal_classification"] is True and
            tooling["runtime_classifier_mutations_rejected"] == 13 and
            tooling["collector_validation"] == "passed", "runtime tooling changed")

    decision = contract["decision"]
    require(decision["implementation_in_progress"] is False and
            decision["hardware_free_implementation_complete"] is True and
            decision["boot_candidate_exists"] is True and
            decision["physical_da921x_write_authorized"] is False and
            decision["device_action"] == "none", "premature hardware decision")
    require(decision["cpu8_cpu9_admission"] == "closed", "CPU admission changed")
    require(decision["next_success_gate"] ==
            "publish-predeployment-evidence-then-live-serviceability",
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
        (("production_package", "repository_dirty"), True),
        (("production_package", "kunit_enabled"), True),
        (("boot_candidate", "padded_size"), 16777215),
        (("boot_candidate", "lk_gates"), 31),
        (("runtime_tooling", "trigger_attempts"), 2),
        (("runtime_tooling", "trigger_retries"), 1),
        (("runtime_tooling", "second_writes"), 1),
        (("decision", "boot_candidate_exists"), False),
        (("decision", "physical_da921x_write_authorized"), True),
        (("decision", "cpu8_cpu9_admission"), "open"),
        (("decision", "implementation_in_progress"), True),
        (("decision", "hardware_free_implementation_complete"), False),
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
    print("hardware_free_implementation=pass")
    print("hardware_action=none")
    print("boot_candidate=true")
    print("physical_da921x_write_authorized=false")
    print("cpu8_cpu9_admission=closed")
    print(f"unsafe_mutations_rejected={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
