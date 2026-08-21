# Protected-readback probe/gate ledger

## Status

The previous exact call-ledger candidate is rejected as `neither`: its one
physical selection exposed no mainline USB, pstore, `last_kmsg`, fixed record,
or changed retained payload before changed-boot-ID Gemian recovery. Neither
protected transport was reached or tested. This non-identical successor is
implemented as deterministic Buildbox patch-generation input and awaits exact
generation, review, canonical admission, and compilation. No native VM build
is permitted.

## Question

Did the prior candidate fail because the one-shot observer never entered, or
did it enter and stop before the complete exact gate immediately preceding the
first protected read?

## Hypothesis and unique evidence

The new opt-in mode preserves the prior kernel inputs, DTB, initramfs, two
read-only protected calls, retained slots, two-write ceiling, and all CPU and
owner closures. It moves the two fixed records to:

1. `probe-enter` in slot 173 at `0x444bd000`, as the first probe operation;
2. `gate-passed` in slot 174 at `0x444be000`, after both backends are acquired
   and the complete current retained-ledger gate passes, immediately before
   the protected-clock call.

The first record requires only the exact `planet,gemini-pda` compatibility,
the exact ramoops reservation base and size, its `ramoops` compatibility and
`no-map` property, and four valid empty headers. The second additionally
requires the proven post-LK `MT6797X` model, every ramoops zone property, the
exact first record, and the remaining empty headers. Both records retain the
existing payload-before-metadata ordering, complete readback, no-overwrite,
no-clear, and no-retry rules.

The new behavior is selected by a second default-off Kconfig mode layered on
the base call ledger. When that mode is disabled, historical patch `0323`
retains its original before-clock/after-clock behavior.

## Decision table

| Recovered evidence | Interpretation | Decision-changing next action |
| --- | --- | --- |
| neither | Probe did not enter, or the minimal board/reservation safety gate refused | Keep both transports unattributed; localize driver binding versus the minimal gate |
| `probe-enter` only | Probe entered, but did not cross backend acquisition plus the full exact gate | Keep both transports unattributed; split acquisition from the full gate without another identical boot |
| `probe-enter` + `gate-passed`, no USB completion | The first protected call was reached; failure remains at or after that call | Isolate the clock call with an after-return observation before testing BigiDVFS again |
| exact USB completion | Both protected reads returned and the observer completed | Validate the bounded runtime record, then resume composition prerequisites |
| malformed, duplicate, or foreign record | Attribution failed | Reject without transport inference |

Two recovered records do **not** by themselves prove that the clock call failed
to return: the unchanged BigiDVFS call follows it, and there is no third
after-clock record. That distinction is deliberately deferred to the branch
that actually reaches the first protected call.

## Safety and build contract

- At most two short writes target only the same otherwise-unused retained-RAM
  zones under the standing diagnostic authorization.
- There is no new writer body, protected read, secure write, retry, owner,
  CPU request, storage operation, reset, reboot, or power operation.
- Patch generation and compilation run only on Buildbox from a clean pushed
  commit. The managed pristine source and exact canonical `0323` patch are
  pinned and replayed before generating the one-patch delta.
- The generated patch uses a synthetic, non-certifying experiment author with
  no DCO sign-off and is not submission-ready.
- Any validated `boot2` installation uses the standing guarded workflow and
  ends in confirmed clean shutdown; no fresh partition backup is required.

## Next action

Commit and push the deterministic generator and profile, generate the exact
one-patch review on Buildbox, fetch and review it, then admit it only if replay,
strict style, profile-series invariants, and mutation checks all pass.
