# P24 lifecycle-closed owner model

## Claim boundary

This directory contains an independent source-only specification oracle
labeled `PARTIAL_P24_CLOSED_OWNER_MODEL`. It models only the initial negative
admission boundary: owner health is `CLOSED`, membership phase is
`UNINITIALIZED`, and admission has no opener.

The oracle does not import or inspect Linux source. It is not an
implementation validator and does not establish a production caller, a
production opener, generic CPU-up or CPUHP hooks, a build/runtime/device
result, or P30E MMU-off correctness.

## Exact request fixtures

The accepted input domain contains two exact request identities:

| Operation | CPU | MPIDR | CPUHP target | Generation | Cookie |
| --- | ---: | ---: | --- | ---: | ---: |
| CPU8 up | 8 | `0x200` | `CPUHP_ONLINE` | 42 | `0x8a720042` |
| CPU9 up | 9 | `0x201` | `CPUHP_ONLINE` | 7 | `0x9a720007` |

These values are request fixtures, not allocated P24 or P30 tokens. The model
never orders generation 42 and generation 7, consumes them, publishes them,
or makes them live. A request with any different operation, CPU, MPIDR, CPUHP
target, generation, or cookie is `INVALID_IDENTITY` and cannot enter owner
admission.

## Named diagnostic prerequisites

The bounded diagnostic universe is:

1. `A34_BOOTSTRAP`
2. `A41_READY`
3. `A25_CALLBACKS`
4. `PROVIDER_OWNER`
5. `A36_PRESTATE`
6. `P30_INTEGRATION`
7. `P30E_MMU_OFF`
8. `P14_P15`
9. `P32_ROLLBACK`
10. `A33_COMMIT`
11. `FAILSTOP_RESET`
12. `A26_VETO`
13. `OWNER_IMPLEMENTATION`

The presented set is diagnostic input only. It is non-exhaustive and cannot
authorize a request. The oracle enumerates all `2^13 = 8,192` subsets,
including the empty and complete sets. It also evaluates caller readiness as
both false and true for each subset.

Three owner-controlled sentinels are deliberately separate from those caller
claims:

- `all_applicable_review_complete = false`;
- `a26_veto_lifted = false`;
- `implementation_enabled = false`.

Presenting similarly named diagnostic rows never changes these sentinels.
Caller readiness is context, never authority.

## Frozen owner state

The only correct owner value has:

- health `CLOSED` and membership phase `UNINITIALIZED`;
- all three authority sentinels false;
- no P31 entry, A38 consumption, or consumed attempt;
- no live token;
- no P17, P18, P30, P14, P15, A33, or P32 publication;
- provider `NONE`, invalid/empty membership, and no hardware effect;
- no CPU_ON request; and
- zero denial epoch, acknowledgment, or reset epoch.

An exact admission probe returns `DENIED_CLOSED`. A malformed probe returns
`INVALID_IDENTITY`. Both results preserve the complete frozen owner value.
There is no correct `AUTHORIZED` result or owner state.

Acknowledgment and reset are not modeled recovery authorities. The correct
model rejects both control actions. A future platform/external-reset owner and
A34 bootstrap contract require a separate milestone; merely naming reset or
acknowledging denial cannot open this owner.

## Reviewed dormant C mapping

Patch `0159` adds the same initial negative boundary as a C-only MT6797 owner
model. Its static value is `CLOSED`, `UNINITIALIZED`, provider `NONE`, with all
diagnostic blockers asserted and every transaction, budget, attempt, token,
membership, controller, retirement, and fault field empty. There is no
production `CLOSED -> AVAILABLE` writer.

For exact CPU8 or CPU9 requests targeting `CPUHP_ONLINE`, `begin_up()` clears
the caller's output and returns `-EAGAIN` before taking the transition mutex or
entering P31/A38. Malformed CPU or CPUHP-target requests return `-EINVAL`.
Token ownership and copy helpers can succeed only in the unreachable
`AVAILABLE` state with a valid bootstrap and live transaction. The owner calls
no P30 mutator and contains no PSCI, CPU_ON, provider, hardware, or CPUHP-effect
operation.

Read-only snapshots expose the complete owner value. The default-off KUnit
suite has eight cases covering the initial closed state, CPU8 and CPU9 denial,
malformed inputs, repeatability, a forged token, and absence of a live token.
The valid denial and token-read cases compare complete owner and P30 snapshots
before and after. The suite was statically reviewed but not built or run.

The C layout explicitly is not a P17/P18/P24 token ABI or a wire/hardware ABI.
Its future transaction fields reserve no authority: they do not prove the
correct ordering or effects until later production integration implements and
reviews them.

## Invariants

| Invariant | Required property |
| --- | --- |
| `CLOSED_LIFECYCLE_ONLY` | Health remains exactly `CLOSED`. |
| `MEMBERSHIP_PHASE_UNINITIALIZED` | Membership never enters `IDLE`, `FROZEN`, or a later phase. |
| `ALL_APPLICABLE_REVIEW_REMAINS_FALSE` | The exhaustive-review sentinel remains false. |
| `A26_VETO_LIFTED_REMAINS_FALSE` | The A26-lift sentinel remains false. |
| `IMPLEMENTATION_ENABLED_REMAINS_FALSE` | The implementation-enable sentinel remains false. |
| `P31_NOT_ENTERED` | Denial precedes P31. |
| `A38_NOT_CONSUMED` | No A38 one-shot is consumed. |
| `ATTEMPT_NOT_CONSUMED` | No operation or call attempt is consumed. |
| `NO_LIVE_TOKEN` | No P24/P30 token is allocated or made live. |
| `P17_NOT_PUBLISHED` / `P18_NOT_PUBLISHED` | Neither up publication occurs. |
| `P30_NOT_REACHED` | No dormant or production P30 handoff occurs. |
| `PROVIDER_UNTOUCHED` | Provider state remains `NONE`. |
| `MEMBERSHIP_UNTOUCHED` | The member ledger remains empty and invalid. |
| `HARDWARE_UNTOUCHED` | No register, regulator, firmware, or other hardware effect occurs. |
| `CPU_ON_NOT_ISSUED` | CPU_ON is never requested. |
| `P14_NOT_PUBLISHED` / `P15_NOT_PUBLISHED` | No secondary completion is published. |
| `A33_NOT_COMMITTED` | No final CPUHP/online commit attestation occurs. |
| `P32_NOT_ENTERED` | No rollback owner is entered. |
| `EXACT_REQUEST_IDENTITY` | Malformed identities cannot enter owner admission. |
| `CALLER_READINESS_NOT_AUTHORITY` | Toggling caller readiness cannot change denial or state. |
| `BOUNDED_LIST_NOT_AUTHORITY` | Even all 13 named diagnostics cannot authorize. |
| `NO_AUTHORIZED_STATE` | No correct probe returns `AUTHORIZED`. |
| `DENIAL_IMMUTABLE` | Every denial preserves the complete frozen owner value. |
| `ACK_NOT_AUTHORITY` / `RESET_NOT_AUTHORITY` | Neither control action can change or open the owner. |

## Oracle method

`scripts/oracle.py` uses frozen standard-library dataclasses. It evaluates the
Cartesian product of two exact identities, every named-prerequisite subset,
and both caller-readiness values. It then rejects a bounded set of
single-field malformed identities and verifies sequential CPU8/gen42 then
CPU9/gen7 denial. The oracle performs no filesystem or source inspection.

`scripts/test_mutations.py` changes one rule at a time and requires the
intended invariant to fire. The 25 mutations cover caller trust, treating the
bounded list as sufficient, ignoring A26, inferred review/implementation,
malformed identity admission, P31/A38/attempt consumption, token allocation,
`FROZEN`, P17/P18/P30, provider/member/hardware effects, CPU_ON,
P14/P15/A33/P32, mutable denial, acknowledgment, and reset.

The exhaustive input matrix is a proof over this finite model only. It is not
a proof over arbitrary kernel concurrency, C memory ordering, generic hotplug
integration, firmware, or hardware.

## Exact nonclaims

- No kernel build, KUnit execution, runtime execution, or device action.
- No production P24 caller and no `CLOSED -> AVAILABLE` opener.
- No generic `cpu_up()`, `_cpu_up()`, CPUHP, callback, or other hook.
- No production P30 integration and no P30E MMU-off object, cache, PoC,
  barrier, or assembly proof.
- No package, boot candidate, deployment, CPU_ON request, or support claim.
