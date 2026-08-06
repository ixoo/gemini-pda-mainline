# Experiment: dormant R03/P29 provider refusal and rollback

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-provider-refusal-rollback` |
| Status | `source-only` (static and bounded-model review; Buildbox pending) |
| Subsystem | MT6797 A72 provider refusal and pre-isolation rollback boundary |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_R03_P29_REFUSAL_ROLLBACK` |

## Question

Can a returned CPU8 provider refusal be accepted only when it proves that no
consumer vote or rail mutation occurred, then record exact restoration of every
P27 effect without starting P28 or CPU_ON?

## Result

Patch 0168 adds two dormant C-only edges after R01. R03 requires the exact
`ACQUIRE_INFLIGHT` CPU8 transaction, consumed acquire budget, completed P27,
zero members, and a same-generation returned-before-vote rejection with no
provider or rail mutation. It restores the provider ledger to `NONE` while
leaving the transaction in `ON_ISSUED` until P29 is proven.

P29 then requires the same transaction identity, the recorded R03 refusal,
exact restoration of the complete P27 effect mask with zero residual effects,
and explicit proof that P28 and CPU_ON never started. It records the rollback,
retires the generation as `REJECTED`, preserves the consumed one-shot budgets,
and does not rearm the attempt. The C code performs no provider call, MMIO,
regulator operation, isolation/SRAM operation, CPUHP effect, P30 handoff, or
PSCI/CPU_ON operation.

## Provenance

- Patch: [0168](../../patches/v7.1.3/0168-arm64-model-dormant-A72-provider-refusal-rollback.patch)
- Prepared source commit: `847682ea4`
- Parent: [R01/R02 provider ledger](../2026-08-05-a72-provider-acquire-ledger/README.md)
- Contract rows: [R03 and P29 provider rows](../2026-08-05-a72-membership-admission-contract/results/provider-contract.tsv)

## Safety and nonclaims

This is a source-only owner ledger. It is not a provider implementation and
does not claim that any live rail was restored. It authorizes no candidate
assembly, deployment, CPU_ON/CPU_OFF request, or device action. P28 isolation
and SRAM sequencing, the real provider owner, P24 CPU_ON, P14/P15, P30/P32,
and reset-only recovery remain open.

## Evidence

- [DESIGN.md](DESIGN.md) records the exact R03/P29 contract.
- [Independent oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact validator](scripts/validate.py)
- [Source transcript](results/source-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Buildbox validation](results/buildbox-validation-20260805.txt) (when recorded)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-provider-refusal-rollback/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-provider-refusal-rollback/scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-provider-refusal-rollback/scripts/validate.py
```

## Conclusion

`PARTIAL_R03_P29_REFUSAL_ROLLBACK` is source-only until the exact pushed commit
passes Buildbox. The next implementation gate is P28's ordered isolation and
SRAM boundary; no hardware path is opened by this experiment.
