# Experiment: dormant A36 operation-specific prestate gate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-a36-prestate-gate` |
| Status | `completed` (source-only, static and bounded-model review) |
| Subsystem | MT6797 A72 P31/A28/frozen-token/A36 seam |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_A36_PRESTATE_GATE` |

## Question

Can the frozen CPU8/CPU9 transaction reject an operation-specific prestate
mismatch before P17/P18, while binding the exact generation, cookie, MPIDR, and
physical `secondary_entry` without reading or changing hardware?

## Result

Patch 0164 adds an immutable A36 prestate record and validates it after the
P31 -> A28 -> frozen-token sequence. CPU8 requires the exact one-way prestate:
DA921x page `0x80`, BUCKB disabled with VSEL `0x46`, SPM `0x218=0x00010132`,
SPM `0x290=0x00000002`, clear PWRAP reset and MP2 DCM, stable sentinels,
protected-clock and pstore readiness, and exclusive watchdog ownership.
CPU9 requires CPU8 online, CPU9 offline, inherited cluster/DCM publication,
an empty shared-write set, and the same watchdog ownership.

Both operations require the exact two-argument call shape, physical
`__pa_symbol(secondary_entry)`, target MPIDR, observer window, generation, and
cookie. A mismatch retires the frozen token as a terminal no-effect rejection
and cannot rearm the consumed attempt.

The patch performs no register read or write, provider or CPUHP effect,
P17/P18 publication, P30 operation, CPU_ON, build, package, candidate,
deployment, or device action.

## Provenance

- Patch: [0164](../../patches/v7.1.3/0164-arm64-validate-frozen-A72-A36-prestates.patch)
- Prepared source commit: `816311d70` (`arm64: validate frozen A72 A36 prestates`)
- Parent: [A36 frozen-token mint](../2026-08-05-a72-a36-frozen-token/README.md)
- Contract: [A72 membership/admission A36 row](../2026-08-05-a72-membership-admission-contract/results/admission-lock-contract.tsv)

## Safety and nonclaims

The prestate is caller-supplied evidence only. This slice does not implement
the owner-safe hardware observers, P27/P28 preparation, provider calls, P17,
P18, P24, P30, or any production opener. The A26 CPU-up veto remains in force.
The exact runtime prestate is therefore not proven and no CPU is enabled.

## Evidence

- [DESIGN.md](DESIGN.md) records the field-level contract and rejection edge.
- [Independent oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact validator](scripts/validate.py)
- [Source transcript](results/source-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-a36-prestate-gate/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-a36-prestate-gate/scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-a36-prestate-gate/scripts/validate.py
```

## Conclusion

`PARTIAL_A36_PRESTATE_GATE` is confirmed for the reviewed source and bounded
model. The next gate remains the authoritative P17/P18 transaction and its
P27/P28/provider implementation, while the current boot veto and no-device
policy remain unchanged.
