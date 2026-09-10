# Native DMA capture placement

## Decision

Use the existing HIF critical section to scope DMA observations, and record
both native failure branches at their actual branch sites. Do not add a
success-only wrapper around the DMA operation: the selected source returns
TRUE on a deadline failure without releasing its mapping or HIF lock, and
separately unmaps after an idle-count escape without observing idle.

The [five-file source receipt](results/dma-hook-sources.json) pins complete
public Git objects at Gemian revision
`59e00a9144d782e148332009a835b99c43382467`. The four HIF files match the earlier
[build selection](results/native-build-selection-sources.json); `sdio.h`
resolves the IRQ macros. This is source and injected-execution evidence,
not attribution of the installed kernel or an admitted radio cycle. No native
kernel source or patch changes in this follow-up.

## Ownership and access boundaries

`AP_DMA_HIF_LOCK` and `AP_DMA_HIF_UNLOCK` in `hif.h` are empty macros with
commented-out lock operations. They cannot protect observer state. In the
selected MT6797 branch, `my_sdio_disable(HifLock)` instead calls
`spin_lock_bh()` on the one global `HifLock`. Both `kalDevPortRead()` and
`kalDevPortWrite()` acquire it before command setup and hold it through DMA
mapping, programming, polling and unmapping on their ordinary path.
Their eventual `my_sdio_enable()` releases it. DMA clock-enable requests
precede acquisition; clock-disable requests follow release.

The names `__disable_irq()` and `__enable_irq()` do not identify CPU interrupt
masking here. `sdio.h` expands them to writes of 1 and 0 to HIF base plus
`0x200`. Capture must account for those issued HIF control writes separately
from bottom-half exclusion and the persistent writer's own IRQ-save lock.
Neither the macro name nor the fixture establishes the hardware's interrupt
state or completion of a posted write.

The bounded HIF-directory source search finds both `DmaConfig`, `DmaPollIntr`
and `DmaPollStart` call sites inside those two port operations. This supports
scoping their observer state under the existing HIF lock. It does not prove
exclusive ownership against reset, interrupt or other subsystem paths. New
capture calls must preserve lock order **HIF lock, then capture lock** and
must not call the generic mutex-taking pmsg writer.

## Selected deadline and idle exits

The selected headers define DMA polling, `CONF_HIF_CONNSYS_DBG=1`,
`CONF_HIF_DMA_DBG=0`, and no preallocated-buffer branch. Both port functions
set a five-second jiffies deadline and test it **before** each INTFLAG polling
callback. On the selected expired-deadline path they invoke the optional DMA
dump, set `WlanDmaFatalErr`, and return TRUE. They do not reach interrupt ACK,
DMA stop, EN polling, unmap, HIF IRQ-enable, HIF unlock or clock-disable.
Deadline expiry before the first callback therefore permits zero INTFLAG
observations. An entry record cannot imply that a register read occurred.

The later EN loop tests `LoopCnt++ > 100000` before each callback. Its count
escape occurs after 100,001 callback invocations when none reports idle.
That branch then reaches the existing unmap and ordinary release sequence.
It must be recorded as a count escape, even though the port returns TRUE and
its software mapping is released. The nine-record consistency checker must
continue to reject it as lacking positive idle before unmap.

These are distinct native behaviors. The observer must not turn the deadline
return into a break, add an unmap, release a lock or repair an IRQ/clock state
to simplify capture. Those would change the mechanism being observed and need
a separate recovery/driver design. In particular, ordinary teardown cannot
be presumed to make progress after the retained-lock return.

## Reproduction and hook requirements

The [fixture](test-dma-native-lifetime.py) extracts the two complete native
port-function bodies, selected configuration macros, HIF lock/IRQ macros,
command bitfields and DMA configuration types from the pinned files. It
compiles them with injected DMA callbacks, MMIO, locks and time. No native
body is rewritten. Port tokens and surrounding structures are host stubs;
this is not a target ABI or register-protocol test.

All [eight cases](results/dma-native-lifetime-test.txt) pass: RX and TX each
exercise ordinary completion, deadline expiry after polling, deadline expiry
before any poll, and the idle-count escape. The fixtures track outstanding
mappings, lock state, requested HIF mask values and clock-request balance.
The synthetic clock selects 499 or zero INTFLAG callbacks in the two deadline
cases; these counts are fixture inputs/results, not measured hardware timing.
No physical device, DMA engine, interrupt or real kernel lock executes.

The next hooks must preserve this contract:

- Assign a transaction under the HIF lock, retain the full DMA API return and
  bind the device ordinal to its initialization lifetime. A pointer cast is
  not a publishable identity, and address reuse cannot prove lifetime identity.
- Sample programming values where the existing PDMA accesses occur. For each
  poll, count the actual accessor read and retain its raw result before the
  callback reduces it to a Boolean; never invoke the callback again to log it.
- Emit each poll entry before its loop and its summary at the actual condition,
  deadline or count branch. Emit the selected deadline failure before the
  existing early return, without synthesizing cleanup records.
- Place unmap entry/return records around the existing call. Leave a missing
  return incomplete and reject count-escape unmapping as positive-idle evidence.
- Freeze the observer's state lifetime, failed-capture behavior and independent
  watchdog recovery before a candidate uses these hooks. The persistent writer
  alone supplies none of the native lock/mapping cleanup guarantees.

No producer hook, kernel build, candidate or physical operation is selected by
this assessment. It resolves placement and failure-path requirements before
implementation; full typed producer/controller integration remains open.
