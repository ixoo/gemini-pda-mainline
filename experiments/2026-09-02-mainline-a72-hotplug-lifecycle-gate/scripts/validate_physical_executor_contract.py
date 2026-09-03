#!/usr/bin/env python3
"""Validate the hardware-free CPU9 physical-executor contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "physical-executor-contract.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(document: dict) -> None:
    require(document.get("schema") == 1, "schema changed")
    require(document.get("experiment") ==
            "2026-09-02-mainline-a72-hotplug-lifecycle-gate",
            "experiment changed")
    require(document.get("phase") ==
            "cpu9-physical-executor-hardware-free-contract",
            "phase changed")
    require(document.get("repository_parent") ==
            "f6230e62490d75ee06c9b6e02c2bb2fd346822f6",
            "repository parent changed")
    require(document.get("canonical_series_entries") == 475,
            "series count changed")
    require(document.get("canonical_series_sha256") ==
            "640f8757299432cf125d34f3049e2aa7b1f1c19b0688e46cbafd1bdb7749bd19",
            "series identity changed")
    require(document.get("manifest_sha256") ==
            "af9331a6d97a73475243dc1f79df6ca70206d3daf69405c20e9145e7c9930b43",
            "manifest identity changed")
    require(document.get("owner_runtime_evidence_sha256") ==
            "3b6177dfb6e6b02cfac1114802c2d924c4ede0d015270517dbaa7b315c10bffa",
            "owner runtime evidence changed")

    watchdog = document.get("watchdog", {})
    require(watchdog == {
        "owner": "established-cpu8-transition",
        "deadline_ms": 15000,
        "entry_identity_required": True,
        "takeover_calls": 0,
        "refresh_calls": 0,
        "cancel_calls": 0,
        "cancellation_api_available": False,
        "terminal_disposition": "durable-result-then-expected-reset",
    }, "watchdog contract changed")

    require(document.get("split_owners") == {
        "preflight_validate_complete": "requesting-controller",
        "disable_and_cpu_off": "target-cpu9",
        "affinity_readback_and_proof": "requesting-controller",
        "retained_callback": "cpu8",
    }, "split ownership changed")

    require(document.get("ordered_stages") == [
        "controller-owner-prepare",
        "controller-watchdog-identity-validate",
        "controller-stable-baseline",
        "generic-owner-validate",
        "target-psci-disable-guard",
        "target-owner-cpu-off-commit",
        "target-durable-commit-checkpoint",
        "target-one-psci-cpu-off",
        "controller-one-active-affinity-level0",
        "controller-stable-post-state",
        "retained-cpu8-bounded-callback",
        "controller-readback-classification",
        "controller-owner-proof",
        "generic-owner-down-complete",
        "controller-distinct-restore",
        "controller-restored-terminal",
        "expected-watchdog-reset",
    ], "stage order changed")

    require(document.get("budgets") == {
        "cpu9_cpu_off": 1,
        "cpu9_affinity_info_level0": 1,
        "cpu8_responsiveness_callback": 1,
        "post_affinity_snapshot": 1,
        "cpu9_restore_cpu_on": 1,
        "cpu_off_retry": 0,
        "affinity_retry": 0,
        "cpu_on_retry": 0,
        "cpu8_last_off": 0,
    }, "budgets changed")

    readback = document.get("readback", {})
    require(readback.get("cpu8_status_bit") == 7,
            "CPU8 status bit changed")
    require(readback.get("cpu9_status_bit") == 6,
            "CPU9 status bit changed")
    require(readback.get("cpu8_required_in_both_status_words") is True,
            "CPU8 two-word requirement removed")
    require(readback.get("cpu9_clear_in_both_status_words") is True,
            "CPU9 two-word requirement removed")
    require(set(readback.get("unchanged_exact", [])) == {
        "spm_mp2_cpusys_pwr_con", "spm_mp2_cpu0_pwr_con",
        "provider-five-byte-tuple", "protected-clock-values",
        "bigidvfs-values",
    }, "exact invariant set changed")
    require(readback.get("unchanged_masked") == {
        "spm_cpu_ext_buck_iso": "0x00000002",
        "mp2_sync_dcm": "0x0000007f",
        "cci_mp2_port_control": "0x00000003",
    }, "masked invariants changed")
    require(readback.get("cci_change_pending_clear") is True,
            "CCI pending gate removed")
    require(readback.get("cpu9_core_control") ==
            "capture-raw-not-acceptance-predicate",
            "CPU9 core control promoted without a mask")
    require(readback.get("general_spm_status") == "correlation-only",
            "general SPM status promoted")

    require(document.get("post_commit_failure") ==
            "terminal-fault-no-retry-no-inverse-reset-only",
            "post-commit policy changed")
    require(document.get("secure_affinity_intrinsically_bounded") is False,
            "secure affinity falsely bounded")
    require(document.get("park_only_success") is False,
            "park-only result accepted")
    for gate in ("production_callbacks_bound", "cpu_can_disable",
                 "boot_candidate", "device_action", "native_vm_build"):
        require(document.get(gate) is False, f"{gate} enabled")


def validate_source(document: dict, source_tree: pathlib.Path) -> None:
    for relative, expected in document.get("prepared_source", {}).items():
        path = source_tree / relative
        require(path.is_file(), f"missing prepared source: {relative}")
        require(sha256(path) == expected,
                f"prepared source identity changed: {relative}")

    watchdog = (source_tree / "include/linux/mtk_wdt.h").read_text()
    require("mtk_wdt_recovery_takeover" in watchdog,
            "watchdog takeover API missing")
    require("recovery_cancel" not in watchdog and
            "recovery_release" not in watchdog and
            "recovery_refresh" not in watchdog,
            "watchdog mutation API unexpectedly present")

    psci = (source_tree / "arch/arm64/kernel/mt6797_psci.c").read_text()
    require("mt6797_psci_cpu_can_disable(unsigned int cpu)" in psci and
            "return false;" in psci,
            "A72 disable veto changed")
    require(".cpu_down_preflight" not in psci and
            ".cpu_down_validate" not in psci and
            ".cpu_down_complete" not in psci and
            ".cpu_down_failed" not in psci,
            "production down callback unexpectedly bound")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=pathlib.Path, default=CONTRACT)
    parser.add_argument("--source-tree", type=pathlib.Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.contract.read_text())
        validate(document)
        if args.source_tree:
            validate_source(document, args.source_tree)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"physical_executor_contract=fail reason={exc}",
              file=sys.stderr)
        return 1
    print("experiment=2026-09-02-mainline-a72-hotplug-lifecycle-gate")
    print("phase=cpu9-physical-executor-hardware-free-contract")
    print("watchdog=inherit-one-shot-15000ms-no-refresh-no-cancel")
    print("affinity=one-active-level0-call-intrinsically-unbounded")
    print("readback=cpu9-two-word-off-cpu8-two-word-on-shared-invariant")
    print("production_callbacks_bound=false")
    print("boot_candidate=false")
    print("device_action=false")
    print("physical_executor_contract=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
