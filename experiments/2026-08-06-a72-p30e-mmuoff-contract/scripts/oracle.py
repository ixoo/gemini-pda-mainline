#!/usr/bin/env python3
"""Validate the bounded P30E MMU-off-visible object contract."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path


FIELDS = (
    "magic", "abi_and_size", "boot_identity_0", "boot_identity_1",
    "boot_identity_2", "boot_identity_3", "operation", "target_cpu",
    "target_mpidr", "generation", "cookie", "controller_state",
    "target_state", "target_sequence", "controller_sequence",
    "target_reason", "target_effects", "target_entry_pc", "target_entry_sp",
    "crc64",
)
SOURCE_AUDIT = Path(__file__).resolve().parents[1] / "results/source-placement-audit-20260806.txt"
IMPLEMENTATION_AUDIT = Path(__file__).resolve().parents[1] / "results/implementation-seam-audit-20260806.txt"
IMMUTABLE = frozenset(FIELDS[:11])
CONTROLLER_OWNED = frozenset({"controller_state", "controller_sequence", "crc64"})
TARGET_OWNED = frozenset({
    "target_state", "target_sequence", "target_reason", "target_effects",
    "target_entry_pc", "target_entry_sp",
})
STATES = ("EMPTY", "ARMED", "TARGET_CLAIMED", "TARGET_PUBLISHED",
          "FAILED", "PARKED", "PANICKED")
LEGAL = {
    "EMPTY": ("ARMED",),
    "ARMED": ("TARGET_CLAIMED", "FAILED", "PARKED", "PANICKED"),
    "TARGET_CLAIMED": ("TARGET_PUBLISHED", "FAILED", "PARKED", "PANICKED"),
    "TARGET_PUBLISHED": (),
    "FAILED": (),
    "PARKED": (),
    "PANICKED": (),
}
WRITER = {field: "controller" for field in IMMUTABLE | CONTROLLER_OWNED}
WRITER.update({field: "target" for field in TARGET_OWNED})


@dataclass(frozen=True)
class Contract:
    fields: tuple[str, ...] = FIELDS
    immutable: frozenset[str] = IMMUTABLE
    controller_owned: frozenset[str] = CONTROLLER_OWNED
    target_owned: frozenset[str] = TARGET_OWNED
    states: tuple[str, ...] = STATES
    legal: dict[str, tuple[str, ...]] | None = None
    writer: dict[str, str] | None = None
    controller_flush_order: tuple[str, ...] = (
        "write_header", "compute_crc", "clean_to_poc", "dsb_sy",
        "publish_armed_release",
    )
    target_publish_order: tuple[str, ...] = (
        "write_result", "increment_target_sequence", "clean_to_poc",
        "dsb_sy", "publish_terminal_release",
    )
    controller_readback_order: tuple[str, ...] = (
        "dsb_sy", "invalidate_complete_range", "read_full_object",
    )
    fail_closed: tuple[str, ...] = (
        "bad_header", "bad_crc", "bad_identity", "bad_sequence",
        "bad_state", "unreadable", "timeout_unproven_cpu_on", "nonreturn",
        "stale_generation", "mismatched_terminal", "failed_readback",
    )
    p14_p15_requires: tuple[str, ...] = (
        "target_published", "complete_readback", "exact_token",
        "online_sample", "no_quarantine",
    )


def validate(contract: Contract) -> None:
    if contract.legal is None:
        contract = replace(contract, legal=LEGAL)
    if contract.writer is None:
        contract = replace(contract, writer=WRITER)
    if len(contract.fields) != 20 or contract.fields != FIELDS:
        raise AssertionError("layout is not the fixed 20-word wire object")
    if not contract.immutable <= set(contract.fields[:11]):
        raise AssertionError("immutable header escaped the first 11 words")
    if contract.controller_owned & contract.target_owned:
        raise AssertionError("field has two owners")
    if contract.immutable & contract.target_owned:
        raise AssertionError("immutable field is target-owned")
    if set(contract.writer) != set(contract.fields):
        raise AssertionError("every field needs exactly one writer")
    if any(owner not in {"controller", "target"} for owner in contract.writer.values()):
        raise AssertionError("unknown field writer")
    if tuple(contract.states) != STATES:
        raise AssertionError("state vocabulary changed")
    if set(contract.legal) != set(STATES):
        raise AssertionError("state transition table incomplete")
    if contract.legal != LEGAL:
        raise AssertionError("state transition table widened or reordered")
    if contract.legal["TARGET_PUBLISHED"]:
        raise AssertionError("published state gained a successor")
    for state, successors in contract.legal.items():
        if any(successor not in STATES for successor in successors):
            raise AssertionError(f"unknown transition from {state}")
    if contract.controller_flush_order != (
        "write_header", "compute_crc", "clean_to_poc", "dsb_sy",
        "publish_armed_release",
    ):
        raise AssertionError("controller arming order weakened")
    if contract.target_publish_order != (
        "write_result", "increment_target_sequence", "clean_to_poc",
        "dsb_sy", "publish_terminal_release",
    ):
        raise AssertionError("target publication order weakened")
    if contract.controller_readback_order != (
        "dsb_sy", "invalidate_complete_range", "read_full_object",
    ):
        raise AssertionError("controller readback order weakened")
    required_failures = {
        "bad_header", "bad_crc", "bad_identity", "bad_sequence", "bad_state",
        "unreadable", "timeout_unproven_cpu_on", "nonreturn", "stale_generation",
        "mismatched_terminal", "failed_readback",
    }
    if not required_failures <= set(contract.fail_closed):
        raise AssertionError("fail-closed causes were removed")
    required_commit = {
        "target_published", "complete_readback", "exact_token", "online_sample",
        "no_quarantine",
    }
    if not required_commit <= set(contract.p14_p15_requires):
        raise AssertionError("P14/P15 gained an incomplete path")


def expect_reject(label: str, mutation) -> None:
    try:
        validate(mutation())
    except AssertionError:
        return
    raise AssertionError(f"mutation accepted: {label}")


def main() -> None:
    base = Contract()
    validate(base)
    source_audit = SOURCE_AUDIT.read_text()
    for needle in (
        "linker_sections=.mmuoff.data.write;__mmuoff_data_start;clean_to_poc_required_for_MMU-off-writeback;separate_.mmuoff.data.read;__mmuoff_data_end",
        "existing_mmuoff_writer=__early_cpu_boot_status;long;section=.mmuoff.data.write;target_writes_failure_status_before_controller_read",
        "existing_mmuoff_reader=secondary_holding_pen_release;volatile_ulong;section=.mmuoff.data.read;controller_writes;target_reads;dcache_clean_inval_poc;sev",
        "psci_cpu_on_signature=cpu_on(unsigned_long_cpuid,unsigned_long_entry_point);no_context_id_argument",
        "secondary_entry_arguments=none;head.S_mov_x0_xzr_then_init_kernel_el_then_secondary_startup",
        "target_slot_selection=static_per-target_slot_or_assembly-global_physical_base_selected_from_MPIDR;context-pointer_handoff_unavailable",
        "directional_gap=existing_linker_sections_separate_MMU-off-writeback_and_MMU-off-readback_lanes;P30E_needs_bidirectional_fields",
        "placement_consequence=split_controller_and_target_write_lanes_or_add_a_dedicated_aligned_bidirectional_section_with_explicit_cache_protocol",
        "decision=SOURCE_PLACEMENT_FEASIBLE_BUT_P30E_IMPLEMENTATION_OPEN",
        "status=PASS_P30E_SOURCE_PLACEMENT_AUDIT",
    ):
        if needle not in source_audit:
            raise AssertionError(f"missing source placement fact: {needle}")
    implementation_audit = IMPLEMENTATION_AUDIT.read_text()
    for needle in (
        "secondary_entry_section=.idmap.text;entry=secondary_entry;entry_arguments=none",
        "psci_handoff=cpu_on(unsigned_long_cpuid,unsigned_long_entry_point);no_context_id",
        "target_mpidr_map=0x200->p30e_cpu8_slot;0x201->p30e_cpu9_slot;other_values=P30U",
        "slot_layout=two_independent_slots;each_slot_alignment=SZ_2K;wire_words=20;wire_bytes=160;reserved_tail=SZ_2K-160",
        "linker_profile=dedicated_.mmuoff.data.bidirectional_after_directional_lanes",
        "target_identity_check=target_cpu_and_target_mpidr_before_claim",
        "publication_scope=full_slot_range;dsb_sy;terminal_release",
        "controller_readback=dsb_sy;invalidate_full_slot_range;read_full_object",
        "implementation_status=DORMANT_ASSEMBLY_C_ARTIFACT_REMAINING",
        "status=PASS_P30E_IMPLEMENTATION_SEAM_AUDIT",
    ):
        if needle not in implementation_audit:
            raise AssertionError(f"missing implementation seam fact: {needle}")
    mutations = (
        ("drop-magic", lambda: replace(base, fields=base.fields[1:])),
        ("share-field-owner", lambda: replace(base, target_owned=base.target_owned | {"magic"})),
        ("target-writes-controller-state", lambda: replace(base, target_owned=base.target_owned | {"controller_state"})),
        ("add-published-successor", lambda: replace(base, legal={**LEGAL, "TARGET_PUBLISHED": ("ARMED",)})),
        ("allow-target-before-armed", lambda: replace(base, legal={**LEGAL, "EMPTY": ("ARMED", "TARGET_CLAIMED")})),
        ("drop-clean", lambda: replace(base, controller_flush_order=("write_header", "compute_crc", "dsb_sy", "publish_armed_release"))),
        ("publish-before-clean", lambda: replace(base, target_publish_order=("write_result", "publish_terminal_release", "clean_to_poc", "dsb_sy"))),
        ("read-state-only", lambda: replace(base, controller_readback_order=("dsb_sy", "read_full_object"))),
        ("drop-stale-fault", lambda: replace(base, fail_closed=tuple(x for x in base.fail_closed if x != "stale_generation"))),
        ("allow-commit-before-readback", lambda: replace(base, p14_p15_requires=tuple(x for x in base.p14_p15_requires if x != "complete_readback"))),
        ("allow-commit-under-quarantine", lambda: replace(base, p14_p15_requires=tuple(x for x in base.p14_p15_requires if x != "no_quarantine"))),
        ("drop-exact-token", lambda: replace(base, p14_p15_requires=tuple(x for x in base.p14_p15_requires if x != "exact_token"))),
        ("drop-sequence", lambda: replace(base, target_publish_order=("write_result", "clean_to_poc", "dsb_sy", "publish_terminal_release"))),
        ("drop-barrier", lambda: replace(base, target_publish_order=("write_result", "increment_target_sequence", "clean_to_poc", "publish_terminal_release"))),
        ("unknown-writer", lambda: replace(base, writer={**WRITER, "magic": "firmware"})),
    )
    for label, mutation in mutations:
        expect_reject(label, mutation)
    print("layout_words=20")
    print("immutable_words=0..10")
    print("controller_owned=controller_state;controller_sequence;crc64")
    print("target_owned=target_state;target_sequence;target_reason;target_effects;target_entry_pc;target_entry_sp")
    print("states=EMPTY->ARMED->TARGET_CLAIMED->terminal")
    print("cache_order=clean_to_poc;dsb_sy;release;invalidate_complete_range;full_readback")
    print("source_placement=existing_directional_mmuoff_lanes;bidirectional_split_or_dedicated_section_required")
    print("target_handoff=PSCI_no_context;static_slot_or_MPIDR_selection_required")
    print("implementation_profile=dedicated_bidirectional_section;two_SZ_2K_slots;MPIDR_0x200_0x201;assembly_identity_check")
    print("negative_mutations=15;all_rejected=1")
    print("p14_p15_requires=target_published;complete_readback;exact_token;online_sample;no_quarantine")
    print("hardware_action=none")
    print("status=PASS_P30E_MMUS_OFF_WIRE_CONTRACT")


if __name__ == "__main__":
    main()
