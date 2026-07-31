# DA921x event-envelope read-only state

| Field | Value |
| --- | --- |
| ID | `2026-07-31-da921x-dual-modalias-envelope-state` |
| Status | `validated candidate prepared; awaiting boot2 deployment` |
| Subsystem | I2C, OF, kobject uevent |
| Device variant | Named Gemini PDA development unit |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | Roadmap Gate 3 serviceability regression |

## Question or hypothesis

Which individual operand makes the exact event-envelope check fail after the
target identity and corrected device path have both matched?

The candidate preserves the stage-2 event, comparison, transport suppression,
no-printk state, unbound real client, module-free initramfs, and CPU0--7
baseline. Its only semantic addition snapshots the following operands before
the existing envelope comparison:

- `envp_idx` and the compile-time envp capacity;
- whether `envp[envp_idx]` is null, or `-1` when that index is unsafe;
- `buflen` and the compile-time packed-buffer capacity.

They are exposed together through the read-only attribute
`/sys/kernel/gemini_da921x_dual_modalias_envelope`.

## Decision

- An `envp_idx` other than 10 identifies the entry-count mismatch.
- An index at or beyond capacity identifies the bounds failure; otherwise a
  zero `terminator_null` identifies the missing terminator.
- A `buflen` at or below zero or above capacity identifies the packed-buffer
  length failure.
- If all operands satisfy the compound condition while stage remains 2, the
  observation is inconsistent with the validator and must be investigated
  before changing any expectation.

## Safety and build policy

The diagnostic stores only integer metadata already read by the existing
validator and exposes it read-only. The indexed terminator observation is
guarded by the same compile-time capacity before dereference. It adds no
printk, event change, transport, driver, provider, transfer, register access,
or storage path. The matching DA921x driver remains module-only and absent
from the initramfs; CPUs 8 and 9 remain offline.

Build the kernel only through `./scripts/build-kernel --backend buildbox` from
an exact clean pushed commit. Do not run a native VM kernel build unless the
owner explicitly requests one.

The experiment patch carries the actual author identity but no DCO sign-off.
It is experiment-only and not submission-ready.

## Build and candidate

Buildbox fetched exact clean, pushed commit
`230fd33c0abb0657999829ed549d41b001c1c4be` and produced release
`7.1.3-gemini-da921x-envstate`. The validated package was assembled twice
without compiling a kernel in the VM; the two LK containers were
byte-identical. The selected candidate is
`candidate-Gate3-da921x-envstate-b6d6b25d`, with full boot2 checksum
`4afe2d97662e9cde1da0a27e2f4a58e0a05e425d9cd5da69abfa51f4136bcea9`.
All 32 LK gates passed.

The exact installer accepts only the currently installed stage-state checksum
as predecessor, resolves `boot2` from the live GPT, verifies the complete
partition after writing, creates no backup, and shuts the device down after
verified success.
