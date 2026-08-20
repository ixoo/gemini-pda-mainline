#!/usr/bin/env python3
"""Validate the exact implementation and recorded deployment contract."""

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
            "runtime-attempt-1-pretrigger-mismatch-no-write",
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

    deployment = contract["deployment"]
    require(deployment["repository_commit"] ==
            "b1d251abc08113e1a75079ca53012a53d19d036c" and
            deployment["known_good_os"] == "3.18.41+",
            "deployment source identity changed")
    require(deployment["target_logical_name"] == "boot2" and
            deployment["target"] == "/dev/mmcblk0p30" and
            deployment["active_root"] == "/dev/mmcblk0p29" and
            deployment["boot_id"] == "6585b668-db35-4a10-95ea-8c64a273b2e3" and
            deployment["target_inactive_unmounted"] is True,
            "deployment target identity changed")
    require(deployment["predecessor_sha256"] ==
            "fd6680d6e0ab3fbd61cc4f46b517a4672dd115eed92f2bbc0ae788b6e263c760" and
            deployment["fresh_predecessor_backup"] is False,
            "deployment predecessor boundary changed")
    require(deployment["candidate_sha256"] == candidate["padded_sha256"] and
            deployment["full_partition_readback_sha256"] ==
            candidate["padded_sha256"] and
            deployment["stable_power"] == "present-100-Good-external-online",
            "deployment payload or power evidence changed")
    require(deployment["write_synced_flushed"] is True and
            deployment["independent_full_readback_identical"] is True and
            deployment["clean_shutdown_confirmed"] is True and
            deployment["automatic_reboot"] is False,
            "deployment completion boundary changed")

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

    runtime = contract["runtime_result"]
    require(runtime["selected_boots"] == 1 and
            runtime["initial_collector_expired_before_selection"] is True and
            runtime["rearm_on_same_selected_boot"] is True,
            "runtime boot accounting changed")
    require(runtime["kernel_release"] ==
            "7.1.3-gemini-da921x-same-write" and
            runtime["architecture"] == "aarch64" and
            runtime["mainline_boot_id_sha256"] ==
            "5e7b53a8ada2d54590237c50b7741c6b4191cfb3fe7dd490b828ae70393b5853",
            "runtime identity changed")
    require(runtime["usb_interface"] == "en7" and
            runtime["usb_mac"] == "42:00:15:19:82:00" and
            runtime["cpu_online"] == "0-7" and runtime["cpu_offline"] == "8-9",
            "runtime serviceability or CPU boundary changed")
    require(runtime["pretrigger_probe_attempts"] == 6 and
            runtime["da921x_i2c_client_counts"] == [0, 0, 0, 0, 0, 0] and
            runtime["pretrigger_complete"] is False,
            "pretrigger mismatch changed")
    require(runtime["trigger_token_attempts"] == 0 and
            runtime["trigger_retries"] == 0 and
            runtime["physical_da921x_write_attempts"] == 0 and
            runtime["classification"] == "pretrigger-mismatch-no-da921x-client",
            "failed-closed classification changed")
    require(runtime["native_reboot_commands"] == 1 and
            runtime["returned_kernel_release"] == "3.18.41+" and
            runtime["returned_boot_id_sha256"] ==
            "303ba3df5445d69843cdc80d295d487ef2a7a25eaf2fcbc04ca64899c72b2585" and
            runtime["changed_gemian_return"] is True,
            "native return evidence changed")
    require(runtime["boot2_sha256_after_return"] == candidate["padded_sha256"] and
            runtime["pstore_files_after_return"] == 0 and
            runtime["reset_reason_class"] == "nondiscriminating-watchdog-block" and
            runtime["repeat_exact_candidate"] is False,
            "post-return or no-repeat boundary changed")

    decision = contract["decision"]
    require(decision["implementation_in_progress"] is False and
            decision["hardware_free_implementation_complete"] is True and
            decision["boot_candidate_exists"] is True and
            decision["physical_da921x_write_authorized"] is False and
            decision["device_action"] ==
            "selected-boot-closed-without-token-native-return",
            "post-runtime decision changed")
    require(decision["cpu8_cpu9_admission"] == "closed", "CPU admission changed")
    require(decision["next_success_gate"] ==
            "offline-localize-missing-da921x-client-before-new-candidate",
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
        (("deployment", "target"), "/dev/mmcblk0p29"),
        (("deployment", "boot_id"), "00000000-0000-0000-0000-000000000000"),
        (("deployment", "fresh_predecessor_backup"), True),
        (("deployment", "candidate_sha256"), "0" * 64),
        (("deployment", "write_synced_flushed"), False),
        (("deployment", "independent_full_readback_identical"), False),
        (("deployment", "clean_shutdown_confirmed"), False),
        (("deployment", "automatic_reboot"), True),
        (("runtime_tooling", "trigger_attempts"), 2),
        (("runtime_tooling", "trigger_retries"), 1),
        (("runtime_tooling", "second_writes"), 1),
        (("runtime_result", "selected_boots"), 2),
        (("runtime_result", "kernel_release"), "3.18.41+"),
        (("runtime_result", "cpu_offline"), "9"),
        (("runtime_result", "pretrigger_probe_attempts"), 5),
        (("runtime_result", "da921x_i2c_client_counts", 0), 1),
        (("runtime_result", "pretrigger_complete"), True),
        (("runtime_result", "trigger_token_attempts"), 1),
        (("runtime_result", "physical_da921x_write_attempts"), 1),
        (("runtime_result", "changed_gemian_return"), False),
        (("runtime_result", "boot2_sha256_after_return"), "0" * 64),
        (("runtime_result", "repeat_exact_candidate"), True),
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
    print("hardware_action=boot2-deployment-and-one-selected-boot")
    print("boot_candidate=true")
    print("physical_da921x_write_authorized=false")
    print("runtime_classification=pretrigger-mismatch-no-da921x-client")
    print("trigger_token_attempts=0")
    print("physical_da921x_write_attempts=0")
    print("changed_gemian_return=true")
    print("cpu8_cpu9_admission=closed")
    print(f"unsafe_mutations_rejected={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
