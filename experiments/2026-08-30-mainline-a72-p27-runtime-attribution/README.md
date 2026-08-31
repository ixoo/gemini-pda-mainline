# Experiment: retain the CPU8 P27 initiating and rollback results

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-p27-runtime-attribution` |
| Status | `exact boot2 candidate deployed and device shut down; boot pending` |
| Subsystem | MT6797 CPU8 P27 platform effect and rollback |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact prior CPU8 trigger reached `add_cpu(8)` and recovered a valid
transition ledger whose latest record is P27
`ROLLBACK_FAULT_PREISO`. Did the initiating P27 acquisition fail in hardware,
did its membership publication reject after a successful physical acquire, or
did the rollback fail after either condition?

## Safety assessment

The diagnostic retains scalar state that already exists in the binder after
the synchronous request returns. It adds no hardware access, request, retry,
CPU9, CPU_OFF, storage, retained-RAM write, reboot, or timing change. The P27
release result is copied into binder-owned memory instead of a temporary stack
object, and the existing read-only live status exposes:

- transition terminal, stage, initiating errno, rollback errno, and checkpoint
  errno;
- transition ownership, rollback, and retained masks; and
- P27 acquire/release operation, error, attempted/completed effect masks,
  ownership, seal state, and bounded SPM/BPLL observations already captured by
  the existing effect owner.

The snapshot is serialized by the binder publication lock. A focused KUnit
case must prove a malformed P27 acquire followed by a failing logical rollback
retains both independent errors and both effect result shapes.

## Procedure

1. Generate one normal format-patch from the exact managed source through
   canonical patch `0448` on Buildbox.
2. Require deterministic replay, source-contract checks, strict style review,
   and the focused binder KUnit case.
3. Admit the patch canonically and build only the existing isolated live KUnit
   and production profiles through `./scripts/build-kernel --backend buildbox`.
4. Construct a new boot2 candidate only after all offline gates pass. Its
   pre-trigger frame must show a zeroed, idle snapshot; its single boot-bound
   trigger must return the complete terminal snapshot before watchdog recovery.

## Decision branches

- P27 acquire result contains an error or incomplete effect mask: repair only
  that exact physical predicate or operation.
- P27 acquire is complete with `error=0`, while `stage_errno` is nonzero:
  attribute the failure to membership completion and retain its exact state.
- P27 release result contains an error or incomplete effect mask: repair only
  that rollback operation.
- P27 release is complete with `error=0`, while `rollback_errno` is nonzero:
  attribute the rollback fault to logical P29 completion.
- Any result after P27 changes the selected stage and supersedes this boundary.

CPU9 remains vetoed until CPU8 is reproducibly online.

## Buildbox generation result

The exact clean pushed project commit
`38ec2b399af31d11900b1af24622f5b0409de8f9` generated canonical patch
`0449` against the managed post-`0448` Linux source. Its bundle passed source
identity and integrity checks, contract validation, deterministic replay, and
checksum verification. Strict checkpatch reported zero warnings and zero
checks; its sole error is the deliberately absent synthetic `Signed-off-by`.
The experiment author is synthetic, this archive is not submission-ready, and
repository policy forbids inventing a DCO certification. Exact generation
evidence is recorded in
[`results/buildbox-patch-generation-20260830.txt`](results/buildbox-patch-generation-20260830.txt).

The exact patch commit also compiled in both the live-trigger and dedicated
binder KUnit profiles on Buildbox. The dedicated hardware-free QEMU run passed
all 48 selected cases: 30 membership-owner, 12 transition-executor, and 6
binder cases, including `mt6797_binder_p27_diagnostic_test`. Exact identities
and the zero-action boundary are recorded in
[`results/buildbox-kunit-20260830.txt`](results/buildbox-kunit-20260830.txt).

## Production candidate result

Buildbox produced the production live-trigger profile from exact clean pushed
commit `b2ca2e5050d38e060aec61b841fde3d395ff589c`. The package has patchset
`a2612437c7beb2235d6054266d2f3557ba15321ea7f0db7ca757c632fadc5c21`,
configuration `9b9118fd...`, and compressed Image `a89ef31c...`; its complete
package checksum manifest passes.

Two independent DT compositions added only the package-owned A41 provenance
leaf to the unchanged serviceability/admission tree and produced exact DT
`7c2f1f76...`. Two independent Android-v0 assemblies produced raw candidate
`fbc299b0...`; two independent padding constructions produced exact 16 MiB
boot2 image `e22db747...`. The independent validator passes all 32 LK gates,
rejects six corrupt-container mutations, and preserves the single dormant
CPU8 request route with no CPU9, CPU_OFF, or retry route. The independent DT
validator rejects ten representative tree mutations. Exact identities and
safety gates are recorded in
[`results/offline-candidate-20260830.txt`](results/offline-candidate-20260830.txt).

The read-only pre-trigger frame now requires the binder diagnostic to be
available, ABI 1, idle, and entirely pristine before the sole request. The
boot-bound terminal classifier captures every transition and P27
acquire/release field, rejects malformed diagnostic values, and retains the
existing changed-boot and one-trigger boundaries. Offline fixtures accept the
four attributable outcomes and reject mutations of the binder return, stage
errno, effect masks, CPU masks, and reboot boundary.

The deployment guard also accepts only the exact retained transition-ledger
bytes already published for the predecessor attempt: attempt 1, generation 4,
terminal P27 `ROLLBACK_FAULT_PREISO`, with generation 3 as its valid preceding
checkpoint. Both admission traces must remain empty. This avoids modifying
retained RAM while ensuring that an unknown or changed record still stops the
install before any boot2 write.

Before the device boot, the hypothesis is that the new terminal frame will
separate physical P27 acquire failure, logical membership completion,
physical P27 release failure, and logical P29 rollback completion. A complete
acquire or release result changes the next action to the corresponding logical
membership repair; an incomplete or error-bearing result changes it to only
the named platform effect. A later stage supersedes P27. CPU9 remains vetoed.

## Deployment result

The guarded installer resolved logical boot2 as `/dev/mmcblk0p30` while Gemian
root remained `/dev/mmcblk0p29`, accepted only the exact published predecessor
ledger and empty traces, and wrote candidate `e22db747...`. The synced and
flushed full-partition readback matched exactly. No fresh backup or retained-RAM
write was made. The device was shut down cleanly and three consecutive TCP/22
closures confirmed it remained unreachable. See
[`results/deployment-20260830.txt`](results/deployment-20260830.txt).
