# Experiment: identify the remaining READY plan predicate

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-plan-predicate-diagnostic` |
| Status | `running` |
| Subsystem | arm64 late-CPU plan validation diagnostics |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

Which exact internal predicate of `mt6797_a72_validate_cap_plan()` remains
false after patch `0437`, given that exact repaired candidate `726b622a...`
still reports public proof mask `0x24000`?

The diagnostic hypothesis is falsifiable: an otherwise identical candidate
must retain the validator's original return value and emit exactly one
`A72_READY_PLAN_DIAG_V1` line on failure. Its 27-bit whole-plan mask and 29-bit
evidence mask must name the false contract without changing READY, CPU, power,
storage, retry, CPU_OFF, or CPU9 behavior.

## Provenance and environment

- Parent repository commit: `24c33409...` until the diagnostic scripts are
  committed.
- Parent kernel series: canonical Linux 7.1.3 through patch `0437`.
- Parent prepared source state: `1beeac9d...`.
- Parent `mt6797_psci.c` SHA-256: `bfa1f825...`.
- Runtime parent candidate: exact boot2 SHA-256 `726b622a...`.
- Runtime parent boot ID: `93114930-acfe-41f2-975b-e84cddf0d5a5`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The patch renames the existing pure validator implementation to a private
contract function and adds a wrapper that returns its result unchanged. Only
when that result is nonzero does it calculate two read-only diagnostic masks
and print one versioned line. It adds no CPU operation, device-tree change,
hardware read or write, retained-RAM write, storage access, retry, CPU_OFF,
reboot, or firmware call. CPU9 remains vetoed.

Any candidate remains subject to exact package, LK-container, live-GPT,
inactive boot2, power, write, readback, and clean-shutdown gates. The diagnostic
candidate must never receive the CPU8 trigger.

## Associated code

- `scripts/source_edits.py`: applies the exact one-file diagnostic wrapper.
- `scripts/validate_source.py`: proves the original contract remains the sole
  return-value owner and validates the two mask schemas.
- `scripts/test_mutations.py`: rejects acceptance bypass, success logging,
  diagnostic bypass, missing mask coverage, and CPU-action mutations.
- `scripts/generate_patch.py`: creates, checks, replays, and packages one
  deterministic format-patch.
- `scripts/generate-on-buildbox`: pins the exact post-`0437` managed source.

## Procedure

1. Generate and replay the one-file patch on exact post-`0437` Buildbox source.
2. Reject mutations that change the contract return, bypass the wrapper, log a
   successful result, remove required mask coverage, or add a CPU action.
3. Admit the patch canonically and build default plus exact live profiles only
   on Buildbox.
4. Recompose the unchanged serviceability/provenance DT and ramdisk, validate
   the Android-v0/LK container independently, and deploy exact boot2.
5. Capture one complete read-only frame and the versioned diagnostic line; do
   not send a trigger.

## Observations

Pending.

## Analysis

The public proof mask deliberately groups all profile callback validation under
`PLAN_VALIDATION`; it cannot distinguish static plan shape, expected evidence,
effect planning, HWCAP planning, target classification, or identity state. A
single read-only internal bitmap is therefore decision-bearing and avoids a
sequence of guessed semantic relaxations.

## Conclusion

`pending-buildbox-generation`.

## Follow-up

Use the first exact diagnostic bitmap to select one source-local correction.
Do not repeat the observer or permit CPU8 until a later non-diagnostic candidate
publishes an exact no-blocker READY frame. Keep CPU9 vetoed.
