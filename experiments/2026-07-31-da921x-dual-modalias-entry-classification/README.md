# DA921x bounded event-entry classification

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-entry-classification` |
| Status | `deployed to boot2; not booted` |
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

## Build and candidate

The profile is `da921x-dual-modalias-entry-classification`, with release
`7.1.3-gemini-da921x-entryclass`. Its 126-patch source and configuration
inputs apply and resolve, all 43 manifest profiles satisfy the canonical-order
invariant, all eight invariant mutations are rejected, and strict checkpatch
reports zero findings apart from the intentionally absent experiment-only DCO.
The predecessor profile resolves the new symbol off. No native VM kernel build
was run.

Buildbox fetched exact clean, pushed commit
`442910e7d14698142915021e576b197247ec8a00` and produced the validated package
`linux-7.1.3-gemini-da921x-dual-modalias-entry-classification-f6e60a8b-23396aaf`.
The package has exact `Image.gz` checksum
`db0b03d4dce1065019f6802ae9c4c55f334d945028ab3c4822a2b6fe4e17435f`.

Two independent candidate assemblies were byte-identical. The selected
candidate is `candidate-Gate3-da921x-entryclass-5933dc9f`, with LK-container
checksum `5933dc9f780f84602ca89697fe5ea15944af0f81f048a0e0d266e4de3dc1b2c7`
and full boot2 checksum
`1c703eb0f649bb33d7c49b1d3a3bd9e966cdf5f9f2a3920ac789ffb886bff4b7`.
All 32 LK gates passed. The initramfs remains module-free, the retained exact
enabled-compatible DTB is unchanged, and the candidate adds no hardware path.

The exact installer accepts only the currently installed envelope-state
checksum as predecessor, resolves `boot2` from the live GPT, creates no backup,
requires a matching full-partition readback, and shuts the device down after a
verified write.

The live GPT resolved `boot2` to `/dev/mmcblk0p30`; it was not the active root
and contained the exact envelope-state predecessor. Battery presence, health,
and capacity passed. The entry-classification candidate was written, synced,
flushed, and independently read back with matching full-partition checksum.
No backup was created, and the device shut down cleanly after verified success.
Runtime evidence remains unset until the owner physically selects boot2.

## Runtime capture

The source-pinned one-shot collector and its standalone device-side checker
are validated and ready. They require the exact installed full-partition
checksum, kernel release, USB identity and route, unchanged nine-entry
envelope, CPU0--7 policy, unbound client, ready handoff, and zero transfer and
lifecycle-oracle counters. The checker validates the six classification fields
without assuming which branch will occur, then removes its temporary `/run`
copy. The collector performs no partition read, storage write, or reboot.

The decision map is recorded in `results/runtime-plan.txt`. A clear
`present_mask` bit identifies an absent fixed entry; the other fields separate
duplicates, ordering, missing `SEQNUM`, and replacements. An inconsistent
classification stops the experiment without changing an expectation.
