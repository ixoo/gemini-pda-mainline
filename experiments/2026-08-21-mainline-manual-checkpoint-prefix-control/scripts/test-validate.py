#!/usr/bin/env python3
"""Reject unsafe mutations of the manual-checkpoint prefix-reason patch."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prefix_validator", SCRIPT_DIR / "validate.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
PATCH = ROOT / "patches/v7.1.3/0329-pstore-report-Gemini-manual-checkpoint-prefix-reason.patch"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def rejected(text: str) -> bool:
    try:
        VALIDATOR.validate_patch(text)
    except AssertionError:
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
        original.replace("@@ -24,6 +24,52 @@", "@@ -24,6 +24,53 @@", 1),
        original.replace("\tdefault n", "\tdefault y", 1),
        original.replace(
            "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_STAGE_CONTROL=y",
            "PSTORE_GEMINI_PROTECTED_READBACK_MANUAL_CONTROL=y",
            1,
        ),
        original.replace(f"#ifdef CONFIG_{VALIDATOR.MODE}", "#if 1", 1),
        original.replace("u32 signature = readl(slot);", "u32 signature = writel(0, slot);", 1),
        original.replace(
            "u32 start = readl((u8 __iomem *)slot + 4);",
            "u32 start = readb((u8 __iomem *)slot + 4);",
            1,
        ),
        original.replace(
            'gemini_prb_prefix_reason = "nonzero-start";',
            'gemini_prb_prefix_reason = "bad-signature";',
            1,
        ),
        original.replace(
            "gemini_prb_prefix_signature = signature;",
            "gemini_prb_prefix_signature = 0;",
            1,
        ),
        original.replace(
            "gemini_prb_capture_prefix(checkpoint, i, true, slot);",
            "(void)slot;",
            1,
        ),
        original.replace(
            "else if (!gemini_prb_slot_empty(slot))",
            "else if (!gemini_prb_slot_exact(slot, gemini_prb_records[0]))",
            1,
        ),
        original.replace(
            "GEMINI_MANUAL_CHECKPOINT_PREFIX_V1",
            "GEMINI_MANUAL_CHECKPOINT_PREFIX_WRONG",
            1,
        ),
        original.replace("reads=3\\n", "reads=4\\n", 1),
        original.replace(
            "gemini_prb_prefix_checkpoint = checkpoint;",
            "cpu_up(8);",
            1,
        ),
        original.replace(
            "gemini_prb_prefix_start = start;",
            "memcpy_toio(slot, &start, sizeof(start));",
            1,
        ),
        original.replace(
            "gemini_prb_prefix_size = size;",
            "i2c_transfer(NULL, NULL, 0);",
            1,
        ),
    )
    require(all(text != original for text in mutations), "a mutation did not alter patch")
    escaped = [index for index, text in enumerate(mutations, 1) if not rejected(text)]
    require(not escaped, f"unsafe mutations escaped: {escaped}")
    print("validation=mainline-manual-checkpoint-prefix-control-mutations")
    print(f"unsafe_mutations_rejected={len(mutations)}")
    print("device_access=none")
    print("hardware_write=none")
    print("result=pass")


if __name__ == "__main__":
    main()
