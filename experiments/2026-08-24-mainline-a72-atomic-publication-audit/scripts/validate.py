#!/usr/bin/env python3
"""Validate the atomic A72 publication contract audit."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
INPUT_COMMIT = "d77441e9dbee1a8639eb439566c81abd7e996a21"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    readme = (EXPERIMENT / "README.md").read_text()
    design = (EXPERIMENT / "DESIGN.md").read_text()
    source = (EXPERIMENT / "results/source-audit-20260824.txt").read_text()
    matrix = (EXPERIMENT / "results/decision-matrix.tsv").read_text()
    index = (ROOT / "experiments/README.md").read_text()
    roadmap = (ROOT / "docs/ROADMAP.md").read_text()

    require(subprocess.run(
        ["git", "-C", str(ROOT), "merge-base", "--is-ancestor",
         INPUT_COMMIT, "HEAD"], check=False).returncode == 0,
        "repository input is not an ancestor")
    require(contract["experiment"] == EXPERIMENT.name, "experiment identity")
    require(contract["repository_input"] == INPUT_COMMIT,
            "repository input")
    require(contract["canonical_parent"].endswith(
        "0344-arm64-revise-A34-for-direct-state-v2.patch"),
        "canonical parent")
    require(contract["prepared_source_state"] ==
            "5f830ffd6050d3831b2a6a5d94b6f8a8125444215f93828de714c5f551dcf0ad",
            "prepared source state")
    require(contract["prepared_source_integrity"] ==
            "6e8edea4e04443353bcc5bc5c6da8eed3914bcca529e864f8af9af52a9ef502d",
            "prepared source integrity")
    expected_patches = {
        "patches/v7.1.3/0342-arm64-add-P30-pristine-bootstrap-claim.patch":
            "302f679c6bcd938b152b9a19c778537c28d44454c74cb5edee42c6fd871f734f",
        "patches/v7.1.3/0343-arm64-bind-A72-direct-state-to-target-identity.patch":
            "63cd561fb6977272b2c2cd579d6909fe38b94e6d22afaa8d35d4dcde56caa0ea",
        "patches/v7.1.3/0344-arm64-revise-A34-for-direct-state-v2.patch":
            "c7f39812d182f85a9b7db3f47cf8de4219efcdf36bfb4b99dae5026fac6bb192",
    }
    require(contract["input_patch_sha256"] == expected_patches,
            "input patch map")
    for relative, expected in expected_patches.items():
        require(sha256(ROOT / relative) == expected,
                f"input patch identity {relative}")
    require(contract["finding"] ==
            "current-separate-release-is-not-an-atomic-publication-boundary",
            "audit finding")
    require(contract["selected"] ==
            "p30-lock-nested-owner-commit-finalizer", "selected design")
    require(contract["lock_order"] == [
        "cpu_hotplug_read", "a72_transition_mutex",
        "direct_source_registry_and_source_locks", "p30_raw_spinlock",
        "a72_state_raw_spinlock",
    ], "lock order")
    commit = contract["commit"]
    require(commit["owner_recheck"] ==
            "exact-pristine-byte-match-plus-private-zero" and
            commit["health_last"] is True and
            commit["fallible_operation_after_health_store"] is False and
            commit["cleared_diagnostic_blocker"] ==
            "MT6797_A72_BLOCK_A34_BOOTSTRAP" and
            commit["first_generation"] == 1 and
            commit["first_cookie"] == "0xa7200001" and
            commit["second_call_before_source"] == "-EALREADY",
            "commit contract")
    scope = contract["scope"]
    require(scope["default_off"] is True and
            scope["hardware_free"] is True and
            scope["production_callers"] == 0,
            "default-off scope")
    require(all(scope[key] is False for key in (
        "physical_reader_binding", "production_replay_source",
        "cpu_veto_change", "cpu_on", "cpu_off", "device_action",
        "boot_candidate",
    )), "scope closure")

    for token in (
        f"repository_input={INPUT_COMMIT}",
        "a34_production_callers=0", "direct_snapshot_production_callers=0",
        "p30_claim_production_callers=0",
        "production_available_assignment_count=0",
        "p30_release_is_fallible=true", "p30_nested_finalize_api=false",
        "release_before_commit_has_prepare_gap=true",
        "commit_before_release_has_postcommit_failure=true",
        "cpu_up_when_available=-EOPNOTSUPP",
        "mt6797_psci_cpu_boot=-EAGAIN",
        "mt6797_psci_cpu_can_disable=false", "hardware_operations=0",
        "boot_candidate=false", "result=selected-nested-finalizer",
    ):
        require(token in source, f"source audit fact {token}")
    rows = [line.split("\t") for line in matrix.splitlines()]
    require(rows[0] == ["option", "p30_prepare_gap",
                        "postcommit_fallible", "lock_order", "result"],
            "decision matrix header")
    require(len(rows) == 7, "decision matrix row count")
    require(rows[-1] == ["p30-lock-nested-owner-commit-finalizer", "no",
                         "no", "valid", "selected"],
            "selected matrix row")
    require(sum(row[-1] == "selected" for row in rows[1:]) == 1,
            "selected matrix option count")

    for token in (
        "completed offline audit; nested P30 finalizer selected",
        "separate fallible call",
        "health = AVAILABLE", "no production caller",
        "does not establish current-boot replay authority",
        "It creates no boot candidate",
    ):
        require(token in readme, f"README contract {token}")
    for token in (
        "P30 private raw spinlock with interrupts disabled",
        "clears the logical claim while retaining the private lock",
        "may acquire only `a72_state_lock`",
        "`health = MT6797_A72_OWNER_AVAILABLE` last",
        "repeat-before-source rejection",
        "all hardware, provider, and CPU request counters remain zero",
    ):
        require(token in design, f"design contract {token}")
    require(EXPERIMENT.name in index, "experiment index")
    for token in (
        "nested P30 finalizer", "raw lock across one non-sleeping commit",
        "both CPU vetoes unchanged", "no production caller",
        "no physical reader binding",
    ):
        require(token in roadmap, f"Roadmap selection {token}")

    for relative in (
        "README.md", "DESIGN.md", "contract.json",
        "results/source-audit-20260824.txt", "results/decision-matrix.tsv",
        "scripts/validate.py",
    ):
        path = EXPERIMENT / relative
        require(path.is_file() and not path.is_symlink(),
                f"missing or unsafe audit file {relative}")

    print("validation=a72-atomic-publication-audit")
    print("finding=current-separate-release-is-not-atomic")
    print("selected=p30-lock-nested-owner-commit-finalizer")
    print("production_callers=0")
    print("cpu_veto_change=false")
    print("hardware_operations=0")
    print("device_action=none")
    print("boot_candidate=false")
    print("result=pass")


if __name__ == "__main__":
    main()
