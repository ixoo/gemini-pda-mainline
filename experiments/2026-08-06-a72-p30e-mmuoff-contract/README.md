# Experiment: P30E MMU-off-visible startup object contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p30e-mmuoff-contract` |
| Status | `Buildbox-validated dormant implementation; production integration blocked` |
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
identity comparison. The physical-slot and wire-identity review found that the
controller API still lacks an explicit slot-physical-address handoff and the
MMU-off side lacks an independent expected boot identity; entry-path and
P17/P18/P24 integration therefore remain blocked. The complete current review
is recorded in
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
corrected comparison. The physical-slot/wire-identity audit is recorded in
[physical-slot review](results/physical-slot-wire-identity-audit-20260806.txt):
the authoritative P17/P18/P24 owner must still define the slot physical
handoff and an independent boot-identity expectation before entry integration
can be reviewed. CPU8/CPU9 admission and device use remain blocked until
those gates close.
