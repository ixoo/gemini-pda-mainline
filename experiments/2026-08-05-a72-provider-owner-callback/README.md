# Experiment: A72 provider-owner callback refusal

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-05-a72-provider-owner-callback` |
| Status | `running` (source and static validation; Buildbox pending) |
| Subsystem | MT6797 A72 R01/R02 provider-owner callback boundary |
| Device variant | Planet Gemini PDA, MT6797; no live-device action |
| Date | 2026-08-05 America/New_York |
| Claim | `PARTIAL_R01_R02_PROVIDER_CALLBACK_REFUSAL` |

## Question

Can the dormant A72 owner invoke a registered provider-owned callback and
classify the current read-only DA921x provider's refusal without using a
consumer supply mapping, changing membership, writing a rail, or issuing
CPU_ON?

## Result so far

Patch 0172 adds a private platform-scoped callback registry owned by the A72
transaction model. The owner consumes R01 before the synchronous call, invokes
the registered provider outside the state spinlock, accepts R02 only from an
exact response, and converts a structured `-EOPNOTSUPP` response with no vote
or mutation into the existing R03 refusal state. The DA921x resource-only
provider registers that callback only in this named profile and deliberately
returns the refusal; it performs no regulator operation.

This is the first real provider-owner call boundary, but it is not a writable
provider and does not make CPU8/CPU9 admissible. P29 completion, a writable
rail transaction, P28 hardware sequencing, P24 CPU_ON, and device validation
remain closed.

## Provenance

- Patch: [0172](../../patches/v7.1.3/0172-arm64-add-provider-owner-callback-refusal-boundary.patch)
- Patch SHA-256: `becd82625a362af8bf46e91cfb6bfe439fc72b6fec612fcbd3c2eaf9d7b1ce87`
- Patch bytes: `13512`
- Source commit used to generate the patch: `826f6ef07`
- Profile: `a72-p24-provider-owner-refusal`
- Series: [series-a72-p24-provider-owner-refusal](../../patches/series-a72-p24-provider-owner-refusal)

## Safety and nonclaims

The callback is default-off and isolated to the named profile. The current
provider callback returns before-vote refusal and never calls a writable
regulator operation, page selection, MMIO path, CPUHP path, PSCI, or CPU_ON.
No boot candidate is assembled, no partition is written, and no device action
is authorized by this experiment.

## Evidence

- [DESIGN.md](DESIGN.md) defines the request/response and lifetime contract.
- [Static oracle](scripts/oracle.py)
- [Source validation](results/source-validation-20260805.txt)
- Buildbox validation will be recorded here before any later lifecycle work.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 experiments/2026-08-05-a72-provider-owner-callback/scripts/oracle.py
```

## Conclusion

The callback/refusal seam is source-complete and statically bounded. The claim
remains provisional until the exact pushed commit passes the named Buildbox
profile. Even after that compile result, the device remains out of scope.

## Follow-up

After Buildbox validation, the next gate is a separately reviewed provider
implementation that can attest a real owned rail transaction and its inverse;
only then can P29/P28 integration be reconsidered. The current read-only
provider must not be upgraded by inference from this result.
