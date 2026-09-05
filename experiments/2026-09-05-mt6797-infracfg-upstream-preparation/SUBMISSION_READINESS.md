# Unsigned infracfg submission readiness packet

**Not ready to send.** The exact six-patch topic has useful build, test and schema
evidence, but patch 3 should preserve old-DT schema compatibility, patch 4 overlaps
an unmerged MT6797 probe conversion, and the actual authors must resolve DCO
certification. No email, maintainer acknowledgement, new validation execution or
patch/profile change is implied by this packet.

## Target and recipients

The [routing snapshot](results/submission-routing-snapshot.json) records current
advertised refs, immutable primary-source URLs, file hashes and all six actual
patch digests. Mainline still points to tested base
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c`. Relevant branch tips observed were:

| Tree | Branch | Commit | Proposed use |
| --- | --- | --- | --- |
| [Clock](https://git.kernel.org/pub/scm/linux/kernel/git/clk/linux.git/) | `clk-next` | `91b1b8d437abe0cd83210d8f257b785a63047aa9` | driver, tests and reset-header topic, with DT/reset review |
| [MediaTek](https://git.kernel.org/pub/scm/linux/kernel/git/mediatek/linux.git/) | `for-next` | `f5be25e697e0362103625b1b197af126ae4ba5f7` | separately routed SoC DTS declaration |

Current clock/mainline maintainer sections agree with the earlier actual-patch
[get_maintainer result](results/maintainer-routing.json). The MediaTek branch has
older clock-maintainer metadata; do not prefer those stale contacts over the
clock tree's current entries. Public review recipients are:

| Topic patches | Maintainers / reviewers | Lists |
| --- | --- | --- |
| 1, 2, 4, 5: reset implementation and tests under `drivers/clk/mediatek/` | Stephen Boyd `sboyd@kernel.org`, Brian Masney `bmasney+clk@redhat.com`, Jerome Brunet `jbrunet+clk@baylibre.com`; Matthias Brugger `matthias.bgg@gmail.com`, AngeloGioacchino Del Regno `angelogioacchino.delregno@collabora.com` | `linux-clk@vger.kernel.org`, `linux-mediatek@lists.infradead.org`, `linux-arm-kernel@lists.infradead.org`, `linux-kernel@vger.kernel.org` |
| 3: binding/header | Clock and MediaTek reviewers above; Rob Herring `robh@kernel.org`, Krzysztof Kozlowski `krzk+dt@kernel.org`, Conor Dooley `conor+dt@kernel.org`, Philipp Zabel `p.zabel@pengutronix.de` | Above lists plus `devicetree@vger.kernel.org` |
| 6: `arch/arm64/boot/dts/mediatek/mt6797.dtsi` | MediaTek and DT maintainers above | MediaTek, ARM, DT and kernel lists |

This is a reviewed recipient proposal, not a send list or merge agreement.
Retain MediaTek reviewers for generic patches 1/2, which path-only discovery
misses. Do not add unrelated keyword-derived recipients. Review the final
regenerated patches again before any authorized submission.

Patch 6 adds only the standard `#reset-cells` property. It includes no new reset
header and adds no consumer phandle. Contrary to the earlier generic routing
note, this exact DTS patch has no compile-time dependency on the new header and
needs no immutable header branch solely to compile. Coordinate semantic ordering
with maintainers; future reset consumers depend on the provider and public IDs.

## Concrete overlapping work

The [August 3 MT6797 common-helper conversion](https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111265.html)
by Akari Tsuyukusa is patch 18 of a
[32-patch clock conversion topic](https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111247.html).
It removes `mtk_infrasys_init()` and the early infracfg provider, introduces an
`infracfg_desc`, and switches to common probe/remove helpers and a tristate
configuration. Our patch 4 inserts reset registration into the removed function.
The conflict is therefore concrete, not merely a similar subject line.

It is absent from the inspected mainline/clock-next MT6797 file bytes. Other
selected implementation/schema/DTS files also match the tested base; the sole
clock Kconfig difference adds an OF dependency to MT8173 mfgtop, away from our
hunks. The five new topic file paths return HTTP 404 at both inspected commits.
This selected-file comparison does not establish full-tree ancestry or prove
that a rebase has been tested.

The official August/September MediaTek thread indexes, the conversion patch and
cover replies were inspected. The inspected replies discuss recipient selection,
not acceptance of the MT6797 conversion. Lore's direct query returned 403; the
bounded archive review cannot exclude newer versions, other lists or unpublished
work. Link the conversion when requesting ordering from the clock maintainers
and its author; no such message has been sent.

If the conversion lands first, retain our reset descriptor/header and use the
existing common-helper `rst_desc` hook in its new infracfg descriptor. Do not
reintroduce the removed private probe or import the entire conversion topic.
The pinned [common helper](https://raw.githubusercontent.com/torvalds/linux/4d7d9486c04d917265f64c55bd23b2cc4fe7749c/drivers/clk/mediatek/clk-mtk.c)
registers resets after clock publication; that differs from our current fail-early
ordering. Audit the then-current unwind, devres and remove paths before adopting
that minimal hook. Existing failure-path conclusions cannot be transferred
unchanged to a reordered provider.

The minimum post-conversion provider footprint is the existing reset-header
include and `.rst_desc = &infra_rst_desc` in `infracfg_desc`; retain the tested
private descriptor and public IDs. Replace the current explicit registration
call/error return with that hook only after the conversion's exact base is
selected. Its module/early-clock changes belong to the conversion, not this
reset topic.

There is a concrete prerequisite to that adaptation. In both the tested base
and inspected clock-next `clk-mtk.c`, reset registration occurs after
`of_clk_add_hw_provider()`. On reset-registration error it jumps to
`unregister_clks`, ultimately freeing `clk_data`, without calling
`of_clk_del_provider()` on that path. Normal remove does call it. This is a
source-level stale-provider risk, not a fault-injection or hardware result.
The [snapshot](results/submission-routing-snapshot.json) pins the exact helper;
our current patch 4 avoids this new ordering by registering resets first.

If adopting the common path, propose a narrowly scoped cleanup fix: on the
post-publication reset-registration error, remove that published clock provider
before unregistering/freeing clocks. Do not remove a provider when clock
publication itself failed. Review whether driver data needs clearing on that
specific source. Fault-injection fixtures should distinguish reset failure after
publication, publication failure, success and normal removal, and verify cleanup
ordering and no remaining provider lookup. These tests and the correction are
proposals only; neither the common helper nor the six patches is modified here.

The concrete ordering choices are therefore: keep the current probe topic first
and have the later conversion preserve its reset capability; or wait for the
conversion, resolve the common-helper cleanup prerequisite and regenerate only
the required reset integration. Maintainers must choose the order. A third,
silent import of the whole 32-patch conversion would exceed this topic's scope.

## Smallest binding compatibility correction

The current schema already permits optional `#reset-cells` with value 1. Patch 3
adds MT6797 to the separate conditional *required* list. Thus it rejects an old
valid MT6797 node merely because that new property is absent. Patch 6 updates
in-tree DTS, but cannot update already distributed DT sources or blobs.

For the next generated topic, omit only patch 3's schema hunk. Keep its two-ID
header and patch 6 unchanged. Relative to the currently patched schema, the
proposed delta removes this one entry from the `if` enum:

```diff
           - mediatek,mt6795-infracfg
-          - mediatek,mt6797-infracfg
           - mediatek,mt7622-infracfg
```

Do not remove MT6797 from `properties.compatible`, alter the shared optional
property definition, change the compatible or renumber the two public IDs.
This preserves both old nodes and new explicit reset providers. It follows the
[kernel DT ABI guidance](https://cdn.kernel.org/doc/html/latest/devicetree/bindings/ABI.html)
to augment bindings while retaining old descriptions; schema rejection and
runtime breakage remain distinct claims.

Source review finds no property-presence check required by reset registration,
and old upstream MT6797 nodes have no reset consumers. This supports, but does
not hardware-test, old-DTB compatibility. Registration adds allocation/error
paths; no claim is made that all old failure outcomes are unchanged.

Proposed validation for that exact regenerated revision, **not run here**:

- Old MT6797 node without `#reset-cells` and new node with value 1 both validate;
  values 0 and 2, malformed cells and unrelated properties still reject.
- Existing compatibles whose schema already requires reset cells still reject
  omission. Keep unrelated schema branches byte-identical.
- Both MT6797 DTBs retain one reset cell; compare generated C/header/config/image
  identities to isolate a schema-only correction before deciding needed rebuilds.
- Preserve generic invalid-index/bank and MT6797 public-ID 0/1 versus 2/64 tests.
  If the provider is rebased onto common helpers, separately test failure unwind
  and registration order on that exact source; no physical session is selected.

## Evidence that may be stated

| Claim | Exact evidence | Limit |
| --- | --- | --- |
| Source and build | [Build receipt](BUILD_ADMISSION.md), build revision `4ec63076aeb6388ba24b33ee20afcf19ced541e1` | Exact current six patches; not the proposed binding correction or future rebase |
| Reset arithmetic | [QEMU attempt 1](VALIDATION_ATTEMPT_1.md): intended eight cases reported pass; extra upstream four-case suite also passed | Original two-suite gate refused; no provider/MMIO/lifetime test and no new `Tested-by` |
| Binding/DT validation | [Schema attempt 2](SCHEMA_ATTEMPT_2.md), exact `f4ff1028` collector, unchanged source/build and empty diagnostics | Complete collection accepted by the integration owner; original review-required receipt retained; no old-DT compatibility fixture |
| Provider errors/lifetime | [Source review](PROVIDER_FAILURE_REVIEW.md) pins current provider and core cleanup chain | No allocation fault injection, concurrent unregister or whole-driver rebind test |
| Physical reset mapping | [PWRAP serviceability](../2026-09-04-mt6797-pwrap-reset-serviceability/README.md), [thermal V4 observation](../2026-09-04-mt6797-thermal-snapshot/results/v4-runtime-pass.txt) | Different integrated local revisions and consumers; supporting mapping evidence, not hardware validation of this upstream topic |

The topic deliberately adds no PWRAP/thermal consumer wiring. Their historical
success does not certify this exact six-patch revision, and no hardware
`Tested-by` may be invented or carried forward automatically.

## Author and DCO decisions before sending

All six current review patches use an explicitly synthetic, unsigned experiment
identity. Historical 0001–0003 contain named metadata; later repair/test patches
and the regeneration add substantive changes. A historical sign-off does not
certify the new combined work.

For patches 1/2 and 4/5, identify the actual author(s) of the corrected helper,
descriptor, provider integration and tests, and review their derivation from the
repair work. For patch 3, review the two-ID header and the proposed optionality
change separately from the superseded historical reset definitions. For patch 6,
confirm the author and certification of the retained DTS declaration. Each real
contributor must decide what they can truthfully certify under the
[kernel submission process](https://docs.kernel.org/process/submitting-patches.html#sign-your-work-the-developer-s-certificate-of-origin).
Do not mechanically replace `From`, copy old sign-offs or invent co-author,
reviewed or tested trailers. No final author identity is selected here.

[The unsigned cover text](UNSIGNED_COVER_LETTER.md) is ready for review after
these decisions and technical ordering are resolved. Main manifest/series and
all original patch/evidence bytes remain unchanged by this packet.
