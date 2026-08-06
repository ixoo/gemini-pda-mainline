# Experiment: dormant P28 post-provider preparation

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-p28-postprovider-preparation` |
| Status | `Buildbox-validated` (compile-only; no hardware action) |
| Subsystem | MT6797 A72 post-provider isolation and SRAM preparation boundary |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_P28_POSTPROVIDER_PREPARATION` |

## Question

Can the exact CPU8 transaction consume a one-shot post-provider preparation
budget and require an ordered same-generation proof of isolation, PWRAP,
software-guard, SRAM-LDO, selector, and calibration preparation without
starting CPU_ON?

## Result

Patch 0169 adds a dormant C-only P28 ledger after R02. It requires `HELD` with
the durable provider identity, completed P27, zero members, CPU8, and an
available post-provider budget. Begin consumes that budget and publishes
`P28_STAGE_INFLIGHT`. Completion accepts only the exact effect mask and order:
isolation `0x2 -> 0x0`, PWRAP deasserted, owned software guard released, two
240 µs waits, 1.1 V SRAM-LDO request, selector `0x8fb`, and stable/valid
calibration readback bound to the held provider identity.

The ledger performs no isolation write, PWRAP/MMIO access, software-guard
mutation, SRAM-LDO service call, provider operation, CPUHP effect, P30 handoff,
or PSCI/CPU_ON call. P24 and real provider ownership remain closed.

## Provenance

- Patch: [0169](../../patches/v7.1.3/0169-arm64-model-dormant-A72-postprovider-preparation.patch)
- Prepared source commit: `afdcd6c9f`
- Parent: [R03/P29 refusal and rollback](../2026-08-05-a72-provider-refusal-rollback/README.md)
- Contract rows: [P28 phase contract](../2026-08-05-a72-membership-admission-contract/results/phase-contract.tsv)

## Safety and nonclaims

This is an attestation-shaped source ledger, not hardware support. It does not
claim a live isolation transition, SRAM voltage, provider vote, or CPU8
availability. It authorizes no candidate assembly, deployment, CPU_ON/CPU_OFF
request, or device action. P24, P14/P15, P30/P32, and real rollback ownership
remain open.

## Evidence

- [DESIGN.md](DESIGN.md) records the exact P28 boundary.
- [Independent oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact validator](scripts/validate.py)
- [Source transcript](results/source-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Buildbox validation](results/buildbox-validation-20260805.txt) (when recorded)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p28-postprovider-preparation/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p28-postprovider-preparation/scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p28-postprovider-preparation/scripts/validate.py
```

## Conclusion

`PARTIAL_P28_POSTPROVIDER_PREPARATION` is Buildbox-validated for the exact
pushed commit. The next gate is the real provider-owner and P24 transaction
integration; no hardware path is opened by this experiment.
