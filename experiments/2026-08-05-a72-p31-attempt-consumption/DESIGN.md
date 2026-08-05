# P31 attempt-ledger design

The dormant `begin_up()` path has this exact order:

```text
request identity + observer window
  -> P31 exact one-shot attempt consumption
  -> A28 exact generic entry snapshot
  -> no-implementation denial
```

P31 accepts only CPU8/CPU9, `CPUHP_ONLINE`, the matching attempt bit, and an
observer window marked open. In `CLOSED`, it returns `-EAGAIN` without touching
the ledger. In `AVAILABLE/IDLE`, it atomically clears the matching bit from
`attempts_available` and sets it in `attempts_consumed`. If A28 then rejects,
the consumed bit remains consumed. If the bit is already consumed or absent,
P31 returns `-EALREADY`; no retry or rearm is possible.

The test-only AVAILABLE seed supplies all four attempt bits and the zero
membership/provider tuple solely to exercise the private ledger. It is not an
A34 bootstrap implementation, has no production caller, and cannot issue
CPU_ON. The owner remains `IDLE` and no transaction identity or token is
allocated. A34/reset recovery is outside this slice.

The observer marker is an explicit input to this dormant seam, not a
capability. A future production caller must replace it with an owner-safe
read-serialization proof before any success path is considered.
