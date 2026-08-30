# Experiment: observe exact READY plan values

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-plan-value-diagnostic` |
| Status | `running` |
| Subsystem | arm64 late-CPU plan value diagnostics |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact predicate observer proves that the live plan differs from profile
expectations for early, target, required, and per-target local capability
bitmaps, and that the collected SMCCC conduit differs from the assumed SMC
value. Which exact bitmap values and conduit enum did the production producers
publish?

The value-observer hypothesis is falsifiable: an otherwise identical candidate
must preserve the validator return and original predicate line while emitting
exactly one `A72_READY_PLAN_VALUES_V1` line on the same failure. That line must
contain `ARM64_NCAPS`, the three global bitmaps, both per-target local bitmaps,
and both target policy conduits. It must not change READY, CPU, power, storage,
retry, CPU_OFF, or CPU9 behavior.

## Provenance and environment

- Parent repository commit: `285f53a5...`.
- Parent kernel series: canonical Linux 7.1.3 through patch `0438`.
- Parent prepared source state: `a5a27faa...`.
- Parent `mt6797_psci.c` SHA-256: `a850c6b5...`.
- Runtime parent candidate: exact boot2 SHA-256 `7ac6f429...`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The patch changes only the existing failure-only validator wrapper. It keeps
the original contract call and returns its result unchanged. When that result
is nonzero and the plan pointer is valid, it prints immutable in-memory plan
bitmaps and two one-byte policy enum values. It adds no CPU operation,
device-tree change, hardware read or write, retained-RAM write, storage access,
retry, CPU_OFF, reboot, or firmware call. CPU9 remains vetoed. The candidate
must never receive the CPU8 trigger.

## Procedure

1. Generate and replay one format-patch from exact post-`0438` Buildbox source.
2. Reject mutations that change the validator return, success guard, null
   guard, exact value fields, profile callback, or add a CPU action.
3. Admit the patch canonically and build default plus exact live profiles only
   on Buildbox.
4. Recompose the unchanged serviceability/provenance DT and ramdisk, validate
   the container independently, and deploy exact boot2.
5. Capture one complete read-only frame and exactly one value line; do not send
   a trigger.

## Conclusion

`exact-value-observer-source-pending`.

## Follow-up

Use the one value frame to distinguish a stale profile expectation from a
producer defect. Repair only the observed contract, then require a silent
diagnostic and exact no-blocker READY frame before any CPU8 trigger. Keep CPU9
vetoed.
