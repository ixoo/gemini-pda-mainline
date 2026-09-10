# Bind firmware observation to the native ON request

The unselected [four-file patch](patches/request-firmware/0001-wlan-bind-firmware-observation-to-the-ON-request.patch)
joins the [request worker](REQUEST_CAPTURE.md) to the existing
[read/image witness](FIRMWARE_IMAGE_HOOKS.md). A successful request return alone
cannot establish a load: native `opfunc_func_on()` returns zero when its driver
state is already ON. The new request state requires a completed image witness
before accepting the ON worker's successful return.

## Causal path and records

The pinned native
[Wi-Fi function callback](https://github.com/gemian/gemini-linux-kernel-3.18/blob/59e00a9144d782e148332009a835b99c43382467/drivers/misc/mediatek/connectivity/common/common_main/core/wmt_func.c)
invokes the registered WLAN probe synchronously. The AHB probe calls
`wlanProbe()`, whose firmware mapping and `wlanAdapterStart()` precede creation
of its WLAN threads. The earlier source-pinned mapping witness carries the
borrowed allocation, adapter and read identity into the divided-image loader.

Three additional kind-10 records link that path to request 1:

| Subtype | Little-endian fields | Native observation point |
| --- | --- | --- |
| 25 | subtype, request, adapter, read ID (`u32`) | Firmware mapping/read entry, before opening the file |
| 26 | subtype, request, adapter, read ID (`u32`) | Validated divided-image witness, before extra descriptor/hash reads |
| 27 | subtype, request, adapter, read ID (`u32`), native status (`s32`) | After the existing image-return record |

The three records add 384 bytes and no firmware-buffer reads, allocations,
file calls, crypto calls or hardware operations. The existing request plus
common/provider records total 4352 bytes with these links; firmware, EMI, DMA,
identity and terminal records remain additional.

The same request lock serializes a three-stage witness. Every stage requires
the bound ON worker, live request phase and matching nonzero adapter/read IDs.
Skipped, repeated, out-of-order, cross-task or mismatched stages fail capture.
The final image status must be zero. Native failures retain their native
behavior and returns. The observer still changes no request, reset, file,
loader or hardware action.

Registration can also invoke a deferred probe from a different context through
`mtk_wcn_wmt_wlan_reg()`. That route cannot satisfy the bound worker check.
This records a refused observation; it does not disable deferred probing or
establish startup isolation. A successful no-load shortcut also fails the
new worker-end gate. Failure has no retry or recovery authorization.

## Decoder and limits

`check_request_firmware()` combines the request/common, firmware-read/image,
EMI and HIF/DMA/ordinary-stop checks. It requires exactly one linked read/image,
HIF acquisition and firmware observation inside ON's worker interval, and
ordinary stop plus HIF release inside OFF's worker interval before common OFF.
DMA records outside both worker intervals are rejected. The older
`check_request_cycle()` remains a request/common-only checker and permits the
new typed links without claiming firmware validation.

The three new native call sites check actual task identity. Temporal containment
of other record families does not identify their issuing tasks. The fixture and
decoder do not prove which bytes reached each HIF submission, interval buffer
immutability, WLAN-thread quiescence, exclusive resource ownership or firmware
execution. A changed-and-restored buffer still passes the boundary hashes.
Controller integration, full-cycle termination, recovery budgets and device
admission remain separate. No kernel profile selects this patch.
The [transmit-boundary audit](TX_SUBMISSION_BOUNDARY.md) now executes native
staging counterexamples and selects the actual transport buffer as the next
payload-witness boundary; caller success and original-buffer hashes remain
insufficient.

## Validation

The [source receipt](results/request-firmware-sources.json) pins four parents,
four outputs and exact format-patch replay/reversal. Apply after the complete
25-patch request-capture composition. The archive author is synthetic and
non-certifying; this is not an upstream submission.

`test-request-firmware.py --tree TREE` reuses the existing request and EMI
fixtures to execute the actual request observer, file-read helpers, divided
loader, hashing observer, EMI wrapper/lower call and slot writer. Task identities,
file contents, crypto and I/O are injected. Eleven native paths preserve return
values and native I/O effects with capture enabled and disabled. Refusals cover
three file failures, six crypto faults, three lost link records, wrong tasks
at read/image-entry/image-return, changed adapter/read identities, repeated or
skipped stages, four witness failures and a successful return without an image.
CRC-valid mutations also check link fields and misplaced record families.

The fixture inserts synthetic DMA, stop, HIF-release and common/provider records
only to test decoder composition. It does not execute a kernel scheduler,
native ioctl/queue path or complete native teardown. The restored-mutation case
is intentionally accepted and preserves the submitted-byte limitation.

The focused Buildbox mode is
`check-startup-objects.py COMMIT --request-firmware`. It composes 26 patches,
runs both request fixtures at their source boundaries and checks the new native
helper dependencies/calls in the fifteen complete translation units.
The [compile receipt](results/request-firmware-object-compile.json) records
success at `a1496ad904012c4063793d779206a7dc5392cb61`. All 74 regular package
files passed exact remote/local inventory and checksum verification; the
`SHA256SUMS` digest is
`3b65f26baa174a7327d336be407257c99fa631168ad93a5df8f75278fb6876f0`.
Both request fixtures pass on Buildbox, and the 22 existing decoder groups pass
locally. Strict Checkpatch passes with only legacy `CAMELCASE` and synthetic
`MISSING_SIGN_OFF` exceptions. Native flags retain `-w`; empty logs are not
warning-clean evidence. No full kernel link, new device test or boot candidate
is included.

The first Buildbox attempt at `ffaa13fb278e58f1fe43d5267d25b4df153a2845`
passed both source-boundary fixtures, then refused before compilation because
the final EMI-family check still required the parent firmware-helper digest.
The successor mode now requires the four pinned child outputs in that final
check, retaining all unchanged EMI pins and the existing parent/child boundary
checks. This was a checker composition error, not a native compiler result.
