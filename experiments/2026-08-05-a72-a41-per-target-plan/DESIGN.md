# A41 per-target planning design

## Boundary

Patch 0153 advances the blocked capability planner from one aggregate ABI 3
answer to attributable ABI 4 state for CPU8 and CPU9:

```text
registered target mask {CPU8, CPU9}
             |
             v
validate slot 0 -> CPU8 and slot 1 -> CPU9
             |
             v
classify every local descriptor independently per slot
             |
             +-- target[0]: 34 classified / 4 present / 6 unresolved
             +-- target[1]: 34 classified / 4 present / 6 unresolved
             |
             v
aggregate classified intersection + present union
             |
             v
CAP_INVENTORY + EFFECT_PLAN + RUNTIME_BINDING + PLAN_VALIDATION
             |
             v
no plan identity / PLAN_FROZEN / commit / READY
```

This is a representation and planner-semantics boundary. It does not add an
observed CPU register, close one of the six dynamic rows, or authorize an
architecture mutation.

## Target attribution

The architecture core now requires every profile slot to name one unique,
in-range logical CPU which is already present in the registered target mask.
The indexed mask must equal the registered mask before any classifier callback
runs. Unused slots and dirty input/result bitmaps are rejected.

The callback receives the validated slot index. Match-list members are
evaluated independently for both targets. Each target retains its own
classified and present bitmaps. An aggregate row is classified only when every
target is classified; aggregate presence is the union of the independently
classified target results. This prevents CPU8 from hiding an unresolved or
different CPU9 result.

## Runtime binding

ABI 4 separates six identities: resolved and running configuration, built and
running image, and expected and running command line. The evidence also names
its origin as NONE, FIXTURE, or RUNTIME. The architecture-owned publication
guard requires:

- origin RUNTIME, never FIXTURE;
- the complete known validity mask;
- six nonzero identities; and
- exact equality within each expected/running pair.

This milestone intentionally supplies origin NONE, zero validity, and zero
identities. The framework therefore restores RUNTIME_BINDING even if a profile
forgets it. The MT6797 partial validator separately requires the record to be
fully empty.

The origin and identities are inputs from `profile->prepare`; ABI 4 does not
independently attest their producer. It rejects a record declared FIXTURE and
detects partial or pair-mismatched fields, but a future unblocking milestone
must add an independently trusted runtime producer and validate that ownership
before allowing the profile to declare RUNTIME.

## Failure semantics

| Mutation or omission | Result |
| --- | --- |
| target missing from the registered mask | core returns `-EINVAL` before classification |
| duplicated, swapped, or residual target slot | core/profile validation fails |
| either target leaves one of 40 rows unresolved | planner returns `-EAGAIN` |
| per-target or aggregate bitmap drift | profile returns `-EINVAL` |
| declared NONE/FIXTURE, partial, or mismatched binding | RUNTIME_BINDING remains set |
| planner failure | CAP_INVENTORY is set |
| profile validation failure | PLAN_VALIDATION is set independently |
| any standing blocker | lifecycle publishes BLOCKED only |

Patch 0092 still returns `-EAGAIN` from `.cpu_boot` and `false` from
`.cpu_can_disable`; `maxcpus=8` remains forced. The architecture commit entry
still panics if it is somehow reached out of order and has no implementation.

## Claim limit

The exact state is `PARTIAL_PER_TARGET_PLAN_BOUNDARY`. Both targets still use
the expected-model static census from patch 0152: 4 PRESENT, 30 ABSENT, and 6
UNRESOLVED. No real CPU8/CPU9 row is closed. The experiment performs no build,
device access, firmware call, CPU request, or network access.
