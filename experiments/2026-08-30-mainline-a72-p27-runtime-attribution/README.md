# Experiment: retain the CPU8 P27 initiating and rollback results

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-p27-runtime-attribution` |
| Status | `focused Buildbox/QEMU validation passed; production build pending` |
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
