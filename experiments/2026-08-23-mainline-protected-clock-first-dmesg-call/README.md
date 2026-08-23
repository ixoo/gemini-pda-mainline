# Experiment: protected clock call in first dmesg

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-23-mainline-protected-clock-first-dmesg-call` |
| Status | patch-generation definition pending review |
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

## Next action

Generate and review patch `0336`, then admit its profile and complete offline
definition, Buildbox, candidate, deployment, and runtime gates before spending
one physical boot.

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
