#!/usr/bin/env python3
"""Move the MT6797 A72 membership-owner KUnit fixtures off stack."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


OWNER_CASES = (
    "mt6797_a72_owner_initial_closed",
    "mt6797_a72_owner_cpu8_denied",
    "mt6797_a72_owner_cpu9_denied",
    "mt6797_a72_owner_public_hook_denied",
    "mt6797_a72_owner_internal_hook_denied",
    "mt6797_a72_owner_non_target_invalid",
    "mt6797_a72_owner_intermediate_target_invalid",
    "mt6797_a72_owner_repeat_is_diagnostic",
    "mt6797_a72_owner_entry_snapshot_gate",
    "mt6797_a72_owner_p31_consumes_once",
    "mt6797_a72_owner_a36_rejects_without_rearm",
    "mt6797_a72_owner_a36_prestate_mutations_rejected",
    "mt6797_a72_owner_cpu9_mints_distinct_token",
    "mt6797_a72_owner_p17_cpu8_publishes_once",
    "mt6797_a72_owner_p18_cpu9_preserves_provider",
    "mt6797_a72_owner_p18_without_provider_rejected",
    "mt6797_a72_owner_p27_cpu8_preparation_once",
    "mt6797_a72_owner_p27_rejects_bad_or_cpu9_proof",
    "mt6797_a72_owner_r01_r02_provider_once",
    "mt6797_a72_owner_r02_rejects_bad_proof_or_cpu9",
    "mt6797_a72_owner_p28_cpu8_preparation_once",
    "mt6797_a72_owner_p28_rejects_bad_proof_or_cpu9",
    "mt6797_a72_owner_r03_p29_rejects_and_retires",
    "mt6797_a72_owner_r03_p29_mutations_rejected",
    "mt6797_a72_owner_binder_success_handoff",
    "mt6797_a72_owner_binder_p32_from_verifying",
    "mt6797_a72_owner_binder_clean_rejection",
    "mt6797_a72_owner_binder_p29_without_provider",
    "mt6797_a72_owner_forged_token_rejected",
    "mt6797_a72_owner_no_live_token",
)

STACK_FIELDS = {
    "before": "\tstruct owner_observation before;\n",
    "after": "\tstruct owner_observation after;\n",
    "transaction": "\tstruct mt6797_a72_transaction transaction;\n",
    "snapshot": "\tstruct mt6797_a72_owner_snapshot snapshot;\n",
}


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def function_span(text: str, name: str) -> tuple[int, int]:
    marker = f"static void {name}(struct kunit *test)\n{{"
    start = text.find(marker)
    if start < 0:
        raise SystemExit(f"function absent: {name}")
    brace = text.find("{", start)
    depth = 0
    index = brace
    quote = ""
    escaped = False
    line_comment = False
    block_comment = False
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char == "/" and next_char == "/":
            line_comment = True
            index += 1
        elif char == "/" and next_char == "*":
            block_comment = True
            index += 1
        elif char in ('"', "'"):
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return start, index + 1
        index += 1
    raise SystemExit(f"unterminated function: {name}")


def move_case_state(text: str, name: str) -> str:
    start, end = function_span(text, name)
    function = text[start:end]
    if re.search(r"\bstate\b", function):
        raise SystemExit(f"unexpected existing state identifier: {name}")

    moved = []
    for field, declaration in STACK_FIELDS.items():
        count = function.count(declaration)
        if count > 1:
            raise SystemExit(f"duplicate {field} fixture: {name}")
        if count == 1:
            function = function.replace(declaration, "", 1)
            function = re.sub(rf"\b{field}\b", f"state->{field}", function)
            moved.append(field)
    if not moved:
        raise SystemExit(f"case has no recognized stack fixture: {name}")

    opening = f"static void {name}(struct kunit *test)\n{{\n"
    function = replace_once(
        function,
        opening,
        opening +
        "\tstruct mt6797_a72_owner_test_state *state = test->priv;\n",
        f"{name} opening",
    )
    return text[:start] + function + text[end:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    path = (
        args.source_root.resolve()
        / "arch/arm64/kernel/mt6797_a72_membership_test.c"
    )
    if not path.is_file() or path.is_symlink():
        raise SystemExit("unsafe membership KUnit source")
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        """struct owner_observation {
\tstruct mt6797_a72_owner_snapshot owner;
\tstruct arm64_late_cpu_startup_snapshot p30;
};

static bool
mt6797_a72_transaction_empty(const struct mt6797_a72_transaction *transaction)
{
\tconst struct mt6797_a72_transaction empty = { };

\treturn !memcmp(transaction, &empty, sizeof(empty));
}
""",
        """struct owner_observation {
\tstruct mt6797_a72_owner_snapshot owner;
\tstruct arm64_late_cpu_startup_snapshot p30;
};

struct mt6797_a72_owner_test_state {
\tstruct owner_observation before;
\tstruct owner_observation after;
\tstruct mt6797_a72_transaction transaction;
\tstruct mt6797_a72_owner_snapshot snapshot;
};

static const struct mt6797_a72_transaction mt6797_a72_empty_transaction;

static bool
mt6797_a72_transaction_empty(const struct mt6797_a72_transaction *transaction)
{
\treturn !memchr_inv(transaction, 0, sizeof(*transaction));
}
""",
        "owner scratch and zero check",
    )
    text = replace_once(
        text,
        """static int mt6797_a72_owner_test_init(struct kunit *test)
{
\t(void)test;
\tmt6797_a72_membership_test_reset();
\treturn 0;
}
""",
        """static int mt6797_a72_owner_test_init(struct kunit *test)
{
\tstruct mt6797_a72_owner_test_state *state;

\tstate = kunit_kzalloc(test, sizeof(*state), GFP_KERNEL);
\tif (!state)
\t\treturn -ENOMEM;
\ttest->priv = state;
\tmt6797_a72_membership_test_reset();
\treturn 0;
}
""",
        "owner test init",
    )
    text = replace_once(
        text,
        "\tconst struct mt6797_a72_transaction empty_transaction = { };\n",
        "",
        "initial empty transaction",
    )
    initial_start, initial_end = function_span(
        text, "mt6797_a72_owner_initial_closed"
    )
    initial = text[initial_start:initial_end]
    initial = re.sub(r"\bempty_transaction\b",
                     "mt6797_a72_empty_transaction", initial)
    text = text[:initial_start] + initial + text[initial_end:]

    for name in OWNER_CASES:
        text = move_case_state(text, name)

    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
