#!/usr/bin/env python3
"""Validate generated source-derived CPU8 admission code."""

from __future__ import annotations

import argparse
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"FAIL: {message}")


def text(root: Path, relative: str) -> str:
    path = root / relative
    require(path.is_file() and not path.is_symlink(), f"exact file: {relative}")
    return path.read_text(encoding="utf-8")


def validate_production(root: Path) -> None:
    header = text(root, "arch/arm64/include/asm/mt6797_a72_membership.h")
    source = text(root, "arch/arm64/kernel/mt6797_a72_membership.c")
    kconfig = text(root, "arch/arm64/Kconfig.platforms")
    for token in (
        "#define MT6797_A72_A36_PRESTATE_ABI 2",
        "mt6797_a72_membership_derive_cpu8(",
        "mt6797_a72_membership_test_derive_cpu8(",
        "immutable owner-derived prestate record",
    ):
        require(token in header, f"header token: {token}")
    require(header.count("mt6797_a72_membership_derive_cpu8(") == 2,
            "derived declaration and disabled stub")
    for token in (
        "config ARM64_MT6797_A72_DERIVED_ADMISSION",
        "depends on ARM64_MT6797_A72_P24_TRANSACTION_OWNER_MODEL",
        "depends on ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR",
        "depends on ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER",
        "this option makes no write or CPU request",
    ):
        require(token in kconfig, f"production Kconfig token: {token}")
    for token in (
        "static struct mt6797_a72_derived_workspace a72_derived_workspace;",
        "#if IS_ENABLED(CONFIG_ARM64_MT6797_A72_DERIVED_ADMISSION)",
        "*published = workspace->observation.direct;",
        "mt6797_a72_ready_token_validate(8, ready);",
        "MT6797_A72_A34_REPLAY_APPLICABLE_PRIMARY_BL31_CLEAR",
        "false, &workspace->direct);",
        "mt6797_a72_derive_cpu8_entry(&workspace->direct,",
        "mt6797_a72_membership_p31_consume_attempt(",
        "mt6797_a72_membership_mint_up_token(",
        "mt6797_a72_derive_cpu8_prestate(&workspace->direct, transaction,",
        "mt6797_a72_membership_bind_a36_prestate(",
        "cpus_read_lock();",
        "mt6797_a72_membership_test_derive_cpu8(",
        "prestate->da921x_page ||",
        "prestate->secure_sentinels_stable ||",
        "prestate->pstore_console_available ||",
        "prestate->watchdog_owned ||",
    ):
        require(token in source, f"source token: {token}")
    for forbidden in (
        "prestate->da921x_page != MT6797_A72_A36_DA921X_PAGE",
        "prestate->secure_sentinels_stable != 1",
        "prestate->pstore_console_available != 1",
        "prestate->watchdog_owned != 1",
        "prestate->da921x_page =",
        "prestate->secure_sentinels_stable =",
        "prestate->pstore_console_available =",
        "prestate->watchdog_owned =",
        "derive_cpu8(const struct mt6797_a72_direct_state_snapshot",
        "add_cpu(", "cpu_up(", "cpu_down(", "cpu_off(",
    ):
        require(forbidden not in source, f"production forbidden: {forbidden}")
    require(source.count("mt6797_a72_membership_derive_cpu8(") == 1,
            "one derived production entry")
    locked = source.index("mt6797_a72_membership_derive_cpu8_locked(")
    ready = source.index("mt6797_a72_ready_token_validate(8, ready)", locked)
    bootstrap = source.index(
        "mt6797_a72_membership_publish_bootstrap_locked(", locked)
    p31 = source.index("mt6797_a72_membership_p31_consume_attempt(", locked)
    mint = source.index("mt6797_a72_membership_mint_up_token(", locked)
    require(ready < bootstrap < p31 < mint,
            "READY then exact bootstrap then P31 then mint")
    require(source.count("*published = workspace->observation.direct;") == 1,
            "one exact published snapshot return")


def validate_tests(root: Path) -> None:
    kconfig = text(root, "arch/arm64/Kconfig")
    makefile = text(root, "arch/arm64/kernel/Makefile")
    test_source = text(
        root, "arch/arm64/kernel/mt6797_a72_derived_admission_test.c"
    )
    owner_test = text(root, "arch/arm64/kernel/mt6797_a72_membership_test.c")
    provider_test = text(root, "drivers/regulator/da9213-legacy-membership-test.c")
    require("config ARM64_MT6797_A72_DERIVED_ADMISSION_KUNIT_TEST" in kconfig,
            "derived Kconfig")
    require("select ARM64_MT6797_A72_P24_OWNER_KUNIT_TEST" in kconfig,
            "owner test dependency")
    require("select ARM64_MT6797_A72_DIRECT_STATE_COMPOSITOR" in kconfig,
            "direct-state test dependency")
    require("select ARM64_MT6797_A72_A34_ELIGIBILITY_EVALUATOR" in kconfig,
            "A34 evaluator dependency")
    require("select ARM64_MT6797_A72_DERIVED_ADMISSION" in kconfig,
            "derived admission dependency")
    require("select ARM64_MT6797_A72_BOOTSTRAP_PUBLISHER" in kconfig,
            "bootstrap publisher dependency")
    require("mt6797_a72_derived_admission_test.o" in makefile,
            "derived test object")
    for token in (
        'KUNIT_CASE(mt6797_a72_derived_success_test)',
        'KUNIT_CASE(mt6797_a72_derived_source_rejections_test)',
        'KUNIT_CASE(mt6797_a72_derived_ready_rejection_test)',
        'KUNIT_CASE(mt6797_a72_legacy_assertions_rejected_test)',
        'KUNIT_CASE(mt6797_a72_derived_repeat_rejected_test)',
        '.name = "mt6797-a72-derived-admission"',
        "a36->da921x_page, (u32)0",
        "a36->secure_sentinels_stable, (u32)0",
        "a36->pstore_console_available, (u32)0",
        "a36->watchdog_owned, (u32)0",
        "mt6797_a72_direct_source_register(",
        "mt6797_a72_membership_test_derive_cpu8(",
        "mt6797_a72_derived_reset_closed();",
        "state->source_calls, (u32)0",
        "state->source_calls, (u32)1",
        "ret, -EALREADY",
    ):
        require(token in test_source, f"test token: {token}")
    require(test_source.count("KUNIT_CASE(") == 5, "five derived cases")
    success = test_source[test_source.index(
        "mt6797_a72_derived_success_test"):
        test_source.index("mt6797_a72_expect_source_rejection")]
    require("seed_available" not in success,
            "success begins from real closed state")
    require("add_cpu(" not in test_source and "cpu_down(" not in test_source,
            "tests have no CPU operation")
    require(".watchdog_owned = 1" not in owner_test,
            "owner fixtures no watchdog assertion")
    require(".secure_sentinels_stable = 1" not in owner_test,
            "owner fixtures no secure assertion")
    require(".pstore_console_available = 1" not in owner_test,
            "owner fixtures no pstore assertion")
    require("prestate.da921x_page = MT6797_A72_A36_DA921X_PAGE" not in
            owner_test, "owner fixture no prestate page assertion")
    require(".da921x_page = MT6797_A72_A36_DA921X_PAGE" in owner_test,
            "owner provider proof retains page field")
    require(".watchdog_owned = 1" not in provider_test,
            "provider fixtures no watchdog assertion")
    require(".secure_sentinels_stable = 1" not in provider_test,
            "provider fixtures no secure assertion")
    require(".pstore_console_available = 1" not in provider_test,
            "provider fixtures no pstore assertion")
    require(".da921x_page = MT6797_A72_A36_DA921X_PAGE" not in provider_test,
            "provider fixtures no page assertion")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("production", "tests"), required=True)
    args = parser.parse_args()
    root = args.source_root.resolve()
    validate_production(root)
    if args.stage == "tests":
        validate_tests(root)
    print("validation=mt6797-a72-derived-admission-source")
    print(f"stage={args.stage}")
    print("derived_production_entries=1")
    print("ready_before_bootstrap=true")
    print("bootstrap_publications=1")
    print("production_source_snapshots=1")
    print("caller_identity_words=0")
    print("caller_page_recovery_assertions=0")
    print("cpu_request_call_sites=0")
    print("cpu_off_call_sites=0")
    if args.stage == "tests":
        print("derived_kunit_cases=5")
        print("success_starts_closed=true")
    print("result=pass")


if __name__ == "__main__":
    main()
