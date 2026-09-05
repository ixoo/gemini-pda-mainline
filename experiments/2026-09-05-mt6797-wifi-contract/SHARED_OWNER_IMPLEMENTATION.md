# Shared EMI and AP-DMA ownership: implementation proposal

Implement one retained CONSYS resource manager, with a private WLAN image
binding, above the existing SCPSYS/reset/regulator authorities. Keep packet
AP-DMA admission separate from firmware EMI ownership: the first whole-image
executor can use PIO. This proposal adds no runtime provider, successful stub,
DT node, policy value or device action. It specifies what the real owner must
do and how the existing parser/HIF code should call it.

The kernel integration owner confirmed the current boundary: local proposal
`f9c13fe954cc8141de51b8f5c87c44632a1e3eea`,
`experiments/2026-09-05-mt6797-whole-image-plan/src/image-plan.{c,h}`,
describes every section, but `mt6797_image_plan_admit()` returns its explicit
owner-required refusal for every mixed image. `get_ordinary()` also applies
that whole-plan gate. Preserve both behaviors until a real owner/executor is
connected; do not add a Boolean or callback that bypasses them.

## Reuse and patch placement

| Existing component | Concrete use in the implementation |
| --- | --- |
| `mtke_parse/get`, `image_plan_prepare/describe` in the integration proposal | Prepare and inspect every section of immutable firmware before resource activation or any ordinary transfer. Keep descriptive metadata separate from executable views. |
| Private kernel `hif.{c,h}` in `2026-09-05-mt6797-wifi-hif-core` | Execute real logical-register reads and ordinary CONFIG/ACK/PDA operations. Its context mutex does not supply external power, IRQ, reset or shared-register ownership. |
| [EMI ABI helper](src/emi_abi.h) | Prepare confined region-18 arguments and decode the raw signed-low-word result. Do not duplicate its translation/alignment/error arithmetic. |
| [Whole-image model](WHOLE_IMAGE_PLANNER.md) | Preserve complete prevalidation, table order, one writable EMI batch, separate seal, terminal poison and firmware-lifetime retention. Its mock owner is not a kernel provider. |
| Existing MT6797 SCPSYS, TOPRGU and regulator work | Keep island/rail/reset effects with their real owners; extend their confirmed-state/admission interface rather than remapping SPM or keyed reset registers in WLAN. |

The patchable split is a shared manager under `drivers/soc/mediatek/`, its
private client declarations, and a WLAN executor beside the private HIF core.
The manager owns reservation/remap/protection policy and client generations.
SCPSYS retains physical power prerequisites after uncertainty as specified in
[PROVIDER_OWNERSHIP.md](PROVIDER_OWNERSHIP.md). The WLAN executor owns immutable
firmware, the complete plan, protocol accounting and section progress. Do not
export these as a userspace ABI or place Wi-Fi sequencing in genpd callbacks.
The initial manager must have a permanent reviewed provider lifetime; a
consumer's devres cleanup cannot own retained hardware prerequisites.

## Reservation and identity contract

Resolve the manager's `memory-region` phandle against the **boot's** reserved
memory resource, using the reserved-memory lookup/resource APIs. Require
`no-map`, no reusable/shared-DMA-pool treatment, checked base/size arithmetic,
and no overlap with another claimed resource. Record and retain the exact
resource identity; neither an old base nor an apparent gap is an allocation.
[Pinned reserved-memory APIs](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/of/of_reserved_mem.c#L843).

The selected remap encodes a 1 MiB-aligned base in a 32-bit address space.
Require that alignment and that the first 1 MiB fits without truncation or
wrap. The resource may be larger; do not require the historical 2 MiB size or
claim the remainder. The EMI helper's ability to represent some wider original
addresses does not establish a wider remap and must not relax this check.

| Extent relative to the verified base | Ownership and lifetime |
| --- | --- |
| `[0, 0x80000)` | WLAN firmware reservation, retained from image activation through confirmed firmware quiescence, including after START and consumer error. Every EMI section must fit here independently. |
| `[0x80000, 0x100000)` | WMT control/coredump protection region. WLAN cannot map, clear, copy into, restore or release it. WMT's smaller mapped extent does not make its remainder available. |
| Remaining resource | Reserved for unresolved/other clients. No packet allocation or speculative clearing. |

Use subtraction-based checks for every described EMI offset/length before
admitting **any** ordinary section. Keep source bounds/overlap and destination
checks from the parser. A larger reservation never expands the WLAN window.

The executor retains the immutable `request_firmware()` buffer and owns its
plan storage exclusively. The manager binding records that plan identity,
source-buffer lifetime, reservation identity, power/firmware generation and a
monotonic owner generation. No caller may invalidate/reuse the plan storage
while bound; generation wrap refuses a new binding. Pointer equality alone
is not a reuse check. A firmware epoch change invalidates every old binding.
The current plan has **no generation field** and is not already such an opaque
snapshot. The real executor must prepare its own private validated snapshot
from owned immutable bytes, with no external reprepare/invalidate access, or
add and review the missing generation/lifetime mechanism. `describe()` alone
does not close that gap. The integration owner explicitly confirmed this
requirement; the proposal does not silently ascribe it to today's header.

## Private interface to implement, not a current admission API

Use opaque `struct mt6797_consys_image` objects allocated by the real manager.
The proposed internal operations below are to be implemented together with
their effects, not installed as success-returning placeholders:

| Operation | Inputs and exact responsibility |
| --- | --- |
| `image_bind(manager, executor_plan, &image)` | Passive allocation/reference acquisition and complete plan/span validation. Return no hardware permission. Missing owners return defer/unsupported errors; competing live clients return busy. |
| `image_begin(image, deadline)` | Validate the complete stable plan and every EMI span against the actual owner binding before any ordinary transfer; reject plan/owner generation changes. Obtain the actual confirmed powered downloader epoch, shared exclusion and HIF prerequisites; establish the owned remap. Only completed admission enables ordinary transfers. This is not `pm_runtime_get()` success renamed as ownership. |
| `image_emi_open(image, deadline)` | After ordinary-section completion, apply the reviewed writable region-18 policy once, preserving the first error and raw SMC status. Mark the attempt before the call. |
| `image_emi_copy(image, section_index, deadline)` | Resolve bytes/offset/length from the retained plan internally; reject ordinary, out-of-range, duplicate or out-of-order entries; enforce bounds and copy only that section. No caller-supplied physical address, payload pointer or permission word. |
| `image_emi_seal(image, deadline)` | Require all planned EMI copies, establish copy visibility, apply the reviewed final policy, and recheck the same owner generation. Sealed is a real effect/state result, not a caller-set flag. |
| Executor START operation | Under the same owner/transaction exclusion, require complete ordinary accounting plus sealed EMI; record START attempted before the first I/O, call the real START transport, then record submitted separately from observed readiness. Use the [reviewed private START core](../2026-09-05-mt6797-hif-start-core/README.md); its [compile acceptance](../2026-09-05-mt6797-hif-start-core/BUILD_RESULT.md) does not supply the missing owner or executor. |
| `image_abort(image, primary_error)` | Poison the image and HIF transaction immediately. Perform at most the specifically safe bounded containment action below. Retain the binding and physical responsibilities after effects. |
| `image_close(image, deadline)` | Attempt owner-controlled quiescence and release only after that succeeds. Return an error and retain the object/resources if it cannot be proved. No unconditional `void put()` may implement this operation. |

Names are proposal names, not symbols already present in a header. The executor
must call owner admission rather than weakening the existing plan API. Ordinary
views should be derived internally from the bound immutable plan after begin;
do not expose an ordinary-only escape hatch for a refused mixed image.
Indices are unsigned section indices; deadlines are absolute monotonic
nanoseconds compatible with `ktime_get_ns()` and the existing HIF API, not a
fresh relative timeout per chunk. Preserve that API's operation-budget checks
inside the executor's complete-image budget. Output bindings start NULL on
passive bind failure; later failures remain attached to the existing object.

A passive binding that never attempted hardware effects can be destroyed
normally. After effects, the manager retains the object independently of the
consumer until close succeeds or recovery explicitly supersedes it. Allocation
failure before effects and hardware uncertainty after effects must have
different cleanup paths. Do not hand an error to a caller and silently drop
the only reference to unresolved resources.

## Shared exclusion and state

Maintain per-client ownership for WMT, WLAN, BT and GNSS, plus an island
generation, active-image pointer and fault state in the manager. A sleeping
lifecycle mutex serializes transitions; it is not held throughout firmware
runtime. The recorded claims persist while unlocked. A separate short remap
critical section serializes masked register operations through the existing
shared register owner. Lock order is manager lifecycle, image transaction,
then HIF context/short register operation. Never sleep or make SMC calls while
holding an IRQ spinlock.

The first supported epoch must establish that other clients/firmware agents
cannot reset, remap or consume the WLAN loading range. Absence of Linux BT/GNSS
drivers is not that evidence. Use an attributable cold/handoff state and the
common owner's real client controls; this proposal supplies no invented
firmware semaphore or per-core reset. Do not require CONMCU to remain reset
during HIF INIT: a downloader must run. The transition from common reset/power
state to that owned downloader epoch remains an explicit provider obligation.

Ordinary WMT/BT/GNSS activity may coexist later only under separately checked
non-overlapping grants. A global reset, remap-base change, MPU reconfiguration
or power-off requires coordination with **all** affected clients, including
firmware. Another client's active claim causes refusal, not forced teardown.
All Linux writers must go through the manager; its mutex cannot exclude an
uncoordinated secure-world or firmware writer. Their handoff contract is a
separate admission premise.

For PIO, the manager/executor must hold real powered mapping, exclusive host
ownership, reset exclusion and the dedicated HIF IRQ/setup-data exclusion
required by `hif.h`. Block new work before joining existing work; do not wait
for an IRQ worker while holding a lock it needs. Revalidate the generation
after draining. Only use an established HIF IRQ mask/restore path; no new
logical-register side effects are inferred here. A normal context mutex is
not a substitute for these responsibilities.

Suggested internal states are `BOUND`, `ACTIVE_LOADING`, `EMI_WRITABLE`,
`EMI_SEALED`, `START_ATTEMPTED`, `START_SUBMITTED`, `RUNNING`, `QUIESCING`,
`FAULT_HELD` and `CLOSED`. Preserve the stage reached, first error, containment
error, raw secure results and generation. Missing dependencies, busy ownership,
stale generations, deadline expiration and a poisoned session remain distinct
errors. Do not translate every refusal to a successful empty lease.

## Remap, MPU and copy operations

The actual shared register is `0x10001340`, not the stale source comment's
address. The common low field is bits 12:0: encoded base bits 11:0 plus enable
bit 12. WLAN's temporary window uses bits 31:16; preserve bits 15:13 too.
Use checked masked replacement under common serialization, not the vendor's
accumulating OR. Require known/handoff-owned initial state; an enabled mapping
to an unexpected base is refusal. Read back the owned field after change and
check the neighboring field has not changed. The upper-window helper, if later
needed, takes a 64 KiB-aligned address and restores only its owned upper field.
The ordinary PIO/EMI-copy path must not invoke it merely because it exists.
[Field-sharing evidence](OWNERSHIP.md).

Region 18 is the WLAN provider operation. Region 19 remains WMT-owned and is
not touched by WLAN recovery. Prepare the exact inclusive first-window range
with `mt6797_emi_prepare()`, using the real owner-held selector context and
reviewed writable/final policy descriptors. Neither policy is supplied by
the WLAN caller. Do not select the vendor all-domain policy as a default.
Master/domain identities and overlap/priority effects of other MPU regions
must support the policy; numeric vendor domain fields alone do not do so.

The real secure adapter calls the compatible deployed service, retains the raw
result, and uses `mt6797_emi_decode_result()` for its signed-low-word status.
No synthetic success from the old Linux wrapper is acceptable. Lock denial
does not authorize unlocking or switching regions; bit 26 remains refused.
An explicit selector observation must be stable for the operation, rather
than a zero-initialized enum or an unrelated DRAM-size predicate.
No read-only query of the retained secure software-lock latch is established;
do not invent one or issue a trial protection write as a passive probe. A
properly admitted operation may still encounter lock denial and must handle it.
[ABI and retained implementation limits](EMI_ABI.md),
[region effects and lock limits](RETAINED_EMI_SECURE_ABI.md).

Map only the first WLAN window under an explicit non-cacheable reserved-memory
contract, retained by the manager rather than consumer devres. Do not silently
fall back to cached mapping if that contract fails. The reviewed implementation
choice must account for the actual `no-map` resource classification: ARM64
rejects an ordinary RAM alias, and `memremap()` rejects mixed ranges and
non-WB System RAM mappings. `memremap()` and `ioremap()` pointers also require
their corresponding copy/access APIs, not casts hiding the distinction.
[Pinned mapping semantics](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/kernel/iomem.c#L41),
[ARM64 mapping restriction](https://github.com/torvalds/linux/blob/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/arch/arm64/mm/ioremap.c#L17).

Use the selected mapping's ordered copy operation, required write ordering,
and a bounded compare/readback while AP access is still permitted before
sealing. Do not read the HIF FIFO as a flush, reopen final protection merely
to compare, or expose compared firmware bytes. Copy/readback establishes the
AP-side stored image; subsequent firmware readiness is a separate observation
of use. The mapping/interconnect visibility contract must be stated by the
real provider; a bare barrier callback returning zero is not that contract.

One absolute budget applies to each admitted operation, with checks before
and after effects. A synchronous SMC or individual MMIO access is not software-
cancellable; a late return poisons the operation and retains possible effects.
Do not promise that a timer can unwind an in-flight access.

## Unwind, recovery and AP-DMA separation

Before any hardware effect, failure may release passive references. After an
ordinary transfer or any remap/protection/copy attempt, poison first and retain
the image binding. Do not retry a consumed command, refund credits, restore
an old image or declare an interrupted copy undone.

If writable protection was attempted, ownership is still intact, and final
restriction has not already been attempted, permit one reviewed bounded
restriction attempt. Preserve its result separately from the primary failure.
If ownership changed, do not write through the stale claim. A failed final
restriction is not retried automatically. Shared remap restoration is likewise
allowed only with actual client quiescence and unchanged field ownership;
restoring a saved whole register can damage another client.

Close/recovery must establish that firmware can no longer fetch the WLAN EMI
window and that no HIF/DMA operation can access retained resources. Only then
may it release the mapping/claims and ask the power owner to drop its reference.
A PM put, consumer detach, successful `free()` or protocol timeout is not that
witness. The common provider, not a WLAN error label, owns any reviewed reset
and the coherent OFF result. Pending WMT diagnostics are preserved before any
common restart that could clear them. Until a recovery sequence is established,
`FAULT_HELD` refuses further work while retaining prerequisites.

AP-DMA gets a distinct channel claim, not a firmware-memory suballocator.
PIO does not program/enable/reset it. When DMA is eventually admitted, claim
only the HIF channel, coordinate the shared clock/protection owner and I2C/BTIF
users, and serialize HIF command setup with channel operation. Use the actual
DMA master's translation domain, dedicated padded buffers and full-width DMA
addresses. Resolve ADDR2/endpoint encoding before selecting any mask. Release
buffers/mappings only after proven idle; timeout pins them with the poisoned
channel owner. No whole-block reset or forced shared-clock shutdown is an
unwind operation. [DMA contract](HIF_DMA_CONTRACT.md) and
[unresolved translation](ADDR2_TRANSLATION.md) remain the exact effect boundary.

## First device-observable gate and remaining effects

The first proposed gate is a **passive ownership snapshot**, not a firmware
load. On a future explicitly selected candidate, report the actual reserved
bounds/classification and existing owners' coherent state: CONN dual-ACK state,
reset/handoff attribution, shared remap identity, selector availability and
client claims. Read only registers already safely accessible through their
owners. If a DMA/CONSYS register is not safely accessible, report unavailable;
do not turn on a clock/domain just to complete this gate. Its mutation counters
must remain zero. This gate is designed here, not admitted or run.

The hypothesis is that a single manager can bind the real reserved resources
without adopting unknown live firmware or changing another client. Matching
bounds plus a coherent attributable cold/handoff state permit construction
of the resource binding for the separately reviewed active sequence. A live
unowned client, alias/overlap or mismatched remap refuses adoption; unavailable
state is inconclusive. Neither branch automatically starts firmware or changes
the selected boot candidate. The eventual gate needs exact candidate/boot
identity and owner-held observations, not a user-supplied success flag.
The passive candidate must also avoid registration-time or pre-probe CONN
activation: an ordinary `power-domains` attachment is not passive by default.
Use the confirmed-state/deferred-publication boundary in
[DEFERRED_REGISTRATION.md](DEFERRED_REGISTRATION.md), or keep CONN unpublished;
do not add a powered consumer just to obtain this snapshot.

Remaining effects are specific: the real CONN/downloader admission and safe
shutdown sequence; external-writer exclusion; deployed secure ABI and current
region ownership; master/domain policy plus overlapping-MPU priority; reserved
mapping visibility; and HIF IRQ/host-ownership transitions. AP-DMA translation
and idle recovery apply only to the DMA backend. Firmware calibration RE is
not a prerequisite for this offline implementation proposal.

The [private immutable binding](../2026-09-05-mt6797-image-binding/README.md)
now implements copied plan storage, owner generations and passive lifetime
checks, with [kernel compilation accepted](../2026-09-05-mt6797-hif-start-core/BUILD_RESULT.md).
The real resource owner and complete executor still need implementation;
active binding entry continues to refuse at unresolved effect boundaries.
Meaningful fixtures should exercise stale-plan/generation rejection, competing
clients, partial effects, failed containment and retained lifetimes on the
same implementation. They must not call a mock's result hardware support.
This document changes no kernel source, manifest, series or hardware-support
claim; kernel build and device validation were not performed. The roadmap
alone owns ordering and admission of the proposed patches and gate.
