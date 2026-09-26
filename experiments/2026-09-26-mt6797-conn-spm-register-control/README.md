# MT6797 CONN SPM transition preamble, compile-only

The selected Gemian and Planet CONN power paths write `0x0b160001` to SPM
`+0x000` before ON and OFF transitions. The retained kernel attribution
confirms those normal-world stores, while the selected mainline SCPSYS
provider has no corresponding operation. See the [key ownership analysis](../2026-09-05-mt6797-wifi-contract/SPM_KEY_ORDER.md)
and [retained-source attribution](../2026-09-05-mt6797-wifi-contract/RETAINED_SPM_ATTRIBUTION.md).

The [single logical patch](../../patches/proposals/0007-pmdomain-mediatek-enable-mt6797-conn-spm-register-control.patch)
adds an optional per-domain SPM register-control value. Only the isolated
MT6797 CONN table entry selects it. The ON callback writes the value after
successful clock acquisition and before the first power request; the OFF
callback writes it after the retained-fault check and before bus protection.
Other domains retain the previous callback path. Neither transition clears
the shared enable. The patch follows the initially-off CONN data and fault
query in canonical series order. Only three `allnoconfig` compile profiles
select this series; this patch adds no CONN DT consumer.

The [Buildbox receipt](results/build.json) pins a full kernel link from clean,
pushed commit `c1202ce4470ec62986c0e4486ffcc751ad7ed69a`. The validated
package includes the exact patch and linked SCPSYS callbacks. Pinned
Checkpatch found zero errors and warnings. The existing host callback fixture
now replays this patch and passes 10 cases and 222 checks, including key
ordering, unselected-domain behavior, no key write after an early clock
failure, and no repeated key write after a latched fault. These are source and
host results, not a device transition.

This proposal does not settle whether retained firmware can change SPM `+0`
concurrently, who owns VCN rail and independent CONMCU reset preparation, or
when a shared key write is safe on hardware. The provider fault latch remains
required after any uncertain transition. A shared CONSYS owner must serialize
those prerequisites and validate them before a first effect-bearing boot.
There was no installation, power transition, firmware load or radio action.
