#!/usr/bin/env python3
"""Validate the MT6797 A72 platform-state generation input."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"validation failed: {message}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    contract = json.loads((HERE / "contract.json").read_text())
    require(contract["repository_parent"] ==
            "cdf5dbe9e1f9331eb261b705f22a52b871a0bc94",
            "signed audit parent")
    for key in ("readme", "design", "matrix"):
        path = ROOT / contract["decision"][key]
        require(sha256(path) == contract["decision"][f"{key}_sha256"],
                f"decision {key} hash")
    require(contract["decision"]["selected_boundary"] ==
            "DEFAULT_OFF_CAPTURE_ONLY_PLATFORM_STATE",
            "selected boundary")
    require(contract["parent"]["source_state"] ==
            "905fb7f5ead29cbe65eaf7f66e41433aea417c2ee15d751ebda6ddf79f19ad8e",
            "parent source state")
    require(contract["validated_generation"] is None and
            contract["validated_build"] is None,
            "unperformed results remain null")
    require(contract["scope"] == {
        "default_off": True,
        "toprgu_status_read": True,
        "platform_samples": 2,
        "polling": False,
        "hardware_write": False,
        "a34_caller": False,
        "opens_owner": False,
        "cpu_on": False,
        "cpu_off": False,
        "device_action": False,
        "boot_candidate": False,
    }, "scope remains closed")

    readme = (HERE / "README.md").read_text()
    design = (HERE / "DESIGN.md").read_text()
    for token in (
        "deterministic Buildbox generation input; patches pending",
        "two immediate bounded samples with no loop or retry",
        "destination that remains all-zero on error",
        "DT node stays disabled",
        "CPU8/CPU9 remain closed",
    ):
        require(token in readme, f"README token: {token}")
    for token in (
        "clears the caller record before any lookup",
        "but do not serialize",
        "secure firmware.",
        "cannot open A34",
        "No register write",
    ):
        require(token in design, f"design token: {token}")

    driver = (HERE / "source/mt6797-a72-platform-state.c").read_text()
    header = (HERE / "source/mt6797-a72-platform-state.h").read_text()
    binding = (HERE / "source/mediatek,mt6797-a72-platform-state.yaml").read_text()
    for token in (
        "MT6797_CCI_MP2_PORT_CONTROL\t\t0x6000",
        "MT6797_CCI_STATUS\t\t\t0x000c",
        "reset_control_status(source->pwrap_reset)",
        "ret = -EBUSY",
        "ret = -EAGAIN",
        "snapshot->valid = true",
    ):
        require(token in driver, f"source driver token: {token}")
    for forbidden in (
        "writel(", "regmap_write(", "reset_control_assert(",
        "reset_control_deassert(", "readl_poll", "while (", "for (",
        "cpu_up(", "cpu_down(",
    ):
        require(forbidden not in driver, f"forbidden source effect: {forbidden}")
    require("bool valid;" in header and "return -EOPNOTSUPP;" in header,
            "typed API and disabled stub")
    require("additionalProperties: false" in binding and
            "- const: cci" in binding,
            "strict named-resource binding")

    buildbox = (ROOT / "scripts/buildbox").read_text()
    for command in (
        "generate-mt6797-a72-platform-state-patches",
        "fetch-mt6797-a72-platform-state-patches",
    ):
        require(buildbox.count(command) >= 2, f"Buildbox command: {command}")

    print("validation=mt6797-a72-platform-state-generation-input")
    print("result=pass")
    print("expected_patches=2")
    print("platform_samples=2-no-loop")
    print("hardware_write=none")
    print("a34_caller=none")
    print("device_action=none")


if __name__ == "__main__":
    main()
