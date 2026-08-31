#!/usr/bin/env python3
"""Apply the exact isolation held-result contract repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


BINDER = Path("drivers/soc/mediatek/mt6797-a72-binder.c")
BINDER_TEST = Path("drivers/soc/mediatek/mt6797-a72-binder-test.c")
PARENT_SHA256 = {
    BINDER: "d8df87d32b6bfda42b84de99bf49fc87a0c914d8b9420d3496b91b0cc4bbf66b",
    BINDER_TEST: "97320d7779f98ba15b943515c02e804984eef91a2f5f67f24b47102ca228aea3",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected one occurrence, found {count}")
    return text.replace(old, new)


def verify_parent(root: Path) -> None:
    for relative, expected in PARENT_SHA256.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"parent file is absent or unsafe: {relative}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(
                f"parent checksum changed for {relative}: {actual} != {expected}"
            )


def apply(root: Path) -> None:
    verify_parent(root)
    binder_path = root / BINDER
    test_path = root / BINDER_TEST
    binder = binder_path.read_text(encoding="utf-8")
    test = test_path.read_text(encoding="utf-8")

    binder = replace_once(
        binder,
        """if (!mt6797_a72_effect_result_shape(&binder->isolation,
\t\t\t\t\t    MT6797_A72_PLATFORM_EFFECT_ISOLATION_CLEAR, true) ||""",
        """/* Isolation remains open while P27 and provider ownership are held. */
\tif (!mt6797_a72_effect_result_shape(&binder->isolation,
\t\t\t\t\t    MT6797_A72_PLATFORM_EFFECT_ISOLATION_CLEAR,
\t\t\t\t\t    false) ||""",
        "isolation seal expectation",
    )
    test = replace_once(
        test,
        "result->sealed = state->malformed != TEST_MALFORMED_ISOLATION;",
        "result->sealed = state->malformed == TEST_MALFORMED_ISOLATION;",
        "production-shaped isolation test result",
    )

    binder_path.write_text(binder, encoding="utf-8")
    test_path.write_text(test, encoding="utf-8")
