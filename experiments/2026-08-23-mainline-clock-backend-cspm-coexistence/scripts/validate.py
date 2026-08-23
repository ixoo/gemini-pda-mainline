#!/usr/bin/env python3
"""Validate the read-free CSPM coexistence definition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parent.parent
ROOT = EXPERIMENT.parent.parent
PATCH_REL = "patches/v7.1.3/0335-soc-mediatek-share-CSPM-through-MT6797-handoff.patch"
FRAGMENT_REL = "configs/gemini-clock-backend-cspm-coexistence.fragment"
PROFILE = "da921x-clock-cspm-coexistence"
PARENT = "da921x-clock-entry-first-dmesg"
MARKER = (
    "GEMINI_CLOCK_BACKEND_CSPM_COEXISTENCE_V1 "
    "state=ready cspm_owner=handoff protected=0 bigidvfs=0 cpu=0"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def removed_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )


def validate_patch_text(patch: str) -> None:
    added = added_lines(patch)
    removed = removed_lines(patch)
    required = (
        'access-controllers = <&dvfsp_handoff>;',
        'reg-names = "mcumixed";',
        "struct mt6797_dvfsp_handoff *handoff;",
        "mt6797_dvfsp_handoff_get(&pdev->dev)",
        "mt6797_dvfsp_cspm_execute(",
        "mutex_lock(&handoff->transfer_lock);",
        "mutex_lock(&handoff->lock);",
        "ret = execute(context, handoff->cspm);",
        "mt6797_dvfsp_clock_execute, &call",
        "GEMINI_CLOCK_BACKEND_CSPM_COEXISTENCE_V1",
        "state=ready cspm_owner=handoff protected=0 bigidvfs=0 cpu=0",
        "CSPM owner=handoff; state owner unregistered",
    )
    for token in required:
        require(token in added, f"required coexistence token missing: {token}")
    require('reg-names = "mcumixed", "cspm";' in removed,
            "old two-resource description is not removed")
    require('devm_platform_ioremap_resource_byname(pdev, "cspm")' in removed,
            "old direct CSPM mapping is not removed")
    require('0x11015000 0 0x1000' in removed,
            "overlapping CSPM resource is not removed")
    require('reg-names = "mcumixed", "cspm";' not in added,
            "two-resource description was re-added")
    require('devm_platform_ioremap_resource_byname(pdev, "cspm")' not in added,
            "direct CSPM mapping was re-added")
    lock_transfer = added.index("mutex_lock(&handoff->transfer_lock);")
    lock_state = added.index("mutex_lock(&handoff->lock);", lock_transfer)
    execute = added.index("ret = execute(context, handoff->cspm);", lock_state)
    unlock_state = added.index("mutex_unlock(&handoff->lock);", execute)
    unlock_transfer = added.index("mutex_unlock(&handoff->transfer_lock);",
                                  unlock_state)
    require(lock_transfer < lock_state < execute < unlock_state < unlock_transfer,
            "CSPM callback does not retain the exact I2C6 lock order")
    for forbidden in (
        "status = \"okay\";",
        "mt6797_bigidvfs_backend_read(",
        "arm_smccc_",
        "psci_ops.cpu_on",
        "cpu_up(",
        "regulator_set_voltage(",
        "kernel_restart(",
        "emergency_restart(",
    ):
        require(forbidden not in added, f"forbidden action added: {forbidden}")
    require("Signed-off-by:" not in patch, "synthetic patch gained a sign-off")


def main() -> None:
    contract = json.loads((EXPERIMENT / "contract.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "kernel/manifest.json").read_text(encoding="utf-8"))
    patch_path = ROOT / PATCH_REL
    patch = patch_path.read_text(encoding="utf-8")
    series = (ROOT / "patches/series").read_text(encoding="utf-8").splitlines()
    fragment = (ROOT / FRAGMENT_REL).read_text(encoding="utf-8").splitlines()

    require(contract["experiment"] == EXPERIMENT.name, "experiment identity changed")
    require(contract["foundation"]["evidence_commit"] == "d61b89c6",
            "runtime foundation changed")
    require(contract["patch"]["path"] == PATCH_REL, "contract patch path changed")
    require(hashlib.sha256(patch_path.read_bytes()).hexdigest() ==
            contract["patch"]["sha256"], "patch identity changed")
    candidate = contract["candidate"]
    require(candidate["build_repository_commit"] ==
            "67e40d761f9e83063742a8e36ffb001c6fa3d38e",
            "candidate build commit changed")
    require(candidate["package_manifest_sha256"] ==
            "703ceb7815c4e443f4504000be2c032eb452ff5aa941bfb3da56d3225933e4c2",
            "candidate package manifest changed")
    require(candidate["control_dtb_sha256"] ==
            "8033f913a4cfd78c2fca9d901c5838285717e9929fc577ea369d7066423c2126",
            "candidate DT changed")
    require(candidate["raw_sha256"] ==
            "dc09377159237c99ef779fbc24824df6c14b8258a9dd237cb7a113e9ed61e6f2",
            "raw candidate identity changed")
    require(candidate["padded_sha256"] ==
            "ae4010449e72ed4d02643616073e8d74f7cad25adb4afb5db69030d39eb324e7",
            "padded candidate identity changed")
    require(candidate["padded_size"] == 16_777_216,
            "candidate partition geometry changed")
    require(candidate["lk_gates"] == "32-of-32",
            "candidate LK gate count changed")
    require(candidate["negative_dtb_mutations_rejected"] == 19,
            "candidate mutation gate count changed")
    require(candidate["boot_candidate"] is True,
            "independently validated candidate was not admitted")
    require(contract["scope"]["clock_backend_protected_reads"] == 0,
            "protected read scope opened")
    require(contract["scope"]["clock_backend_mmio_transactions"] == 0,
            "clock MMIO scope opened")
    require(contract["scope"]["boot_candidate"] is True,
            "admitted candidate scope changed")
    require(contract["runtime_oracle"]["coexistence_marker"] == MARKER,
            "runtime marker contract changed")
    validate_patch_text(patch)

    profiles = manifest["config"]["profiles"]
    require(PROFILE in profiles and PARENT in profiles, "profile missing")
    require(profiles[PROFILE]["patch_series"] == "patches/series",
            "profile series changed")
    require(profiles[PROFILE]["fragments"] ==
            profiles[PARENT]["fragments"] + [FRAGMENT_REL],
            "profile is not the exact clock-entry parent plus coexistence identity")
    require(series[-1] == PATCH_REL.removeprefix("patches/"),
            "coexistence patch is not canonical tail")
    require(series.count(PATCH_REL.removeprefix("patches/")) == 1,
            "coexistence patch series count changed")
    for line in (
        "# CONFIG_MTK_MT6797_DVFSP_BIGIDVFS_BACKEND is not set",
        "# CONFIG_MTK_MT6797_PROTECTED_READBACK_OBSERVER is not set",
        'CONFIG_LOCALVERSION="-gemini-clock-cspm-coexist"',
    ):
        require(line in fragment, f"fragment gate missing: {line}")

    foundation = ROOT / contract["foundation"]["result"]
    foundation_text = foundation.read_text(encoding="utf-8")
    for token in (
        "cspm_resource_owner=1001a000.dvfsp-clock-backend",
        "handoff_probe_result=-EBUSY",
        "i2c6_result=deferred",
        "da921x_i2c_clients=0",
        "protected_read_admitted=false",
        "next_branch=single-cspm-owner-or-explicit-shared-access-with-full-serviceability",
    ):
        require(token in foundation_text, f"foundation token missing: {token}")

    print("validation=clock-backend-cspm-coexistence-definition")
    print(f"manifest_profiles={len(profiles)}")
    print(f"canonical_patch_count={len(series)}")
    print("cspm_resource_owner=dvfsp_handoff")
    print("clock_backend_resources=mcumixed")
    print("i2c6_transfer_exclusion=complete")
    print("protected_clock_reads=0")
    print("bigidvfs_reads=0")
    print("clock_backend_mmio_transactions=0")
    print("cpu8_cpu9_admission=closed")
    print("device_access=none")
    print("hardware_write=none")
    print("boot_candidate=true")
    print("result=pass")


if __name__ == "__main__":
    main()
