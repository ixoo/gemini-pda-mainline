#!/usr/bin/env python3
"""Validate the frozen hardware-free Gate-6 B2 design."""

from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contract.json"
README = ROOT / "README.md"
DESIGN = ROOT / "DESIGN.md"


class ContractError(RuntimeError):
    """Raised when the design escapes its hardware-free boundary."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def validate(contract: dict, readme: str, design: str) -> None:
    parent = contract["parent"]
    fixture = contract["fixture"]
    plan = contract["expected_plan"]
    completion = contract["completion_results"]
    retry = contract["retry_contract"]
    lease = contract["lease_result_precedence"]
    prohibited = contract["prohibited"]
    exit_criteria = contract["exit_criteria"]

    require(contract["schema"] == "gemini-i2c6-write-transport-kunit-v1",
            "unexpected schema")
    require(contract["status"] == "completed-hardware-free",
            "completed hardware-free status changed")
    require(contract["roadmap_gate"] == "Gate-6-B2", "wrong roadmap gate")
    require(contract["hardware_scope"] == "none", "hardware scope escaped")
    require(parent["gate6_B1"] == parent["gate6_B3"] ==
            parent["gate6_B4"] == "closed", "parent blocker state changed")

    require(fixture == {
        "adapter": "in-memory-fake",
        "address": "0x2a",
        "messages": 1,
        "flags": 0,
        "length": 2,
        "payload": ["0xa5", "0x5a"],
        "physical_adapter_registrations": 0,
        "start_writes": 0,
        "hardware_transfers": 0,
    }, "fixture must remain exact and hardware-free")
    require(plan == {
        "operation": "I2C_MASTER_WR",
        "slave_addr": "0x54",
        "use_dma": False,
        "control_dma_en": False,
        "control_dir_change": False,
        "transfer_len": 2,
        "transac_len": 1,
        "fifo_writes": ["0xa5", "0x5a"],
    }, "programmed short-write plan changed")

    require(completion["exact_completion"] == 0,
            "exact completion must be controller success")
    require(completion["successful_adapter_result"] == 1,
            "one message must produce adapter result one")
    require(completion["arbitration_loss"] == "-EAGAIN",
            "arbitration result changed")
    require(completion["timeout"] == "-ETIMEDOUT", "timeout result changed")
    require(completion["ack_or_hs_nack"] == "-ENXIO", "NACK result changed")
    require(completion["unexpected_irq"] == "-EIO",
            "unexpected IRQ result changed")
    require(completion["mixed_completion_and_error"] == "error",
            "mixed completion/error must fail")

    require(retry == {
        "retries_before": 1,
        "retries_during": 0,
        "retries_after": 1,
        "root_lock_calls": 1,
        "root_unlock_calls": 1,
        "root_lock_held_during_transfer": True,
        "max_fake_transfer_calls": 1,
        "restore_on_every_exit": True,
    }, "no-retry contract changed")
    require(lease == {
        "positive_transport_negative_lease": "lease",
        "negative_transport_zero_lease": "transport",
        "negative_transport_negative_lease": "transport",
        "positive_transport_zero_lease": "transport",
        "ledger_finishes": 1,
    }, "lease-result precedence changed")

    require(len(contract["required_kunit_cases"]) == 12,
            "required KUnit case count changed")
    require(len(set(contract["required_kunit_cases"])) == 12,
            "required KUnit cases must be unique")
    require(all(prohibited.values()), "every prohibited effect must remain true")
    require(exit_criteria["production_helpers_exercised"] is True,
            "production helper coupling is required")
    require(exit_criteria["canonical_series_valid"] is True,
            "canonical series gate is required")
    require(exit_criteria["focused_buildbox_package_valid"] is True,
            "Buildbox package gate is required")
    require(exit_criteria["qemu_kunit_failed"] == 0 and
            exit_criteria["qemu_kunit_skipped"] == 0,
            "KUnit failure/skip allowance changed")
    require(exit_criteria["implementation_complete"] is True,
            "completed production-coupled implementation proof is required")
    require(exit_criteria["gate6_B2"] == "closed",
            "B2 closure must remain explicit")
    require(exit_criteria["gate6_write"] == "not-authorized",
            "Gate-6 write must remain unauthorized")
    require(exit_criteria["cpu8_cpu9_admission"] == "closed",
            "CPU8/CPU9 must remain closed")

    for token in (
        "hardware-free",
        "production",
        "retries_during = 0",
        "lease_exit < 0",
        "No Gemini boot",
    ):
        require(token in design, f"design token missing: {token}")
    for token in (
        "Buildbox only",
        "hardware-free",
        "No Gemini device",
        "hardware register was touched",
        "Every DA921x write",
        "CPU8/CPU9 admission remains closed",
    ):
        require(token in readme, f"README token missing: {token}")


def test_fail_closed(contract: dict, readme: str, design: str) -> int:
    mutations = [
        ("physical-adapter", lambda c: c["fixture"].update(
            physical_adapter_registrations=1)),
        ("real-address", lambda c: c["fixture"].update(address="0x68")),
        ("dma", lambda c: c["expected_plan"].update(use_dma=True)),
        ("retry", lambda c: c["retry_contract"].update(retries_during=1)),
        ("two-calls", lambda c: c["retry_contract"].update(
            max_fake_transfer_calls=2)),
        ("wrong-lock-scope", lambda c: c["retry_contract"].update(
            root_lock_held_during_transfer=False)),
        ("two-unlocks", lambda c: c["retry_contract"].update(
            root_unlock_calls=2)),
        ("hide-lease-failure", lambda c: c["lease_result_precedence"].update(
            positive_transport_negative_lease="transport")),
        ("allow-skip", lambda c: c["exit_criteria"].update(
            qemu_kunit_skipped=1)),
        ("authorize-write", lambda c: c["exit_criteria"].update(
            gate6_write="authorized")),
        ("drop-completion", lambda c: c["exit_criteria"].update(
            implementation_complete=False)),
        ("drop-prohibition", lambda c: c["prohibited"].update(
            physical_i2c=False)),
    ]
    rejected = 0
    for name, mutate in mutations:
        candidate = copy.deepcopy(contract)
        mutate(candidate)
        try:
            validate(candidate, readme, design)
        except ContractError:
            rejected += 1
        else:
            raise ContractError(f"unsafe mutation accepted: {name}")
    return rejected


def main() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    readme = README.read_text(encoding="utf-8")
    design = DESIGN.read_text(encoding="utf-8")
    validate(contract, readme, design)
    rejected = test_fail_closed(contract, readme, design)
    print("validation=mainline-i2c6-write-transport-kunit-design")
    print("roadmap_gate=Gate-6-B2")
    print("fixture=one-message-two-byte-in-memory-write")
    print("production_contract=fifo-plan,root-locked-once,result-precedence")
    print("hardware_action=none")
    print("kernel_build=buildbox-pass")
    print("qemu_kunit=pass-12-fail-0-skip-0")
    print("device_boot=none")
    print("gate6_B2=closed")
    print("gate6_write=not-authorized")
    print("cpu8_cpu9_admission=closed")
    print(f"unsafe_mutations_rejected={rejected}")
    print("decision=CLOSE_B2_REFRESH_PREWRITE_REVIEW")
    print("result=pass")


if __name__ == "__main__":
    main()
