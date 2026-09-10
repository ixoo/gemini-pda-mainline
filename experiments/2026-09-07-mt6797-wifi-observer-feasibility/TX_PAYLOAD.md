# Native pre-map firmware payload witness

The unselected [patch](patches/tx-payload/0001-wlan-join-native-firmware-payload-digests-to-DMA.patch)
implements the transport-buffer boundary selected by the
[staging audit](TX_SUBMISSION_BOUNDARY.md). It records the eight actual payload
spans immediately before the existing DMA mapping and joins them to that DMA
operation's ordinary completion and native port return. It does not establish
post-hash buffer immutability, firmware execution or a device-test candidate.

## Native path

The divided loader passes its existing image context to the section loop.
A stack-owned chunk witness follows each synchronous call through allocation,
the native payload copy, NIC coalescing and the AHB port function. Every stage
checks the borrowed image owner's actual `current` task and the expected phase.
Source, command and coalescing pointers, section position and bounded extents
must agree. No witness is queued, globally published or given an additional
task reference. Existing no-witness entry points remain available; ordinary
NIC calls retain the original HAL macro path.

Only the ordinary DMA mapping branch can produce a payload witness. Immediately
before `dma_map_single(..., DMA_TO_DEVICE)`, the observer checks the logical
PDA header and hashes its payload using the image's already acquired generic
SHA-256 transform. It excludes the eight-byte header and all bus padding. The
reserved header byte remains native policy and is not required to be zero.
The subsequent link records the existing DMA observer's transaction ordinal;
the port-return witness requires that mapping to have reached its recorded
unmap completion. PIO, alternate mapping, early refusal and incomplete DMA
cannot supply a successful chunk witness. Native behavior and returns remain
unchanged, including an early false port return hidden by NIC success and a
timeout returning true while retaining DMA resources.

Each complete chunk adds three kind-7 records, using the chunk ordinal as the
record envelope's transaction. All scalar fields below are little-endian `u32`:

| Subtype | Payload fields after subtype | Observation |
| --- | --- | --- |
| 12 | adapter, image/read ID, chunk, section, image offset, payload length, logical length, 32-byte SHA-256 | Actual coalescing payload before mapping |
| 13 | adapter, image/read ID, chunk, DMA transaction | After the existing DMA-map record, before programming |
| 14 | adapter, image/read ID, chunk, DMA transaction, native port result | After ordinary unmap; true is required |

Eight chunks add 24 records (3072 bytes) and eight hashes over 14832 payload
bytes. They add no transform allocation, payload copy, mapping, hardware read,
write, retry or cleanup. Capture disabled adds no hash or capture-slot store.
The new hashing and record writes occur while the native HIF lock is held;
stack use, lock duration and the full watchdog budget still need candidate-level
review and measurement. CPU reads after DMA ownership transfer are not added.

## Decoder and retained expectations

`check_image_tx()` requires independently supplied image metadata and eight
payload digests, exact ordered section coverage, one distinct ordinary TX DMA
transaction per chunk, and the selected 512-byte bus-block extent. It rejects
interleaved unrelated DMA within a chunk and requires the digest, map, link,
programming, unmap and port-return order. `check_request_tx()` composes this
with the existing request/read/image/EMI/stop checks. Neither classifies a full
hardware cycle as successful.

The [retained expectations](results/firmware-tx-chunks.json) were derived inside
the RE VM from the retained file only after its full size and SHA-256 matched
the existing [image inspection](../2026-09-05-mt6797-wifi-contract/results/firmware-mtke.json).
For each of the first two descriptors, split its source span into consecutive
chunks of at most 2048 bytes and hash each exact span. The receipt contains
only image identity, section metadata and hashes. It contains no firmware or
calibration bytes and is not a runtime observation or redistribution license.

A mutation injected after the pre-map hash is deliberately accepted by the
digest/record check even though the mocked mapped bytes differ. This prevents
mistaking the new boundary for an immutable-buffer proof. Native staging occurs
before HIF locking; broader consumer isolation and a stable-buffer ownership
contract remain necessary. Controller integration, complete linking, recovery
budget and device admission remain open.

## Shared-buffer ownership review

Read-only inspection of Gemian source revision
`59e00a9144d782e148332009a835b99c43382467` narrows the next ownership change.
The locations below are relative to `drivers/misc/mediatek/connectivity/wlan/gen3/`
in that baseline, before the observer patches; they are source observations,
not evidence of a runtime race or an exhaustive caller-isolation proof.

| Source location | Observed lifetime or access |
| --- | --- |
| `nic/nic.c:195-204,262-264` | Allocate one common buffer sized to the larger TX/RX requirement; release it during memory teardown. |
| `nic/nic_tx.c:143,1565,1723,2269` | TX aliases that allocation. MSDU, command and initialization-command paths stage into it before entering the port operation. |
| `nic/nic_rx.c:206,3247-3275` | RX aliases the same allocation. Aggregated receive fills it through the port, then copies packets out after the port call returns. |
| `nic/nic_rx.c:3680-3686` | The extra-four-byte response branch likewise reads into the shared buffer and copies the response out after the port call. |
| `include/config.h:196,705,740` | Baseline definitions enable RX aggregation, multithreading and the extra-four-byte response branch. These definitions are not a candidate configuration receipt. |
| `os/linux/hif/ahb_sdioLike/ahb.c:855,1133` | Port read/write acquire the HIF lock inside the port functions; this does not cover earlier TX staging or subsequent RX copy-out. |
| `os/linux/gl_init.c:1965,1975,2047,2078-2081` | Probe publishes `gPrDev` and installs the IRQ before adapter start, but creates the normal TX/HIF/RX workers afterward. |
| `os/linux/hif/ahb_sdioLike/ahb.c:1314-1352` | The installed AHB IRQ handler disables the IRQ, records bookkeeping, sets the interrupt flag and wakes the HIF wait queue. It does not itself fill the coalescing buffer. |

Consequently, early IRQ installation alone is not evidence of a competing
buffer writer during firmware loading. Normal worker creation order narrows
startup concurrency, but does not prove that global entry points, reset or
teardown are excluded by the eventual capture controller.

A guard only around `kalDevPortWrite()` is insufficient. Any ownership fix
must cover the common allocation from before TX staging through DMA release,
and RX filling through its final copy-out, together with allocation teardown.
A capture-only overlap detector could invalidate evidence but would not prevent
the underlying access. It must not be presented as an immutability fix. Resolve
controller exclusion of these callers before choosing between a diagnostic
detector and changed native serialization; neither change is selected here.
In particular, do not insert a second acquisition of the existing HIF lock
around staging without resolving nested port locking and all return paths.

## Validation

The [source receipt](results/tx-payload-sources.json) pins six parent/output
files and format-patch replay/reversal: five files change, while the unchanged
HAL header is a fixture input. Apply after the complete 26-patch request/firmware
composition. The archive author is synthetic and supplies no DCO certification.
No canonical kernel profile selects this patch.

The [focused fixture](test-tx-payload.py) compiles actual parent/child section
loops, chunk constructors, NIC staging, AHB port functions, PDMA callbacks,
image observer and slot writer. Adapter layouts, tasks, CONFIG success, command
allocation, crypto, DMA API, MMIO and locks are injected. The wrapper invokes
section/image boundaries directly; it does not execute the native ioctl,
scheduler, full divided loader, EMI path or teardown. The previous fixtures
retain their separate scopes.

Nine native paths preserve returns, MMIO order and mocked mapped bytes with
capture enabled and disabled. They cover ordinary completion, early port
refusal, changed staging, wrong task, retained-resource timeout, PIO, post-hash
mutation, hash failure and allocation failure. Tests also refuse 29 stage,
pointer, extent and task faults, all 24 lost payload records, and CRC-valid
field/order/drop/duplicate mutations. Normal capture uses the same one
transform allocation/free and ten hashes total: two image and eight payload.
Host strict compilation and the existing 22 decoder groups pass. Strict
Checkpatch passes with the legacy `CAMELCASE` and synthetic `MISSING_SIGN_OFF`
exceptions. No device operation was performed.

`check-startup-objects.py COMMIT --tx-payload` is the focused clean-pushed
Buildbox mode: 27 patches and 17 complete native translation units, including
both newly changed NIC and AHB units. It verifies parent/output pins, runs
the request fixtures before this patch and the new native TX fixture afterward,
and checks the emitted capture dependencies/calls. The
[native compilation receipt](results/tx-payload-object-compile.json) records
success at `ac128b5bbf2366e710261c1cf84b1f06000f1ffa`. All 84 package files
were verified against the remote inventory and the 83-entry checksum manifest;
the manifest SHA-256 is
`736a935e8a302388f8c9f326f4b6a4f671f6cdf2678cdda21e8e458282eb8066`.
Native commands retain the baseline warning-suppression flags, so empty
diagnostics do not establish warning-clean compilation. No full kernel link,
new boot candidate or device execution is included.
