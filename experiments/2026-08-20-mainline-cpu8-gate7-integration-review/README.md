# Experiment: mainline CPU8 Gate-7 integration review

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-20-mainline-cpu8-gate7-integration-review` |
| Status | `completed` offline review; pre-P28 positive-provider abort is the next source slice |
| Subsystem | MT6797 Cortex-A72 CPU8 owner, DA921x Buck B, P27/P28, P24/P30 |
| Device variant | Planet Gemini PDA named development unit |
| Date(s) | 2026-08-20 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7 |

## Question or hypothesis

After the positive DA921x provider passes its isolated fake-adapter proof, can
current Linux 7.1 safely connect it directly to P28 and CPU8, or is there a
smaller missing production-owner boundary that must be implemented first?

The falsifiable claim is that current source can publish a successful acquire
as `HELD`, but cannot yet retire that vote and the P27 prefix if the same CPU8
transaction stops before P28. Therefore neither P28 nor CPU_ON is admissible.

## Provenance and environment

- Repository revision:
  `d3c2aeecbbce5f8feaf7d00549580d318e7e03e6`.
- Kernel baseline: Linux 7.1.3 and the canonical 287-entry patch series.
- Exact manifest, series, source-patch, provider-QEMU, membership-contract,
  A41, source-closure, and safe-off hashes are pinned in
  [`contract.json`](contract.json).
- The audit reads repository files and canonical patches only. It does not
  treat the reused Buildbox source tree as exact source evidence.
- No compiler, kernel build, package, boot image, device endpoint, partition,
  CPU request, or hardware register was used.

During the review, the reused Buildbox prepared tree had a matching input-state
marker but retained the pre-0294 `ARM64_MT6797_A72_PROVIDER_OWNER` help text.
The positive provider implementation and compiled Image were present, so this
specific observation is documentation-only; it does not establish the scope
of any other drift. Commit `d3c2aeecbbce5f8feaf7d00549580d318e7e03e6`
repairs the wrapper so reuse additionally requires a recursive content, mode,
path, and symlink digest. Buildbox DNS was unavailable before the corrected
tree could be reconstructed, so that remote validation remains deferred and
no VM fallback was used.

## Safety assessment

This review is repository-only and read-only with respect to the device. It
authorizes no kernel build on the VM, physical DA921x write, P27/P28 effect,
CPU_ON, CPU_OFF, boot image, boot2 write, reboot, or shutdown. CPU8 and CPU9
remain behind the A26 boot veto; the A14 disable veto remains mandatory.

The selected implementation slice is also hardware-free and default-off. Its
tests must use a fake adapter through the production registry seam. A physical
provider call remains a later, separate admission decision.

## Associated code

- [`DESIGN.md`](DESIGN.md) freezes the current gap and exact next state edges.
- [`contract.json`](contract.json) pins identities, safety gates, decisions,
  and the next implementation boundary.
- [`results/integration-matrix.tsv`](results/integration-matrix.tsv) separates
  complete, partial, and missing current-mainline ownership.
- [`scripts/validate.py`](scripts/validate.py) verifies the pinned inputs,
  canonical ordering, source semantics, matrix, contract, and safety markers.
- [`results/audit-validation-20260820.txt`](results/audit-validation-20260820.txt)
  records the sanitized validator result.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  experiments/2026-08-20-mainline-cpu8-gate7-integration-review/scripts/validate.py
```

## Procedure

1. Pin the exact positive-provider QEMU receipt and all current owner/provider
   source patches by SHA-256.
2. Trace the selected profile from A41 and P30 through the closed owner,
   admission hooks, provider registry, stopped-firmware window, and positive
   provider transaction.
3. Enumerate the owner state after every returned acquire outcome and compare
   it with the available release and P29 edges.
4. Test whether any current source edge can release a successful CPU8-up vote
   before P28 and then retire the P27 prefix.
5. Preserve the A41, P24/P30, A26, A14, P27-executor, and P28-executor gaps as
   independent later boundaries.
6. Select the smallest default-off hardware-free slice that closes the first
   unsafe gap without enabling P28 or CPU_ON.

## Observations

- The positive provider itself is implemented and its exact isolated QEMU run
  passes all six cases, including both successful acquire/release and every
  injected failure/mismatch family.
- `mt6797_a72_membership_run_provider_acquire()` can consume R01, call the
  registered provider, validate a successful response, and publish R02
  `HELD` with the exact generation/cookie handle.
- Only the legacy `-EOPNOTSUPP` response has a clean owner path: R03 returns
  provider state to `NONE`, after which P29 accepts the exact P27 rollback and
  retires the transaction as rejected.
- Any other returned acquire error or malformed positive response is returned
  to the caller after R01 has published `ACQUIRE_INFLIGHT`; current source does
  not publish `FAULT_UNKNOWN` or a transaction fault for that outcome.
- The registry exports `mt6797_a72_provider_release()`, and the DA921x provider
  implements exact-handle release. No membership function calls it.
- CPU8-up has no pre-P28 provider-abort budget or positive-release proof. P29
  requires `provider_state=NONE` plus `provider_rejection_valid`; it cannot
  retire a successfully acquired and then released vote.
- P27 and P28 are attestation ledgers, not hardware executors. P28 begins only
  from `HELD` and immediately consumes the post-provider budget before its
  future isolation/SRAM sequence.
- A41 cannot publish READY, P24/P30 have no production caller, the owner has no
  production `CLOSED -> AVAILABLE` writer, and patch 0092 still returns
  `-EAGAIN` before CPU_ON while prohibiting CPU disable.

## Analysis

The isolated provider proof closes its internal state machine, but it does not
close the transaction owner around that state machine. Starting P28 from the
current `HELD` edge would create an unsafe gap: a pre-isolation stop has no
membership-owned exact release and P27-retirement path, while an ambiguous
acquire return lacks an explicit fail-stop publication.

The first new production seam must therefore remain before P28. It needs to:

1. classify every returned non-refusal acquire error or invalid success as
   `provider=FAULT_UNKNOWN`, transaction `FAULT`, reset-only, with no retry;
2. add one CPU8-up-only pre-P28 abort budget;
3. publish `RELEASE_INFLIGHT` before calling release with the exact R02 handle;
4. accept only the complete exact release response and then clear the durable
   provider identity;
5. let P29 retire the P27 prefix only with either the existing R03 refusal or
   the new exact positive-abort proof; and
6. exercise these edges through the production registry and positive DA921x
   transaction on an unregistered fake adapter.

This slice changes no production reachability because the lifecycle owner
remains closed and has no caller. It is nevertheless production-seam code,
not a standalone model: the test must traverse the same registry, response,
handle, owner-state, and inverse functions later hardware execution would use.

## Conclusion

`rejected` for direct P28 or CPU8 integration at current mainline revision
`d3c2aeecbbce5f8feaf7d00549580d318e7e03e6`.

`confirmed` for the next source boundary: implement and exhaustively test the
default-off, hardware-free pre-P28 positive-provider abort and terminal-fault
mapping described above. The current A26/A14 vetoes, closed lifecycle owner,
P27/P28 executor gaps, A41 blockers, and absence of P24/P30 CPU_ON integration
remain unchanged.

## Follow-up

The authoritative order and exit criteria are in
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8). This review does not
authorize a device candidate or physical execution.
