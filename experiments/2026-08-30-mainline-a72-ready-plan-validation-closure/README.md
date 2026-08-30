# Experiment: close the stale READY plan-validation predicate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-plan-validation-closure` |
| Status | `running` |
| Subsystem | arm64 late-CPU profile validation |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Does the production MT6797 late-CPU plan remain blocked after exact runtime
identity succeeds because its validator still requires the historical
`ARM64_LATE_CPU_BLOCK_ATTESTATION_USERS` bit that patch `0434` removed from the
production profile blocker set?

The source hypothesis is falsifiable: exact runtime mask `0x24000` must decode
to plan validation plus the downstream identity-withheld bit, and the prepared
source must contain that stale required-bit predicate. Removing only that
predicate and its now-unused allowed-mask member must accept the zero-blocker
production evidence while preserving all configuration, topology, fixture,
runtime-binding, CPU8-only, and CPU9-veto gates.

## Provenance and environment

- Runtime candidate: exact boot2 SHA-256 `f694ddb9...`, kernel release
  `7.1.3-gemini-a72-admission-live`.
- Runtime boot ID: `bbb23e82-7f3f-4985-810b-8a61b01734e0`.
- Parent kernel series: canonical Linux 7.1.3 through patch `0436`.
- Parent prepared source state: `0dfa06a3...`.
- Parent `mt6797_psci.c` SHA-256: `da539721...`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The source repair is hardware-free and changes one pure validation predicate.
It adds no CPU request, CPU9, retry, CPU_OFF, storage, retained-RAM, reboot, or
firmware path. The runtime attempt was read-only except for the owner-authorized
USB-shell reboot to known-good Gemian after the frame was captured. The
controller remained armed and unconsumed with zero CPU requests.

Any later candidate remains subject to exact package, container, live-GPT,
inactive boot2, power, write, readback, and clean-shutdown gates. CPU9 remains
vetoed until CPU8 has an attributable result.

## Associated code

- `scripts/source_edits.py`: exact-parent, one-file stale-predicate removal.
- `scripts/validate_source.py`: validates the production zero-blocker truth
  table, the unchanged fixture closure, and absence of request-path changes.
- `scripts/test_mutations.py`: rejects stale-bit, overbroad-mask, fixture, and
  CPU-action mutations.
- `scripts/generate_patch.py`: creates one deterministic format-patch, runs
  strict checkpatch, replays it, and packages checksum-covered review evidence.
- `scripts/generate-on-buildbox`: pins the managed post-`0436` source and emits
  only the validated patch-review package.

## Procedure

1. Preserve the attempt-2 observer, pre-trigger frame, and exact blocker lines.
2. Decode `0x24000` against the current blocker definitions and lifecycle order.
3. Generate one patch from the exact post-`0436` source on Buildbox.
4. Reject mutations that reintroduce the stale required bit, admit an unrelated
   blocker, alter the fixture closure, or add a CPU action.
5. Admit the patch canonically, audit all manifest profiles, and build the
   default and exact live-trigger profiles on Buildbox.
6. Recompose the package-owned provenance leaf with the proven serviceability
   DT, then require a new exact live READY frame before one CPU8-only trigger.

## Observations

Attempt 2 proved a real boot2 start, a long intermediate `0x0e8d:0x20ff`
session, and eventual exact mainline USB. The immutable pre-trigger frame
matched the installed candidate, provenance leaf, running identity, release,
boot ID, serviceability, controller, and zero-execution state. It rejected
only because `profile_blocked_count=1`.

Same-boot dmesg reports one successful runtime-identity verification followed
by proof mask `0x24000`. That is bit 17 (`PLAN_VALIDATION`) plus bit 14
(`SOURCE_IDENTITY`). The lifecycle computes bit 14 whenever validation fails
and therefore identifies bit 17 as the initiating failure.

The exact prepared source confirms the contradiction: production preparation
starts with only `RUNTIME_BINDING`, and successful runtime cross-binding clears
it, while `mt6797_a72_evidence_is_bound_expectation()` still requires
`ATTESTATION_USERS` to be set. Patch `0434` intentionally removed that bit from
the production blocker set when the finalization callbacks became the owner.
See
[`results/runtime-attempt-2-stale-plan-validator-20260830.txt`](results/runtime-attempt-2-stale-plan-validator-20260830.txt).

Buildbox generated canonical patch `0437` from repository commit
`3039a42e1d0558eba9a2c0b098764c512a065f10` and the exact post-`0436`
prepared source. Source validation and strict checkpatch passed, replay was
identical, zero-blocker production evidence was accepted, and all six unsafe
mutations were rejected. The patch adds no CPU request, CPU9, CPU_OFF, or retry
path. See
[`results/buildbox-generation-20260830.txt`](results/buildbox-generation-20260830.txt).

## Analysis

The boot and runtime-provenance hypotheses passed. The seven-minute `0x20ff`
dwell was latency, not a loader failure. No DT or container control is needed.
The remaining failure is deterministic and source-local: a historical
fail-closed predicate was not updated with the same lifecycle transition as
the production blocker macro.

Accepting zero blockers in this helper does not bypass a safety gate. The core
still rejects any nonzero blocker before freezing or committing a plan, while
configuration and topology remain the only conditionally permitted inputs to
the pure validator so their existing core-owned rejection path is preserved.

## Conclusion

`confirmed-stale-plan-validation-predicate`: exact candidate `f694ddb9...`
reached mainline and verified runtime identity, but READY was unreachable due
to the stale `ATTESTATION_USERS` requirement. CPU8 was not requested and the
candidate must not be repeated.

## Follow-up

Generate and admit one post-`0436` source patch removing only the stale
production predicate and its unused allowed-mask member. Patch `0437` now
contains that exact repair as an experiment-only archive with a synthetic,
non-certifying author and no DCO sign-off; it is not submission-ready. Audit all
manifest profiles and build on Buildbox, reuse the proven composed DT and
serviceability ramdisk, then require exact READY qualification before one
CPU8-only trigger. Keep CPU9 vetoed.
