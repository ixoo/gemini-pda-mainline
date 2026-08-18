#!/usr/bin/env python3
"""Validate the runtime-triggered read-only DA921x preflight boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT = Path(__file__).resolve().parents[1]
PATCH = ROOT / (
    "patches/v7.1.3/"
    "0285-regulator-trigger-legacy-DA921x-read-only-preflight.patch"
)
FRAGMENT = ROOT / "configs/gemini-da921x-runtime-preflight-ledger.fragment"
PROFILE = "da921x-runtime-preflight-ledger"
PARENT = "da921x-lk-clock-readonly-provider"
EXPECTED_HASHES = {
    PATCH: "5e920076e0f2308b07d128ed382b7b0c042511dd054889b1cc9c0344ec85dbe7",
    FRAGMENT: "8ab4032a4c49014c5aa4aaa08f2805946502ca37992d650e91b7185685e0eddc",
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
        require(
            (actual_old, actual_new) == (declared_old, declared_new),
            f"malformed patch hunk {hunk_count}",
        )
    require(hunk_count == 13, "unexpected patch hunk count")


def validate_contract(contract: dict) -> None:
    require(contract["status"] == "candidate-validated-deployment-pending", "wrong status")
    require(contract["profile"] == PROFILE, "profile changed")
    require(contract["parent_profile"] == PARENT, "parent changed")
    require(
        contract["kernel_release"] == "7.1.3-gemini-da921x-preflight-rt",
        "kernel release changed",
    )
    trigger = contract["trigger"]
    require(
        trigger == {
            "token": "run-readonly-preflight-20260818-a",
            "accepted_requests": 1,
            "invalid_token_i2c_transfers": 0,
            "repeated_token_i2c_transfers": 0,
            "precondition_failure_i2c_transfers": 0,
            "required_state": "idle",
            "success_state": "passed",
            "failure_state": "failed",
        },
        "trigger contract changed",
    )
    ledger = contract["ledger"]
    require(ledger["capacity"] == 32, "ledger capacity changed")
    require(ledger["pretrigger_count"] == 20, "pre-trigger count changed")
    require(ledger["posttrigger_count"] == 30, "post-trigger count changed")
    require(ledger["expected_overflow"] == 0, "ledger overflow opened")
    require(len(ledger["pretrigger_sequence"]) == 20, "pre-trigger sequence length")
    require(len(ledger["trigger_sequence"]) == 10, "trigger sequence length")
    require(ledger["pretrigger_sequence"] == [
        "69:05", "69:06", "69:47", "68:d3", "68:5e", "68:d9", "68:da",
        "69:05", "69:06", "69:47", "68:d3", "68:5e", "68:d9", "68:da",
        "68:5d", "68:5e", "68:d7", "68:5d", "68:d9", "68:5e",
    ], "pre-trigger sequence changed")
    require(ledger["trigger_sequence"] == [
        "68:56", "68:51", "68:5e", "68:d9", "68:da",
        "68:56", "68:51", "68:5e", "68:d9", "68:da",
    ], "trigger sequence changed")
    require(all(value == 0 for value in contract["forbidden"].values()),
            "forbidden action opened")
    require(contract["cpu_policy"]["cpu_requests"] == 0, "CPU request opened")
    require(contract["decision_map"]["gate6_write"] == "not-authorized",
            "Gate-6 write opened")
    require(contract["decision_map"]["cpu8_cpu9_admission"] == "closed",
            "CPU8/CPU9 admission opened")


def validate_sources(patch_text: str, fragment: str) -> None:
    added = additions(patch_text)
    c_diff = patch_text.split(
        "diff --git a/drivers/regulator/da9213-legacy-regulator.c", 1
    )[1]
    c_added = additions(c_diff)
    for required in (
        "CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT",
        "depends on !REGULATOR_DA9213_LEGACY_PREFLIGHT",
        "run-readonly-preflight-20260818-a",
        "static DEVICE_ATTR_RW(readonly_preflight)",
        "devm_device_add_group",
        "DA9213_LEGACY_RUNTIME_PREFLIGHT_IDLE",
        "DA9213_LEGACY_RUNTIME_PREFLIGHT_RUNNING",
        "DA9213_LEGACY_RUNTIME_PREFLIGHT_PASSED",
        "DA9213_LEGACY_RUNTIME_PREFLIGHT_FAILED",
        "safe_prestate=%u register_data_writes=0",
    ):
        require(required in added, f"source missing: {required}")

    require(
        patch_text.count(
            "-#if IS_ENABLED(CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT)"
        ) == 7,
        "automatic/common guard partition changed",
    )
    require(
        c_added.count("da9213_legacy_preflight_sample(chip)") == 1,
        "runtime trigger must call the ten-read sample exactly once",
    )
    store = c_added.split("static ssize_t readonly_preflight_store", 1)[1]
    store = store.split("static DEVICE_ATTR_RW", 1)[0]
    ordered = (
        "sysfs_streq",
        "mutex_lock",
        "DA9213_LEGACY_RUNTIME_PREFLIGHT_IDLE",
        "chip->observation.valid",
        "DA9213_LEGACY_READ_REGISTRATION] != 2",
        "DA9213_LEGACY_READ_OBSERVER] != 4",
        "DA9213_LEGACY_READ_PREFLIGHT])",
        "DA9213_LEGACY_RUNTIME_PREFLIGHT_RUNNING",
        "da9213_legacy_preflight_sample(chip)",
        "DA9213_LEGACY_RUNTIME_PREFLIGHT_PASSED",
    )
    positions = [store.find(token) for token in ordered]
    require(all(position >= 0 for position in positions), "trigger guard missing")
    require(positions == sorted(positions), "trigger guard order changed")
    require("-EALREADY" in store and "-EPROTO" in store,
            "one-shot or precondition refusal missing")

    for forbidden in (
        "i2c_master_send(",
        "i2c_smbus_write",
        "regmap_write(",
        "regmap_update_bits(",
        ".set_voltage_sel",
        ".enable =",
        ".disable =",
        "cpu_up(",
        "cpu_down(",
        "msgs[0].buf[1]",
        "PAGE_CON",
    ):
        require(forbidden not in c_added, f"source opens forbidden boundary: {forbidden}")

    required_fragment = (
        "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y",
        "CONFIG_I2C_MT65XX_GEMINI_ENTRY_LEDGER=y",
        "# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set",
        "CONFIG_REGULATOR_DA9213_LEGACY_RUNTIME_PREFLIGHT=y",
        'CONFIG_LOCALVERSION="-gemini-da921x-preflight-rt"',
    )
    for line in required_fragment:
        require(fragment.count(line) == 1, f"fragment missing or duplicates: {line}")


def reject_mutations(contract: dict, patch_text: str, fragment: str) -> int:
    mutations = []
    changed = copy.deepcopy(contract)
    changed["trigger"]["accepted_requests"] = 2
    mutations.append(("repeat", lambda: validate_contract(changed)))
    changed = copy.deepcopy(contract)
    changed["trigger"]["invalid_token_i2c_transfers"] = 1
    mutations.append(("invalid-token-transfer", lambda: validate_contract(changed)))
    changed = copy.deepcopy(contract)
    changed["ledger"]["pretrigger_count"] = 19
    mutations.append(("pre-count", lambda: validate_contract(changed)))
    changed = copy.deepcopy(contract)
    changed["ledger"]["posttrigger_count"] = 29
    mutations.append(("post-count", lambda: validate_contract(changed)))
    changed = copy.deepcopy(contract)
    changed["ledger"]["trigger_sequence"].pop()
    mutations.append(("sequence", lambda: validate_contract(changed)))
    changed = copy.deepcopy(contract)
    changed["forbidden"]["automatic_preflight_reads"] = 10
    mutations.append(("automatic", lambda: validate_contract(changed)))
    changed = copy.deepcopy(contract)
    changed["decision_map"]["gate6_write"] = "authorized"
    mutations.append(("write", lambda: validate_contract(changed)))
    mutations.extend([
        ("token-compare", lambda: validate_sources(
            patch_text.replace("sysfs_streq", "strcmp", 1), fragment)),
        ("one-shot", lambda: validate_sources(
            patch_text.replace("-EALREADY", "-EAGAIN", 1), fragment)),
        ("phase", lambda: validate_sources(
            patch_text.replace("DA9213_LEGACY_READ_OBSERVER] != 4",
                               "DA9213_LEGACY_READ_OBSERVER] != 3", 1), fragment)),
        ("fragment", lambda: validate_sources(
            patch_text,
            fragment.replace(
                "# CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT is not set",
                "CONFIG_REGULATOR_DA9213_LEGACY_PREFLIGHT=y", 1))),
    ])

    rejected = 0
    for name, mutation in mutations:
        try:
            mutation()
        except (ValidationError, IndexError):
            rejected += 1
        else:
            raise ValidationError(f"unsafe mutation accepted: {name}")
    return rejected


def main() -> None:
    for path, expected in EXPECTED_HASHES.items():
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        require(actual == expected, f"checksum changed: {path.relative_to(ROOT)}")

    patch_text = PATCH.read_text(encoding="utf-8")
    fragment = FRAGMENT.read_text(encoding="utf-8")
    validate_patch_hunks(patch_text)
    validate_sources(patch_text, fragment)

    series = [
        line.strip() for line in (ROOT / "patches/series").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]
    require(series[-3:] == [
        "v7.1.3/0283-i2c-mediatek-add-bounded-I2C6-entry-ledger.patch",
        "v7.1.3/0284-regulator-observe-legacy-DA921x-write-preflight.patch",
        "v7.1.3/0285-regulator-trigger-legacy-DA921x-read-only-preflight.patch",
    ], "runtime preflight is not the canonical tail")

    manifest = json.loads((ROOT / "kernel/manifest.json").read_text())
    profiles = manifest["config"]["profiles"]
    require(profiles[PROFILE]["base"] == profiles[PARENT]["base"],
            "profile base changed")
    require(profiles[PROFILE]["fragments"] ==
            profiles[PARENT]["fragments"] +
            ["configs/gemini-da921x-runtime-preflight-ledger.fragment"],
            "profile is not an exact parent extension")

    contract = json.loads((EXPERIMENT / "contract.json").read_text())
    validate_contract(contract)
    rejected = reject_mutations(contract, patch_text, fragment)

    print("validation=mainline-da921x-runtime-preflight-ledger")
    print(f"profile={PROFILE}")
    print("kernel_release=7.1.3-gemini-da921x-preflight-rt")
    print("pretrigger_transfers=20")
    print("posttrigger_transfers=30")
    print("accepted_trigger_requests=1")
    print("automatic_preflight_reads=0")
    print("register_data_write_operations=0")
    print("CPU8_CPU9_admission=closed")
    print(f"unsafe_mutations_rejected={rejected}")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
