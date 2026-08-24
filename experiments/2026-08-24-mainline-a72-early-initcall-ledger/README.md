# Experiment: A72 early initcall ledger

## Status

Canonical patch `0362` generated, validated, admitted, and built on Buildbox.
The exact LK candidate is independently validated and awaits one guarded
`boot2` deployment. The predecessor's exact `subsys-init` and `fs-init`
records were both empty after an automatic return to changed-ID Gemian. That
candidate is retired. This successor moves the primary records to pure and
core initcall levels and adds one bounded fallback record that attributes a
failed pure checkpoint when record 2 remains safely available.

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
| Neither | Pure init was not established, the fallback also refused, or the automatic reset did not retain the records | Audit pre-initcall and reset-retention attribution; do not repeat |
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
candidate validation. The next action is the guarded live-GPT `boot2` install,
full readback, and clean shutdown; recovery tooling will then be pinned to that
deployment boot ID before the owner selects `boot2`.
