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
reserved-memory descriptor to both OF resource views, rejects overlap with
other initialized reservations, and claims the first MiB through the kernel
resource tree. A duplicate manager or competing claim refuses. The claim is
permanent in this built-in driver; no consumer devres cleanup can free it.

This is Linux resource exclusion, not a physical or firmware handoff. The
claim cannot exclude retained firmware, secure world or another bus master,
and it does not make the current private image binding active. The next owner
slices must add serialized shared remap, attributable rail/reset and CONN
power ordering, EMI policy/visibility, retained failure state and a staged
child before an effect-bearing Wi-Fi boot. The [v8 last-client trace](../2026-09-26-gemian-wifi-reference/results/trace-shared-off-v8-1.json)
supports the vendor reference off/on branch but does not supply those grants.

The two internal format patches are [the binding](../../patches/proposals/0017-dt-bindings-soc-add-MT6797-CONSYS-owner.patch)
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

The [validated Buildbox package](results/build.json) from the exact clean
`d5617ec3` input links `mt6797_consys_probe` with the selected option. The
focused binding/example check passed without diagnostics using dtschema 2026.9,
and all five Gemini DTBs match the preceding focused A53 Wi-Fi build byte for
byte. No device action was taken; this still is not a boot2 candidate.
