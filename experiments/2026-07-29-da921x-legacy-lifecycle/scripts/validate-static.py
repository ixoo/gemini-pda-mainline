#!/usr/bin/env python3
"""Validate the isolated Gate 3 lifecycle-oracle contract."""

from __future__ import annotations

import json
import pathlib
import re
import sys


EXPERIMENT = "2026-07-29-da921x-legacy-lifecycle"
PATCH = "v7.1.3/0126-i2c-mediatek-add-read-only-I2C6-lifecycle-oracle.patch"
PROFILE = "da921x-legacy-lifecycle"
FRAGMENT = "configs/gemini-da921x-legacy-lifecycle.fragment"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def count(text: str, token: str, wanted: int) -> None:
    actual = text.count(token)
    require(actual == wanted, f"{token!r}: expected {wanted}, found {actual}")


def validate(repository: pathlib.Path) -> None:
    manifest = json.loads((repository / "kernel/manifest.json").read_text())
    series = [
        line.strip()
        for line in (repository / "patches/series").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    patch_path = repository / "patches" / PATCH
    patch = patch_path.read_text()
    additions = "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    fragment = (repository / FRAGMENT).read_text()
    profiles = manifest["config"]["profiles"]
    profile = profiles[PROFILE]

    require(series[-1] == PATCH, "Gate 3 patch is not last in canonical series")
    require(profile["fragments"][-2:] == [
        "configs/gemini-da921x-legacy-bind.fragment",
        FRAGMENT,
    ], "Gate 3 profile does not extend the exact Gate 2 fragment stack")
    require("patch_series" not in profile, "Gate 3 profile bypasses canonical series")

    for token in (
        "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE=y",
        'CONFIG_LOCALVERSION="-gemini-da921x-life"',
        "maxcpus=8",
        "initcall_blacklist=mt6797_a72_power_driver_init",
    ):
        require(token in fragment, f"Gate 3 fragment missing {token}")

    for token in (
        "oracle_combined_pointer_reads",
        "oracle_primary_pointer_reads",
        "oracle_page2_pointer_reads",
        "oracle_write_only_messages",
        "oracle_register_data_write_messages",
        "oracle_other_transfers",
        "oracle_other_address_transfers",
        "mtk_i2c_record_lifecycle_oracle(i2c, msgs, num);",
        "msgs[0].len == 1",
        "msgs[1].len == 1",
        "msgs[i].len > 1",
        "sysfs_emit_at(",
    ):
        require(token in patch, f"Gate 3 patch missing {token}")

    for token in (
        "debugfs_create_file",
        "DEVICE_ATTR_WO",
        "DEVICE_ATTR_RW",
        ".write =",
        "copy_from_user",
        "i2c_transfer(",
        "__i2c_transfer(",
        "mtk_i2c_init_hw(i2c);",
        "writel(",
        "writew(",
        "reset_pending",
        "regulator_register",
        "devm_regulator_register",
    ):
        require(token not in additions, f"Gate 3 oracle gained forbidden path: {token}")

    count(patch, "mtk_i2c_record_lifecycle_oracle(i2c, msgs, num);", 1)
    count(patch, "CONFIG_I2C_MT65XX_GEMINI_LIFECYCLE_ORACLE", 4)
    require(
        not re.search(r"^\+.*(?:reboot|shutdown|poweroff)\b", patch, re.MULTILINE),
        "Gate 3 patch gained a boot-state action",
    )

    gate2_validator = (
        repository
        / "experiments/2026-07-29-da921x-legacy-bind/scripts/validate-static.py"
    )
    require(gate2_validator.is_file(), "Gate 2 validator is missing")


def main() -> int:
    repository = pathlib.Path(__file__).resolve().parents[3]
    try:
        validate(repository)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print("validation=da921x-legacy-lifecycle-static")
    print(f"experiment={EXPERIMENT}")
    print(f"profile={PROFILE}")
    print("observation_surface=read-only-existing-handoff-status")
    print("transfer_trigger=absent")
    print("hardware_programming_delta=absent")
    print("provider=absent")
    print("a72_request=absent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
