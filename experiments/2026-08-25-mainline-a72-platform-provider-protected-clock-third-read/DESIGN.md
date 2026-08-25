# Third-reader design

## Boundary

The predecessor already qualified one stable platform snapshot followed by one
stable DA921x provider snapshot. This successor adds exactly one later reader:
the already-qualified handoff-owned protected-clock backend. It does not reuse
the earlier clock-only artifact and does not add the BigiDVFS reader.

All three supplier devices must be present and bound before the first platform
observation. Their references remain held through the complete attempt. A
missing or unbound platform source, exact `dlg,da9214-legacy` provider, or exact
`mediatek,mt6797-dvfsp-clock-backend` returns `-EPROBE_DEFER` with zero platform,
provider, retained-memory, or clock effects.

The only admitted order is:

```text
resolve-and-hold(platform, provider, clock)
  -> platform_snapshot
  -> provider_snapshot
  -> checkpoint(before-clock)
  -> protected_clock_backend_read
  -> checkpoint(after-clock)
  -> terminal receipt
```

There is no caller retry. Once the protected-clock function has returned, its
return code and the after-checkpoint outcome are terminal observations and the
probe succeeds so the platform core cannot repeat the hardware call.

## Retained attribution

The new `GAPC-20260825-A` mode owns only first-dmesg records 1 and 2. It reuses
the qualified all-ones header gate, signature-last commit, complete local
readback, and no-clear protocol.

| Slot | Record | Meaning |
| --- | --- | --- |
| 1 | `before-clock`, CRC `7a63713c` | Platform and provider returned valid; the clock call is next |
| 2 | `after-clock`, CRC `5773d4f6` | The single clock call returned, whether success or error |

Maximum retained write attempts are two. The passed provider boundary is not
written again. That keeps a one-record recovery result attributable to the
protected-clock call rather than to an earlier reader.

## Protected-clock effects

This experiment is not hardware-read-only. One backend call uses one balanced
I2C clock prepare-enable/disable pair and the handoff's existing exclusive CSPM
callback. Inside that call the current transport performs:

- one fixed `CSPM_POWERON_EN` write and readback;
- at most 200 semaphore request/write-read iterations to acquire;
- one 200 ns settle after acquisition;
- 18 fixed payload register reads: 11 MCUMIXED and 7 CSPM; and
- at most 200 semaphore request/write-read iterations to release.

Therefore the explicit transport ceiling is 401 MMIO writes and 419 MMIO reads,
including worst-case semaphore polling. Typical success is smaller, but the
definition admits only the source-enforced maximum. A failed attempted snapshot
may latch the clock backend fault once. No secure call, DA921x register-data
write, BigiDVFS read, provider acquire/release, publisher call, owner mutation,
or CPU request is admitted.

## Result handling

Before the clock attempt, every failure clears the result and terminates without
a clock call. After the clock function returns, the observer logs its exact
return code, ABI, generation, and every raw word. An after-checkpoint failure is
also logged but cannot cause an automatic second call.

The candidate passes only with exact live identity, one `ret=0` ABI-2 generation-
1 clock record, both retained records, the complete platform/provider prefix,
Stage-27 serviceability, CPUs 0--7 online, CPUs 8--9 offline, and all forbidden
action counts at zero.

## Implementation shape

Buildbox generation will create four logical patches after canonical `0373`:

1. a mutually exclusive two-record pstore mode;
2. a binding for a new candidate-only three-source observer;
3. the observer with injected operations and explicit dependency gates; and
4. hardware-free KUnit coverage of call order, failure clearing, no-effect
   defer, terminal clock errors, terminal after-checkpoint failure, and success.

The passed platform/provider observer remains unchanged and its profiles remain
historical controls. The new candidate DT will replace that observer node with
the new observer and add only its clock-backend phandle.
