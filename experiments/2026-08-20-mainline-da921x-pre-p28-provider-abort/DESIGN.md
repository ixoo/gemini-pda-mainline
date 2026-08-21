# Pre-P28 provider-abort design

## State edges

The enabled, test-seeded CPU8-up path may execute only:

```text
NONE -> ACQUIRE_INFLIGHT -> HELD
HELD -> RELEASE_INFLIGHT -> NONE
NONE + exact P27 inverse -> REJECTED
```

The abort budget is distinct from provider acquire, future normal provider
release, P28, and CPU_ON budgets. It is available only for CPU8-up, consumed
before calling release, and never replenished.

## Fail-stop returns

After `ACQUIRE_INFLIGHT`, any returned outcome other than an exact positive
response or the existing exact before-vote refusal publishes:

```text
provider = FAULT_UNKNOWN
owner health = FAULTED
phase = FAULT
recovery = reset-only
```

The same terminal applies after `RELEASE_INFLIGHT` for every returned error or
malformed success. The held identity is retained on release fault. There is no
retry, guessed handle, second release, or speculative inverse.

## Exact positive abort

Entry requires the exact live CPU8 transaction, completed P27 ledger, `HELD`
provider and matching durable handle, unconsumed abort/P28/CPU_ON budgets,
P28 stage `NONE`, and zero members. The owner publishes `RELEASE_INFLIGHT`
before calling the registry with the R02 generation/cookie.

Success requires every response field: returned/vote/provider/rail flags,
settle time, page, disabled Buck B, VSEL, origin, origin generation, and exact
handle. Only then does the owner store the abort proof, clear both durable
provider identities, and publish `NONE`.

## P29 predecessors

P29 accepts exactly one mutually exclusive predecessor:

- R03 exact refusal before any vote; or
- exact positive pre-P28 abort with its budget consumed.

Both require provider `NONE`, zero durable provider identity, P28 never
started, P28 budget available, CPU_ON unissued, CPU_ON budget available, and
the exact complete P27 inverse proof. No other state can retire the prefix.

## Focused proof

The six KUnit families cover exact lifecycle success, all 22 negative/short
acquire failure ordinals, 14 malformed acquire successes, all 22
negative/short release failure ordinals, 14 malformed release successes, and
stale handle, duplicate abort, plus nine P29 proof mutations. Exact positive
transport tests use the same production callback ops through the production
registry with an injectable endpoint and an unregistered fake adapter.
The suite observes `RELEASE_INFLIGHT`, the consumed abort budget, and the exact
durable handle from inside the release callback. It repeats each faulted
acquire/release request and requires local `-EPERM` with unchanged provider or
I2C call counts, proving that terminal faults cannot retry.

## Preserved closures

No source in this slice adds a lifecycle opener, production caller, physical
adapter registration, P27/P28 executor, PSCI call, membership commit, CPU_ON,
CPU_OFF, boot candidate, or device action.
