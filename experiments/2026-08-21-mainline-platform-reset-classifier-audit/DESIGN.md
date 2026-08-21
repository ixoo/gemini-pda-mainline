# Platform-reset classifier decision

## No positive tuple from current inputs

The two implemented inputs are:

```text
raw TOPRGU WDT_STATUS
current preloader ram-console wdt_status
```

The exact shipping preloader derives the second value from the first. Their
agreement is correlated by construction and cannot create reset-strength
authority. A strict classifier over only these inputs has no positive row.

Unknown bits, any represented RGU cause, any contradiction, and exact zero in
both fields all remain reject outcomes. Exact zero excludes represented reset
causes but does not prove the discarded power-on stage marker.

## Positive source signal and lost transport

The exact preloader separately classifies power off/on reset when both are
true:

- the captured raw TOPRGU status is zero; and
- entry-time `INTERVAL[1:0]` is the hardware-default stage marker `3`.

It stores class `4` in a preloader-private cell, then rewrites
`INTERVAL[2:0]`. Pinned LK consumes bit 2 into a private Boolean and rewrites
the same bits again. Neither the class, the Boolean, nor the entry-time
interval reaches the retained typed snapshots available to Linux.

The apparent direct SRAM cell is not an admissible transport. One read-only
Gemian probe stalled the unit before returning data. That address is now a
permanent no-access boundary unless a future independently reviewed hardware
owner supplies a safe accessor; raw `/dev/mem`, magic mapping, retry, and a
kernel `ioremap()` experiment are forbidden.

Changing LK to export the class is also outside this boundary. It would modify
the separate bootloader partition and boot contract, while the current goal is
an inactive boot2 kernel path.

## Selected next boundary

Replace the impossible cause-classifier implementation step with an audit of
direct A34 recovery-state attestation. The audit must determine whether the
canonical tree already has owner-safe, immutable observations for every state
whose recovery the platform/external-reset premise was intended to guarantee:

- external DA921x Buck B page, enable, status, and selector state;
- SPM A72 power status, reset, isolation, SRAM and power-control state;
- TOPRGU PWRAP reset state;
- protected A72 clock, mux/divider, CCI and DCM state;
- CPU8/CPU9 physical-off evidence plus CPUHP, masks, methods, and MPIDRs;
- BL31 private replay zero under the exact firmware contract; and
- empty provider, membership, transaction, P30, fault, generation, cookie,
  and attempt state immediately before publication.

The audit may refine A34 only if this is a complete state proof, not a smaller
collection of convenient registers. Any unobservable, non-owner-safe, mutable,
or contradictory member keeps the lifecycle `CLOSED / UNINITIALIZED`.

## Explicit exclusions

This decision adds no classifier implementation, kernel patch, build, LK
change, SRAM access, MMIO read, device boot, boot2 write, A34 production
caller, lifecycle publication, provider action, P28 effect, P30 arm, PSCI
call, CPU veto change, `CPU_ON`, or `CPU_OFF`.
