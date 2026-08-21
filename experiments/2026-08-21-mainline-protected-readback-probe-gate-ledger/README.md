# Protected-readback probe/gate ledger

## Status

The previous exact call-ledger candidate is rejected as `neither`: its one
physical selection exposed no mainline USB, pstore, `last_kmsg`, fixed record,
or changed retained payload before changed-boot-ID Gemian recovery. Neither
protected transport was reached or tested. This non-identical successor is now
generated, reviewed, and admitted canonically as patch `0324`. The exact
Buildbox kernel and independently validated Android-v0/16 MiB candidate now
pass offline. Guarded deployment is pending. No native VM build occurred.

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

## Next action

Commit and push the sanitized build/candidate evidence and reproducible tools,
then prepare the guarded `boot2` installer and exact runtime classifiers. After
those pass offline, deploy once, verify full-partition readback, and shut down.
