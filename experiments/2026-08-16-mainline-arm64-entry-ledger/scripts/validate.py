#!/usr/bin/env python3
"""Validate the exact fail-closed Gemini arm64 entry-ledger implementation."""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[3]
PATCH_NAME = "v7.1.3/0281-arm64-add-Gemini-entry-stage-ledger.patch"
PATCH_PATH = ROOT / "patches" / PATCH_NAME
SERIES_PATH = ROOT / "patches/series"
MANIFEST_PATH = ROOT / "kernel/manifest.json"
FRAGMENT = "configs/gemini-arm64-entry-ledger.fragment"
FRAGMENT_PATH = ROOT / FRAGMENT
PROFILE = "da921x-modules-arm64-entry-ledger"
PARENT = "da921x-resource-only-provider-modules-control"
AUDIT_SCRIPTS = ROOT / "experiments/2026-08-16-mainline-arm64-entry-ledger-audit/scripts"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


record_layout = load_module("gael_record_layout", AUDIT_SCRIPTS / "record-layout.py")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def added_file(patch: str, path: str) -> str:
    start = f"diff --git a/{path} b/{path}\n"
    require(patch.count(start) == 1, f"{path} diff identity changed")
    body = patch.split(start, 1)[1]
    body = body.split("\ndiff --git ", 1)[0]
    require("new file mode 100644" in body, f"{path} is not a new regular file")
    lines = []
    in_hunk = False
    for line in body.splitlines():
        if line.startswith("@@ "):
            in_hunk = True
            continue
        if in_hunk and line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    require(lines, f"{path} has no added source")
    return "\n".join(lines) + "\n"


def diff_body(patch: str, path: str) -> str:
    start = f"diff --git a/{path} b/{path}\n"
    require(patch.count(start) == 1, f"{path} diff identity changed")
    return patch.split(start, 1)[1].split("\ndiff --git ", 1)[0]


def macro_body(source: str, name: str) -> str:
    match = re.search(
        rf"^\s*\.macro\s+{re.escape(name)}(?:\s+[^\n]+)?\n(.*?)^\s*\.endm\s*$",
        source,
        re.MULTILINE | re.DOTALL,
    )
    require(match is not None, f"assembly macro missing: {name}")
    return match.group(1)


def strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//.*", "", source)


def word_rows(body: str, operation: str) -> list[tuple[int, int]]:
    pattern = re.compile(
        rf"^\s*gemini_entry_ledger_{operation}_word "
        r"\\base, ([0-9]+), 0x([0-9a-f]{4}), 0x([0-9a-f]{4})"
        r"(?:, \\fail)?$",
        re.MULTILINE,
    )
    return [
        (int(offset), int(high, 16) << 16 | int(low, 16))
        for offset, low, high in pattern.findall(body)
    ]


def validate_assembly(source: str) -> None:
    clean = strip_comments(source)
    registers = {int(value) for value in re.findall(r"\b[wx]([0-9]+)\b", clean)}
    require(registers <= set(range(9, 16)), f"protected register used: {registers}")
    require(not re.search(r"\bsp\b", clean), "stack pointer used")
    require(not re.search(r"^\s*(?:bl|blr|ret)\b", clean, re.MULTILINE), "call/return used")
    require(not re.search(r"^\s*(?:adr|adrp)\b", clean, re.MULTILINE), "address literal used")
    require(not re.search(r"^\s*ldr\s+[^,]+,\s*=", clean, re.MULTILINE), "literal load used")
    require(not re.search(r"^\s*(?:stp|str)\s+x", clean, re.MULTILINE), "wide store used")
    require(not re.search(r"^\s*(?:dc|ic)\b", clean, re.MULTILINE), "cache operation used")
    require(clean.count("mrs\tx10, CurrentEL") == 2, "CurrentEL gate count changed")
    require(clean.count("mrs\tx10, sctlr_el1") == 2, "SCTLR_EL1 gate count changed")
    require(clean.count("mrs\tx10, sctlr_el2") == 2, "SCTLR_EL2 gate count changed")
    require(clean.count("tbnz\tx10, #0") == 2, "MMU-off gate count changed")
    require(clean.count("tbnz\tx10, #2") == 2, "data-cache-off gate count changed")
    require(clean.count("movz\tx9, #0xb000") == 2, "ledger base low word changed")
    require(clean.count("movk\tx9, #0x444b, lsl #16") == 2, "ledger base high word changed")
    require(clean.count("dsb\tsy") == 6, "full-system write ordering changed")

    expected = record_layout.validate()
    for index, (stage, payload, words) in enumerate(expected[:2]):
        stem = "primary" if index == 0 else "switch"
        stores = word_rows(macro_body(source, f"gemini_entry_ledger_{stem}_store"), "store")
        verifies = word_rows(macro_body(source, f"gemini_entry_ledger_{stem}_verify"), "verify")
        wanted = [(12 + offset * 4, word) for offset, word in enumerate(words)]
        require(stores == wanted, f"{stage.name} assembly stores differ from frozen record")
        require(verifies == wanted, f"{stage.name} full readback differs from frozen record")
        rebuilt = b"".join(word.to_bytes(4, "little") for _, word in stores)[: len(payload)]
        require(rebuilt == payload, f"{stage.name} assembly bytes do not roundtrip")

    primary = macro_body(source, "gemini_arm64_entry_ledger_primary")
    switch = macro_body(source, "gemini_arm64_entry_ledger_pre_switch")
    require(primary.count("gemini_entry_ledger_require_empty") == 4,
            "primary four-header fingerprint changed")
    require(switch.count("gemini_entry_ledger_require_empty") == 3,
            "pre-switch target/later empty checks changed")
    require(switch.count("gemini_entry_ledger_require_primary_or_empty") == 1,
            "pre-switch independent earlier-slot policy changed")
    require(primary.index("gemini_entry_ledger_primary_store") < primary.index("str\tw13, [x9, #4]") <
            primary.index("str\tw13, [x9, #8]"), "primary commit order changed")
    require(switch.index("gemini_entry_ledger_switch_store") < switch.index("str\tw13, [x14, #4]") <
            switch.index("str\tw13, [x14, #8]"), "pre-switch commit order changed")
    require("gemini_entry_ledger_primary_verify x9" in primary,
            "primary complete readback call missing")
    require("gemini_entry_ledger_switch_verify x14" in switch,
            "pre-switch complete readback call missing")


def validate_c(source: str, expected_records: list[bytes]) -> None:
    table = source.split("static const char * const gemini_entry_records[]", 1)[1]
    table = table.split("};", 1)[0]
    entries = re.findall(r'((?:\s*"(?:\\.|[^"\\])*")+\s*),', table)
    records = []
    for entry in entries:
        literals = re.findall(r'"(?:\\.|[^"\\])*"', entry)
        records.append("".join(ast.literal_eval(item) for item in literals).encode("ascii"))
    require(records == expected_records, "C records differ from frozen exact bytes")
    for needle in (
        "GEMINI_ENTRY_RESERVE_BASE\t0x44410000ULL",
        "GEMINI_ENTRY_RESERVE_SIZE\t0x000e0000ULL",
        "GEMINI_ENTRY_BASE\t\t0x444bb000ULL",
        "GEMINI_ENTRY_SLOT_COUNT\t\t4",
        "GEMINI_ENTRY_SIGNATURE\t\t0x43474244",
        "if (i < stage)",
        "gemini_entry_slot_empty(slot)",
        "gemini_entry_slot_exact(slot, gemini_entry_records[i])",
        "memcpy_toio((u8 __iomem *)slot + GEMINI_ENTRY_HEADER_SIZE, record, len);",
        "writel(len, (u8 __iomem *)slot + 4);",
        "writel(len, (u8 __iomem *)slot + 8);",
        "readl(slot) != GEMINI_ENTRY_SIGNATURE",
        "of_flat_dt_is_compatible(root, \"planet,gemini-pda\")",
        "ramoops@44410000",
        "of_flat_dt_get_addr_size",
        "no_map_len != 0",
        "memblock_is_region_reserved(addr, size)",
        "gemini_entry_checkpoint(2, false);",
        "gemini_entry_checkpoint(3, true);",
    ):
        require(needle in source, f"C safety contract missing: {needle}")
    require(source.count("dsb(sy);") == 3, "C full-system ordering count changed")
    write = source[source.index("static bool __init gemini_entry_write"):]
    require(write.index("memcpy_toio") < write.index("writel(len, (u8 __iomem *)slot + 4)") <
            write.index("writel(len, (u8 __iomem *)slot + 8)"), "C commit order changed")
    clean = strip_comments(source)
    prohibited = re.compile(
        r"\b(?:psci(?:_[a-z0-9_]+)?|cpu_up|cpu_down|regulator|i2c|clk_set|watchdog|restart|reboot|poweroff|"
        r"msleep|mdelay|udelay|usleep_range)\b",
        re.IGNORECASE,
    )
    require(not prohibited.search(clean), "prohibited runtime effect entered C source")


def validate(
    patch: str,
    series: str,
    manifest: dict,
    fragment: str,
) -> None:
    series_lines = [line.strip() for line in series.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
    require(series_lines[-1] == PATCH_NAME, "entry-ledger patch is not canonical tail")
    require(series_lines.count(PATCH_NAME) == 1, "entry-ledger patch identity is not unique")

    profiles = manifest["config"]["profiles"]
    require(PROFILE in profiles and PARENT in profiles, "profile or parent missing")
    parent_fragments = profiles[PARENT]["fragments"]
    profile = profiles[PROFILE]
    require(profile["base"] == profiles[PARENT]["base"], "profile base differs from parent")
    require(profile["fragments"] == parent_fragments + [FRAGMENT],
            "profile is not an exact isolated parent extension")
    require("patch_series" not in profile, "profile introduced a noncanonical series")
    require(fragment.splitlines() == [
        "# Experiment-only four-slot arm64 entry ledger with two MMU-off checkpoints.",
        "# The exact module-policy control and CPU8/CPU9 veto remain unchanged.",
        "# CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER is not set",
        "CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER=y",
        'CONFIG_LOCALVERSION="-gemini-entryled-a"',
    ], "profile fragment changed")

    disclosure = re.sub(r"\s+", " ", patch)
    require("default-off" in disclosure and "is not submission-ready" in disclosure,
            "experiment-only patch disclosure changed")
    require("Signed-off-by:" not in patch, "synthetic experiment patch gained a sign-off")
    assembly = added_file(patch, "arch/arm64/kernel/gemini-entry-ledger-head.S")
    c_source = added_file(patch, "fs/pstore/gemini_entry_ledger.c")
    validate_assembly(assembly)
    rows = record_layout.validate()
    validate_c(c_source, [payload for _, payload, _ in rows])

    head = diff_body(patch, "arch/arm64/kernel/head.S")
    require(re.search(
        r"bl\trecord_mmu_state\n\+#ifdef CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER\n"
        r"\+\tgemini_arm64_entry_ledger_primary\n\+#endif\n \tbl\tpreserve_boot_args",
        head,
    ) is not None, "primary-entry hook moved")
    require(re.search(
        r"bl\t__cpu_setup.*\n\+#ifdef CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER\n"
        r"\+\tgemini_arm64_entry_ledger_pre_switch\n\+#endif\n \tb\t__primary_switch",
        head,
    ) is not None, "pre-primary-switch hook moved")
    setup = diff_body(patch, "arch/arm64/kernel/setup.c")
    require(
        "early_ioremap_init();\n"
        "+\tgemini_arm64_entry_ledger_post_mmu_checkpoint();\n \n"
        " \tsetup_machine_fdt" in setup,
            "post-MMU hook moved")
    require(
        "arm64_memblock_init();\n"
        " \tgemini_pre_ramoops_ledger_setup_checkpoint();\n"
        "+\tgemini_arm64_entry_ledger_post_reserved_checkpoint();" in setup,
            "post-reserved hook moved")
    kconfig = diff_body(patch, "fs/pstore/Kconfig")
    require("config PSTORE_GEMINI_ARM64_ENTRY_LEDGER" in kconfig, "Kconfig option missing")
    require("+\tdefault n" in kconfig, "entry ledger is not default-off")
    require("depends on !PSTORE_GEMINI_PRE_RAMOOPS_LEDGER" in kconfig,
            "old and new ledgers are not mutually isolated")
    makefile = diff_body(patch, "fs/pstore/Makefile")
    require("CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER) += gemini_entry_ledger.o" in makefile,
            "entry-ledger object selection missing")
    ram = diff_body(patch, "fs/pstore/ram.c")
    require("CONFIG_PSTORE_GEMINI_ARM64_ENTRY_LEDGER" in ram and
            "of_machine_is_compatible(\"planet,gemini-pda\")" in ram,
            "isolated normal-ramoops bypass missing")
    header = diff_body(patch, "include/linux/pstore_ram.h")
    require(header.count("gemini_arm64_entry_ledger_") == 4,
            "checkpoint declarations/stubs changed")


def main() -> None:
    validate(
        PATCH_PATH.read_text(encoding="utf-8"),
        SERIES_PATH.read_text(encoding="utf-8"),
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
        FRAGMENT_PATH.read_text(encoding="utf-8"),
    )
    print("validation=arm64-entry-ledger-implementation")
    print("patch=0281")
    print("assembly_stages=2")
    print("early_mapped_stages=2")
    print("protected_registers=preserved")
    print("independent_stage_policy=empty-or-exact")
    print("cpu8_cpu9_admission=closed")
    print("result=pass")


if __name__ == "__main__":
    main()
