#!/usr/bin/env python3
"""Apply the exact CPU8 SRAM selector-mask contract repair."""

from __future__ import annotations

import hashlib
from pathlib import Path


BINDER = Path("drivers/soc/mediatek/mt6797-a72-binder.c")
BINDER_TEST = Path("drivers/soc/mediatek/mt6797-a72-binder-test.c")
SOURCE_FILES = (BINDER, BINDER_TEST)
PARENT_SHA256 = {
    BINDER: "b73e396fb09f7849772fb9c13be5e64916a642de9d593e2cde826f59cadacae5",
    BINDER_TEST: "6d27466ed6e9365d4512be6ac611fa2e486774568cdd42a02836321dc3253ed9",
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
        """\tif (sram->selector_first == MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_FIRST;
\tif (sram->selector_second == MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_SECOND;""",
        """\tif ((sram->selector_first & MT6797_BIGIDVFS_SRAM_SELECTOR_MASK) ==
\t    MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_FIRST;
\tif ((sram->selector_second & MT6797_BIGIDVFS_SRAM_SELECTOR_MASK) ==
\t    MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED)
\t\tmask |= MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_SECOND;""",
        "masked selector predicates",
    )

    test = replace_once(
        test,
        "#define TEST_MAX_EVENTS 96U\n",
        """#define TEST_MAX_EVENTS 96U
#define TEST_SELECTOR_STATUS BIT(22)
#define TEST_SELECTOR_LOW_MISMATCH BIT(0)
""",
        "selector test constants",
    )
    test = replace_once(
        test,
        """\tunsigned int checkpoint_fail_stage;
\tbool terminal_fails;""",
        """\tunsigned int checkpoint_fail_stage;
\tu32 selector_status;
\tu32 selector_xor;
\tbool terminal_fails;""",
        "selector test state",
    )
    test = replace_once(
        test,
        """\tresult->selector_first = MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED;
\tresult->selector_second = MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED;""",
        """\tresult->selector_first = MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED |
\t\tstate->selector_status;
\tresult->selector_second = (MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED |
\t\tstate->selector_status) ^ state->selector_xor;""",
        "selector test result",
    )
    test = replace_once(
        test,
        """static void mt6797_binder_one_shot_test(struct kunit *test)
{
\tstruct mt6797_binder_test_state *state = test->priv;
\tstruct mt6797_a72_binder_diagnostic diagnostic;
\tint ret;
""",
        """static void mt6797_binder_sram_selector_mask_test(struct kunit *test)
{
\tstruct mt6797_binder_test_state *state = test->priv;
\tstruct mt6797_a72_binder_diagnostic diagnostic;
\tu32 selector = MT6797_BIGIDVFS_SRAM_SELECTOR_EXPECTED |
\t\tTEST_SELECTOR_STATUS;
\tint ret;

\tstate->selector_status = TEST_SELECTOR_STATUS;
\tKUNIT_ASSERT_EQ(test, mt6797_binder_test_run_to_completion(state), 0);
\tmt6797_a72_binder_test_diagnostic(&state->binder, &diagnostic);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_selector_first, selector);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_selector_second, selector);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_match_mask,
\t\t\tMT6797_A72_BINDER_SRAM_REQUIRED_MASK);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_complete_attempted, 1U);

\tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
\tKUNIT_ASSERT_NOT_NULL(test, state);
\tmt6797_binder_test_active = state;
\tstate->selector_status = TEST_SELECTOR_STATUS;
\tstate->selector_xor = TEST_SELECTOR_LOW_MISMATCH;
\tmt6797_a72_binder_test_init(&state->binder, &mt6797_binder_test_ops);
\tret = mt6797_a72_binder_test_boot(&state->binder, 8,
\t\t\t\t\t  mt6797_binder_test_cpu_boot);
\tKUNIT_ASSERT_EQ(test, ret, -EPROTO);
\tmt6797_a72_binder_test_diagnostic(&state->binder, &diagnostic);
\tKUNIT_EXPECT_EQ(test, diagnostic.sram_match_mask,
\t\t\tMT6797_A72_BINDER_SRAM_REQUIRED_MASK &
\t\t\t~MT6797_A72_BINDER_SRAM_MATCH_SELECTOR_SECOND);
\tKUNIT_EXPECT_EQ(test, diagnostic.p28_complete_attempted, 0U);
\tKUNIT_EXPECT_EQ(test, state->cpu_boots, 0U);
}

static void mt6797_binder_one_shot_test(struct kunit *test)
{
\tstruct mt6797_binder_test_state *state = test->priv;
\tstruct mt6797_a72_binder_diagnostic diagnostic;
\tint ret;
""",
        "selector mask KUnit",
    )
    test = replace_once(
        test,
        """\tKUNIT_CASE(mt6797_binder_sram_diagnostic_test),
\tKUNIT_CASE(mt6797_binder_one_shot_test),""",
        """\tKUNIT_CASE(mt6797_binder_sram_diagnostic_test),
\tKUNIT_CASE(mt6797_binder_sram_selector_mask_test),
\tKUNIT_CASE(mt6797_binder_one_shot_test),""",
        "selector mask KUnit case",
    )

    binder_path.write_text(binder, encoding="utf-8")
    test_path.write_text(test, encoding="utf-8")
