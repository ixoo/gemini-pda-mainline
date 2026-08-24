# Experiment: A72 early initcall ledger

## Status

Canonical patch `0362` generated, validated, admitted, and built on Buildbox.
The exact LK candidate is independently validated, installed to live-GPT
inactive `boot2`, fully read back, and completed its one attempt. Changed-ID
Gemian recovery found both records exact empty, pstore empty, and no independent
mainline identity in `last_kmsg` or the watchdog-class reboot record. Because
the earlier positive control reached `/init` and USB yet returned with the
same empty record state, these bytes establish only that no record survived;
they do not localize execution before pure init. The candidate is retired.

## Hypothesis

The failing kernel reaches the earliest global initcall levels even though the
later subsystem checkpoint was not retained. An independent pure-init record,
a later core-init record, and a mutually exclusive pure-refusal record in slot
2 separate early progress from a primary writer refusal without relying on
USB, console, screen state, or reboot timing.

## Exact evidence

1. `GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init
   outcome=commit slot=1 crc32=03d9627f`
2. `GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=core-init
   outcome=commit slot=2 crc32=57dd63b5`
3. `GEMINI_A72_EARLY_INIT_V1 token=GAEI-20260824-A checkpoint=pure-init
   outcome=primary-refused slot=2 crc32=5767e326`

Record 2 contains either the core checkpoint after a successful pure record or
the refusal marker after a failed pure checkpoint, never both. All writes use
the first-dmesg raw all-ones precondition, payload-before-metadata,
signature-last commit, barriers, and complete local readback.

## Decision table

| Retained result | Interpretation | Next action |
| --- | --- | --- |
| Neither | No record survived; execution position remains unresolved because a prior positive control returned with the same empty state | Use a live pre-reboot observation path; do not repeat |
| Refusal only | Pure init ran and the primary checkpoint refused; exact DT/map/slot-2 fallback gates passed | Localize the primary refusal gate |
| Pure only | Pure init committed; core init was not established | Split pure-to-core ordering |
| Pure plus refusal | Pure record became exact but its checkpoint reported failure | Audit local readback/ordering; do not infer core progress |
| Pure plus core | Both early initcall levels committed | Move forward between core and subsys init |
| Malformed, foreign, or core without pure | Attribution failed | Reject without ordering inference |

## Safety and build contract

- The enabled path makes at most two short retained-RAM write attempts, only
  in first-dmesg records 1 and 2. It never overwrites, clears, or retries a
  target record.
- The fallback runs only after the primary pure checkpoint returns failure. It
  repeats the exact DT gate, requires a successful bounded mapping and an
  all-ones record-2 header, and commits only the fixed refusal record.
- The observer is linked to satisfy the inherited base-ledger dependency but
  is not registered. No allocation, source lookup, physical snapshot,
  provider transaction, clock/BigiDVFS call, publication, owner mutation, or
  CPU request occurs.
- Patch generation and kernel compilation use exact clean, signed, pushed
  commits on Buildbox. No native VM kernel build is authorized.
- This definition is not a compiled kernel, boot candidate, device write, or
  CPU8/CPU9 admission.

## Current result

The exact canonical parent is patch `0361` and the managed Buildbox source
state through that patch is pinned by its state, integrity, and three touched
file hashes. Generation attempt 1 stopped before patch creation because its
validator did not normalize an adjacent split C string. Attempt 2 passed
source, patch-shape, and byte-identical replay gates, then strict checkpatch
rejected one missing blank line. The validator-only and formatting-only
corrections are recorded separately.

Attempt 3 passes exact source validation, the exact three-file boundary,
byte-identical replay, and strict checkpatch with zero errors, warnings, or
checks. The fetched patch is admitted byte-for-byte as canonical `0362` with
SHA-256 `65771c690b9c19833160d8547898b2f97b8b0149518092700eab3ef8b861a5a9`.

Buildbox job
`26274db63316bbb24eeb9bfa8de21759da666b9e-a72-early-initcall-ledger-m0`
compiled exact release `7.1.3-gemini-a72-early` from clean signed repository
commit `26274db63316bbb24eeb9bfa8de21759da666b9e`. Package checksums passed.
The deterministic LK container uses the runtime-proven serviceability ramdisk
and exact physical-source DTB, passes all 32 LK gates, and was independently
reassembled and validated. Its raw SHA-256 is
`8bff90591b02f0c888e794c2abb28daf0768b754745f193b11b195f804f22789`;
the exact 16 MiB `boot2` image SHA-256 is
`d2951eade3c08c889ecaeb1376f85262c44ad729048ddc3164c1db39acced609`.
No device access, device write, or CPU admission occurred during build or
candidate validation. Guarded deployment then resolved live-GPT inactive
`boot2` as `/dev/mmcblk0p30` while Gemian root remained
`/dev/mmcblk0p29`. Both record headers were exact empty. The predecessor
checksum was recorded without creating a redundant backup; the exact padded
candidate was written, synced, flushed, and matched by a full 16 MiB readback.
Gemian shutdown was confirmed unreachable without reboot.

The recovery classifier was pinned to deployment boot ID
`ca6e280a-1d4b-4db3-ae9e-9d3234d4082c` and exact installed SHA-256
`d2951eade3c08c889ecaeb1376f85262c44ad729048ddc3164c1db39acced609`.
It accepts exactly the five decision-table branches, rejects core without pure
and malformed, conflicting, stale, or unsafe captures, and passed 18 mutation
tests.

The owner selected `boot2` once. Changed-ID Gemian returned with boot ID
`9a06ac83-21f4-4d7c-8522-5a93c33c372e`; the exact candidate remained on
inactive `boot2`. Pstore was mounted and empty, and records 1 and 2 retained
exact empty headers. The raw frozen classifier reported
`before-pure-init-or-both-writers-refused`, but that is not promoted to an
execution boundary: the earlier entry-ledger positive control independently
reached `/init` and USB before returning with the same empty headers.
`last_kmsg` contained only the known generic status-5 header, while the
returned reboot record carried the common nondiscriminating watchdog class and
no mainline identity.

The exact artifact is retired. The selected successor is not another retained
record or an identical retry. Recontainer this exact kernel with the
runtime-proven Stage-27 DTB and pre-arm a live USB/netcat collector so evidence
is read before any reboot or Gemian clearing. That DT-only control can decide
whether the current kernel reaches `/init` and expose the early records live,
without another kernel build or any CPU request.
