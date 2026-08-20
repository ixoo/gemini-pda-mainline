#!/usr/bin/env python3
"""Exercise the three-patch validator against unsafe mutations."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("validate_patches.py")
SPEC = importlib.util.spec_from_file_location("same_value_patch_validator", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise SystemExit("cannot load patch validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
ROOT = Path(__file__).resolve().parents[3]
CANONICAL = ROOT / "patches/v7.1.3"


def validate_set(texts: tuple[str, ...],
                 extra: dict[str, str] | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="gemini-same-write-patches.") as tmp:
        patch_dir = Path(tmp)
        for name, text in zip(VALIDATOR.PATCHES, texts, strict=True):
            (patch_dir / name).write_text(text, encoding="utf-8")
        for name, text in (extra or {}).items():
            (patch_dir / name).write_text(text, encoding="utf-8")
        VALIDATOR.validate(patch_dir)


def changed(texts: tuple[str, ...], index: int,
            old: str, new: str) -> tuple[str, ...]:
    require_count = texts[index].count(old)
    if require_count != 1:
        raise SystemExit(f"mutation anchor count changed: {old}: {require_count}")
    candidate = list(texts)
    candidate[index] = candidate[index].replace(old, new, 1)
    return tuple(candidate)


def main() -> None:
    texts = tuple((CANONICAL / name).read_text(encoding="utf-8")
                  for name in VALIDATOR.PATCHES)
    validate_set(texts)
    mutations: list[tuple[tuple[str, ...], dict[str, str] | None]] = [
        (changed(texts, 0,
                 "gemini-mainline@example.invalid",
                 "wrong@example.invalid"), None),
        (changed(texts, 0,
                 "Subject: [PATCH 1/3]",
                 "Subject: [PATCH]"), None),
        (changed(texts, 1,
                 "---\n drivers/regulator/Kconfig",
                 "Signed-off-by: Synthetic <nobody@example.invalid>\n---\n"
                 " drivers/regulator/Kconfig"), None),
        (changed(texts, 0,
                 "+\tu8 second_byte;",
                 "+\tu8 changed_byte;"), None),
        (changed(texts, 1,
                 "+\tu8 payload[2] = { 0xda, 0x46 };",
                 "+\tu8 payload[2] = { 0xda, 0x45 };"), None),
        (changed(texts, 1,
                 "+\ti2c_lock_bus(adapter, I2C_LOCK_ROOT_ADAPTER);",
                 "+\t/* root lock removed */"), None),
        (changed(texts, 1,
                 "+\tret = da9213_legacy_same_value_write(adapter, address, ops, result);",
                 "+\tret = da9213_legacy_same_value_write(adapter, address, ops, result);\n"
                 "+\tret = da9213_legacy_same_value_write(adapter, address, ops, result);"),
         None),
        (changed(texts, 1,
                 "+\t.transfer = __i2c_transfer,",
                 "+\t.transfer = i2c_transfer,"), None),
        (changed(texts, 2,
                 "+\tKUNIT_CASE(da9213_same_value_invalid_execute),",
                 "+\t/* invalid-execute case removed */"), None),
        (changed(texts, 2,
                 "+#define DA9213_TEST_ADDRESS\t0x2a",
                 "+#define DA9213_TEST_ADDRESS\t0x68"), None),
        (changed(texts, 2,
                 "+/* Hardware-free coverage for the DA921x same-value-write sequence. */",
                 "+i2c_add_adapter(&adapter);"), None),
        (changed(texts, 0,
                 "diff --git a/drivers/i2c/busses/Kconfig b/drivers/i2c/busses/Kconfig",
                 "diff --git a/drivers/i2c/busses/unexpected.c b/drivers/i2c/busses/unexpected.c"),
         None),
        (texts, {"9999-extra.patch": texts[0]}),
    ]

    rejected = 0
    for index, (candidate, extra) in enumerate(mutations, start=1):
        try:
            validate_set(candidate, extra)
        except VALIDATOR.ValidationError:
            rejected += 1
        else:
            raise SystemExit(f"unsafe normal-patch mutation accepted: {index}")
    print("validation=mainline-da921x-same-value-write-patch-validator")
    print("positive_cases=1")
    print(f"unsafe_patch_mutations_rejected={rejected}")
    print("hardware_action=none")
    print("result=pass")


if __name__ == "__main__":
    main()
