# MT6797 CONN in the modern child-domain provider, compile-only

The existing Linux 7.1.3 child-domain provider creates domains only for
available DT child nodes. Its MT6797 data was absent. The selected Gemian and
Planet clock providers place CONN control at SPM `0x32c`, dual status bit 1 at
`0x180`/`0x184`, and infracfg protection bits 17–18 at `0x220` with status
at `0x228`. The [power-domain contract](../2026-09-05-mt6797-wifi-contract/POWER_DOMAIN.md)
pins those facts and distinguishes the unrelated generic CONN offset `0x280`.

The isolated series reuses the earlier [ID-12 binding patch](../../patches/proposals/0004-dt-bindings-power-add-mt6797-conn-domain-id.patch),
then applies the modern provider's checked initial-OFF, fault-retention and
status-read proposals. A [binding patch](../../patches/proposals/0011-dt-bindings-power-admit-mt6797-child-domain-controller.patch)
admits a distinct `mediatek,mt6797-power-controller` compatible. The
[data patch](../../patches/proposals/0012-pmdomain-mediatek-describe-mt6797-conn-child-domain.patch)
defines only CONN at ID 12, selects confirmed initial OFF and fault retention,
and rejects undefined MT6797 IDs. No DT node uses the new compatible and no
child or consumer is added. The accepted A53 DT keeps its separate legacy
flat SCPSYS node; this profile is not a boot candidate.

The data does not establish the selected vendor OFF power-bit ordering, SPM
register-control authority, external VCN rail and independent CONMCU reset,
or shared remap/EMI ownership. A future CONSYS owner must query the retained
fault before every hardware use, including after a failed OFF that genpd may
not retry. The default-off flag prevents probe-time CONN power-on, but it does
not authorize an effect-bearing DT child or firmware load.

The patches apply in canonical order to the pinned Linux 7.1.3 source.
Pinned checkpatch reports zero errors and warnings for the binding patch;
the new SoC header produces only its generic MAINTAINERS-coverage warning.
The pinned MAINTAINERS file already covers `drivers/pmdomain/` under GENERIC
PM DOMAINS, so no new ownership entry is invented.
No DCO certification is made by these internal proposals.
