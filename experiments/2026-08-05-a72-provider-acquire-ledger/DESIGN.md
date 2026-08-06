# Dormant R01/R02 provider-owner design

The source-only order is:

```text
P31 -> A28 -> frozen token -> A36 -> P17 -> P27 -> R01 -> R02
```

R01 is a one-shot call boundary. Under the transition and state locks it
requires the exact live CPU8 identity, completed P27, `ON_ISSUED`, conservative
`members=0`, provider `NONE`, and an available provider-acquire budget. It
consumes that budget and publishes `ACQUIRE_INFLIGHT` before the future
synchronous provider call. A nonreturning call would remain inflight and may
not be retried; this source slice does not make that call.

R02 is a returned-confirmed edge. It requires the same transaction generation
and cookie, the consumed acquire budget, `ACQUIRE_INFLIGHT`, completed P27,
`members=0`, and a nonzero held-reference identity. The proof must attest the
inherited 1 ms settle, page `0x80`, BUCKB enabled, VSEL `0x46`, and M01 origin.
Only then does the owner publish `HELD` and copy the durable identity into the
active transaction. Membership stays `0x0` until later CPU8 completion.

No provider API, MMIO, regulator, isolation, SRAM-LDO, CPUHP, P30, or PSCI
operation appears in this patch. A malformed or stale proof leaves the
inflight owner unchanged. R03 (rejected-before-vote) and its exact P29
pre-isolation rollback are the next separate contract edge.
