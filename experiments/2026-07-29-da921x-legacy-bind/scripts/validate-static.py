#!/usr/bin/env python3
"""Validate the Gate 2 DA921x identification-only integration."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PATCH_DIR = ROOT / "patches" / "v7.1.3"
BINDING_PATCH = PATCH_DIR / (
    "0123-dt-bindings-regulator-add-legacy-direct-address-DA92.patch"
)
DRIVER_PATCH = PATCH_DIR / (
    "0124-regulator-add-read-only-legacy-DA921x-identification.patch"
)
BOARD_PATCH = PATCH_DIR / (
    "0125-arm64-dts-mediatek-describe-Gemini-legacy-DA9214.patch"
)
PROFILE = ROOT / "configs" / "gemini-da921x-legacy-bind.fragment"
MANIFEST = ROOT / "kernel" / "manifest.json"
SERIES = ROOT / "patches" / "series"
CONTRACT_VALIDATOR = (
    ROOT
    / "experiments"
    / "2026-07-29-da921x-legacy-driver-contract"
    / "scripts"
    / "validate-contract.py"
)

EXPECTED_SAMPLES = [
    ("DA9213_LEGACY_PAGE2", "05", "d9"),
    ("DA9213_LEGACY_PAGE2", "06", "d0"),
    ("DA9213_LEGACY_PAGE2", "47", "c0"),
    ("DA9213_LEGACY_PRIMARY", "d3", "1f"),
    ("DA9213_LEGACY_PRIMARY", "5e", "00"),
    ("DA9213_LEGACY_PRIMARY", "d9", "46"),
    ("DA9213_LEGACY_PRIMARY", "da", "46"),
]
EXPECTED_TAIL = [
    "v7.1.3/0123-dt-bindings-regulator-add-legacy-direct-address-DA92.patch",
    "v7.1.3/0124-regulator-add-read-only-legacy-DA921x-identification.patch",
    "v7.1.3/0125-arm64-dts-mediatek-describe-Gemini-legacy-DA9214.patch",
]


class ValidationError(RuntimeError):
    """A contract invariant was violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def added_file(patch: Path, target: str) -> str:
    lines: list[str] = []
    active = False
    marker = f"diff --git a/{target} b/{target}"
    for line in patch.read_text(encoding="utf-8").splitlines():
        if line.startswith("diff --git "):
            active = line == marker
            continue
        if active and line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    require(lines, f"{patch.name} does not add expected content for {target}")
    return "\n".join(lines) + "\n"


def validate_driver(driver: str) -> None:
    require("#define DA9213_LEGACY_PRIMARY_ADDR\t0x68" in driver,
            "primary address is not fixed at 0x68")
    require("#define DA9213_LEGACY_PAGE2_ADDR\t0x69" in driver,
            "page2 address is not fixed at 0x69")
    require("#define DA9213_LEGACY_PASSES\t\t2" in driver,
            "probe does not require exactly two transcript passes")

    samples = re.findall(
        r"\{\s*(DA9213_LEGACY_(?:PRIMARY|PAGE2)),\s*"
        r"0x([0-9a-f]{2}),\s*0x([0-9a-f]{2})\s*\}",
        driver,
    )
    require(samples == EXPECTED_SAMPLES, "probe tuple differs from Gate 1")

    required = [
        "i2c_lock_bus(client->adapter, I2C_LOCK_ROOT_ADAPTER);",
        "i2c_unlock_bus(client->adapter, I2C_LOCK_ROOT_ADAPTER);",
        "__i2c_transfer(client->adapter, msgs, ARRAY_SIZE(msgs));",
        "msgs[0].flags = 0;",
        "msgs[0].len = 1;",
        "msgs[0].buf = &reg;",
        "msgs[1].flags = I2C_M_RD;",
        "msgs[1].len = 1;",
        "msgs[1].buf = &value;",
        "devm_i2c_new_dummy_device",
        'of_get_child_by_name(np, "regulators")',
    ]
    for token in required:
        require(token in driver, f"missing required driver token: {token}")

    require(driver.count("__i2c_transfer(") == 1,
            "driver must contain exactly one direct transfer call site")
    require(not re.search(r"(?<!_)i2c_transfer\s*\(", driver),
            "retrying i2c_transfer() is forbidden")

    forbidden = [
        "PAGE_CON",
        "regmap",
        "i2c_smbus",
        "i2c_master_send",
        "i2c_transfer_buffer_flags",
        "regulator_register",
        "devm_regulator",
        "request_irq",
        "dev_pm_ops",
        ".remove",
        ".shutdown",
        ".suspend",
        ".resume",
    ]
    for token in forbidden:
        require(token not in driver, f"forbidden driver path present: {token}")

    for compatible in (
        "dlg,da9213-legacy",
        "dlg,da9214-legacy",
        "dlg,da9215-legacy",
    ):
        require(driver.count(compatible) == 1,
                f"unexpected match-table count for {compatible}")


def validate_binding(binding: str) -> None:
    for compatible in (
        "dlg,da9213-legacy",
        "dlg,da9214-legacy",
        "dlg,da9215-legacy",
    ):
        require(compatible in binding, f"binding omits {compatible}")
    for token in (
        "Primary register-bank address. The legacy interface fixes this at",
        "Secondary register-bank address. The legacy interface fixes this at",
        "0x68.",
        "0x69.",
        "- const: primary",
        "- const: page2",
    ):
        require(token in binding, f"binding omits fixed tuple token: {token}")
    require("regulators" in binding, "binding does not describe output topology")


def validate_board(board: str) -> None:
    for token in (
        'compatible = "dlg,da9214-legacy";',
        "reg = <0x68>, <0x69>;",
        'reg-names = "primary", "page2";',
        "clock-frequency = <3400000>;",
        "mediatek,use-push-pull;",
        "pinctrl-0 = <&i2c6_pins_a>;",
    ):
        require(token in board, f"board patch omits: {token}")
    for token in ("regulators", "-supply", "a72", "cpu@"):
        require(token not in board, f"board patch exposes forbidden consumer: {token}")


def validate_repository() -> tuple[str, str, str]:
    subprocess.run(
        [sys.executable, str(CONTRACT_VALIDATOR)],
        cwd=ROOT,
        check=True,
    )

    binding = added_file(
        BINDING_PATCH,
        "Documentation/devicetree/bindings/regulator/dlg,da9213-legacy.yaml",
    )
    driver = added_file(
        DRIVER_PATCH,
        "drivers/regulator/da9213-legacy-regulator.c",
    )
    board = added_file(
        BOARD_PATCH,
        "arch/arm64/boot/dts/mediatek/mt6797-gemini-pda.dts",
    )
    validate_binding(binding)
    validate_driver(driver)
    validate_board(board)

    profile = PROFILE.read_text(encoding="utf-8")
    for token in (
        "CONFIG_REGULATOR_DA9213_LEGACY=y",
        "# CONFIG_REGULATOR_DA9211 is not set",
        "# CONFIG_I2C_CHARDEV is not set",
        "# CONFIG_MTK_MT6797_A72_POWER is not set",
        "# CONFIG_I2C_MT65XX_ORION_DIAGNOSTIC is not set",
        "# CONFIG_I2C_MT65XX_QUASAR_DIAGNOSTIC is not set",
        "# CONFIG_I2C_MT65XX_FERMI_DIAGNOSTIC is not set",
        "maxcpus=8",
    ):
        require(token in profile, f"profile omits isolation token: {token}")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    profile_data = manifest["config"]["profiles"].get("da921x-legacy-bind")
    require(profile_data is not None, "manifest omits da921x-legacy-bind")
    require("patch_series" not in profile_data,
            "Gate 2 profile must use the canonical series")
    require(str(PROFILE.relative_to(ROOT)) in profile_data["fragments"],
            "manifest profile omits its isolation fragment")

    series = [
        line.strip()
        for line in SERIES.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    require(series[-3:] == EXPECTED_TAIL, "canonical series has wrong Gate 2 tail")
    return binding, driver, board


def self_test(binding: str, driver: str, board: str) -> None:
    mutations = [
        ("probe data write", driver + "\nregmap_write(map, 0, 0);\n",
         validate_driver),
        ("retrying transfer", driver.replace("__i2c_transfer", "i2c_transfer", 1),
         validate_driver),
        ("two-byte pointer write", driver.replace("msgs[0].len = 1;",
                                                  "msgs[0].len = 2;", 1),
         validate_driver),
        ("wrong page2 address", driver.replace(
            "#define DA9213_LEGACY_PAGE2_ADDR\t0x69",
            "#define DA9213_LEGACY_PAGE2_ADDR\t0x6a",
            1,
        ), validate_driver),
        ("provider-bearing board", board + "\nregulators { };\n",
         validate_board),
        ("wrong binding tuple", binding.replace("0x69.", "0x6a.", 1),
         validate_binding),
    ]
    for name, mutated, validator in mutations:
        try:
            validator(mutated)
        except ValidationError:
            continue
        raise ValidationError(f"negative self-test was not rejected: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="also prove representative unsafe mutations are rejected",
    )
    args = parser.parse_args()
    try:
        binding, driver, board = validate_repository()
        if args.self_test:
            self_test(binding, driver, board)
    except (OSError, KeyError, ValidationError, subprocess.CalledProcessError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: Gate 2 static integration contract")
    if args.self_test:
        print("PASS: unsafe mutation rejection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
