# MT6797 shared CONSYS reservation owner

The first production owner slice establishes a boot reservation claim in
`drivers/soc/mediatek`, outside the WLAN image parser. It is selected only by
the `mt6797-a53-consys-owner-compile` profile. There is no active manager DT
node, child population, CONN transition, remap write, EMI secure call, firmware
load, radio operation or device candidate in this profile.

The driver requires one boot-allocated `memory-region` directly under
`/reserved-memory`, with the MT6797 CONSYS compatible, `no-map`, no reusable or
DMA-pool treatment, no region callback, at least 1 MiB, a 1 MiB-aligned base
and an addressable first MiB below 4 GiB. It compares the initialized
reserved-memory descriptor to both OF resource views and rejects overlap
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
