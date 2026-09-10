# Native Wi-Fi request attribution

The unselected [request patch](patches/request-capture/0001-wmt-bind-captured-requests-to-worker-and-common-off.patch)
connects one native Wi-Fi ON/OFF ioctl pair to its allocated operations,
worker completions and the synchronous [common OFF scope](COMMON_OFF_HOOKS.md).
It follows the [operation ownership repair](OPERATION_OWNERSHIP.md). These are
observation hooks, not a controller, resource exclusion or device admission.

## Recorded path

Capture accepts the exact unsigned-long ioctl arguments `0x80000003`, then
`3`, on the same task. Upper-word aliases are refused even though the native
ioctl masks its argument. Native behavior and returns remain unchanged when
capture refuses a request. The function wrapper binds the allocated operation,
actual opcode, Wi-Fi type and 4000 ms timeout before its power-save wake-up.
The submit hook records the queue offer before publication; actual worker
entry supplies evidence that this operation reached a worker.

A successful ON has seven request records. OFF has nine request records,
with the existing fifteen common/provider records between its common entry
and return. The worker must finish before the waiter records a positive wait,
valid zero result and native success. The ioctl then records its translated
zero return. OFF common entry must run on the bound worker and links request
2 to common/provider invocation 1. No task identifier or pointer is retained.

Kind 10 request subtypes have these little-endian payloads; `u32` fields are
unsigned and `s32` fields signed. The envelope transaction equals request ID.
General kind-10 framing remains opaque; the typed checker enforces this schema.

| Subtype | Fields |
| --- | --- |
| 16 | subtype, request, exact ioctl argument (`u32`) |
| 17 | subtype, request, native opcode, type, timeout (`u32`) |
| 18 | subtype, request (`u32`): queue offer |
| 19 | subtype, request, worker opcode, type (`u32`) |
| 20 | subtype, request (`u32`), core result (`s32`) |
| 21 | subtype, request (`u32`), wait result (`s32`), result-valid (`u32`), operation result (`s32`), native success (`u32`) |
| 22/23 | subtype, request, common invocation (`u32`): entry/return |
| 24 | subtype, request (`u32`), ioctl result (`s32`) |

The sixteen new records consume 2048 bytes; including the fifteen lower-scope
records gives 3968 bytes. Identity, firmware, DMA and terminal records are
additional. The controller must budget the complete cycle before admission.

## Lifetime and failure

A private raw spinlock serializes request metadata and record appends. It
covers no core call, queue operation, signal wait or hardware operation.
Common entry takes the request lock before the separate common lock; common
return releases its common lock before calling the request helper. There is
no common-lock-to-request-lock nesting.

The root task is pinned from ON entry through successful OFF return, including
the interval between ioctls. Each worker is pinned through its observed core
return. Successful releases occur on the matching live current task. A failed
scope retains at most one root and one worker pin until recovery; the existing
common observer can separately retain its worker pin. There is no rearm API.

The operation pointer is protected by the native caller/queue ownership and
cleared before normal waiter cleanup. A final pool release invalidates any
still-bound operation before reuse, including an early power-save wake-up
failure. An inactive capture cannot resume consuming observer metadata.
A competing function operation, mismatched task, bad stage or result,
failed retained append, or native reset entry irreversibly fails capture.
Reset invalidation precedes the first native reset action and applies between
ioctls and after OFF while the complete capture remains active. Auxiliary
non-function operations are not treated as request identity; their resource
effects still require separate isolation.

The observer does not suppress native reset, queue or hardware behavior.
Faults end the evidence stream, not those underlying operations. Capture
failure is never permission to issue another request or restart the device.

## Checks and remaining work

The [source receipt](results/request-capture-sources.json) pins the five parent
files, six outputs and reversible format-patch. The synthetic experiment author
is non-certifying and supplies no DCO sign-off. This patch is outside canonical
series and all kernel profiles.

`test-request-capture.py --tree TREE` compiles the actual request header and
retained slot writer with injected task identities, locks and byte I/O. It
checks normal completion and reference release, inactive behavior, every
missing/repeated event, every lost request record, reset at every boundary,
early pool release, wrong task/operation, rejected arguments/results and
CRC-valid decoder mutations. The common/provider stream used in this test
is synthetic; it tests decoder composition, not execution of the native
ioctl, queue, CCF or concurrent kernel scheduler. The earlier independent
native common/provider and operation-ownership tests retain their own scope.

`check_request_cycle()` requires the complete ordered request/common sequence
and all successful scalar results. It does not equate the absence of a failed
producer terminal with whole-cycle completion: no full-cycle terminal is
created by these hooks. Firmware/HIF causality, external controller identity,
reset/resource isolation, competing consumers and watchdog/recovery admission
remain unchecked.

`check-startup-objects.py COMMIT --request-capture` composes 25 patches and
compiles the fifteen existing full native translation units with pinned
source boundaries and request header/call-target checks. The
[Buildbox receipt](results/request-capture-object-compile.json) records successful
compilation at `090c5ae5dfe73292ecefcb14bd898cdb201c3448`. All 74 regular package
files matched the remote inventory and local checksums. Its `SHA256SUMS` digest
is `8f8da34bc31801c5b1e93e6c31a604f794e40733b276dc401384947f2069ae57`.
The emitted ioctl code retains the full-width entry argument and both translated
return branches; the function wrapper binds before power-save wake-up and the
normal worker path brackets its core call with request records.

The request fixture passed on both the host and Buildbox. All 22 existing
decoder groups and eight slot-writer groups pass. Strict Checkpatch passes with
legacy `CAMELCASE`, synthetic `MISSING_SIGN_OFF` and experiment-only
`FILE_PATH_CHANGES` exceptions. Native compiler flags include `-w`, so empty
compiler logs do not establish warning-clean compilation. Full kernel linking,
timing/lock budgets and on-device validation remain separate gates.

The subsequent [firmware/request join](REQUEST_FIRMWARE.md) adds three link
records and requires image completion before accepting the ON worker return.
The request/common-only decoder above retains its narrower scope.
