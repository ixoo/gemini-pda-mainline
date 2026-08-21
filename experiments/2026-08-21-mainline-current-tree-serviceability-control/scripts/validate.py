#!/usr/bin/env python3
"""Validate the exact prebuild current-tree serviceability control."""

from __future__ import annotations

import json
from pathlib import Path


PROFILE = "da921x-current-service-control"
PARENT = "da921x-same-value-write"
FRAGMENT = "configs/gemini-current-service-control.fragment"
EXPECTED_FRAGMENT = """# Current-tree serviceability control derived from the last runtime-proven
# DA921x same-value profile. Keep its read-only provider and observation path,
# but make the action path and all protected-readback/clock-entry paths absent.
# CONFIG_REGULATOR_DA9213_LEGACY_SAME_VALUE_WRITE is not set
# CONFIG_MTK_MT6797_DVFSP_CLOCK_BACKEND is not set
# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set
# CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER is not set
# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_LEDGER is not set
# CONFIG_PSTORE_GEMINI_PROTECTED_READBACK_PROBE_GATE_LEDGER is not set
# CONFIG_PSTORE_GEMINI_CLOCK_BACKEND_ENTRY_LEDGER is not set
CONFIG_LOCALVERSION=\"-gemini-service-ctl\"
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    manifest = json.loads((repo / "kernel/manifest.json").read_text(encoding="utf-8"))
    profiles = manifest["config"]["profiles"]
    parent = profiles[PARENT]
    control = profiles[PROFILE]

    require(control["base"] == parent["base"] == "defconfig", "profile base changed")
    require(control["patch_series"] == manifest["patch_series"] == "patches/series",
            "control does not select the canonical series")
    require(control["fragments"] == parent["fragments"] + [FRAGMENT],
            "control is not an exact final-fragment derivative")
    require(control["fragments"].count(FRAGMENT) == 1, "control fragment count changed")

    fragment = repo / FRAGMENT
    require(fragment.is_file() and not fragment.is_symlink(), "control fragment is unsafe")
    require(fragment.read_text(encoding="utf-8") == EXPECTED_FRAGMENT,
            "control fragment contents changed")

    series = (repo / "patches/series").read_text(encoding="utf-8").splitlines()
    require(series[-1] == "v7.1.3/0326-pstore-make-protected-readback-base-writer-usable-by-clock.patch",
            "canonical series tip changed")
    require(len(series) == len(set(series)), "canonical series contains duplicates")
    for selected in control["fragments"]:
        path = repo / selected
        require(path.is_file() and not path.is_symlink(), f"unsafe fragment: {selected}")

    contract = json.loads((repo / "experiments/2026-08-21-mainline-current-tree-serviceability-control/contract.json").read_text(encoding="utf-8"))
    require(contract["profile"]["name"] == PROFILE, "contract profile changed")
    require(contract["profile"]["expected_release"] == "7.1.3-gemini-service-ctl",
            "contract release changed")
    require(contract["scope"]["boot_candidate"] is True,
            "independently validated candidate is not admitted")
    require(contract["scope"]["regulator_data_writes"] == 0,
            "prebuild scope permits a regulator-data write")
    require(contract["decision"]["repetitions"] == 1, "repetition budget changed")

    require(contract["required_configuration"]["NR_CPUS"] == 512,
            "resolved NR_CPUS changed")
    require(contract["required_configuration"]["dt_cpu_nodes"] == 10,
            "DT CPU-node count changed")
    require(contract["candidate"]["negative_dtb_mutations_rejected"] == 15,
            "candidate mutation gate changed")

    print("validation=current-tree-serviceability-control")
    print(f"profile={PROFILE}")
    print(f"profile_fragments={len(control['fragments'])}")
    print(f"canonical_patch_count={len(series)}")
    print("clock_entry_writer=disabled")
    print("same_value_action=disabled")
    print("protected_reads=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
