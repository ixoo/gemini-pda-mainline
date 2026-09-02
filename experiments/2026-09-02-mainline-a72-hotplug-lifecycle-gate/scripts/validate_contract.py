#!/usr/bin/env python3
"""Validate the CPU9 physical-off and same-boot restore gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys


EXPERIMENT = "2026-09-02-mainline-a72-hotplug-lifecycle-gate"
SERIES_SHA256 = "3f55b6be379d540d947c68deb74966b2a7f0ae05819305841f1a077c33da4610"
MANIFEST_SHA256 = "af9331a6d97a73475243dc1f79df6ca70206d3daf69405c20e9145e7c9930b43"
SOURCE_HASHES = {
    "arch/arm64/include/asm/cpu_ops.h":
        "8148d875ffa9110d8c7d9f4fe4121ac6441c541392d5c09381693fa02825ac64",
    "arch/arm64/include/asm/mt6797_a72_membership.h":
        "8c19c6a8ffb8d4292f65791a6edc08c73cad11c79a26b6b88e296c9d1e241d16",
    "arch/arm64/kernel/mt6797_a72_membership.c":
        "17758faa2a96b6d4eb1535ee0068b3ebae3e64bcdafae4108605f8ba1867dace",
    "arch/arm64/kernel/mt6797_psci.c":
        "13c0497e4a462e5367d39236dbf6fecaf7478df012705d8f5e6ed39625e16d8e",
    "arch/arm64/kernel/smp.c":
        "90ca49f088b2ea697d7c35b1340a985e5119a5fe71dd9c0713e1c703632beb2f",
    "kernel/cpu.c":
        "bb87f455ebdd3e2b74befbd097a3a35723ac6350cafbd322aa3caffa4f6b7302",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", source, re.S)
    require(match is not None, f"missing function {name}")
    start = match.start()
    depth = 0
    opened = False
    for offset in range(match.end() - 1, len(source)):
        char = source[offset]
        if char == "{":
            depth += 1
            opened = True
        elif char == "}":
            depth -= 1
            if opened and depth == 0:
                return source[start:offset + 1]
    raise ValueError(f"unterminated function {name}")


def validate_contract(contract: dict) -> None:
    require(contract.get("schema") == 1, "schema changed")
    require(contract.get("experiment") == EXPERIMENT, "experiment changed")
    require(contract.get("repository_parent") ==
            "0dc07a6bc46da6bb1b074ffee4ce5efd26908411",
            "repository parent changed")
    require(contract.get("canonical_series_entries") == 474,
            "canonical series count changed")
    require(contract.get("canonical_series_sha256") == SERIES_SHA256,
            "canonical series identity changed")
    require(contract.get("manifest_sha256") == MANIFEST_SHA256,
            "manifest identity changed")
    require(contract.get("prepared_source", {}).get("files") == SOURCE_HASHES,
            "prepared source identities changed")

    current = contract.get("current_boundary", {})
    require(current == {
        "cpu_can_disable": False,
        "normal_down_owner": False,
        "cpu9_restore_owner": False,
        "p32_scope": "failed-cpu-up-rollback-only",
        "initial_cpu8_up_attempt_consumed": True,
        "initial_cpu9_up_attempt_consumed": True,
        "standard_hotplug_exposed": False,
    }, "current boundary changed")

    selected = contract.get("selected_transition", {})
    require(selected == {
        "target_cpu": 9,
        "retained_peer_cpu": 8,
        "entry_members": "0x3",
        "offline_members": "0x1",
        "restored_members": "0x3",
        "physical_cpu_off_required": True,
        "park_only_is_success": False,
        "last_a72_off_allowed": False,
    }, "selected physical transition changed")

    require(contract.get("implementation_order") == [
        "hardware-free-generic-down-handoffs",
        "hardware-free-cpu9-down-and-restore-owner",
        "buildbox-compile-and-focused-kunit",
        "offline-candidate-and-recovery-validation",
        "one-physical-cpu9-off-and-same-boot-restore",
    ], "implementation order changed")

    handoffs = contract.get("required_generic_handoffs")
    require(handoffs == [
        {
            "name": "cpu_down_preflight",
            "placement": "before-cpu_maps_update_begin",
            "owner": "requesting-controller",
        },
        {
            "name": "cpu_down_validate",
            "placement": "after-cpu_add_remove_lock-before-cpus_write_lock",
            "owner": "generic-cpuhp",
        },
        {
            "name": "cpu_down_complete",
            "placement": "after-full-requested-cpuhp-down-before-cpus_write_unlock",
            "owner": "generic-cpuhp",
        },
    ], "generic handoff map changed")

    required_target_handoffs = {
        "target-cpu-disable-prepare-before-topology-removal",
        "target-cpu-off-commit-before-psci-cpu-off",
        "controller-one-affinity-attempt-after-target-dead-publication",
        "controller-cpu9-per-core-power-readback",
        "controller-cpu8-bounded-responsiveness",
        "controller-shared-state-invariance",
        "controller-offline-membership-commit",
        "controller-distinct-cpu9-restore-preflight",
        "controller-one-cpu-on-attempt",
        "controller-secondary-and-full-cpuhp-restore-completion",
    }
    require(set(contract.get("target_and_controller_handoffs", [])) ==
            required_target_handoffs,
            "target/controller handoff set changed")

    require(contract.get("budgets") == {
        "cpu9_cpu_off": 1,
        "cpu9_affinity_info_level0": 1,
        "cpu9_restore_cpu_on": 1,
        "cpu8_last_off": 0,
        "cpu0_through_cpu7_off": 0,
        "cpu_off_retry": 0,
        "affinity_retry": 0,
        "cpu_on_retry": 0,
    }, "call budgets changed")

    timing = contract.get("timing", {})
    require(timing.get("secure_affinity_call_is_intrinsically_bounded") is False,
            "secure affinity call falsely bounded")
    require(timing.get("external_recovery_watchdog_ms") == 15000,
            "recovery watchdog changed")
    require(timing.get("watchdog_refresh_after_cpu_off_commit") is False,
            "post-commit watchdog refresh enabled")
    require(timing.get("watchdog_cancel_point") ==
            "after-restored-topology-serviceability-and-progress",
            "watchdog cancel point changed")

    require(contract.get("failure_policy") == {
        "before_cpu_off_commit":
            "release-owned-software-state-and-reject-without-hardware-effect",
        "at_or_after_cpu_off_commit":
            "retain-conservative-state-no-retry-no-guessed-inverse-reset-only",
        "restore_failure": "retain-fault-no-second-cpu-on-reset-only",
    }, "failure policy changed")

    predicate = set(contract.get("physical_pass_predicate", []))
    required_predicate = {
        "fresh-exact-candidate-and-pristine-trigger",
        "cpu0-through-cpu9-online-at-entry",
        "exact-4+4+2-topology-at-entry",
        "one-target-cpu9-cpu-off-commit",
        "one-controller-affinity-info-level0-attempt",
        "cpu0-through-cpu8-online-with-cpu9-offline",
        "cpu8-bounded-callback-passes",
        "cpu9-per-core-off-readback-passes",
        "shared-cluster-provider-clock-cci-state-unchanged",
        "one-distinct-cpu9-restore-cpu-on-attempt",
        "cpu0-through-cpu9-online-after-restore",
        "exact-4+4+2-topology-after-restore",
        "cpu8-and-cpu9-independent-accounting-advances",
        "usb-netcat-serviceability-preserved",
        "retained-terminal-attribution-valid",
        "changed-boot-id-recovery-and-unchanged-boot2",
    }
    require(predicate == required_predicate, "physical pass predicate changed")

    forbidden = set(contract.get("forbidden_actions", []))
    required_forbidden = {
        "cpu8-last-off", "cpu0-through-cpu7-off", "park-only-success-claim",
        "second-affinity-query", "cpu-off-retry", "cpu-on-retry",
        "cpufreq-change", "opp-change", "thermal-change", "idle-change",
        "suspend-change", "device-storage-write", "primary-boot-write",
        "native-vm-kernel-build",
    }
    require(forbidden == required_forbidden, "forbidden-action set changed")
    require(contract.get("boot_candidate") is False, "boot candidate enabled")
    require(contract.get("device_action") is False, "device action enabled")
    require(contract.get("native_vm_build") is False, "native VM build enabled")


def validate_source(contract: dict, source_tree: pathlib.Path) -> None:
    for relative, expected in SOURCE_HASHES.items():
        path = source_tree / relative
        require(path.is_file(), f"missing source file {relative}")
        require(sha256(path) == expected, f"source identity changed: {relative}")

    psci = (source_tree / "arch/arm64/kernel/mt6797_psci.c").read_text()
    can_disable = function_body(psci, "mt6797_psci_cpu_can_disable")
    require(re.search(r"\{\s*return false;\s*\}", can_disable, re.S) is not None,
            "A72 disable veto changed")
    require(".cpu_can_disable = mt6797_psci_cpu_can_disable" in psci,
            "A72 disable callback missing")

    cpu_ops = (source_tree / "arch/arm64/include/asm/cpu_ops.h").read_text()
    kernel_cpu = (source_tree / "kernel/cpu.c").read_text()
    require("cpu_down_preflight" not in cpu_ops and
            "cpu_down_validate" not in cpu_ops and
            "cpu_down_complete" not in cpu_ops,
            "current source unexpectedly has down handoffs")
    require("arch_cpu_down_preflight" not in kernel_cpu and
            "arch_cpu_down_validate" not in kernel_cpu and
            "arch_cpu_down_complete" not in kernel_cpu,
            "current generic down path unexpectedly changed")

    membership_h = (source_tree /
                    "arch/arm64/include/asm/mt6797_a72_membership.h").read_text()
    membership_c = (source_tree /
                    "arch/arm64/kernel/mt6797_a72_membership.c").read_text()
    require("MT6797_A72_OPERATION_CPU9_OFF" in membership_h and
            "MT6797_A72_OPERATION_CPU8_LAST_OFF" in membership_h,
            "historical off operation slots missing")
    require("MT6797_A72_OPERATION_CPU9_OFF" not in membership_c and
            "MT6797_A72_OPERATION_CPU8_LAST_OFF" not in membership_c,
            "current source unexpectedly implements a down operation")
    up_operation = function_body(membership_c, "mt6797_a72_up_operation")
    require("MT6797_A72_OPERATION_CPU8_UP" in up_operation and
            "MT6797_A72_OPERATION_CPU9_UP" in up_operation and
            "CPU9_OFF" not in up_operation,
            "up-only operation mapping changed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parents[1] /
                        "contract.json")
    parser.add_argument("--source-tree", type=pathlib.Path)
    parser.add_argument("--contract-only", action="store_true")
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()

    try:
        require(not (args.contract_only and args.source_only),
                "--contract-only and --source-only are mutually exclusive")
        if not args.source_only:
            contract = json.loads(args.contract.read_text())
            validate_contract(contract)
        else:
            contract = {}
        if args.contract_only:
            require(args.source_tree is None,
                    "--contract-only and --source-tree are mutually exclusive")
        else:
            require(args.source_tree is not None,
                    "--source-tree is required for source validation")
            validate_source(contract, args.source_tree)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"hotplug_lifecycle_contract=fail reason={exc}", file=sys.stderr)
        return 1

    print("experiment=2026-09-02-mainline-a72-hotplug-lifecycle-gate")
    print("current_path=disable-vetoed-down-owner-absent-restore-owner-absent")
    print("selected_transition=cpu9-physical-off-retain-cpu8-then-distinct-restore")
    print("secure_affinity=active-one-attempt-internally-unbounded")
    print("recovery=external-watchdog-15000ms-reset-only-after-commit")
    print("park_only_success=false")
    print("boot_candidate=false")
    print("device_action=false")
    print("hotplug_lifecycle_contract=pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
