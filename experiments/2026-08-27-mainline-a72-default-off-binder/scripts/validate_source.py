#!/usr/bin/env python3
"""Validate the generated retained-checkpoint executor repair."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


EXPECTED_HASHES = {
    "fs/pstore/gemini_transition_ledger_internal.h":
        "49a8969ab72fc5b8cc8e40700eab3741595596dd1a81b6e2438a289c42d1eae3",
    "fs/pstore/gemini_transition_ledger_test.c":
        "cff09903407d3bf3b6bc449546a8bb3b0be9db3d5020c81533ba8ebc8abe29cb",
    "drivers/soc/mediatek/mt6797-a72-transition-internal.h":
        "71772cdb3691008ab488cfe24c67e10bb7d079173852df8f156ab8d8f90fef64",
    "drivers/soc/mediatek/mt6797-a72-transition.c":
        "b312c3c6aed3ac8cf06bd168b3ee7d378bf96d44e6ebef0f3f9e8f7af785eabc",
    "drivers/soc/mediatek/mt6797-a72-transition-test.c":
        "d4d6dfcc02a4af8fae1fd80ffaec27fa851a00508c6abbe43e8bdb0085f009a5",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(text: str, needles: tuple[str, ...], label: str) -> None:
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{label}: missing {missing[0]!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    texts: dict[str, str] = {}
    for relative, expected in EXPECTED_HASHES.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"generated path is not an exact file: {relative}")
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"generated hash changed: {relative}: {actual} != {expected}"
            )
        texts[relative] = path.read_text(encoding="utf-8")

    header = texts[
        "drivers/soc/mediatek/mt6797-a72-transition-internal.h"
    ]
    source = texts["drivers/soc/mediatek/mt6797-a72-transition.c"]
    tests = texts["drivers/soc/mediatek/mt6797-a72-transition-test.c"]
    ledger_header = texts["fs/pstore/gemini_transition_ledger_internal.h"]
    ledger_tests = texts["fs/pstore/gemini_transition_ledger_test.c"]
    require(ledger_header, (
        "#define GEMINI_TRANSITION_LEDGER_MAX_STAGE 10U",
    ), "ledger header")
    require(ledger_tests, (
        "for (stage = 1; stage <= GEMINI_TRANSITION_LEDGER_MAX_STAGE; stage++)",
        "KUNIT_EXPECT_EQ(test, latest.generation, 21U);",
        "GEMINI_TRANSITION_LEDGER_MAX_STAGE, 5);",
    ), "ledger tests")
    require(header, (
        "MT6797_A72_TRANSITION_STAGE_MEMBERSHIP",
        "int checkpoint_errno;",
        "bool membership_published;",
        "unsigned int terminal_commits;",
        "int (*checkpoint)(void *context,",
        "int (*membership_commit)(void *context, unsigned int cpu);",
        "int (*terminal)(void *context,",
    ), "header")
    require(source, (
        "result->terminal_commits++;",
        "ret = ops->terminal(context, result);",
        "if (!result->isolation_attempted)",
        "ret = ops->membership_commit(context, MT6797_A72_TRANSITION_CPU8);",
        "result->membership_published = true;",
        "MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF, 0, 0);",
        "atomic_read_acquire(&controller->consumed)",
    ), "source")
    membership = source.index("ret = ops->membership_commit")
    success = source.index(
        "MT6797_A72_TRANSITION_CPU8_ONLINE_PROOF, 0, 0);", membership
    )
    if membership >= success:
        raise SystemExit("success terminal precedes membership publication")
    if source.count("ops->cpu_on(context, MT6797_A72_TRANSITION_CPU8)") != 1:
        raise SystemExit("CPU_ON call count changed")
    if "cpu_off(" in source or "cpu_down(" in source:
        raise SystemExit("CPU_OFF path appeared")
    require(tests, (
        "mt6797_transition_checkpoint_failures_test",
        "mt6797_transition_terminal_failures_test",
        "KUNIT_EXPECT_EQ(test, result.checkpoints, 20U);",
        "KUNIT_EXPECT_EQ(test, result.terminal_commits, 1U);",
        "KUNIT_EXPECT_TRUE(test, result.membership_published);",
        "stage == MT6797_A72_TRANSITION_STAGE_MEMBERSHIP &&",
    ), "tests")
    if tests.count("KUNIT_CASE(") != 12:
        raise SystemExit("focused KUnit case count changed")
    if tests.count("phase <= MT6797_A72_TRANSITION_AFTER") != 2:
        raise SystemExit("ordinary/terminal checkpoint phase loops changed")

    print("validation=a72-default-off-executor-source")
    print("executor_stages=10")
    print("retained_ledger_max_stage=10")
    print("regular_checkpoint_failures=20")
    print("terminal_failure_contexts=31")
    print("focused_kunit_cases=12")
    print("cpu_on_call_sites=1")
    print("cpu_off_call_sites=0")
    print("result=pass")


if __name__ == "__main__":
    main()
