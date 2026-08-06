# Experiment: P30E MMU-off-visible startup object contract

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-06-a72-p30e-mmuoff-contract` |
| Status | `source-only contract complete; production integration blocked` |
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
mutations. It does not add an assembly implementation, a production caller,
CPU_ON/OFF operation, build, package, boot candidate, or device action.

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
- [P30 generation model](../2026-08-05-a72-p30-generation-protocol/README.md)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-06-a72-p30e-mmuoff-contract/scripts/oracle.py
```

## Follow-up

Implement the object in a dedicated assembly/C patch only after the exact
linker placement, target entry point, cache operations, and architecture
barriers are reviewed against the selected Linux source. Then compare that
implementation to this contract and the P30 model with Buildbox. Until that
comparison passes, CPU8/CPU9 admission and device use remain blocked.
