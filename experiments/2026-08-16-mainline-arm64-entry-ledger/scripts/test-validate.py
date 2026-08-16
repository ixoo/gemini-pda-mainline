#!/usr/bin/env python3
"""Reject representative unsafe arm64 entry-ledger implementation mutations."""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gael_validate", SCRIPT_DIR / "validate.py")
assert spec and spec.loader
validator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = validator
spec.loader.exec_module(validator)


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"mutation source count changed: {old}")
    return text.replace(old, new)


def replace_first(text: str, old: str, new: str) -> str:
    if old not in text:
        raise AssertionError(f"mutation source missing: {old}")
    return text.replace(old, new, 1)


def main() -> None:
    patch = validator.PATCH_PATH.read_text(encoding="utf-8")
    series = validator.SERIES_PATH.read_text(encoding="utf-8")
    manifest = json.loads(validator.MANIFEST_PATH.read_text(encoding="utf-8"))
    fragment = validator.FRAGMENT_PATH.read_text(encoding="utf-8")
    validator.validate(patch, series, manifest, fragment)

    cases: list[tuple[str, str, dict, str]] = []
    cases.append((replace_once(
        patch, "\tdefault n\n+\thelp\n+\t  Write four short",
        "\tdefault y\n+\thelp\n+\t  Write four short",
    ), series, manifest, fragment))
    cases.append((replace_first(
        patch, "movk\tx9, #0x444b, lsl #16",
        "movk\tx9, #0x444c, lsl #16",
    ), series, manifest, fragment))
    cases.append((replace_once(patch, "tbnz\tx10, #0, .Lgemini_primary_done_\\@", "nop"), series, manifest, fragment))
    cases.append((replace_once(patch, "tbnz\tx10, #2, .Lgemini_primary_done_\\@", "nop"), series, manifest, fragment))
    cases.append((replace_first(patch, "mov\tx14, x9", "mov\tx0, x9"), series, manifest, fragment))
    cases.append((replace_first(
        patch, "gemini_entry_ledger_require_empty x14, .Lgemini_primary_done_\\@",
        "nop",
    ), series, manifest, fragment))
    cases.append((replace_first(patch, "dsb\tsy", "dmb\tsy"), series, manifest, fragment))
    cases.append((replace_first(patch, "0x3d3d, 0x3d3d", "0x3d3c, 0x3d3d"), series, manifest, fragment))
    cases.append((replace_once(patch, "if (i < stage)", "if (i <= stage)"), series, manifest, fragment))
    cases.append((replace_once(
        patch, "return memblock_is_region_reserved(addr, size);", "return true;",
    ), series, manifest, fragment))
    cases.append((replace_once(
        patch, "gemini_entry_checkpoint(3, true);",
        "gemini_entry_checkpoint(3, false);",
    ), series, manifest, fragment))
    cases.append((replace_once(
        patch, "gemini_entry_checkpoint(2, false);",
        "psci_cpu_on();\n+\tgemini_entry_checkpoint(2, false);",
    ), series, manifest, fragment))
    cases.append((replace_once(
        patch,
        "#ifdef CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER\n"
        "+\tif (of_machine_is_compatible",
        "#if 0\n+\tif (of_machine_is_compatible",
    ), series, manifest, fragment))
    cases.append((patch, series.replace(validator.PATCH_NAME + "\n", ""), manifest, fragment))
    cases.append((patch, series, manifest, fragment.replace(
        "# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set",
        "CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER=y",
    )))

    missing_fragment = deepcopy(manifest)
    missing_fragment["config"]["profiles"][validator.PROFILE]["fragments"].pop()
    cases.append((patch, series, missing_fragment, fragment))

    rejected = 0
    for mutated_patch, mutated_series, mutated_manifest, mutated_fragment in cases:
        try:
            validator.validate(mutated_patch, mutated_series, mutated_manifest, mutated_fragment)
        except (AssertionError, KeyError, ValueError):
            rejected += 1
        else:
            raise AssertionError(f"unsafe mutation {rejected + 1} was accepted")

    print("validation=arm64-entry-ledger-implementation-mutations")
    print(f"negative_mutations_rejected={rejected}")
    print("result=pass")


if __name__ == "__main__":
    main()
