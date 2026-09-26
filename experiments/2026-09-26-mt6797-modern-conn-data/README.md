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

The [Buildbox result](results/build.json) records a full ARM64 kernel link
from clean pushed commit `7c8f349542c7ee20f7b2d035840430039bcd6112`.
The fetched package passed its SHA256 inventory check and contains all six
selected patches. The resolved configuration builds the modern provider and
disables the legacy one; `System.map` contains `mt6797_scpsys_data`. Neither
packaged MT6797 DTB contains the new compatible string. These are build and
DTB-selection checks, not hardware activation.

The patched source passed `make dt_binding_check` for the changed power
controller schema on Buildbox. Isolated `dtschema` 2026.9 and `yamllint` 1.38.0
also passed direct `dt-doc-validate` and YAML lint for that file. The direct
checks matter because this kernel Makefile treats some schema-tool failures
as warnings. No MT6797 child-node example or effect-bearing DT was added.
