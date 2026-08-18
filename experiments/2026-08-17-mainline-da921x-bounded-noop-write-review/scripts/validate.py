#!/usr/bin/env python3
"""Validate the design-only DA921x bounded no-op contract."""

from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract.json"


class ContractError(RuntimeError):
    """Raised when the design escapes its fail-closed boundary."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate(contract: dict) -> None:
    transaction = contract["proposed_transaction"]
    preflight = contract["required_preflight"]
    post = contract["postconditions"]
    failure = contract["failure_policy"]
    decision = contract["decision"]

    require(contract["status"] == "blocked-design-only", "status must block implementation")
    require(transaction["classification"] == "same-value-no-op", "transaction must be a no-op")
    require(transaction["i2c_address"] == "0x68", "wrong I2C address")
    require(transaction["register"] == "0xda", "wrong target register")
    require(transaction["register_name"] == "VBUCKB_B", "wrong target name")
    require(transaction["pre_value"] == transaction["write_value"] == transaction["post_value"] == "0x46",
            "target value must remain exactly 0x46")
    require(transaction["messages"] == 1, "exactly one write message is allowed")
    require(transaction["message_bytes"] == ["0xda", "0x46"], "unexpected message payload")
    require(transaction["expected_transfer_return"] == 1, "write must complete exactly one message")
    require(transaction["retries"] == 0, "retries are forbidden")
    require(transaction["page_con_accesses"] == 0, "PAGE_CON must remain untouched")
    require(transaction["consumer_requests"] == 0, "consumer request is forbidden")
    require(transaction["cpu_requests"] == 0, "CPU request is forbidden")
    require(transaction["second_or_rollback_write"] is False, "a second write is forbidden")

    require(preflight["buckb_cont_0x5e"] == "0x00", "Buck B control prestate must be exact")
    require(preflight["buckb_enabled"] is False, "Buck B must be disabled")
    require(preflight["selected_voltage_register"] == "VBUCKB_A", "VBUCKB_B must be unselected")
    require(preflight["gpi_enable_control"] is False, "GPI enable control must be absent")
    require(preflight["gpi_voltage_select"] is False, "GPI voltage selection must be absent")
    require(preflight["vbuckb_a_0xd9"] == preflight["vbuckb_b_0xda"] == "0x46",
            "both Buck B selectors must have the observed 0x46 prestate")
    require(preflight["control_a_0x56_v_lock_mask"] == "0x80", "wrong V_LOCK mask")
    require(preflight["control_a_0x56_v_lock_expected"] == "0x00", "V_LOCK must be clear")
    require(preflight["provider_consumers"] == 0, "provider consumers must remain absent")
    require(preflight["root_adapter_lock"] is True, "root adapter lock is required")
    require(preflight["linux_generation_cookie_lease"] is True, "Linux lease is required")
    require(preflight["firmware_writer_exclusion"] == "required-but-unproven",
            "firmware ownership must remain explicitly unproven")

    require(post["immediate_vbuckb_b_0xda"] == post["delayed_vbuckb_b_0xda"] == "0x46",
            "both target readbacks must equal the prestate")
    require(post["buckb_cont_0x5e"] == "0x00", "Buck B must remain disabled")
    require(post["vbuckb_a_0xd9"] == "0x46", "selected voltage register must remain unchanged")
    require(post["page_con_accesses"] == 0, "postcondition must not touch PAGE_CON")
    require(post["cpu_online"] == "0-7" and post["cpu_offline"] == "8-9",
            "CPU8/9 must remain closed")

    require(failure["retry"] is False, "failure retry is forbidden")
    require(failure["attempt_inverse_after_uncertain_transfer"] is False,
            "uncertain completion must not trigger another write")
    require(failure["enable_buckb"] is False and failure["select_vbuckb_b"] is False,
            "rail activation is forbidden")
    require(failure["request_cpu8_or_cpu9"] is False, "A72 request is forbidden")

    blockers = contract["blockers"]
    require([item["id"] for item in blockers] == [
        "B1-firmware-owner",
        "B2-write-transport",
        "B3-transfer-attribution",
        "B4-live-preflight",
    ], "blocker ledger changed")
    require(all(item["status"] == "blocking" for item in blockers), "every blocker must remain active")
    require(decision["implementation_eligible"] is False, "implementation must remain ineligible")
    require(decision["kernel_build_authorized"] is False, "kernel build must remain unauthorized")
    require(decision["device_write_authorized"] is False, "device write must remain unauthorized")
    require(decision["cpu8_cpu9_admission"] == "closed", "CPU8/9 admission must remain closed")
    require(decision["ordered_follow_up_owner"] ==
            "docs/ROADMAP.md#6-prove-one-bounded-writable-operation",
            "Roadmap must remain the sole owner of the ordered follow-up")


def test_fail_closed(contract: dict) -> int:
    mutations = [
        ("changed-value", lambda c: c["proposed_transaction"].update(write_value="0x45")),
        ("enable-buck", lambda c: c["failure_policy"].update(enable_buckb=True)),
        ("cpu-request", lambda c: c["proposed_transaction"].update(cpu_requests=1)),
        ("retry", lambda c: c["proposed_transaction"].update(retries=1)),
        ("drop-blocker", lambda c: c["blockers"].pop()),
        ("authorize-build", lambda c: c["decision"].update(kernel_build_authorized=True)),
    ]
    rejected = 0
    for name, mutate in mutations:
        candidate = copy.deepcopy(contract)
        mutate(candidate)
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
    print("contract_schema=gemini-da921x-bounded-noop-write-review-v1")
    print("proposed_transaction=0x68:0xda:0x46->0x46")
    print("hardware_action=none")
    print("implementation_eligible=no")
    print("blockers=4")
    print(f"unsafe_mutations_rejected={rejected}")
    print("decision=BLOCK_WRITE;PREPARE_READ_ONLY_ATTRIBUTION")
    print("result=pass")


if __name__ == "__main__":
    main()
