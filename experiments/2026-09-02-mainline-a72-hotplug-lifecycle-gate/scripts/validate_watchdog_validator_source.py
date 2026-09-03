#!/usr/bin/env python3
"""Validate the disconnected read-only MTK watchdog validator source."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\b{re.escape(name)}\s*\([^;]*?\)\s*\{{", source,
                      re.S)
    require(match is not None, f"missing function: {name}")
    depth = 0
    for offset in range(match.end() - 1, len(source)):
        if source[offset] == "{":
            depth += 1
        elif source[offset] == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():offset + 1]
    raise ValueError(f"unterminated function: {name}")


def validate(root: pathlib.Path, require_tests: bool) -> None:
    header = (root / "include/linux/mtk_wdt.h").read_text()
    source = (root / "drivers/watchdog/mtk_wdt.c").read_text()
    psci = (root / "arch/arm64/kernel/mt6797_psci.c").read_text()

    for token in (
        "struct mtk_wdt_recovery_validation {",
        "u64 identity;", "u32 mode;", "u32 length;", "u32 owned;",
        "int mtk_wdt_recovery_validate(",
    ):
        require(token in header, f"public contract missing: {token}")
    require(header.count("mtk_wdt_recovery_validate(") == 2,
            "enabled declaration or disabled stub changed")
    stub = header.split("static inline int mtk_wdt_recovery_validate(", 1)[1]
    require("*validation = (struct mtk_wdt_recovery_validation){};" in stub and
            "return -EOPNOTSUPP;" in stub,
            "disabled validator stub changed")

    helper = function_body(source, "mtk_wdt_recovery_validate_owner")
    require("if (!owner->owned)" in helper and "return -ENODATA;" in helper,
            "software ownership gate missing")
    require("if (identity != owner->identity)" in helper and
            "return -EACCES;" in helper,
            "identity equality gate missing")
    require(helper.count("ops->read(") == 2 and
            "WDT_MODE" in helper and "WDT_LENGTH" in helper,
            "validator read budget changed")
    require("WDT_LENGTH_TIMEOUT_MASK" in helper and
            "WDT_MODE_RECOVERY_MASK" in helper and
            "WDT_MODE_EN | WDT_MODE_AUTO_START" in helper,
            "hardware configuration gate missing")
    for token in ("ops->write", "iowrite", "writel", "WDT_RST_RELOAD",
                  "next_identity", "takeover"):
        require(token not in helper, f"validator mutation added: {token}")

    public = function_body(source, "mtk_wdt_recovery_validate")
    require("spin_lock_irqsave(&mtk_wdt->recovery_lock" in public and
            "spin_unlock_irqrestore(&mtk_wdt->recovery_lock" in public,
            "recovery lock missing")
    require(public.count("mtk_wdt_recovery_validate_owner(") == 1,
            "owner validator call count changed")
    require("EXPORT_SYMBOL_GPL(mtk_wdt_recovery_validate);" in source,
            "validator export missing")
    for token in ("iowrite", "writel", "recovery_takeover(",
                  "watchdog_ping", "next_identity"):
        require(token not in public, f"public validator mutation: {token}")

    takeover = function_body(source, "mtk_wdt_recovery_execute")
    require(takeover.count("ops->write(") == 3 and
            "WDT_LENGTH" in takeover and "WDT_MODE" in takeover and
            "WDT_RST" in takeover,
            "existing takeover write sequence changed")
    require("recovery_cancel" not in header + source and
            "recovery_refresh" not in header + source and
            "recovery_release" not in header + source,
            "watchdog owner became mutable")
    require("mtk_wdt_recovery_validate" not in psci,
            "validator connected to production")
    require("return false;" in function_body(
        psci, "mt6797_psci_cpu_can_disable"),
        "CPU disable veto opened")

    if require_tests:
        require(source.count("KUNIT_CASE(mtk_wdt_recovery_") == 7,
                "watchdog KUnit case count changed")
        for name in ("validate_success_test", "validate_rejections_test"):
            require(f"KUNIT_CASE(mtk_wdt_recovery_{name})" in source,
                    f"missing validator test: {name}")
        success = function_body(
            source, "mtk_wdt_recovery_validate_success_test")
        rejection = function_body(
            source, "mtk_wdt_recovery_validate_rejections_test")
        require("KUNIT_EXPECT_EQ(test, 2U, state.reads);" in success and
                "KUNIT_EXPECT_EQ(test, 0U, state.writes);" in success,
                "success read/write budget assertion missing")
        for error in ("-EINVAL", "-EACCES", "-ENODATA", "-EIO"):
            require(error in rejection, f"missing rejection: {error}")
        require("KUNIT_EXPECT_EQ(test, 0U, state.writes);" in rejection,
                "rejection write-free assertion missing")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=pathlib.Path, required=True)
    parser.add_argument("--require-tests", action="store_true")
    args = parser.parse_args()
    try:
        validate(args.source_root.resolve(), args.require_tests)
    except (OSError, ValueError) as exc:
        print(f"watchdog_validator_source=fail reason={exc}", file=sys.stderr)
        return 1
    print("watchdog_validator_source=pass")
    print("validation_reads=2")
    print("validation_writes=0")
    print("watchdog_mutations=0")
    print("production_callers=0")
    print("cpu_can_disable=false")
    if args.require_tests:
        print("focused_kunit_cases=2")
        print("total_watchdog_kunit_cases=7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
