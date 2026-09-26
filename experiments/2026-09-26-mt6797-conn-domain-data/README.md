# MT6797 CONN power-domain data, compile-only

The selected Gemian clock provider describes the CONN island at SPM control
offset `0x32c`, dual power-status bit 1 and infracfg protection bits 17–18.
The existing upstream MT6797 SCPSYS table has no CONN entry. The [power-domain
contract](../2026-09-05-mt6797-wifi-contract/POWER_DOMAIN.md) records the
selected source path, including why generic offset `0x280` is wrong for this
SoC and why a bare table entry would power CONN during provider registration.

Two internal proposal patches add power-domain ID 12 and the corresponding
data to pinned Linux `4d7d9486c04d917265f64c55bd23b2cc4fe7749c`:
[the binding ID](../../patches/proposals/0004-dt-bindings-power-add-mt6797-conn-domain-id.patch)
and [the SCPSYS entry](../../patches/proposals/0005-pmdomain-mediatek-describe-mt6797-conn-island.patch).
The latter selects the already compiled initially-off, clock-before-reset OFF
and failure-retention capabilities. Registration must see both CONN power
status bits off before publishing the domain; it performs no CONN power-on.
All three manifest profiles selecting `patches/series-mt6797-provider-compile`
are isolated `allnoconfig` compile profiles. No boot profile or DT consumer
selects these proposals.

This data does not make activation safe. A common CONSYS owner must establish
SPM register-control authority, VCN rail and independent CONMCU-reset order,
client exclusion, EMI/remap policy, and a fault check before every use. The
SCPSYS failure latch alone cannot retain resources owned outside SCPSYS.
Do not attach a consumer or deploy this compile series as a boot candidate.

The two patches replay on the prepared provider-compile source in order,
and each passes the pinned kernel's
`checkpatch.pl --no-tree --no-signoff` with zero errors and warnings. They
carry synthetic, non-certifying authorship and no DCO sign-off; they are not
upstream submissions.

Buildbox fetched clean pushed commit `32272b49cb8d73331f006fb9f8b1ef5a67e19633`,
applied all 19 selected patches, and compiled and linked
`mt6797-provider-compile`. The validated package inventory is
`8ebdf147a8818da56c81ac7cebc94bd35e75b58c60d44775167edff6ba7356a0`;
the [sanitized build result](buildbox-result.json) pins its source, patchset,
config and linked SCPSYS symbols. No device execution or boot candidate was
produced. The next implementation step is the common owner that keeps the
external rail/reset resources and checks SCPSYS's latched fault before any
firmware transaction.
