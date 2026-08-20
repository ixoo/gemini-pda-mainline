#!/usr/bin/env python3
"""Validate the fresh Gate-6 same-value-write preflight review."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any


EXPERIMENT = Path(__file__).resolve().parents[1]
CONTRACT = EXPERIMENT / "contract.json"


class ContractError(RuntimeError):
    """Raised when the review escapes its frozen fail-closed boundary."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_receipts(contract: dict[str, Any]) -> None:
    receipts = contract["closure_receipts"]
    require(
        [receipt["blockers"] for receipt in receipts]
        == [
            ["B1-firmware-owner"],
            ["B2-write-transport"],
            ["B3-transfer-attribution", "B4-live-preflight"],
        ],
        "closure receipt order or blocker coverage changed",
    )
    require(all(receipt["status"] == "closed" for receipt in receipts),
            "every original blocker must have closed evidence")

    for receipt in receipts:
        path = (EXPERIMENT / receipt["path"]).resolve()
        require(path.is_file(), f"missing closure receipt: {receipt['path']}")
        require(sha256(path) == receipt["sha256"],
                f"closure receipt checksum changed: {receipt['path']}")
        text = path.read_text(encoding="utf-8")
        for marker in receipt["required_markers"]:
            require(marker in text,
                    f"closure marker missing from {receipt['path']}: {marker}")


def validate_pretrigger(contract: dict[str, Any]) -> None:
    ledger = contract["pretrigger_ledger"]
    expected = [
        "69:05", "69:06", "69:47", "68:d3", "68:5e", "68:d9", "68:da",
        "69:05", "69:06", "69:47", "68:d3", "68:5e", "68:d9", "68:da",
        "68:d7", "68:d9", "68:d7", "68:5d", "68:d9", "68:5e",
    ]
    require(ledger["schema"] == "v1", "pretrigger evidence must retain v1 identity")
    require(ledger["capacity"] == 32, "ledger capacity must remain 32")
    require(ledger["required_count"] == 20, "pretrigger ledger must contain 20 entries")
    require(ledger["required_overflow"] == 0, "pretrigger ledger must not overflow")
    require(ledger["required_sequence"] == expected, "pretrigger sequence changed")
    require(ledger["required_shape"] ==
            "two-message-one-byte-pointer-plus-one-byte-read",
            "pretrigger shape changed")
    require(ledger["required_result"] == 2 and ledger["required_complete"] is True,
            "every pretrigger transfer must complete exactly")
    require(ledger["host_capture_before_token"] is True,
            "host must retain pretrigger evidence before the token")
    require(ledger["verify_again_under_root_lock_before_first_action_transfer"] is True,
            "kernel must recheck the ledger under the root lock")


def validate_sequence(contract: dict[str, Any]) -> None:
    sequence = contract["action_sequence"]
    expected_registers = [
        "0x56", "0x51", "0x5e", "0xd9", "0xda", "0xda",
        "0xda", "0xda", "0x56", "0x51", "0x5e", "0xd9",
    ]
    require(len(sequence) == 12, "the action window must contain exactly 12 transfers")
    require([item["ordinal"] for item in sequence] == list(range(1, 13)),
            "action ordinals must be contiguous")
    require([item["register"] for item in sequence] == expected_registers,
            "action register sequence changed")
    require([item["ledger_count_after"] for item in sequence] == list(range(21, 33)),
            "action ledger accounting changed")
    require([item["kind"] for item in sequence].count("write") == 1,
            "exactly one action transfer may be a write")
    require(sequence[5] == {
        "ordinal": 6,
        "kind": "write",
        "register": "0xda",
        "value": "0x46",
        "expected_transfer_return": 1,
        "ledger_count_after": 26,
    }, "write action changed")
    for index in [0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11]:
        require(sequence[index]["kind"] == "read", "non-write action must be a read")
    require([sequence[index]["expected"] for index in range(5)] ==
            ["0x7b", "0xc1", "0x00", "0x46", "0x46"],
            "exact preflight values changed")
    require(sequence[6]["phase"] == "immediate-readback" and
            sequence[6]["expected"] == "0x46",
            "immediate readback changed")
    require(sequence[7]["phase"] == "delayed-readback" and
            sequence[7]["expected"] == "0x46" and
            sequence[7]["delay_before_us"] == {"minimum": 10000, "maximum": 11000},
            "delayed readback or delay changed")
    require([sequence[index]["expected"] for index in range(8, 12)] ==
            ["0x7b", "0xc1", "0x00", "0x46"],
            "poststate values changed")


def validate(contract: dict[str, Any]) -> None:
    require(contract["schema"] ==
            "gemini-da921x-same-value-write-preflight-review-v1",
            "wrong contract schema")
    require(contract["status"] ==
            "completed-hardware-free-implementation-eligible",
            "review status changed")
    require(contract["roadmap_gate"] == "Gate-6-pre-write-review",
            "wrong roadmap gate")
    require(contract["hardware_scope"] == "none", "review must remain hardware-free")
    parent = contract["review_parent"]
    require(parent["repository_commit"] ==
            "60b8de7e0d3dbf15e36071a7a9ae9aade5e1d931",
            "review parent changed")
    require(parent["cpu_online"] == "0-7" and parent["cpu_offline"] == "8-9" and
            parent["maxcpus"] == 8, "review parent CPU closure changed")

    validate_receipts(contract)
    validate_pretrigger(contract)
    validate_sequence(contract)

    one_shot = contract["one_shot"]
    require(one_shot["token"] == "run-same-value-write-20260819-a",
            "one-shot token changed")
    require(one_shot["accepted_requests"] == 1,
            "exactly one accepted request is required")
    require(one_shot["state_lock"] == "da9213-legacy-device-mutex",
            "driver state must be mutex-serialized")
    require(one_shot["initial_state"] == "idle" and
            one_shot["success_state"] == "passed" and
            one_shot["prewrite_failure_state"] == "failed-no-write" and
            one_shot["postwrite_failure_state"] == "faulted-no-further-i2c",
            "one-shot state machine changed")
    require(one_shot["wrong_token_transfers"] == 0 and
            one_shot["repeated_token_transfers"] == 0 and
            one_shot["precondition_failure_transfers"] == 0,
            "refused requests must not transfer")

    pre = contract["preconditions"]
    require(pre["i2c_address"] == "0x68", "wrong device address")
    require(pre["control_a_0x56"] == "0x7b" and
            pre["control_a_v_lock_mask"] == "0x80" and
            pre["control_a_v_lock_expected"] == "0x00",
            "CONTROL_A/V_LOCK precondition changed")
    require(pre["status_b_0x51"] == "0xc1", "STATUS_B precondition changed")
    require(pre["buckb_cont_0x5e"] == "0x00" and pre["buckb_enabled"] is False,
            "Buck B must remain disabled")
    require(pre["selected_voltage_register"] == "VBUCKB_A",
            "VBUCKB_B must remain unselected")
    require(pre["vbuckb_a_0xd9"] == pre["vbuckb_b_0xda"] == "0x46",
            "selector prestate changed")
    require(pre["provider_consumers"] == 0, "provider consumers are forbidden")
    require(pre["cpu_online"] == "0-7" and pre["cpu_offline"] == "8-9" and
            pre["maxcpus"] == 8, "CPU8/9 must remain closed")
    require(pre["power_stable"] is True and pre["handoff_state"] == "ready" and
            pre["scp_reset_control"] == "0x00000000" and
            pre["transaction_reset_failures"] == 0,
            "ownership or power precondition changed")

    window = contract["bus_window"]
    require(window["root_adapter_lock_calls"] == 1 and
            window["root_adapter_unlock_calls"] == 1,
            "the full action window needs one root lock/unlock")
    require(window["lock_scope"] ==
            "pretrigger-ledger-verification-through-final-poststate-or-first-failure",
            "root-lock scope changed")
    require(window["adapter_retries_saved"] is True and
            window["adapter_retries_during"] == 0 and
            window["adapter_retries_restored_on_every_exit"] is True,
            "retry suppression/restoration changed")
    require(window["transfer_api_under_lock"] == "__i2c_transfer" and
            window["forbidden_transfer_api_under_lock"] == "i2c_transfer",
            "locked transfer API contract changed")
    require(window["private_controller_header_import"] is False,
            "regulator code must not import a controller-private header")
    require(window["controller_ledger_verifier"] ==
            "read-only-public-experiment-api-no-transfer",
            "pre-write controller ledger verifier changed")
    require(window["max_action_transfers"] == 12 and
            window["automatic_retry"] is False,
            "action bound or retry policy changed")

    write = contract["write_contract"]
    require(write["classification"] == "same-value-no-op", "write must be same-value")
    require(write["i2c_address"] == "0x68" and write["register"] == "0xda" and
            write["register_name"] == "VBUCKB_B", "write target changed")
    require(write["pre_value"] == write["write_value"] ==
            write["post_value"] == "0x46", "write must retain 0x46")
    require(write["messages"] == 1 and write["message_bytes"] == ["0xda", "0x46"] and
            write["expected_transfer_return"] == 1,
            "write message changed")
    require(write["write_attempts"] == 1 and
            write["second_or_inverse_write"] is False,
            "only one write attempt is allowed")
    require(write["page_con_accesses"] == 0 and write["consumer_requests"] == 0 and
            write["cpu_requests"] == 0, "forbidden side effect admitted")

    payload = contract["payload_attribution"]
    require(payload["required_ledger_schema"] == "v2" and
            payload["recorded_payload_bytes_for_write"] == 2,
            "both write bytes must be attributable")
    require(payload["required_write_entry"] == {
        "address": "0x68",
        "messages": 1,
        "flags": "0x0000",
        "length": 2,
        "payload": ["0xda", "0x46"],
        "result": 1,
        "complete": True,
    }, "required write ledger entry changed")
    require(payload["write_shaped_entries"] == 1 and
            payload["register_data_write_entries"] == 1 and
            payload["other_transfers"] == 0 and
            payload["other_address_transfers"] == 0 and payload["overflow"] == 0,
            "write attribution bounds changed")

    post = contract["success_postconditions"]
    require(post["ledger_count"] == 32 and post["ledger_spare_entries"] == 0,
            "success must consume exactly the remaining 12 ledger entries")
    require(post["transaction_entry_checks"] == 32 and
            post["transaction_exit_checks"] == 32 and
            post["transaction_reset_failures"] == 0,
            "transaction-window success accounting changed")
    require(post["control_a_0x56"] == "0x7b" and post["status_b_0x51"] == "0xc1" and
            post["buckb_cont_0x5e"] == "0x00" and post["vbuckb_a_0xd9"] == "0x46" and
            post["immediate_vbuckb_b_0xda"] == "0x46" and
            post["delayed_vbuckb_b_0xda"] == "0x46",
            "success register poststate changed")
    require(post["cpu_online"] == "0-7" and post["cpu_offline"] == "8-9" and
            post["sysfs_mount_after_collection"] == "ro",
            "success serviceability closure changed")

    failure = contract["failure_policy"]
    require(failure["stop_after_first_transfer_error_or_value_mismatch"] is True,
            "first failure must stop the sequence")
    require(failure["automatic_retry"] is False and
            failure["second_or_inverse_write"] is False and
            failure["further_i2c_after_write_attempt_failure"] == 0,
            "failure path must not retry or write again")
    require(failure["enable_buckb"] is False and
            failure["select_vbuckb_b"] is False and
            failure["request_cpu8_or_cpu9"] is False,
            "failure path must not activate the rail or A72 CPUs")
    require(failure["preserve_partial_ledger"] is True and
            failure["preserve_kernel_result"] is True,
            "partial failure evidence must survive")
    stages = failure["failure_stages"]
    require([stage["ordinal"] for stage in stages] == list(range(1, 13)),
            "failure-stage ordinals changed")
    require([stage["ledger_count"] for stage in stages] == list(range(21, 33)),
            "failure-stage ledger counts changed")
    require([stage["write_attempts"] for stage in stages] == [0] * 5 + [1] * 7,
            "failure-stage write accounting changed")
    require([stage["state"] for stage in stages] ==
            ["failed-no-write"] * 5 + ["faulted-no-further-i2c"] * 7,
            "failure-stage terminal states changed")

    host = contract["host_observation"]
    require(all(host[key] is True for key in [
        "collector_must_be_validated_before_candidate",
        "pretrigger_capture_must_precede_token",
        "copy_immutable_result_before_recovery",
        "native_reboot_only_after_classification",
        "changed_boot_id_gemian_required",
        "boot2_checksum_reconfirmation_required",
    ]), "host observation or recovery gate changed")
    require(host["automatic_second_trigger"] is False and
            host["automatic_second_write"] is False,
            "host must never repeat the write")

    gates = contract["implementation_gates"]
    require(gates["source_validator"] == "required" and
            gates["hardware_free_sequence_kunit"] == "required" and
            gates["all_failure_stage_kunit"] == "required" and
            gates["payload_attribution_mutation_tests"] == "required" and
            gates["canonical_series_audit"] == "required" and
            gates["all_manifest_profiles_audit"] == "required",
            "offline implementation gates changed")
    require(gates["build_backend"] == "buildbox" and
            gates["exact_clean_pushed_commit"] is True,
            "build must use an exact clean pushed Buildbox commit")
    require(gates["candidate_validation"] == "required" and
            gates["collector_validation"] == "required" and
            gates["predeployment_hypothesis"] == "required" and
            gates["deployment_evidence_pushed_before_boot"] is True,
            "candidate/deployment gates changed")

    decision = contract["decision"]
    require(decision["original_blockers_closed"] == [
        "B1-firmware-owner", "B2-write-transport",
        "B3-transfer-attribution", "B4-live-preflight",
    ], "original blocker ledger changed")
    require(decision["implementation_eligible"] is True and
            decision["buildbox_kernel_build_eligible"] is True,
            "review must permit only the next offline implementation/build phase")
    require(decision["physical_da921x_write_authorized"] is False and
            decision["boot_candidate_exists"] is False and
            decision["device_action"] == "none",
            "review must not authorize hardware action")
    require(decision["cpu8_cpu9_admission"] == "closed",
            "CPU8/CPU9 admission must remain closed")
    require(decision["next_action"] ==
            "implement-and-hardware-free-validate-exact-contract",
            "next action changed")
    require(decision["ordered_follow_up_owner"] ==
            "docs/ROADMAP.md#6-prove-one-bounded-writable-operation",
            "Roadmap must own the ordered follow-up")


def set_path(candidate: dict[str, Any], path: tuple[Any, ...], value: Any) -> None:
    node: Any = candidate
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value


def test_fail_closed(contract: dict[str, Any]) -> int:
    mutations = [
        ("hardware-scope", ("hardware_scope",), "device"),
        ("parent-cpu", ("review_parent", "cpu_offline"), "9"),
        ("receipt-open", ("closure_receipts", 0, "status"), "blocking"),
        ("receipt-hash", ("closure_receipts", 1, "sha256"), "0" * 64),
        ("pretrigger-count", ("pretrigger_ledger", "required_count"), 19),
        ("pretrigger-overflow", ("pretrigger_ledger", "required_overflow"), 1),
        ("skip-lock-recheck", ("pretrigger_ledger", "verify_again_under_root_lock_before_first_action_transfer"), False),
        ("second-request", ("one_shot", "accepted_requests"), 2),
        ("wrong-token-transfer", ("one_shot", "wrong_token_transfers"), 1),
        ("v-lock", ("preconditions", "control_a_v_lock_expected"), "0x80"),
        ("enable-buck", ("preconditions", "buckb_enabled"), True),
        ("consumer", ("preconditions", "provider_consumers"), 1),
        ("cpu-request-precondition", ("preconditions", "cpu_offline"), "9"),
        ("two-locks", ("bus_window", "root_adapter_lock_calls"), 2),
        ("retries", ("bus_window", "adapter_retries_during"), 1),
        ("nested-lock-api", ("bus_window", "transfer_api_under_lock"), "i2c_transfer"),
        ("private-header", ("bus_window", "private_controller_header_import"), True),
        ("extra-transfer", ("bus_window", "max_action_transfers"), 13),
        ("changed-value", ("write_contract", "write_value"), "0x45"),
        ("inverse-write", ("write_contract", "second_or_inverse_write"), True),
        ("page-con", ("write_contract", "page_con_accesses"), 1),
        ("cpu-request", ("write_contract", "cpu_requests"), 1),
        ("one-byte-ledger", ("payload_attribution", "recorded_payload_bytes_for_write"), 1),
        ("wrong-payload", ("payload_attribution", "required_write_entry", "payload", 1), "0x45"),
        ("second-write-entry", ("payload_attribution", "write_shaped_entries"), 2),
        ("ledger-spare", ("success_postconditions", "ledger_spare_entries"), 1),
        ("reset-failure", ("success_postconditions", "transaction_reset_failures"), 1),
        ("status-change", ("success_postconditions", "status_b_0x51"), "0xc0"),
        ("failure-retry", ("failure_policy", "automatic_retry"), True),
        ("failure-inverse", ("failure_policy", "second_or_inverse_write"), True),
        ("post-failure-read", ("failure_policy", "further_i2c_after_write_attempt_failure"), 1),
        ("bad-stage-count", ("failure_policy", "failure_stages", 5, "ledger_count"), 27),
        ("no-immutable-copy", ("host_observation", "copy_immutable_result_before_recovery"), False),
        ("native-build", ("implementation_gates", "build_backend"), "vm"),
        ("authorize-write", ("decision", "physical_da921x_write_authorized"), True),
        ("admit-cpu8", ("decision", "cpu8_cpu9_admission"), "open"),
    ]
    rejected = 0
    for name, path, value in mutations:
        candidate = copy.deepcopy(contract)
        set_path(candidate, path, value)
        try:
            validate(candidate)
        except ContractError:
            rejected += 1
        else:
            raise ContractError(f"unsafe mutation accepted: {name}")
    return rejected


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    validate(contract)
    rejected = test_fail_closed(contract)
    print("contract_schema=gemini-da921x-same-value-write-preflight-review-v1")
    print("review_parent=60b8de7e0d3dbf15e36071a7a9ae9aade5e1d931")
    print("closure_receipts=3")
    print("original_blockers_closed=4")
    print("pretrigger_ledger=20/32")
    print("action_transfers=12")
    print("success_ledger=32/32")
    print("write=0x68:0xda:0x46->0x46")
    print("write_attempts=1")
    print("payload_attribution=v2:da:46")
    print("hardware_action=none")
    print("implementation_eligible=yes")
    print("build_backend=buildbox")
    print("physical_da921x_write_authorized=no")
    print("boot_candidate=false")
    print("cpu8_cpu9_admission=closed")
    print(f"unsafe_mutations_rejected={rejected}")
    print("decision=IMPLEMENT_AND_HARDWARE_FREE_VALIDATE")
    print("result=pass")


if __name__ == "__main__":
    main()
