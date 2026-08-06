# Experiment: dormant A72 P27 preparation ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-p27-preparation-ledger` |
| Status | `completed` (source-only, static and bounded-model review) |
| Subsystem | MT6797 A72 frozen transaction and preprovider preparation seam |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_P27_PREPARATION_LEDGER` |

## Question

Can the published CPU8 transaction consume its one-shot P27 preparation budget
and record the exact preprovider prefix without invoking a provider, changing
membership, or issuing CPU_ON?

## Result

Patch 0166 adds a dormant C-only two-edge ledger. The begin edge requires the
published CPU8 transaction, conservative `members=0`, provider `NONE`, and an
available preparation budget; it consumes that budget before any real P27
effect. The completion edge accepts only the same generation/cookie and the
exact ordered-prefix attestation: MP2 reset release, B-PLL ordering read, and
owner-locked PWRAP assertion. The ledger remains `ON_ISSUED` and records no
hardware operation itself.

KUnit coverage proves one-shot consumption, rejects a malformed effect mask
without changing the owner, and rejects CPU9. The patch contains no provider
call, regulator vote, MMIO access, CPUHP effect, P30 handoff, or PSCI/CPU_ON
call. The A26 CPU-up veto remains active.

The exact pushed commit was then compiled on Buildbox using the full profile.
All 155 canonical patches applied, the package validator passed, and no
candidate was assembled or deployed. The build is compile evidence only.

## Provenance

- Patch: [0166](../../patches/v7.1.3/0166-arm64-record-dormant-A72-P27-preparation.patch)
- Prepared source commit: `16d7eb1ec` (`arm64: record dormant A72 P27 preparation`)
- Parent: [P17/P18 publication ledger](../2026-08-05-a72-p17-p18-publication/README.md)
- Contract: [P27 row](../2026-08-05-a72-membership-admission-contract/results/phase-contract.tsv)

## Safety and nonclaims

The preparation record is an attestation-shaped C object, not evidence that
the device registers changed. P27/P28 provider-owner integration, R01/R02,
P24 CPU_ON, secondary completion, P14/P15, P30/P32, and A41 closures remain
open. This experiment does not authorize candidate assembly, deployment, or
device action.

## Evidence

- [DESIGN.md](DESIGN.md) records the exact ledger boundary.
- [Independent oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact validator](scripts/validate.py)
- [Source transcript](results/source-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Buildbox transcript](results/buildbox-validation-20260805.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p27-preparation-ledger/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p27-preparation-ledger/scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p27-preparation-ledger/scripts/validate.py
```

## Conclusion

`PARTIAL_P27_PREPARATION_LEDGER` is confirmed for the reviewed source, bounded
model, and Buildbox compile. The next implementation gate is P28 plus the
real provider R01/R02 transaction; that work must remain dormant until its
failure and rollback contract is separately represented.
