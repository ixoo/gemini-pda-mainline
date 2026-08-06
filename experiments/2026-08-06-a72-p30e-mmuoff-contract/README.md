# Experiment: P30E MMU-off-visible startup object contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p30e-mmuoff-contract` |
| Status | `Buildbox-validated dormant implementation; owner handoff and physical-range proof pass; secondary_entry integration blocked` |
| Subsystem | arm64 late CPU8/CPU9 startup arbitration and target-side publication |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-06 America/New_York |
| Claim | `PARTIAL_P30E_MMUS_OFF_WIRE_CONTRACT` |

## Question

Can the dormant C-only P30 model be given one precise object that both the
MMU-on controller and the MMU-off target can observe, without duplicating
state or allowing a stale/ambiguous target result to reach P14/P15?

## Result

The contract defines a fixed word layout, one writer per field, exact token
binding, sequence/state transitions, cache maintenance and barrier order, and
fail-closed P30U publication. The controller and target share the object by a
physical address in a reserved, non-reclaimed region; neither side passes a
normal virtual pointer through the startup path. The dormant C object remains a
controller model only and cannot authorize a target result by itself.

The contract is validated by an independent finite oracle and 15 negative
mutations. The default-off C/assembly implementation now applies through the
canonical Linux 7.1.3 series and passes the Buildbox kernel-artifact package
validation; the exact result is recorded in
[Buildbox validation](results/buildbox-validation-20260806.txt). It still has
no production caller, CPU_ON/OFF operation, boot candidate, or device action.
The corrected implementation now passes the callable-flow and operation/MPIDR
identity comparison. Follow-up patch `0178` adds an explicit slot-physical
address to the controller request, validates it against the retained static
slot and alignment, and adds a separate target-identity sidecar that the
MMU-off path compares before publication. Patch `0179` binds the frozen
P17/P18/P24 transaction to a distinct READY-owned target expectation and exact
static slot address in a dormant owner-side handoff description. The handoff
does not arm P30E, call `secondary_entry`, issue CPU_ON/OFF, or change Linux
membership. Follow-up patch `0180` now proves the two-slot section is aligned,
non-overlapping with the directional MMU-off sections, and contained in the
`_text.._end` kernel-image range that arm64 reserves with memblock; the
controller-side helper rejects a slot outside those linker bounds. The
remaining integration gate is a separately reviewed `secondary_entry` binding
under the same owner. The complete current review is recorded in
[implementation comparison](results/implementation-contract-comparison-20260806.txt).

## Safety boundary

- `P30E_READY` is not an admission token; it only describes a valid wire
  object before the first CPU_ON.
- A header, token, generation, sequence, CRC, physical address, or state
  mismatch enters P30U and suppresses P14/P15.
- The target must publish failure before parking, and the controller must
  invalidate/read back the target publication before any membership commit.
- No retry or inverse is inferred from a malformed or non-returning target.
- The existing A26 boot veto, A14 disable veto, provider gate, and reset-only
  recovery remain unchanged.

## Associated files

- [P30E design](DESIGN.md)
- [Independent oracle](scripts/oracle.py)
- [Validation result](results/contract-validation-20260806.txt)
- [Pinned arm64 source-placement audit](results/source-placement-audit-20260806.txt)
- [Implementation seam audit](results/implementation-seam-audit-20260806.txt)
- [P30 generation model](../2026-08-05-a72-p30-generation-protocol/README.md)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-06-a72-p30e-mmuoff-contract/scripts/oracle.py
```

## Follow-up

The source audit selects a dedicated aligned bidirectional section with
separate 2 KiB CPU8/CPU9 slots. The implementation uses MPIDR `0x200` or
`0x201` in the dormant `.idmap.text` seam, validates the target CPU/MPIDR
words, and uses the full-range cache protocol. Buildbox now validates the
complete implementation package for this profile. The first comparison found
compile-invisible control-flow and identity gaps; those repairs now pass the
corrected comparison. Patch `0178` now makes the physical slot and target
identity checks explicit in the request/target seam; its Buildbox package is
recorded in the validation result. Patch `0179` now populates those fields in
the dormant owner-side handoff from the frozen transaction and a distinct
READY-owned expectation. Patch `0180` adds the linker and controller-side
range proof described above. The physical-slot/wire-identity audit is recorded in
[physical-slot review](results/physical-slot-wire-identity-audit-20260806.txt):
the remaining source-only gate is a separately reviewed `secondary_entry`
binding under the same owner, including its MMU-off address and publication
handoff. CPU8/CPU9 admission and device use remain blocked until that gate and
the broader A25/A26/A14/provider gates close.
