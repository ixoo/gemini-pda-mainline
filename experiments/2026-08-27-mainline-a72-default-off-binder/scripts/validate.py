#!/usr/bin/env python3
"""Validate the frozen hardware-free CPU8 binder audit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_text(path: Path, needles: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    for needle in needles:
        if needle not in text:
            raise SystemExit(f"missing {needle!r} in {path.name}")


def main() -> None:
    contract = json.loads((ROOT / "contract.json").read_text(encoding="utf-8"))
    evidence = contract["evidence"]
    source = ROOT / evidence["source_interface_map"]["path"]

    assert contract["schema"] == 1
    assert contract["canonical_series_entries"] == 384
    assert contract["current_closed_boundaries"]["binder_arm_callers"] == 0
    assert contract["current_closed_boundaries"]["cpu8_request_callers"] == 0
    assert contract["current_closed_boundaries"]["physical_owner_callers"] == 0
    assert len(contract["interface_gaps"]) == 6
    assert len(contract["selected_repairs"]) == 6
    assert contract["binder_contract"]["cpu"] == 8
    assert contract["binder_contract"]["cpu9_offline"] is True
    assert contract["binder_contract"]["regular_success_checkpoints"] == 18
    assert contract["binder_contract"]["terminal_commits"] == 1
    assert contract["binder_contract"]["recovery_timeout_ms"] == 15000
    assert len(contract["binder_contract"]["supplier_references"]) == 3
    assert contract["binder_contract"]["cpu_off_requests"] == 0
    assert contract["binder_contract"]["retries"] == 0
    assert contract["hardware_free_proof"] == {
        "physical_backends": 0,
        "mmio": False,
        "retained_ram": False,
        "smc": False,
        "production_cpu_requests": 0,
        "enabled_binder_dt_nodes": 0,
        "network": False,
        "device_action": False,
        "boot_candidate": False,
    }
    assert contract["kernel_build"] is False
    assert contract["native_vm_build"] is False
    assert contract["device_action"] is False
    assert sha256(source) == evidence["source_interface_map"]["sha256"]
    assert sha256(ROOT / "DESIGN.md") == evidence["design_sha256"]

    require_text(
        ROOT / "DESIGN.md",
        (
            "checkpoint callback is `void`",
            "one armed CPU8 token",
            "exactly three bound",
            "suppliers resolved from explicit phandles",
            "terminalize the binder before the existing P32",
            "no `cpu_up()`",
            "zero CPU_OFF/retry",
        ),
    )
    require_text(
        source,
        (
            "executor_checkpoint_return=void",
            "membership_available_preflight=minus-EOPNOTSUPP",
            "required_supplier_references=3",
            "production_cpu8_request_callers=0",
            "boot_candidate=false",
        ),
    )
    require_text(
        ROOT / "README.md",
        (
            "Direct glue is rejected.",
            "Buildbox only",
            "no late CPU caller",
            "no boot candidate is selected",
        ),
    )

    print("validation=a72-default-off-binder-audit")
    print("interface_gaps=6")
    print("selected_repairs=6")
    print("supplier_references=3")
    print("regular_checkpoints=18")
    print("terminal_commits=1")
    print("cpu_requests=0")
    print("device_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
