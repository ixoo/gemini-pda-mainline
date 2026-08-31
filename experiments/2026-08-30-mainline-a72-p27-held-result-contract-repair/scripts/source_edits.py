#!/usr/bin/env python3
"""Apply the exact P27 held-result contract repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


BINDER = Path("drivers/soc/mediatek/mt6797-a72-binder.c")
BINDER_TEST = Path("drivers/soc/mediatek/mt6797-a72-binder-test.c")
PARENT_SHA256 = {
    BINDER: "c4c99901f34a3fdc1b90e424477727557410c528bbcc53911eb1565d9989d3c7",
    BINDER_TEST: "e05e2ed8cd5f515895255cd22d0539c6d6428194589329b095b4e55048fd5d0a",
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
        """static bool
mt6797_a72_effect_result_shape(const struct mt6797_a72_platform_effect_result *result,
\t\t\t       enum mt6797_a72_platform_effect_operation operation)
{
\treturn result && result->abi == MT6797_A72_PLATFORM_EFFECT_ABI &&
\t\tresult->operation == operation && result->sealed;
}
""",
        """static bool
mt6797_a72_effect_result_shape(const struct mt6797_a72_platform_effect_result *result,
\t\t\t       enum mt6797_a72_platform_effect_operation operation,
\t\t\t       bool sealed)
{
\treturn result && result->abi == MT6797_A72_PLATFORM_EFFECT_ABI &&
\t\tresult->operation == operation && result->sealed == sealed;
}
""",
        "explicit seal expectation",
    )
    binder = replace_once(
        binder,
        """if (!mt6797_a72_effect_result_shape(&binder->p27,
\t\t\t\t\t    MT6797_A72_PLATFORM_EFFECT_P27_ACQUIRE)) {""",
        """/* A successful acquire remains open while P27 ownership is held. */
\tif (!mt6797_a72_effect_result_shape(&binder->p27,
\t\t\t\t\t    MT6797_A72_PLATFORM_EFFECT_P27_ACQUIRE,
\t\t\t\t\t    false)) {""",
        "P27 acquire seal expectation",
    )
    for operation in (
        "MT6797_A72_PLATFORM_EFFECT_P27_RELEASE",
        "MT6797_A72_PLATFORM_EFFECT_ISOLATION_CLEAR",
        "MT6797_A72_PLATFORM_EFFECT_DCM_UPDATE",
    ):
        binder = replace_once(
            binder,
            f"{operation}) ||",
            f"{operation}, true) ||",
            f"sealed result expectation for {operation}",
        )

    test = replace_once(
        test,
        "result->sealed = state->malformed != TEST_MALFORMED_P27;",
        "result->sealed = state->malformed == TEST_MALFORMED_P27;",
        "production-shaped P27 test result",
    )
    test = replace_once(
        test,
        "KUNIT_EXPECT_EQ(test, diagnostic.p27_acquire_sealed, 0U);",
        "KUNIT_EXPECT_EQ(test, diagnostic.p27_acquire_sealed, 1U);",
        "malformed sealed-acquire diagnostic",
    )

    binder_path.write_text(binder, encoding="utf-8")
    test_path.write_text(test, encoding="utf-8")
