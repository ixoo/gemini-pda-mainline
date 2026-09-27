# MT6797 shared CONSYS reservation owner

The first production owner slice binds an existing boot reservation in
`drivers/soc/mediatek`, outside the WLAN image parser. The initial
`mt6797-a53-consys-owner-compile` profile selects it without an active manager
DT node, child population, CONN transition, remap write, EMI secure call,
firmware load, radio operation or device candidate. The later passive profile
adds a manager DT node without activating those effects.

The driver requires one boot-allocated `memory-region` directly under
`/reserved-memory`, with the MT6797 CONSYS compatible, `no-map`, no reusable or
DMA-pool treatment, no region callback, at least 1 MiB, a 1 MiB-aligned base
and an addressable first MiB below 4 GiB. It compares the initialized
reserved-memory descriptor to the consumer resource view and rejects overlap
with other initialized reservations. The later [binding correction](../../patches/proposals/0021-soc-mediatek-bind-existing-no-map-CONSYS-reserve.patch)
requires the first MiB to be covered by ARM64's existing busy, non-System-RAM
boot resource. A duplicate manager refuses. The boot reservation already
excludes ordinary competing resource requests; the owner's binding is
permanent and cannot be freed by consumer devres cleanup.

This is Linux resource exclusion, not a physical or firmware handoff. The
binding cannot exclude retained firmware, secure world or another bus master,
and it does not make the current private image binding active. The next owner
slices must add serialized shared remap, attributable rail/reset and CONN
power ordering, EMI policy/visibility, retained failure state and a staged
child before an effect-bearing Wi-Fi boot. The [v8 last-client trace](../2026-09-26-gemian-wifi-reference/results/trace-shared-off-v8-1.json)
supports the vendor reference off/on branch but does not supply those grants.

The initial two internal format patches are [the binding](../../patches/proposals/0017-dt-bindings-soc-add-MT6797-CONSYS-owner.patch)
and [the owner](../../patches/proposals/0018-soc-mediatek-claim-MT6797-CONSYS-reserve.patch).
They were exported from a narrow synthetic snapshot of the prepared Linux
7.1.3 Kconfig/Makefile inputs; their parent hashes are not upstream commits.
The synthetic patch author is not a DCO sign-off or upstream submission.
The selected series is a canonical-order extension of the accepted A53 Wi-Fi
core integration series.

Compile hypothesis: both patches apply to the pinned source and the owner
links into the A53 integration image, while all Gemini DTBs remain unchanged.
A failed patch, Kconfig resolution, binding check, C compile/link or DTB
comparison refuses this slice. A successful build proves no device behavior;
it must not be installed on boot2.

The [initial validated Buildbox package](results/build.json) from the exact clean
`d5617ec3` input links `mt6797_consys_probe` with the selected option. The
focused binding/example check passed without diagnostics using dtschema 2026.9,
and all five Gemini DTBs match the preceding focused A53 Wi-Fi build byte for
byte. No device action was taken; this still is not a boot2 candidate.

## Four-byte shared remap claim

The [binding update](../../patches/proposals/0019-dt-bindings-soc-require-MT6797-CONSYS-remap-word.patch)
and [owner update](../../patches/proposals/0020-soc-mediatek-claim-MT6797-CONSYS-remap-word.patch)
require the actual TOPCKGEN remap word at `0x10001340` as one exact
four-byte MMIO resource. The owner validates the boot reservation, then
claims/maps the remap word; another Linux remap-resource claimant or a
mismatched DT address
refuses probe. The existing topckgen clock node covers only
`0x10000000..0x10000fff`, so this is a disjoint register claim rather than a
second mapping of the clock provider's resource. There is still no remap
read/write or external-writer exclusion. The selected A53 compile profile
continues to have no active owner DT node.

The [remap-claim build](results/build-remap.json) from clean `aaa732e2`
passed full Buildbox package validation and focused dtschema 2026.9
binding/example checks. Both new patches passed checkpatch without findings.
The owner remains linked, and all five Gemini DTBs remain byte-identical to
the prior owner build. No device action was taken.

## Boot resource-tree correction

The pinned ARM64 path registers each no-map memory region as a `reserved`
resource, then `reserve_memblock_reserved_regions()` places a busy `reserved`
child over allocated boot reservations before platform probe. The dynamic
OF allocation uses `memblock_phys_alloc_range()` and marks this range no-map.
`request_mem_region()` does not descend into a busy child, so the initial
owner's additional first-MiB request would refuse its own valid reservation.
The [correction](../../patches/proposals/0021-soc-mediatek-bind-existing-no-map-CONSYS-reserve.patch)
checks that one busy non-System-RAM resource covers the verified first MiB
and retains a single owner binding instead. It does not release or alter the
boot reservation. The earlier compile receipts did not test this runtime
condition and are superseded for boot selection. No owner DT node or hardware
action has been added.

The [corrected Buildbox package](results/build-reserve-corrected.json) from
clean `6ee2850c` passed full package validation; the owner is selected and
linked, and all five Gemini DTBs match the preceding owner package byte for
byte. Patch 0021 passed checkpatch without findings. The binding YAML did not
change after its clean dtschema 2026.9 check. No device action was taken; this
remains a compile-only owner foundation, not a boot2 candidate.

## Dynamic allocation correction and passive binding candidate

The first owner probe checked a static `reg` property and used
`of_address_to_resource()` on its target. Gemini's boot-allocated reservation
has `size`, `alignment` and `alloc-ranges`, but no `reg`; the first active
binding would therefore refuse before reaching the resource-tree check. The
[dynamic correction](../../patches/proposals/0023-soc-mediatek-resolve-dynamic-CONSYS-reservation.patch)
requires that dynamic form and compares the initialized `reserved_mem` with
`of_reserved_mem_region_to_resource()`. It retains the busy boot-resource
check and refuses a static replacement. Earlier compile receipts do not
validate this active probe path and are superseded for boot selection.

The isolated `mt6797-a53-consys-owner-passive` profile adds [one DTS
patch](../../patches/proposals/0022-arm64-dts-mediatek-bind-passive-Gemini-CONSYS-owner.patch)
to the corrected owner series. It labels the existing dynamic no-map CONSYS
reservation and gives the shared owner its exact four-byte remap resource.
There is no power-domain attachment, child, remap read/write, rail vote,
reset, EMI operation, firmware request or radio operation. The original
compile profile and its DTBs stay unchanged.

The device hypothesis is that the corrected probe can bind the initialized
boot reservation and claim the disjoint remap resource in a mainline boot.
The unique observation is one `mt6797-consys` bound record joined to the
exact boot identity and reservation placement; a missing record, probe error
or boot regression redirects resource/DT diagnosis before any active owner
work.

The first passive build from `52637bb2` linked successfully but still had
the static-`reg` probe error described above. It was never made a boot2
candidate. The [corrected Buildbox package](results/build-passive.json) from
clean pushed `60b8972b` passed full inventory validation. The owner is linked,
and the built Gemini tree has the exact four-byte remap resource and a phandle
to the dynamic reservation. All five Gemini DTBs stayed byte-identical to the
earlier passive build because the correction changed only C. The new DTS and
driver patches passed checkpatch without findings; the focused binding YAML
passed `dt-doc-validate`. No device action occurred during those builds.

The [exact candidate recipe](build-passive-candidate.py) checked that package,
the accepted A53 RAM parent and its 47-member archive. It changed only the
init release gate, added one passive owner DT node and one phandle to the
existing reservation, validated the LK Android-v0 container and padded it to
16 MiB. The [sanitized candidate receipt](results/passive-candidate.json)
records boot image SHA-256 `38ebcb1c…b54eb69` and full boot2 SHA-256
`251449ff…2a29a`; the image and private authentication keys remain ignored.
The [installer adapter](install-passive.py) reuses the reviewed live-GPT
boot2 guard, exact predecessor/readback checks and clean shutdown. Its first
generated shell refused at the initial remote gate because the inherited
baseline required release `3.18.41+`, while this verified Gemian boot runs
`3.18.41-gemini-wifi-ref8+`. That refusal occurred before an evidence
directory, write or shutdown; the same Gemian boot and WLAN carrier remained.
The adapter now pins that exact v8 release as well as the boot ID, and the
replacement shell passed offline preparation, syntax and ShellCheck. The
[session binding](passive-session.py) passed offline candidate
validation. The [host runner](passive-host.py) uses the established bounded
authenticated USB collection and reviewed Gemian return path after an owner
selection. The unique on-device result remains the owner bind record in an
authenticated complete log; an absent record or probe error is a negative
result, not a reason to repeat the same image.
