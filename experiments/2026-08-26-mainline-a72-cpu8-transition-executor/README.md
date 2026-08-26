# Mainline CPU8 injected transition executor

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-26-mainline-a72-cpu8-transition-executor` |
| Status | hardware-free implementation in progress |
| Subsystem | MT6797 CPU8 transition coordination and rollback boundary |
| Device variant | Planet Gemini PDA, MT6797 |
| Date(s) | 2026-08-26 America/New_York |
| Investigator(s) | Project maintainers |
| Tracking issue | Roadmap Gate 7, first mainline CPU8 request |

## Hypothesis

The first active CPU8 candidate needs an independently testable coordinator
before any physical callback is connected. A default-off executor with injected
operations can prove the exact one-shot, watchdog-first, single-CPU_ON,
pre-isolation rollback, and post-isolation retain rules without touching the
Gemini or any hardware interface.

The source prerequisite and rejected configuration-only branches are frozen in
the preceding
[active-transition admission audit](../2026-08-26-mainline-a72-cpu8-active-transition-audit/README.md).

## This phase

Generate two review patches from the exact canonical tree through `0383`:

1. a default-off operation-injected coordinator with no production caller,
   device binding, trigger, or physical backend; and
2. an exhaustive KUnit suite covering success, every stage failure, entry
   rejection, malformed ownership, rollback faults, and the one-shot guard.

The coordinator names nine ordered stages but implements no MMIO, regmap,
reset, regulator, I2C, secure-call, PSCI, CPU-hotplug, retained-RAM, watchdog,
or DCM operation itself. Those remain callbacks that a later patch must connect
one at a time after the pure state machine passes.

## Generation chronology

- Clean pushed commit `f35a39d2` reached strict Checkpatch, but the generator
  hid the diagnostic body when the command failed.
- Commit `190f4299` exposed the exact result: 29 continuation-style checks, the
  normal new-file MAINTAINERS warning, and the missing-sign-off error expected
  for a synthetic non-certifying experiment archive.
- Commit `9df7d930` fixed the reported wrapping and used the repository's
  established `MISSING_SIGN_OFF,FILE_PATH_CHANGES` exception; two alignment
  checks remained.
- Commit `44ff3f0e` reduced the exact generated production patch to one helper
  alignment check.
- Commit `829c2b66` published that correction and removed the callable
  controller initializer so the executor API cannot reset a consumed one-shot.
  The exact format-patch run cleared the production patch, then exposed 13
  KUnit continuation-alignment checks that the earlier file-mode preflight did
  not reproduce.
- The current correction aligns every reported continuation with its opening
  parenthesis. Publication and a new exact format-patch run are pending; only
  that patch-mode result is authoritative for admission.

See
[`results/pre-admission-style-20260826.txt`](results/pre-admission-style-20260826.txt)
for the bounded receipt. No generation attempt compiled a kernel or contacted
the Gemini.

## Exit

- Normal `git format-patch` output replays on the exact prepared source.
- Both patches pass strict Checkpatch.
- All source and mutation validators pass.
- A named Buildbox KUnit profile compiles the exact canonical result.
- No native VM build, boot candidate, device request, partition write, reboot,
  or retained-memory write occurs.
