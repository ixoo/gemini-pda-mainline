# Native firmware-stop capture hooks

The unselected [stop patch](patches/stop/0001-wlan-capture-native-adapter-stop-decisions.patch)
implements the existing [kind-7 stop records](PERSISTENT_CAPTURE.md#firmware-stop-payload-and-consistency-check)
against the [pinned native inputs](results/stop-capture-sources.json). It depends
on the ten-patch pstore capture series and the native DMA capture patch. It
applies only to the selected MT6797 AHB configuration; no other chip or HIF
configuration is validated. It supplies no controller, recovery owner or
hardware admission.

## Invocation and gate attribution

A source-wide gen3 search finds two callers of `wlanAdapterStop()`: normal
remove and probe-failure cleanup. The patch adds their explicit caller values
1 and 2 to the native internal signature and its declaration. The observer
allocates a stop-invocation ordinal, then uses the calling adapter's existing
HIF initialization ordinal as its software identity. Neither ordinal proves
physical identity or installed-source attribution. No pointer is published.

The capture state lives on the stop caller's stack. Queue clearing remains
before the original D0/no-ack/card-removal gate. Those predicates retain their
original order and short-circuit evaluation; unevaluated fields stay zero.
The entry record is emitted after gate evaluation and before power-down work.
If queue clearing hangs, this entry record is absent. Command ownership is
sampled at its original gate after power acquisition, and the command is called
once only on the same original driver-owned branch. The helper records its
actual result without converting the native adapter return into a shutdown
verdict.

The poll summary distinguishes READY clear, successful fallback, reset and
skipped work. Every fallback invocation is counted, including failures before
a later READY-clear exit. The original interrupt drain, delays, reset,
firmware-ownership call, cleanup and returned status remain in place. A failed
capture cannot repair or cancel those operations.

## Synchronous read context

The non-SDIO register dispatcher and accessor accept an optional capture
context. Ordinary callers pass null. Only the outer stop WCIR read passes the
local context; nested fallback reads and unrelated register traffic do not.
The existing dispatch condition supplies direct/queued classification without
a second predicate evaluation. A direct accessor records the value immediately
after the existing assignment and before returning. The caller then records
the value it consumed. Request, attributed completion and last-completed-request
counters are 64-bit and overflow ends capture as failed.

The queued branch retains its original wake and interruptible wait, but **never
passes the stack context to the HIF worker**. Its completions are unobserved,
not evidence that no hardware read occurred. Its wait result is still discarded
by the native macro and is not recorded by this producer. Queued and mixed
records therefore remain insufficient for ordinary stop consistency, including
when the initialized zero or an unattributed actual read clears READY. No
asynchronous callback retains a pointer into the stop caller's stack.

The context checks output-pointer identity, register offset, dispatch and
request ordinal before attributing completion. Duplicate or invalid completion,
retired binding and ordinal/count overflow fail capture. The helper holds no
native HIF lock and performs no additional register access. The existing
pstore writer still serializes append, enforces capacity and closes on error.
Stack ownership does not prove adapter/thread quiescence; native lifetime and
recovery requirements remain separate.

## Verification

The [host fixture](test-stop-capture.py) compiles both actual adapter-stop
bodies, their selected register-dispatch macros and actual register-accessor
bodies. It links the real observer helpers and slot writer to injected hardware,
queue, clock and cleanup operations. The [45 comparisons](results/stop-capture-test.txt)
require identical native effects across fifteen cases, with capture disabled,
enabled and an injected lost record store:

- ordinary direct completion;
- each entry gate, firmware-owned skip and command failure;
- fallback success, reset timeout and bus-failure reset;
- interrupted queued wait without a read and queued completion with a read;
- direct dispatch by a named HIF caller and probe-failure cleanup;
- READY clear after failed fallbacks and mixed direct/queued dispatch.

Only the eligible ordinary direct case passes `check_stop()`. All other
cases retain a successful native adapter return and are refused by the stop
checker. A lost record store leaves incomplete framing, with identical native
effects; disabled capture makes no retained stores. The fixture resets observer
globals only when modeling a new boot. It does not model physical timing,
interrupt delivery, real kernel locks or concurrent native object lifetime.

Reproduce against the pinned original files, patched stop files and prior DMA
helper files:

```sh
python3 experiments/2026-09-07-mt6797-wifi-observer-feasibility/test-stop-capture.py ORIGINAL STOP_PATCHED DMA_PATCHED
```

Patch replay and reversal pass. Strict Checkpatch passes with explicit
exceptions for the synthetic non-certifying archive identity, new-file
maintainer inventory, legacy native field names and macro argument reuse.
The reused dispatcher retains native macro evaluation behavior; the added
context arguments are only null or a local pointer. Spelling and const-structure
dictionaries were unavailable. This is not an upstream submission.

The Buildbox `check-startup-objects.py COMMIT --stop` lane compiles the complete
native adapter, glue, accessor and new helper units after applying the full
pstore/DMA/stop dependency chain. It verifies patched header dependencies.
Compilation is pending for these inputs. A full kernel rebuild and link,
controller integration and independent watchdog recovery remain required
before candidate admission; no device action is selected.
