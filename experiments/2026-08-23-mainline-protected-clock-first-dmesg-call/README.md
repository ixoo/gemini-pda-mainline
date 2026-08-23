# Experiment: protected clock call in first dmesg

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-protected-clock-first-dmesg-call` |
| Status | exact candidate independently validated; deployment pending |
| Subsystem | MT6797 protected clock readback, CSPM handoff, retained RAM |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-23 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, one protected clock read |

## Question or hypothesis

Does exactly one protected clock snapshot return successfully when it executes
through the runtime-qualified single-owner CSPM handoff while the complete
I2C6/DA921x serviceability baseline remains available?

The clock-only observer and its `before-clock`/`after-clock` call sites already
exist. Its earlier artifact was inconclusive because the records occupied
sparse dmesg zones 173 and 174, which the downstream recovery reader could not
enumerate. Records 1 and 2, signature-last commit, warm retention, downstream
enumeration, read-free clock entry, and CSPM coexistence are now independently
qualified. This successor changes only the record positions and identities.

## Exact discriminator

1. Commit record 1 immediately before the existing single clock call.
2. Execute that call through the handoff-owned CSPM callback.
3. Commit record 2 only after the call returns.
4. Publish the existing complete raw clock record and terminal receipt if USB
   serviceability is reached.

The observer's existing clock-only mode makes one clock call, zero BigiDVFS
calls, zero retries, and no owner or CPU request. The candidate DT will enable
only the clock backend and observer; the compiled BigiDVFS transport remains
disabled in DT and no secure call is permitted.

## Decision map

- Exact records 1 and 2 plus one successful ABI-1/generation-1 live clock
  record qualify the protected clock transport for later composition.
- Record 1 only proves call entry and localizes a non-returning reset to the
  clock transaction; do not add BigiDVFS or retry it unchanged.
- Neither record rejects attribution before the call.
- Any duplicate call, BigiDVFS bind/call, missing handoff/I2C6/DA921x service,
  ownership conflict, malformed record, write, retry, or CPU action rejects
  the candidate.

## Patch-generation boundary

The first phase generates one normal format-patch from the exact Buildbox
prepared source through canonical patch `0335`. The patch may edit only pstore
Kconfig and the existing retained-ledger record selection. It adds no writer,
observer call site, transport operation, DT enable, or runtime trigger.

The generated patch uses a clearly synthetic, non-certifying experiment author
without a DCO sign-off and remains not submission-ready. Generation performs no
kernel build, candidate construction, device access, or hardware action.

## Build and candidate

Buildbox produced exact release `7.1.3-gemini-clock-one-read` from repository
commit `da8cad285d7c92d7dcd1d0cecc104d2f8908308a`; no native VM build was run.
Only the validated package was fetched. See the
[Buildbox result](results/buildbox-build-pass.txt).

The deterministic Android-v0/LK candidate combines that package with the
unchanged serviceability ramdisk and a reproducible DT that enables the
single-owner clock backend plus the clock-only observer. BigiDVFS is compiled
only as the observer's link dependency and remains disabled in DT. Exact
padded boot2 SHA-256 is
`3892e776c183027851d73bec8bf938732c43ddad030a80ddee42240537ba35f6`.
All 32 LK gates and 23 independent DT mutations passed; see the
[candidate result](results/candidate-validation-pass.txt).

This candidate is deliberately not read-free. It performs one bounded
handoff-owned CSPM clock snapshot, including the existing semaphore polling
inside that single transaction and one I2C clock enable/disable pair. It makes
zero observer retries, BigiDVFS calls, secure calls, DA921x data writes, or CPU
requests.

## Deployment and runtime procedure

The guarded installer requires both retained-RAM record headers to be exactly
empty, resolves logical `boot2` from the live GPT, records the predecessor
checksum without making a fresh backup, writes only when needed, verifies a
matching full-partition readback, and shuts down after success. It never
automatically reboots after the write.

One physical boot has two independent result paths:

1. The read-only USB/netcat probe requires one complete ABI-1/generation-1
   clock snapshot, one exact terminal receipt with one clock call and zero
   BigiDVFS calls, full USB/keyboard/I2C6/DA921x serviceability, and exactly one
   CSPM and MCUMIXED owner.
2. After the bounded native return to a changed-ID Gemian boot, direct retained
   RAM must contain exact `before-clock` record 1 and `after-clock` record 2;
   pstore enumeration is recorded separately and may be either available or
   absent without weakening the direct-RAM attribution.

The runtime tools accept one exact live result and two bounded retained
recovery forms. They reject 51 unsafe live mutations and 12 retained-record
mutations offline.

## Current boundary

The exact candidate and its deployment/runtime tooling are admitted offline.
Deployment preflight 1 failed closed before any partition write because records
1 and 2 still contained the exact checkpoints from the successful predecessor
coexistence boot. Read-only inspection attributed both records exactly. Gemian
was then shut down cleanly so an ordinary cold start can clear retained RAM
without a `/dev/mem` write. No protected-clock runtime result is claimed here
yet. See the [safe refusal](results/deployment-preflight-1-stale-coexistence-records.txt).
The ordered execution sequence remains owned by
[Roadmap Gate 7](../../docs/ROADMAP.md#7-bring-up-cpu8).

Generation attempt 1 at exact commit `ee05a0f3` stopped in the Buildbox wrapper
before source validation because Bash rejected a multiline conditional. No
source edit or review artifact was created. The condition is split into exact
file-safety and value checks for the next attempt; see the
[rejected tooling attempt](results/generation-attempt-1-shell-condition-rejected.txt).

Attempt 2 at exact commit `698877be` passed source semantics, patch shape, and
byte-identical replay. Strict checkpatch then rejected only two `SPLIT_STRING`
warnings for the fixed atomic retained-record literals. The implementation is
unchanged for the next attempt; its review command now carries the same narrow,
provenance-recorded exception used by the earlier atomic record patches. See
the [review-policy rejection](results/generation-attempt-2-split-string-review-rejected.txt).

Attempt 3 at exact commit `0e84916b` passed source semantics, patch shape,
byte-identical replay, and the narrow recorded checkpatch policy. Manual review
admitted exact patch SHA-256
`97394ab84b4f0fc68f69388a8456a6f82321f2597405b9f23c253949ecf7033f`
and its isolated full-service profile. The admitted definition is not yet a
boot candidate; see the [generation result](results/generation-attempt-3-pass.txt).
