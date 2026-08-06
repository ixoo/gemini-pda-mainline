# Experiment: dormant A72 provider acquire ledger

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-provider-acquire-ledger` |
| Status | `completed` (source, static, bounded-model, and Buildbox validation) |
| Subsystem | MT6797 A72 R01/R02 provider-owner boundary |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_R01_R02_PROVIDER_LEDGER` |

## Question

Can the exact CPU8 transaction publish the one-shot provider acquire boundary
and retain a durable same-generation `HELD` identity without making a provider
call, changing membership, or starting P28/CPU_ON?

## Result

Patch 0167 adds two dormant C-only edges after completed P27. R01 requires
`ON_ISSUED`, CPU8, `members=0`, provider `NONE`, completed P27, and the
available acquire budget. It consumes that budget and publishes
`ACQUIRE_INFLIGHT` before the future synchronous call boundary. R02 accepts
only the same transaction identity plus an exact proof of the inherited 1 ms
settle, DA921x page `0x80`, BUCKB enabled, VSEL `0x46`, M01 origin, and a new
nonzero durable reference identity. It then publishes `HELD` while membership
remains `0x0`.

The proof object is an attestation-shaped source record; this patch performs no
provider call, regulator vote, MMIO access, CPUHP effect, P28 isolation/SRAM
operation, P30 handoff, or PSCI/CPU_ON call. KUnit coverage proves the one-shot
R01/R02 path and rejects malformed proof fields and CPU9. R03 rejection and
P29 rollback remain intentionally unimplemented.

## Provenance

- Patch: [0167](../../patches/v7.1.3/0167-arm64-model-dormant-A72-provider-acquire.patch)
- Prepared source commit: `7201af73e` (`arm64: model dormant A72 provider acquire`)
- Parent: [P27 preparation ledger](../2026-08-05-a72-p27-preparation-ledger/README.md)
- Contract: [provider rows](../2026-08-05-a72-membership-admission-contract/results/provider-contract.tsv)

## Safety and nonclaims

`HELD` here is only an owner-model state based on caller-supplied proof; it is
not runtime regulator evidence. R03/P29 failure and rollback, P28, P24
CPU_ON, secondary completion, P14/P15, P30/P32, and A41 closures remain open.
This experiment does not authorize candidate assembly, deployment, or device
action.

## Evidence

- [DESIGN.md](DESIGN.md) records the exact R01/R02 boundary.
- [Independent oracle](scripts/oracle.py)
- [Mutation runner](scripts/test_mutations.py)
- [Exact validator](scripts/validate.py)
- [Source transcript](results/source-validation-20260805.txt)
- [Mutation transcript](results/mutation-validation-20260805.txt)
- [Buildbox validation](results/buildbox-validation-20260805.txt)

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-provider-acquire-ledger/scripts/oracle.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-provider-acquire-ledger/scripts/test_mutations.py
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-provider-acquire-ledger/scripts/validate.py
```

## Conclusion

`PARTIAL_R01_R02_PROVIDER_LEDGER` is confirmed for the reviewed source,
bounded model, and exact pushed-commit Buildbox compile. The package is not a
boot candidate: no deployment or device action is authorized by this result.
The next gate is the explicit R03/P29 refusal-and-rollback edge, followed by
P28 only after a real provider-owner implementation exists.
