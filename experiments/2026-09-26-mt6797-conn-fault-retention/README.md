# MT6797 CONN provider failure retention prerequisite

The legacy MediaTek SCPSYS ON callback releases its clock and optional supply
after an ACK, SRAM or bus-protection error, even when the power request has
already been written and OFF has not been proved. For a future initially-off
CONN domain, that cleanup could remove prerequisites from an uncertain island.

The [one-change proposal](../../patches/proposals/0003-pmdomain-mediatek-retain-failed-domain-resources.patch)
adds an opt-in failure latch to the existing provider. An opted domain keeps
acquired prerequisites after an ON failure, records the first error, and
refuses later ON/OFF callbacks. OFF errors also latch; the existing OFF path
already retains clock and supply votes before a confirmed OFF ACK. Domains
without the flag keep their previous cleanup behavior. The new flag requires
the existing initially-off registration capability, so a flagged domain cannot
fail during provider-probe activation.

No domain selects the flag, so this patch has no device effect. It does not
acquire CONN rails, control independent CONMCU reset, enable the SPM key,
choose an EMI policy or grant a WLAN transaction. A failed OFF can leave genpd
software state ON, causing a later consumer resume to skip the power callback;
the eventual shared owner must check the latched fault before **every** use.
There is no automatic recovery or resource release from a latched fault.

The patch was exported from a temporary single-file Git tree using Linux
`4d7d9486c04d917265f64c55bd23b2cc4fe7749c` SCPSYS source SHA-256
`9ce2b2c95a38bc4c7b801aff9b7c26da2dc8ec2e3fd34199adaedf1db3007226`
after applying the selected deferred-registration and CONN OFF-order proposals.
It replayed onto that exact predecessor with whitespace checks. Pinned upstream
`checkpatch.pl --no-tree --no-signoff` reported zero errors and warnings.
The synthetic patch author makes no DCO certification; this is an internal
integration proposal, not an upstream submission. The destination is the
MediaTek power-domain provider; delete the proposal if upstream takes an
equivalent failure-retention design or this shared owner is replaced.

The isolated `mt6797-provider-compile` series selects this patch after its
two prerequisites. Compilation can validate integration, but only a later
admitted domain and owner-controlled device protocol can test failure
retention on hardware. No boot2 candidate is admitted by this change.
