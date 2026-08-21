#!/usr/bin/env python3
"""Validate the DA921x provider-state generation input."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def main() -> None:
    contract = json.loads((HERE / "contract.json").read_text())
    require(contract["repository_parent"] ==
            "4b7535ee4a956c91ef6df3ba8451554af3410d35",
            "platform-state evidence parent")
    require(contract["parent"]["source_state"] ==
            "905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e",
            "managed parent source state")
    require(contract["expected_patches"] == [
        "patches/v7.1.3/0312-arm64-add-read-only-provider-state-snapshot.patch",
        "patches/v7.1.3/0313-regulator-export-stable-DA921x-provider-state.patch",
        "patches/v7.1.3/0314-regulator-test-stable-DA921x-provider-state.patch",
    ], "three logical patch identities")
    require(contract["validated_generation"] is None,
            "generation remains pending")
    require(contract["validated_build"] is None,
            "build remains pending")
    require(contract["scope"] == {
        "samples": 2,
        "reads_on_success": 10,
        "adapter_retries": 0,
        "polling": False,
        "hardware_write": False,
        "delay": False,
        "a34_caller": False,
        "opens_owner": False,
        "cpu_on": False,
        "cpu_off": False,
        "device_action": False,
        "boot_candidate": False,
    }, "closed scope")

    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    for token in (
        "two immediate complete samples under one root",
        "exactly ten reads on success",
        "provider registry mutex -> endpoint mutex -> I2C root-adapter lock",
        "No result in this experiment authorizes CPU8",
    ):
        require(token in readme, f"README token: {token}")
    for token in (
        "does not classify rail ownership",
        "clears the destination before registry lookup",
        "uses local accounting objects",
        "cannot by itself make CPU8 eligible",
    ):
        require(token in design, f"design token: {token}")

    edits = (HERE / "scripts/source_edits.py").read_text()
    for token in (
        "MT6797_A72_PROVIDER_STATE_ABI",
        "mt6797_a72_provider_snapshot",
        "da9213_legacy_provider_state_snapshot",
        "I2C_LOCK_ROOT_ADAPTER",
        "DA9213_PROVIDER_SNAPSHOT_ACTIONS",
        "da9213_provider_snapshot_transport_faults",
    ):
        require(token in edits, f"source edit token: {token}")
    for forbidden in ("cpu_up(", "cpu_down(", "psci_ops"):
        require(forbidden not in edits, f"forbidden edit effect: {forbidden}")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-da921x-provider-state-patches",
        "fetch-da921x-provider-state-patches",
    ):
        require(buildbox.count(command) >= 2,
                f"Buildbox command: {command}")

    print("design_validation=pass")
    print("expected_patch_count=3")
    print("hardware_write=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
