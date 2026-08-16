#!/usr/bin/env python3
"""Validate the exact default-off Gemini pre-ramoops stage ledger."""

from __future__ import annotations

import json
from pathlib import Path
import re
import zlib


ROOT = Path(__file__).resolve().parents[3]
PATCH_NAME = "v7.1.3/0280-pstore-add-Gemini-pre-ramoops-stage-ledger.patch"
PATCH_PATH = ROOT / "patches" / PATCH_NAME
FRAGMENT_PATH = ROOT / "configs/gemini-pre-ramoops-ledger.fragment"
MANIFEST_PATH = ROOT / "kernel/manifest.json"
SERIES_PATH = ROOT / "patches/series"
PARENT = "da921x-resource-only-provider-modules-control"
PROFILE = "da921x-modules-pre-ramoops-ledger"
FRAGMENT = "configs/gemini-pre-ramoops-ledger.fragment"
TOKEN = "GPRL-20260816-A"
STAGES = (
    ("reserved-scan", 171, "0x444bb000ULL"),
    ("early-initcall", 172, "0x444bc000ULL"),
    ("core-initcall", 173, "0x444bd000ULL"),
    ("postcore-initcall", 174, "0x444be000ULL"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def integrity(stage: str, slot: int) -> str:
    source = f"token={TOKEN}|stage={stage}|slot={slot}".encode()
    return f"{zlib.crc32(source):08x}"


def added_lines(patch: str) -> str:
    return "\n".join(
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )


def validate_inputs(
    manifest: dict[str, object], series: str, patch: str, fragment: str
) -> None:
    profiles = manifest["config"]["profiles"]  # type: ignore[index]
    parent = profiles[PARENT]  # type: ignore[index]
    profile = profiles[PROFILE]  # type: ignore[index]
    require(profile["base"] == parent["base"] == "defconfig", "base drift")
    require(
        profile["fragments"] == [*parent["fragments"], FRAGMENT],
        "profile is not the exact parent plus one final fragment",
    )

    lines = [line for line in series.splitlines() if line and not line.startswith("#")]
    require(lines[-1] == PATCH_NAME, "ledger patch is not canonical-series tail")
    require(lines.count(PATCH_NAME) == 1, "ledger patch series identity is not unique")

    semantic = [
        line for line in fragment.splitlines() if line and not line.startswith("#")
    ]
    require(
        semantic
        == [
            "CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER=y",
            'CONFIG_LOCALVERSION="-gemini-preledger-a"',
        ],
        "fragment gained unrelated policy",
    )

    added = added_lines(patch)
    require(
        patch.count("config PSTORE_GEMINI_PRE_RAMOOPS_LEDGER") == 1,
        "Kconfig gate drift",
    )
    require("depends on PSTORE_RAM=y" in patch, "built-in ramoops dependency missing")
    require(
        "depends on ARM64 && ARCH_MEDIATEK && OF" in patch,
        "platform dependency drift",
    )
    require("default n" in patch, "ledger is not default-off")
    require(
        patch.count("#ifdef CONFIG_PSTORE_GEMINI_PRE_RAMOOPS_LEDGER") == 3,
        "source/header gates drifted",
    )

    setup_order = re.search(
        r"arm64_memblock_init\(\);\n\+\tgemini_pre_ramoops_ledger_setup_checkpoint\(\);\n \n \tpaging_init\(\);",
        patch,
    )
    require(setup_order is not None, "setup checkpoint placement drift")
    require("GEMINI_PRELEDGER_RESERVE_BASE\t0x44410000ULL" in added, "reserve base drift")
    require("GEMINI_PRELEDGER_RESERVE_SIZE\t0x000e0000ULL" in added, "reserve size drift")
    require("GEMINI_PRELEDGER_BASE\t\t0x444bb000ULL" in added, "ledger base drift")
    require("GEMINI_PRELEDGER_SLOT_COUNT\t4" in added, "slot count drift")
    require("GEMINI_PRELEDGER_SIGNATURE\t0x43474244" in added, "DBGC signature drift")
    require('"ramoops@44410000"' in added, "exact DT node check missing")
    require('of_get_flat_dt_prop(ramoops, "no-map"' in added, "no-map check missing")
    require("memblock_is_region_reserved(addr, size)" in added, "memblock reservation check missing")

    for stage, slot, address in STAGES:
        crc = integrity(stage, slot)
        marker = f"stage={stage} slot={slot} crc32={crc}"
        require(patch.count(marker) == 1, f"record identity drift: {stage}")
        require(address in added, f"slot address drift: {slot}")
    require(patch.count("GEMINI_PRE_RAMOOPS_LEDGER_V1 token=GPRL-20260816-A") == 4,
            "candidate token count drift")
    require(patch.count('"====0.000000-D\\n"') == 4, "ramoops dmesg framing drift")

    all_empty = added.index("for (i = 0; i < GEMINI_PRELEDGER_SLOT_COUNT; i++)")
    first_write = added.index("gemini_preledger_write(ledger, gemini_preledger_records[0])")
    require(all_empty < first_write, "first write precedes all-slot validation")
    require("memcpy_toio" in added, "record data write missing")
    require(added.index("memcpy_toio") < added.index("writel(len, (u8 __iomem *)slot + 4)"),
            "start committed before record data")
    require(added.index("writel(len, (u8 __iomem *)slot + 4)") <
            added.index("writel(len, (u8 __iomem *)slot + 8)"),
            "size committed before start")
    require("gemini_preledger_armed = false;" in added, "later-stage disarm missing")
    require("early_ioremap(GEMINI_PRELEDGER_BASE" in added, "early mapping missing")
    require("ioremap_wc(gemini_preledger_slots[stage]" in added, "initcall WC mapping missing")
    require("early_initcall(gemini_preledger_early_checkpoint);" in added, "early initcall missing")
    require("core_initcall(gemini_preledger_core_checkpoint);" in added, "core initcall missing")
    require("postcore_initcall(gemini_preledger_postcore_checkpoint);" in added, "postcore initcall missing")

    skip = added.index('if (of_machine_is_compatible("planet,gemini-pda"))')
    registration = patch.rindex("platform_driver_register(&ramoops_driver)")
    require(skip < registration, "normal ramoops is not bypassed before registration")

    for forbidden in (
        "i2c_transfer(",
        "regulator_get(",
        "regulator_set_",
        "regmap_read(",
        "regmap_write(",
        "cpu_up(",
        "cpu_down(",
        "psci_ops.cpu_on(",
        "schedule_delayed_work(",
        "add_timer(",
        "kernel_restart(",
        "emergency_restart(",
        "kernel_power_off(",
        "Signed-off-by:",
    ):
        require(forbidden not in patch, f"forbidden operation present: {forbidden}")
    require("synthetic, non-certifying author identity" in patch, "author status missing")
    require("not submission-ready" in patch, "experiment-only status missing")


def main() -> None:
    validate_inputs(
        json.loads(MANIFEST_PATH.read_text(encoding="utf-8")),
        SERIES_PATH.read_text(encoding="utf-8"),
        PATCH_PATH.read_text(encoding="utf-8"),
        FRAGMENT_PATH.read_text(encoding="utf-8"),
    )
    print("validation=mainline-pre-ramoops-ledger-static")
    print(f"parent_profile={PARENT}")
    print("profile_delta=one-final-fragment")
    print("selected_slots=171,172,173,174")
    print("first_write_gate=exact-dt-reservation-and-four-empty-headers")
    print("normal_ramoops=skipped-on-gemini-for-isolated-profile")
    print("runtime_partition_access=none")
    print("regulator_i2c_cpu_timer_reboot_actions=none")
    print("result=pass")


if __name__ == "__main__":
    main()
