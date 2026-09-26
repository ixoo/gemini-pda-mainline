# MT6797 modern CONN SPM preamble, compile-only

The selected Planet and Gemian CONN control paths write `0x0b160001` to
SPM `+0x000` before ON and OFF transitions. The
[source audit](../2026-09-05-mt6797-wifi-contract/SPM_KEY_ORDER.md)
distinguishes this shared SPM register from the unrelated CSPM key and does
not establish retained-firmware writer exclusion or a safe clear operation.
The legacy SCPSYS [proposal](../2026-09-26-mt6797-conn-spm-register-control/README.md)
already models the same preamble in its isolated profile.

The [modern provider patch](../../patches/proposals/0014-pmdomain-mediatek-select-mt6797-conn-spm-preamble.patch)
uses the provider's existing SPM regmap. Only the MT6797 CONN data selects the
value. ON writes it after basic clock acquisition and before a power request;
OFF writes it before bus protection. Both writes check the regmap result. A
failed write latches a fault and leaves acquired resources retained for the
opted domain; no later transition step runs. The patch does not clear the
shared enable. Other domains perform no added write.

It follows the fault query in the canonical series and the isolated
`mt6797-modern-provider-compile` profile. No MT6797 child DT node or client
is present. The accepted A53 profile stays unchanged, and this is not a
boot2 candidate. Pinned checkpatch reports zero errors and warnings. The
synthetic patch author makes no DCO certification or upstream submission.

Buildbox compilation remains to be recorded. A device transition still needs
the external VCN rail, independent CONMCU reset, source-supported OFF order,
shared remap/EMI policy, and retained-writer exclusion before admission.
