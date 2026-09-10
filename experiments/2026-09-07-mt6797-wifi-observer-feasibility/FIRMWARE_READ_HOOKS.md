# Native firmware file-read capture

The unselected [patch](patches/firmware-read/0001-wlan-capture-native-firmware-file-read-results.patch)
records the allocation, signed file-read result and output publication in the
native `kalFirmwareImageMapping()` path. The [source receipt](results/firmware-read-capture-sources.json)
pins the complete original and changed `gl_kal.c` files to Gemian revision
`59e00a9144d782e148332009a835b99c43382467`. The tested composition is the
MT6797 AHB configuration with the ten pstore patches, DMA hooks and stop hooks.
No manifest profile or boot candidate selects this patch.

The native `kalFirmwareLoad()` helper reports success after a negative, short
or oversized file-read return and assigns that signed result to an unsigned
32-bit length. A successful wrapper return therefore cannot justify reading or
hashing that reported extent. The observer preserves those native effects and
records both values. It adds no payload read, hash, file operation, allocation,
cleanup, retry or change to native error handling.

## Records and scope

Kind 7 subtypes 8–11 use a mapping-invocation ordinal in the envelope. Each
payload includes the existing software HIF binding ordinal as its adapter ID.
No pointer, filename, payload or calibration content is published.

| Subtype | Layout | Fields after subtype and adapter ID |
| --- | --- | --- |
| 8, entry | `<2I` | None; recorded before opening firmware |
| 9, allocation | `<5I` | Requested file bytes, actual aligned allocation argument, allocation-present flag |
| 10, read | `<4Iq` | Requested read bytes, read-called flag, signed 64-bit actual return |
| 11, return | `<5I` | Outputs-published flag, published 32-bit length, returned-buffer-present flag |

The context is local to the synchronous mapping invocation. An internal read
helper receives that context; the original read entry point remains available
with a null context. The missing-file-method branch records no read call and a
zero result placeholder. Open failure records entry and unsuccessful mapping
return only. Native assertions, file position, size conversion, output stores,
free and close operations retain their original order. Retired binding,
ordinal overflow and writer failure end capture without repairing native work.
A hang or fault may leave only a prefix.

`check_firmware_read()` requires the exact four-record sequence, a stable adapter
ID, a nonzero allocation covering the requested bytes with correct four-byte
rounding, an exact full read and matching successful publication. Its result
checks recorded extents only. It does not prove input-buffer identity, original
64-bit inode size, immutable contents, expected image hash, firmware execution,
HIF lifetime membership, a complete cycle or hardware safety. In particular,
the unchanged native null-allocation and invalid-length paths can still fault.
Future hashing must have its own buffer and extent checks before dereferencing.

## Validation

The [host fixture](test-firmware-read-capture.py) compiles the actual original
and patched mapping/read bodies with the real capture helpers and slot writer.
It compares 16 cases with capture disabled, enabled and a lost first-record
store: 48 identical native effect sequences. Cases include open failure, zero
size, null allocation, negative/short/zero/oversized reads, a return exceeding
32 bits, allocation rounding overflow, absent file/method pointers, binding
retirement and both aligned and unaligned successful sizes. Native assertions
are recorded and file operations are injected; this does not execute a real
null-buffer file read or model kernel fault handling, timing or concurrency.

Reproduce with the receipt-pinned complete source files and DMA helper directory:

```sh
python3 experiments/2026-09-07-mt6797-wifi-observer-feasibility/test-firmware-read-capture.py ORIGINAL_C PATCHED_C DMA_PATCHED
python3 experiments/2026-09-07-mt6797-wifi-observer-feasibility/test-capture-records.py
```

All 20 decoder test groups pass, including valid-checksum field mutations and
malformed record rejection. Patch replay/reversal and strict Checkpatch pass;
exceptions cover the synthetic non-certifying archive identity, file inventory,
legacy names and macro reuse. This is not an upstream submission.

The [native compile receipt](results/firmware-read-object-compile.json) passes
from clean published input `e09ef144638983cff0b329f1c931c3e3974cc1bb`. The
Buildbox lane `check-startup-objects.py COMMIT --firmware-read` applied all
13 patches and compiled original and changed `gl_kal.c` using the recorded
AArch64 command. Patched HIF, library, dispatcher and pstore header dependencies
were verified, as were the emitted capture/read call sites. All eight package
files passed remote/local inventory verification. The native flags retain
`-w`; empty diagnostics do not establish warning-clean code. Full kernel
linking, controller integration and device validation remain separate work.

## Firmware-read lifetime join

`check_firmware_bindings()` composes the file-read extent checker with the
existing DMA/ordinary-stop lifetime checker. Every firmware-read record must
name that same software HIF binding, follow its acquisition and precede stop
entry. A read that straddles either boundary is rejected. Several complete
mapping invocations are allowed; their ordinals are independent of DMA and
stop ordinals. This does not associate a particular read with a DMA transfer.

All 22 decoder test groups pass. Three valid streams cover reads before DMA,
after DMA, and multiple mapping invocations. Eight valid-checksum streams pass
the separate extent and shutdown checks but fail the join: another adapter,
read or entry before binding, read after release, read during or after stop,
and return during stop or after release. Missing read or shutdown evidence
also refuses. These fixtures establish recorded ordering only, not producer
coverage, buffer identity, firmware execution, common OFF or a complete cycle.

No producer or kernel input changed. No kernel build or device test was run
for this offline decoder change. The integrated controller, remaining native
capture sites and admitted recovery protocol are still required before a
hardware session can establish the lifetime predicates.

The separate [failure-handling successor](FIRMWARE_READ_SAFETY.md) rejects
invalid sizes, failed allocations and incomplete reads before mapping
publication. It deliberately changes those native failure paths while keeping
this original capture patch and its receipts unchanged.

The unselected [firmware image hooks](FIRMWARE_IMAGE_HOOKS.md) carry the successful
read witness into native buffer hashing and section records; interval immutability
and full cycle admission remain unproven.
