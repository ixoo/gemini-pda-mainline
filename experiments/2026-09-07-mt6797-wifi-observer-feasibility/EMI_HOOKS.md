# Native EMI protection and copy capture

This unselected observer component fills the kind-8 producer gap described in
[persistent capture](PERSISTENT_CAPTURE.md#emi-section-payload-and-consistency-check).
It follows the [firmware image hooks](FIRMWARE_IMAGE_HOOKS.md). It does not admit
the native permission policy, supply shared-memory ownership or select a boot.

## Exact observation

The [patch](patches/emi/0001-wlan-capture-native-EMI-protection-and-copy.patch) and
[source receipt](results/emi-capture-sources.json) pin six parent/output files.
Apply it after the existing fifteen pstore/DMA/stop/read/image patches. It is
absent from the canonical kernel series. Its synthetic archive author supplies
no DCO certification or upstream submission claim.

For sections 2 and 3 of the selected four-section image, the loader passes its
image context into a section recorder. A monotonic counter admits only two
section operations in the captured cycle; a third attempt closes observation.
Each section record carries the image/read ordinal, adapter, physical base and
original descriptor. A returned non-null mapping receives that section's
ordinal as mapping identity. Copy records derive source and destination offsets
from the actual pointers passed to the existing `kalMemCopy()`, with pointer
and extent guards before observation. The helper reads no firmware payload.

The native MPU wrapper discards its lower return. New built-in capture variants
therefore carry the section ordinal and open/restrict phase through the existing
spinlocked wrapper into `mt_emi_mpu_set_region_protection_capture()`. The lower
helper emits entry and return around the existing secure call, while that lock
is still held. It records the actual packed region/permission argument and
signed result. The configuration-dependent no-op branch has its own recorded
branch value. Existing APIs remain zero-capture wrappers, with their original
return behavior. The new variants export no module symbols.

The native permission requests, secure calls, map/copy ordering and outer
wrapper result remain unchanged. The instrumentation does not repair ignored
mapping failure, skipped copies or missing unmap. A null native mapping can
still fault in the existing copy path; a failed span condition can still leave
the loader reporting success. These are candidate admission concerns, not
successful transfer evidence. Added local arguments make each copy record and
its native call use the same pointers and length.

Each complete section produces eight 128-byte records: section, protection-open
entry/return, mapping result, copy entry/return and protection-restrict
entry/return. Two sections add 2048 bytes, separate from image, read, DMA and
cycle records. There is no extra mapping, payload access, hardware readback,
permission request, unmap, retry or recovery action. Record writes add time
inside the existing EMI lock; the full lock/latency/recovery budget remains
unmeasured and must be admitted before hardware use.

## Tests and limits

`test-emi-capture.py PARENT CHANGED IMAGE_SOURCES DMA_SOURCES` composes the actual
receipt-pinned divided loader, MPU wrapper, lower function, capture helpers and
record writer. It injects the secure call, lock, mappings, copies, file I/O and
hash backend. Permission packing comes from the native pinned header. It
compares the original and changed native effect sequence and return value with
capture enabled and disabled and with both secure and no-op lower branches.

Eleven paths cover success, either HIF stage failure, missing EMI base,
persistent/restored image mutation, skipped copy, null mapping, lost copy-return
record, negative lower status and unexpected positive lower status. The null
mapping case logs the would-be copy without dereferencing it; it does not claim
the native kernel safely returns from that fault. Eleven guards cover operation
budget, invalid section/order, null mapping, pointer/span, zero-length and stage
refusals. The injected append asserts lock ownership for protection records.

Successful secure-path records pass both image/read lineage and full image/EMI
coverage checks. Hidden negative/positive lower errors and skipped copies fail
EMI validation even when the native loader returns success. A no-op protection
branch is not accepted as secure protection. Boundary-matched image hashes
still cannot establish interval immutability, and copy return cannot establish
visibility to another master.

`check-startup-objects.py COMMIT --emi` is the clean-pushed Buildbox compilation
path for seven complete translation units and sixteen patches. It verifies the
patched EMI header and lower capture calls as well as the five WLAN units.
Compilation evidence will be recorded separately; this reproduction command is
not a kernel-link or device-runtime result. Controller, provider OFF, isolation,
shared reservation/permission ownership and recovery admission remain open.
