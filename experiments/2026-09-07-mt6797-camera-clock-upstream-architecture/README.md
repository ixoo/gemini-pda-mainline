# MT6797 camera-clock current-upstream architecture

## Decision

The [partial-fabric follow-up](PARTIAL_FABRIC.md) corrects one historical
dependency: the pinned IOMMU parser skips disabled larbs, so an initial consumer
does not acquire a software requirement to enable all seven together. This
does not resolve the consumer or hardware-lifetime stop below. The independent
clock slot-count fix is complete at its compile-only boundary.

No clock topic is admitted from local patches 0021/0022 yet. Current mainline,
clock `clk-next`, and MediaTek `for-next` contain neither the MT6797 CAMSYS/MJCSYS
clock IDs and providers nor an MT6797 DTS node that instantiates them. Current
mainline also has no MT6797 SMI/IOMMU match or MediaTek camera capture/SENINF
driver. The existing MT6797 ISP and MJC power domains use only their basic
domain state and do not consume the proposed leaf gates. Provider compilation
and schema feasibility therefore would not supply the real consumer story
required by the work contract.

CAM and MJC are separable future topics, not one camera patch set. CAM gates
could eventually serve a proved camera/larb2 path. MJC is a different
fixed-function block and has no camera consumer in the inspected current tree.
Do not carry its compatible, IDs, Kconfig option or driver merely because the
local patches combine them.

There is also an unresolved provider-index contract. Patch 0021 numbers CAM
IDs 1–7 with `CLK_CAM_NR` 8 and MJC IDs 1–6 with `CLK_MJC_NR` 7, while patch
0022 gives each `mtk_clk_desc.num_clks` the smaller `ARRAY_SIZE()` value. The
current `mtk_clk_simple_probe()` allocates that many provider slots and
`mtk_clk_register_gates()` indexes them by `gate->id`; the largest local ID is
therefore equal to, rather than below, the allocated count. Current
`clk-mt6797-img.c` has the same one-based-ID/`ARRAY_SIZE()` shape. That is
evidence of the same static risk, not a safe precedent and not proof of a
runtime failure.

The required next discriminator is a separately scoped current-upstream review
of local patches 0023–0025 for the MT6797 SMI/IOMMU/DTS consumer boundary,
together with an independently resolved clock-ID/provider-slot contract. This
item did not inspect or disposition those patches. Until both prerequisites
produce an exact consumer, resource lifetime and validation chain, keep 0021
and 0022 local and admit neither CAM nor MJC upstream work.

## Source and provenance boundary

The public-current source pin is Torvalds commit
`28924df2a08f440c73991b83028032c901de2ae4`. Clock `clk-next` is pinned at
`91b1b8d437abe0cd83210d8f257b785a63047aa9`, and MediaTek `for-next` at
`f5be25e697e0362103625b1b197af126ae4ba5f7`. Exact source paths, sizes,
SHA-256 values and negative lookups are in
[`results/source-review.json`](results/source-review.json). No Linux tree was
cloned or retained.

The frozen local inputs match their contract:

| Input | SHA-256 |
| --- | --- |
| patch 0021 | `df7b724bfdd38301416a4e0474338a9f7ef8fbde882d3e27a39c22b7f12c8f05` |
| patch 0022 | `03dfe99596f00f1c406c36da968b9d53de2368008c26c8caebc62cb9a28eee26` |
| July camera README | `050017875b353d95073f0e84e4aea6aa93e93d3fd6d193d2dfe89479899b6e08` |
| July mainline design | `bc53b7c292fd556395d8a9750776c30cde98252841ba5d1f3592108334f4dfca` |
| July pipeline contract | `ac7452eaa33f71474b23cbecd3a28d191dcc4d42c485fa052f71c6f457ede9d1` |

July's statements that Linux 7.1.3 supplied CAMSYS clocks and camera/larb
nodes describe the project's locally patched 7.1.3 package. Official stable
v7.1.3 at `199c9959d3a9b53f346c221757fc7ac507fbac50` omits the CAM/MJC IDs,
providers and DTS nodes, as does pinned current mainline. This is provenance,
not an upstream removal or regression. The July runtime and source observations
remain historical evidence for that exact local package and vendor graph; none
of its linked private captures or vendor sources was opened here.

Bounded exact-string public searches found no MT6797 CAMSYS/MJCSYS clock
submission. This negative result is not an exhaustive statement about all
public discussion.

## Current dependency map

```text
current topckgen
  +-- mm_sel       (present)
  +-- camtg_sel    (present)
  `-- mjc_sel      (present)

proposed CAMSYS provider (0021/0022, absent upstream)
  +-- CAMSYS/SENINF/CAMTG/CAMSV0..2 gates
  `-- LARB2 gate
        `-- future MT6797 SMI/IOMMU + larb2 consumer (not current)

current IMGSYS provider
  `-- LARB6/DIP/DPE/FDVT gates
        `-- frozen vendor camera graph only; no current MT6797 capture consumer

proposed MJCSYS provider (0021/0022, absent upstream)
  +-- MJC engine gates
  `-- MJC larb/asif gates
        `-- future MJC/larb4 consumer (not current and not a camera topic)

current MT6797 power domains
  +-- ISP (CLK_NONE; no proposed leaf-gate consumer)
  `-- MJC (CLK_NONE; no proposed leaf-gate consumer)
```

The three proposed parent names exist in current `clk-mt6797.c`, so parent-name
absence is not the stop. The stop is the missing provider-slot contract and
missing downstream ownership chain. A DT clock-controller node is provider
instantiation, not by itself a functional consumer. Likewise, a power-domain
entry that names no CAM/MJC gate does not validate those gates.

The frozen camera pipeline says a vendor ISP transaction used CAMSYS and
IMGSYS clocks with larb2/larb6 DMA resources, but that monolithic private ABI
is not a current V4L2/media-controller consumer. It also records six CAMSV
register/IRQ nodes against only three CAMSV clocks and three configured M4U
ports. That unresolved count must not be hidden by registering all gates or by
inventing current camera nodes.

## Patch dispositions

### 0021 — retain locally; split and redesign only after prerequisites

The current clock syscon schema and MT6797 clock header still lack both
compatibles and both ID sets. Those additions are not superseded upstream, but
absence alone does not make the combined patch useful. A future CAM binding
topic must contain only the CAM compatible and a reviewed ID namespace. A
future MJC binding topic must be independent and wait for its own consumer.

Do not freeze the current one-based IDs until the provider-slot contract is
resolved. The resolution may require a zero-based new namespace or a reviewed
provider implementation that represents sparse/one-based IDs safely; this
review does not choose between them.

### 0022 — retain locally; no provider submission yet

The gate offsets, bit positions and parent names in the local patch remain
project evidence, and the driver resembles current MediaTek simple-gate
drivers. That resemblance establishes coding shape only. It does not establish
the consumer, power/SMI lifetime or safe provider indexing.

Any future rewrite must separate CAMSYS from MJCSYS, resolve the ID/allocation
contract, and land only with an immediate schema-checked DTS consumer whose
own subsystem contract is accepted. Compile success alone is insufficient.

The combined local patches are removable only when the targeted upstream base
contains accepted equivalents for every locally required CAM and MJC binding,
ID and provider behavior, or after they are replaced by separately ordered
local patches that retain the still-needed half. Any split or replacement must
audit every manifest-selected series against canonical order.

## Future upstream and validation route

A later CAM clock series would route through the Common Clock Framework and
Devicetree binding review, with ARM/MediaTek review for its SoC DTS consumer.
The separately scoped SMI/IOMMU prerequisite also requires the current
MediaTek SMI and IOMMU owners. MJC needs its own subsystem consumer and route;
it must not borrow the camera validation story.

Before any implementation dispatch, freeze these acceptance checks:

1. prove the exact current consumer and its clock, power-domain, SMI/IOMMU and
   removal lifetime;
2. assert every exported clock ID is strictly within the allocated provider
   slot count, including a negative boundary fixture for the highest ID;
3. run focused `dt_binding_check` for the modified clock schema and focused
   `dtbs_check` for the accepted consumer;
4. compile the separated clock provider and its actual consumer on the pinned
   upstream base, then run `scripts/checkpatch.pl --strict`; and
5. audit canonical series order if local patches are split or replaced.

These checks establish source/schema integration only. Hardware testing would
still need a named Gemini revision, exact kernel/DT/configuration, attributable
clock state, one proved camera or MJC transaction, and safe teardown. Nothing
in this record enables CAMSYS, IMGSYS, MJC, SENINF, ISP, a sensor, streaming or
DMA.

## Authorship and limitations

Both local patches use the synthetic identity `Gemini PDA Mainline Project
<noreply@example.com>` and carry a matching synthetic `Signed-off-by`. They are
not submission-ready. A future upstream rewrite must identify its actual
author and may add a DCO sign-off only when that person can truthfully certify
it. This review does not infer authorship, maintainer agreement or acceptance.

This was an offline public-source audit. It made no build, device or private
access, implementation, shared-file change, upstream contact, camera action or
hardware-support claim.

Review-ready UTC: `2026-09-07T20:47:53Z`.

Accepted UTC: `2026-09-07T20:52:42Z` on first specialist review. No topic or
implementation was admitted.
