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
The [validated Buildbox package](results/stop-capture-object-compile.json)
passes from clean published input `ca870bc02c9a7c55318d5d384b3e0f60f839fc65`:
three original and four patched translation units compile, and all 21 package
files pass remote/local checksum verification. The helper uses the recorded
`ahb.c` compiler flags and has no baseline counterpart. Native commands retain
`-w`; empty compiler logs do not establish warning-clean code.

Two earlier checks were rejected before packaging. The first omitted the
patched NIC basename include directory used by `precomp.h`. After that was
fixed, the check wrongly required the dispatcher header in `ahb.c`, which does
not use it. A diagnostic replay identified that unit and its actual patched
HIF/library dependencies. The final check requires the dispatcher header in
its adapter/glue consumers, the patched library/HIF headers in all three native
units, and the public pstore header in the helper.

Emitted code contains the direct captured accessor, both dispatch branches,
entry/command gates, fallback counter and final stop records. Both native
callers pass their intended distinct IDs. The compiler duplicates some gate
record sites across mutually exclusive branches; these are not extra runtime
records. The prior DMA call sites remain in the accessor unit. These checks
establish object integration, not physical timing or full-cycle behavior.

A full kernel rebuild and link, remaining producer/controller integration and
independent watchdog recovery remain required before candidate admission;
no device action is selected.

## DMA and stop lifetime join

`check_shutdown_bindings()` in [the decoder](capture-records.py) composes the
existing DMA binding, DMA operation and ordinary-stop checks. It requires one
stop invocation for the same software HIF ordinal, all four stop records before
binding release and after binding acquisition, and no recorded DMA activity
after stop returns. DMA within the stop invocation remains permitted: the stop
command can use the native transfer path. Numeric transaction IDs may coincide
across the DMA and stop record families.

The [decoder tests](test-capture-records.py) pass all 19 test groups. Two valid
orderings cover transfers before stop and during its command. Seven deliberately
misjoined streams still pass all three individual checks but fail the new join:
another adapter, stop before binding, stop after release, entry before binding,
return after release, DMA after stop and a second complete stop invocation.
These streams have valid framing and checksums, so rejection tests the
relationship between observations rather than corrupted storage.

This is an offline component check. It does not require a cycle-complete
terminal, establish absence of unobserved activity, validate physical device
identity, join firmware loading or common OFF, or prove thread quiescence. The
future controller/result classifier must require this join alongside its other
cycle predicates. No producer bytes changed and no kernel build or device test
was performed for this decoder change.

## Removal wait witness

The unselected [removal-wait patch](patches/stop-workers/0001-wlan-record-native-removal-completion-waits.patch)
records the native halt-lock result and three completion waits before normal
removal enters adapter stop. It follows the complete 27-patch
[TX payload composition](TX_PAYLOAD.md); its
[source receipt](results/stop-workers-sources.json) pins the three parent/output
files and unchanged baseline worker source. No canonical profile selects it.
The archive identity is synthetic and provides no DCO certification.

The concrete source problem is in `wlanRemove()`: a failed HIF, RX or main
completion wait prints a stack and continues. It then clears thread pointers
and enters adapter stop, whose cleanup releases the common coalescing buffer.
The earlier stop witness therefore cannot distinguish completed native waits
from timed-out workers. Capturing the existing returns adds no wait, retry,
lock acquisition or teardown operation and preserves each native timeout branch.
It does not make that native timeout cleanup safe.

One kind-7 subtype-15 record uses the software HIF device ordinal as its
transaction. Its 40-byte payload is little-endian: subtype, device and
multithread flag (`u32` each), halt-lock return (`s32`), then HIF, RX and main
wait returns (`u64` each). The native `unsigned long` wait returns are widened
without truncation. HIF/RX slots are zero when multithreading is not compiled.
The one record consumes 128 capture bytes. A missing/retired binding aborts
capture; disabled capture makes no retained store. A hang before the summary
leaves it absent.

`check_stop_workers()` supplements the existing ordinary stop check: exactly
one summary must precede exactly one ordinary stop for the same adapter; the
selected multithread branch, zero halt-lock return and all three positive waits
are required. This predicate must be composed with request, firmware, DMA and
resource checks before any later controller interprets a complete cycle. It
neither replaces them nor upgrades their existing scopes.

Successful native waits still **do not prove worker exit**. In the pinned
`os/linux/gl_kal.c`, HIF, RX and main workers signal their completion before
wake-lock active/unlock/destroy calls. The baseline completion locations are
2586, 2665 and 2930. The apparent adapter arguments to those macros are discarded
by their definitions; cleanup uses worker-local wake locks. The
[macro-expansion follow-up](REMOVE_RETENTION.md#completion-tail-correction)
corrects the earlier claim of trailing adapter accesses. It supplies no reason
to move the completion calls. Reset, other callers and full buffer ownership
remain separate requirements.

The [focused fixture](test-stop-workers.py) compiles the actual parent/child
removal wait block, the actual observer and slot writer. Injected completion,
lock, task-pointer and memory operations compare 144 native sequences across
both multithread branches, every timeout combination, halt-lock failure,
disabled/enabled capture and a lost store. The record join rejects missing,
duplicate, late, wrong-adapter and unsuccessful wait summaries. Missing and
retired bindings produce failed terminals. The stop suffix used for the join
is synthetic; the fixture does not execute complete removal, worker bodies,
the scheduler, wake-lock cleanup or hardware.

Host strict compilation, all 22 existing decoder test groups and strict
Checkpatch pass with the legacy `CAMELCASE` and synthetic `MISSING_SIGN_OFF`
exceptions. `check-startup-objects.py COMMIT --stop-workers` adds the producer
unit to the clean-pushed Buildbox composition (28 patches, 18 native units),
verifies source pins and runs the native fixtures. The
[native compilation receipt](results/stop-workers-object-compile.json) records
success at `33db48d8ffd13c2a6c88de739ec2efd3d8fcd62d`. All 87 regular package
files match the remote inventory and the 86-entry checksum manifest, whose
SHA-256 is `88b070963802b013a5a086342eb68d75ec318c054a52ac0b07634c7f8d77cb8c`.
The native compiler commands retain baseline warning suppression; empty logs
are not warning-clean evidence. No full kernel link, device candidate or
device operation is included.
