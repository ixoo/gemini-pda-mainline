#!/usr/bin/env python3
"""Validate the source-only I2C6 entry-ledger and DA921x preflight boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
LEDGER_PATCH = ROOT / "patches/v7.1.3/0283-i2c-mediatek-add-bounded-I2C6-entry-ledger.patch"
PREFLIGHT_PATCH = ROOT / "patches/v7.1.3/0284-regulator-observe-legacy-DA921x-write-preflight.patch"
FRAGMENT = ROOT / "configs/gemini-da921x-readonly-preflight-ledger.fragment"
PROFILE = "da921x-readonly-preflight-ledger"
PARENT = "da921x-lk-clock-readonly-provider"
EXPECTED_HASHES = {
    LEDGER_PATCH: "fa7a04e4ec0473174a9171b9a274a0df7acc9d3a2883ce9c8c86377ecb1de8f1",
    PREFLIGHT_PATCH: "5f1ec060de13fc9cce3c2a131754ff4820ffb8fb8105ad96f75d936037e59168",
    FRAGMENT: "b7186198b1372aa2a08d875d657b363caffddc73205df24699c1e1150151d2d3",
}


class ValidationError(RuntimeError):
    """Raised when a source or contract invariant is violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def additions(text: str) -> str:
    return "\n".join(
        line[1:] for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def validate_patch_hunks(text: str) -> None:
    lines = text.splitlines()
    index = 0
    hunk_count = 0
    while index < len(lines):
        match = re.match(
            r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[index]
        )
        if not match:
            index += 1
            continue
        declared_old = int(match.group(2) or 1)
        declared_new = int(match.group(4) or 1)
        actual_old = 0
        actual_new = 0
        hunk_count += 1
        index += 1
        while index < len(lines):
            line = lines[index]
            if line.startswith("@@ ") or line.startswith("diff --git ") or line == "-- ":
                break
            if line.startswith(" "):
                actual_old += 1
                actual_new += 1
            elif line.startswith("-"):
                actual_old += 1
            elif line.startswith("+"):
                actual_new += 1
            elif line.startswith("\\"):
                pass
            else:
                break
            index += 1
        require((actual_old, actual_new) == (declared_old, declared_new),
                f"malformed hunk counts: {lines[index] if index < len(lines) else 'EOF'}")
    require(hunk_count > 0, "patch contains no hunks")


def validate_contract(contract: dict) -> None:
    require(contract["status"] == "source-implemented-build-pending", "wrong status")
    require(contract["profile"] == PROFILE and contract["parent_profile"] == PARENT,
            "profile identity changed")
    ledger = contract["ledger"]
    require(ledger["capacity"] == 32 and ledger["expected_count"] == 30,
            "ledger bounds changed")
    require(ledger["expected_overflow"] == 0, "overflow must fail closed")
    require(len(ledger["expected_sequence"]) == 30, "wrong sequence length")
    require(ledger["expected_sequence"][:14] == [
        "69:05", "69:06", "69:47", "68:d3", "68:5e", "68:d9", "68:da",
        "69:05", "69:06", "69:47", "68:d3", "68:5e", "68:d9", "68:da",
    ], "identity sequence changed")
    require(ledger["expected_sequence"][14:16] == ["68:5d", "68:5e"],
            "registration discriminator changed")
    require(ledger["expected_sequence"][-10:] == [
        "68:56", "68:51", "68:5e", "68:d9", "68:da",
        "68:56", "68:51", "68:5e", "68:d9", "68:da",
    ], "preflight sequence changed")
    require(contract["phase_accounting"] == {
        "identity_reads": 14,
        "registration_reads": 2,
        "registration_inferred_registers": ["0x5d", "0x5e"],
        "observer_reads": 4,
        "preflight_reads": 10,
        "register_data_writes": 0,
    }, "phase accounting changed")
    require(all(value == 0 for value in contract["forbidden"].values()),
            "forbidden action opened")
    require(contract["decision_map"]["gate6_write"] == "not-authorized",
            "Gate-6 write opened")
    require(contract["decision_map"]["cpu8_cpu9_admission"] == "closed",
            "CPU8/CPU9 admission opened")


def validate_sources(ledger_text: str, preflight_text: str, fragment: str) -> None:
    ledger_added = additions(ledger_text)
    preflight_added = additions(preflight_text)
    ledger_code = additions(ledger_text.split(
        "diff --git a/drivers/i2c/busses/i2c-mt65xx.c", 1)[1])
    preflight_code = additions(preflight_text.split(
        "diff --git a/drivers/regulator/da9213-legacy-regulator.c", 1)[1])
    for required in (
        "CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER",
        "MTK_I2C_ENTRY_LEDGER_CAPACITY\t32",
        "msgs[0].buf[0]",
        "mtk_i2c_entry_ledger_begin",
        "mtk_i2c_entry_ledger_finish",
        "entry_ledger=v1 count=%u capacity=%u overflow=%u",
    ):
        require(required in ledger_added, f"ledger source missing: {required}")
    require("msgs[0].buf[1]" not in ledger_added, "ledger exposes a data byte")

    for required in (
        "CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT",
        "DA9213_LEGACY_PREFLIGHT_PASSES\t2",
        "[DA9213_LEGACY_PREFLIGHT_CONTROL_A] = 0x56",
        "[DA9213_LEGACY_PREFLIGHT_STATUS_B] = 0x51",
        "[DA9213_LEGACY_PREFLIGHT_BUCKB_CONT] = 0x5e",
        "[DA9213_LEGACY_PREFLIGHT_VBUCKB_A] = 0xd9",
        "[DA9213_LEGACY_PREFLIGHT_VBUCKB_B] = 0xda",
        "registration_reads=%u observer_reads=%u preflight_reads=%u",
        "first[DA9213_LEGACY_PREFLIGHT_CONTROL_A] & 0x80",
        "safe_prestate=%u register_data_writes=0",
    ):
        require(required in preflight_added, f"preflight source missing: {required}")

    combined = ledger_code + "\n" + preflight_code
    for forbidden in (
        "i2c_master_send(", "i2c_smbus_write", "regmap_write(",
        "regmap_update_bits(", ".set_voltage_sel", ".enable =", ".disable =",
        "cpu_up(", "cpu_down(", "PAGE_CON", "msgs[0].buf[1]",
    ):
        require(forbidden not in combined, f"source opens forbidden boundary: {forbidden}")

    required_fragment = (
        "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y",
        "CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y",
        "CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT=y",
        'CONFIG_LOCALVERSION="-gemini-da921x-preflight"',
    )
    for line in required_fragment:
        require(fragment.count(line) == 1, f"fragment missing or duplicates: {line}")


def reject_mutations(contract: dict, ledger_text: str, preflight_text: str,
                     fragment: str) -> int:
    mutations = [
        ("capacity", lambda: validate_sources(
            ledger_text.replace("MTK_I2C_ENTRY_LEDGER_CAPACITY\t32",
                                "MTK_I2C_ENTRY_LEDGER_CAPACITY\t31", 1),
            preflight_text, fragment)),
        ("payload", lambda: validate_sources(
            ledger_text.replace("msgs[0].buf[0]", "msgs[0].buf[1]", 1),
            preflight_text, fragment)),
        ("passes", lambda: validate_sources(
            ledger_text,
            preflight_text.replace("DA9213_LEGACY_PREFLIGHT_PASSES\t2",
                                   "DA9213_LEGACY_PREFLIGHT_PASSES\t1", 1),
            fragment)),
    ]
    changed = copy.deepcopy(contract)
    changed["forbidden"]["cpu8_cpu9_requests"] = 1
    mutations.append(("cpu", lambda: validate_contract(changed)))
    changed = copy.deepcopy(contract)
    changed["ledger"]["expected_sequence"].pop()
    mutations.append(("sequence", lambda: validate_contract(changed)))
    changed = copy.deepcopy(contract)
    changed["decision_map"]["gate6_write"] = "authorized"
    mutations.append(("write", lambda: validate_contract(changed)))

    rejected = 0
    for name, mutation in mutations:
        try:
            mutation()
        except ValidationError:
            rejected += 1
        else:
            raise ValidationError(f"unsafe mutation accepted: {name}")
    return rejected


def main() -> None:
    for path, expected in EXPECTED_HASHES.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual == expected, f"checksum changed: {path.relative_to(ROOT)}")

    ledger_text = LEDGER_PATCH.read_text(encoding="utf-8")
    preflight_text = PREFLIGHT_PATCH.read_text(encoding="utf-8")
    fragment = FRAGMENT.read_text(encoding="utf-8")
    validate_patch_hunks(ledger_text)
    validate_patch_hunks(preflight_text)
    validate_sources(ledger_text, preflight_text, fragment)

    series = [line.strip() for line in (ROOT / "patches/series").read_text().splitlines()
              if line.strip() and not line.startswith("#")]
    attribution = [
        "v7.1.3/0283-i2c-mediatek-add-bounded-I2C6-entry-ledger.patch",
        "v7.1.3/0284-regulator-observe-legacy-DA921x-write-preflight.patch",
    ]
    start = series.index(attribution[0])
    require(series[start:start + len(attribution)] == attribution,
            "attribution patches are not canonically adjacent")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    require(profiles[PROFILE]["base"] == profiles[PARENT]["base"], "profile base changed")
    require(profiles[PROFILE]["fragments"] ==
            profiles[PARENT]["fragments"] +
            ["configs/gemini-da921x-readonly-preflight-ledger.fragment"],
            "profile is not an exact parent extension")

    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    validate_contract(contract)
    rejected = reject_mutations(contract, ledger_text, preflight_text, fragment)

    print("validation=mainline-da921x-readonly-preflight-ledger")
    print("profile=da921x-readonly-preflight-ledger")
    print("kernel_release=7.1.3-gemini-da921x-preflight")
    print("ledger_capacity=32")
    print("expected_transfers=30")
    print("preflight_reads=10")
    print("register_data_write_operations=0")
    print("CPU8_CPU9_admission=closed")
    print(f"unsafe_mutations_rejected={rejected}")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
