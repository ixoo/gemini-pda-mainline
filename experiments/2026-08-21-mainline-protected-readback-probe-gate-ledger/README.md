# Protected-readback probe/gate ledger

## Status

The previous exact call-ledger candidate is rejected as `neither`: its one
physical selection exposed no mainline USB, pstore, `last_kmsg`, fixed record,
or changed retained payload before changed-boot-ID Gemian recovery. Neither
protected transport was reached or tested. This non-identical successor is now
generated, reviewed, and admitted canonically as patch `0324`. The exact
Buildbox kernel and independently validated Android-v0/16 MiB candidate now
pass offline. The source-pinned guarded installer, USB collector, strict USB
validator, and retained-record classifier also pass their offline contracts.
Guarded deployment and one physical selection are complete. The runtime result
is `neither`; the artifact is rejected without repetition. No native VM build
occurred.

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
| neither | Probe did not enter, or the minimal board/reservation gate, mapping, prefix check, or fixed write refused | Keep both transports unattributed; move before the observer and isolate its predecessor init/probe path |
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
  commit. The managed prepared source through canonical `0323`, each touched
  parent file, and the exact canonical `0323` patch identity are pinned before
  generating the one-patch delta; no duplicate source extraction is created.
- The generated patch uses a synthetic, non-certifying experiment author with
  no DCO sign-off and is not submission-ready.
- Any validated `boot2` installation uses the standing guarded workflow and
  ends in confirmed clean shutdown; no fresh partition backup is required.

## Generation and admission

Exact pushed commit `f16b57f` generated one patch on Buildbox from the managed,
integrity-verified source through canonical `0323`. The generator pins the
prepared source state, every touched parent file, and the canonical parent
patch identity. Source semantics, patch shape, byte-identical replay, strict
checkpatch, package checksums, manual review, the 105-profile canonical-series
audit, and all eight invariant mutations pass. The fetched and admitted patch
bytes are identical. See [`results/generation-f16b57f.txt`](results/generation-f16b57f.txt).

Exact clean pushed commit `1343e6c` then compiled the isolated profile on
Buildbox with modules disabled. Package checksums, configuration, linked
symbols, and provenance pass; both ledger symbols and both read-only backends
are built in while older ledger modes and CPU admission remain off. The DTB is
byte-identical to the predecessor. See
[`results/build-1343e6c.txt`](results/build-1343e6c.txt).

Two independent Android-v0 assemblies and two independent padding methods
agree byte-for-byte. All 32 LK gates pass and the independent validator rejects
all six mutations. The 7,639,040-byte raw image is `c04de416...a233`; the exact
16 MiB `boot2` image is `6cb729ef...2e62`. The serviceability ramdisk remains
byte-identical and no device was accessed. See
[`results/candidate-c04de416.txt`](results/candidate-c04de416.txt).

The source-pinned installer resolved inactive live-GPT `boot2` as p30 while
Gemian used p29, required all four retained-slot headers to be exact-empty,
recorded predecessor `3ce494c9...715a`, and wrote candidate
`6cb729ef...2e62`. The independent full-partition readback matched, no fresh
backup was made, and the device shut down cleanly. See
[`results/deployment-attempt-1-success.txt`](results/deployment-attempt-1-success.txt).

One physical selection returned automatically to changed-boot-ID Gemian. The
normal pstore view exposed no files; bounded raw recovery found both owned
headers valid-empty and both 120-byte payload regions still erased. The
generic 74-byte `last_kmsg` header was unchanged and inactive `boot2` still
matched exactly. Therefore the strict result is `neither`: the observer did
not reach its first record, or the minimal gate/mapping/write path refused.
Neither protected transport was reached. The USB collector was rearmed only
after physical selection began, so its negative window is not used as primary
evidence. See
[`results/runtime-attempt-1-neither-20260821.txt`](results/runtime-attempt-1-neither-20260821.txt).

The linked image contains the ledger and observer probe/initcall. Link order
places the clock-backend and BigiDVFS-backend device initcalls immediately
before the observer initcall, while the record is the observer probe's first
operation. The next useful discriminator therefore moves earlier and removes
both protected calls: isolate clock-backend driver registration and probe
entry before evaluating BigiDVFS or the observer again. See
[`results/post-result-boundary-audit-20260821.txt`](results/post-result-boundary-audit-20260821.txt).

## Next action

Reject this exact artifact without repetition. Preserve its runtime result as
the boundary input for a new experiment that makes no protected call and
isolates clock-backend driver registration from the first clock-backend probe
operation. The repository-wide sequence remains owned by
[`docs/ROADMAP.md`](../../docs/ROADMAP.md).
