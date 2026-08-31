# Design: A72 effect-plan stage ledger

## Runtime gap

The existing `A72_READY_PLAN_DIAG_V1` line is emitted by the final profile
validator. It proves the draft is incomplete but does not expose the return
from `arm64_plan_late_cpu_effects()` or distinguish its profile derivation from
generic validation.

## Selected observation path

Canonical patch `0461` adds two immutable-format `pr_info()` records:

```text
A72_EFFECT_DERIVE_V1 stage=<source-stage> target=<index-or--1> ret=<errno>
ARM64_LATE_CPU_EFFECT_PLAN_V1 stage=<preconditions|derive|validate|complete> ret=<errno>
```

The MT6797 record is emitted exactly once per derivation call, at the existing
return edge. The generic record identifies the outer planner boundary. Stage
labels map one-to-one to source checks and are validated during generation.

## Safety and interpretation

The records are ordinary boot log text. They allocate no retained memory and
perform no device access. Existing return values and branch conditions remain
unchanged. A diagnostic boot is observation-only: the CPU8 trigger is withheld
regardless of the resulting plan state. The result selects the next source
repair or test; it is not itself hardware support evidence.
