# Whole-image START requires an attributable EMI owner result

The ordinary-section composition does not complete the selected MT6797
image. This audit resolves the required EMI work and identifies the concrete
missing ownership/result contract. It adds no speculative EMI writer, generic
image framework or “EMI done” Boolean. The seven existing integration headers
and their APIs are unchanged; that boundary was confirmed to the independent
compile-only kernel-adapter worker.

## Required work from the selected source

At Planet `c5b0be85017ad0c599725e8273842efdbecdd88a`, gen3
`wlanImageDividDownload` routes indices 0 and 1 to ordinary CONFIG/PDA and
every later entry to EMI. The existing retained metadata records two entries
of each kind, as already owned by [the firmware audit](FIRMWARE_FORMAT.md).
The current task did not reopen private inputs or make a hardware observation.
[Rechecked primary source identities](results/whole-image-emi-sources.json).

For each EMI entry the source requires nonzero `gConEmiPhyBase`, maps the
first 512 KiB of that reservation, and copies the entry's source bytes to
offset `destination & 0xfffff`. The offset plus length must fit 512 KiB.
These are source-byte copies, not PDA, and no CONFIG credit/ACK is used for
them. Its encryption-selector handling for the first two HIF entries must
not be extrapolated into host decryption of later EMI data.

The loader temporarily sets MPU region 18 to allow all eight domains, then
requests the restricted domain-2 policy after copying. These are observed
source policies, not approved permissions for a new provider. The concrete
SoC master/domain mapping and ownership requirements remain those in
[OWNERSHIP.md](OWNERSHIP.md) and [the DMA/EMI contract](HIF_DMA_CONTRACT.md).
WMT separately configures region 19 for the next half-MiB and clears a smaller
control/coredump mapping there. That neighboring range is not WLAN scratch.
The remap register is shared with WMT, so independent mapping/protection
writers are not an adequate ownership design.

## Source success cannot be used as a completion receipt

The range check uses 32-bit addition, and its false branch does not fail the
load. The source does not check the mapping result or protection result in
this path. Its `fgEmiDownloaded` variable is set after the last entry, but
the apparent skip condition is only a commented TODO: it is **not** an
active conditional that permits skipping EMI after a warm reload. The flag
also does not prove that the preceding copies/protection operations succeeded.

More specifically, `emi_mpu_set_region_protection` in the pinned MT6797 MPU
source (lines 1124–1136) masks/encodes permissions and region, locks, calls
`mt_emi_mpu_set_region_protection`, then returns an unchanged zero. The lower
function is declared to return `int`, but its result is discarded. Therefore
even checking that wrapper's return would not establish protection success.
This is an exact source-level error-propagation gap, not a hypothetical
requirement to time every MMIO access. It requires a provider result or
verified state, not reuse of that unconditional success value.

## Parser boundary: validation metadata is not an executable plan

The existing `parse_mtke` validates CRC, bounded source spans, destination
overflow, source/destination overlap and later-entry EMI window ranges.
It returns counts, lengths and sanitized flags. It deliberately does not
return source offsets, destination addresses, key selectors, mapped memory
or owned byte views. Thus its result cannot currently be handed directly to
an image executor. Structural validity also does not attest actual reserved
memory, permissions or the firmware session.

A future private in-memory plan can reuse those validated fields without
publishing them, but it must bind the same immutable input and every entry
to its owner operation. Inventing such a plan now would still lack a real
EMI owner to execute it. A caller-set completion flag would only conceal
that missing implementation.

## Concrete evidence/action handoff

| Missing input | Exact evidence/action needed before an EMI writer is admitted |
| --- | --- |
| Actual reservation and lifetime | The selected boot's post-loader reservation base/size, attributed to that session, plus the provider's exclusive lease of the first 512 KiB. The old reserved-memory callback records only a base, not a checked size/lifetime contract. Reuse existing attributable evidence if available; no capture is requested or performed here. |
| Protection authority and result | Resolve the selected lower `mt_emi_mpu_set_region_protection` implementation and its callable authority/failure semantics. A replacement provider must report the real result or verify the admitted protection state; the existing wrapper's zero is unusable as proof. Establish actual AP/CONSYS domain identities before choosing permissions. |
| Shared remap exclusion | Identify the single WMT/CONSYS owner and serialized field ownership for the mapping, including firmware agents, so another client cannot alter it during the copy or restriction step. This must preserve the neighboring WMT extent. |
| Copy visibility and confinement | An owner implementation must validate each immutable source range and EMI destination using subtraction-based overflow-safe bounds, use the mapping-appropriate copy/access path, and establish visibility to CONSYS before reporting completion. Ordinary CPU memcpy into an unchecked vendor mapping is not that contract. |
| Failure and release | Failed copy/protection/restoration invalidates the image session and blocks START; it must not produce a success receipt or a new retry session. Keep the provider responsible for safe resource retention/recovery instead of silently releasing shared memory. |

These are implementation inputs for the shared-resource owner, not a request
for a speculative device write. The narrow offline follow-up is attribution
of the lower MPU operation and the provider authority/error path. A later
owner session may supply missing live reservation/ownership observations,
but this task performs and schedules none.

## Whole-image eligibility after those facts are available

The eventual image owner must account for every validated entry: both
ordinary sections submitted through their successful CONFIG/PDA flows, every
required EMI copy completed by the admitted owner, and the final protection/
visibility result established for the same image and session. Invalid,
unhandled, failed or skipped EMI entries prevent START. Earlier downloads,
the vendor static flag, a CRC pass or an ordinary-section completion cannot
substitute. Only then may the existing START submission/readiness boundary
be called under its own ownership/deadline rules.

No complete-image START eligibility is implemented by this handoff because
that EMI owner/result is absent. This is the requested concrete missing
resource contract, rather than an unconnected host validator. PIO remains a
viable transport direction; this EMI obligation is independent of enabling
DMA. Host compilation success remains distinct from usable Wi-Fi.

## Coordinator review

Project Planning reviewed `0115ea4d`, independently matched all four public
source lengths/hashes, and accepted the distinction between ordinary submission
and whole-image completion. The next source investigation is already assigned
to follow the lower protection operation through its actual authority and error
semantics and compare available upstream ownership interfaces. Discarding a
return value does not itself prove that EMI support is impossible or that the
underlying operation failed. The missing provider contract must be resolved
concretely rather than converted into a permanent abstract blocker. No new
writer, runtime permission or device observation follows from this review.
