# Experiment: repair READY plan expectations

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-ready-plan-expectation-repair` |
| Status | `running` |
| Subsystem | arm64 late-CPU plan validation |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

The exact post-`0439` runtime value frame localized the READY-plan rejection to
three stale profile expectations. Does repairing only those expectations allow
the otherwise identical production plan to validate without changing its
producers, expected-effects model, or any CPU action?

The hypothesis is falsifiable: an exact live candidate must produce no
`A72_READY_PLAN_DIAG_V1` or `A72_READY_PLAN_VALUES_V1` failure line, no profile
blocker, and no CPU request. Any remaining validator failure selects another
read-only diagnostic; a clean READY result selects one later CPU8-only trigger
candidate. CPU9 remains vetoed.

## Provenance and environment

- Parent repository commit: `e0078b04...`.
- Parent kernel series: canonical Linux 7.1.3 through patch `0439`.
- Parent prepared source state: `404d5b64...`.
- Parent prepared source integrity: `1f8f978d...`.
- Parent `mt6797_psci.c` SHA-256: `08f3be5c...`.
- Runtime evidence: exact boot ID `ec5f3d02...`, kernel
  `7.1.3-gemini-a72-admission-live`, and boot2 SHA-256 `1c08f1fc...`.
- Build backend: Buildbox only; no native VM build.

## Safety assessment

The patch changes only hard-coded validator expectations. It adds the observed
early `ARM64_WORKAROUND_845719`, removes the unobserved target and required
`ARM64_MISMATCHED_CACHE_TYPE`, and changes the production policy expectation
and its diagnostic from SMC to the observed NONE conduit. Fixture evidence
remains SMC. The patch adds no CPU operation, hardware access, firmware call,
power or storage operation, retained-RAM write, retry, CPU_OFF, or reboot.
CPU8 and CPU9 remain offline and unrequested throughout this experiment.

## Associated code

- `scripts/source_edits.py`: exact post-`0439` edits.
- `scripts/validate_source.py`: source-contract and safety validation.
- `scripts/test_mutations.py`: decision-changing mutation rejection.
- `scripts/generate_patch.py`: deterministic format-patch generation/replay.
- `scripts/generate-on-buildbox`: pinned Buildbox entry point.

## Procedure

1. Generate and replay one format-patch from the exact post-`0439` Buildbox
   source.
2. Reject mutations that restore any stale expectation, alter the fixture
   conduit, bypass the validator wrapper, or add a CPU action.
3. Admit the patch canonically and build the default and exact live profiles
   on Buildbox.
4. Recompose and independently validate an otherwise unchanged serviceability
   candidate.
5. Install exact inactive logical `boot2`, verify its full readback, and shut
   down the device.
6. Capture one read-only boot and require a silent diagnostic, zero blockers,
   and zero CPU requests. Do not send a trigger.

## Observations

Buildbox generated exactly one format-patch from prepared source state
`404d5b64...` and integrity `1f8f978d...`. The parent and final
`mt6797_psci.c` hashes are `08f3be5c...` and `3179b9f3...`; patch `0440` is
`b629ff95...`. Strict checkpatch, deterministic replay, exact contract checks,
and all eight adverse source mutations pass. The generation changed no profile
fragment, performed no native VM build or device action, and marks its output
`boot_candidate=false`. See
[`results/buildbox-generation-20260830.txt`](results/buildbox-generation-20260830.txt).
The canonical patch is byte-identical to that output; the canonical-order
audit passes all 158 manifest profiles and its self-test rejects eight invalid
series mutations.

## Analysis

The review contains only the three corrections selected by the exact live
value frame. It does not change the production producers or expected-effects
model, and the fixture continues to require and publish SMC. Canonical-series
validation passes; compile validation remains pending.

## Conclusion

`running`.

## Follow-up

Only a clean attributable READY result may select a separate CPU8-only trigger
candidate. CPU9 remains out of scope until CPU8 admission is repeatable.
