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

## Native producer implementation

The unselected [DMA patch](patches/dma/0001-wlan-observe-native-AHB-DMA-lifetimes.patch)
now implements those hooks against the [pinned inputs](results/dma-capture-sources.json).
It adds the built-in helper to the MT6797 HIF objects and private state to the
native HIF structure. Initialization records a new software ordinal after the
existing `Dev` assignment; no pointer is published. Kind 2 carries either
`<4I>` initialization (subtype 1, ordinal, route, pointer-present) or `<3I>`
retirement (subtype 2, ordinal, pending transaction). The envelope carries the
same ordinal. Route 1 is the native platform-device assignment; route 2 is the
misc-device branch, which the consistency checker refuses. This records a
software binding, not physical endpoint or DMA translation identity.

The existing HIF lock protects transfer fields. Native accesses supply thirteen
setup samples, four shutdown samples, and the raw result of each actual poll
read. The helper accumulates poll counts in 64 bits; overflow saturates and
records reason 5. No per-poll persistent record or additional MMIO read is
introduced. Each transfer retains its full DMA address and obtains a new
transaction ID. Unmap entry and return surround the existing DMA API call.
The selected early deadline return records a summary and preserves its missing
cleanup. Reset records failure before the existing native reset operation.

Retirement sets an atomic flag without acquiring the HIF lock, since that lock
may remain held on the native deadline path. It reads the pending transaction
without modifying transfer fields, records retirement and fails the capture
if a transfer remains. A later transfer emission sees retirement and fails.
Reset similarly does not modify transfer fields outside their lock. There is
no deferred work holding a trace pointer. These hooks do not repair native
teardown races or prove that all users have stopped; a controller must join
the relevant actors before completing capture.

Capture remains inactive until the native owner begins. A bind that happened
before begin supplies no ordinal for later DMA. Missing samples, duplicate
samples, a changed device, reused live transaction or retired state fails the
capture. Append failure stops that transaction's recording while leaving the
native operation intact. The pstore activity query is a lock-protected snapshot,
not a reservation; every append still checks the actual writer state.

The [combined fixture](test-dma-capture.py) compiles the actual original and
patched port functions and six PDMA callbacks with injected MMIO, DMA, clock
and locks. It includes the real capture helper and slot writer. Its
[24 comparisons](results/dma-capture-test.txt) require identical native access
sequences for both directions and four exits, each with inactive capture,
active capture and an injected lost record store. Eleven helper cases cover
invalid lifetime/sample state, retirement, abort, zero-read deadline and
64-bit counting/overflow. Eight records with recalculated CRCs test invalid
binding histories. The independent decoder accepts the ordinary complete
DMA sequence and refuses all three native failure cases. These tests model
new boots when resetting fixture globals; production counters are not reset.

Reproduce with the exact original basenames and patched HIF directory:

```sh
python3 experiments/2026-09-07-mt6797-wifi-observer-feasibility/test-dma-capture.py ORIGINAL PATCHED_HIF
```

The fixture stubs HIF initialization/retirement, clocks and diagnostic dump;
it does not compile the full native glue structure or prove target ABI,
physical timing, concurrent kernel lifetime, persistence or Wi-Fi operation.
The native compile lane is `check-startup-objects.py COMMIT --dma` on Buildbox
and requires clean published input. Compilation is pending for this source
revision. The changed HIF structure requires all consumers to be rebuilt in a
full native kernel before any deployment. Controller integration, watchdog
recovery and candidate admission remain open; no candidate is selected.
