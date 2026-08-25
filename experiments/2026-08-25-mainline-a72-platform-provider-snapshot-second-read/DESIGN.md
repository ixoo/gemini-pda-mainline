# Design: platform then DA921x provider snapshot

## Fixed call order

The candidate-only observer owns this exact straight-line transaction:

```text
platform_snapshot
  -> checkpoint(before-provider)
  -> provider_snapshot
  -> checkpoint(after-provider)
  -> terminal log
```

The platform result and provider result live in one typed output that is
zeroed before validation and again on every failure. A terminal receipt is
emitted only after both snapshots are valid and record 2 has committed.

## Reader contracts

The platform source is unchanged from the passed predecessor. It performs two
samples of 13 read-only observations under its mutex, refuses CCI busy or
movement, and returns the second stable sample with `valid=1`.

The provider call uses the already separated
`mt6797_a72_provider_snapshot()` registry API. The bound DA921x endpoint holds
its endpoint mutex and root-adapter lock, saves and zeros adapter retries,
performs two fixed five-register pointer/read samples, rejects any transfer
error, short result, or byte mismatch, restores retries, and returns a typed
`valid=1` record. The observer does not acquire or release the provider and
does not compile or call its writer.

## Retained attribution

The mode owns consecutive first-dmesg slots 1 and 2 in the existing
`0x44410000` reservation. Both raw headers must be all ones before the first
write. Each record uses the already qualified payload-first, start, size,
signature-last, barrier, and full-readback protocol. No record is cleared,
repaired, overwritten, or retried.

| Slot | Token | Meaning |
| --- | --- | --- |
| 1 | `GAPP-20260825-A before-provider` | Platform returned valid; provider is the next call |
| 2 | `GAPP-20260825-A after-provider` | Provider returned valid |

Maximum retained write attempts are two. A record-2 attempt is reachable only
after a successful record-1 commit and valid provider result.

## Injected proof

Hardware-free KUnit must cover six cases:

1. exact success order and one call per reader;
2. platform error with no checkpoint or provider call;
3. invalid platform output;
4. record-1 refusal with no provider call;
5. provider error or invalid output after record 1; and
6. record-2 refusal after both readers.

Every failure result must be byte-for-byte zero. The injected suite performs
no MMIO, I2C, retained-RAM, SMC, provider-registry, publication, owner, or CPU
operation.

## Configuration closure

The candidate profile must enable the existing Stage-27 serviceability stack,
provider owner and read-only DA921x endpoint, three read-free backend probes,
new observer, and new ledger. It must explicitly disable:

- the predecessor platform-only observer and ledger;
- the old full physical-source observer and all its ledger modes;
- the positive provider transaction and firmware-writer transaction window;
- protected-readback observers, protected-clock calls, and BigiDVFS calls;
- direct compositor, publisher, production owner, provider acquire/release,
  and every CPU8/CPU9 action.

The KUnit profile adds only the injected test and enough dependencies to link
the observer; it performs no physical operation.

## Stop rules

- Stop before patch creation on any prepared-source or dependency hash drift.
- Stop before admission on patch scope, replay, or strict-style failure.
- Stop before a device build on any series-invariant or KUnit failure.
- Stop before deployment on package, DT, container, mutation, or classifier
  failure.
- Never repeat an unchanged physical artifact unless repeatability itself is
  the predeclared hypothesis and a new observation distinguishes outcomes.
