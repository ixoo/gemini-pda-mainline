# DA921x bounded event-entry classification

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-entry-classification` |
| Status | `inputs validated; not built or booted` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

The envelope-state candidate proved that the target event has nine entries,
one fewer than the ordered validator expects. Which expected fixed entry is
absent, and is the deficit instead explained by a replacement, duplicate,
ordering difference, or missing `SEQNUM`?

This candidate preserves the exact stage-2 event, comparison, transport
suppression, no-printk state, unbound real client, module-free initramfs, and
CPU0--7 baseline. Its only semantic addition classifies the existing bounded
environment before the unchanged envelope comparison and exposes:

- `present_mask`, bits 0--8 in the validator's expected-entry order;
- `duplicate_mask` for expected entries seen more than once;
- `ordered_prefix`, the exact expected prefix length;
- `seqnum_count` and the first `seqnum_index` (`-1` when absent); and
- `unexpected_count` for bounded entries matching neither category.

The read-only attribute is
`/sys/kernel/gemini_da921x_dual_modalias_entry_classification`. No arbitrary
entry text is copied, printed, or exported.

## Decision

- A clear bit in `present_mask` identifies each absent fixed expectation.
- A nonzero `duplicate_mask` identifies an expected-entry duplicate.
- `ordered_prefix` identifies the first ordered divergence.
- `seqnum_count=0` identifies a missing sequence entry; a count above one
  identifies duplication, while `seqnum_index` locates its first occurrence.
- A nonzero `unexpected_count` identifies a replacement or other unmatched
  bounded entry.
- Any internally inconsistent classification blocks expectation changes and
  requires source-level investigation before another boot.

## Safety and build policy

The scan is capped by the compile-time pointer-array capacity. A string is
compared only when its pointer falls within the already bounded packed buffer
and a terminator exists before that buffer ends. Only integer classifications
are retained. The event, validator, target transport suppression, and cleanup
remain unchanged; no driver, provider, transfer, register access, printk, or
storage path is added.

Build the kernel only through `./scripts/build-kernel --backend buildbox` from
an exact clean pushed commit. Do not run a native VM kernel build unless the
owner explicitly requests one.

The experiment patch carries the actual author identity but no DCO sign-off.
It is experiment-only and not submission-ready.

## Current state

The profile is `da921x-dual-modalias-entry-classification`, with release
`7.1.3-gemini-da921x-entryclass`. Its 126-patch source and configuration
inputs apply and resolve, all 43 manifest profiles satisfy the canonical-order
invariant, all eight invariant mutations are rejected, and strict checkpatch
reports zero findings apart from the intentionally absent experiment-only DCO.
The predecessor profile resolves the new symbol off. No native VM kernel build
was run. Build, candidate, deployment, and runtime identities remain unset
until their respective gates pass.
