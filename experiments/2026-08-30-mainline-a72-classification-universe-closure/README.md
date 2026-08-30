# Experiment: close the READY classified-capability universe

## Record

| Field | Value |
| --- | --- |
| ID | `2026-08-30-mainline-a72-classification-universe-closure` |
| Status | `running` |
| Subsystem | arm64 late-CPU plan validation |
| Device variant | Planet Computers Gemini PDA, named development unit |
| Date(s) | 2026-08-30 |
| Investigator(s) | Julien Etienne and Codex |
| Tracking issue | `docs/ROADMAP.md` late Cortex-A72 admission gate |

## Question or hypothesis

After patch `0440`, the exact live plan fails only the global and per-target
classified-capability weight predicates (`plan=0x40800`, `evidence=0`). The
value frame proves `ARM64_MISMATCHED_CACHE_TYPE` is absent from both target
local bitmaps, while the production classifier still classifies that compiled
capability. Does moving this capability into the profile's absent list close
both remaining counts without changing any producer, effect, or CPU action?

The hypothesis is falsifiable: an otherwise identical live candidate must
produce no READY diagnostic/value line, no profile blocker, and no CPU request.
Any remaining predicate selects another read-only observation. A clean result
selects one later CPU8-only trigger candidate. CPU9 remains vetoed.

## Safety assessment

The proposed patch adds one existing capability enum to a static expected-
absent list. It does not change classification, target local state, required
state, effects, firmware policy, hardware access, retained RAM, storage,
retry, CPU_OFF, reboot, or any CPU request path.

## Procedure

1. Generate and replay one format-patch from the managed exact post-`0440`
   source state; verify the canonical `0440` parent identity independently.
2. Reject mutations that remove the absent entry or restore it to present or
   required state.
3. Admit the patch canonically and build default plus exact live profiles on
   Buildbox.
4. Recompose the unchanged serviceability candidate and repeat the exact
   silent, read-only READY capture. Do not send a trigger.

## Observations

Buildbox generated and replayed canonical candidate patch `0441` from managed
post-`0440` source state `10328b30...`; the patch adds exactly
`ARM64_MISMATCHED_CACHE_TYPE` to `mt6797_a72_absent_caps`. Source validation
passed and four decision-changing mutations were rejected. The generated patch
contains no producer, effect, policy, CPU request, CPU9, CPU_OFF, retry, or
hardware-write change. See
[the generation record](results/buildbox-generation-20260830.txt).

## Analysis

Pending.

## Conclusion

`running`.

## Follow-up

Only a clean attributable READY result may select a CPU8-only trigger.
