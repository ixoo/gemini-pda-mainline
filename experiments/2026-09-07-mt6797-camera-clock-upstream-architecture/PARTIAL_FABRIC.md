# SMI fabric can be scoped to an admitted consumer

## Result

The pinned upstream software does **not** require all seven MT6797 larbs to
be enabled together. This corrects the blanket dependency stated in local
patch 0025's commit message. It removes an assumed dependency on unrelated
CAM/MJC clock providers when assessing a first consumer on another larb.
It does not establish that partial fabric operation is safe on this hardware.

This is a bounded follow-up to the requested 0023–0025 consumer review, not
completion of that review. No consumer, binding, driver or device candidate is
admitted. In particular, the unresolved display and camera resource contracts
are unchanged.

## Source identity

The comparison uses manifest-pinned upstream commit
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`, rather than claiming current HEAD.
The complete retained source archive was SHA-256 verified as
`45590c057805bc9cf7281ce04d5dbde5316b7c8b017998cafac301f67e92682d` on Buildbox.
Both inspected files in the prepared clock-allocation source matched their
archive members byte for byte. No source tree was transferred or modified.

| Upstream path | SHA-256 |
| --- | --- |
| `drivers/iommu/mtk_iommu.c` | `9d2e5aa4806e7291df179cad50fe58aaf75e0cb5c92eae7eca63ecb3e33888e0` |
| `drivers/memory/mtk-smi.c` | `6425b65c76b78b527faa3c1526f3282767ce44257b77a4936b32284d92e0ed8f` |

Local patch 0024 SHA-256 is
`86ae3fa90ee32167d53a1327b4ab4efa7d5c29d2639ef8ba661200da89ad1abc`;
patch 0025 SHA-256 is
`393c62c4d8e28aa5fa71c04a3730aedd422a3eaad4aa320588395280c603b787`.
Their historical bytes, certifications and runtime claims are unchanged.

## What the code actually requires

In `mtk_iommu_mm_dts_parse()` at lines 1170–1289, a disabled larb is skipped
before platform-device lookup, driver readiness checks or component matching.
At least one available larb must supply a common SMI node; all participating
larbs must resolve to the same common device. An available larb with no bound
driver causes probe deferral. The common device receives a runtime-PM link to
the IOMMU.

Larb numbering must survive any subset. The parser uses `mediatek,larb-id`
when present and otherwise the original phandle-list index. Patch 0025 lists
larb0 through larb6 in order. Leaving entries disabled preserves those indices;
compacting the list would renumber entries unless an independently validated
explicit-ID description replaces that convention. This is a parser fact, not
validation of a new binding or DT.

`mtk_iommu_probe_device()` at lines 874–925 links the actual DMA consumer to
its referenced larb. A missing larb device is rejected. Without
`DL_WITH_MULTI_LARB`, multiple port IDs on different larbs are rejected;
patch 0024 does not set that flag. A proposed multi-larb consumer therefore
needs its own review, rather than assuming the subset result solves it.

In `mtk-smi.c`, component binding at lines 164–178 joins the larb to the
IOMMU's device-indexed array. Common-device lookup and runtime-PM linking at
lines 584–623 precede component registration. Probe at lines 644–681 obtains
that larb's clocks and enables runtime PM; resume/suspend at lines 694–729
operate its clock set and port configuration. These inspected paths do not
request every other larb's clocks. The resulting dependency chain is consumer
to participating larb, larb to common, and common to IOMMU, with the declared
power domains still required.

## Consequence and remaining work

Assess a first real consumer with its complete participating-larb set and
shared common/IOMMU resources. Do not require unrelated camera or MJC clock
work merely because the historical DT enumerates all seven larbs. Conversely,
do not infer safe hardware isolation, retained-firmware handoff, correct port
translation, common bus routing or suspend/unbind behavior from software's
ability to skip a disabled node.

The full 0023–0025 review still needs binding applicability, platform flags,
port/domain mapping and a concrete consumer's ownership and teardown contract.
The clock slot-count correction is already tracked by the separate
[allocation experiment](../2026-09-08-mt6797-clock-id-allocation/README.md).
No kernel input changed, so no build or hardware test was performed. Validation
here consists of archive/file identity checks and direct call-path inspection;
repository checks cover publication.
