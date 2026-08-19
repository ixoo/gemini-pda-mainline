#!/usr/bin/env python3
"""Validate the corrected I2C6 firmware-writer transaction-window source."""

from __future__ import annotations

import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
PATCH_NAME = (
    "v7.1.3/0287-soc-mediatek-guard-I2C6-transfer-window-with-SCP-reset.patch"
)
PATCH = ROOT / "patches" / PATCH_NAME
FRAGMENT = ROOT / "configs/gemini-i2c6-firmware-writer-transaction-window.fragment"
MANIFEST = ROOT / "kernel/manifest.json"
SERIES = ROOT / "patches/series"
CONTRACT = EXPERIMENT / "contract.json"
PROFILE = "da921x-i2c6-firmware-writer-transaction-window"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_contract(contract: dict) -> None:
    require(contract["status"] == "source-designed-awaiting-build",
            "contract status changed")
    require(contract["profile"] == PROFILE, "profile changed")
    require(contract["kernel_release"] == "7.1.3-gemini-i2c6-fwtxn",
            "release changed")
    require(contract["probe"]["required_scp_reset_control"] ==
            ["0x00000000", "0x00000000"], "probe reset predicate changed")
    require(contract["probe"]["scp_debug_pc"] == "record-only",
            "debug PC became authoritative")
    require(contract["probe"]["devapc_ao"] ==
            "record-only-non-authoritative", "Device-APC became authoritative")
    same_boot = contract["same_boot"]
    for field in ("i2c6_transactions", "transaction_entry_reset_checks",
                  "transaction_exit_reset_checks", "entry_ledger_entries"):
        require(same_boot[field] == 20, f"{field} changed")
    require(same_boot["required_transaction_reset_value"] == "0x00000000",
            "transaction reset predicate changed")
    require(all(value == 0 for value in contract["forbidden"].values()),
            "a forbidden action opened")
    require(contract["decision_map"]["gate6_write"] == "not-authorized",
            "Gate-6 write opened")
    require(contract["decision_map"]["cpu8_cpu9_admission"] == "closed",
            "CPU admission opened")


def validate_sources(patch: str, fragment: str, manifest: dict,
                     series: list[str]) -> None:
    required_patch = (
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW",
        "mt6797_dvfsp_check_scp_reset_locked(handoff, true)",
        "mt6797_dvfsp_check_scp_reset_locked(handoff, false)",
        "i2c6-scp-reset-entry-failed",
        "i2c6-scp-reset-exit-failed",
        "transaction_entry_checks=%llu",
        "transaction_exit_checks=%llu",
        "transaction_reset_failures=%u",
    )
    for token in required_patch:
        require(patch.count(token) >= 1, f"missing patch token: {token}")
    require(patch.count("readl(handoff->scp_cfg + SCP_CFG_RESET_CONTROL)") == 1,
            "transaction reset read shape changed")
    require("writel(" not in patch and "i2c_transfer(" not in patch,
            "patch gained a forbidden hardware operation")
    require(fragment.count(
        "CONFIG_MTK_MT6797_I2C6_FW_WRITER_TRANSACTION_WINDOW=y") == 1,
        "transaction-window option missing")
    require(fragment.count(
        "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y") == 1,
        "entry-ledger lifecycle oracle missing")
    require(fragment.count("CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y") == 1,
            "entry ledger missing")
    require(fragment.count(
        'CONFIG_LOCALVERSION="-gemini-i2c6-fwtxn"') == 1,
        "release fragment changed")
    profile = manifest["config"]["profiles"][PROFILE]
    require(profile["base"] == "defconfig", "profile base changed")
    require(profile["fragments"][-1] ==
            "configs/gemini-i2c6-firmware-writer-transaction-window.fragment",
            "profile fragment changed")
    require(series.count(PATCH_NAME) == 1, "patch series entry changed")
    require(series[-1] == PATCH_NAME, "patch is not last in canonical order")


def mutation_rejected(contract: dict, patch: str, fragment: str,
                      manifest: dict, series: list[str]) -> bool:
    try:
        validate_contract(contract)
        validate_sources(patch, fragment, manifest, series)
    except (AssertionError, KeyError):
        return True
    return False


def main() -> None:
    patch = PATCH.read_text(encoding="utf-8")
    fragment = FRAGMENT.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    series = [line for raw in SERIES.read_text(encoding="utf-8").splitlines()
              if (line := raw.strip()) and not line.startswith("#")]
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    validate_contract(contract)
    validate_sources(patch, fragment, manifest, series)

    mutations: list[tuple[dict, str, str, dict, list[str]]] = []
    changed = copy.deepcopy(contract)
    changed["probe"]["scp_debug_pc"] = "required-zero"
    mutations.append((changed, patch, fragment, manifest, series))
    changed = copy.deepcopy(contract)
    changed["probe"]["devapc_ao"] = "authoritative"
    mutations.append((changed, patch, fragment, manifest, series))
    changed = copy.deepcopy(contract)
    changed["same_boot"]["transaction_exit_reset_checks"] = 0
    mutations.append((changed, patch, fragment, manifest, series))
    changed = copy.deepcopy(contract)
    changed["forbidden"]["da921x_register_data_writes"] = 1
    mutations.append((changed, patch, fragment, manifest, series))
    mutations.append((contract, patch.replace(
        "mt6797_dvfsp_check_scp_reset_locked(handoff, false)",
        "mt6797_dvfsp_check_scp_reset_locked(handoff, true)", 1),
        fragment, manifest, series))
    mutations.append((contract, patch + "\nwritel(1, handoff->scp_cfg);\n",
                      fragment, manifest, series))
    mutations.append((contract, patch, fragment.replace(
        "CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y", "", 1),
        manifest, series))
    mutations.append((contract, patch, fragment.replace(
        "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y", "", 1),
        manifest, series))
    mutations.append((contract, patch, fragment, manifest, series[:-1]))
    require(all(mutation_rejected(*mutation) for mutation in mutations),
            "an unsafe mutation escaped validation")

    print("validation=mainline-i2c6-firmware-writer-transaction-window")
    print(f"profile={PROFILE}")
    print("probe_reset_samples=2")
    print("transaction_entry_checks_expected=20")
    print("transaction_exit_checks_expected=20")
    print("SCP_register_writes=0")
    print("Device_APC_register_writes=0")
    print("DA921x_register_data_writes=0")
    print("Gate6_write=not-authorized")
    print("CPU8_CPU9_admission=closed")
    print(f"unsafe_mutations_rejected={len(mutations)}")
    print("result=pass")


if __name__ == "__main__":
    main()
