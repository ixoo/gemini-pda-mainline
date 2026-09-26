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

## Accepted A53 source integration gate

The seven provider proposals in `patches/series-mt6797-provider-compile`
were replayed in canonical order against the exact prepared Linux 7.1.3 source
for `mt6797-a53-service-facilities`. Each `git apply --check` and apply
succeeded without an edit or conflict. The source-state and integrity markers
were `d6b5f84c94d546466c5c8d9afb003f2a12b99e26ca30c998933cb920`
and `a00f12af87ce6b49cb20eb71659d5415c508f48cae9b22a1fbf720258579801d`;
the preimage `mtk-scpsys.c` SHA-256 was
`cc913ca5cc4e652a49c6cf4822131328fda41ce9fa3719f0279b77ccbd28ada6`.
This establishes source-level portability onto the accepted boot foundation,
not a kernel build or device result for that combined profile.

The accepted A53 configuration explicitly has `# CONFIG_MTK_SCPSYS is not set`.
Enabling the legacy provider would register every described MT6797 domain;
`scpsys_register_domain()` calls `power_on()` for each domain without
`MTK_SCPD_KEEP_DEFAULT_OFF`. The proposals select that cap only for CONN.
Consequently a naive A53 profile enabling SCPSYS would introduce probe-time
power transitions for unrelated domains. The next boot candidate must first
define and validate the registration/consumer behavior of those domains as
well as the CONN rail, reset and shared-writer owner. No such profile was made
or installed. The running Gemian Wi-Fi reference was inspected read-only and
was not changed by this source replay.

## Child-domain provider comparison

The exact prepared Linux 7.1.3 A53 source also contains
`drivers/pmdomain/mediatek/mtk-pm-domains.c` (SHA-256
`d9a2fc3d875ec737a01234109115db9d39779b64597c2888d6db631970184f3b`)
and `mtk-pm-domains.h` (SHA-256
`52f4d9b0780a4c4bf236e48ab8b513803865e636e91eb6507f3915e63715a5ab`).
Unlike the legacy provider, `scpsys_probe()` calls `scpsys_add_one_domain()`
only for available DT child nodes. Describing a CONN child alone can therefore
avoid probe-time registration and power requests for unrelated MT6797 domains.
The accepted DT instead has a legacy flat `mediatek,mt6797-scpsys` node, and
the accepted A53 config disables both SCPSYS drivers; this is a migration
direction, not a drop-in profile switch.

The newer driver's existing `MTK_SCPD_KEEP_DEFAULT_OFF` branch merely warns
if `scpsys_domain_is_on()` reports ON, then calls `pm_genpd_init(..., true)`
anyway. That status helper ignores both `regmap_read()` return values and
collapses mixed dual-status bits into OFF. A CONN domain must instead refuse
ON, mixed or unreadable status before publication, as the legacy proposal
already does. The newer ON callback also releases basic clocks and its
optional supply after an ACK or later preparation error without proving OFF;
its subsequent cleanup may issue further bus-protection or SRAM operations.
It has no matching retained-fault query, MT6797 `0x32c` CONN data, selected
SPM key preamble, or external VCN/reset sequence. The generic `SPM_CONN_PWR_CON`
constant is `0x280`, which is not the selected MT6797 CONN offset.

Accordingly, porting only the CONN table entry to this provider would avoid
unrelated probe effects but would not admit activation. A useful migration
must first make initially-off admission and post-request failure retention
fail closed, then add MT6797 data and child DT, the rail/reset/key owner and
the retained-writer and EMI contract. Preserve the accepted baseline until
that complete effect-bearing path has a reviewable failure lifetime. This
comparison was read-only on Buildbox; it made no build, device or radio change.
