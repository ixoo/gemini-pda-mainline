# Complete MTKE image planning boundary

This original kernel-compatible delta fills the C planning gap between the
existing structural parser and private HIF core. It preserves a complete
ordinary-plus-EMI description while explicitly refusing unresolved EMI execution.
It is incremental whole-image implementation, not a firmware loader or runtime
admission. No device or Buildbox operation is requested by this packet.

## Existing work and the missing boundary

The pinned Python `wifi_whole_image.py` already implements whole-image sequencing
and a modeled exclusive lease contract. The C MTKE parser already validates all
entries and returns indexed views. The private HIF core already executes one
bounded ordinary section under a caller-retained INIT transaction. This delta
reuses that parser and adds no duplicate parser, FIFO encoder, executor, CRC or
owner scaffold. [inputs.json](inputs.json) pins all reused source identities.

The Python model owns an immutable snapshot and acquires its modeled EMI lease
before the first ordinary transfer. Its broader execution contract is not ported
or declared complete here. This C layer is a fixed-size caller-owned context,
with no allocation or section array, and no runtime registration or hardware
callbacks. It validates the entire image before publishing any plan.

## API and refusal boundary

`mt6797_image_plan_prepare` invalidates any old plan, calls the existing complete
parser, visits every section, and publishes total count plus separate ordinary
and EMI counts and byte totals only on success. Every declared section is
accounted for. A valid mixed image returns planning success, never a partial
ordinary-only plan. Invalid or unknown-reserved input returns the parser's -1
or -2 and leaves the entire plan invalid.

`mt6797_image_plan_describe` exposes every validated section's offset, length,
destination, route, masked EMI offset and raw/interpreted encryption metadata.
Descriptions contain no payload pointer or transfer handle. They remain available
for mixed-image review even when execution admission is refused.

`mt6797_image_plan_admit` is a separate routing gate. Any EMI section returns
`MT6797_PLAN_EMI_OWNER_REQUIRED` (-3), because this implementation has no real
shared EMI/AP-DMA owner binding. No Boolean or supplied callback can override
that refusal. `mt6797_image_plan_get_ordinary` applies the whole-plan gate before
returning even the first ordinary payload view. On refusal it clears output.
There is no function to transfer an EMI section or silently skip it.

Ordinary-only routing success permits inspecting its ordinary views; it does not
certify firmware identity, allowed destination policy, HIF ownership, transaction
credits, sequence reservation, deadline or START readiness. A future caller must
complete these distinct admissions before passing an ordinary request to the
existing HIF core. This packet does not bypass their unresolved contracts.

## Lifetime and unfinished ownership binding

The caller must retain input bytes immutable from prepare through every view and
use, serialize prepare/describe/admit/get/invalidate, and keep context, input and
output storage distinct. Treat context fields as private except the accounting
summary. Discard all old views before reprepare, invalidation or freeing bytes.
The C API does not detect caller mutation, concurrency or forged internal fields;
it is not a security boundary against its own caller. Unlike the Python model,
it does not make an input copy. An eventual firmware owner must supply the stable
owned buffer, for example a retained firmware object with a reviewed lifetime.

The unfinished mixed-image binding must attach a real exclusive shared EMI/AP-DMA
resource owner to this exact plan and attempt, validate every EMI span against
that owner before any ordinary transfer, and retain reservation, mapping,
protection/remap and DMA exclusion through copying, visibility, sealing, START
and firmware lifetime/recovery. Ownership loss or uncertain effects must poison
the attempt; a generic memory free or runtime-PM return is no release witness.
Per-section and START execution must reuse existing transaction contracts. The
separate owner proposal owns these unresolved hardware effects. There is no fake
lease or assumed reset/quiescence witness in this plan.

## Offline evidence

Run `python3 experiments/2026-09-05-mt6797-whole-image-plan/scripts/verify.py`
from the repository root. It verifies pinned reused sources, generates/replays
[one logical patch](0003-wifi-mediatek-prevalidate-image-plan.patch), runs host
fixtures and records full strict checkpatch output in
[validation.json](validation.json). Temporary state is scoped, locked and cleaned.

Differential tests compare construction and every descriptive section against
the existing Python WholeImage model without calling its step or START. They
passed 2,360 inputs: 739 valid plans, 1,621 refusals and 34,828 section descriptions.
The suite includes all counts 1 through 256, truncations and deterministic
mutations with stale/recomputed CRCs. Valid mixed images retain all descriptions
but expose zero executable views. Ordinary-only payload views match the model.
The differential claim covers planning only, not equivalence to the Python lease
acquisition or runtime executor.

Strict C11, warnings-as-errors, AddressSanitizer and UndefinedBehaviorSanitizer
passed 280 exact-allocation count/short-input cases plus explicit null, reserved
and invalidation checks. The final section is deliberately malformed, including
later EMI entries, and the whole plan and first executable view are refused.
No hardware callback exists in the C implementation. Parser structural coverage
and HIF scalar/deadline failure coverage remain in their existing experiments.

Strict checkpatch has no source findings. Its missing DCO error and generic
MAINTAINERS warning remain unfiltered: the synthetic experiment author makes no
certification and this patch is not ready for upstream submission. No kernel
compile or hardware test has been run for this new delta.

## Future kernel integration

[proposal.json](proposal.json) specifies the exact three-file kernel delta and
future emitted-object expectations. Append this patch after the existing parser
patch in the shared provider series; no config change is needed. The coordinator
alone edits canonical series and manifest, audits all consumers, computes the
new clean revision/source/config identities and serializes the managed source
refresh. Reuse the existing source path, with no duplicate Linux checkout.

An admitted explicit Buildbox build must retain the earlier HIF/parser/CRC
acceptance and additionally prove the exact image-plan source hashes, .cmd kernel
compilation, AArch64 nonzero FUNC definitions for all five public APIs, references
to mtke_parse/mtke_get, private archive membership and matching vmlinux/System.map
definitions. Scope no-registration/no-initcall/no-export checks to the private
objects. A successful build would prove compilation/linkage only; mixed-image
execution remains refused until the real owner and complete executor are reviewed.
