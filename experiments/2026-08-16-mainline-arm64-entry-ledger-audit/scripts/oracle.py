#!/usr/bin/env python3
"""Validate the offline arm64 entry-ledger design and outcome semantics."""

from __future__ import annotations

from dataclasses import dataclass
import itertools
import zlib


TOKEN = "GAEL-20260816-A"
PREFIX = "GEMINI_ARM64_ENTRY_LEDGER_V1"
RESERVATION = (0x44410000, 0x444F0000)
ZONE_BASE = 0x444BB000
ZONE_SIZE = 0x1000
SIGNATURE = 0x43474244
PROTECTED_REGISTERS = frozenset(
    {"x0", "x1", "x2", "x3", "x19", "x20", "x21", "x30", "sp"}
)
ALLOWED_ASSEMBLY_CLOBBERS = frozenset(f"x{number}" for number in range(9, 16))
EXPECTED_STAGES = (
    ("primary-entry", 171, "990b22bb"),
    ("pre-primary-switch", 172, "c00e5ee2"),
    ("post-mmu", 173, "1297491b"),
    ("post-reserved-scan", 174, "88a58bc9"),
)


@dataclass(frozen=True)
class Stage:
    name: str
    slot: int
    hook: str
    mode: str
    clobbers: frozenset[str] = frozenset()
    require_mmu_off: bool = False
    require_dcache_off: bool = False
    require_current_el: bool = False
    require_all_header_fingerprint: bool = True
    accept_prior_empty_or_exact: bool = True
    require_exact_dt: bool = False
    require_memblock_reservation: bool = False
    independent_of_prior_write: bool = True
    data_before_start_before_size: bool = True
    full_readback: bool = True
    aligned_access_only: bool = True

    @property
    def address(self) -> int:
        return ZONE_BASE + (self.slot - 171) * ZONE_SIZE

    @property
    def crc(self) -> str:
        source = f"token={TOKEN}|stage={self.name}|slot={self.slot}".encode()
        return f"{zlib.crc32(source):08x}"


@dataclass(frozen=True)
class Design:
    stages: tuple[Stage, ...]
    signature: int = SIGNATURE
    reservation: tuple[int, int] = RESERVATION
    normal_ramoops_bypassed: bool = True
    default_off: bool = True
    isolated_profile: bool = True
    runtime_effects: frozenset[str] = frozenset({"retained-ram-record"})


def exact_design() -> Design:
    assembly = dict(
        mode="mmu-off-physical",
        clobbers=ALLOWED_ASSEMBLY_CLOBBERS,
        require_mmu_off=True,
        require_dcache_off=True,
        require_current_el=True,
    )
    return Design(
        stages=(
            Stage("primary-entry", 171, "post-record_mmu_state", **assembly),
            Stage("pre-primary-switch", 172, "post-__cpu_setup", **assembly),
            Stage("post-mmu", 173, "post-early_ioremap_init", mode="early-ioremap"),
            Stage(
                "post-reserved-scan",
                174,
                "post-arm64_memblock_init",
                mode="early-ioremap",
                require_exact_dt=True,
                require_memblock_reservation=True,
            ),
        )
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate(design: Design) -> None:
    stages = design.stages
    require(len(stages) == 4, "stage count changed")
    require(
        [(stage.name, stage.slot, stage.crc) for stage in stages] == list(EXPECTED_STAGES),
        "stage identity or CRC changed",
    )
    require([stage.slot for stage in stages] == [171, 172, 173, 174], "slot order changed")
    require(
        [stage.address for stage in stages]
        == [0x444BB000, 0x444BC000, 0x444BD000, 0x444BE000],
        "stage address changed",
    )
    require(design.signature == SIGNATURE, "persistent signature changed")
    require(design.reservation == RESERVATION, "reservation changed")
    for stage in stages:
        require(
            design.reservation[0] <= stage.address
            and stage.address + ZONE_SIZE <= design.reservation[1],
            f"{stage.name} escaped reservation",
        )
        require(stage.require_all_header_fingerprint, f"{stage.name} lost fingerprint")
        require(stage.accept_prior_empty_or_exact, f"{stage.name} accepts foreign prior data")
        require(stage.independent_of_prior_write, f"{stage.name} became cascade-dependent")
        require(stage.data_before_start_before_size, f"{stage.name} commit order changed")
        require(stage.full_readback, f"{stage.name} lost readback")
        require(stage.aligned_access_only, f"{stage.name} permits unaligned access")
        require(len(stage.crc) == 8, f"{stage.name} CRC malformed")
    require(stages[0].hook == "post-record_mmu_state", "entry hook moved")
    require(stages[1].hook == "post-__cpu_setup", "pre-switch hook moved")
    for stage in stages[:2]:
        require(stage.mode == "mmu-off-physical", f"{stage.name} access mode changed")
        require(stage.require_current_el, f"{stage.name} lost CurrentEL gate")
        require(stage.require_mmu_off, f"{stage.name} lost MMU gate")
        require(stage.require_dcache_off, f"{stage.name} lost cache gate")
        require(not (stage.clobbers & PROTECTED_REGISTERS), f"{stage.name} clobbers boot state")
        require(stage.clobbers <= ALLOWED_ASSEMBLY_CLOBBERS, f"{stage.name} clobber set expanded")
    require(stages[2].hook == "post-early_ioremap_init", "post-MMU hook moved")
    require(stages[2].mode == "early-ioremap", "post-MMU mapping changed")
    require(stages[3].hook == "post-arm64_memblock_init", "reserved hook moved")
    require(stages[3].mode == "early-ioremap", "reserved mapping changed")
    require(stages[3].require_exact_dt, "final stage lost exact DT gate")
    require(stages[3].require_memblock_reservation, "final stage lost reservation gate")
    require(design.default_off and design.isolated_profile, "configuration isolation lost")
    require(design.normal_ramoops_bypassed, "normal ramoops can consume records")
    require(design.runtime_effects == {"retained-ram-record"}, "runtime effects expanded")


def enumerate_outcomes(design: Design) -> int:
    """Prove independent refusals cannot overstate monotonically reached stages."""
    count = 0
    for reached_count in range(5):
        reached = tuple(index < reached_count for index in range(4))
        for gates in itertools.product((False, True), repeat=4):
            written = tuple(reached[index] and gates[index] for index in range(4))
            if any(written):
                highest_index = max(index for index, value in enumerate(written) if value)
                require(reached[highest_index], "marker overstated execution reach")
                require(
                    all(reached[index] for index in range(highest_index + 1)),
                    "marker violated chronological reach",
                )
            for index, value in enumerate(written):
                require(not value or reached[index], "unreached stage wrote")
                if reached[index] and gates[index]:
                    require(value, "earlier refusal hid a later valid stage")
            count += 1
    return count


def main() -> None:
    design = exact_design()
    validate(design)
    outcomes = enumerate_outcomes(design)
    print("validation=arm64-entry-ledger-design-oracle")
    print("stages=primary-entry,pre-primary-switch,post-mmu,post-reserved-scan")
    print("slots=171,172,173,174")
    print(f"outcomes_checked={outcomes}")
    print("assembly_clobbers=x9-x15-only")
    print("incoming_mmu_cache=runtime-gated")
    print("stage_independence=earlier-empty-or-exact")
    print("runtime_effects=retained-ram-record-only")
    print("implementation=none")
    print("device_access=none")
    print("result=pass")


if __name__ == "__main__":
    main()
