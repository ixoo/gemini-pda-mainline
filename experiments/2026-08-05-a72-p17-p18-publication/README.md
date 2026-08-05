# Experiment: dormant A72 P17/P18 publication ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-p17-p18-publication` |
| Status | `completed` (source-only, static and bounded-model review) |
| Subsystem | MT6797 A72 frozen transaction and provider publication seam |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_P17_P18_PUBLICATION` |

## Question

Can the frozen transaction publish the exact pre-effect `ON_ISSUED` phase while
preserving the provider contract, before any P27/P28, provider, CPUHP, or
PSCI/CPU_ON operation?

## Result

Patch 0165 adds a dormant C-only publication edge after A36. CPU8/P17 accepts
only provider state `NONE` and an empty provider identity. CPU9/P18 accepts
only provider state `HELD` and the exact durable provider identity copied into
the transaction at mint. The publication is one-shot: it advances the owner to
`ON_ISSUED`, records `p17_p18_published`, and rejects a second publication.

The KUnit-only CPU9 seed is a synthetic M01 identity; it performs no provider
call. No provider acquire/release, hardware or CPUHP effect, P27/P28 action,
P30 handoff, PSCI/CPU_ON call, build, package, deployment, or device action is
present. The A26 CPU-up veto remains active.

## Provenance

- Patch: [0165](../../patches/v7.1.3/0165-arm64-publish-dormant-A72-P17-P18-phases.patch)
- Prepared source commit: `07b50996f` (`arm64: publish dormant A72 P17 P18 phases`)
- Parent: [A36 prestate gate](../2026-08-05-a72-a36-prestate-gate/README.md)
- Contract: [P17/P18 and provider rows](../2026-08-05-a72-membership-admission-contract/DESIGN.md)

## Safety and nonclaims

`ON_ISSUED` is only a C ledger phase in this experiment. It does not arm P30,
invoke a provider, change membership, run CPUHP, issue CPU_ON, or establish a
successful CPU-up. The P27/P28 preparation, provider implementation, P24
CPU_ON boundary, P14/P15, P30/P32, and A41 closures remain open.

## Evidence

- [DESIGN.md](DESIGN.md) records the publication and provider invariants.
- [Independent oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact validator](scripts/validate.py)
- [Source transcript](results/source-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p17-p18-publication/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p17-p18-publication/scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-p17-p18-publication/scripts/validate.py
```

## Conclusion

`PARTIAL_P17_P18_PUBLICATION` is confirmed for the reviewed source and bounded
model. The next implementation gate is P27/P28 and the real provider-owner
transaction; this milestone does not authorize a build or device action.
