# Experiment: expose the CPU8 SRAM/P28 terminal boundary

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-31-mainline-a72-sram-p28-terminal-diagnostic` |
| Status | `canonical patch admitted; exact 49-test KUnit pass; production Buildbox gate pending` |
| Subsystem | MT6797 CPU8 binder, BigiDVFS SRAM owner, and P28 membership boundary |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-31 |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact isolation-result repair advanced the one-shot CPU8 transition from
stage 4 to stage 5 and returned `-EPROTO`. Which exact binder SRAM predicate or
surrounding P28 return boundary rejected the production result?

## Provenance and environment

- Parent: canonical Linux 7.1.3 series through patch `0451`.
- Parent source state:
  `a8e03cc2f0266b34115dce43d173860b76d5b8ad1e0fb8a76cb18f8e918aabbe`.
- Parent integrity:
  `b2059c466329a2b697aa4da60fa4624f901e56d47ffe7a6e0deb415975349d3d`.
- Build and patch generation backend: Buildbox only.
- Runtime source: the single-trigger result in the preceding
  [isolation held-result repair](../2026-08-30-mainline-a72-isolation-held-result-contract-repair/README.md).

## Safety assessment

The proposed change records return values and copies already-owned result
fields into the existing read-only status. It replaces the inline SRAM shape
condition with one equivalent helper that also emits a match mask. It does not
add or reorder a provider call, secure call, MMIO access, CPU request, CPU9
path, CPU_OFF path, retry, retained-RAM write, storage access, delay, watchdog
operation, or device action.

No physical candidate may be prepared until deterministic patch replay,
strict review, focused KUnit, and the exact production profile pass on
Buildbox. CPU9 remains vetoed until CPU8 is reproducibly online.

## Associated code

- `scripts/source_edits.py` applies the exact diagnostic-only source changes
  to the checksum-pinned post-`0451` files.
- `scripts/generate_patch.py` creates and replays canonical patch `0452`,
  verifies unchanged operation/request call counts, and rejects write paths.
- `scripts/generate-on-buildbox` pins the managed source state and clean
  project commit.
- `scripts/run-kunit-qemu` and `scripts/classify-kunit.py` accept only the
  exact fetched Buildbox package and the 30/12/7 focused suite inventory.

The generator writes only a temporary Git tree and a checksum-covered patch
review package on Buildbox. It performs no device access.

## Procedure

1. Generate one normal format-patch from the exact post-`0451` source.
2. Bump the read-only binder diagnostic ABI and expose P28 begin, SRAM-owner
   return, SRAM predicate-match, and P28 completion boundaries.
3. Expose every field of the SRAM owner result, including both selector and
   calibration reads and the attempt identity.
4. Reuse the same 12-bit match helper for the existing binder predicate so the
   reported mask and decision cannot diverge.
5. Cover malformed SRAM and successful P28 completion in binder KUnit.
6. Replay the patch, prove physical/request call counts unchanged, run focused
   KUnit on Buildbox, then build the exact live-trigger profile on Buildbox.

## Observations

- Candidate `510cb652...` passed the pristine gate, issued exactly one CPU8
  request, and returned `-EPROTO` at stage 5 (`SRAM`).
- The transition retained P27 and provider ownership; CPU8 and CPU9 remained
  offline, with zero CPU9, CPU_OFF, retry, or native reboot requests.
- Changed-ID Gemian recovery preserved a valid generation-10 terminal record
  at stage 5.
- The physical SRAM owner does not return `-EPROTO`; its distinct failures are
  service, readback, stability, range, ownership, and one-shot errors. The
  production P28 owner also uses `-EPERM` for a rejected state. The exact
  `-EPROTO` therefore narrows to the binder's P28-begun guard or SRAM result
  shape, but the current ABI exposes neither.
- Buildbox generated and deterministically replayed exactly one patch from the
  checksum-pinned post-`0451` source. The patch SHA-256 is `5aa5fe3b...`.
- Its audit finds the complete SRAM result, all 12 predicate bits, and all
  three return boundaries exposed while every physical and request call count
  remains unchanged.
- Strict Checkpatch reports zero warnings and zero checks. Its sole error is
  the deliberately absent DCO sign-off for the synthetic experiment author;
  this internal archive is not submission-ready.
- All 158 manifest profiles remain canonical-order subsequences, and eight
  invariant mutations are rejected.
- Buildbox built the exact `a72-default-off-binder-kunit` profile from patch
  commit `404807a5...`; the fetched package passed all checksum and provenance
  checks.
- The isolated no-network QEMU run passed all 49 expected tests: 30 P24 owner,
  12 transition executor, and 7 binder cases, including the new SRAM terminal
  diagnostic. It issued zero physical CPU, CPU_OFF, or retry requests. See the
  [KUnit result](results/kunit-qemu-404807a5-20260831.txt).

## Analysis

A repair would be premature. Although successful owner code appears to
construct every binder-required field, runtime has disproved that assumption
at the aggregate predicate. A complete raw result plus a predicate-match mask
will show whether the mismatch is ABI, step masks, voltage, selector, attempt
identity, error, attempted effect, verified state, or seal state. Explicit
attempt/return markers distinguish that shape rejection from either P28
boundary without another inference.

## Conclusion

The next valid experiment is diagnostic-only. It must make one future stage-5
terminal result self-decoding before any contract repair is selected. The
prior candidate is retired and must not be repeated.

## Follow-up

Build the exact production profile on Buildbox. Prepare at most one new boot2
candidate after its offline diagnostic contract is complete. Retain the CPU9
veto.
