# Draft inquiry: MT6797 infracfg reset and clock probe ordering

Status: **draft only; not sent**. This asks for an integration decision, not
review or acceptance of the unsigned reset patches. The actual sender must
review the final recipients and wording before contact. No DCO sign-off or
authorship claim belongs on this inquiry.

The [revised reset topic](revised-topic/INTEGRATION.md) has six logical
changes. Its provider patch registers resets before clocks in the current
private `mtk_infrasys_init()` path. Akari Tsuyukusa's public
[MT6797 conversion, patch 18/32](https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111265.html)
removes that function and supplies the common descriptor/probe path. The
[September 25 footprint check](results/upstream-ordering-refresh-20260925.json)
found neither conversion nor reset topic in the inspected mainline, clock-next
or MediaTek for-next MT6797 driver bytes. That limited tree check cannot settle
unmerged review or maintainer preference. This draft targets the precise
ordering question without presenting the local series as submission-ready.

Suggested routing for review before sending: `linux-clk@vger.kernel.org` and
`linux-mediatek@lists.infradead.org`; copy Akari Tsuyukusa and the relevant
clock/MediaTek maintainers from the then-current `MAINTAINERS` and
`scripts/get_maintainer.pl` result. The older
[routing snapshot](results/maintainer-routing.json) is a starting point, not a
frozen recipient list.

## Draft body

Subject: Question: MT6797 infracfg reset support versus clock-probe conversion

The Gemini PDA mainline project is preparing MT6797 infracfg reset support
for the two source-backed lines used by thermal and PMIC wrapper. The small
series also bounds the generic SET/CLEAR reset-bank translation. It has not
been submitted: final authorship,
DCO certification and current-base validation remain open.

The current provider change registers its reset descriptor before clocks in
`mtk_infrasys_init()`. Akari's [patch 18/32][conversion] replaces that private
probe with the MediaTek common descriptor/probe path. Which ordering would you
prefer for review: submit reset support against the current private probe and
have the conversion preserve it, or wait for the conversion and adapt the
reset descriptor to its accepted base?

If the conversion should come first, we would use its `rst_desc` hook. Our
source audit also found that the current common helper publishes the clock
provider before reset registration, then frees the clock data on failure
without first removing the published provider. We would treat that unwind as a
separate prerequisite fix, reviewed against the exact accepted conversion.

The [local revised-topic record][topic] describes the two reset mappings,
optional old-DT binding compatibility, bounded tests and the proposed split.
We are asking only for ordering guidance at this stage.

[conversion]: https://lists.infradead.org/pipermail/linux-mediatek/2026-August/111265.html
[topic]: https://github.com/ixoo/gemini-pda-mainline/tree/9f0d8170477c742f907eca6b81f951464c994ce9/experiments/2026-09-05-mt6797-infracfg-upstream-preparation/revised-topic
