#!/usr/bin/env python3
"""Validate the exact same-version Gemian pmsg witness child."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from witness_edits import (
    ENTRY_RECORD,
    OBSERVER_DEFINE_PARENT,
    OBSERVER_INCLUDE_PARENT,
    OBSERVER_INIT_PARENT,
    PARENT_SHA256,
    PMSG_HELPER_ANCHOR,
    PMSG_INCLUDES_PARENT,
    PSCI_DEFINE_PARENT,
    PSCI_INCLUDE_PARENT,
    PSCI_PRE_SCHEDULER_PARENT,
    PSCI_TERMINAL_PARENT,
    PRE_SCHEDULER_RECORD,
    PSTORE_DECL_ANCHOR,
    TERMINAL_FAULT_RECORD,
    TERMINAL_PASS_RECORD,
    transform_mapping,
)


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate(children: dict[str, str], parents: dict[str, str], *, exact: bool) -> None:
    expected = transform_mapping(parents, verify_hashes=exact)
    require(children == expected, "child is not the exact deterministic transform")

    pmsg = children["fs/pstore/pmsg.c"]
    parent_pmsg = parents["fs/pstore/pmsg.c"]
    header = children["include/linux/pstore.h"]
    observer = children[
        "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c"
    ]
    psci = children["arch/arm64/kernel/psci.c"]

    require(pmsg.count("PMSG_MAX_KERNEL_RECORD_SIZE 256") == 1,
            "kernel record bound changed")
    require(pmsg.count("mutex_lock(&pmsg_lock)") ==
            parent_pmsg.count("mutex_lock(&pmsg_lock)") + 1 and
            pmsg.count("mutex_unlock(&pmsg_lock)") ==
            parent_pmsg.count("mutex_unlock(&pmsg_lock)") + 1,
            "pmsg writer serialization inventory changed")
    for term in ("psinfo", "psinfo->write_buf", "psinfo->name",
                 '!strcmp(psinfo->name, "ramoops")'):
        require(term in pmsg, f"backend guard changed: {term}")
    require(pmsg.count("PSTORE_TYPE_PMSG") ==
            parent_pmsg.count("PSTORE_TYPE_PMSG") + 1,
            "pmsg backend call inventory changed")
    require("persistent_ram_" not in pmsg, "helper bypasses the pstore backend")
    require(header.count("pstore_write_pmsg_kernel") == 2,
            "public helper declaration/stub inventory changed")

    records = (
        ENTRY_RECORD,
        PRE_SCHEDULER_RECORD,
        TERMINAL_PASS_RECORD,
        TERMINAL_FAULT_RECORD,
    )
    for record in records:
        require(record.endswith("\\n") and len(record.encode()) <= 256,
                f"record bound changed: {record!r}")
    require(observer.count(ENTRY_RECORD) == 1, "entry record changed")
    require(psci.count(PRE_SCHEDULER_RECORD) == 1,
            "pre-scheduler record changed")
    require(psci.count(TERMINAL_PASS_RECORD) == 1 and
            psci.count(TERMINAL_FAULT_RECORD) == 1,
            "terminal record inventory changed")
    require(observer.index("pstore_write_pmsg_kernel") <
            observer.index("proc_create("), "entry record moved after proc init")
    require(psci.index("mt6797_a72_pmsg_pre_scheduler") <
            psci.index("mt6797_a72_sc_run();"),
            "pre-scheduler record moved after scheduler")
    terminal_fn = psci.split(
        "static noinline void mt6797_a72_sc_terminal", 1
    )[1].split("static void mt6797_a72_hold_workfn", 1)[0]
    require(terminal_fn.index("passed = parent_pass") <
            terminal_fn.index("pstore_write_pmsg_kernel") <
            terminal_fn.index('pr_emerg("gemini-a72-pair-v7') <
            terminal_fn.index("mt6797_a72_regcap_emit"),
            "pre-capsule terminal order changed")
    require(terminal_fn.count("pstore_write_pmsg_kernel") == 1,
            "terminal writer call count changed")

    for marker in (
        "gemini-a72-sc-phase",
        "gemini-a72-pair-v6",
        "gemini-a72-pair-v7",
        "gemini-a72-regcap-v1",
    ):
        require(psci.count(marker) == parents["arch/arm64/kernel/psci.c"].count(marker),
                f"inherited console marker inventory changed: {marker}")

    delta = "\n".join(
        children[path] for path in sorted(children)
    )
    parent_all = "\n".join(parents[path] for path in sorted(parents))
    for pattern in (
        r"\bpsci_ops\.", r"\bcpu_(?:up|down)\s*\(",
        r"\bioremap\s*\(", r"\b(?:readl|writel)(?:_relaxed)?\s*\(",
        r"\bregulator_", r"\bclk_", r"\bsmc\b", r"\bhvc\b",
        r"\bpersistent_ram_(?:write|zap|new|free_old)\s*\(",
        r"\b(?:u|m|ms)sleep\s*\(", r"\b(?:u|m)delay\s*\(",
    ):
        require(len(re.findall(pattern, delta)) == len(re.findall(pattern, parent_all)),
                f"forbidden action entered child: {pattern}")


def synthetic_parent() -> dict[str, str]:
    return {
        "fs/pstore/pmsg.c": PMSG_INCLUDES_PARENT + PMSG_HELPER_ANCHOR + "tail\n",
        "include/linux/pstore.h": "head\n" + PSTORE_DECL_ANCHOR + "tail\n",
        "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c":
            OBSERVER_INCLUDE_PARENT + OBSERVER_DEFINE_PARENT +
            OBSERVER_INIT_PARENT + "tail\n",
        "arch/arm64/kernel/psci.c":
            PSCI_INCLUDE_PARENT + PSCI_DEFINE_PARENT +
            "static noinline void mt6797_a72_sc_terminal(bool parent_pass)\n{\n"
            "\tbool passed;\n\tpassed = parent_pass && true;\n" +
            PSCI_TERMINAL_PARENT + "\tmt6797_a72_regcap_emit(&r8);\n}\n" +
            "static void mt6797_a72_hold_workfn(struct work_struct *work)\n{\n" +
            PSCI_PRE_SCHEDULER_PARENT + "}\n",
    }


def expect_reject(name: str, children: dict[str, str], parents: dict[str, str]) -> None:
    try:
        validate(children, parents, exact=False)
    except (ValidationError, RuntimeError):
        return
    raise ValidationError(f"unsafe mutation accepted: {name}")


def self_test() -> None:
    parents = synthetic_parent()
    child = transform_mapping(parents, verify_hashes=False)
    validate(child, parents, exact=False)
    mutations: list[tuple[str, str, str]] = [
        ("record-bound", "fs/pstore/pmsg.c", "256", "512"),
        ("backend", "fs/pstore/pmsg.c", '"ramoops"', '"any"'),
        ("writer-lock", "fs/pstore/pmsg.c", "mutex_lock(&pmsg_lock);", ""),
        ("entry", "drivers/misc/mediatek/base/power/mt6797/mt_a72_transition_observer.c",
         "(void)pstore_write_pmsg_kernel", "(void)0 /* removed */;\n\t(void)pstore_write_pmsg_kernel"),
        ("pre-scheduler", "arch/arm64/kernel/psci.c",
         "mt6797_a72_pmsg_pre_scheduler", "mt6797_a72_pmsg_terminal_pass"),
        ("terminal-result", "arch/arm64/kernel/psci.c",
         "passed ?\n\t\tmt6797_a72_pmsg_terminal_pass",
         "mt6797_a72_pmsg_terminal_pass"),
        ("terminal-order", "arch/arm64/kernel/psci.c",
         "\t(void)pstore_write_pmsg_kernel(passed ?",
         "\tmt6797_a72_regcap_emit(&r8);\n"
         "\t(void)pstore_write_pmsg_kernel(passed ?"),
        ("raw-write", "fs/pstore/pmsg.c", "return ret;",
         "persistent_ram_write(NULL, buf, count);\n\treturn ret;"),
    ]
    for name, path, old, new in mutations:
        mutated = dict(child)
        require(old in mutated[path], f"self-test mutation anchor absent: {name}")
        mutated[path] = mutated[path].replace(old, new, 1)
        expect_reject(name, mutated, parents)
    print("validation=a72-pmsg-witness-definition")
    print(f"parent_paths={len(PARENT_SHA256)}")
    print(f"record_count={len((ENTRY_RECORD, PRE_SCHEDULER_RECORD, TERMINAL_PASS_RECORD, TERMINAL_FAULT_RECORD))}")
    print(f"negative_mutations={len(mutations)}")
    print("device_action=none")


def read_mapping(root: Path) -> dict[str, str]:
    return {
        path: (root / path).read_text(encoding="utf-8")
        for path in PARENT_SHA256
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--parent-root", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.source is None or args.parent_root is None:
        parser.error("--source and --parent-root are required without --self-test")
    parents = read_mapping(args.parent_root)
    children = read_mapping(args.source)
    validate(children, parents, exact=True)
    print("validation=a72-pmsg-witness-source")
    print("parent_reversal=byte-identical")
    print("changed_paths=4")
    print("retained_record_bytes_lt=1024")
    print("device_action=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
