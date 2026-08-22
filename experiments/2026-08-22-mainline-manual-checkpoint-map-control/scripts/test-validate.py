#!/usr/bin/env python3
"""Reject unsafe mutations of the manual-checkpoint mapping control."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
SPEC = importlib.util.spec_from_file_location(
    "map_validator", SCRIPT_DIR / "validate.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
PATCH = ROOT / "patches/v7.1.3/0330-pstore-compare-Gemini-ramoops-mapping-models.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rejected(text: str) -> bool:
    try:
        VALIDATOR.validate_patch(text)
    except (AssertionError, ValueError):
        return True
    return False


def main() -> None:
    original = PATCH.read_text(encoding="utf-8")
    VALIDATOR.validate_patch(original)
    mutations = (
        original.replace(
            "-- \n2.39.5",
            "Signed-off-by: Synthetic <nobody@example.invalid>\n-- \n2.39.5",
            1,
        ),
        original.replace("@@ -174,6 +174,21 @@", "@@ -174,6 +174,22 @@", 1),
        original.replace("\tdefault n", "\tdefault y", 1),
        original.replace(
            "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_PREFIX_CONTROL=y",
            "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y",
            1,
        ),
        original.replace(f"#ifdef CONFIG_{VALIDATOR.MODE}", "#if 1", 1),
        original.replace("readl(ledger)", "writel(0, ledger)", 1),
        original.replace("pfn_valid(start >> PAGE_SHIFT)", "true", 1),
        original.replace("persistent_ram_vmap(start, sizeof(*buffer),", "ioremap(start,", 1),
        original.replace("MEM_TYPE_WCOMBINE", "MEM_TYPE_NORMAL", 1),
        original.replace("READ_ONCE(buffer->sig)", "0", 1),
        original.replace("atomic_read(&buffer->start)", "0", 1),
        original.replace("vunmap(vaddr - offset_in_page(start));", "cpu_up(8);", 1),
        original.replace("gemini_prb_capture_map_control(ledger);", "gemini_prb_write(ledger, NULL);", 1),
        original.replace("goto out;", "return true;", 1),
        original.replace(
            'gemini_prb_map_reason = "both-empty";',
            'gemini_prb_map_reason = "ramoops-empty-parallel-all-ones";',
            1,
        ),
        original.replace(
            "GEMINI_MANUAL_CHECKPOINT_MAP_CONTROL_V1",
            "GEMINI_MANUAL_CHECKPOINT_MAP_CONTROL_WRONG",
            1,
        ),
        original.replace("rr=%u pr=3 w=0", "rr=%u pr=3 w=1", 1),
    )
    require(all(text != original for text in mutations), "a mutation did not alter patch")
    escaped = [index for index, text in enumerate(mutations, 1) if not rejected(text)]
    require(not escaped, f"unsafe mutations escaped: {escaped}")
    print("validation=mainline-manual-checkpoint-map-control-mutations")
    print(f"unsafe_mutations_rejected={len(mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
