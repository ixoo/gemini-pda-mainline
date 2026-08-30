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

Canonical patchset commit `787ff75a...` passed both the default Buildbox build
and the exact `a72-admission-live-trigger-candidate` profile build. Two clean
container serializations and two independent DT compositions were byte-for-
byte identical. Independent validation accepted all 32 LK-container gates,
rejected ten DT mutations and six container mutations, and the silent READY
validator rejected thirteen decision-changing runtime mutations. The exact
padded candidate is `2245c1c4...`; it retains CPU8 as the sole later request
path but contains no request in this read-only boot. See
[the offline candidate record](results/offline-candidate-20260830.txt).

The candidate was written to the live-GPT-resolved inactive `boot2` after the
expected `9abdd1c6...` predecessor matched. Its full-partition readback matched
`2245c1c4...`, and the device was then shut down without a reboot. See
[the deployment record](results/deployment-20260830.txt).

Boot ID `4ec37034...` then produced the exact silent READY frame: runtime
identity verified once, no profile blocker, no READY diagnostic or values
line, controller state `armed`, CPUs 0-7 online, CPUs 8-9 offline, and zero
trigger executions, CPU requests, CPU_OFF requests, or retries. The first
private capture exposed an observer defect in which empty diagnostic lines
were concatenated and the inherited validator expected a failure-only proof
mask. After correcting those two read-only expectations, a second capture of
the same unchanged boot passed. No trigger was sent. The device was then
returned to Gemian by its validated USB reboot path. See
[the runtime record](results/runtime-ready-20260830.txt).

## Analysis

The runtime result confirms the hypothesis. Adding the one omitted capability
to the expected-absent universe closed both the global and per-target
classified-weight predicates. The absence of the failure-only proof-mask line
is consistent with the blocker disappearing. Because the kernel, DT,
serviceability contract, and observer remained otherwise fixed, this is
attributable evidence that the complete pre-trigger plan now passes. The
experiment did not attempt CPU admission.

## Conclusion

`complete`: exact pre-trigger readiness is established with zero execution.

## Follow-up

Prepare one separate CPU8-only trigger candidate from this exact validated
state. Keep CPU9 vetoed and retain the one-shot, fail-closed observation and
Gemian recovery contract.
