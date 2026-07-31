# DA921x OF event-layout correction

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-event-layout-correction` |
| Status | `completed; exact corrected layout serviceable` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Does the real-OF target event reach the existing successful validation and
normal cleanup path when the ordered validator expects the runtime-proven
eight fixed entries followed by `SEQNUM`?

The entry-classification candidate uniquely observed all eight OF-path fixed
entries exactly once and in order, no I2C fallback modalias, one `SEQNUM` at
index 8, and no unexpected entry. Exact source control flow independently
explains that result. This candidate changes only the false ninth fixed-entry
expectation; it preserves the exact event, transport suppression, no-printk
read-only state, module-free unbound client, and zero-hardware baseline.

## Decision

- Exact state `validated` and final stage 17 with the full serviceability and
  zero-activity baseline proves complete eight-entry-plus-`SEQNUM` validation,
  successful suppression, and normal cleanup are safe.
- A reset before serviceability implicates the corrected complete-assembly or
  successful-cleanup path and stops expectation work.
- A surviving state short of validation identifies the exact remaining stage
  without repeating an identical artifact.
- Any changed envelope, client binding, module availability, I2C activity, or
  baseline rejects attribution.

## Safety and build policy

The target event remains suppressed before transport. The matching driver is
module-only and absent from the initramfs; the real client stays unbound. The
patch adds no driver, provider, transfer, register access, printk, storage
access, or reboot path. Runtime observation is read-only.

Build the kernel only through `./scripts/build-kernel --backend buildbox` from
an exact clean pushed commit. Do not run a native VM kernel build unless the
owner explicitly requests one.

The experiment patch carries the actual author identity but no DCO sign-off.
It is experiment-only and not submission-ready.

## Input validation

The named `da921x-of-event-layout-correction` profile selects the existing
serviceability stack plus only the new correction symbol and release
`7.1.3-gemini-da921x-ofevent`. All 127 patches apply to the pinned Linux
7.1.3 source, the configuration merges with every requested symbol enabled,
and the historical entry-classification profile resolves the new correction
symbol off. All 44 manifest profiles satisfy the canonical-order invariant,
and all eight focused invariant mutations are rejected.

Strict focused checkpatch reports zero errors, warnings, and checks when the
intentionally absent experiment-only DCO is excluded. Host and VM free-space
checks passed with 95 GiB and 83 GiB available, respectively. No native VM
kernel build was run and the device was not accessed.

## Build and candidate

Buildbox fetched exact clean pushed commit
`0656017566dccc893e008fff1d73ff101d383bbe` and produced validated package
`linux-7.1.3-gemini-da921x-of-event-layout-correction-ccf22d64-6cf84909`.
The package release is `7.1.3-gemini-da921x-ofevent`; its exact `Image.gz`
checksum is
`a768b874378c063f7cbf4f6204cedc25f0359a1a911718539acf16ce0c0cd43d`.
No native VM kernel build was run.

Two independent candidate assemblies from that package and the retained exact
Gate 3 DT and module-free initramfs were byte-identical. The selected candidate
is `candidate-Gate3-da921x-ofevent-461e90ef`, with LK-container checksum
`461e90ef1bc6dab04797ddf8d8b90454e172effb6cb7de70ff638930b351d5b9`
and full boot2 checksum
`d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2`.
All 32 LK gates passed. The duplicate assembly was removed after comparison,
and only the bounded selected candidate was exported to ignored host staging.

The guarded installer accepts only the currently installed entry-classifier
checksum as predecessor, resolves `boot2` from the live GPT, creates no backup,
requires a matching full-partition readback, and shuts the device down after a
verified write. Deployment was deferred until the named device returned from
the entry-classifier runtime to known-good Gemian, the authorized installation
environment.

## Deployment

One identity-checked native reboot returned the completed entry-classifier
runtime to known-good Gemian release `3.18.41+` with a changed boot ID and no
storage access during the reboot request. The guarded installer then resolved
logical `boot2` to `/dev/mmcblk0p30` while Gemian root remained
`/dev/mmcblk0p29`. The exact entry-classifier predecessor checksum matched;
battery presence, 96% capacity, and `Good` health passed.

The candidate was written, synced, flushed, and independently read back with
the matching full-partition checksum
`d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2`.
The temporary readback was removed, no backup was created, and the device shut
down cleanly after verified success.

## Runtime capture

The source-pinned one-shot USB/netcat collector and standalone device-side
checker are validated and ready. They require the exact installed full boot2
checksum, release, USB identity and route, validated read-only state, final
stage 17, unchanged nine-entry envelope, runtime-proven entry classification,
CPU0--7 policy, unbound real client, ready handoff, and zero transfer and
lifecycle-oracle counters.

The checker writes only a temporary `/run` copy and removes it after execution.
The collector performs no partition read, storage write, or reboot. The exact
first-boot hypothesis and acceptance map are frozen in
`results/runtime-plan.txt`; any changed identity, envelope, event
classification, client state, or hardware baseline rejects attribution.

## Runtime result

The first selected boot matched release `7.1.3-gemini-da921x-ofevent`, full
boot2 checksum
`d9370fd47dd4c4e3ae1851ffd639a9b1e623b3f36de54560935323618690def2`,
USB identity and route, and boot ID
`ae825dbe-88e3-4f35-ba1d-3ce4745e212e`. The source-pinned checker reported
state `validated`, final stage 17, the exact nine-entry envelope, and:

`present_mask=0xff duplicate_mask=0x0 ordered_prefix=8 seqnum_count=1 seqnum_index=8 unexpected_count=0`

The real `1-0068` client retained its OF node and remained unbound. CPUs 0--7,
USB/netcat, and handoff serviceability passed while every I2C and lifecycle
oracle remained at zero. The event was suppressed before transport. The
checker removed its temporary `/run` copy and performed no partition read,
storage write, or reboot. Local console and keyboard usability were not
separately assessed.

This proves the runtime-classified eight fixed entries plus final `SEQNUM`
validate completely and clean up safely. Event construction, exact bounded
serialization inputs, successful return, and cleanup are no longer the open
boundary. The next discriminator may construct the netlink skb from this exact
validated event and discard it before socket traversal or multicast, thereby
separating message allocation/serialization from listener and delivery paths.
