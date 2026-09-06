#!/usr/bin/env python3
"""Host-only contract fixtures for the passive CONSYS boot slice.

The model mirrors only the immutable metadata and private-reference boundary;
it does not emulate a kernel, a device, a bus, firmware, or radio hardware.
"""

from dataclasses import dataclass, replace
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "patches/v7.1.3/0544-soc-mediatek-add-MT6797-passive-CONSYS-boot-binding.patch"
SERIES = ROOT / "patches/series-mt6797-consys-passive-boot"

SIZE = 0x200000
ALIGN = 0x200000
RANGE_BASE = 0x40000000
RANGE_SIZE = 0x80000000


def check(condition: bool, message: str) -> None:
    """Raise even under python -O; assertions are not test oracles here."""
    if not condition:
        raise AssertionError(message)


@dataclass
class Reservation:
    compatible: int = 1
    parent: bool = True
    available: bool = True
    no_map: bool = True
    reusable: bool = False
    no_map_fixup: bool = False
    reg: bool = False
    size_cells: int = 2
    size: int = SIZE
    alignment_cells: int = 2
    alignment: int = ALIGN
    ranges_cells: int = 4
    range_base: int = RANGE_BASE
    range_size: int = RANGE_SIZE
    allocated_base: int = 0x60000000
    allocated_size: int = SIZE
    wrapped_range: bool = False
    custom_ops: bool = False


@dataclass
class Provider:
    generation: int = 1
    published: bool = False
    references: int = 1


@dataclass
class Client:
    bound: bool = False
    provider: Provider | None = None
    generation: int = 0


def validate(reservation: Reservation) -> bool:
    if reservation.compatible != 1 or not reservation.parent or not reservation.available:
        return False
    if reservation.reg or not reservation.no_map or reservation.reusable or reservation.no_map_fixup:
        return False
    if reservation.size_cells != 2 or reservation.size != SIZE:
        return False
    if reservation.alignment_cells != 2 or reservation.alignment != ALIGN:
        return False
    if reservation.ranges_cells != 4 or reservation.range_size == 0:
        return False
    if reservation.wrapped_range or reservation.range_base + reservation.range_size - 1 > (1 << 64) - 1:
        return False
    if reservation.range_base != RANGE_BASE or reservation.range_size != RANGE_SIZE:
        return False
    if reservation.custom_ops or reservation.allocated_size != SIZE or not reservation.allocated_base:
        return False
    if reservation.allocated_base % ALIGN:
        return False
    allocated_end = reservation.allocated_base + reservation.allocated_size - 1
    range_end = reservation.range_base + reservation.range_size - 1
    return allocated_end <= range_end and allocated_end >= reservation.range_base


def publish(reservation: Reservation, generation: int = 1) -> Provider | None:
    # Publication is deliberately after the complete metadata validation.
    if not validate(reservation):
        return None
    if not generation:
        return None
    return Provider(generation=generation, published=True)


def acquire(client: Client, provider: Provider | None) -> int:
    if client.bound:
        return -16  # -EBUSY
    if provider is None or not provider.published or not provider.generation:
        return -19  # -ENODEV
    if provider.references == 0:
        return -116  # -ESTALE
    provider.references += 1
    client.bound = True
    client.provider = provider
    client.generation = provider.generation
    return 0


def release(client: Client) -> None:
    if not client.bound:
        return
    check(client.provider is not None, "release requires a provider")
    check(client.generation == client.provider.generation, "release generation")
    check(client.provider.references > 1, "release reference count")
    client.provider.references -= 1
    client.bound = False
    client.provider = None
    client.generation = 0


def source_text() -> str:
    text = PATCH.read_text(encoding="utf-8")
    start = text.index("+// SPDX-License-Identifier: GPL-2.0-only")
    end = text.index("\n-- \n", start)
    return "\n".join(line[1:] for line in text[start:end].splitlines())


def expect_refusal(name: str, reservation: Reservation) -> None:
    check(publish(reservation) is None, name)


def run() -> int:
    cases = 0
    base = Reservation()
    check(publish(base) is not None, "base publication")
    cases += 1

    mutations = {
        "absent-compatible": {"compatible": 0},
        "duplicate-compatible": {"compatible": 2},
        "missing-no-map": {"no_map": False},
        "reusable": {"reusable": True},
        "no-map-fixup": {"no_map_fixup": True},
        "static-reg": {"reg": True},
        "malformed-size-cells": {"size_cells": 1},
        "wrong-size": {"size": SIZE // 2},
        "malformed-alignment-cells": {"alignment_cells": 1},
        "wrong-alignment": {"alignment": ALIGN * 2},
        "malformed-range-cells": {"ranges_cells": 3},
        "wrong-range-base": {"range_base": RANGE_BASE + ALIGN},
        "wrong-range-size": {"range_size": RANGE_SIZE // 2},
        "wrapped-range": {"wrapped_range": True},
        "zero-allocation": {"allocated_base": 0},
        "misaligned-allocation": {"allocated_base": 0x60001000},
        "wrong-allocation-size": {"allocated_size": SIZE // 2},
        "allocation-outside-range": {"allocated_base": 0xC0000000},
        "region-callback": {"custom_ops": True},
        "wrong-parent": {"parent": False},
        "unavailable-node": {"available": False},
    }
    for name, changes in mutations.items():
        expect_refusal(name, replace(base, **changes))
        cases += 1

    check(publish(base, generation=0) is None, "zero generation")
    cases += 1
    provider = publish(base)
    check(provider is not None and provider.published, "provider publication")
    client = Client()
    check(acquire(client, provider) == 0, "first client acquire")
    check(acquire(Client(), provider) == 0, "second passive client acquire")
    check(acquire(client, provider) == -16, "competing client acquire")
    cases += 3
    stale = Provider(generation=0, published=True, references=1)
    check(acquire(Client(), stale) == -19, "zero-generation provider")
    cases += 1
    provider.references = 0
    check(acquire(Client(), provider) == -116, "stale provider")
    cases += 1
    provider = publish(base)
    check(provider is not None, "second provider publication")
    client = Client()
    check(acquire(client, provider) == 0, "lifetime acquire")
    before = provider.references
    release(client)
    check(provider.references == before - 1 and not client.bound, "balanced release")
    release(client)
    check(provider.references == before - 1, "idempotent release")
    cases += 2

    source = source_text()
    check(source.index("#include <linux/types.h>") <
          source.index("#include <linux/byteorder/generic.h>"),
          "kernel types precede byteorder helpers")
    cases += 1
    check("state=BOUND generation=%llu" in source, "stable success prefix")
    for field in ("power", "reset", "remap", "protection", "firmware", "radio", "dma"):
        check(re.search(rf"{field}=%u", source), f"log counter {field}")
        check(re.search(rf"\.{field} = 0", source), f"zero counter {field}")
    check("client=%s" in source and 'MT6797_PASSIVE_CLIENT "wlan-passive"' in source,
          "passive client log")
    check("of_reserved_mem_lookup" in source and '"mediatek,consys-reserve-memory"' in source,
          "reserved-memory observer")
    check("of_find_compatible_node(of_node_get(node), NULL" in source,
          "independent OF iterator reference")
    check("of_find_compatible_node(node, NULL" not in source,
          "old consuming OF iterator pattern")
    check("of_node_put(duplicate)" in source, "duplicate reference release")
    check("reserved->base" not in source.split('pr_info("mt6797-consys-passive: state=BOUND', 1)[1],
          "no address in success log")
    forbidden = (
        "ioremap", "memremap", "request_mem_region", "devm_request_mem_region",
        "clk_get", "clk_prepare", "clk_enable", "regulator_get", "reset_control",
        "regmap_", "request_firmware", "rfkill", "cfg80211", "dma_request",
        "dmaengine", "writel", "writew", "writel_relaxed", "atomic_inc",
        "++mt6797_effects", "mt6797_effects.power++", "retry", "radio_on",
    )
    for token in forbidden:
        check(token not in source, token)
    check("static const struct mt6797_passive_effects" in source, "immutable counters")
    check("mt6797_passive_client_release" in source, "passive release helper")
    check(source.index("mt6797_validate_reserved_memory") < source.index("provider->published = true"),
          "publication after validation")
    cases += 12

    series = [line for line in SERIES.read_text().splitlines() if line and not line.startswith("#")]
    canonical = [line for line in (ROOT / "patches/series").read_text().splitlines() if line and not line.startswith("#")]
    positions = [canonical.index(item) for item in series]
    check(positions == sorted(positions), "canonical series order")
    check(series[-1].endswith("0544-soc-mediatek-add-MT6797-passive-CONSYS-boot-binding.patch"),
          "new patch is last")
    fragment = (ROOT / "configs/gemini-mt6797-consys-passive.fragment").read_text()
    check("CONFIG_MTK_MT6797_CONSYS_PASSIVE_BOOT=y" in fragment, "fragment Kconfig symbol")
    check('CONFIG_LOCALVERSION="-gemini-consys-passive"' in fragment, "fragment identity")
    check("configs/gemini-mt6797-consys-passive.fragment" not in
          (ROOT / "configs/gemini.fragment").read_text(), "isolated fragment")
    check("does not provide a usable Wi-Fi device" in PATCH.read_text(encoding="utf-8"),
          "no support claim")
    cases += 3

    print(f"passive CONSYS fixtures: PASS cases={cases}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
