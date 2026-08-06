# A72 provider-owner callback refusal design

## Ordered boundary

```text
P31 -> A28 -> frozen token -> A36 -> P17 -> P27 -> R01
  -> provider callback -> R02 or R03 -> P29
```

The owner remains the only component that can advance the transaction state.
The DA921x driver owns its callback context and registers one callback after
the fixed identity transcript and read-only provider registration succeed.
There is no Device Tree supply phandle and no generic regulator consumer
lookup: the callback is the explicit platform ownership boundary.

## Request contract

The owner begins R01 and consumes its one-shot budget before constructing a
request. The request carries ABI `1`, CPU8-up operation `1`, the inherited
1 ms settle, page `0x80`, Buck-B selector `0x46`, and the transaction
generation/cookie. The provider must validate these values and must not use
the request as permission to write hardware.

## Response contract

Success returns ABI `1`, a nonzero provider handle, the exact settle/page/
selector observation, BUCKB enabled, M01 origin, and a matching origin
generation. The owner converts that response into the existing R02 proof and
revalidates it under the transaction locks.

The current read-only provider returns `-EOPNOTSUPP` with `returned=1` and all
vote/mutation flags clear. The owner converts only that fully structured result
into the existing R03 before-vote rejection. An absent provider, malformed
response, or any other error leaves the acquire state inflight; it is not
silently retried or treated as clean rollback.

## Lifetime and locking

The registry serializes registration, unregister, and callback execution. A
managed device action unregisters the provider before its context is released.
The owner does not hold its raw state spinlock across the potentially sleeping
provider callback; R01 and R02/R03 each revalidate the transaction identity
after the call.

## Explicit nonclaims

This seam contains no writable regulator operation, regulator vote, page
selection, MMIO, CPUHP callback, P28 isolation/SRAM effect, P30 handoff,
PSCI/CPU_ON call, CPU8/CPU9 admission, or boot/device action. It proves only
that a provider-owned callback can be invoked and that the existing refusal
ledger is reached without a consumer mapping.
