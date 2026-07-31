# DA921x OF event-layout correction

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-of-event-layout-correction` |
| Status | `input validation passed; awaiting Buildbox build` |
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
