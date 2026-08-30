# Experiment: retain the CPU8 P27 initiating and rollback results

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-p27-runtime-attribution` |
| Status | `source-defined; Buildbox patch generation pending` |
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
