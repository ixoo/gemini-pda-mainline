# DA921x ordered validation-stage state

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-stage-state` |
| Status | `kernel inputs prepared; awaiting validation` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Which exact ordered comparison is the last one completed by the corrected
dual-modalias validator before the state remains `pending`?

The candidate retains the corrected root paths, exact ordered event validator,
no-printk state, target transport suppression, real unbound OF client,
module-free initramfs, and CPU0–7 baseline. Its only semantic addition is an
atomic integer exposed read-only at
`/sys/kernel/gemini_da921x_dual_modalias_stage`.

## Stage contract

| Stage | Last successful boundary |
| --- | --- |
| `0` | target event not matched |
| `1` | action, subsystem, and client name |
| `2` | corrected device path |
| `3` | ten-entry envelope shape |
| `4`–`12` | ordered entries 0–8 respectively |
| `13` | sequence prefix |
| `14` | final packed-buffer boundary |
| `15` | non-empty sequence value |
| `16` | entirely numeric sequence value |
| `17` | complete validation and existing state set to `validated` |

The code records only successful boundaries. A value below `17` identifies
the immediately following check as the first unresolved boundary.

## Decision

- A serviceable stage below `17` selects exactly one next validator correction
  or observation and forbids repeating this candidate.
- Stage `17` plus state `validated` proves the complete event construction;
  the remaining question is full console, keyboard, USB, handoff, and
  zero-hardware-activity serviceability.
- A pre-serviceability reset implicates only the new stage writes or the
  already reached boundary and does not advance provider work.

## Safety and build policy

The diagnostic writes only an in-kernel atomic integer and exposes it through
a read-only sysfs attribute. It adds no printk, transport, driver, provider,
transfer, register access, or storage path. The matching DA921x driver remains
module-only and absent from the initramfs; CPUs 8 and 9 remain offline.

Build the kernel only through `./scripts/build-kernel --backend buildbox` from
an exact clean pushed commit. Do not run a native VM kernel build unless the
owner explicitly requests one.
